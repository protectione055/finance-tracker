#!/usr/bin/env python3
"""
数据库迁移脚本 V1 -> V2
将旧数据库数据迁移到新的三表结构
"""

import sys
sys.path.insert(0, 'src')

import sqlite3
from decimal import Decimal
from datetime import datetime

def migrate():
    """执行迁移"""
    print("=" * 60)
    print("数据库迁移 V1 -> V2")
    print("=" * 60)
    print()
    
    old_db = "./data/finance.db"
    new_db = "./data/finance_v2.db"
    
    # 连接旧数据库
    print(f"[→] 连接旧数据库: {old_db}")
    old_conn = sqlite3.connect(old_db)
    old_conn.row_factory = sqlite3.Row
    old_cursor = old_conn.cursor()
    
    # 初始化新数据库
    print(f"[→] 初始化新数据库: {new_db}")
    from storage.database_v2 import DatabaseV2
    db = DatabaseV2(new_db)
    
    # 创建账户管理器
    from storage.database_v2 import AccountManager, TransactionManager
    account_mgr = AccountManager(db)
    trans_mgr = TransactionManager(db)
    
    # 统计旧数据
    old_cursor.execute('SELECT COUNT(*) as count FROM transactions')
    count = old_cursor.fetchone()['count']
    print(f"  发现 {count} 条交易记录")
    
    # 迁移数据
    print()
    print("[→] 开始迁移数据...")
    
    old_cursor.execute('''
        SELECT * FROM transactions
        ORDER BY transaction_time
    ''')
    
    migrated_count = 0
    skipped_count = 0
    
    for row in old_cursor:
        try:
            # 获取或创建账户
            account_number = row['account_id']
            account_name = row['account_name'] or f"账户({account_number})"
            account_type = row['account_type'] or 'debit'
            
            account_id = account_mgr.get_or_create_account(
                account_number=account_number,
                account_name=account_name,
                account_type=account_type,
                institution=row['source_type']
            )
            
            if not account_id:
                print(f"  [✗] 无法创建账户: {account_number}")
                skipped_count += 1
                continue
            
            # 重建 RawTransaction
            from models.transaction import (
                RawTransaction, Counterparty, PaymentChannel
            )
            from decimal import Decimal
            
            transaction = RawTransaction(
                raw_id=row['raw_id'] or '',
                source_type=row['source_type'],
                source_account=row['source_account'] or '',
                transaction_time=datetime.fromisoformat(row['transaction_time']),
                account_id=account_number,
                transaction_type=row['transaction_type'],
                amount=Decimal(str(row['amount'])),
                currency=row['currency'],
                balance=Decimal(str(row['balance'])) if row['balance'] else None,
                counterparty=Counterparty(
                    name=row['counterparty_name'] or '未知',
                    type=row['counterparty_type'],
                    category=row['counterparty_category']
                ) if row['counterparty_name'] else None,
                channel=PaymentChannel(
                    name=row['channel_name'],
                    provider=row['channel_provider'],
                    method=row['channel_method']
                ) if row['channel_name'] else None,
                raw_data=row['raw_data'],
                notes=row['notes']
            )
            
            # 保存交易
            success, message = trans_mgr.save_transaction(transaction, account_id)
            
            if success:
                migrated_count += 1
                print(f"  [{migrated_count}] 已迁移: {transaction.transaction_time} - {transaction.amount}元")
            elif message == "duplicate":
                # 重复记录，不算失败
                migrated_count += 1
            else:
                print(f"  [✗] 迁移失败: {message}")
                skipped_count += 1
        
        except Exception as e:
            print(f"  [✗] 处理记录时出错: {e}")
            skipped_count += 1
            continue
    
    # 关闭连接
    old_conn.close()
    
    # 输出统计
    print()
    print("=" * 60)
    print("迁移完成")
    print("=" * 60)
    print(f"  成功迁移: {migrated_count} 条")
    print(f"  跳过/失败: {skipped_count} 条")
    print()
    print(f"新数据库: {new_db}")
    print("=" * 60)


if __name__ == "__main__":
    migrate()
