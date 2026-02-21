"""
数据获取模块 (已优化)

该模块包含所有与基金数据获取相关的功能：
- 实时基金数据获取
- 历史数据获取
- 数据库操作
- 通知服务
- 数据字段映射

优化版本特性：
- 批量数据获取 - 减少API调用次数
- API速率限制 - 避免触发频率限制
- 多级缓存策略 - 提升响应速度
"""

# 新版本（推荐）
from .optimized_fund_data import OptimizedFundData, batch_get_fund_data
from .batch_fund_data_fetcher import BatchFundDataFetcher
from .rate_limiter import RateLimiter, rate_limited, get_tushare_limiter

# 旧版本（保持兼容）
from .multi_source_adapter import MultiSourceDataAdapter
from .fund_realtime import FundRealTime
from .enhanced_database import EnhancedDatabaseManager
from .enhanced_notification import EnhancedNotificationManager

# 向后兼容：MultiSourceFundData 现在指向 OptimizedFundData
MultiSourceFundData = OptimizedFundData

__all__ = [
    # 新版本（推荐）
    'OptimizedFundData',
    'BatchFundDataFetcher',
    'batch_get_fund_data',
    'RateLimiter',
    'rate_limited',
    'get_tushare_limiter',
    
    # 旧版本（保持兼容）
    'MultiSourceDataAdapter',
    'MultiSourceFundData',  # 向后兼容别名
    'FundRealTime',
    'EnhancedDatabaseManager',
    'EnhancedNotificationManager'
]
