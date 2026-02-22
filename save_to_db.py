#!/usr/bin/env python3
"""
将交易记录保存到数据库
"""

import sys
sys.path.insert(0, 'src')

from datetime import datetime, timedelta
from adapters.qqmail_adapter import QQMailIMAPAdapter
from storage.database import TransactionRepository

def main():
    print("=" * 60)
    print("将交易记录保存到数据库")
    print("=" * 60)
    print()
    
    # 配置
    config = {
        'username': 'protectione055@foxmail.com',
        'auth_code': 'ztdxpqtfkzypbdcc',
        'imap_server': 'imap.qq.com',
        'imap_port': 993,
        'use_ssl': True
    }
    
    # 创建适配器和仓库
    adapter = QQMailIMAPAdapter()
    repo = TransactionRepository("./data/finance.db")
    
    try:
        # 初始化适配器
        print("[→] 初始化适配器...")
        adapter.initialize(config)
        print("[✓] 适配器初始化成功")
        print()
        
        # 拉取并保存交易
        print("[→] 拉取最近7天的交易记录...")
        print()
        
        saved_count = 0
        duplicate_count = 0
        error_count = 0
        
        for transaction in adapter.fetch_transactions(
            start_time=datetime.now() - timedelta(days=7)
        ):
            success, message = repo.save_transaction(transaction)
            
            if success:
                saved_count += 1
                print(f"  [✓] 已保存: {transaction.transaction_time} - {transaction.amount}元 - {transaction.counterparty.name if transaction.counterparty else '未知'}")
            elif message == "duplicate":
                duplicate_count += 1
                print(f"  [⚠] 重复记录，跳过: {transaction.transaction_time}")
            else:
                error_count += 1
                print(f"  [✗] 保存失败: {message}")
        
        print()
        print("=" * 60)
        print("保存统计")
        print("=" * 60)
        print(f"  成功保存: {saved_count} 条")
        print(f"  重复跳过: {duplicate_count} 条")
        print(f"  保存失败: {error_count} 条")
        print()
        
        # 显示数据库中的记录
        print("=" * 60)
        print("数据库中的最新记录")
        print("=" * 60)
        
        transactions = repo.get_transactions(limit=10)
        for i, t in enumerate(transactions, 1):
            print(f"  {i}. {t['transaction_time']} | {t['account_id']} | {t['transaction_type']} | {t['amount']}元 | {t['counterparty_name'] or '未知'}")
        
        print()
        
        # 关闭连接
        adapter.close()
        print("[✓] 连接已关闭")
        
    except Exception as e:
        print(f"\n[✗] 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
