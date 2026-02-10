#!/usr/bin/env python
# coding: utf-8
"""
统一配置管理模块
提供集中化的配置管理和验证机制
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = "root"
    database: str = "fund_analysis"
    charset: str = "utf8mb4"
    pool_size: int = 10
    pool_timeout: int = 30


@dataclass
class CacheConfig:
    """缓存配置"""
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    default_ttl: int = 900  # 15分钟
    memory_cache_size: int = 1000


@dataclass
class NotificationConfig:
    """通知配置"""
    enabled: bool = True
    token: str = ""
    provider: str = "wechat"
    fallback_enabled: bool = True


@dataclass
class DataSourceConfig:
    """数据源配置"""
    tushare: Dict[str, str] = field(default_factory=lambda: {
        'token': '5ff19facae0e5b26a407d491d33707a9884a39a714a0d76b6495725b',
        'timeout': '10'
    })
    akshare: Dict[str, str] = field(default_factory=lambda: {
        'timeout': '15',
        'retry_times': '3'
    })
    eastmoney: Dict[str, str] = field(default_factory=lambda: {
        'timeout': '10'
    })


@dataclass
class AppConfig:
    """应用配置"""
    debug: bool = False
    secret_key: str = "your-secret-key-here"
    host: str = "0.0.0.0"
    port: int = 5001
    timezone: str = "Asia/Shanghai"


@dataclass
class SystemConfig:
    """系统配置"""
    # 文件路径配置
    fund_position_file: str = "d:/codes/py4zinia/pro2/fund_search/京东金融.xlsx"
    report_dir: str = "D:/coding/trae_project/py4zinia/pro2/reports"
    
    # 策略配置
    default_base_investment: float = 1000.0
    max_positions: int = 10
    risk_tolerance: float = 0.05
    
    # 性能配置
    max_concurrent_requests: int = 5
    request_timeout: int = 30
    batch_size: int = 100


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None, env_prefix: str = "FUND"):
        self.env_prefix = env_prefix
        self._configs = {}
        self._load_configs(config_file)
    
    def _load_configs(self, config_file: Optional[str] = None):
        """加载配置"""
        # 加载环境变量配置
        self._load_from_env()
        
        # 加载配置文件（如果存在）
        if config_file and os.path.exists(config_file):
            self._load_from_file(config_file)
        
        # 验证配置
        self._validate_configs()
        
        logger.info("配置加载完成")
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        # 数据库配置
        self._configs['database'] = DatabaseConfig(
            host=os.environ.get(f'{self.env_prefix}_DB_HOST', 'localhost'),
            port=int(os.environ.get(f'{self.env_prefix}_DB_PORT', '3306')),
            user=os.environ.get(f'{self.env_prefix}_DB_USER', 'root'),
            password=os.environ.get(f'{self.env_prefix}_DB_PASSWORD', 'root'),
            database=os.environ.get(f'{self.env_prefix}_DB_NAME', 'fund_analysis'),
            charset=os.environ.get(f'{self.env_prefix}_DB_CHARSET', 'utf8mb4'),
            pool_size=int(os.environ.get(f'{self.env_prefix}_DB_POOL_SIZE', '10')),
            pool_timeout=int(os.environ.get(f'{self.env_prefix}_DB_POOL_TIMEOUT', '30'))
        )
        
        # 缓存配置
        self._configs['cache'] = CacheConfig(
            redis_host=os.environ.get(f'{self.env_prefix}_REDIS_HOST', 'localhost'),
            redis_port=int(os.environ.get(f'{self.env_prefix}_REDIS_PORT', '6379')),
            redis_db=int(os.environ.get(f'{self.env_prefix}_REDIS_DB', '0')),
            default_ttl=int(os.environ.get(f'{self.env_prefix}_CACHE_TTL', '900')),
            memory_cache_size=int(os.environ.get(f'{self.env_prefix}_MEMORY_CACHE_SIZE', '1000'))
        )
        
        # 通知配置
        self._configs['notification'] = NotificationConfig(
            enabled=os.environ.get(f'{self.env_prefix}_NOTIFICATION_ENABLED', 'true').lower() == 'true',
            token=os.environ.get(f'{self.env_prefix}_NOTIFICATION_TOKEN', ''),
            provider=os.environ.get(f'{self.env_prefix}_NOTIFICATION_PROVIDER', 'wechat'),
            fallback_enabled=os.environ.get(f'{self.env_prefix}_NOTIFICATION_FALLBACK', 'true').lower() == 'true'
        )
        
        # 应用配置
        self._configs['app'] = AppConfig(
            debug=os.environ.get(f'{self.env_prefix}_DEBUG', 'false').lower() == 'true',
            secret_key=os.environ.get(f'{self.env_prefix}_SECRET_KEY', 'your-secret-key-here'),
            host=os.environ.get(f'{self.env_prefix}_HOST', '0.0.0.0'),
            port=int(os.environ.get(f'{self.env_prefix}_PORT', '5001')),
            timezone=os.environ.get(f'{self.env_prefix}_TIMEZONE', 'Asia/Shanghai')
        )
        
        # 系统配置
        self._configs['system'] = SystemConfig(
            fund_position_file=os.environ.get(f'{self.env_prefix}_POSITION_FILE', 
                                            'd:/codes/py4zinia/pro2/fund_search/京东金融.xlsx'),
            report_dir=os.environ.get(f'{self.env_prefix}_REPORT_DIR',
                                    'D:/coding/trae_project/py4zinia/pro2/reports'),
            default_base_investment=float(os.environ.get(f'{self.env_prefix}_BASE_INVESTMENT', '1000.0')),
            max_positions=int(os.environ.get(f'{self.env_prefix}_MAX_POSITIONS', '10')),
            risk_tolerance=float(os.environ.get(f'{self.env_prefix}_RISK_TOLERANCE', '0.05')),
            max_concurrent_requests=int(os.environ.get(f'{self.env_prefix}_MAX_CONCURRENT', '5')),
            request_timeout=int(os.environ.get(f'{self.env_prefix}_REQUEST_TIMEOUT', '30')),
            batch_size=int(os.environ.get(f'{self.env_prefix}_BATCH_SIZE', '100'))
        )
    
    def _load_from_file(self, config_file: str):
        """从配置文件加载配置"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
            
            # 合并配置（文件配置优先于环境变量）
            for section, config_data in file_config.items():
                if section in self._configs:
                    # 更新现有配置
                    for key, value in config_data.items():
                        if hasattr(self._configs[section], key):
                            setattr(self._configs[section], key, value)
                else:
                    # 创建新的配置节
                    self._configs[section] = config_data
                    
            logger.info(f"从配置文件加载配置: {config_file}")
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}")
    
    def _validate_configs(self):
        """验证配置的有效性"""
        errors = []
        
        # 验证数据库配置
        db_config = self._configs.get('database')
        if db_config:
            if not db_config.host or not db_config.database:
                errors.append("数据库主机和数据库名不能为空")
            if db_config.port <= 0 or db_config.port > 65535:
                errors.append("数据库端口必须在1-65535之间")
        
        # 验证通知配置
        notif_config = self._configs.get('notification')
        if notif_config and notif_config.enabled and not notif_config.token:
            logger.warning("通知功能已启用但未配置token")
        
        # 验证系统配置
        sys_config = self._configs.get('system')
        if sys_config:
            if sys_config.default_base_investment <= 0:
                errors.append("默认投资额必须大于0")
            if sys_config.max_positions <= 0:
                errors.append("最大持仓数量必须大于0")
            if not 0 <= sys_config.risk_tolerance <= 1:
                errors.append("风险容忍度必须在0-1之间")
        
        if errors:
            raise ValueError(f"配置验证失败: {'; '.join(errors)}")
        
        logger.info("配置验证通过")
    
    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            section: 配置节名称
            key: 配置项名称（可选）
            default: 默认值
            
        Returns:
            配置值
        """
        if section not in self._configs:
            return default
        
        config_section = self._configs[section]
        
        if key is None:
            return config_section
        
        if hasattr(config_section, key):
            return getattr(config_section, key)
        else:
            return default
    
    def get_database_config(self) -> DatabaseConfig:
        """获取数据库配置"""
        return self._configs.get('database', DatabaseConfig())
    
    def get_cache_config(self) -> CacheConfig:
        """获取缓存配置"""
        return self._configs.get('cache', CacheConfig())
    
    def get_notification_config(self) -> NotificationConfig:
        """获取通知配置"""
        return self._configs.get('notification', NotificationConfig())
    
    def get_app_config(self) -> AppConfig:
        """获取应用配置"""
        return self._configs.get('app', AppConfig())
    
    def get_system_config(self) -> SystemConfig:
        """获取系统配置"""
        return self._configs.get('system', SystemConfig())
    
    def get_all_configs(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._configs.copy()
    
    def update_config(self, section: str, key: str, value: Any):
        """
        更新配置值
        
        Args:
            section: 配置节名称
            key: 配置项名称
            value: 新值
        """
        if section not in self._configs:
            raise KeyError(f"配置节 '{section}' 不存在")
        
        config_section = self._configs[section]
        if hasattr(config_section, key):
            setattr(config_section, key, value)
            logger.info(f"配置更新: {section}.{key} = {value}")
        else:
            raise AttributeError(f"配置项 '{key}' 在节 '{section}' 中不存在")
    
    def reload(self, config_file: Optional[str] = None):
        """
        重新加载配置
        
        Args:
            config_file: 配置文件路径
        """
        self._configs.clear()
        self._load_configs(config_file)
        logger.info("配置已重新加载")


# 全局配置管理器实例
config_manager = ConfigManager()

# 为了向后兼容，保留原有的配置访问方式
DATABASE_CONFIG = config_manager.get_database_config()
CACHE_CONFIG = config_manager.get_cache_config()
NOTIFICATION_CONFIG = config_manager.get_notification_config()
APP_CONFIG = config_manager.get_app_config()
SYSTEM_CONFIG = config_manager.get_system_config()