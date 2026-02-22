#!/usr/bin/env python3
"""
拉取最新交易信息并更新数据库
使用 QQ 邮箱 IMAP
"""

import sys
import os
import sqlite3
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.adapters.qqmail_adapter import QQMailIMAPAdapter

# 配置
EMAIL = 'protectione055@foxmail.com'
AUTH_CODE = 'ztdxpqtfkzypbdcc'
DB_PATH = 'data/finance.db'

def init_adapter():
    """初始化适配器"""
    adapter = QQMailIMAPAdapter()
    config = {
        'username': EMAIL,
        'auth_code': AUTH_CODE,
        'imap_server': 'imap.qq.com',
        'imap_port': 993
    }
    success = adapter.initialize(config)
    return adapter if success else None

def get_last_transaction_time():
    """获取数据库中最新交易的时间"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(transaction_time) FROM transactions;')
    result = cursor.fetchone()[0]
    conn.close()
    
    if result:
        return datetime.fromisoformat(result.replace('Z', '+00:00'))
    # 如果没有数据，返回 7 天前
    return datetime.now() - timedelta(days=7)

def save_transaction_to_db(transaction):
    """保存单条交易到数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO transactions (
                transaction_id, source_type, source_account, raw_id,
                transaction_time, record_time, timezone,
                account_id, account_type, account_name,
                transaction_type, amount, currency, balance,
                counterparty_name, counterparty_type, counterparty_category,
                channel_name, channel_provider, channel_method,
                location_city, location_country,
                metadata, raw_data, tags, notes,
                status, verification_status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(transaction_id) DO NOTHING
        ''', (
            transaction.transaction_id,
            transaction.source_type,
            transaction.source_account,
            transaction.raw_id,
            transaction.transaction_time.isoformat() if transaction.transaction_time else None,
            transaction.record_time.isoformat() if transaction.record_time else None,
            transaction.timezone,
            transaction.account_id,
            transaction.account_type,
            transaction.account_name,
            transaction.transaction_type,
            transaction.amount,
            transaction.currency,
            transaction.balance,
            transaction.counterparty_name,
            transaction.counterparty_type,
            transaction.counterparty_category,
            transaction.channel_name,
            transaction.channel_provider,
            transaction.channel_method,
            transaction.location_city,
            transaction.location_country,
            transaction.metadata,
            transaction.raw_data,
            transaction.tags,
            transaction.notes,
            transaction.status,
            transaction.verification_status,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        return cursor.rowcount > 0  # True if inserted, False if conflict
        
    except Exception as e:
        print(f"保存交易失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    print("=" * 70)
    print("拉取最新交易信息并更新数据库")
    print("=" * 70)
    
    # 1. 初始化适配器
    print("\n[1/5] 初始化 QQ 邮箱适配器...")
    adapter = init_adapter()
    if not adapter:
        print("      ✗ 初始化失败")
        return 1
    print("      ✓ 初始化成功")
    
    # 2. 获取上次拉取时间
    print("\n[2/5] 检查数据库中的最新交易...")
    last_time = get_last_transaction_time()
    print(f"      上次拉取时间: {last_time}")
    
    # 3. 拉取交易
    print("\n[3/5] 从 QQ 邮箱拉取交易...")
    start_time = last_time
    end_time = datetime.now()
    
    transactions = list(adapter.fetch_transactions(
        start_time=start_time,
        end_time=end_time
    ))
    
    print(f"      ✓ 找到 {len(transactions)} 条新交易")
    
    # 4. 保存到数据库
    print("\n[4/5] 保存到数据库...")
    saved_count = 0
    duplicate_count = 0
    
    for txn in transactions:
        # 生成交易ID
        txn_id = txn.generate_transaction_id()
        
        # 打印交易信息
        print(f"\n      交易: {txn_id}")
        print(f"        时间: {txn.transaction_time}")
        print(f"        金额: {txn.amount} {txn.currency}")
        if txn.counterparty:
            print(f"        商户: {txn.counterparty.name}")
        
        # 保存
        if save_transaction_to_db(txn):
            saved_count += 1
            print("        ✓ 已保存")
        else:
            duplicate_count += 1
            print("        ⚠ 重复记录，跳过")
    
    print(f"\n      统计: 新增 {saved_count} 条, 重复 {duplicate_count} 条")
    
    # 5. 更新完成
    print("\n[5/5] 更新完成")
    
    # 关闭适配器
    adapter.close()
    
    print("\n" + "=" * 70)
    print(f"✓ 拉取完成: 共 {len(transactions)} 条交易，新增 {saved_count} 条")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    exit(main())
