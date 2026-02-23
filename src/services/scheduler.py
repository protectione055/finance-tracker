"""
调度器 - 定时任务管理
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any

from src.services.config_manager import ConfigManager
from src.services.sync_manager import SyncManager


class ScheduledTask:
    """定时任务"""
    
    def __init__(
        self,
        name: str,
        func: Callable,
        interval_minutes: int,
        args: tuple = (),
        kwargs: dict = None
    ):
        self.name = name
        self.func = func
        self.interval_minutes = interval_minutes
        self.args = args
        self.kwargs = kwargs or {}
        
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count = 0
        self.is_running = False
    
    def should_run(self) -> bool:
        """是否应该执行"""
        if self.is_running:
            return False
        if self.next_run is None:
            return True
        return datetime.now() >= self.next_run
    
    def execute(self) -> Any:
        """执行任务"""
        self.is_running = True
        self.last_run = datetime.now()
        
        try:
            result = self.func(*self.args, **self.kwargs)
            self.run_count += 1
            return result
        finally:
            self.is_running = False
            # 计算下次执行时间
            self.next_run = self.last_run + timedelta(minutes=self.interval_minutes)


class Scheduler:
    """任务调度器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    def add_task(
        self,
        name: str,
        func: Callable,
        interval_minutes: int,
        args: tuple = (),
        kwargs: dict = None
    ) -> ScheduledTask:
        """添加定时任务"""
        with self._lock:
            task = ScheduledTask(
                name=name,
                func=func,
                interval_minutes=interval_minutes,
                args=args,
                kwargs=kwargs
            )
            self.tasks[name] = task
            return task
    
    def remove_task(self, name: str) -> bool:
        """移除任务"""
        with self._lock:
            if name in self.tasks:
                del self.tasks[name]
                return True
            return False
    
    def get_task(self, name: str) -> Optional[ScheduledTask]:
        """获取任务"""
        return self.tasks.get(name)
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        result = []
        for name, task in self.tasks.items():
            result.append({
                'name': name,
                'interval_minutes': task.interval_minutes,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'next_run': task.next_run.isoformat() if task.next_run else None,
                'run_count': task.run_count,
                'is_running': task.is_running
            })
        return result
    
    def start(self, interval: int = 60) -> None:
        """
        启动调度器
        
        Args:
            interval: 检查间隔（秒）
        """
        if self._running:
            return
        
        self._running = True
        print(f"[→] 调度器启动，检查间隔: {interval}秒")
        
        try:
            while self._running:
                self._check_and_execute()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[✓] 调度器收到停止信号")
        finally:
            self._running = False
    
    def start_background(self, interval: int = 60) -> threading.Thread:
        """在后台线程启动调度器"""
        self._thread = threading.Thread(target=self.start, args=(interval,))
        self._thread.daemon = True
        self._thread.start()
        return self._thread
    
    def stop(self) -> None:
        """停止调度器"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
    
    def _check_and_execute(self) -> None:
        """检查并执行任务"""
        with self._lock:
            tasks_to_run = [
                task for task in self.tasks.values()
                if task.should_run()
            ]
        
        for task in tasks_to_run:
            print(f"[→] 执行任务: {task.name}")
            try:
                result = task.execute()
                print(f"[✓] 任务完成: {task.name}")
            except Exception as e:
                print(f"[✗] 任务失败: {task.name} - {e}")


def create_default_scheduler(config: Dict[str, Any]) -> Scheduler:
    """
    创建默认调度器，预置常用任务
    """
    from src.services.sync_manager import SyncManager
    
    scheduler = Scheduler(config)
    sync_manager = SyncManager(config)
    
    # 添加每小时同步任务
    scheduler.add_task(
        name="qqmail_sync",
        func=sync_manager.sync,
        interval_minutes=60,
        args=("qqmail",),
        kwargs={"days": 1}
    )
    
    return scheduler
