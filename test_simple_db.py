#!/usr/bin/env python3
"""
测试精简版两表数据库
"""

import sys
sys.path.insert(0, 'src')

from datetime import datetime
from decimal import Decimal
from storage.database_simple import SimpleDatabase

def main():
    print("=" * 60)
    print("精简版两表数据库测试")
    print("表结构: accounts + transactions")
    print("=" * 60)
    print()
    
    # 创建数据库
    db = SimpleDatabase("./data/finance_simple.db")
    
    # 创建或获取账户
    print("[→] 创建/获取账户...")
    account_id = db.get_or_create_account(
        account_number="8551",
        account_name="招商银行借记卡",
        account_type="debit",
        institution="招商银行"
    )
    
    if not account_id:
        print("[✗] 账户创建失败")
        return
    
    print(f"[✓] 账户ID: {account_id}")
    print()
    
    # 模拟保存交易
    print("[→] 保存交易记录...")
    
    from models.transaction import (
        RawTransaction, Counterparty, PaymentChannel
    )
    
    # 交易1
    trans1 = RawTransaction(
        raw_id="test_001",
        source_type="cmb_email",
        source_account="95555@message.cmbchina.com",
        transaction_time=datetime(2026, 2, 21, 17, 26, 0),
        account_id="8551",
        transaction_type="consumption",
        amount=Decimal("5.50"),
        currency="CNY",
        balance=Decimal("100641.12"),
        counterparty=Counterparty(
            name="广东赛壹便利店有限公司",
            type="merchant"
        ),
        channel=PaymentChannel(
            name="微信支付",
            provider="财付通"
        )
    )
    
    success, msg = db.save_transaction(trans1, account_id)
    if success:
        print(f"  [✓] 交易1已保存: 5.50元")
    else:
        print(f"  [✗] 交易1保存失败: {msg}")
    
    # 交易2
    trans2 = RawTransaction(
        raw_id="test_002",
        source_type="cmb_email",
        source_account="95555@message.cmbchina.com",
        transaction_time=datetime(2026, 2, 21, 19, 25, 0),
        account_id="8551",
        transaction_type="consumption",
        amount=Decimal("3.00"),
        currency="CNY",
        balance=Decimal("100638.62"),
        counterparty=Counterparty(
            name="山月荟装扮",
            type="merchant"
        ),
        channel=PaymentChannel(
            name="微信支付",
            provider="财付通"
        )
    )
    
    success, msg = db.save_transaction(trans2, account_id)
    if success:
        print(f"  [✓] 交易2已保存: 3.00元")
    else:
        print(f"  [✗] 交易2保存失败: {msg}")
    
    print()
    
    # 查询当前状态
    print("[→] 查询当前状态...")
    print()
    
    # 查询账户余额
    balance = db.get_account_balance(account_id)
    if balance is not None:
        print(f"  💰 账户当前余额: {balance} 元")
    
    # 查询总余额
    total = db.get_total_balance()
    print(f"  💵 总积蓄: {total} 元")
    print()
    
    # 查询交易记录
    transactions = db.get_transactions(limit=10)
    print(f"  📋 最近 {len(transactions)} 条交易记录:")
    for i, t in enumerate(transactions, 1):
        print(f"    {i}. {t['transaction_time']} | {t['transaction_type']} | {t['amount']}元 | {t['counterparty_name'] or '未知'}")
    
    print()
    print("=" * 60)
    print("[✓] 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
