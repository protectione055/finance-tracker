#!/usr/bin/env python3
"""
保存交易记录到数据库
"""

import sys
sys.path.insert(0, 'src')

from datetime import datetime
from decimal import Decimal
from storage.db_minimal import MinimalDB
from models.transaction import RawTransaction, Counterparty, PaymentChannel

def main():
    print("=" * 60)
    print("保存交易记录")
    print("=" * 60)
    print()
    
    # 连接数据库
    db = MinimalDB("./data/finance_minimal.db")
    
    # 获取账户ID
    account_id = db.get_or_create_account(
        account_number="8551",
        account_name="招商银行借记卡",
        account_type="debit",
        institution="招商银行"
    )
    
    if not account_id:
        print("[✗] 无法获取账户")
        return
    
    # 交易1: 17:26 消费 5.50元
    print("[→] 保存交易1...")
    trans1 = RawTransaction(
        raw_id="cmb_20260221_172600",
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
        print("  [✓] 交易1已保存: -5.50元")
    else:
        print(f"  [✗] 交易1失败: {msg}")
    
    # 交易2: 19:25 消费 3.00元
    print("[→] 保存交易2...")
    trans2 = RawTransaction(
        raw_id="cmb_20260221_192500",
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
        print("  [✓] 交易2已保存: -3.00元")
    else:
        print(f"  [✗] 交易2失败: {msg}")
    
    print()
    
    # 显示结果
    print("=" * 60)
    print("当前状态")
    print("=" * 60)
    print()
    
    # 账户信息
    accounts = db.list_accounts()
    if accounts:
        acc = accounts[0]
        print("📊 账户信息:")
        print(f"  名称: {acc['account_name']}")
        print(f"  账号: {acc['account_number']}")
        print(f"  当前余额: {acc['current_balance']} 元")
        print()
    
    # 总余额
    total = db.get_total_balance()
    print(f"💰 总积蓄: {total} 元")
    print()
    
    # 交易记录
    transactions = db.get_transactions(limit=10)
    print(f"📋 交易记录 ({len(transactions)} 条):")
    for i, t in enumerate(transactions, 1):
        print(f"  {i}. {t['transaction_time']} | {t['counterparty_name']} | -{t['amount']}元 | 余额:{t['balance_after']}元")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
