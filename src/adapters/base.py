"""
数据源适配器基类
定义所有数据源适配器必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import Iterator, List, Optional, Dict, Any
from datetime import datetime
from src.models.transaction import RawTransaction


class DataSourceAdapter(ABC):
    """
    数据源适配器抽象基类
    
    所有数据源（QQ邮箱、招行API、支付宝等）必须实现此接口。
    适配器的职责是将特定数据源格式转换为统一的 RawTransaction 格式。
    """
    
    def __init__(self):
        self._initialized = False
        self._config: Dict[str, Any] = {}
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """
        数据源类型标识
        
        Returns:
            唯一标识，如 'qqmail', 'cmb_email', 'alipay_api'
        """
        pass
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        人类可读的数据源名称
        
        Returns:
            如 'QQ邮箱(IMAP)', '招商银行邮件'
        """
        pass
    
    @property
    def capabilities(self) -> Dict[str, bool]:
        """
        数据源能力声明
        
        Returns:
            {
                'real_time': False,      # 是否支持实时推送
                'historical': True,      # 是否支持历史数据
                'bidirectional': False,  # 是否支持双向同步
                'auto_categorize': False # 是否提供自动分类
            }
        """
        return {
            'real_time': False,
            'historical': True,
            'bidirectional': False,
            'auto_categorize': False
        }
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        初始化数据源连接
        
        Args:
            config: 数据源配置参数，不同数据源配置不同
                qqmail: {username, auth_code, imap_server}
                cmb_email: {parser_config}
                
        Returns:
            是否初始化成功
        """
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            {
                'status': 'healthy' | 'degraded' | 'unhealthy',
                'latency_ms': 150,
                'last_success': datetime,
                'error_count': 0,
                'message': 'OK'
            }
        """
        pass
    
    @abstractmethod
    def fetch_transactions(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        account_filter: Optional[str] = None,
        **kwargs
    ) -> Iterator[RawTransaction]:
        """
        获取交易记录（核心方法）
        
        这是适配器的核心职责：将所有数据源数据转换为统一的 RawTransaction
        
        Args:
            start_time: 开始时间（包含）
            end_time: 结束时间（包含）
            account_filter: 账户过滤（如卡号尾号）
            **kwargs: 数据源特定参数
            
        Yields:
            RawTransaction 对象
        """
        pass
    
    @abstractmethod
    def close(self):
        """关闭数据源连接，释放资源"""
        pass
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self._config.copy()


class DataSourceError(Exception):
    """数据源基础异常"""
    
    def __init__(self, message: str, retryable: bool = False, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.details = details or {}


class ConnectionError(DataSourceError):
    """连接错误 - 可重试"""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, retryable=True, details=details)


class AuthenticationError(DataSourceError):
    """认证错误 - 需人工介入"""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, retryable=False, details=details)


class ParseError(DataSourceError):
    """解析错误 - 记录日志，跳过"""
    
    def __init__(self, message: str, raw_data: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message, retryable=False, details=details)
        self.raw_data = raw_data


class RateLimitError(DataSourceError):
    """速率限制错误 - 可重试，需要等待"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, details: Optional[Dict] = None):
        super().__init__(message, retryable=True, details=details)
        self.retry_after = retry_after  # 建议等待秒数
