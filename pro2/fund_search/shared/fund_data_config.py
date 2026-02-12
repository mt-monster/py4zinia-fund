#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金数据获取统一配置

集中管理基金数据获取的相关配置，包括：
- API速率限制配置
- 缓存策略配置
- 数据源优先级配置
- 批量获取配置

使用示例:
    from shared.fund_data_config import FundDataConfig
    
    # 获取配置
    config = FundDataConfig()
    
    # 使用配置创建获取器
    fetcher = OptimizedFundData(
        tushare_token=config.tushare_token,
        enable_batch=config.enable_batch,
        enable_rate_limit=config.enable_rate_limit
    )
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class RateLimitConfig:
    """速率限制配置"""
    max_calls: int = 75          # 每分钟最大调用次数（留有余量，避免正好触发80次限制）
    period: int = 60             # 时间周期（秒）
    timeout: float = 65.0        # 最大等待时间（秒）
    retry_delay: float = 5.0     # 触发限制后的重试等待时间（秒）


@dataclass
class CacheConfig:
    """缓存配置"""
    # 内存缓存TTL（秒）
    memory_ttl: Dict[str, int] = field(default_factory=lambda: {
        'latest_nav': 900,           # 15分钟
        'nav_history': 3600,         # 1小时
        'fund_basic': 86400,         # 1天
        'performance': 3600,         # 1小时
        'yesterday_return': 900,     # 15分钟
    })
    
    # 数据库缓存TTL（秒）
    db_ttl: Dict[str, int] = field(default_factory=lambda: {
        'latest_nav': 1800,          # 30分钟
        'nav_history': 86400,        # 1天
        'fund_basic': 604800,        # 7天
        'performance': 86400,        # 1天
    })
    
    # 缓存清理配置
    max_memory_cache_size: int = 1000    # 最大内存缓存条目数
    cleanup_batch_size: int = 100        # 每次清理的条目数


@dataclass
class BatchConfig:
    """批量获取配置"""
    enabled: bool = True             # 是否启用批量获取
    max_workers: int = 2             # 并行线程数（降低以避免频率限制）
    chunk_size: int = 100            # 每批处理的基金数量
    preload_on_startup: bool = False # 启动时是否预加载全量数据
    preload_fund_codes: Optional[list] = None  # 预加载的基金代码列表


@dataclass
class DataSourcePriority:
    """数据源优先级配置"""
    # 历史净值获取优先级
    nav_history_priority: list = field(default_factory=lambda: [
        'tushare_bulk',  # Tushare批量接口（优化后）
        'tushare',       # Tushare单只接口
        'akshare',       # Akshare接口
        'sina',          # 新浪接口
    ])
    
    # 实时数据获取优先级
    realtime_priority: list = field(default_factory=lambda: [
        'sina',          # 新浪实时数据
        'akshare',       # Akshare实时数据
        'tushare',       # Tushare数据
    ])
    
    # 基金基本信息获取优先级
    basic_info_priority: list = field(default_factory=lambda: [
        'akshare',       # Akshare基本信息
        'tushare',       # Tushare基本信息
    ])


class FundDataConfig:
    """
    基金数据获取统一配置类
    
    集中管理所有与基金数据获取相关的配置
    """
    
    # 默认Tushare Token（从环境变量或配置文件获取）
    DEFAULT_TUSHARE_TOKEN = os.getenv(
        'TUSHARE_TOKEN',
        '5ff19facae0e5b26a407d491d33707a9884a39a714a0d76b6495725b'
    )
    
    def __init__(self, 
                 tushare_token: Optional[str] = None,
                 enable_batch: bool = True,
                 enable_rate_limit: bool = True,
                 enable_cache: bool = True):
        """
        初始化配置
        
        Args:
            tushare_token: Tushare API Token
            enable_batch: 是否启用批量获取优化
            enable_rate_limit: 是否启用API速率限制
            enable_cache: 是否启用缓存
        """
        # API配置
        self.tushare_token = tushare_token or self.DEFAULT_TUSHARE_TOKEN
        self.request_timeout = 30
        
        # 功能开关
        self.enable_batch = enable_batch
        self.enable_rate_limit = enable_rate_limit
        self.enable_cache = enable_cache
        
        # 子配置
        self.rate_limit = RateLimitConfig()
        self.cache = CacheConfig()
        self.batch = BatchConfig()
        self.priority = DataSourcePriority()
        
        # 根据Tushare账号等级调整速率限制
        self._adjust_rate_limit_by_account()
    
    def _adjust_rate_limit_by_account(self):
        """根据Tushare账号等级调整配置"""
        # 可以通过token识别账号等级，这里使用默认配置
        # 免费版: 80次/分钟
        # 标准版: 根据实际权限调整
        # 高级版: 根据实际权限调整
        pass
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'tushare_token': self.tushare_token[:10] + '...' if self.tushare_token else None,
            'request_timeout': self.request_timeout,
            'enable_batch': self.enable_batch,
            'enable_rate_limit': self.enable_rate_limit,
            'enable_cache': self.enable_cache,
            'rate_limit': {
                'max_calls': self.rate_limit.max_calls,
                'period': self.rate_limit.period,
            },
            'batch': {
                'enabled': self.batch.enabled,
                'max_workers': self.batch.max_workers,
                'chunk_size': self.batch.chunk_size,
            }
        }
    
    @classmethod
    def from_env(cls) -> 'FundDataConfig':
        """从环境变量创建配置"""
        return cls(
            tushare_token=os.getenv('TUSHARE_TOKEN'),
            enable_batch=os.getenv('FUND_DATA_ENABLE_BATCH', 'true').lower() == 'true',
            enable_rate_limit=os.getenv('FUND_DATA_ENABLE_RATE_LIMIT', 'true').lower() == 'true',
            enable_cache=os.getenv('FUND_DATA_ENABLE_CACHE', 'true').lower() == 'true'
        )
    
    @classmethod
    def development(cls) -> 'FundDataConfig':
        """开发环境配置（禁用部分优化以便调试）"""
        return cls(
            enable_batch=True,
            enable_rate_limit=True,
            enable_cache=True
        )
    
    @classmethod
    def production(cls) -> 'FundDataConfig':
        """生产环境配置（全部优化启用）"""
        return cls(
            enable_batch=True,
            enable_rate_limit=True,
            enable_cache=True
        )
    
    @classmethod
    def high_performance(cls) -> 'FundDataConfig':
        """高性能配置（激进的优化策略）"""
        config = cls(
            enable_batch=True,
            enable_rate_limit=True,
            enable_cache=True
        )
        # 调整批量配置
        config.batch.max_workers = 3
        config.batch.preload_on_startup = True
        # 调整缓存配置
        config.cache.memory_ttl['latest_nav'] = 600  # 10分钟
        return config


# 全局配置实例
_config_instance: Optional[FundDataConfig] = None


def get_config() -> FundDataConfig:
    """
    获取全局配置实例（单例模式）
    
    Returns:
        FundDataConfig: 全局配置实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = FundDataConfig.from_env()
    return _config_instance


def set_config(config: FundDataConfig):
    """
    设置全局配置实例
    
    Args:
        config: 配置实例
    """
    global _config_instance
    _config_instance = config


# 便捷函数
def get_fund_data_config() -> FundDataConfig:
    """获取基金数据配置的便捷函数"""
    return get_config()
