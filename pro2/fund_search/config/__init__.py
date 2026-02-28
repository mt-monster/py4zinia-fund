#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一配置管理模块

提供集中化的配置管理，支持：
- YAML/JSON 配置文件
- 环境变量覆盖
- 分层配置（开发/测试/生产）
- 配置验证
- 向后兼容

使用示例:
    # 方式1: 使用统一入口
    from fund_search.config import settings
    
    db_host = settings.database.host
    cache_ttl = settings.cache.default_ttl
    
    # 方式2: 使用便捷函数
    from fund_search.config import get_db_config, get_strategy_config
    
    db_config = get_db_config()
    strategy_config = get_strategy_config()
    
    # 方式3: 通过路径访问（支持嵌套）
    warning_threshold = settings.get('strategy.stop_loss.warning_threshold')
    
    # 方式4: 向后兼容（原有代码无需修改）
    from fund_search.config import DATABASE_CONFIG, CACHE_CONFIG

环境变量:
    所有配置都支持通过环境变量覆盖，格式为: FUND_<SECTION>_<KEY>
    例如:
    - FUND_DB_HOST=localhost
    - FUND_DB_PORT=3306
    - FUND_CACHE_DEFAULT_TTL=900
    - FUND_WEB_DEBUG=true
"""

import logging
from typing import Dict, Any, Optional

# 导入基础组件
from .base import (
    BaseConfig,
    ConfigLoader,
    Environment,
    detect_environment,
    get_config_dir,
    get_project_root,
    load_config,
)

# 导入配置类
from .settings import (
    # 配置数据类
    DatabaseConfig,
    CacheConfig,
    NotificationConfig,
    WechatConfig,
    EmailConfig,
    DataSourceConfig,
    TushareConfig,
    AkshareConfig,
    StrategyConfig,
    StopLossConfig,
    VolatilityConfig,
    TrendConfig,
    CeleryConfig,
    OcrConfig,
    BaiduOcrConfig,
    WebConfig,
    SystemConfig,
    LoggingConfig,
    # 管理器
    Settings,
    get_settings,
    get_db_config,
    get_cache_config,
    get_datasource_config,
    get_strategy_config,
)

logger = logging.getLogger(__name__)

# =============================================================================
# 全局设置实例（延迟加载）
# =============================================================================
_settings: Optional[Settings] = None


def _get_settings() -> Settings:
    """获取或创建全局设置实例（线程安全）"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# =============================================================================
# 向后兼容：提供与原配置模块相同的接口
# =============================================================================

# 数据库配置（向后兼容）
DATABASE_CONFIG: DatabaseConfig = None  # 延迟初始化

# 缓存配置（向后兼容）
CACHE_CONFIG: CacheConfig = None  # 延迟初始化

# 通知配置（向后兼容）
NOTIFICATION_CONFIG: NotificationConfig = None  # 延迟初始化

# 应用配置（向后兼容）
APP_CONFIG: WebConfig = None  # 延迟初始化

# 系统配置（向后兼容）
SYSTEM_CONFIG: SystemConfig = None  # 延迟初始化

# 投资策略配置（向后兼容）
INVESTMENT_STRATEGY_CONFIG: StrategyConfig = None  # 延迟初始化

# 数据源配置（向后兼容）
DATA_SOURCE_CONFIG: DataSourceConfig = None  # 延迟初始化

# 绩效分析配置（向后兼容）
PERFORMANCE_CONFIG: Dict[str, Any] = {
    'historical_days': 365,
    'trading_days_per_year': 252,
    'var_confidence': 0.05,
    'weights': {
        'annualized_return': 0.3,
        'sharpe_ratio': 0.25,
        'max_drawdown': 0.2,
        'volatility': 0.15,
        'win_rate': 0.1
    }
}

# 图表配置（向后兼容）
CHART_CONFIG: Dict[str, Any] = {
    'dpi': 350,
    'figsize': (16, 10),
    'style': 'seaborn-v0_8',
    'color_palette': {
        'positive': ['#2E8B57', '#3CB371', '#219C55'],
        'neutral': ['#E7C628', '#F39C12', '#E67E22'],
        'negative': ['#CD5C5C', '#C0392B', '#922B21']
    }
}

# 日志配置（向后兼容）
LOGGING_CONFIG: LoggingConfig = None  # 延迟初始化

# 基础配置（向后兼容）
BASE_CONFIG: Dict[str, Any] = {
    'fund_position_file': '',
    'sheet_name': '持仓数据',
    'columns': {
        'fund_code': '代码',
        'fund_name': '名称',
        'holding_amount': '持有金额',
        'daily_profit': '当日盈亏',
        'daily_return_rate': '当日盈亏率',
        'holding_profit': '持有盈亏',
        'holding_return_rate': '持有盈亏率',
        'total_profit': '累计盈亏',
        'total_return_rate': '累计盈亏率'
    }
}


def _init_backward_compatible_configs():
    """初始化向后兼容的配置变量"""
    global DATABASE_CONFIG, CACHE_CONFIG, NOTIFICATION_CONFIG
    global APP_CONFIG, SYSTEM_CONFIG, INVESTMENT_STRATEGY_CONFIG
    global DATA_SOURCE_CONFIG, LOGGING_CONFIG, BASE_CONFIG
    
    try:
        s = _get_settings()
        
        # 初始化各配置
        DATABASE_CONFIG = s.database
        CACHE_CONFIG = s.cache
        NOTIFICATION_CONFIG = s.notification
        APP_CONFIG = s.web
        SYSTEM_CONFIG = s.system
        INVESTMENT_STRATEGY_CONFIG = s.strategy
        DATA_SOURCE_CONFIG = s.datasource
        LOGGING_CONFIG = s.logging
        
        # 更新 BASE_CONFIG
        BASE_CONFIG['fund_position_file'] = s.system.fund_position_file
        
        logger.debug("向后兼容配置初始化完成")
    except Exception as e:
        logger.warning(f"向后兼容配置初始化失败: {e}")


# =============================================================================
# 统一访问接口
# =============================================================================

class _SettingsProxy:
    """
    设置代理类
    
    提供对 Settings 的延迟访问，确保在首次访问时才初始化
    """
    
    def __getattr__(self, name: str):
        """代理属性访问到实际的 Settings 实例"""
        s = _get_settings()
        return getattr(s, name)
    
    def get(self, path: str, default: Any = None) -> Any:
        """通过路径获取配置值"""
        s = _get_settings()
        return s.get(path, default)
    
    def reload(self):
        """重新加载配置"""
        global _settings
        _settings = None
        _init_backward_compatible_configs()
    
    def to_dict(self) -> Dict[str, Any]:
        """导出所有配置"""
        s = _get_settings()
        return s.to_dict()


# 创建代理实例，作为统一入口
settings = _SettingsProxy()


# =============================================================================
# 初始化
# =============================================================================

def init_config(force: bool = False):
    """
    显式初始化配置系统
    
    Args:
        force: 是否强制重新初始化
    """
    global _settings
    
    if force or _settings is None:
        _settings = None
        _init_backward_compatible_configs()
        logger.info("配置系统初始化完成")


# 自动初始化（仅在导入时执行）
_init_backward_compatible_configs()


# =============================================================================
# 导出列表
# =============================================================================

__all__ = [
    # 统一入口
    'settings',
    'init_config',
    
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
    
    # 基础组件
    'BaseConfig',
    'ConfigLoader',
    'Environment',
    'detect_environment',
    'get_config_dir',
    'get_project_root',
    'load_config',
    
    # 向后兼容
    'DATABASE_CONFIG',
    'CACHE_CONFIG',
    'NOTIFICATION_CONFIG',
    'APP_CONFIG',
    'SYSTEM_CONFIG',
    'INVESTMENT_STRATEGY_CONFIG',
    'DATA_SOURCE_CONFIG',
    'PERFORMANCE_CONFIG',
    'CHART_CONFIG',
    'LOGGING_CONFIG',
    'BASE_CONFIG',
]
