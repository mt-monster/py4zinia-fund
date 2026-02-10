#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据源适配器基类
定义所有数据源适配器的通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import logging


@dataclass
class DataSourceHealth:
    """数据源健康状态"""
    success_count: int = 0
    fail_count: int = 0
    total_response_time: float = 0.0
    last_success: Optional[datetime] = None
    last_fail: Optional[datetime] = None
    last_error: Optional[str] = None
    
    @property
    def total_calls(self) -> int:
        return self.success_count + self.fail_count
    
    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return self.success_count / self.total_calls
    
    @property
    def avg_response_time(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_response_time / self.total_calls
    
    def record_success(self, response_time: float):
        """记录成功调用"""
        self.success_count += 1
        self.total_response_time += response_time
        self.last_success = datetime.now()
    
    def record_fail(self, error: str):
        """记录失败调用"""
        self.fail_count += 1
        self.last_fail = datetime.now()
        self.last_error = error


class BaseDataSourceAdapter(ABC):
    """
    数据源适配器基类
    
    所有数据源适配器必须继承此类，实现标准接口
    """
    
    def __init__(self, name: str, timeout: int = 10):
        """
        初始化适配器
        
        Args:
            name: 适配器名称
            timeout: 请求超时时间（秒）
        """
        self.name = name
        self.timeout = timeout
        self.health = DataSourceHealth()
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def get_fund_nav_history(
        self, 
        fund_code: str, 
        days: int = 365,
        **kwargs
    ) -> pd.DataFrame:
        """
        获取基金历史净值
        
        Args:
            fund_code: 基金代码
            days: 获取天数
            **kwargs: 额外参数
            
        Returns:
            DataFrame: 包含净值历史的DataFrame
                      列: date, nav, accum_nav, daily_return
        """
        pass
    
    @abstractmethod
    def get_fund_basic_info(self, fund_code: str) -> Dict[str, Any]:
        """
        获取基金基本信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            Dict: 基金基本信息字典
        """
        pass
    
    def get_realtime_data(self, fund_code: str) -> Dict[str, Any]:
        """
        获取实时数据（可选实现）
        
        Args:
            fund_code: 基金代码
            
        Returns:
            Dict: 实时数据字典，不支持返回空字典
        """
        return {}
    
    def is_available(self) -> bool:
        """
        检查数据源是否可用
        
        Returns:
            bool: 数据源是否健康
        """
        return self.health.success_rate >= 0.5
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        获取健康状态
        
        Returns:
            Dict: 健康状态信息
        """
        return {
            'name': self.name,
            'available': self.is_available(),
            'success_rate': self.health.success_rate,
            'avg_response_time': self.health.avg_response_time,
            'total_calls': self.health.total_calls,
            'last_success': self.health.last_success,
            'last_fail': self.health.last_fail,
            'last_error': self.health.last_error
        }
    
    def _standardize_nav_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化净值DataFrame
        
        Args:
            df: 原始DataFrame
            
        Returns:
            标准化后的DataFrame
        """
        from ..constants import FUND_NAV_COLUMN_MAPPING
        
        if df.empty:
            return df
        
        # 重命名列
        existing_mapping = {
            k: v for k, v in FUND_NAV_COLUMN_MAPPING.items() 
            if k in df.columns
        }
        if existing_mapping:
            df = df.rename(columns=existing_mapping)
        
        # 确保数值列的类型正确
        numeric_columns = ['nav', 'accum_nav', 'daily_return']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
