#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
优化后的多数据源基金数据获取模块

主要优化:
1. 集成批量获取器，减少API调用次数
2. 添加速率限制，避免触发频率限制
3. 增强缓存策略
4. 智能降级处理

使用示例:
    from data_retrieval.optimized_fund_data import OptimizedFundData
    
    fetcher = OptimizedFundData(tushare_token="your_token")
    
    # 单只基金获取（自动使用批量接口优化）
    data = fetcher.get_fund_nav_history("000001")
    
    # 批量获取（高效）
    batch_data = fetcher.batch_get_fund_nav(["000001", "000002", "000003"])
"""

import pandas as pd
import numpy as np
import akshare as ak
import tushare as ts
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from functools import wraps

from .multi_source_fund_data import MultiSourceFundData, DataSourceHealth
from .batch_fund_data_fetcher import BatchFundDataFetcher
from .rate_limiter import get_tushare_limiter

logger = logging.getLogger(__name__)


class OptimizedFundData(MultiSourceFundData):
    """
    优化后的多数据源基金数据获取器
    
    继承自 MultiSourceFundData，添加了批量获取和速率限制功能
    """
    
    def __init__(self, tushare_token: Optional[str] = None, 
                 timeout: int = 10,
                 enable_batch: bool = True,
                 enable_rate_limit: bool = True):
        """
        初始化优化后的获取器
        
        Args:
            tushare_token: Tushare API token
            timeout: 请求超时时间
            enable_batch: 是否启用批量获取优化
            enable_rate_limit: 是否启用速率限制
        """
        super().__init__(tushare_token, timeout)
        
        self.enable_batch = enable_batch
        self.enable_rate_limit = enable_rate_limit
        
        # 批量获取器
        self.batch_fetcher = None
        if enable_batch and tushare_token:
            self.batch_fetcher = BatchFundDataFetcher(
                tushare_token=tushare_token,
                use_cache=True,
                max_workers=2  # 降低并发数以避免频率限制
            )
        
        # 待批量处理的队列
        self._pending_batch = []
        self._batch_lock = False
        
        logger.info(f"OptimizedFundData初始化完成 (批量优化: {enable_batch}, 速率限制: {enable_rate_limit})")
    
    def _get_nav_from_tushare(self, fund_code: str) -> pd.DataFrame:
        """
        从tushare获取净值历史（带速率限制）
        
        重写父类方法，添加速率控制
        """
        if not self.tushare_pro:
            raise ValueError("Tushare未初始化")
        
        # 应用速率限制
        if self.enable_rate_limit:
            limiter = get_tushare_limiter('fund_nav')
            limiter.wait_if_needed(timeout=65)
            limiter.record_call()
        
        start_time = time.time()
        
        try:
            df = self.tushare_pro.fund_nav(ts_code=fund_code)
            
            # 标准化列名
            column_mapping = {
                'nav_date': 'date',
                'unit_nav': 'nav',
                'accum_nav': 'accum_nav'
            }
            df = df.rename(columns=column_mapping)
            df['source'] = 'tushare'
            
            # 数据类型转换
            df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
            df['accum_nav'] = pd.to_numeric(df['accum_nav'], errors='coerce')
            
            # 计算日增长率
            if 'nv_daily_growth' in df.columns:
                df['daily_return'] = pd.to_numeric(df['nv_daily_growth'], errors='coerce')
            else:
                df = df.sort_values('date', ascending=True)
                df['daily_return'] = df['nav'].pct_change() * 100
                df = df.sort_values('date', ascending=False)
            
            elapsed = time.time() - start_time
            self.health.record_success('tushare', elapsed)
            
            logger.debug(f"从tushare获取 {fund_code} 历史净值 {len(df)} 条，耗时 {elapsed:.3f}s")
            return df
            
        except Exception as e:
            elapsed = time.time() - start_time
            self.health.record_fail('tushare', str(e))
            
            # 检查是否是频率限制错误
            if '最多访问' in str(e) or '频率' in str(e) or '80次' in str(e):
                logger.warning(f"触发Tushare频率限制，等待后重试: {e}")
                time.sleep(5)  # 等待5秒后重试
                return self._get_nav_from_tushare(fund_code)  # 递归重试
            
            logger.error(f"从tushare获取 {fund_code} 失败: {e}")
            raise
    
    def get_fund_nav_history(
        self, 
        fund_code: str, 
        source: str = 'auto',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        use_batch: bool = True
    ) -> pd.DataFrame:
        """
        获取基金历史净值（优化版本）
        
        Args:
            fund_code: 基金代码
            source: 数据源 ('akshare', 'tushare', 'auto')
            start_date: 开始日期
            end_date: 结束日期
            use_batch: 是否尝试使用批量接口
            
        Returns:
            DataFrame: 净值历史数据
        """
        # 如果启用批量优化且是单只基金查询，尝试使用批量接口
        if use_batch and self.batch_fetcher and source in ('auto', 'tushare'):
            try:
                results = self.batch_fetcher.batch_get_nav_history([fund_code])
                if fund_code in results:
                    df = results[fund_code]
                    
                    # 日期过滤
                    if start_date:
                        df = df[df['date'] >= start_date]
                    if end_date:
                        df = df[df['date'] <= end_date]
                    
                    logger.info(f"使用批量接口获取 {fund_code} 成功")
                    return df
            except Exception as e:
                logger.warning(f"批量接口获取失败，降级到单只获取: {e}")
        
        # 使用父类方法
        return super().get_fund_nav_history(fund_code, source, start_date, end_date)
    
    def batch_get_fund_nav(self, fund_codes: List[str], 
                          prefer_source: str = 'auto') -> Dict[str, pd.DataFrame]:
        """
        批量获取多只基金的历史净值
        
        这是主要的批量获取接口，会优先使用批量优化策略
        
        Args:
            fund_codes: 基金代码列表
            prefer_source: 优先数据源
            
        Returns:
            Dict[str, pd.DataFrame]: 基金代码 -> 历史数据
        """
        if not fund_codes:
            return {}
        
        logger.info(f"批量获取 {len(fund_codes)} 只基金数据")
        
        # 使用批量获取器
        if self.batch_fetcher and prefer_source in ('auto', 'tushare'):
            try:
                return self.batch_fetcher.batch_get_nav_history(fund_codes)
            except Exception as e:
                logger.warning(f"批量获取器失败: {e}")
        
        # 降级到逐个获取
        results = {}
        for code in fund_codes:
            try:
                df = self.get_fund_nav_history(code, source=prefer_source, use_batch=False)
                if not df.empty:
                    results[code] = df
            except Exception as e:
                logger.error(f"获取基金 {code} 失败: {e}")
        
        return results
    
    def batch_get_latest_nav(self, fund_codes: List[str]) -> Dict[str, Dict]:
        """
        批量获取多只基金的最新净值
        
        Args:
            fund_codes: 基金代码列表
            
        Returns:
            Dict[str, Dict]: 基金代码 -> 最新净值数据
        """
        if not self.batch_fetcher:
            # 降级到逐个获取
            results = {}
            for code in fund_codes:
                try:
                    data = self.get_fund_latest_nav(code)
                    if data:
                        results[code] = data
                except Exception as e:
                    logger.error(f"获取基金 {code} 最新净值失败: {e}")
            return results
        
        return self.batch_fetcher.batch_get_latest_nav(fund_codes)
    
    def preload_fund_data(self, fund_codes: Optional[List[str]] = None) -> bool:
        """
        预加载基金数据到缓存
        
        Args:
            fund_codes: 要预加载的基金代码列表，None表示加载全部
            
        Returns:
            bool: 是否成功
        """
        if not self.batch_fetcher:
            logger.warning("批量获取器未启用，无法预加载")
            return False
        
        try:
            if fund_codes is None:
                # 预加载全量数据
                self.batch_fetcher.preload_all_fund_nav(force_refresh=True)
            else:
                # 批量获取指定基金
                self.batch_fetcher.batch_get_nav_history(fund_codes)
            
            return True
        except Exception as e:
            logger.error(f"预加载数据失败: {e}")
            return False
    
    def get_optimized_stats(self) -> Dict:
        """获取优化后的统计信息"""
        stats = {
            'health': self.get_health_status(),
            'batch_enabled': self.enable_batch,
            'rate_limit_enabled': self.enable_rate_limit
        }
        
        if self.batch_fetcher:
            stats['batch_stats'] = self.batch_fetcher.get_stats()
        
        if self.enable_rate_limit:
            stats['rate_limits'] = {
                'fund_nav': get_tushare_limiter('fund_nav').get_stats()
            }
        
        return stats


# 便捷函数
def get_optimized_fund_data(tushare_token: Optional[str] = None) -> OptimizedFundData:
    """
    获取优化后的基金数据获取器实例
    
    Args:
        tushare_token: Tushare API token
        
    Returns:
        OptimizedFundData: 优化后的获取器实例
    """
    return OptimizedFundData(
        tushare_token=tushare_token,
        enable_batch=True,
        enable_rate_limit=True
    )


# 向后兼容的批量获取函数
def batch_get_fund_data(fund_codes: List[str], 
                       tushare_token: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """
    批量获取基金数据的便捷函数
    
    Args:
        fund_codes: 基金代码列表
        tushare_token: Tushare token
        
    Returns:
        Dict[str, pd.DataFrame]: 基金代码 -> 历史数据
    """
    fetcher = get_optimized_fund_data(tushare_token)
    return fetcher.batch_get_fund_nav(fund_codes)


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("优化后的基金数据获取器测试")
    print("=" * 60)
    
    test_funds = ['000001', '000002', '021539', '100055']
    
    fetcher = OptimizedFundData()
    
    # 测试批量获取
    print("\n测试批量获取:")
    batch_results = fetcher.batch_get_fund_nav(test_funds)
    for code, df in batch_results.items():
        print(f"  {code}: {len(df)} 条数据")
    
    # 测试统计
    print(f"\n统计信息: {fetcher.get_optimized_stats()}")
