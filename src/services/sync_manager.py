"""
同步管理器 - 统一管理数据同步
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from src.adapters.qqmail_adapter import QQMailIMAPAdapter
from src.storage.database import TransactionRepository


class SyncManager:
    """同步管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._adapters: Dict[str, Any] = {}
        self._repo = self._init_repository()
        self._init_adapters()

    def _init_repository(self) -> TransactionRepository:
        """初始化数据库仓库"""
        db_config = self.config.get('database', {}) if isinstance(self.config, dict) else {}
        sqlite_config = db_config.get('sqlite', {}) if isinstance(db_config, dict) else {}
        db_path = sqlite_config.get('path', './data/finance.db')
        return TransactionRepository(db_path=db_path)
    
    def _init_adapters(self) -> None:
        """初始化适配器"""
        sources = self.config.get('sources', {})
        
        # QQMail 适配器
        if sources.get('qqmail', {}).get('enabled', False):
            self._adapters['qqmail'] = QQMailIMAPAdapter()
    
    def sync(self, source: str, days: int = 7, dry_run: bool = False) -> Dict[str, Any]:
        """
        执行同步
        
        Args:
            source: 数据源名称 (qqmail, all)
            days: 拉取多少天的数据
            dry_run: 试运行模式
            
        Returns:
            同步结果统计
        """
        if source == 'all':
            return self._sync_all(days, dry_run)
        
        return self._sync_single(source, days, dry_run)
    
    def _sync_single(self, source: str, days: int, dry_run: bool) -> Dict[str, Any]:
        """同步单个数据源"""
        if source not in self._adapters:
            raise ValueError(f"未知的数据源: {source}")
        
        adapter = self._adapters[source]
        config = self._get_source_config(source)
        sync_config = config.get('sync', {}) if isinstance(config, dict) else {}
        
        # 初始化适配器
        adapter.initialize(config)
        
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        # 优先使用账户级 last_sync_time
        account_id = config.get('account_id') if isinstance(config, dict) else None
        if account_id:
            last_sync = self._repo.get_last_sync_time(account_id)
            if last_sync:
                start_time = last_sync
        else:
            _, last_sync = self._repo.get_single_account_last_sync_time()
            if last_sync:
                start_time = last_sync
        
        # 获取交易数据
        new_count = 0
        duplicate_count = 0
        errors = []
        
        try:
            for transaction in adapter.fetch_transactions(
                start_time,
                end_time,
                account_filter=account_id,
                mark_as_read=sync_config.get('mark_as_read', False)
            ):
                if dry_run:
                    counterparty_name = (
                        transaction.counterparty.name
                        if getattr(transaction, "counterparty", None) is not None
                        else "未知对手方"
                    )
                    print(f"  [试运行] {transaction.transaction_time} | {transaction.amount} | {counterparty_name}")
                    new_count += 1
                    continue
                
                # 保存到数据库
                try:
                    saved, message = self._repo.save_transaction(transaction)
                    if saved:
                        new_count += 1
                    elif message == "duplicate":
                        duplicate_count += 1
                        # 即使重复，也推进最后同步时间
                        self._repo.update_account_last_sync_time(
                            account_id=transaction.account_id,
                            last_sync_time=transaction.transaction_time,
                            account_name=transaction.account_name,
                            account_type=transaction.account_type,
                        )
                    else:
                        errors.append(message)
                except Exception as e:
                    errors.append(str(e))
        
        finally:
            adapter.close()
        
        return {
            'source': source,
            'new': new_count,
            'duplicate': duplicate_count,
            'errors': errors,
            'dry_run': dry_run,
            'start_time': start_time,
            'end_time': end_time
        }
    
    def _sync_all(self, days: int, dry_run: bool) -> Dict[str, Any]:
        """同步所有数据源"""
        results = {}
        total_new = 0
        total_duplicate = 0
        
        for source in self._adapters.keys():
            print(f"\n[→] 同步 {source}...")
            result = self._sync_single(source, days, dry_run)
            results[source] = result
            total_new += result['new']
            total_duplicate += result['duplicate']
        
        return {
            'sources': results,
            'total_new': total_new,
            'total_duplicate': total_duplicate,
            'dry_run': dry_run
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        status = {}
        
        for name, adapter in self._adapters.items():
            try:
                health = adapter.health_check()
                status[name] = {
                    'status': health.get('status', 'unknown'),
                    'last_sync': None,  # TODO: 从数据库查询
                    'total_records': 0,  # TODO: 从数据库查询
                    'health': health
                }
            except Exception as e:
                status[name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return status
    
    def _get_source_config(self, source: str) -> Dict[str, Any]:
        """获取数据源配置"""
        sources = self.config.get('sources', {})
        return sources.get(source, {})
