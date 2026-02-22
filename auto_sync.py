#!/usr/bin/env python3
"""
自动同步脚本 - 从QQ邮箱拉取新交易并保存到数据库
"""

import sys
sys.path.insert(0, 'src')

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from adapters.qqmail_adapter import QQMailIMAPAdapter
from storage.db_minimal import MinimalDB
from models.transaction import RawTransaction

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('./logs/auto_sync.log')
    ]
)
logger = logging.getLogger('auto_sync')


def sync_transactions():
    """同步交易记录"""
    logger.info("=" * 60)
    logger.info("开始自动同步")
    logger.info("=" * 60)
    
    # 配置
    config = {
        'username': 'protectione055@foxmail.com',
        'auth_code': 'ztdxpqtfkzypbdcc',
        'imap_server': 'imap.qq.com',
        'imap_port': 993,
        'use_ssl': True
    }
    
    # 创建适配器和数据库
    adapter = QQMailIMAPAdapter()
    db = MinimalDB("./data/finance_minimal.db")
    
    try:
        # 初始化适配器
        logger.info("[→] 初始化适配器...")
        adapter.initialize(config)
        logger.info("[✓] 适配器初始化成功")
        
        # 获取或创建账户
        account_id = db.get_or_create_account(
            account_number="8551",
            account_name="招商银行借记卡",
            account_type="debit",
            institution="招商银行"
        )
        
        if not account_id:
            logger.error("[✗] 无法获取账户")
            return
        
        logger.info(f"[✓] 账户ID: {account_id}")
        
        # 拉取最近24小时的交易
        logger.info("[→] 拉取交易记录...")
        
        new_count = 0
        duplicate_count = 0
        
        for transaction in adapter.fetch_transactions(
            start_time=datetime.now() - timedelta(hours=24)
        ):
            # 保存交易
            success, message = db.save_transaction(transaction, account_id)
            
            if success:
                new_count += 1
                logger.info(f"  [✓] 新交易: {transaction.transaction_time} - {transaction.amount}元")
            elif message == "duplicate":
                duplicate_count += 1
                logger.debug(f"  [⚠] 重复交易: {transaction.transaction_time}")
            else:
                logger.error(f"  [✗] 保存失败: {message}")
        
        logger.info(f"[✓] 同步完成: {new_count} 条新交易, {duplicate_count} 条重复")
        
        # 显示当前余额
        balance = db.get_account_balance(account_id)
        total = db.get_total_balance()
        
        logger.info(f"[ℹ] 当前余额: {balance} 元")
        logger.info(f"[ℹ] 总积蓄: {total} 元")
        
        # 关闭连接
        adapter.close()
        logger.info("[✓] 同步完成")
        
    except Exception as e:
        logger.error(f"[✗] 同步失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    sync_transactions()
