#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一基金数据服务
提供统一的数据获取接口，自动处理数据源降级，集成缓存
"""

import time
import pandas as pd
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import logging

from data_retrieval.adapters import AkshareAdapter, SinaAdapter
from data_retrieval.adapters.base import BaseDataSourceAdapter
from .cache import fund_cache

logger = logging.getLogger(__name__)


@dataclass
class FundRealtimeData:
    """基金实时数据 DTO"""
    fund_code: str
    fund_name: Optional[str] = None
    current_nav: Optional[float] = None
    yesterday_nav: Optional[float] = None
    daily_return: Optional[float] = None
    estimate_nav: Optional[float] = None
    estimate_return: Optional[float] = None
    data_source: str = ''
    update_time: Optional[datetime] = None


class FundDataService:
    """
    统一基金数据服务
    
    协调多个数据源适配器，提供自动降级机制
    集成缓存层，提高数据获取性能
    消除原先分散在各处的重复数据获取逻辑
    """
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.adapters: Dict[str, BaseDataSourceAdapter] = {
            'akshare': AkshareAdapter(),
            'sina': SinaAdapter()
        }
        
        # 数据源优先级（按顺序尝试）
        self.source_priority = ['akshare', 'sina']
        
        # 缓存实例
        self.cache = fund_cache
        
        self.logger = logging.getLogger(__name__)
        self._initialized = True
        
        self.logger.info("基金数据服务初始化完成（含缓存）")
    
    def get_fund_nav_history(
        self, 
        fund_code: str, 
        days: int = 365,
        preferred_source: str = 'akshare',
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        获取基金历史净值（带缓存）
        
        优先从缓存获取，缓存未命中时从数据源获取
        支持自动降级和缓存写入
        
        Args:
            fund_code: 基金代码
            days: 获取天数
            preferred_source: 首选数据源
            use_cache: 是否使用缓存（默认True）
            
        Returns:
            DataFrame: 净值历史数据
        """
        # 1. 尝试从缓存获取
        if use_cache:
            cached_df = self.cache.get_nav_history(fund_code, days)
            if cached_df is not None and not cached_df.empty:
                self.logger.debug(f"缓存命中: {fund_code} 净值历史 ({days}天)")
                return cached_df
        
        # 2. 从数据源获取
        sources_to_try = [preferred_source] + [
            s for s in self.source_priority if s != preferred_source
        ]
        
        for source_name in sources_to_try:
            adapter = self.adapters.get(source_name)
            if not adapter:
                continue
            
            try:
                self.logger.debug(f"尝试从 {source_name} 获取基金 {fund_code} 净值历史")
                df = adapter.get_fund_nav_history(fund_code, days)
                
                if not df.empty:
                    # 写入缓存
                    if use_cache:
                        self.cache.set_nav_history(fund_code, days, df)
                    
                    source_label = "首选" if source_name == preferred_source else "降级"
                    self.logger.info(f"{source_label}: 从 {source_name} 获取基金 {fund_code} 净值历史成功，共 {len(df)} 条")
                    return df
                    
            except Exception as e:
                self.logger.warning(f"从 {source_name} 获取基金 {fund_code} 净值历史失败: {e}")
                continue
        
        self.logger.error(f"无法从任何数据源获取基金 {fund_code} 的净值历史")
        return pd.DataFrame()
    
    def get_realtime_data(
        self, 
        fund_code: str,
        use_cache: bool = True
    ) -> FundRealtimeData:
        """
        获取实时数据（带缓存）
        
        组合多个数据源的数据，优先使用新浪实时数据
        
        Args:
            fund_code: 基金代码
            use_cache: 是否使用缓存（默认True，缓存5分钟）
            
        Returns:
            FundRealtimeData: 实时数据对象
        """
        # 尝试从缓存获取
        if use_cache:
            cached_data = self.cache.get_realtime_data(fund_code)
            if cached_data:
                self.logger.debug(f"缓存命中: {fund_code} 实时数据")
                return FundRealtimeData(
                    fund_code=fund_code,
                    **cached_data
                )
        
        # 从数据源获取
        dto = FundRealtimeData(fund_code=fund_code, update_time=datetime.now())
        
        # 优先获取新浪实时数据
        sina_data = self.adapters['sina'].get_realtime_data(fund_code)
        if sina_data:
            dto.fund_name = sina_data.get('fund_name')
            dto.current_nav = sina_data.get('today_nav')
            dto.yesterday_nav = sina_data.get('yesterday_nav')
            dto.daily_return = sina_data.get('daily_growth')
            dto.estimate_nav = sina_data.get('estimate_nav')
            dto.estimate_return = sina_data.get('estimate_growth')
            dto.data_source = 'sina'
            self.logger.debug(f"从新浪获取基金 {fund_code} 实时数据成功")
        else:
            # 回退到 akshare
            akshare_data = self.adapters['akshare'].get_realtime_data(fund_code)
            if akshare_data:
                dto.current_nav = akshare_data.get('current_nav')
                dto.daily_return = akshare_data.get('daily_growth')
                dto.data_source = akshare_data.get('data_source', 'akshare')
                self.logger.debug(f"从akshare获取基金 {fund_code} 实时数据成功")
        
        # 写入缓存
        if use_cache:
            cache_data = {
                'fund_name': dto.fund_name,
                'current_nav': dto.current_nav,
                'yesterday_nav': dto.yesterday_nav,
                'daily_return': dto.daily_return,
                'estimate_nav': dto.estimate_nav,
                'estimate_return': dto.estimate_return,
                'data_source': dto.data_source,
                'update_time': dto.update_time
            }
            self.cache.set_realtime_data(fund_code, cache_data)
        
        return dto
    
    def get_fund_basic_info(
        self, 
        fund_code: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        获取基金基本信息（带缓存）
        
        Args:
            fund_code: 基金代码
            use_cache: 是否使用缓存（默认True，缓存1天）
            
        Returns:
            Dict: 基金基本信息
        """
        # 尝试从缓存获取
        if use_cache:
            cached_info = self.cache.get_basic_info(fund_code)
            if cached_info:
                self.logger.debug(f"缓存命中: {fund_code} 基本信息")
                return cached_info
        
        # 从数据源获取
        info = self.adapters['akshare'].get_fund_basic_info(fund_code)
        
        # 写入缓存
        if use_cache and info:
            self.cache.set_basic_info(fund_code, info)
        
        return info
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        获取所有数据源的健康状态
        
        Returns:
            Dict: 各数据源的健康状态
        """
        return {
            name: adapter.get_health_status()
            for name, adapter in self.adapters.items()
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict: 缓存统计信息
        """
        return self.cache.get_stats()
    
    def get_best_available_source(self) -> str:
        """
        获取当前最佳可用数据源
        
        Returns:
            str: 数据源名称
        """
        for source in self.source_priority:
            adapter = self.adapters.get(source)
            if adapter and adapter.is_available():
                return source
        return self.source_priority[0]  # 默认返回第一个


# 全局服务实例
fund_data_service = FundDataService()
