"""
QQ 邮箱 IMAP 适配器
支持通过 IMAP 协议拉取邮件并解析交易信息
"""

import imaplib
import ssl
import email
import email.policy
from datetime import datetime, timedelta
from typing import Iterator, Optional, Dict, Any, List
from adapters.base import (
    DataSourceAdapter, ConnectionError, AuthenticationError,
    ParseError, RateLimitError
)
from models.transaction import RawTransaction
from parsers.cmb_email_parser import CMBEmailParser


class QQMailIMAPAdapter(DataSourceAdapter):
    """
    QQ 邮箱 IMAP 适配器
    
    用于从 QQ 邮箱拉取邮件，支持解析招行动账通知等财务邮件。
    """
    
    # 类属性
    source_type = "qqmail"
    source_name = "QQ邮箱(IMAP)"
    
    # IMAP 服务器配置
    IMAP_SERVER = "imap.qq.com"
    IMAP_PORT = 993
    
    def __init__(self):
        super().__init__()
        self._mail: Optional[imaplib.IMAP4_SSL] = None
        self._parser = CMBEmailParser()
        self._username: Optional[str] = None
        self._auth_code: Optional[str] = None
    
    @property
    def capabilities(self) -> Dict[str, bool]:
        """数据源能力声明"""
        return {
            'real_time': False,      # 不支持实时推送
            'historical': True,      # 支持历史数据拉取
            'bidirectional': False,  # 不支持双向同步
            'auto_categorize': False # 不提供自动分类
        }
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        初始化数据源连接
        
        Args:
            config: 配置字典，必须包含：
                - username: QQ 邮箱地址
                - auth_code: 授权码（非邮箱密码）
                - imap_server: IMAP 服务器（可选，默认 imap.qq.com）
                - imap_port: IMAP 端口（可选，默认 993）
        
        Returns:
            是否初始化成功
        """
        try:
            # 验证必要配置
            self._username = config.get('username')
            self._auth_code = config.get('auth_code')
            
            if not self._username or not self._auth_code:
                raise AuthenticationError(
                    "配置错误：必须提供 username 和 auth_code",
                    details={'missing_fields': ['username', 'auth_code']}
                )
            
            # 保存配置
            self._config = config
            self._initialized = True
            
            print(f"[✓] QQMail 适配器初始化成功: {self._username}")
            return True
            
        except AuthenticationError:
            raise
        except Exception as e:
            raise ConnectionError(
                f"初始化失败: {e}",
                details={'error': str(e)}
            )
    
    def _connect(self) -> imaplib.IMAP4_SSL:
        """建立 IMAP 连接"""
        try:
            # 创建 SSL 上下文
            context = ssl.create_default_context()
            
            # 连接服务器
            server = self._config.get('imap_server', self.IMAP_SERVER)
            port = self._config.get('imap_port', self.IMAP_PORT)
            
            print(f"[→] 连接 IMAP 服务器: {server}:{port}")
            mail = imaplib.IMAP4_SSL(server, port, ssl_context=context)
            
            # 登录
            print(f"[→] 登录邮箱: {self._username}")
            status, response = mail.login(self._username, self._auth_code)
            
            if status != 'OK':
                raise AuthenticationError(
                    f"登录失败: {response}",
                    details={'status': status, 'response': str(response)}
                )
            
            print("[✓] IMAP 连接成功")
            return mail
            
        except AuthenticationError:
            raise
        except Exception as e:
            raise ConnectionError(
                f"连接失败: {e}",
                details={'error': str(e)}
            )
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 尝试连接
            mail = self._connect()
            
            # 获取邮箱状态
            status, response = mail.status('INBOX', '(MESSAGES RECENT UIDNEXT UIDVALIDITY UNSEEN)')
            
            # 关闭连接
            mail.close()
            mail.logout()
            
            return {
                'status': 'healthy',
                'latency_ms': 0,  # 实际应该测量
                'last_success': datetime.now(),
                'error_count': 0,
                'message': 'OK',
                'details': {'status_response': str(response)}
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'latency_ms': 0,
                'last_success': None,
                'error_count': 1,
                'message': str(e),
                'details': {'error': str(e)}
            }
    
    def fetch_transactions(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        account_filter: Optional[str] = None,
        **kwargs
    ) -> Iterator[RawTransaction]:
        """
        获取交易记录
        
        从 QQ 邮箱拉取邮件，解析其中的财务交易信息。
        
        Args:
            start_time: 开始时间（包含），默认 7 天前
            end_time: 结束时间（包含），默认现在
            account_filter: 账户过滤（如卡号尾号）
            **kwargs: 其他参数
                - folder: 邮箱文件夹，默认 INBOX
                - mark_as_read: 是否标记为已读，默认 False
        
        Yields:
            RawTransaction 对象
        """
        if not self._initialized:
            raise RuntimeError("适配器未初始化，请先调用 initialize()")
        
        # 设置默认时间范围
        if not start_time:
            start_time = datetime.now() - timedelta(days=7)
        if not end_time:
            end_time = datetime.now()
        
        # 获取其他参数
        folder = kwargs.get('folder', 'INBOX')
        mark_as_read = kwargs.get('mark_as_read', False)
        
        try:
            # 连接邮箱
            mail = self._connect()
            
            # 选择文件夹
            status, _ = mail.select(folder)
            if status != 'OK':
                raise ConnectionError(f"无法打开文件夹: {folder}")
            
            # 搜索邮件
            search_criteria = self._build_search_criteria(start_time, end_time)
            status, data = mail.search(None, search_criteria)
            
            if status != 'OK':
                print(f"搜索邮件失败: {data}")
                return
            
            email_ids = data[0].split()
            print(f"找到 {len(email_ids)} 封邮件")
            
            # 处理每封邮件
            for email_id in email_ids:
                try:
                    # 获取邮件内容
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    # 解析邮件
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email, policy=email.policy.default)
                    
                    # 提取邮件信息
                    subject = msg.get('Subject', '')
                    from_addr = msg.get('From', '')
                    date = msg.get('Date', '')
                    
                    # 提取正文
                    body = self._extract_body(msg)
                    
                    # 检查是否为招行邮件
                    if not self._parser.is_cmb_email(subject, from_addr):
                        continue
                    
                    # 解析交易
                    transaction = self._parser.parse(body, subject, from_addr, date)
                    
                    if transaction:
                        # 账户过滤
                        if account_filter and transaction.account_id != account_filter:
                            continue
                        
                        # 时间过滤
                        if transaction.transaction_time < start_time or transaction.transaction_time > end_time:
                            continue
                        
                        yield transaction
                        
                        # 标记为已读
                        if mark_as_read:
                            mail.store(email_id, '+FLAGS', '\\Seen')
                
                except Exception as e:
                    print(f"处理邮件 {email_id} 失败: {e}")
                    continue
            
            # 关闭连接
            mail.close()
            mail.logout()
            
        except Exception as e:
            raise ConnectionError(f"获取交易失败: {e}")
    
    def _build_search_criteria(self, start_time: datetime, end_time: datetime) -> str:
        """构建 IMAP 搜索条件"""
        # 格式化日期为 IMAP 格式 (01-Jan-2024)
        since_str = start_time.strftime('%d-%b-%Y')
        before_str = (end_time + timedelta(days=1)).strftime('%d-%b-%Y')
        
        # 搜索条件：日期范围内，未读邮件
        criteria = f'(SINCE "{since_str}" BEFORE "{before_str}")'
        
        return criteria
    
    def _extract_body(self, msg: email.message.Message) -> str:
        """提取邮件正文"""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = part.get('Content-Disposition', '')
                
                # 优先获取纯文本
                if content_type == "text/plain" and 'attachment' not in content_disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body = payload.decode(charset, errors='ignore')
                        break
                
                # 备选 HTML
                elif content_type == "text/html" and not body:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        html = payload.decode(charset, errors='ignore')
                        # 简单 HTML 转文本
                        body = self._html_to_text(html)
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='ignore')
        
        return body
    
    def _html_to_text(self, html: str) -> str:
        """简单 HTML 转文本"""
        import re
        
        # 移除 script 和 style
        text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # 替换常见标签
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<p[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '', text, flags=re.IGNORECASE)
        
        # 移除所有标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 解码 HTML 实体
        import html as html_module
        text = html_module.unescape(text)
        
        # 清理空白
        lines = [line.strip() for line in text.split('\n')]
        return '\n'.join(line for line in lines if line)
    
    def close(self):
        """关闭连接"""
        # 连接在 fetch_transactions 中已关闭
        self._initialized = False
