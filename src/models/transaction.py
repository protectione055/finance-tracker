"""
交易数据模型 - 统一的数据结构
所有数据源最终都转换为此格式
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, List, Any
import hashlib
import json


@dataclass(frozen=True)
class Counterparty:
    """交易对手方信息"""
    name: str                              # 商户名/对方账户
    type: Optional[str] = None            # 类型: merchant/person/platform
    category: Optional[str] = None       # 分类: 餐饮/购物/交通等
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass(frozen=True)
class PaymentChannel:
    """支付渠道信息"""
    name: Optional[str] = None            # 渠道名: 微信支付/支付宝
    provider: Optional[str] = None        # 提供商: 财付通/网联
    method: Optional[str] = None          # 支付方式: 快捷支付/扫码/刷卡
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass(frozen=True)
class Location:
    """地理位置信息"""
    city: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class RawTransaction:
    """
    标准化原始交易数据
    
    这是所有数据源统一的输出格式，字段设计考虑：
    1. 完整性 - 涵盖交易的所有关键信息
    2. 可扩展性 - 支持未来新增字段
    3. 可追溯性 - 保留原始数据和元数据
    
    注意：所有没有默认值的字段必须放在有默认值的字段之前
    """
    
    # ==================== 来源标识（无默认值）====================
    raw_id: str                           # 数据源提供的原始ID
    source_type: str                     # 数据源类型: qqmail/cmb_email/alipay_api
    source_account: str                 # 源账户标识 (如邮箱地址/账号)
    
    # ==================== 时间信息（无默认值）====================
    transaction_time: datetime          # 交易发生时间 (必须)
    
    # ==================== 账户信息（无默认值）====================
    account_id: str                      # 账户标识 (卡号尾号/账号)
    
    # ==================== 交易详情（无默认值）====================
    transaction_type: str                # 类型: consumption/income/transfer/refund/fee
    amount: Decimal                     # 金额 (正数，单位:元)
    
    # ==================== 时间信息（有默认值）====================
    timezone: str = "Asia/Shanghai"     # 时区信息
    
    # ==================== 账户信息（有默认值）====================
    account_type: Optional[str] = None  # 账户类型: debit/credit/wallet
    account_name: Optional[str] = None  # 账户名称 (如"招行借记卡")
    
    # ==================== 交易详情（有默认值）====================
    currency: str = "CNY"               # 币种 (CNY/USD/EUR等)
    balance: Optional[Decimal] = None  # 余额 (可选)
    
    # ==================== 复合对象（有默认值）====================
    counterparty: Optional[Counterparty] = None    # 对手方信息
    channel: Optional[PaymentChannel] = None       # 支付渠道
    location: Optional[Location] = None            # 地理位置
    
    # ==================== 元数据（有默认值）====================
    metadata: Dict[str, Any] = field(default_factory=dict)  # 原始元数据
    raw_data: str = ""            # 原始数据快照
    tags: List[str] = field(default_factory=list)              # 标签
    notes: str = ""                # 备注
    
    # ==================== 状态追踪（有默认值）====================
    status: str = "confirmed"            # pending/confirmed/cancelled
    verification_status: str = "unverified"  # 核实状态
    
    def __post_init__(self):
        """初始化后处理"""
        # 确保金额是 Decimal 类型
        if isinstance(self.amount, (int, float, str)):
            object.__setattr__(self, 'amount', Decimal(str(self.amount)))
        if self.balance and isinstance(self.balance, (int, float, str)):
            object.__setattr__(self, 'balance', Decimal(str(self.balance)))
    
    def generate_transaction_id(self) -> str:
        """
        生成唯一交易ID
        基于关键字段的 SHA256 哈希
        """
        key_data = (
            f"{self.source_type}:"
            f"{self.source_account}:"
            f"{self.transaction_time.isoformat()}:"
            f"{self.account_id}:"
            f"{self.amount}:"
            f"{self.counterparty.name if self.counterparty else 'unknown'}"
        )
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        data = asdict(self)
        
        # 处理 Decimal 类型
        if isinstance(self.amount, Decimal):
            data['amount'] = str(self.amount)
        if self.balance and isinstance(self.balance, Decimal):
            data['balance'] = str(self.balance)
        
        # 处理 datetime
        if isinstance(self.transaction_time, datetime):
            data['transaction_time'] = self.transaction_time.isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RawTransaction':
        """从字典创建实例"""
        # 解析时间
        if isinstance(data.get('transaction_time'), str):
            data['transaction_time'] = datetime.fromisoformat(data['transaction_time'])
        
        # 解析金额
        if 'amount' in data:
            data['amount'] = Decimal(str(data['amount']))
        if 'balance' in data and data['balance']:
            data['balance'] = Decimal(str(data['balance']))
        
        # 解析复合对象
        if 'counterparty' in data and data['counterparty']:
            data['counterparty'] = Counterparty(**data['counterparty'])
        if 'channel' in data and data['channel']:
            data['channel'] = PaymentChannel(**data['channel'])
        if 'location' in data and data['location']:
            data['location'] = Location(**data['location'])
        
        return cls(**data)


# ==================== 常量定义 ====================

class TransactionType:
    """交易类型常量"""
    CONSUMPTION = "consumption"      # 消费
    INCOME = "income"                # 收入
    TRANSFER_OUT = "transfer_out"    # 转出
    TRANSFER_IN = "transfer_in"      # 转入
    REFUND = "refund"                # 退款
    FEE = "fee"                      # 手续费
    INTEREST = "interest"            # 利息
    DIVIDEND = "dividend"            # 分红
    OTHER = "other"                  # 其他


class AccountType:
    """账户类型常量"""
    DEBIT = "debit"                    # 借记卡
    CREDIT = "credit"                  # 信用卡
    WALLET = "wallet"                  # 钱包
    ALIPAY = "alipay"                  # 支付宝
    WECHAT = "wechat"                  # 微信支付
    PAYPAL = "paypal"                  # PayPal
    INVESTMENT = "investment"          # 投资账户
    LOAN = "loan"                      # 贷款账户
    OTHER = "other"                    # 其他


class CounterpartyType:
    """对手方类型常量"""
    MERCHANT = "merchant"              # 商户
    PERSON = "person"                  # 个人
    PLATFORM = "platform"              # 平台
    BANK = "bank"                      # 银行
    GOVERNMENT = "government"          # 政府
    OTHER = "other"                    # 其他


class TransactionStatus:
    """交易状态常量"""
    PENDING = "pending"                # 待处理
    CONFIRMED = "confirmed"            # 已确认
    CANCELLED = "cancelled"            # 已取消
    DISPUTED = "disputed"              # 争议中
    REFUNDED = "refunded"              # 已退款
