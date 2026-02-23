#!/usr/bin/env python3
"""
Finance Tracker - 统一命令行入口
"""

import sys
import click
import yaml
from pathlib import Path
from typing import Optional

# 确保 src 目录在路径中
sys.path.insert(0, str(Path(__file__).parent))

from src.services.config_manager import ConfigManager
from src.services.sync_manager import SyncManager
from src.services.scheduler import Scheduler, create_default_scheduler
from src.storage.database import TransactionRepository


@click.group()
@click.option('--config', '-c', default='config/config.yaml', help='配置文件路径')
@click.pass_context
def cli(ctx, config):
    """Finance Tracker - 个人财务管理工具"""
    ctx.ensure_object(dict)
    ctx.obj['config_manager'] = ConfigManager(config)
    ctx.obj['config_path'] = config
    # 复用配置中的数据库路径
    cfg = ctx.obj['config_manager'].load()
    db_config = cfg.get('database', {}) if isinstance(cfg, dict) else {}
    sqlite_cfg = db_config.get('sqlite', {}) if isinstance(db_config, dict) else {}
    db_path = sqlite_cfg.get('path', './data/finance.db')
    ctx.obj['repo'] = TransactionRepository(db_path=db_path)


# ==================== 同步命令 ====================

@cli.group()
def sync():
    """数据同步命令"""
    pass


@sync.command()
@click.option('--source', '-s', 'source', required=True, 
              type=click.Choice(['qqmail', 'all']),
              help='数据源')
@click.option('--days', '-d', default=7, help='拉取多少天的数据')
@click.option('--dry-run', is_flag=True, help='试运行，不保存数据')
@click.pass_context
def run(ctx, source, days, dry_run):
    """执行同步"""
    config = ctx.obj['config_manager'].load()
    sync_manager = SyncManager(config)
    
    sources = ['all'] if source == 'all' else [source]
    
    for src in sources:
        click.echo(f"\n[→] 同步 {src}...")
        try:
            result = sync_manager.sync(src, days=days, dry_run=dry_run)
            click.echo(f"[✓] {src}: 新增 {result['new']} 条, 重复 {result['duplicate']} 条")
        except Exception as e:
            click.echo(f"[✗] {src}: {e}", err=True)


@sync.command()
@click.pass_context
def status(ctx):
    """查看同步状态"""
    config = ctx.obj['config_manager'].load()
    sync_manager = SyncManager(config)
    
    status = sync_manager.get_status()
    
    click.echo("\n📊 同步状态")
    click.echo("=" * 50)
    for source, info in status.items():
        click.echo(f"\n{source}:")
        click.echo(f"  状态: {info.get('status', 'unknown')}")
        click.echo(f"  上次同步: {info.get('last_sync', '从未')}")


# ==================== 配置命令 ====================

@cli.group()
def config():
    """配置管理命令"""
    pass


@config.command()
@click.pass_context
def show(ctx):
    """显示当前配置"""
    cfg = ctx.obj['config_manager'].load()
    click.echo(yaml.dump(cfg, default_flow_style=False, allow_unicode=True))


@config.command()
@click.argument('key')
@click.argument('value')
@click.pass_context
def set(ctx, key, value):
    """设置配置项 (key 格式: section.subsection.key)"""
    cfg_manager = ctx.obj['config_manager']
    
    # 尝试解析 value
    try:
        import json
        value_parsed = json.loads(value)
    except json.JSONDecodeError:
        value_parsed = value
    
    cfg_manager.set(key, value_parsed)
    click.echo(f"[✓] 已设置: {key} = {value_parsed}")


@config.command()
@click.argument('key')
@click.pass_context
def get(ctx, key):
    """获取配置项"""
    cfg_manager = ctx.obj['config_manager']
    value = cfg_manager.get(key)
    
    if value is not None:
        click.echo(f"{key} = {value}")
    else:
        click.echo(f"[✗] 配置项不存在: {key}", err=True)


# ==================== 调度命令 ====================

@cli.group()
def schedule():
    """定时任务管理"""
    pass


@schedule.command()
@click.option('--interval', '-i', default=60, help='检查间隔（分钟）')
@click.pass_context
def start(ctx, interval):
    """启动调度器"""
    config = ctx.obj['config_manager'].load()
    scheduler = create_default_scheduler(config)
    
    click.echo(f"[→] 启动调度器，检查间隔: {interval}分钟")
    try:
        scheduler.start(interval=interval)
    except KeyboardInterrupt:
        click.echo("\n[✓] 调度器已停止")


@schedule.command()
@click.pass_context
def status(ctx):
    """查看调度状态"""
    config = ctx.obj['config_manager'].load()
    scheduler = create_default_scheduler(config)
    
    jobs = scheduler.list_tasks()
    
    click.echo("\n📅 定时任务")
    click.echo("=" * 50)
    for job in jobs:
        click.echo(f"\n{job['name']}:")
        click.echo(f"  间隔: {job['interval_minutes']}分钟")
        click.echo(f"  下次运行: {job.get('next_run', '未调度')}")


# ==================== 主入口 ====================

# ==================== 账户/交易查询 ====================

@cli.group()
def account():
    """账户查询命令"""
    pass


@account.command("list")
@click.option('--limit', '-l', default=50, help='限制条数')
@click.pass_context
def account_list(ctx, limit):
    """列出账户信息"""
    repo = ctx.obj['repo']
    with repo._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, account_id, account_name, account_type, current_balance, last_sync_time
            FROM accounts
            ORDER BY account_id
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
    for row in rows:
        click.echo(f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")


@cli.group()
def tx():
    """交易查询命令"""
    pass


@tx.command("list")
@click.option('--limit', '-l', default=50, help='限制条数')
@click.option('--account-id', '-a', default=None, help='账户ID过滤')
@click.option('--type', '-t', 'tx_type', default=None, help='交易类型过滤')
@click.pass_context
def tx_list(ctx, limit, account_id, tx_type):
    """列出交易记录"""
    repo = ctx.obj['repo']
    rows = repo.get_transactions(
        account_id=account_id,
        transaction_type=tx_type,
        limit=limit,
    )
    for r in rows:
        click.echo(f"{r['transaction_time']} | {r['amount']} | {r.get('counterparty_name')} | {r['transaction_type']}")


# ==================== 主入口 ====================

if __name__ == '__main__':
    cli()
