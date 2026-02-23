# Finance Tracker

个人财务追踪工具（当前仅支持通过 QQ 邮箱 IMAP 拉取招商银行动账通知邮件）。

## 功能范围（已实现）

- QQ 邮箱 IMAP 同步（招商银行动账通知）
- 招行动账邮件解析（消费/入账/收款等常见格式）
- 统一交易模型 `RawTransaction`
- 本地 SQLite 入库与去重
- 账户 `last_sync_time` 记录与增量同步
- 账户 `current_balance` 更新（有余额则直接写入；无余额则按交易类型增减）
- 净资产计算（基于 `accounts.current_balance`）
- CLI 操作（同步/配置/调度/查询）

## 快速开始

### 1. 准备配置

复制示例配置并填写你的 QQ 邮箱与授权码：

```bash
cp config/config.example.yaml config/config.yaml
nano config/config.yaml
```

**`config.yaml` 关键字段说明**

- `sources.qqmail.username`：QQ 邮箱地址
- `sources.qqmail.auth_code`：QQ 邮箱授权码（不是登录密码）
- `sources.qqmail.account_id`：卡号尾号（建议填写，用于按账户同步与 `last_sync_time` 过滤）

授权码获取路径：QQ 邮箱 → 设置 → 账户 → 开启 IMAP/SMTP 服务。

### 2. 运行同步（Dry-Run）

先试运行，确认解析正常：

```bash
python3 cli.py sync run --source qqmail --days 7 --dry-run
```

### 3. 正式入库同步

去掉 `--dry-run` 即写入本地数据库：

```bash
python3 cli.py sync run --source qqmail --days 7
```

数据库默认路径：`./data/finance.db`

### 4. 增量同步说明

- 系统会在 `accounts.last_sync_time` 中记录**该账户最新交易时间**。
- 下次同步会优先从该时间开始拉取，避免重复。

### 5. 常用 CLI 命令

```bash
# 查看同步状态
python3 cli.py sync status

# 查看当前配置
python3 cli.py config show

# 修改配置项（示例）
python3 cli.py config set sources.qqmail.account_id 8551

# 启动调度器（每 60 分钟检查）
python3 cli.py schedule start --interval 60

# 查看账户信息（含 current_balance）
python3 cli.py account list --limit 50

# 查看交易记录
python3 cli.py tx list --limit 50

# 按账户和交易类型过滤
python3 cli.py tx list --account-id 8551 --type income
```

## 数据模型与存储

- 统一模型：`src/models/transaction.py`
- SQLite 存储：`src/storage/database.py`
- 账户表：`accounts`（包含 `current_balance` 与 `last_sync_time`）
- 交易表：`transactions`（包含 `account_pk` 外键）

## 开发与测试

### 环境准备

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### 运行测试

```bash
python3 -m pytest tests/
```

## 项目结构

```
finance-tracker/
├── config/
│   └── config.example.yaml    # 示例配置（当前实现以此为准）
├── src/
│   ├── adapters/              # 数据源适配器
│   ├── models/                # 数据模型
│   ├── parsers/               # 招行动账邮件解析
│   ├── services/              # CLI/调度编排
│   ├── storage/               # SQLite 存储
│   └── utils/
├── data/
│   ├── imports/               # 预留目录（未使用）
│   └── finance.db             # SQLite 数据库（运行后生成）
├── logs/                       # 运行日志（忽略）
├── openspec/                   # OpenSpec 工件
├── tests/
└── README.md
```

## 注意事项

- `config/config.yaml` 包含敏感信息，已在 `.gitignore` 中忽略，不要提交。
- 当前仅支持招商银行动账邮件，其他来源未实现。

---

*Last updated: 2026-02-23*
