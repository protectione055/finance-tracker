"""
积蓄/余额追踪器
用于记录和追踪各账户的余额变化
"""

import sqlite3
import json
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pathlib import Path
from contextlib import contextmanager


class BalanceTracker:
    """
    余额追踪器
    
    功能：
    1. 记录各账户的余额历史
    2. 追踪总积蓄变化
    3. 生成余额趋势报表
    4. 计算净资产
    """
    
    def __init__(self, db_path: str = "./data/finance.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()
    
    def _init_tables(self):
        """初始化余额追踪表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 账户余额历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS account_balances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    account_name TEXT,
                    account_type TEXT,  -- debit/credit/wallet/investment
                    balance DECIMAL(15, 2) NOT NULL,
                    currency TEXT DEFAULT 'CNY',
                    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    source_transaction_id TEXT,  -- 关联的交易记录ID
                    notes TEXT,
                    
                    -- 索引
                    UNIQUE(account_id, recorded_at)
                )
            ''')
            
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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT UNIQUE NOT NULL,
                    account_name TEXT,
                    account_type TEXT,  -- debit/credit/wallet/investment/loan
                    institution TEXT,   -- 发卡机构：招商银行/支付宝等
                    currency TEXT DEFAULT 'CNY',
                    is_active BOOLEAN DEFAULT 1,
                    is_included_in_net_worth BOOLEAN DEFAULT 1,  -- 是否计入净资产
                    credit_limit DECIMAL(15, 2),  -- 信用额度（信用卡用）
                    opened_at DATE,
                    closed_at DATE,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_balances_account 
                ON account_balances(account_id, recorded_at)
            ''')
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
    
    def record_balance(
        self,
        account_id: str,
        balance: Decimal,
        recorded_at: Optional[datetime] = None,
        account_name: Optional[str] = None,
        account_type: Optional[str] = None,
        source_transaction_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        记录账户余额
        
        Args:
            account_id: 账户标识（如卡号尾号）
            balance: 余额
            recorded_at: 记录时间（默认当前时间）
            account_name: 账户名称
            account_type: 账户类型
            source_transaction_id: 来源交易ID
            notes: 备注
        
        Returns:
            是否成功
        """
        if recorded_at is None:
            recorded_at = datetime.now()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO account_balances
                    (account_id, account_name, account_type, balance, recorded_at,
                     source_transaction_id, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    account_id,
                    account_name,
                    account_type,
                    str(balance),
                    recorded_at.isoformat(),
                    source_transaction_id,
                    notes
                ))
                
                conn.commit()
                return True
                
            except Exception as e:
                print(f"[✗] 记录余额失败: {e}")
                conn.rollback()
                return False
    
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
                # 获取所有账户的最新余额
                cursor.execute('''
                    SELECT 
                        ab.account_id,
                        ab.account_name,
                        ab.account_type,
                        ab.balance,
                        ab.recorded_at
                    FROM account_balances ab
                    INNER JOIN (
                        SELECT account_id, MAX(recorded_at) as max_time
                        FROM account_balances
                        GROUP BY account_id
                    ) latest ON ab.account_id = latest.account_id 
                        AND ab.recorded_at = latest.max_time
                    ORDER BY ab.account_id
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
    
    def get_balance_history(
        self,
        account_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取余额历史
        
        Args:
            account_id: 账户ID（可选）
            start_time: 开始时间
            end_time: 结束时间
            limit: 限制条数
        
        Returns:
            余额历史记录列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if account_id:
                conditions.append('account_id = ?')
                params.append(account_id)
            
            if start_time:
                conditions.append('recorded_at >= ?')
                params.append(start_time.isoformat())
            
            if end_time:
                conditions.append('recorded_at <= ?')
                params.append(end_time.isoformat())
            
            # 构建 SQL
            sql = 'SELECT * FROM account_balances'
            if conditions:
                sql += ' WHERE ' + ' AND '.join(conditions)
            sql += ' ORDER BY recorded_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
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


def demo():
    """演示如何使用余额追踪器"""
    print("=" * 60)
    print("余额追踪器演示")
    print("=" * 60)
    print()
    
    tracker = BalanceTracker("./data/finance.db")
    
    # 示例：记录一些余额
    from decimal import Decimal
    
    print("[→] 记录账户余额...")
    
    # 记录招行账户余额
    tracker.record_balance(
        account_id="8551",
        balance=Decimal("100638.62"),
        account_name="招商银行借记卡",
        account_type="debit",
        notes="初始余额"
    )
    
    print("  [✓] 已记录: 8551 - 100638.62元")
    
    # 计算并记录净资产
    print("\n[→] 计算净资产...")
    
    net_worth = tracker.calculate_net_worth(
        notes="首次计算"
    )
    
    if net_worth:
        print(f"  [✓] 净资产计算完成")
        print(f"      总资产: {net_worth['total_assets']} 元")
        print(f"      总负债: {net_worth['total_liabilities']} 元")
        print(f"      净资产: {net_worth['net_worth']} 元")
        print(f"      账户数: {net_worth['account_count']} 个")
    
    # 查询余额历史
    print("\n[→] 查询余额历史...")
    
    balances = tracker.get_balance_history(
        account_id="8551",
        limit=10
    )
    
    print(f"  [✓] 找到 {len(balances)} 条记录")
    for b in balances:
        print(f"      {b['recorded_at']}: {b['balance']} 元")
    
    print("\n[✓] 演示完成！")


if __name__ == "__main__":
    demo()
