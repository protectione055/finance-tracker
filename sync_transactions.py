#!/usr/bin/env python3
"""
交易同步脚本

从 QQ 邮箱拉取交易邮件，解析并保存到数据库，更新账户信息。

逻辑：
1. 获取账户的 last_sync_time
2. 拉取该时间之后的邮件
3. 解析交易并保存
4. 更新账户余额和 last_sync_time
"""

import sys
import os
import sqlite3
import hashlib
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.adapters.qqmail_adapter import QQMailIMAPAdapter

# 配置
EMAIL = 'protectione055@foxmail.com'
AUTH_CODE = 'ztdxpqtfkzypbdcc'
DB_PATH = 'data/finance.db'


def get_or_create_account():
    """
    获取或创建默认账户
    
    Returns:
        (account_id, last_sync_time) 元组
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 查询现有账户
    cursor.execute("""
        SELECT account_id, last_sync_time 
        FROM accounts 
        WHERE is_active = 1 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    
    if result:
        account_id = result[0]
        last_sync_time = result[1]
        
        # 如果没有上次同步时间，使用7天前
        if not last_sync_time:
            last_sync_time = (datetime.now() - timedelta(days=7)).isoformat()
        
        conn.close()
        return account_id, last_sync_time
    
    # 没有账户，创建默认账户
    print("[INFO] 没有找到活跃账户，创建默认账户...")
    
    import uuid
    account_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO accounts (
            account_id, account_name, account_type, 
            institution, currency, is_active, 
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        account_id,
        '招商银行一卡通',
        'DEBIT',
        '招商银行',
        'CNY',
        1,
        now,
        now
    ))
    
    conn.commit()
    conn.close()
    
    # 返回新账户，同步时间设为7天前
    last_sync_time = (datetime.now() - timedelta(days=7)).isoformat()
    
    return account_id, last_sync_time


def update_account_sync(account_id, new_balance=None):
    """
    更新账户同步时间和余额
    
    Args:
        account_id: 账户ID
        new_balance: 新余额（可选，仅用于记录，不存入accounts表）
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    
    # 只更新同步时间，不更新余额（accounts表没有current_balance字段）
    cursor.execute("""
        UPDATE accounts 
        SET last_sync_time = ?, 
            updated_at = ?
        WHERE account_id = ?
    """, (now, now, account_id))
    
    conn.commit()
    conn.close()


def main():
    """主函数"""
    print("=" * 70)
    print("交易同步脚本")
    print("=" * 70)
    
    # 1. 获取账户和上次同步时间
    print("\n[1/6] 获取账户信息...")
    account_id, last_sync_time = get_or_create_account()
    
    # 将字符串时间转为 datetime
    if isinstance(last_sync_time, str):
        last_sync_dt = datetime.fromisoformat(last_sync_time.replace('Z', '+00:00'))
    else:
        last_sync_dt = last_sync_time
    
    print(f"      账户ID: {account_id}")
    print(f"      上次同步: {last_sync_dt}")
    
    # 2. 初始化适配器
    print("\n[2/6] 初始化 QQ 邮箱适配器...")
    adapter = QQMailIMAPAdapter()
    config = {
        'username': EMAIL,
        'auth_code': AUTH_CODE,
        'imap_server': 'imap.qq.com',
        'imap_port': 993
    }
    
    if not adapter.initialize(config):
        print("      ✗ 初始化失败")
        return 1
    
    print("      ✓ 初始化成功")
    
    # 3. 拉取邮件
    print("\n[3/6] 从 QQ 邮箱拉取交易...")
    end_time = datetime.now()
    
    transactions = list(adapter.fetch_transactions(
        start_time=last_sync_dt,
        end_time=end_time
    ))
    
    print(f"      ✓ 找到 {len(transactions)} 条新交易")
    
    # 4. 保存交易到数据库
    print("\n[4/6] 保存交易到数据库...")
    saved_count = 0
    
    for txn in transactions:
        txn_id = txn.generate_transaction_id()
        
        print(f"\n      交易: {txn_id}")
        print(f"        时间: {txn.transaction_time}")
        print(f"        类型: {txn.transaction_type}")
        print(f"        金额: {txn.amount} {txn.currency}")
        if txn.counterparty:
            print(f"        对手方: {txn.counterparty.name}")
        
        # 保存到数据库
        if save_transaction_to_db(txn):
            saved_count += 1
            print("        ✓ 已保存")
        else:
            print("        ⚠ 重复记录，跳过")
    
    print(f"\n      统计: 新增 {saved_count} 条")
    
    # 5. 更新账户余额和同步时间
    print("\n[5/6] 更新账户信息...")
    
    if saved_count > 0:
        # 获取最新余额（从最近的交易）
        latest_txn = max(transactions, key=lambda x: x.transaction_time)
        new_balance = latest_txn.balance
        
        update_account_sync(account_id, new_balance)
        print(f"      ✓ 账户余额更新为: {new_balance}")
    else:
        # 只更新同步时间
        update_account_sync(account_id)
        print("      ✓ 同步时间已更新")
    
    # 6. 关闭适配器
    print("\n[6/6] 关闭连接...")
    adapter.close()
    print("      ✓ 连接已关闭")
    
    # 总结
    print("\n" + "=" * 70)
    print("同步完成")
    print("=" * 70)
    print(f"  新交易: {saved_count} 条")
    print(f"  总交易: {len(transactions)} 条")
    print("=" * 70)
    
    return 0


def save_transaction_to_db(transaction):
    """保存单条交易到数据库（支持 RawTransaction 对象）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 从 RawTransaction 提取数据
        # 生成 transaction_id
        txn_id = transaction.generate_transaction_id() if hasattr(transaction, 'generate_transaction_id') else str(transaction.raw_id)
        
        # 提取对手方信息
        counterparty_name = None
        counterparty_type = None
        counterparty_category = None
        if transaction.counterparty:
            counterparty_name = transaction.counterparty.name
            counterparty_type = transaction.counterparty.type.value if hasattr(transaction.counterparty.type, 'value') else str(transaction.counterparty.type)
            counterparty_category = transaction.counterparty.category
        
        # 提取渠道信息
        channel_name = None
        channel_provider = None
        channel_method = None
        if transaction.channel:
            channel_name = transaction.channel.name
            channel_provider = transaction.channel.provider
            channel_method = transaction.channel.method
        
        # 处理 metadata（转为 JSON 字符串）
        import json
        metadata_json = json.dumps(transaction.metadata) if transaction.metadata else None
        
        # 处理枚举值
        account_type_val = None
        if transaction.account_type:
            account_type_val = transaction.account_type.value if hasattr(transaction.account_type, 'value') else str(transaction.account_type)
        
        transaction_type_val = None
        if transaction.transaction_type:
            transaction_type_val = transaction.transaction_type.value if hasattr(transaction.transaction_type, 'value') else str(transaction.transaction_type)
        
        status_val = None
        if transaction.status:
            status_val = transaction.status.value if hasattr(transaction.status, 'value') else str(transaction.status)
        
        verification_status_val = None
        if transaction.verification_status:
            verification_status_val = transaction.verification_status.value if hasattr(transaction.verification_status, 'value') else str(transaction.verification_status)
        
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
            txn_id,
            transaction.source_type,
            transaction.source_account,
            transaction.raw_id,
            transaction.transaction_time.isoformat() if transaction.transaction_time else None,
            None,  # record_time not in RawTransaction
            transaction.timezone,
            transaction.account_id,
            account_type_val,
            transaction.account_name,
            transaction_type_val,
            float(transaction.amount) if transaction.amount else 0,
            transaction.currency,
            float(transaction.balance) if transaction.balance else None,
            counterparty_name,
            counterparty_type,
            counterparty_category,
            channel_name,
            channel_provider,
            channel_method,
            transaction.location.city if transaction.location else None,
            transaction.location.country if transaction.location else None,
            metadata_json,
            transaction.raw_data,
            ','.join(transaction.tags) if transaction.tags else None,
            transaction.notes,
            status_val,
            verification_status_val,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        return cursor.rowcount > 0  # True if inserted, False if conflict
        
    except Exception as e:
        print(f"保存交易失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    exit(main())
