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

from models.transaction import RawTransaction


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
            
            # 主交易表
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
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
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
                
                # 准备数据
                data = self._transaction_to_db_dict(transaction, transaction_id)
                
                # 插入数据
                columns = ', '.join(data.keys())
                placeholders = ', '.join('?' for _ in data)
                
                cursor.execute(f'''
                    INSERT INTO transactions ({columns})
                    VALUES ({placeholders})
                ''', list(data.values()))
                
                conn.commit()
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
