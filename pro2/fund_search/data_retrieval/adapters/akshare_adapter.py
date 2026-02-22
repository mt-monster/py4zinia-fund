#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Akshare 数据源适配器
提供对东方财富数据的统一访问接口
"""

import time
from typing import Dict, Any, Optional
import pandas as pd
import logging

from .base import BaseDataSourceAdapter
from data_retrieval.utils.constants import DEFAULT_RETRY_TIMES, DEFAULT_RETRY_DELAY

logger = logging.getLogger(__name__)


class AkshareAdapter(BaseDataSourceAdapter):
    """
    Akshare 数据源适配器
    
    提供基金净值历史、基本信息等数据的获取
    """
    
    def __init__(self, timeout: int = 15, max_retries: int = DEFAULT_RETRY_TIMES):
        super().__init__('akshare', timeout)
        self.max_retries = max_retries
        self._akshare = None  # 延迟加载
    
    def _get_akshare(self):
        """延迟加载 akshare 模块"""
        if self._akshare is None:
            import akshare as ak
            self._akshare = ak
        return self._akshare
    
    def get_fund_nav_history(
        self, 
        fund_code: str, 
        days: int = 365,
        **kwargs
    ) -> pd.DataFrame:
        """
        获取基金历史净值（带重试机制）
        
        Args:
            fund_code: 基金代码
            days: 获取天数
            
        Returns:
            DataFrame: 净值历史数据
        """
        ak = self._get_akshare()
        
        for attempt in range(self.max_retries):
            start_time = time.time()
            try:
                self.logger.debug(f"获取基金 {fund_code} 净值历史 (尝试 {attempt + 1}/{self.max_retries})")
                
                df = ak.fund_open_fund_info_em(
                    symbol=fund_code, 
                    indicator='单位净值走势',
                    period='最大值'
                )
                
                if df is None or df.empty:
                    self.logger.warning(f"基金 {fund_code} 返回空数据")
                    return pd.DataFrame()
                
                # 标准化处理
                df = self._standardize_nav_df(df)
                
                # 限制天数
                if days and len(df) > days:
                    df = df.tail(days).reset_index(drop=True)
                
                # 记录成功
                response_time = time.time() - start_time
                self.health.record_success(response_time)
                
                self.logger.info(f"成功获取基金 {fund_code} 净值历史，共 {len(df)} 条记录")
                return df
                
            except Exception as e:
                response_time = time.time() - start_time
                error_msg = str(e)
                self.health.record_fail(error_msg)
                
                if attempt < self.max_retries - 1:
                    sleep_time = DEFAULT_RETRY_DELAY * (2 ** attempt)  # 指数退避
                    self.logger.warning(f"获取失败 (尝试 {attempt + 1}): {error_msg}，{sleep_time}秒后重试")
                    time.sleep(sleep_time)
                else:
                    self.logger.error(f"获取基金 {fund_code} 净值历史失败（已重试{self.max_retries}次）: {error_msg}")
        
        return pd.DataFrame()
    
    def get_fund_basic_info(self, fund_code: str) -> Dict[str, Any]:
        """
        获取基金基本信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            Dict: 基金基本信息
        """
        ak = self._get_akshare()
        start_time = time.time()
        
        try:
            self.logger.debug(f"获取基金 {fund_code} 基本信息")
            
            fund_info = ak.fund_open_fund_info_em(
                symbol=fund_code, 
                indicator="基本信息"
            )
            
            if fund_info is None or fund_info.empty:
                return {}
            
            # 转换为字典
            info_dict = {}
            for _, row in fund_info.iterrows():
                item = row.get('项目', '')
                value = row.get('数值', '')
                if item:
                    info_dict[item] = value
            
            # 记录成功
            response_time = time.time() - start_time
            self.health.record_success(response_time)
            
            return info_dict
            
        except Exception as e:
            response_time = time.time() - start_time
            self.health.record_fail(str(e))
            self.logger.error(f"获取基金 {fund_code} 基本信息失败: {e}")
            return {}
    
    def get_realtime_data(self, fund_code: str) -> Dict[str, Any]:
        """
        获取实时估算数据
        
        Args:
            fund_code: 基金代码
            
        Returns:
            Dict: 实时估算数据
        """
        ak = self._get_akshare()
        start_time = time.time()
        
        try:
            # 尝试获取实时估算
            try:
                df = ak.fund_etf_daily_em(symbol=fund_code)
                if not df.empty:
                    latest = df.iloc[-1]
                    response_time = time.time() - start_time
                    self.health.record_success(response_time)
                    return {
                        'current_nav': float(latest.get('收盘价', 0)),
                        'daily_growth': float(latest.get('涨跌幅', 0)),
                        'data_source': 'akshare_realtime'
                    }
            except:
                pass
            
            # 回退到最新净值
            nav_df = self.get_fund_nav_history(fund_code, days=1)
            if not nav_df.empty:
                latest = nav_df.iloc[-1]
                return {
                    'current_nav': latest.get('nav'),
                    'daily_growth': latest.get('daily_return'),
                    'data_source': 'akshare_nav'
                }
            
            return {}
            
        except Exception as e:
            response_time = time.time() - start_time
            self.health.record_fail(str(e))
            self.logger.error(f"获取基金 {fund_code} 实时数据失败: {e}")
            return {}
    
    def get_fund_list(self) -> pd.DataFrame:
        """
        获取基金列表
        
        Returns:
            DataFrame: 基金列表
        """
        ak = self._get_akshare()
        
        try:
            df = ak.fund_name_em()
            return df
        except Exception as e:
            self.logger.error(f"获取基金列表失败: {e}")
            return pd.DataFrame()
