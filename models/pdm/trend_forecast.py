"""level2 趋势预测：LSTM 振动趋势 + ISO 10816 分级（方案 4.3.2 level2 / 4.3.3）。

每天跑一次：用过去 7 天振动序列预测未来 7 天趋势，结合 ISO 10816
振动速度分级阈值输出 WARNING / DANGER 预警。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# ISO 10816 振动速度分级阈值（mm/s，方案 4.3.3）
# --------------------------------------------------------------------------- #
ISO10816_GOOD_MAX = 2.8       # < 2.8     良好：正常运行
ISO10816_NOTICE_MAX = 7.1     # 2.8~7.1   注意：加强监测频率
ISO10816_UNQUALIFIED_MAX = 18.0  # 7.1~18  不合格：计划检修
# > 18 危险：立即停机

GRADE_LABELS = {
    "GOOD": "良好（正常运行）",
    "NOTICE": "注意（加强监测频率）",
    "UNQUALIFIED": "不合格（计划检修）",
    "DANGER": "危险（立即停机）",
}


def iso10816_grade(velocity_mm_s: float) -> str:
    """按 ISO 10816 对振动速度分级。"""
    if velocity_mm_s < ISO10816_GOOD_MAX:
        return "GOOD"
    if velocity_mm_s < ISO10816_NOTICE_MAX:
        return "NOTICE"
    if velocity_mm_s < ISO10816_UNQUALIFIED_MAX:
        return "UNQUALIFIED"
    return "DANGER"


# --------------------------------------------------------------------------- #
# LSTM 趋势预测
# --------------------------------------------------------------------------- #
HISTORY_DAYS = 7    # 输入：过去 7 天
FORECAST_DAYS = 7   # 输出：未来 7 天


class TrendLSTM(nn.Module):
    """单变量振动趋势 LSTM（每小时一个点，7×24 → 7×24）。"""

    def __init__(self, input_steps: int = HISTORY_DAYS * 24,
                 output_steps: int = FORECAST_DAYS * 24,
                 hidden_size: int = 64, num_layers: int = 2):
        super().__init__()
        self.lstm = nn.LSTM(1, hidden_size, num_layers, batch_first=True,
                            dropout=0.1 if num_layers > 1 else 0.0)
        self.head = nn.Linear(hidden_size, output_steps)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        :param x: (batch, input_steps, 1)
        :return: (batch, output_steps)
        """
        out, _ = self.lstm(x)
        return self.head(out[:, -1, :])


@dataclass
class TrendForecastConfig:
    hidden_size: int = 64
    num_layers: int = 2
    epochs: int = 80
    learning_rate: float = 1e-3
    batch_size: int = 32
    device: str = "cuda" if torch.cuda.is_available() else "cpu"


class TrendForecaster:
    """设备振动趋势预测器（每台关键设备一个实例，每日定时跑一次）。"""

    def __init__(self, device_id: str, config: Optional[TrendForecastConfig] = None):
        self.device_id = device_id
        self.cfg = config or TrendForecastConfig()
        self.model = TrendLSTM(HISTORY_DAYS * 24, FORECAST_DAYS * 24,
                               self.cfg.hidden_size, self.cfg.num_layers).to(self.cfg.device)
        self._fitted = False

    # ------------------------------------------------------------------ #
    def fit(self, hourly_vibration: np.ndarray) -> None:
        """用历史小时级振动序列训练（骨架训练循环）。

        TODO(训练): 数据来自 TDengine 设备状态表(3.4.4)聚合到小时级；
        加验证集/早停/MLflow 记录；与 level1 共用设备台账。
        """
        series = np.asarray(hourly_vibration, dtype=np.float32)
        mean, std = float(series.mean()), float(series.std() + 1e-8)
        norm = (series - mean) / std
        self._norm = (mean, std)

        in_steps, out_steps = HISTORY_DAYS * 24, FORECAST_DAYS * 24
        X, Y = [], []
        for i in range(len(norm) - in_steps - out_steps + 1):
            X.append(norm[i: i + in_steps])
            Y.append(norm[i + in_steps: i + in_steps + out_steps])
        X_t = torch.tensor(np.asarray(X)[..., None], device=self.cfg.device)
        Y_t = torch.tensor(np.asarray(Y), device=self.cfg.device)

        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.cfg.learning_rate)
        criterion = nn.MSELoss()
        loader = torch.utils.data.DataLoader(
            torch.utils.data.TensorDataset(X_t, Y_t),
            batch_size=self.cfg.batch_size, shuffle=True,
        )
        self.model.train()
        for epoch in range(self.cfg.epochs):
            total = 0.0
            for xb, yb in loader:
                optimizer.zero_grad()
                loss = criterion(self.model(xb), yb)
                loss.backward()
                optimizer.step()
                total += loss.item() * len(xb)
            if (epoch + 1) % 20 == 0:
                logger.info("[%s] epoch %d loss=%.5f", self.device_id, epoch + 1,
                            total / len(X_t))
        self._fitted = True

    # ------------------------------------------------------------------ #
    def level2_trend_forecast(self, history_7d: np.ndarray) -> Optional[Dict[str, str]]:
        """每日趋势预警（方案 4.3.2 level2）。

        :param history_7d: 过去 7 天小时级振动速度序列（长度 7×24）
        :return: 预警字典或 None
        """
        if not self._fitted:
            raise RuntimeError(f"[{self.device_id}] 模型未训练")
        mean, std = self._norm
        norm = (np.asarray(history_7d, dtype=np.float32) - mean) / std
        self.model.eval()
        with torch.no_grad():
            x = torch.tensor(norm[None, ..., None], device=self.cfg.device)
            trend = self.model(x).cpu().numpy()[0] * std + mean

        grade = iso10816_grade(float(trend[-1]))
        if grade == "DANGER":
            return {"level": "DANGER", "device_id": self.device_id,
                    "msg": f"振动进入\"危险\"区（>{ISO10816_UNQUALIFIED_MAX}mm/s），建议尽快停机检查"}
        if grade == "UNQUALIFIED":
            return {"level": "WARNING", "device_id": self.device_id,
                    "msg": "劣化趋势明显，建议安排检修"}
        return None
