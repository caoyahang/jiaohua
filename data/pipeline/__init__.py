"""data.pipeline：数据管道层。

- etl：抽取 → 质量校验 → 入库（TDengine/PostgreSQL）
- quality_check：范围检查/突变检查/缺失插值 + 换向期数据标记剔除（V1.1红线）
- quality_report：数据质量日报统计（覆盖率/在线率/各标记计数，方案§3.3）
- feature_store：约40维配煤特征组装（特征分组常量定义）
- k_coefficients：K均/K安/K1/K2/K3 热工K系数计算
"""
