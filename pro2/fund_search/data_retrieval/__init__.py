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
from .fetchers.optimized_fund_data import OptimizedFundData
from .fetchers.batch_fund_data_fetcher import BatchFundDataFetcher
from .utils.rate_limiter import RateLimiter, rate_limited, get_tushare_limiter

# 辅助函数
def batch_get_fund_data(fund_codes, **kwargs):
    """
    批量获取基金数据的辅助函数
    
    Args:
        fund_codes: 基金代码列表
        **kwargs: 传递给OptimizedFundData的参数
        
    Returns:
        dict: {fund_code: fund_data}
    """
    fetcher = OptimizedFundData(**kwargs)
    return fetcher.batch_get_fund_nav(fund_codes)

# 旧版本（保持兼容）
from .adapters.multi_source_adapter import MultiSourceDataAdapter
from services.fund_realtime import FundRealTime
from data_access.enhanced_database import EnhancedDatabaseManager
from services.notification import EnhancedNotificationManager

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
