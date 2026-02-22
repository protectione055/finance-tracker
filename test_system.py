#!/usr/bin/env python3
"""
系统测试脚本
测试财务追踪系统的核心功能
"""

import sys
sys.path.insert(0, 'src')

from datetime import datetime
from decimal import Decimal
from models.transaction import RawTransaction, Counterparty, PaymentChannel
from parsers.cmb_email_parser import CMBEmailParser
from storage.database import TransactionRepository

def test_parser():
    """测试招行邮件解析器"""
    print("=" * 60)
    print("测试 1: 招行邮件解析器")
    print("=" * 60)
    
    # 测试邮件样本
    test_cases = [
        # 快捷支付（你提供的样本）
        "您账户8551于02月21日19:25在财付通-微信支付-山月荟装扮快捷支付3.00元，余额100638.62",
        # 标准消费
        "您账户*1234于02月21日19:25消费CNY 128.50",
        # 入账
        "您账户*1234于02月21日10:00入账CNY 5000.00",
    ]
    
    parser = CMBEmailParser()
    
    for i, email_body in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {email_body[:40]}...")
        
        transaction = parser.parse(email_body)
        
        if transaction:
            print(f"  ✅ 解析成功")
            print(f"     交易ID: {transaction.generate_transaction_id()}")
            print(f"     时间: {transaction.transaction_time}")
            print(f"     账户: {transaction.account_id}")
            print(f"     类型: {transaction.transaction_type}")
            print(f"     金额: {transaction.amount} 元")
            if transaction.counterparty:
                print(f"     商户: {transaction.counterparty.name}")
            if transaction.channel:
                print(f"     渠道: {transaction.channel.name}")
            if transaction.balance:
                print(f"     余额: {transaction.balance} 元")
        else:
            print(f"  ❌ 解析失败")
    
    print("\n")
    return True


def test_database():
    """测试数据库"""
    print("=" * 60)
    print("测试 2: 数据库存储")
    print("=" * 60)
    
    try:
        # 创建仓库
        repo = TransactionRepository("./data/test.db")
        print("✅ 数据库初始化成功")
        
        # 创建测试交易
        from datetime import datetime
        from decimal import Decimal
        
        transaction = RawTransaction(
            raw_id="test_001",
            source_type="cmb_email",
            source_account="test@cmb.com",
            transaction_time=datetime(2026, 2, 21, 19, 25, 0),
            account_id="8551",
            transaction_type="consumption",
            amount=Decimal("3.00"),
            currency="CNY",
            balance=Decimal("100638.62"),
            counterparty=Counterparty(
                name="山月荟装扮",
                type="merchant",
                category="购物"
            ),
            channel=PaymentChannel(
                name="微信支付",
                provider="财付通",
                method="quick_pay"
            )
        )
        
        # 保存交易
        success, message = repo.save_transaction(transaction)
        if success:
            print(f"✅ 交易保存成功: {message}")
        else:
            print(f"❌ 交易保存失败: {message}")
            return False
        
        # 查询交易
        transactions = repo.get_transactions(limit=10)
        print(f"✅ 查询到 {len(transactions)} 条交易记录")
        
        print("\n")
        return True
        
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n")
    print("=" * 60)
    print("财务追踪系统 - 功能测试")
    print("=" * 60)
    print("\n")
    
    results = []
    
    # 测试 1: 解析器
    results.append(("招行邮件解析器", test_parser()))
    
    # 测试 2: 数据库
    results.append(("数据库存储", test_database()))
    
    # 总结
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    print("\n")
    if all_passed:
        print("🎉 所有测试通过！系统运行正常。")
    else:
        print("⚠️ 部分测试失败，请检查日志。")
    print("\n")


if __name__ == "__main__":
    main()
