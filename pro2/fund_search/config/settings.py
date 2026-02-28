#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一配置管理 - 设置模块
定义所有配置数据类并提供统一的设置管理器
"""

import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

from .base import BaseConfig, ConfigLoader, get_config_dir, detect_environment, Environment

logger = logging.getLogger(__name__)


# =============================================================================
# 数据库配置
# =============================================================================
@dataclass
class DatabaseConfig(BaseConfig):
    """数据库配置"""
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = "root"
    database: str = "fund_analysis"
    charset: str = "utf8mb4"
    pool_size: int = 10
    pool_timeout: int = 30
    
    def validate(self) -> tuple[bool, list[str]]:
        """验证数据库配置"""
        errors = []
        
        if not self.host:
            errors.append("数据库主机不能为空")
        if not self.database:
            errors.append("数据库名不能为空")
        if not (0 < self.port <= 65535):
            errors.append("数据库端口必须在 1-65535 之间")
        
        return len(errors) == 0, errors
    
    def to_connection_string(self) -> str:
        """生成数据库连接字符串"""
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"


# =============================================================================
# 缓存配置
# =============================================================================
@dataclass
class CacheConfig(BaseConfig):
    """缓存配置"""
    # Redis 配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # 缓存策略
    default_ttl: int = 900  # 15分钟
    memory_cache_size: int = 1000
    
    # 内存缓存 TTL（秒）
    memory_ttl_latest_nav: int = 900        # 15分钟
    memory_ttl_nav_history: int = 3600      # 1小时
    memory_ttl_fund_basic: int = 86400      # 1天
    memory_ttl_performance: int = 3600      # 1小时
    
    # 数据库缓存 TTL（秒）
    db_ttl_latest_nav: int = 1800           # 30分钟
    db_ttl_nav_history: int = 86400         # 1天
    db_ttl_fund_basic: int = 604800         # 7天
    
    def get_memory_ttl(self, data_type: str) -> int:
        """获取内存缓存 TTL"""
        mapping = {
            'latest_nav': self.memory_ttl_latest_nav,
            'nav_history': self.memory_ttl_nav_history,
            'fund_basic': self.memory_ttl_fund_basic,
            'performance': self.memory_ttl_performance,
        }
        return mapping.get(data_type, self.default_ttl)
    
    def get_db_ttl(self, data_type: str) -> int:
        """获取数据库缓存 TTL"""
        mapping = {
            'latest_nav': self.db_ttl_latest_nav,
            'nav_history': self.db_ttl_nav_history,
            'fund_basic': self.db_ttl_fund_basic,
        }
        return mapping.get(data_type, self.default_ttl)


# =============================================================================
# 通知配置
# =============================================================================
@dataclass
class WechatConfig(BaseConfig):
    """微信通知配置"""
    enabled: bool = True
    token: str = ""
    template: str = "html"


@dataclass
class EmailConfig(BaseConfig):
    """邮件通知配置"""
    enabled: bool = False
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_receivers: List[str] = field(default_factory=list)


@dataclass
class NotificationConfig(BaseConfig):
    """通知配置"""
    wechat: WechatConfig = field(default_factory=WechatConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    fallback_enabled: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationConfig':
        """从字典创建，支持嵌套配置"""
        wechat_data = data.get('wechat', {})
        email_data = data.get('email', {})
        
        return cls(
            wechat=WechatConfig.from_dict(wechat_data),
            email=EmailConfig.from_dict(email_data),
            fallback_enabled=data.get('fallback_enabled', True)
        )


# =============================================================================
# 数据源配置
# =============================================================================
@dataclass
class TushareConfig(BaseConfig):
    """Tushare 数据源配置"""
    token: str = ""
    timeout: int = 30
    max_retries: int = 3


@dataclass
class AkshareConfig(BaseConfig):
    """Akshare 数据源配置"""
    timeout: int = 30
    max_retries: int = 3
    delay_between_requests: float = 1.0


@dataclass
class FallbackConfig(BaseConfig):
    """备用数据源配置"""
    sina_enabled: bool = True
    eastmoney_enabled: bool = True
    request_timeout: int = 10


@dataclass
class DataSourceConfig(BaseConfig):
    """数据源配置"""
    tushare: TushareConfig = field(default_factory=TushareConfig)
    akshare: AkshareConfig = field(default_factory=AkshareConfig)
    fallback: FallbackConfig = field(default_factory=FallbackConfig)
    
    # 数据源优先级
    primary: str = "tushare"
    backup_1: str = "akshare"
    backup_2: List[str] = field(default_factory=lambda: ["sina", "eastmoney"])
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataSourceConfig':
        """从字典创建，支持嵌套配置"""
        return cls(
            tushare=TushareConfig.from_dict(data.get('tushare', {})),
            akshare=AkshareConfig.from_dict(data.get('akshare', {})),
            fallback=FallbackConfig.from_dict(data.get('fallback', {})),
            primary=data.get('priority', {}).get('primary', 'tushare'),
            backup_1=data.get('priority', {}).get('backup_1', 'akshare'),
            backup_2=data.get('priority', {}).get('backup_2', ["sina", "eastmoney"])
        )


# =============================================================================
# 投资策略配置
# =============================================================================
@dataclass
class StopLossConfig(BaseConfig):
    """止损配置"""
    warning_threshold: float = -0.08
    stop_loss_threshold: float = -0.12
    full_redeem: bool = False
    redeem_ratio: float = 0.3
    stop_loss_label: str = "🛑 **止损触发**"
    warning_label: str = "⚠️ **亏损警告**"


@dataclass
class VolatilityConfig(BaseConfig):
    """波动率配置"""
    high_threshold: float = 0.25
    low_threshold: float = 0.10
    high_adjustment: float = 0.5
    low_adjustment: float = 1.2
    normal_adjustment: float = 1.0
    lookback_days: int = 20


@dataclass
class TrendConfig(BaseConfig):
    """趋势配置"""
    ma_short_period: int = 5
    ma_long_period: int = 10
    uptrend_adjustment: float = 1.2
    downtrend_adjustment: float = 0.7
    sideways_adjustment: float = 1.0


@dataclass
class StrategyConfig(BaseConfig):
    """策略配置"""
    # 买入倍数
    buy_multipliers: Dict[str, float] = field(default_factory=lambda: {
        'strong_buy': 2.5,
        'buy': 1.5,
        'weak_buy': 1.2,
        'hold': 0.0,
        'sell': 0.0,
        'weak_sell': 0.0,
        'stop_loss': 0.0
    })
    
    # 子配置
    stop_loss: StopLossConfig = field(default_factory=StopLossConfig)
    volatility: VolatilityConfig = field(default_factory=VolatilityConfig)
    trend: TrendConfig = field(default_factory=TrendConfig)
    
    # 风险指标
    risk_free_rate: float = 0.03
    trading_days_per_year: int = 252
    historical_days: int = 365
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyConfig':
        """从字典创建，支持嵌套配置"""
        return cls(
            buy_multipliers=data.get('buy_multipliers', {
                'strong_buy': 2.5, 'buy': 1.5, 'weak_buy': 1.2,
                'hold': 0.0, 'sell': 0.0, 'weak_sell': 0.0, 'stop_loss': 0.0
            }),
            stop_loss=StopLossConfig.from_dict(data.get('stop_loss', {})),
            volatility=VolatilityConfig.from_dict(data.get('volatility', {})),
            trend=TrendConfig.from_dict(data.get('trend', {})),
            risk_free_rate=data.get('risk_free_rate', 0.03),
            trading_days_per_year=data.get('trading_days_per_year', 252),
            historical_days=data.get('historical_days', 365)
        )
    
    def validate(self) -> tuple[bool, list[str]]:
        """验证策略配置"""
        errors = []
        
        # 验证止损配置
        if self.stop_loss.warning_threshold >= 0:
            errors.append("止损警告阈值应为负数")
        if self.stop_loss.stop_loss_threshold >= 0:
            errors.append("止损阈值应为负数")
        if self.stop_loss.warning_threshold < self.stop_loss.stop_loss_threshold:
            errors.append("止损警告阈值应大于止损阈值")
        
        # 验证波动率配置
        if self.volatility.high_threshold <= self.volatility.low_threshold:
            errors.append("高波动阈值应大于低波动阈值")
        
        # 验证趋势配置
        if self.trend.ma_short_period >= self.trend.ma_long_period:
            errors.append("短期均线周期应小于长期均线周期")
        
        return len(errors) == 0, errors


# =============================================================================
# Celery 配置
# =============================================================================
@dataclass
class CeleryConfig(BaseConfig):
    """Celery 配置"""
    broker_url: str = "memory://"
    result_backend: str = "cache+memory://"
    task_always_eager: bool = True
    task_eager_propagates: bool = True
    task_serializer: str = "json"
    accept_content: List[str] = field(default_factory=lambda: ["json"])
    result_serializer: str = "json"
    timezone: str = "Asia/Shanghai"
    enable_utc: bool = True
    worker_concurrency: int = 4
    task_default_queue: str = "default"


# =============================================================================
# OCR 配置
# =============================================================================
@dataclass
class BaiduOcrConfig(BaseConfig):
    """百度 OCR 配置"""
    api_key: str = ""
    secret_key: str = ""
    use_accurate: bool = True
    timeout: int = 30


@dataclass
class OcrConfig(BaseConfig):
    """OCR 配置"""
    default_engine: str = "baidu"
    use_gpu: bool = False
    confidence_threshold: float = 0.5
    baidu: BaiduOcrConfig = field(default_factory=BaiduOcrConfig)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OcrConfig':
        """从字典创建，支持嵌套配置"""
        return cls(
            default_engine=data.get('default_engine', 'baidu'),
            use_gpu=data.get('use_gpu', False),
            confidence_threshold=data.get('confidence_threshold', 0.5),
            baidu=BaiduOcrConfig.from_dict(data.get('baidu', {}))
        )


# =============================================================================
# Web 应用配置
# =============================================================================
@dataclass
class WebConfig(BaseConfig):
    """Web 应用配置"""
    debug: bool = False
    secret_key: str = "your-secret-key-change-in-production"
    host: str = "0.0.0.0"
    port: int = 5001
    timezone: str = "Asia/Shanghai"
    max_content_length: int = 16 * 1024 * 1024  # 16MB


# =============================================================================
# 系统配置
# =============================================================================
@dataclass
class SystemConfig(BaseConfig):
    """系统配置"""
    # 文件路径
    fund_position_file: str = ""
    report_dir: str = ""
    
    # 投资策略
    default_base_investment: float = 1000.0
    max_positions: int = 10
    risk_tolerance: float = 0.05
    
    # 性能
    max_concurrent_requests: int = 5
    request_timeout: int = 30
    batch_size: int = 100
    
    # 图表
    chart_dpi: int = 350
    chart_style: str = "seaborn-v0_8"
    
    def __post_init__(self):
        """初始化后设置默认路径"""
        if not self.fund_position_file:
            # 默认使用项目目录下的文件
            project_root = Path(__file__).parent.parent
            self.fund_position_file = str(project_root / "京东金融.xlsx")
        
        if not self.report_dir:
            project_root = Path(__file__).parent.parent.parent
            self.report_dir = str(project_root / "reports")


# =============================================================================
# 日志配置
# =============================================================================
@dataclass
class LoggingConfig(BaseConfig):
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "fund_analysis.log"
    enable_console: bool = True
    enable_file: bool = True
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


# =============================================================================
# 统一设置管理器
# =============================================================================
class Settings:
    """
    统一设置管理器
    
    集中管理所有配置，提供统一的访问接口
    """
    
    _instance: Optional['Settings'] = None
    _initialized: bool = False
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_dir: Optional[str] = None, env_prefix: str = "FUND"):
        """
        初始化设置管理器
        
        Args:
            config_dir: 配置文件目录，默认使用内置 config 目录
            env_prefix: 环境变量前缀
        """
        if self._initialized:
            return
        
        self.env_prefix = env_prefix
        self._config_dir = Path(config_dir) if config_dir else get_config_dir()
        
        # 配置实例
        self._database: Optional[DatabaseConfig] = None
        self._cache: Optional[CacheConfig] = None
        self._notification: Optional[NotificationConfig] = None
        self._datasource: Optional[DataSourceConfig] = None
        self._strategy: Optional[StrategyConfig] = None
        self._celery: Optional[CeleryConfig] = None
        self._ocr: Optional[OcrConfig] = None
        self._web: Optional[WebConfig] = None
        self._system: Optional[SystemConfig] = None
        self._logging: Optional[LoggingConfig] = None
        
        # 加载所有配置
        self._load_all_configs()
        
        self._initialized = True
        logger.info("统一配置管理器初始化完成")
    
    def _load_all_configs(self):
        """加载所有配置"""
        # 加载配置文件
        file_configs = ConfigLoader.load_directory(self._config_dir)
        
        # 数据库配置
        db_data = file_configs.get('database', {})
        db_data.update(self._load_from_env('DB'))
        self._database = DatabaseConfig.from_dict(db_data)
        
        # 缓存配置
        cache_data = file_configs.get('cache', {})
        cache_data.update(self._load_from_env('CACHE'))
        self._cache = CacheConfig.from_dict(cache_data)
        
        # 通知配置
        notif_data = file_configs.get('notification', {})
        self._notification = NotificationConfig.from_dict(notif_data)
        
        # 数据源配置
        ds_data = file_configs.get('datasource', {})
        ds_data.update(self._load_from_env('DS'))
        self._datasource = DataSourceConfig.from_dict(ds_data)
        
        # 策略配置
        strategy_data = file_configs.get('strategy', {})
        self._strategy = StrategyConfig.from_dict(strategy_data)
        
        # Celery 配置
        celery_data = file_configs.get('celery', {})
        celery_data.update(self._load_from_env('CELERY'))
        self._celery = CeleryConfig.from_dict(celery_data)
        
        # OCR 配置
        ocr_data = file_configs.get('ocr', {})
        ocr_data.update(self._load_from_env('OCR'))
        self._ocr = OcrConfig.from_dict(ocr_data)
        
        # Web 配置
        web_data = file_configs.get('web', {})
        web_data.update(self._load_from_env('WEB'))
        self._web = WebConfig.from_dict(web_data)
        
        # 系统配置
        system_data = file_configs.get('system', {})
        system_data.update(self._load_from_env(''))
        self._system = SystemConfig.from_dict(system_data)
        
        # 日志配置
        logging_data = file_configs.get('logging', {})
        logging_data.update(self._load_from_env('LOG'))
        self._logging = LoggingConfig.from_dict(logging_data)
        
        # 验证所有配置
        self._validate_all()
    
    def _load_from_env(self, suffix: str) -> Dict[str, Any]:
        """从环境变量加载配置"""
        prefix = f"{self.env_prefix}_{suffix}_" if suffix else f"{self.env_prefix}_"
        result = {}
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                result[config_key] = value
        
        return result
    
    def _validate_all(self):
        """验证所有配置"""
        configs = [
            ('database', self._database),
            ('strategy', self._strategy),
        ]
        
        for name, config in configs:
            if config:
                is_valid, errors = config.validate()
                if not is_valid:
                    logger.error(f"{name} 配置验证失败: {errors}")
    
    # =============================================================================
    # 配置属性访问
    # =============================================================================
    @property
    def database(self) -> DatabaseConfig:
        """数据库配置"""
        return self._database
    
    @property
    def cache(self) -> CacheConfig:
        """缓存配置"""
        return self._cache
    
    @property
    def notification(self) -> NotificationConfig:
        """通知配置"""
        return self._notification
    
    @property
    def datasource(self) -> DataSourceConfig:
        """数据源配置"""
        return self._datasource
    
    @property
    def strategy(self) -> StrategyConfig:
        """策略配置"""
        return self._strategy
    
    @property
    def celery(self) -> CeleryConfig:
        """Celery 配置"""
        return self._celery
    
    @property
    def ocr(self) -> OcrConfig:
        """OCR 配置"""
        return self._ocr
    
    @property
    def web(self) -> WebConfig:
        """Web 配置"""
        return self._web
    
    @property
    def system(self) -> SystemConfig:
        """系统配置"""
        return self._system
    
    @property
    def logging(self) -> LoggingConfig:
        """日志配置"""
        return self._logging
    
    # =============================================================================
    # 便捷方法
    # =============================================================================
    def reload(self):
        """重新加载所有配置"""
        self._initialized = False
        self._load_all_configs()
        self._initialized = True
        logger.info("配置已重新加载")
    
    def to_dict(self) -> Dict[str, Any]:
        """导出所有配置为字典"""
        return {
            'database': self._database.to_dict() if self._database else {},
            'cache': self._cache.to_dict() if self._cache else {},
            'notification': self._notification.to_dict() if self._notification else {},
            'datasource': self._datasource.to_dict() if self._datasource else {},
            'strategy': self._strategy.to_dict() if self._strategy else {},
            'celery': self._celery.to_dict() if self._celery else {},
            'ocr': self._ocr.to_dict() if self._ocr else {},
            'web': self._web.to_dict() if self._web else {},
            'system': self._system.to_dict() if self._system else {},
            'logging': self._logging.to_dict() if self._logging else {},
        }
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        通过路径获取配置值
        
        Args:
            path: 配置路径，如 'database.host' 或 'strategy.stop_loss.warning_threshold'
            default: 默认值
            
        Returns:
            配置值
        """
        parts = path.split('.')
        
        # 获取顶级配置
        config_map = {
            'database': self._database,
            'cache': self._cache,
            'notification': self._notification,
            'datasource': self._datasource,
            'strategy': self._strategy,
            'celery': self._celery,
            'ocr': self._ocr,
            'web': self._web,
            'system': self._system,
            'logging': self._logging,
        }
        
        if not parts or parts[0] not in config_map:
            return default
        
        config = config_map[parts[0]]
        if config is None:
            return default
        
        # 遍历嵌套属性
        value = config
        for part in parts[1:]:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        
        return value


# =============================================================================
# 全局设置实例
# =============================================================================
def get_settings() -> Settings:
    """获取全局设置实例"""
    return Settings()


# 便捷访问函数
def get_db_config() -> DatabaseConfig:
    """获取数据库配置"""
    return get_settings().database


def get_cache_config() -> CacheConfig:
    """获取缓存配置"""
    return get_settings().cache


def get_datasource_config() -> DataSourceConfig:
    """获取数据源配置"""
    return get_settings().datasource


def get_strategy_config() -> StrategyConfig:
    """获取策略配置"""
    return get_settings().strategy


__all__ = [
    # 配置类
    'DatabaseConfig',
    'CacheConfig',
    'NotificationConfig',
    'WechatConfig',
    'EmailConfig',
    'DataSourceConfig',
    'TushareConfig',
    'AkshareConfig',
    'StrategyConfig',
    'StopLossConfig',
    'VolatilityConfig',
    'TrendConfig',
    'CeleryConfig',
    'OcrConfig',
    'BaiduOcrConfig',
    'WebConfig',
    'SystemConfig',
    'LoggingConfig',
    # 管理器
    'Settings',
    'get_settings',
    'get_db_config',
    'get_cache_config',
    'get_datasource_config',
    'get_strategy_config',
]
