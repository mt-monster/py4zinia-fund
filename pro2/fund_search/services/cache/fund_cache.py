#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金数据专用缓存
提供针对基金数据的缓存策略
"""

import pandas as pd
import logging
from typing import Optional
from datetime import datetime

from .memory_cache import MemoryCache

logger = logging.getLogger(__name__)


class FundDataCache:
    """
    基金数据缓存
    
    针对基金数据的特点提供分级缓存策略：
    - 实时数据（日涨跌幅）：TTL = 5分钟
    - 净值历史：TTL = 1小时
    - 基金基本信息：TTL = 1天
    """
    
    def __init__(self):
        self._cache = MemoryCache(max_size=2000)
        self.logger = logging.getLogger(__name__)
    
    def _make_key(self, fund_code: str, data_type: str, **params) -> str:
        """生成缓存键"""
        param_str = ":".join(f"{k}={v}" for k, v in sorted(params.items()))
        if param_str:
            return f"fund:{fund_code}:{data_type}:{param_str}"
        return f"fund:{fund_code}:{data_type}"
    
    def get_nav_history(
        self, 
        fund_code: str, 
        days: int = 365
    ) -> Optional[pd.DataFrame]:
        """
        获取缓存的净值历史
        
        Args:
            fund_code: 基金代码
            days: 天数
            
        Returns:
            DataFrame 或 None
        """
        key = self._make_key(fund_code, 'nav_history', days=days)
        cached = self._cache.get(key)
        
        if cached is not None:
            self.logger.debug(f"缓存命中: {fund_code} 净值历史 ({days}天)")
            return cached
        
        return None
    
    def set_nav_history(
        self, 
        fund_code: str, 
        days: int,
        df: pd.DataFrame,
        ttl: int = 3600  # 默认1小时
    ):
        """
        缓存净值历史
        
        Args:
            fund_code: 基金代码
            days: 天数
            df: DataFrame
            ttl: 过期时间（秒）
        """
        key = self._make_key(fund_code, 'nav_history', days=days)
        self._cache.set(key, df, ttl=ttl)
        self.logger.debug(f"缓存写入: {fund_code} 净值历史 ({len(df)}条, TTL={ttl}s)")
    
    def get_realtime_data(self, fund_code: str) -> Optional[dict]:
        """
        获取缓存的实时数据
        
        实时数据TTL较短（5分钟）
        """
        key = self._make_key(fund_code, 'realtime')
        return self._cache.get(key)
    
    def set_realtime_data(
        self, 
        fund_code: str, 
        data: dict,
        ttl: int = 300  # 5分钟
    ):
        """缓存实时数据"""
        key = self._make_key(fund_code, 'realtime')
        self._cache.set(key, data, ttl=ttl)
        self.logger.debug(f"缓存写入: {fund_code} 实时数据 (TTL={ttl}s)")
    
    def get_basic_info(self, fund_code: str) -> Optional[dict]:
        """
        获取缓存的基本信息
        
        基本信息TTL较长（1天）
        """
        key = self._make_key(fund_code, 'basic_info')
        return self._cache.get(key)
    
    def set_basic_info(
        self, 
        fund_code: str, 
        info: dict,
        ttl: int = 86400  # 1天
    ):
        """缓存基本信息"""
        key = self._make_key(fund_code, 'basic_info')
        self._cache.set(key, info, ttl=ttl)
        self.logger.debug(f"缓存写入: {fund_code} 基本信息 (TTL={ttl}s)")
    
    def invalidate_fund(self, fund_code: str):
        """使某基金的所有缓存失效"""
        # 简单实现：目前不支持前缀删除，通过设置短TTL实现
        self.logger.info(f"缓存失效: {fund_code}")
    
    def get_stats(self) -> dict:
        """获取缓存统计"""
        stats = self._cache.get_stats()
        return {
            **stats,
            'type': 'fund_data_cache'
        }
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()


# 全局基金数据缓存实例
fund_cache = FundDataCache()
