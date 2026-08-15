"""LSTM 火道温度预测模型（方案 4.2.3/4.2.4 步骤1：状态预估）。

输入：过去 60min 多变量序列（火道温度、煤气流量、分烟道吸力、烟气残氧，1min采样）
输出：未来 30min 火道温度曲线（30 个时间步）

⚠️ 数据清洗前提：换向前后 2~3 分钟的温度/流量/吸力为脏数据，
必须在 ETL 管道打标剔除后再喂入本模型（方案 4.2.6）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

# 序列窗口定义（对齐方案 4.2.4）
INPUT_WINDOW_MIN = 60    # 过去 60 分钟
OUTPUT_WINDOW_MIN = 30   # 预测未来 30 分钟
# 输入特征通道（与 4.2.5 采集清单对齐，重采样到 1min）
FEATURE_COLUMNS = ["fire_temp", "gas_flow", "flue_draft", "residual_o2"]


class TemperatureLSTM(nn.Module):
    """LSTM 温度预测网络：序列输入 → 未来 30 步温度曲线。"""

    def __init__(
        self,
        n_features: int = len(FEATURE_COLUMNS),
        hidden_size: int = 128,
        num_layers: int = 2,
        output_steps: int = OUTPUT_WINDOW_MIN,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.output_steps = output_steps
        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        # 取最后时刻隐状态 → 线性映射到未来 30 步温度
        self.head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, output_steps),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        :param x: (batch, 60, n_features) 过去 60min 标准化后的序列
        :return: (batch, 30) 未来 30min 温度预测（标准化空间）
        """
        out, _ = self.lstm(x)
        return self.head(out[:, -1, :])


@dataclass
class LSTMTrainConfig:
    """训练超参（后续由贝叶斯优化自动调参，方案 4.2.3）。"""

    epochs: int = 100
    batch_size: int = 64
    learning_rate: float = 1e-3
    hidden_size: int = 128
    num_layers: int = 2
    val_ratio: float = 0.15
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    feature_columns: List[str] = field(default_factory=lambda: list(FEATURE_COLUMNS))


class TemperaturePredictor:
    """LSTM 温度预测器：训练、推理、标准化封装（供 MPC 步骤1调用）。"""

    def __init__(self, config: Optional[LSTMTrainConfig] = None):
        self.cfg = config or LSTMTrainConfig()
        self.model = TemperatureLSTM(
            n_features=len(self.cfg.feature_columns),
            hidden_size=self.cfg.hidden_size,
            num_layers=self.cfg.num_layers,
        ).to(self.cfg.device)
        # 标准化参数（fit 时统计，推理时复用）
        self.feat_mean: Optional[np.ndarray] = None
        self.feat_std: Optional[np.ndarray] = None
        self.temp_mean: float = 0.0
        self.temp_std: float = 1.0

    # ------------------------------------------------------------------ #
    def make_sequences(
        self, df: "pd.DataFrame"
    ) -> tuple[np.ndarray, np.ndarray]:
        """把长时序 DataFrame 切分为 (样本, 60, 特征) / (样本, 30) 监督序列。

        TODO(数据): 接 TDengine 炉温记录表(3.4.4 炉温/4.2.5 采集清单)后按燃烧室
        分组切窗；切窗前确认换向期脏数据已被 ETL 剔除或插值。
        """
        import pandas as pd  # noqa: F401  （类型提示用）

        data = df[self.cfg.feature_columns].to_numpy(dtype=np.float32)
        temp_col = self.cfg.feature_columns.index("fire_temp")
        X, Y = [], []
        total = INPUT_WINDOW_MIN + OUTPUT_WINDOW_MIN
        for i in range(len(data) - total + 1):
            X.append(data[i: i + INPUT_WINDOW_MIN])
            Y.append(data[i + INPUT_WINDOW_MIN: i + total, temp_col])
        return np.asarray(X), np.asarray(Y)

    def fit(self, df: "pd.DataFrame") -> Dict[str, List[float]]:
        """训练（骨架：标准 MSE 回归训练循环）。

        TODO(训练): 加 MLflow 记录、早停、按燃烧室分组验证；超参后续用贝叶斯优化。
        """
        X, Y = self.make_sequences(df)
        self.feat_mean = X.reshape(-1, X.shape[-1]).mean(axis=0)
        self.feat_std = X.reshape(-1, X.shape[-1]).std(axis=0) + 1e-8
        self.temp_mean = float(Y.mean())
        self.temp_std = float(Y.std() + 1e-8)

        Xs = (X - self.feat_mean) / self.feat_std
        Ys = (Y - self.temp_mean) / self.temp_std

        n_val = int(len(Xs) * self.cfg.val_ratio)
        X_train = torch.tensor(Xs[:-n_val], device=self.cfg.device)
        Y_train = torch.tensor(Ys[:-n_val], device=self.cfg.device)
        X_val = torch.tensor(Xs[-n_val:], device=self.cfg.device)
        Y_val = torch.tensor(Ys[-n_val:], device=self.cfg.device)

        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.cfg.learning_rate)
        criterion = nn.MSELoss()
        history: Dict[str, List[float]] = {"train_loss": [], "val_loss": []}

        dataset = torch.utils.data.TensorDataset(X_train, Y_train)
        loader = torch.utils.data.DataLoader(dataset, batch_size=self.cfg.batch_size, shuffle=True)
        for epoch in range(self.cfg.epochs):
            self.model.train()
            epoch_loss = 0.0
            for xb, yb in loader:
                optimizer.zero_grad()
                loss = criterion(self.model(xb), yb)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item() * len(xb)
            self.model.eval()
            with torch.no_grad():
                val_loss = criterion(self.model(X_val), Y_val).item()
            history["train_loss"].append(epoch_loss / len(X_train))
            history["val_loss"].append(val_loss)
            if (epoch + 1) % 20 == 0:
                logger.info("epoch %d train=%.5f val=%.5f", epoch + 1,
                            history["train_loss"][-1], val_loss)
        return history

    # ------------------------------------------------------------------ #
    def predict_next_30min(self, history_60min: np.ndarray) -> np.ndarray:
        """MPC 步骤1接口：过去 60min 序列 → 未来 30min 温度曲线（℃）。

        :param history_60min: (60, n_features) 原始量纲序列
        :return: (30,) 未来 30min 火道温度预测
        """
        if self.feat_mean is None:
            raise RuntimeError("模型未训练/未加载标准化参数")
        x = (history_60min - self.feat_mean) / self.feat_std
        self.model.eval()
        with torch.no_grad():
            t = torch.tensor(x[None, ...], dtype=torch.float32, device=self.cfg.device)
            pred = self.model(t).cpu().numpy()[0]
        return pred * self.temp_std + self.temp_mean

    def save(self, path: str) -> None:
        """保存模型权重 + 标准化参数。"""
        torch.save({
            "state_dict": self.model.state_dict(),
            "config": self.cfg.__dict__,
            "feat_mean": self.feat_mean, "feat_std": self.feat_std,
            "temp_mean": self.temp_mean, "temp_std": self.temp_std,
        }, path)

    @classmethod
    def load(cls, path: str) -> "TemperaturePredictor":
        """加载训练好的预测器。"""
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        obj = cls(LSTMTrainConfig(**ckpt["config"]))
        obj.model.load_state_dict(ckpt["state_dict"])
        obj.feat_mean, obj.feat_std = ckpt["feat_mean"], ckpt["feat_std"]
        obj.temp_mean, obj.temp_std = ckpt["temp_mean"], ckpt["temp_std"]
        return obj
