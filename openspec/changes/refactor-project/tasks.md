# Tasks: refactor-project

## 1. 代码收敛
1. 选定 `src/` 为唯一实现路径。
2. `cli.py` 改为调用 `src` 实现（适配器、解析器、存储）。
3. `core/sync_manager.py` 对接 `src/storage/database.py`，补齐写库逻辑。

## 2. 数据链路打通
1. 交易入库：解析后写入 `transactions`，支持去重与统计。
2. 可选：从交易中提取余额，记录到 `account_balances`。

## 3. 配置与文档一致
1. 明确主配置模板（`config/config.example.yaml`）。
2. `config/settings.yaml` 中未实现内容标注 future/experimental。
3. README 中标注未实现功能或移除描述。

## 4. 测试补齐
1. CMB 邮件解析器单测（覆盖多格式样例）。
2. 数据库存储写入与去重测试。
