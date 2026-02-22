"""
招商银行邮件解析器
支持解析招行动账通知邮件，提取交易信息
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
from src.models.transaction import (
    RawTransaction, Counterparty, PaymentChannel,
    TransactionType, AccountType, CounterpartyType
)


class CMBEmailParser:
    """
    招商银行动账通知邮件解析器
    
    支持多种邮件格式：
    1. 快捷支付：您账户8551于02月21日19:25在财付通-微信支付-山月荟装扮快捷支付3.00元，余额100638.62
    2. 消费：您账户*1234于02月21日19:25消费CNY 128.50
    3. 入账：您账户*1234于02月21日19:25入账CNY 1000.00
    """
    
    def __init__(self):
        self.patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """编译正则表达式模式"""
        return {
            # 快捷支付模式（最详细）
            'quick_pay': re.compile(
                r'您账户\*?(\d{4})于'
                r'(\d{2})月(\d{2})日(\d{2}):(\d{2})'
                r'在(.+?)'
                r'快捷支付'
                r'(\d+\.?\d*)元，'
                r'余额(\d+\.?\d*)',
                re.UNICODE
            ),
            
            # 带商户的消费
            'merchant_consumption': re.compile(
                r'您账户\*?(\d{4})于'
                r'(\d{2})月(\d{2})日(\d{2}):(\d{2})'
                r'在(.+?)'
                r'消费'
                r'([A-Z]{3})?\s*(\d+\.?\d*)元?',
                re.UNICODE
            ),
            
            # 标准消费
            'consumption': re.compile(
                r'您账户\*?(\d{4})于'
                r'(\d{2})月(\d{2})日(\d{2}):(\d{2})'
                r'消费'
                r'([A-Z]{3})?\s*(\d+\.?\d*)元?',
                re.UNICODE
            ),
            
            # 入账（标准格式）
            'income': re.compile(
                r'您账户\*?(\d{4})于'
                r'(\d{2})月(\d{2})日(\d{2}):(\d{2})'
                r'入?账'
                r'([A-Z]{3})?\s*(\d+\.?\d*)元?',
                re.UNICODE
            ),

            # 收款入账（带余额和备注，如微信零钱提现）
            'income_with_balance': re.compile(
                r'您账户\*?(\d{4})于'
                r'(\d{2})月(\d{2})日(\d{2}):(\d{2})'
                r'收款'
                r'(\d+\.?\d*)元，'
                r'余额(\d+\.?\d*)，'
                r'备注：(.+?)(?:\n|$)',
                re.UNICODE
            ),
            
            # 转账支出
            'transfer_out': re.compile(
                r'您向(.+?)转账'
                r'([A-Z]{3})?\s*(\d+\.?\d*)元?',
                re.UNICODE
            ),
            
            # 余额查询
            'balance_query': re.compile(
                r'余额(?:为)?[:：]?\s*(\d+\.?\d*)',
                re.UNICODE
            ),
        }
    
    def parse(self, email_body: str, email_subject: str = "", 
              email_from: str = "", email_date: str = "") -> Optional[RawTransaction]:
        """
        解析邮件内容，提取交易信息
        
        Args:
            email_body: 邮件正文
            email_subject: 邮件主题
            email_from: 发件人
            email_date: 邮件日期
            
        Returns:
            RawTransaction 对象，如果解析失败返回 None
        """
        # 清理文本
        text = self._clean_text(email_body)
        
        # 尝试按优先级匹配各种模式
        patterns_to_try = [
            ('quick_pay', TransactionType.CONSUMPTION),
            ('merchant_consumption', TransactionType.CONSUMPTION),
            ('consumption', TransactionType.CONSUMPTION),
            ('income_with_balance', TransactionType.INCOME),  # 优先匹配带余额的入账格式
            ('income', TransactionType.INCOME),
            ('transfer_out', TransactionType.TRANSFER_OUT),
        ]
        
        for pattern_name, trans_type in patterns_to_try:
            pattern = self.patterns.get(pattern_name)
            if not pattern:
                continue
            
            match = pattern.search(text)
            if match:
                try:
                    return self._build_transaction(
                        match, pattern_name, trans_type,
                        text, email_subject, email_from, email_date
                    )
                except Exception as e:
                    print(f"解析失败 [{pattern_name}]: {e}")
                    continue
        
        # 所有模式都匹配失败
        return None
    
    def _clean_text(self, text: str) -> str:
        """清理文本，移除多余空白和换行"""
        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # 移除多余空白
        lines = [line.strip() for line in text.split('\n')]
        # 合并为单行（某些模式需要）
        return ' '.join(line for line in lines if line)
    
    def _build_transaction(
        self,
        match: re.Match,
        pattern_name: str,
        transaction_type: str,
        full_text: str,
        email_subject: str,
        email_from: str,
        email_date: str
    ) -> RawTransaction:
        """
        根据匹配结果构建 RawTransaction
        """
        groups = match.groups()
        
        # 提取基本信息
        card_tail = self._extract_card_tail(groups, pattern_name)
        trans_time = self._extract_time(groups, pattern_name)
        amount = self._extract_amount(groups, pattern_name)
        balance = self._extract_balance(groups, pattern_name, full_text)
        
        # 提取对手方信息（主要针对快捷支付）
        counterparty = self._extract_counterparty(groups, pattern_name, full_text)
        
        # 提取支付渠道
        channel = self._extract_channel(groups, pattern_name, full_text)
        
        # 构建 RawTransaction
        return RawTransaction(
            raw_id=self._generate_raw_id(match, pattern_name),
            source_type="cmb_email",
            source_account=email_from,
            transaction_time=trans_time,
            account_id=card_tail,
            account_type=AccountType.DEBIT,
            transaction_type=transaction_type,
            amount=amount,
            currency="CNY",
            balance=balance,
            counterparty=counterparty,
            channel=channel,
            metadata={
                'pattern_matched': pattern_name,
                'email_subject': email_subject,
                'email_date': email_date,
            },
            raw_data=full_text[:1000],  # 保留前1000字符用于调试
        )
    
    def _extract_card_tail(self, groups: tuple, pattern_name: str) -> str:
        """提取卡号尾号"""
        if pattern_name in ['quick_pay', 'merchant_consumption', 'consumption', 'income', 'income_with_balance']:
            return groups[0] if groups[0] else "unknown"
        return "unknown"
    
    def _extract_time(self, groups: tuple, pattern_name: str) -> datetime:
        """提取交易时间"""
        try:
            if pattern_name in ['quick_pay', 'merchant_consumption', 'consumption', 'income', 'income_with_balance']:
                month, day, hour, minute = int(groups[1]), int(groups[2]), int(groups[3]), int(groups[4])
                year = datetime.now().year
                # 处理跨年情况
                now = datetime.now()
                if month > now.month:
                    year -= 1
                return datetime(year, month, day, hour, minute)
        except (IndexError, ValueError) as e:
            print(f"时间解析失败: {e}")

        return datetime.now()
    
    def _extract_amount(self, groups: tuple, pattern_name: str) -> Decimal:
        """提取金额"""
        try:
            if pattern_name == 'quick_pay':
                return Decimal(str(groups[6]))
            elif pattern_name in ['merchant_consumption']:
                return Decimal(str(groups[7]))
            elif pattern_name in ['consumption', 'income']:
                return Decimal(str(groups[6] if len(groups) > 6 else groups[5]))
            elif pattern_name == 'income_with_balance':
                # 带余额的入账格式：金额在第6组
                return Decimal(str(groups[5]))
            elif pattern_name == 'transfer_out':
                return Decimal(str(groups[2]))
        except (IndexError, ValueError, Decimal.InvalidOperation) as e:
            print(f"金额解析失败: {e}")
        
        return Decimal("0")
    
    def _extract_balance(self, groups: tuple, pattern_name: str, full_text: str) -> Optional[Decimal]:
        """提取余额"""
        try:
            # 快捷支付格式：余额在第7组
            if pattern_name == 'quick_pay' and len(groups) > 7:
                return Decimal(str(groups[7]))
            
            # 带余额的入账格式：余额在第6组
            if pattern_name == 'income_with_balance' and len(groups) > 6:
                return Decimal(str(groups[6]))
            
            # 尝试从文本中匹配余额
            balance_pattern = re.compile(r'余额[:：]?\s*(\d+\.?\d*)')
            match = balance_pattern.search(full_text)
            if match:
                return Decimal(str(match.group(1)))
        except (IndexError, ValueError, Decimal.InvalidOperation) as e:
            print(f"余额解析失败: {e}")
        
        return None
    
    def _extract_counterparty(self, groups: tuple, pattern_name: str, full_text: str) -> Optional[Counterparty]:
        """提取对手方信息"""
        try:
            if pattern_name == 'quick_pay' and len(groups) > 5:
                merchant_str = groups[5]
                # 解析 "财付通-微信支付-山月荟装扮" 格式
                parts = merchant_str.split('-')
                
                provider = parts[0] if len(parts) > 0 else None
                channel_name = parts[1] if len(parts) > 1 else None
                merchant_name = parts[2] if len(parts) > 2 else merchant_str
                
                return Counterparty(
                    name=merchant_name.strip(),
                    type=CounterpartyType.MERCHANT,
                    category=self._infer_category(merchant_name)
                )
            
            elif pattern_name == 'merchant_consumption' and len(groups) > 5:
                merchant_name = groups[5]
                return Counterparty(
                    name=merchant_name.strip(),
                    type=CounterpartyType.MERCHANT,
                    category=self._infer_category(merchant_name)
                )
            
            elif pattern_name == 'transfer_out':
                recipient = groups[0]
                return Counterparty(
                    name=recipient.strip(),
                    type=CounterpartyType.PERSON,
                    category=None
                )
            
            elif pattern_name == 'income_with_balance' and len(groups) > 7:
                # 从备注字段解析对手方信息
                remark = groups[7]
                # 解析 "财付通-张子鸣-微信零钱提现" 格式
                parts = remark.split('-')
                
                if len(parts) >= 2:
                    provider = parts[0].strip()  # 财付通
                    payer_name = parts[1].strip()  # 张子鸣
                    
                    return Counterparty(
                        name=payer_name,
                        type=CounterpartyType.PERSON,
                        category=None
                    )
                else:
                    # 备注格式不符合预期，使用整个备注作为对手方名
                    return Counterparty(
                        name=remark.strip(),
                        type=CounterpartyType.MERCHANT,
                        category=None
                    )
        
        except Exception as e:
            print(f"对手方解析失败: {e}")
        
        return None
    
    def _extract_channel(self, groups: tuple, pattern_name: str, full_text: str) -> Optional[PaymentChannel]:
        """提取支付渠道信息"""
        try:
            if pattern_name == 'quick_pay' and len(groups) > 5:
                merchant_str = groups[5]
                parts = merchant_str.split('-')
                
                provider = parts[0] if len(parts) > 0 else None  # 财付通
                channel_name = parts[1] if len(parts) > 1 else None  # 微信支付
                
                return PaymentChannel(
                    name=channel_name,
                    provider=provider,
                    method='quick_pay'
                )
            
            # 处理带余额的入账格式（如微信零钱提现）
            if pattern_name == 'income_with_balance' and len(groups) > 7:
                remark = groups[7]
                parts = remark.split('-')
                
                if len(parts) >= 3:
                    provider = parts[0].strip()  # 财付通
                    # parts[1] 是付款人姓名
                    channel_info = parts[2].strip() if len(parts) > 2 else ""
                    
                    # 判断渠道类型
                    if '微信' in channel_info or '零钱' in channel_info:
                        return PaymentChannel(
                            name='微信零钱提现',
                            provider=provider,
                            method='transfer'
                        )
                    else:
                        return PaymentChannel(
                            name=channel_info,
                            provider=provider,
                            method='transfer'
                        )
                elif len(parts) == 1:
                    # 备注只有一项，作为渠道名
                    return PaymentChannel(
                        name=parts[0].strip(),
                        provider=None,
                        method='transfer'
                    )
            
            # 从全文匹配渠道关键词
            if '微信支付' in full_text or '财付通' in full_text:
                return PaymentChannel(name='微信支付', provider='财付通')
            elif '支付宝' in full_text:
                return PaymentChannel(name='支付宝', provider='支付宝')
        
        except Exception as e:
            print(f"支付渠道解析失败: {e}")
        
        return None
    
    def _infer_category(self, merchant_name: str) -> Optional[str]:
        """根据商户名推断消费类别"""
        merchant_lower = merchant_name.lower()
        
        # 关键词映射
        category_keywords = {
            '餐饮': ['餐厅', '饭店', '美食', '咖啡', '奶茶', '火锅', '烧烤', '快餐', '肯德基', '麦当劳', '星巴克'],
            '购物': ['商城', '超市', '便利店', '京东', '淘宝', '天猫', '拼多多', '亚马逊'],
            '交通': ['地铁', '公交', '打车', '滴滴', '出租车', '加油', '停车', '高速'],
            '娱乐': ['电影', '视频', '音乐', '游戏', '网吧', 'ktv', '影院'],
            '生活服务': ['水电', '燃气', '物业', '话费', '宽带', '快递', '洗衣'],
            '医疗健康': ['医院', '药店', '诊所', '体检'],
            '教育': ['培训', '学校', '学费', '书本'],
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in merchant_name or kw in merchant_lower for kw in keywords):
                return category
        
        return None
    
    def _generate_raw_id(self, match: re.Match, pattern_name: str) -> str:
        """生成原始ID"""
        import hashlib
        content = f"{pattern_name}:{match.group(0)}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def is_cmb_email(self, subject: str, from_addr: str = "") -> bool:
        """
        判断是否为招行动账邮件
        
        Args:
            subject: 邮件主题
            from_addr: 发件人地址
            
        Returns:
            是否为招行动账邮件
        """
        cmb_keywords = [
            '招商银行', '招行', 'CMB', 
            '动账通知', '消费提醒', '入账通知',
            '账户变动', '支付提醒'
        ]
        
        # 检查主题
        if any(kw in subject for kw in cmb_keywords):
            return True
        
        # 检查发件人
        if from_addr and any(domain in from_addr for domain in ['cmbchina.com', 'cmb.com']):
            return True
        
        return False


# 便捷函数
def parse_cmb_email(email_body: str, **kwargs) -> Optional[RawTransaction]:
    """便捷函数：解析招行动账邮件"""
    parser = CMBEmailParser()
    return parser.parse(email_body, **kwargs)
