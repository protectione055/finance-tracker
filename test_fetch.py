#!/usr/bin/env python3
"""
测试从 QQ 邮箱拉取招行动账邮件
"""

import sys
sys.path.insert(0, 'src')

from adapters.qqmail_adapter import QQMailIMAPAdapter
from storage.database import TransactionRepository

def main():
    print("=" * 60)
    print("测试从 QQ 邮箱拉取招行动账邮件")
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
    
    # 创建适配器
    adapter = QQMailIMAPAdapter()
    
    try:
        # 初始化
        print(f"[→] 正在初始化...")
        success = adapter.initialize(config)
        if not success:
            print("[✗] 初始化失败")
            return
        print("[✓] 初始化成功")
        print()
        
        # 拉取邮件
        print("[→] 正在拉取最近7天的邮件...")
        print()
        
        from datetime import datetime, timedelta
        
        count = 0
        for transaction in adapter.fetch_transactions(
            start_time=datetime.now() - timedelta(days=7)
        ):
            count += 1
            print(f"  [{count}] {transaction.transaction_time}")
            print(f"       账户: {transaction.account_id}")
            print(f"       类型: {transaction.transaction_type}")
            print(f"       金额: {transaction.amount} 元")
            if transaction.counterparty:
                print(f"       商户: {transaction.counterparty.name}")
            if transaction.channel:
                print(f"       渠道: {transaction.channel.name}")
            print()
        
        if count == 0:
            print("  (最近7天内没有找到招行动账邮件)")
        else:
            print(f"[✓] 共找到 {count} 条交易记录")
        
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
