"""配煤成本优化器 —— 模型B：遗传算法寻优 + 模型C：SHAP解释（方案 4.1.2/4.1.5）。

重依赖（scikit-opt/shap）采用懒加载：导入 constraints 等轻量子模块时
不要求安装 scikit-opt（PEP 562）。
"""

__all__ = ["BlendingOptimizer", "OptimizeRequest", "OptimizeResponse", "BlendExplainer"]


def __getattr__(name: str):
    """按需加载重依赖模块（optimizer 依赖 scikit-opt，explainer 依赖 shap）。"""
    if name in ("BlendingOptimizer", "OptimizeRequest", "OptimizeResponse"):
        from . import optimizer
        return getattr(optimizer, name)
    if name == "BlendExplainer":
        from .explainer import BlendExplainer
        return BlendExplainer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
