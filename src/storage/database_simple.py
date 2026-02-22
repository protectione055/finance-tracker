"""
精简版数据库 - 两表设计
1. accounts - 账户表（记录当前余额）
2. transactions - 交易记录表（记录动账）
"""

import sqlite3
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from contextlib import contextmanager

from models.transaction import RawTransaction


class SimpleDatabase:
    """精简版数据库"""
    
    def __init__(self, db_path: str = "./data/finance_simple.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()
    
    def _init_tables(self):
        """初始化表结构"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. 账户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    account_number TEXT,              -- 卡号尾号等
                    account_name TEXT NOT NULL,     -- 账户名称
                    account_type TEXT NOT NULL,     -- debit/credit/wallet
                    institution TEXT,               -- 招商银行/支付宝等
                    current_balance DECIMAL(15,2) DEFAULT 0,  -- 当前余额
                    currency TEXT DEFAULT 'CNY',
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 2. 交易记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    transaction_time DATETIME NOT NULL,
                    transaction_type TEXT NOT NULL,   -- consumption/income
                    amount DECIMAL(15,2) NOT NULL,
                    currency TEXT DEFAULT 'CNY',
                    balance_after DECIMAL(15,2),      -- 交易后余额
                    counterparty_name TEXT,           -- 商户
                    channel_name TEXT,                -- 微信支付/支付宝
                    raw_data TEXT,                    -- 原始数据
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (account_id) REFERENCES accounts(id)
                )
            ''')
            
            # 索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_trans_account_time 
                ON transactions(account_id, transaction_time)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_trans_time 
                ON transactions(transaction_time)
            ''')
            
            conn.commit()
            print("[✓] 数据库初始化完成")
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    # ========== 账户管理 ==========
    
    def get_or_create_account(
        self,
        account_number: str,
        account_name: str,
        account_type: str,
        institution: Optional[str] = None
    ) -> Optional[str]:
        """获取或创建账户"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 查找现有账户
            cursor.execute(
                'SELECT id FROM accounts WHERE account_number = ? AND is_active = 1',
                (account_number,)
            )
            row = cursor.fetchone()
            if row:
                return row['id']
        
        # 创建新账户
        return self.create_account(
            account_number=account_number,
            account_name=account_name,
            account_type=account_type,
            institution=institution
        )
    
    def create_account(
        self,
        account_number: str,
        account_name: str,
        account_type: str,
        institution: Optional[str] = None,
        initial_balance: Decimal = Decimal('0')
    ) -> Optional[str]:
        """创建新账户"""
        account_id = str(uuid.uuid4())
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO accounts (
                        id, account_number, account_name, account_type,
                        institution, current_balance, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    account_id,
                    account_number,
                    account_name,
                    account_type,
                    institution,
                    str(initial_balance),
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                print(f"[✓] 账户创建成功: {account_name}")
                return account_id
                
            except Exception as e:
                print(f"[✗] 创建账户失败: {e}")
                conn.rollback()
                return None
    
    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """获取账户信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM accounts WHERE id = ?',
                (account_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def list_accounts(self) -> List[Dict[str, Any]]:
        """列出所有账户"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM accounts
                WHERE is_active = 1
                ORDER BY account_type, account_name
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_total_balance(self) -> Decimal:
        """获取总余额"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT SUM(current_balance) as total
                FROM accounts
                WHERE is_active = 1
            ''')
            row = cursor.fetchone()
            return Decimal(str(row['total'])) if row['total'] else Decimal('0')
    
    # ========== 交易管理 ==========
    
    def save_transaction(
        self,
        raw_transaction: RawTransaction,
        account_id: str
    ) -> Tuple[bool, str]:
        """保存交易记录并更新账户余额"""
        transaction_id = str(uuid.uuid4())
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # 检查是否已存在
                cursor.execute(
                    'SELECT id FROM transactions WHERE id = ?',
                    (transaction_id,)
                )
                if cursor.fetchone():
                    return False, "duplicate"
                
                # 获取当前余额
                cursor.execute(
                    'SELECT current_balance FROM accounts WHERE id = ?',
                    (account_id,)
                )
                row = cursor.fetchone()
                balance_before = Decimal(str(row['current_balance'])) if row else Decimal('0')
                
                # 计算新余额
                amount = raw_transaction.amount
                if raw_transaction.transaction_type in ['consumption', 'transfer_out', 'fee']:
                    balance_after = balance_before - amount
                else:
                    balance_after = balance_before + amount
                
                # 准备交易数据
                data = {
                    'id': transaction_id,
                    'account_id': account_id,
                    'transaction_time': raw_transaction.transaction_time.isoformat(),
                    'transaction_type': raw_transaction.transaction_type,
                    'amount': str(raw_transaction.amount),
                    'currency': raw_transaction.currency,
                    'balance_after': str(balance_after),
                    'counterparty_name': raw_transaction.counterparty.name if raw_transaction.counterparty else None,
                    'channel_name': raw_transaction.channel.name if raw_transaction.channel else None,
                    'raw_data': raw_transaction.raw_data,
                }
                
                # 插入交易记录
                columns = ', '.join(data.keys())
                placeholders = ', '.join('?' for _ in data)
                
                cursor.execute(f'''
                    INSERT INTO transactions ({columns})
                    VALUES ({placeholders})
                ''', list(data.values()))
                
                # 更新账户余额
                cursor.execute('''
                    UPDATE accounts 
                    SET current_balance = ?, updated_at = ?
                    WHERE id = ?
                ''', (
                    str(balance_after),
                    datetime.now().isoformat(),
                    account_id
                ))
                
                conn.commit()
                return True, "saved"
                
            except sqlite3.IntegrityError as e:
                conn.rollback()
                return False, f"integrity_error: {e}"
            except Exception as e:
                conn.rollback()
                return False, f"error: {e}"
    
    def get_transactions(
        self,
        account_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """查询交易记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            conditions = []
            params = []
            
            if account_id:
                conditions.append('account_id = ?')
                params.append(account_id)
            
            if start_time:
                conditions.append('transaction_time >= ?')
                params.append(start_time.isoformat())
            
            if end_time:
                conditions.append('transaction_time <= ?')
                params.append(end_time.isoformat())
            
            sql = 'SELECT * FROM transactions'
            if conditions:
                sql += ' WHERE ' + ' AND '.join(conditions)
            sql += ' ORDER BY transaction_time DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
