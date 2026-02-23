from decimal import Decimal

from src.parsers.cmb_email_parser import CMBEmailParser
from src.models.transaction import TransactionType


def test_cmb_email_quick_pay_parse():
    parser = CMBEmailParser()
    body = "您账户8551于02月21日19:25在财付通-微信支付-山月荟装扮快捷支付3.00元，余额100638.62"

    tx = parser.parse(body, email_subject="招商银行动账通知", email_from="notify@cmbchina.com")

    assert tx is not None
    assert tx.account_id == "8551"
    assert tx.transaction_type == TransactionType.CONSUMPTION
    assert tx.amount == Decimal("3.00")
    assert tx.counterparty is not None
    assert tx.counterparty.name == "山月荟装扮"
    assert tx.channel is not None
    assert tx.channel.name == "微信支付"


def test_cmb_email_income_receive_parse():
    parser = CMBEmailParser()
    body = "您账户8551于02月22日14:12收款10.00元，余额100719.62，备注：财付通-张子鸣-微信零钱提现"

    tx = parser.parse(body, email_subject="一卡通账户变动通知", email_from="95555@message.cmbchina.com")

    assert tx is not None
    assert tx.account_id == "8551"
    assert tx.transaction_type == TransactionType.INCOME
    assert tx.amount == Decimal("10.00")
