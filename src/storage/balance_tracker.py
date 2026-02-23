"""
净资产追踪器
基于 accounts.current_balance 计算净资产
"""

import sqlite3
import json
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pathlib import Path
from contextlib import contextmanager

from src.storage.schema import ACCOUNTS_TABLE_SQL


class BalanceTracker:
    """
    净资产追踪器
    
    功能：
    1. 基于 accounts.current_balance 计算净资产
    2. 记录净资产历史
    """
    
    def __init__(self, db_path: str = "./data/finance.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()
    
    def _init_tables(self):
        """初始化余额追踪表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 总积蓄/净资产历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS net_worth_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_assets DECIMAL(15, 2) NOT NULL,      -- 总资产
                    total_liabilities DECIMAL(15, 2) DEFAULT 0, -- 总负债
                    net_worth DECIMAL(15, 2) NOT NULL,       -- 净资产
                    currency TEXT DEFAULT 'CNY',
                    calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    account_count INTEGER,                      -- 统计的账户数量
                    breakdown TEXT,                           -- 各账户明细(JSON)
                    notes TEXT
                )
            ''')
            
            # 账户配置表（用于管理账户信息）
            cursor.execute(ACCOUNTS_TABLE_SQL)
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_net_worth_date 
                ON net_worth_history(calculated_at)
            ''')
            
            conn.commit()
            print("[✓] 余额追踪表初始化完成")
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def calculate_net_worth(
        self,
        calculated_at: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        计算并记录净资产
        
        Args:
            calculated_at: 计算时间
            notes: 备注
        
        Returns:
            净资产信息字典，失败返回 None
        """
        if calculated_at is None:
            calculated_at = datetime.now()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # 获取所有账户的当前余额
                cursor.execute('''
                    SELECT 
                        account_id,
                        account_name,
                        account_type,
                        current_balance AS balance,
                        updated_at AS recorded_at
                    FROM accounts
                    WHERE current_balance IS NOT NULL
                    ORDER BY account_id
                ''')
                
                rows = cursor.fetchall()
                
                # 计算净资产
                total_assets = Decimal('0')
                total_liabilities = Decimal('0')
                account_breakdown = []
                
                for row in rows:
                    balance = Decimal(str(row['balance']))
                    account_type = row['account_type'] or 'unknown'
                    
                    account_info = {
                        'account_id': row['account_id'],
                        'account_name': row['account_name'],
                        'account_type': account_type,
                        'balance': str(balance),
                        'recorded_at': row['recorded_at']
                    }
                    account_breakdown.append(account_info)
                    
                    # 分类统计
                    if account_type in ['credit', 'loan']:
                        # 信用卡、贷款算作负债
                        total_liabilities += balance
                    else:
                        # 其他算作资产
                        total_assets += balance
                
                net_worth = total_assets - total_liabilities
                
                # 保存到数据库
                cursor.execute('''
                    INSERT INTO net_worth_history
                    (total_assets, total_liabilities, net_worth, calculated_at,
                     account_count, breakdown, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(total_assets),
                    str(total_liabilities),
                    str(net_worth),
                    calculated_at.isoformat(),
                    len(account_breakdown),
                    json.dumps(account_breakdown, ensure_ascii=False),
                    notes
                ))
                
                conn.commit()
                
                # 返回结果
                return {
                    'calculated_at': calculated_at.isoformat(),
                    'total_assets': str(total_assets),
                    'total_liabilities': str(total_liabilities),
                    'net_worth': str(net_worth),
                    'account_count': len(account_breakdown),
                    'accounts': account_breakdown
                }
                
            except Exception as e:
                print(f"[✗] 计算净资产失败: {e}")
                import traceback
                traceback.print_exc()
                conn.rollback()
                return None
    
    def get_net_worth_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取净资产历史
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            limit: 限制条数
        
        Returns:
            净资产历史记录列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if start_time:
                conditions.append('calculated_at >= ?')
                params.append(start_time.isoformat())
            
            if end_time:
                conditions.append('calculated_at <= ?')
                params.append(end_time.isoformat())
            
            # 构建 SQL
            sql = 'SELECT * FROM net_worth_history'
            if conditions:
                sql += ' WHERE ' + ' AND '.join(conditions)
            sql += ' ORDER BY calculated_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # 解析 breakdown JSON
            result = []
            for row in rows:
                data = dict(row)
                if data.get('breakdown'):
                    import json
                    try:
                        data['breakdown'] = json.loads(data['breakdown'])
                    except:
                        pass
                result.append(data)
            
            return result


if __name__ == "__main__":
    tracker = BalanceTracker("./data/finance.db")
    net_worth = tracker.calculate_net_worth(notes="manual run")
    print(net_worth)
