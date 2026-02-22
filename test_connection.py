#!/usr/bin/env python3
"""
测试 QQ 邮箱连接
验证系统可以正常连接到 QQ 邮箱并拉取邮件
"""

import sys
sys.path.insert(0, 'src')

from adapters.qqmail_adapter import QQMailIMAPAdapter
from storage.database import TransactionRepository

def test_connection():
    """测试连接"""
    print("=" * 60)
    print("测试 QQ 邮箱 IMAP 连接")
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
        print(f"[→] 正在初始化适配器...")
        print(f"    邮箱: {config['username']}")
        
        success = adapter.initialize(config)
        if not success:
            print("[✗] 初始化失败")
            return False
        
        print("[✓] 适配器初始化成功")
        print()
        
        # 健康检查
        print("[→] 执行健康检查...")
        health = adapter.health_check()
        
        print(f"    状态: {health['status']}")
        print(f"    消息: {health['message']}")
        
        if health['status'] == 'healthy':
            print("[✓] 健康检查通过")
        else:
            print("[✗] 健康检查失败")
            return False
        
        print()
        
        # 测试拉取邮件
        print("[→] 测试拉取交易记录...")
        print("    拉取最近1天的邮件...")
        
        count = 0
        for transaction in adapter.fetch_transactions(
            start_time=__import__('datetime').datetime.now() - __import__('datetime').timedelta(days=1)
        ):
            count += 1
            print(f"\n    [交易 {count}]")
            print(f"    时间: {transaction.transaction_time}")
            print(f"    账户: {transaction.account_id}")
            print(f"    类型: {transaction.transaction_type}")
            print(f"    金额: {transaction.amount} 元")
            if transaction.counterparty:
                print(f"    商户: {transaction.counterparty.name}")
            if transaction.channel:
                print(f"    渠道: {transaction.channel.name}")
        
        if count == 0:
            print("    (最近1天内没有新的交易邮件)")
        else:
            print(f"\n[✓] 成功拉取 {count} 条交易记录")
        
        print()
        
        # 关闭连接
        adapter.close()
        print("[✓] 连接已关闭")
        
        return True
        
    except Exception as e:
        print(f"\n[✗] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n")
    print("=" * 60)
    print("财务追踪系统 - 连接测试")
    print("=" * 60)
    print("\n")
    
    success = test_connection()
    
    print("\n")
    print("=" * 60)
    if success:
        print("✅ 所有测试通过！系统配置正确。")
    else:
        print("❌ 测试失败，请检查配置和网络连接。")
    print("=" * 60)
    print("\n")


if __name__ == "__main__":
    main()
