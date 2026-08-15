# prometheus/rules/ —— 告警规则文件放置约定

- 告警规则按模块分文件：`<模块>_rules.yml`（如 `blend_rules.yml`、`furnace_rules.yml`）。
- 新增规则文件后，在 `../prometheus.yml` 的 `rule_files:` 中登记引用才会生效。
- 告警阈值必须与 `config/settings.yaml` 同源，禁止在规则文件里自创第二份口径（总纲 §0.1）。
