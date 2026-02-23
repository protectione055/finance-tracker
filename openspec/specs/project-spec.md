# Finance Tracker 项目规范（Project Spec）

版本: 0.1  
日期: 2026-02-23  
范围: 当前代码库实现与既定方向的统一说明

## 1. 项目概述
Finance Tracker 是一个本地优先的个人财务管理工具，目标是从邮件/导出文件等渠道采集交易数据，统一为标准化交易模型，并存储到本地数据库，提供后续分析、报表与资产追踪能力的基础。

## 2. 目标
1. 统一交易数据模型，支持多来源数据标准化。
2. 自动同步交易邮件（当前实现为 QQ 邮箱 IMAP 抓取招行动账通知）。
3. 将交易数据持久化至本地 SQLite，支持查询与去重。
4. 记录账户余额历史，支持净资产计算。
5. 提供可操作的 CLI 入口，便于个人使用与自动化调度。

## 3. 非目标（当前版本）
1. 完整的多渠道导入（支付宝/微信/银行 CSV）已在配置或 README 中提及，但当前代码未实现。
2. 分析报告、预算、告警等能力在 README/config 中出现，但当前未有实现。
3. 完整的 Web/UI 展示与多用户协作不在当前范围。
4. 生产级任务调度、分布式存储与多数据库切换不在当前范围。

## 4. 典型场景
1. 用户在 QQ 邮箱中接收招行动账通知邮件，期望自动抓取并入库。
2. 用户希望通过 CLI 查看同步状态、触发同步与配置管理。
3. 用户记录余额历史并定期计算净资产变化。

## 5. 当前功能范围（以代码为准）
1. 交易数据模型:
   - `src/models/transaction.py` 定义 `RawTransaction` 等核心数据结构。
2. 邮件解析:
   - `src/parsers/cmb_email_parser.py` 支持多种招行动账通知格式解析。
3. 数据源适配器:
   - `src/adapters/qqmail_adapter.py` 通过 IMAP 拉取 QQ 邮箱并解析交易。
4. 数据存储:
   - `src/storage/database.py` 提供交易写入与查询（SQLite）。
   - `src/storage/balance_tracker.py` 记录余额历史与净资产计算。
5. CLI:
   - `cli.py` 提供 sync/config/schedule 命令组。
6. 调度:
   - `core/scheduler.py` 提供定时任务框架（每小时触发 QQ 邮箱同步）。

## 6. 体系结构
当前代码存在两套平行实现，后续需收敛：
1. 顶层 `core/` 与 `adapters/`:
   - `core/` 管理配置、同步、调度。
   - `adapters/qqmail.py` 实现 IMAP 抓取与简化解析。
   - 该路径中数据库写入仍为 TODO。
2. `src/` 体系:
   - `src/models/` 统一交易模型。
   - `src/parsers/` 处理招行动账邮件解析。
   - `src/adapters/` 管理 IMAP 拉取与解析。
   - `src/storage/` 提供 SQLite 持久化与余额/净资产追踪。

**收敛建议**：后续应选择 `src/` 体系作为主实现，将 `core/` 仅作为 CLI 调度与编排层，避免重复逻辑与配置分叉。

## 7. 关键数据流
1. IMAP 拉取邮件（QQ 邮箱）  
2. 解析招行动账通知，生成 `RawTransaction`  
3. 生成稳定交易 ID（hash）  
4. 持久化到 `data/finance.db`  
5. 可选：从交易中提取余额并记录账户余额历史  
6. 可选：计算净资产并记录历史

## 8. 交易数据模型规范（摘要）
统一模型为 `RawTransaction`，核心字段：
1. 来源标识:
   - `raw_id`, `source_type`, `source_account`
2. 交易信息:
   - `transaction_time`, `transaction_type`, `amount`, `currency`
3. 账户信息:
   - `account_id`, `account_type`, `account_name`
4. 对手方与渠道:
   - `counterparty`, `channel`, `location`
5. 元数据:
   - `metadata`, `raw_data`, `tags`, `notes`
6. 状态:
   - `status`, `verification_status`

备注:
1. `RawTransaction.generate_transaction_id()` 通过关键字段生成稳定 ID，用于去重。
2. 金额/余额使用 `Decimal`，序列化时转字符串。

## 9. 数据库规范（SQLite）
数据库路径默认 `./data/finance.db`，主要表结构：
1. `transactions`
   - 核心字段：交易 ID、时间、账户、金额、对手方、渠道、元数据。
   - 索引：时间、账户、类型、来源。
2. `daily_summaries`（预留/未使用）
3. `processing_logs`（预留/未使用）
4. `account_balances`
5. `net_worth_history`
6. `accounts`（账户元信息管理）

## 10. 配置规范
当前存在两份配置模板，需明确主用配置：
1. `config/config.example.yaml`（CLI 与 `core/` 使用）
   - `sources.qqmail`、`database`、`scheduler`、`logging`
   - 支持环境变量覆盖：
     - `QQMAIL_USERNAME` → `sources.qqmail.username`
     - `QQMAIL_AUTH_CODE` → `sources.qqmail.auth_code`
     - `DATABASE_URL` → `database.url`
2. `config/settings.yaml`（包含更多功能设想）
   - 含支付宝/微信/银行导入、报告、告警等配置，但当前未实现。

**规范要求**：对外发布与文档应以 `config/config.example.yaml` 为准，避免功能声明超出实现范围。

## 11. CLI 规范
入口：`cli.py`  
命令组：
1. `sync run --source qqmail|all --days N [--dry-run]`
2. `sync status`
3. `config show|get|set`
4. `schedule start --interval N`
5. `schedule status`

## 12. 自动化脚本
根目录脚本用于同步与数据更新（具体逻辑待核实）：
1. `auto_sync.py`
2. `auto_sync_hourly.py`
3. `fetch_and_update.py`
4. `save_to_db.py`

## 13. 安全与隐私
1. IMAP 认证使用 QQ 邮箱授权码，配置文件需避免提交到版本库。
2. 本地 SQLite 数据库包含敏感交易信息，应在本机保护与备份。
3. 日志中避免输出完整账户信息与敏感数据。

## 14. 已知缺口与待完善点
1. `core/sync_manager.py` 内的数据库写入逻辑为 TODO。
2. README 与配置中描述的支付宝/微信/银行 CSV 导入、预算、报告等功能未实现。
3. 两套实现（`core/` 与 `src/`）存在重复，需要统一入口与配置。
4. 测试目录为空，暂无自动化测试覆盖。

## 15. 里程碑建议（可选）
1. 收敛架构：统一 `core` 与 `src` 的实现路径。
2. 打通完整同步链路：IMAP → 解析 → DB 入库。
3. 完成最小分析与报表输出（Markdown）。
4. 增加测试覆盖：解析器、存储层、同步流程。
