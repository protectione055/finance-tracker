"""
共享数据库表结构定义
"""

ACCOUNTS_TABLE_SQL = '''
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id TEXT UNIQUE NOT NULL,
        account_name TEXT,
        account_type TEXT,
        institution TEXT,
        current_balance DECIMAL(15, 2),
        currency TEXT DEFAULT 'CNY',
        is_active BOOLEAN DEFAULT 1,
        is_included_in_net_worth BOOLEAN DEFAULT 1,
        credit_limit DECIMAL(15, 2),
        opened_at DATE,
        closed_at DATE,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_sync_time DATETIME
    )
'''
