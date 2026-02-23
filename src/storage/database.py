"""
数据库访问层
支持 SQLite（本地）和 PostgreSQL（生产）
"""

import sqlite3
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from contextlib import contextmanager

from src.storage.schema import ACCOUNTS_TABLE_SQL

from src.models.transaction import RawTransaction


class TransactionRepository:
    """交易数据仓库"""
    
    def __init__(self, db_path: str = "./data/finance.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 账户表（先创建，供交易表外键引用）
            cursor.execute(ACCOUNTS_TABLE_SQL)

            # 主交易表（包含 accounts 外键）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id TEXT UNIQUE NOT NULL,
                    
                    -- 来源信息
                    source_type TEXT NOT NULL,
                    source_account TEXT NOT NULL,
                    raw_id TEXT,
                    
                    -- 时间信息
                    transaction_time DATETIME NOT NULL,
                    record_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    timezone TEXT DEFAULT 'Asia/Shanghai',
                    
                    -- 账户信息
                    account_id TEXT NOT NULL,
                    account_pk INTEGER,
                    account_type TEXT,
                    account_name TEXT,
                    
                    -- 交易详情
                    transaction_type TEXT NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    currency TEXT DEFAULT 'CNY',
                    balance DECIMAL(15, 2),
                    
                    -- 对手方信息（JSON 存储）
                    counterparty_name TEXT,
                    counterparty_type TEXT,
                    counterparty_category TEXT,
                    
                    -- 支付渠道（JSON 存储）
                    channel_name TEXT,
                    channel_provider TEXT,
                    channel_method TEXT,
                    
                    -- 位置信息（JSON 存储）
                    location_city TEXT,
                    location_country TEXT,
                    
                    -- 元数据
                    metadata TEXT,  -- JSON
                    raw_data TEXT,
                    tags TEXT,  -- JSON 数组
                    notes TEXT,
                    
                    -- 状态
                    status TEXT DEFAULT 'confirmed',
                    verification_status TEXT DEFAULT 'unverified',
                    
                    -- 索引字段
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (account_pk) REFERENCES accounts(id)
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_transactions_time 
                ON transactions(transaction_time)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_transactions_account 
                ON transactions(account_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_transactions_type 
                ON transactions(transaction_type)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_transactions_source 
                ON transactions(source_type, source_account)
            ''')
            
            # 日汇总表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    date DATE PRIMARY KEY,
                    account_id TEXT,
                    total_expense DECIMAL(15, 2) DEFAULT 0,
                    total_income DECIMAL(15, 2) DEFAULT 0,
                    transaction_count INTEGER DEFAULT 0,
                    top_category TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 处理日志表（防止重复处理）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processing_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT,  -- success/failed/skipped
                    message TEXT,
                    UNIQUE(source_type, source_id)
                )
            ''')

            conn.commit()
            print("[✓] 数据库初始化完成")

        self._ensure_accounts_columns()
        self._ensure_transactions_account_fk()

    def _ensure_accounts_columns(self) -> None:
        """确保 accounts 表存在必要字段"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(accounts)")
            cols = [r[1] for r in cursor.fetchall()]
            if "last_sync_time" not in cols:
                cursor.execute("ALTER TABLE accounts ADD COLUMN last_sync_time DATETIME")
            if "current_balance" not in cols:
                cursor.execute("ALTER TABLE accounts ADD COLUMN current_balance DECIMAL(15, 2)")
            conn.commit()

    def _ensure_transactions_account_fk(self) -> None:
        """
        确保 transactions 表存在 account_pk 外键字段并完成回填
        若缺少外键约束，则重建表结构并迁移数据
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(transactions)")
            cols = [r[1] for r in cursor.fetchall()]
            if "account_pk" not in cols:
                cursor.execute("ALTER TABLE transactions ADD COLUMN account_pk INTEGER")

            cursor.execute("SELECT DISTINCT account_id FROM transactions")
            for (account_id,) in cursor.fetchall():
                if not account_id:
                    continue
                cursor.execute(
                    "INSERT OR IGNORE INTO accounts (account_id) VALUES (?)",
                    (account_id,),
                )

            cursor.execute(
                """
                UPDATE transactions
                SET account_pk = (
                    SELECT id FROM accounts WHERE accounts.account_id = transactions.account_id
                )
                WHERE account_pk IS NULL
                """
            )

            cursor.execute("PRAGMA foreign_key_list(transactions)")
            fk_list = cursor.fetchall()
            has_fk = any(row[3] == "account_pk" and row[2] == "accounts" for row in fk_list)
            if not has_fk:
                self._rebuild_transactions_with_fk(conn)

            conn.commit()

    def _rebuild_transactions_with_fk(self, conn: sqlite3.Connection) -> None:
        """重建 transactions 表以添加外键约束"""
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")

        cursor.execute("ALTER TABLE transactions RENAME TO transactions_old")

        cursor.execute('''
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                
                source_type TEXT NOT NULL,
                source_account TEXT NOT NULL,
                raw_id TEXT,
                
                transaction_time DATETIME NOT NULL,
                record_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                timezone TEXT DEFAULT 'Asia/Shanghai',
                
                account_id TEXT NOT NULL,
                account_pk INTEGER,
                account_type TEXT,
                account_name TEXT,
                
                transaction_type TEXT NOT NULL,
                amount DECIMAL(15, 2) NOT NULL,
                currency TEXT DEFAULT 'CNY',
                balance DECIMAL(15, 2),
                
                counterparty_name TEXT,
                counterparty_type TEXT,
                counterparty_category TEXT,
                
                channel_name TEXT,
                channel_provider TEXT,
                channel_method TEXT,
                
                location_city TEXT,
                location_country TEXT,
                
                metadata TEXT,
                raw_data TEXT,
                tags TEXT,
                notes TEXT,
                
                status TEXT DEFAULT 'confirmed',
                verification_status TEXT DEFAULT 'unverified',
                
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (account_pk) REFERENCES accounts(id)
            )
        ''')

        cursor.execute('''
            INSERT INTO transactions (
                id, transaction_id, source_type, source_account, raw_id,
                transaction_time, record_time, timezone,
                account_id, account_pk, account_type, account_name,
                transaction_type, amount, currency, balance,
                counterparty_name, counterparty_type, counterparty_category,
                channel_name, channel_provider, channel_method,
                location_city, location_country,
                metadata, raw_data, tags, notes,
                status, verification_status,
                created_at, updated_at
            )
            SELECT
                id, transaction_id, source_type, source_account, raw_id,
                transaction_time, record_time, timezone,
                account_id, account_pk, account_type, account_name,
                transaction_type, amount, currency, balance,
                counterparty_name, counterparty_type, counterparty_category,
                channel_name, channel_provider, channel_method,
                location_city, location_country,
                metadata, raw_data, tags, notes,
                status, verification_status,
                created_at, updated_at
            FROM transactions_old
        ''')

        cursor.execute("DROP TABLE transactions_old")

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_transactions_time 
            ON transactions(transaction_time)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_transactions_account 
            ON transactions(account_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_transactions_type 
            ON transactions(transaction_type)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_transactions_source 
            ON transactions(source_type, source_account)
        ''')

        cursor.execute("PRAGMA foreign_keys=ON")
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()
    
    def save_transaction(self, transaction: RawTransaction) -> Tuple[bool, str]:
        """
        保存交易记录
        
        Returns:
            (是否成功, 消息)
        """
        # 生成交易ID
        transaction_id = transaction.generate_transaction_id()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # 检查是否已存在
                cursor.execute(
                    'SELECT id FROM transactions WHERE transaction_id = ?',
                    (transaction_id,)
                )
                if cursor.fetchone():
                    return False, "duplicate"
                
                account_pk = self._ensure_account(
                    account_id=transaction.account_id,
                    account_name=transaction.account_name,
                    account_type=transaction.account_type,
                )

                # 准备数据
                data = self._transaction_to_db_dict(transaction, transaction_id)
                data['account_pk'] = account_pk
                
                # 插入数据
                columns = ', '.join(data.keys())
                placeholders = ', '.join('?' for _ in data)
                
                cursor.execute(f'''
                    INSERT INTO transactions ({columns})
                    VALUES ({placeholders})
                ''', list(data.values()))
                
                conn.commit()
                self.update_account_last_sync_time(
                    account_id=transaction.account_id,
                    last_sync_time=transaction.transaction_time,
                    account_name=transaction.account_name,
                    account_type=transaction.account_type,
                )
                self._sync_current_balance(transaction)
                return True, "saved"
                
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return False, f"integrity_error: {e}"
            except Exception as e:
                conn.rollback()
                return False, f"error: {e}"
    
    def _transaction_to_db_dict(self, transaction: RawTransaction, 
                                 transaction_id: str) -> Dict[str, Any]:
        """将 RawTransaction 转换为数据库字典"""
        data = {
            'transaction_id': transaction_id,
            'raw_id': transaction.raw_id,
            'source_type': transaction.source_type,
            'source_account': transaction.source_account,
            'transaction_time': transaction.transaction_time.isoformat(),
            'timezone': transaction.timezone,
            'account_id': transaction.account_id,
            'account_pk': None,
            'account_type': transaction.account_type,
            'account_name': transaction.account_name,
            'transaction_type': transaction.transaction_type,
            'amount': str(transaction.amount),
            'currency': transaction.currency,
            'balance': str(transaction.balance) if transaction.balance else None,
            'metadata': json.dumps(transaction.metadata) if transaction.metadata else None,
            'raw_data': transaction.raw_data,
            'tags': json.dumps(transaction.tags) if transaction.tags else None,
            'notes': transaction.notes,
            'status': transaction.status,
            'verification_status': transaction.verification_status,
        }
        
        # 对手方信息
        if transaction.counterparty:
            data['counterparty_name'] = transaction.counterparty.name
            data['counterparty_type'] = transaction.counterparty.type
            data['counterparty_category'] = transaction.counterparty.category
        
        # 支付渠道
        if transaction.channel:
            data['channel_name'] = transaction.channel.name
            data['channel_provider'] = transaction.channel.provider
            data['channel_method'] = transaction.channel.method
        
        # 位置
        if transaction.location:
            data['location_city'] = transaction.location.city
            data['location_country'] = transaction.location.country
        
        return data
    
    def get_transactions(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        account_id: Optional[str] = None,
        transaction_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """查询交易记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if start_time:
                conditions.append('transaction_time >= ?')
                params.append(start_time.isoformat())
            
            if end_time:
                conditions.append('transaction_time <= ?')
                params.append(end_time.isoformat())
            
            if account_id:
                conditions.append('account_id = ?')
                params.append(account_id)
            
            if transaction_type:
                conditions.append('transaction_type = ?')
                params.append(transaction_type)
            
            # 构建 SQL
            sql = 'SELECT * FROM transactions'
            if conditions:
                sql += ' WHERE ' + ' AND '.join(conditions)
            sql += ' ORDER BY transaction_time DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]

    def get_last_sync_time(self, account_id: str) -> Optional[datetime]:
        """获取指定账户的最后同步时间"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT last_sync_time FROM accounts WHERE account_id = ?",
                (account_id,),
            )
            row = cursor.fetchone()
            if not row or not row[0]:
                return None
            try:
                return datetime.fromisoformat(row[0])
            except Exception:
                return None

    def get_single_account_last_sync_time(self) -> Tuple[Optional[str], Optional[datetime]]:
        """
        若 accounts 表仅有一条记录，返回其 account_id 与 last_sync_time
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT account_id, last_sync_time FROM accounts")
            rows = cursor.fetchall()
            if len(rows) != 1:
                return None, None
            account_id, last_sync_time = rows[0][0], rows[0][1]
            if not last_sync_time:
                return account_id, None
            try:
                return account_id, datetime.fromisoformat(last_sync_time)
            except Exception:
                return account_id, None

    def update_account_last_sync_time(
        self,
        account_id: str,
        last_sync_time: datetime,
        account_name: Optional[str] = None,
        account_type: Optional[str] = None,
    ) -> None:
        """更新账户的最后同步时间（不存在则创建）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO accounts (account_id, account_name, account_type)
                VALUES (?, ?, ?)
                """,
                (account_id, account_name, account_type),
            )
            cursor.execute(
                """
                UPDATE accounts
                SET last_sync_time = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    account_name = COALESCE(account_name, ?),
                    account_type = COALESCE(account_type, ?)
                WHERE account_id = ?
                  AND (last_sync_time IS NULL OR last_sync_time < ?)
                """,
                (
                    last_sync_time.isoformat(),
                    account_name,
                    account_type,
                    account_id,
                    last_sync_time.isoformat(),
                ),
            )
            conn.commit()

    def update_account_current_balance(
        self,
        account_id: str,
        current_balance: Decimal,
        account_name: Optional[str] = None,
        account_type: Optional[str] = None,
    ) -> None:
        """更新账户当前余额（不存在则创建）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO accounts (account_id, account_name, account_type)
                VALUES (?, ?, ?)
                """,
                (account_id, account_name, account_type),
            )
            cursor.execute(
                """
                UPDATE accounts
                SET current_balance = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    account_name = COALESCE(account_name, ?),
                    account_type = COALESCE(account_type, ?)
                WHERE account_id = ?
                """,
                (str(current_balance), account_name, account_type, account_id),
            )
            conn.commit()

    def _sync_current_balance(self, transaction: RawTransaction) -> None:
        """
        同步 accounts.current_balance：
        1) 若交易自带 balance，则直接使用
        2) 否则按交易类型增减（基于当前余额，默认 0）
        """
        if transaction.balance is not None:
            self.update_account_current_balance(
                account_id=transaction.account_id,
                current_balance=transaction.balance,
                account_name=transaction.account_name,
                account_type=transaction.account_type,
            )
            return

        # 无 balance 时按交易类型增减
        delta = self._infer_balance_delta(transaction)
        if delta is None:
            return

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT current_balance FROM accounts WHERE account_id = ?",
                (transaction.account_id,),
            )
            row = cursor.fetchone()
            current = Decimal(str(row[0])) if row and row[0] is not None else Decimal("0")

        new_balance = current + delta
        self.update_account_current_balance(
            account_id=transaction.account_id,
            current_balance=new_balance,
            account_name=transaction.account_name,
            account_type=transaction.account_type,
        )

    def _infer_balance_delta(self, transaction: RawTransaction) -> Optional[Decimal]:
        """根据交易类型推断余额变化"""
        tx_type = transaction.transaction_type
        amount = transaction.amount
        if amount is None:
            return None

        # 支出类
        if tx_type in {"consumption", "transfer_out", "fee"}:
            return Decimal("0") - amount

        # 收入类
        if tx_type in {"income", "transfer_in", "refund", "interest", "dividend"}:
            return amount

        return None

    def _ensure_account(
        self,
        account_id: str,
        account_name: Optional[str] = None,
        account_type: Optional[str] = None,
    ) -> Optional[int]:
        """确保账户存在并返回主键"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO accounts (account_id, account_name, account_type)
                VALUES (?, ?, ?)
                """,
                (account_id, account_name, account_type),
            )
            cursor.execute(
                """
                UPDATE accounts
                SET account_name = COALESCE(account_name, ?),
                    account_type = COALESCE(account_type, ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE account_id = ?
                """,
                (account_name, account_type, account_id),
            )
            cursor.execute(
                "SELECT id FROM accounts WHERE account_id = ?",
                (account_id,),
            )
            row = cursor.fetchone()
            conn.commit()
            return row[0] if row else None
