# Finance Tracker v2.0 架构设计

## 目标

将现有的脚本化工具重构为服务化的个人财务管理系统。

## 核心架构

```
┌─────────────────────────────────────────────────────────┐
│                      API Gateway                        │
│              (FastAPI + Uvicorn + Nginx)                  │
└─────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼──────┐  ┌────────▼────────┐  ┌──────▼──────┐
│   Sync     │  │   Analytics     │  │   Report    │
│  Service   │  │    Service      │  │   Service   │
└──────┬──────┘  └────────┬────────┘  └──────┬──────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────┐
│              Message Queue (Redis/RabbitMQ)          │
│         - 任务队列                                    │
│         - 事件总线                                  │
└─────────────────────────┬───────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼─────┐  ┌────────▼─────┐  ┌────────▼─────┐
│  PostgreSQL │  │    Redis     │  │   MinIO      │
│  (主数据库)  │  │   (缓存)     │  │  (文件存储)  │
└─────────────┘  └──────────────┘  └──────────────┘
```

## 服务拆分

### 1. Core API Service (核心 API 服务)
- **职责**: RESTful API 入口、认证、路由
- **技术**: FastAPI, Pydantic, JWT
- **端口**: 8000

### 2. Sync Service (同步服务)
- **职责**: 数据同步、定时任务、ETL
- **技术**: Celery, APScheduler
- **功能**:
  - QQ 邮箱拉取
  - 支付宝/微信/银行导入
  - 数据清洗和标准化

### 3. Analytics Service (分析服务)
- **职责**: 数据分析、预算、告警
- **技术**: Pandas, NumPy
- **功能**:
  - 消费分析
  - 预算追踪
  - 异常检测
  - 趋势预测

### 4. Report Service (报告服务)
- **职责**: 报告生成、导出
- **技术**: Jinja2, WeasyPrint
- **功能**:
  - Markdown/HTML/PDF 报告
  - 图表生成
  - 定时报告推送

## 数据模型

### 核心实体

```python
# 用户
class User:
    id: UUID
    email: str
    hashed_password: str
    settings: UserSettings
    created_at: datetime

# 账户
class Account:
    id: UUID
    user_id: UUID
    name: str
    type: AccountType  # BANK, CREDIT, WALLET
    institution: str
    account_number: str  # 脱敏
    currency: str
    initial_balance: Decimal
    current_balance: Decimal
    is_active: bool

# 交易
class Transaction:
    id: UUID
    account_id: UUID
    transaction_time: datetime
    type: TransactionType  # INCOME, EXPENSE, TRANSFER
    amount: Decimal
    currency: str
    balance_after: Decimal
    counterparty: str
    category: str
    description: str
    tags: List[str]
    source: str  # qqmail, alipay, manual
    source_id: str  # 原始ID
    raw_data: Dict  # 原始数据

# 分类规则
class CategorizationRule:
    id: UUID
    user_id: UUID
    name: str
    condition: RuleCondition  # counterparty_contains, amount_range
    category: str
    priority: int
    is_active: bool

# 预算
class Budget:
    id: UUID
    user_id: UUID
    name: str
    period: BudgetPeriod  # MONTHLY, YEARLY
    categories: List[str]
    amount: Decimal
    rollover: bool
    alerts: List[BudgetAlert]
```

## API 设计

### RESTful Endpoints

```
# 认证
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout

# 账户
GET    /api/v1/accounts
POST   /api/v1/accounts
GET    /api/v1/accounts/{id}
PUT    /api/v1/accounts/{id}
DELETE /api/v1/accounts/{id}
POST   /api/v1/accounts/{id}/sync

# 交易
GET    /api/v1/transactions
POST   /api/v1/transactions
GET    /api/v1/transactions/{id}
PUT    /api/v1/transactions/{id}
DELETE /api/v1/transactions/{id}
POST   /api/v1/transactions/bulk
POST   /api/v1/transactions/import

# 分类
GET    /api/v1/categories
POST   /api/v1/categories/rules
GET    /api/v1/categories/rules/{id}
PUT    /api/v1/categories/rules/{id}
DELETE /api/v1/categories/rules/{id}
POST   /api/v1/categories/apply

# 分析
GET    /api/v1/analytics/summary
GET    /api/v1/analytics/trends
GET    /api/v1/analytics/categories
GET    /api/v1/analytics/forecast

# 预算
GET    /api/v1/budgets
POST   /api/v1/budgets
GET    /api/v1/budgets/{id}
PUT    /api/v1/budgets/{id}
DELETE /api/v1/budgets/{id}
GET    /api/v1/budgets/{id}/status

# 报告
GET    /api/v1/reports
POST   /api/v1/reports/generate
GET    /api/v1/reports/{id}
GET    /api/v1/reports/{id}/download
POST   /api/v1/reports/schedule

# 同步
POST   /api/v1/sync/start
GET    /api/v1/sync/status
GET    /api/v1/sync/history
POST   /api/v1/sync/qqmail
POST   /api/v1/sync/alipay
POST   /api/v1/sync/wechat

# 设置
GET    /api/v1/settings
PUT    /api/v1/settings
GET    /api/v1/settings/data
POST   /api/v1/settings/data/backup
POST   /api/v1/settings/data/restore
DELETE /api/v1/settings/data/clear

# WebSocket (实时更新)
WS     /ws/transactions
WS     /ws/sync
WS     /ws/notifications
```

## 部署架构

### 开发环境
```
docker-compose up -d
```

### 生产环境
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/finance
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
  
  worker:
    build: .
    command: celery -A tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/finance
      - REDIS_URL=redis://redis:6379
  
  scheduler:
    build: .
    command: celery -A tasks beat --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379
  
  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=finance
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl

volumes:
  postgres_data:
  redis_data:
```

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| API | FastAPI | RESTful API |
| 任务队列 | Celery + Redis | 异步任务、定时任务 |
| 数据库 | PostgreSQL | 主数据库 |
| 缓存 | Redis | 会话、缓存、实时数据 |
| 前端 | Vue.js + Element Plus | 管理界面 |
| 部署 | Docker + Docker Compose | 容器化部署 |
| 监控 | Prometheus + Grafana | 监控告警 |

## 迁移路径

### 阶段 1: 核心 API (2周)
- 搭建 FastAPI 框架
- 数据库模型迁移
- 基础 CRUD API

### 阶段 2: 业务逻辑 (2周)
- 同步服务
- 分析服务
- 分类服务

### 阶段 3: 高级功能 (2周)
- 报告服务
- 预算告警
- WebSocket 实时更新

### 阶段 4: 前端与部署 (2周)
- Vue.js 管理界面
- Docker 部署
- 监控告警

## 下一步行动

1. 确认架构设计
2. 搭建开发环境
3. 开始 Phase 1 开发

需要我立即开始实施吗？