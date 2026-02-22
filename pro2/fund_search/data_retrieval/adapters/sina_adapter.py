#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
新浪实时数据适配器
提供基金实时估算数据的获取
"""

import time
import requests
from typing import Dict, Any, Optional
import pandas as pd
import logging

from .base import BaseDataSourceAdapter
from data_retrieval.utils.constants import SINA_REALTIME_FIELD_MAPPING

logger = logging.getLogger(__name__)


class SinaAdapter(BaseDataSourceAdapter):
    """
    新浪实时数据适配器
    
    提供基金实时净值、估算数据等信息的获取
    """
    
    def __init__(self, timeout: int = 10):
        super().__init__('sina', timeout)
        self.base_url = "https://hq.sinajs.cn/list=f_{}"
        self.headers = {
            'Referer': 'https://finance.sina.com.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self._session = None  # 延迟创建session
    
    def _get_session(self) -> requests.Session:
        """获取或创建会话"""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(self.headers)
        return self._session
    
    def get_realtime_data(self, fund_code: str) -> Dict[str, Any]:
        """
        获取实时数据
        
        Args:
            fund_code: 基金代码
            
        Returns:
            Dict: 实时数据
        """
        start_time = time.time()
        
        try:
            url = self.base_url.format(fund_code)
            session = self._get_session()
            
            response = session.get(url, timeout=self.timeout)
            response.encoding = 'gbk'
            
            data = self._parse_sina_response(response.text)
            
            if data:
                response_time = time.time() - start_time
                self.health.record_success(response_time)
                data['data_source'] = 'sina'
                self.logger.debug(f"成功获取基金 {fund_code} 实时数据")
            
            return data
            
        except Exception as e:
            response_time = time.time() - start_time
            self.health.record_fail(str(e))
            self.logger.error(f"获取基金 {fund_code} 实时数据失败: {e}")
            return {}
    
    def _parse_sina_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析新浪响应
        
        Args:
            response_text: 响应文本
            
        Returns:
            Dict: 解析后的数据
        """
        if not response_text or 'var hq_str_f_' not in response_text:
            return {}
        
        # 提取数据部分
        start = response_text.find('"') + 1
        end = response_text.rfind('"')
        
        if start <= 0 or end <= start:
            return {}
        
        fields = response_text[start:end].split(',')
        
        if len(fields) < 5:
            return {}
        
        # 解析字段
        result = {}
        
        # 基金名称
        result['fund_name'] = fields[0].strip() if fields[0] else None
        
        # 今日净值
        try:
            result['today_nav'] = float(fields[1]) if fields[1] else None
        except (ValueError, TypeError):
            result['today_nav'] = None
        
        # 昨日净值
        try:
            result['yesterday_nav'] = float(fields[2]) if fields[2] else None
        except (ValueError, TypeError):
            result['yesterday_nav'] = None
        
        # 日增长率
        try:
            result['daily_growth'] = float(fields[3]) if fields[3] else None
        except (ValueError, TypeError):
            result['daily_growth'] = None
        
        # 日期
        result['date'] = fields[4].strip() if len(fields) > 4 else None
        
        # 估算净值和增长率（可能不存在）
        if len(fields) > 6:
            try:
                result['estimate_nav'] = float(fields[5]) if fields[5] else None
            except (ValueError, TypeError):
                result['estimate_nav'] = None
            
            try:
                result['estimate_growth'] = float(fields[6]) if fields[6] else None
            except (ValueError, TypeError):
                result['estimate_growth'] = None
        
        return result
    
    def get_fund_nav_history(self, fund_code: str, days: int = 365, **kwargs) -> pd.DataFrame:
        """
        新浪不提供历史数据，返回空DataFrame
        
        Returns:
            pd.DataFrame: 空DataFrame
        """
        return pd.DataFrame()
    
    def get_fund_basic_info(self, fund_code: str) -> Dict[str, Any]:
        """
        新浪不提供基本信息，返回空字典
        
        Returns:
            Dict: 空字典
        """
        return {}
    
    def close(self):
        """关闭会话"""
        if self._session:
            self._session.close()
            self._session = None
