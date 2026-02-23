"""
配置管理器 - 统一管理应用配置
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self._config: Optional[Dict] = None
    
    def load(self) -> Dict[str, Any]:
        """加载配置"""
        if self._config is not None:
            return self._config
        
        # 如果配置文件不存在，从示例创建
        if not self.config_path.exists():
            example_path = self.config_path.parent / "config.example.yaml"
            if example_path.exists():
                import shutil
                shutil.copy(example_path, self.config_path)
                print(f"[i] 从示例创建配置文件: {self.config_path}")
        
        # 加载 YAML
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = {}
        
        # 环境变量覆盖
        self._apply_env_overrides()
        
        return self._config
    
    def save(self, config: Dict[str, Any]) -> None:
        """保存配置"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        self._config = config
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """获取配置项 (支持点号路径，如 'sources.qqmail.username')"""
        config = self.load()
        keys = key_path.split('.')
        current = config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    def set(self, key_path: str, value: Any) -> None:
        """设置配置项"""
        config = self.load()
        keys = key_path.split('.')
        current = config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        self.save(config)
    
    def _apply_env_overrides(self) -> None:
        """应用环境变量覆盖"""
        env_mappings = {
            'QQMAIL_USERNAME': ('sources', 'qqmail', 'username'),
            'QQMAIL_AUTH_CODE': ('sources', 'qqmail', 'auth_code'),
            'DATABASE_URL': ('database', 'url'),
        }
        
        for env_var, path in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                current = self._config
                for key in path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[path[-1]] = value
