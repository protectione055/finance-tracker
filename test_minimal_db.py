#!/usr/bin/env python3
"""
测试极简两表数据库
"""

import sys
sys.path.insert(0, 'src')

from datetime import datetime
from decimal import Decimal
from storage.db_minimal import MinimalDB
from models.transaction import RawTransaction, Counterparty, PaymentChannel

def main():
    print("=" * 60)
    print("极简两表数据库测试")
    print("表: accounts + transactions")
    print("=" * 60)
    print()
    
    # 创建数据库
    db = MinimalDB("./data/finance_minimal.db")
    
    # 获取或创建账户
    print("[→] 获取或创建账户...")
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
    
    # 保存交易1
    print("[→] 保存交易记录...")
    
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
        print(f"  [✓] 交易1已保存: -5.50元")
    else:
        print(f"  [✗] 交易1失败: {msg}")
    
    # 保存交易2
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
        print(f"  [✓] 交易2已保存: -3.00元")
    else:
        print(f"  [✗] 交易2失败: {msg}")
    
    print()
    
    # 查询结果
    print("=" * 60)
    print("查询结果")
    print("=" * 60)
    print()
    
    # 账户余额
    balance = db.get_account_balance(account_id)
    if balance is not None:
        print(f"💰 账户当前余额: {balance} 元")
    
    # 总余额
    total = db.get_total_balance()
    print(f"💵 总积蓄: {total} 元")
    print()
    
    # 交易记录
    transactions = db.get_transactions(limit=10)
    print(f"📋 最近 {len(transactions)} 条交易记录:")
    for i, t in enumerate(transactions, 1):
        print(f"  {i}. {t['transaction_time']} | {t['transaction_type']} | -{t['amount']}元 | {t['counterparty_name'] or '未知'}")
    
    print()
    print("=" * 60)
    print("[✓] 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
