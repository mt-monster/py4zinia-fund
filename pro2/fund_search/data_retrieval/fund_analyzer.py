#!/usr/bin/env python
# coding: utf-8

"""
基金分析器模块
用于分析基金的各种指标，包括相关性分析
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from .enhanced_fund_data import EnhancedFundData
from .enhanced_database import EnhancedDatabaseManager
from shared.enhanced_config import DATABASE_CONFIG

logger = logging.getLogger(__name__)

class FundAnalyzer:
    """
    基金分析器类
    """
    
    def __init__(self, enable_cache: bool = True):
        """
        初始化基金分析器
        
        参数：
        enable_cache: 是否启用缓存机制
        """
        self.fund_data = EnhancedFundData()
        self.db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        self.enable_cache = enable_cache
        self._cache = {}  # 缓存相关性结果
        self._cache_time = {}  # 缓存时间
    
    def analyze_correlation(self, fund_codes: List[str], use_cache: bool = True, 
                          min_data_points: int = 30) -> Dict:
        """
        分析多只基金之间的相关性
        
        参数：
        fund_codes: 基金代码列表
        use_cache: 是否使用缓存
        min_data_points: 最少数据点数
        
        返回：
        dict: 包含相关性矩阵和基金信息的字典
        """
        try:
            logger.info(f"开始分析基金相关性: {fund_codes}")
            
            # 验证输入
            fund_codes = self._validate_fund_codes(fund_codes)
            
            # 检查缓存
            if use_cache and self.enable_cache:
                cache_key = tuple(sorted(fund_codes))
                if cache_key in self._cache:
                    cache_time = self._cache_time.get(cache_key)
                    if cache_time and (datetime.now() - cache_time).total_seconds() < 86400:
                        logger.info(f"使用缓存结果: {cache_key}")
                        return self._cache[cache_key]
            
            # 执行分析
            result = self._analyze_correlation_impl(fund_codes, min_data_points)
            
            # 保存到缓存
            if self.enable_cache:
                cache_key = tuple(sorted(fund_codes))
                self._cache[cache_key] = result
                self._cache_time[cache_key] = datetime.now()
            
            return result
            
        except Exception as e:
            logger.error(f"分析基金相关性失败: {e}")
            raise
    
    def _validate_fund_codes(self, fund_codes: List[str]) -> List[str]:
        """
        验证基金代码
        
        参数：
        fund_codes: 基金代码列表
        
        返回：
        list: 验证后的基金代码列表
        """
        # 检查重复
        original_count = len(fund_codes)
        fund_codes = list(set(fund_codes))
        if len(fund_codes) < original_count:
            logger.warning(f"基金代码中存在重复，已自动去重 ({original_count} -> {len(fund_codes)})")
        
        # 检查最少数量
        if len(fund_codes) < 2:
            raise ValueError("至少需要2只基金进行相关性分析")
        
        return fund_codes
    
    def _analyze_correlation_impl(self, fund_codes: List[str], 
                                 min_data_points: int = 30) -> Dict:
        """
        相关性分析的实现方法
        
        参数：
        fund_codes: 基金代码列表
        min_data_points: 最少数据点数
        
        返回：
        dict: 相关性分析结果
        """
        # 获取基金数据
        fund_data = {}
        fund_names = {}
        failed_codes = []
        
        for fund_code in fund_codes:
            try:
                # 获取基金名称
                fund_name = self._get_fund_name(fund_code)
                if not fund_name:
                    fund_info = self.fund_data.get_fund_basic_info(fund_code)
                    fund_name = fund_info.get('fund_name', fund_code)
                fund_names[fund_code] = fund_name
                
                # 获取历史数据
                nav_data = self.fund_data.get_historical_data(fund_code, days=365)
                
                if nav_data.empty:
                    failed_codes.append((fund_code, "无历史数据"))
                    logger.warning(f"基金 {fund_code} 无历史数据")
                    continue
                
                # 检查日收益率列
                if 'daily_return' not in nav_data.columns:
                    failed_codes.append((fund_code, "缺少日收益率数据"))
                    logger.warning(f"基金 {fund_code} 缺少日收益率数据")
                    continue
                
                # 清理数据：移除 NaN 和无穷大
                nav_data = nav_data.dropna(subset=['daily_return'])
                nav_data = nav_data[np.isfinite(nav_data['daily_return'])]
                
                # 检查数据点数
                if len(nav_data) < min_data_points:
                    failed_codes.append((fund_code, f"数据不足 ({len(nav_data)} < {min_data_points})"))
                    logger.warning(f"基金 {fund_code} 数据不足: {len(nav_data)} < {min_data_points}")
                    continue
                
                # 检查日收益率的合理性（不超过 ±100%）
                if (nav_data['daily_return'].abs() > 100).any():
                    logger.warning(f"基金 {fund_code} 存在异常收益率，已过滤")
                    nav_data = nav_data[nav_data['daily_return'].abs() <= 100]
                
                if len(nav_data) < min_data_points:
                    failed_codes.append((fund_code, "过滤后数据不足"))
                    continue
                
                # 保存数据
                fund_data[fund_code] = nav_data[['date', 'daily_return']].copy()
                logger.info(f"基金 {fund_code} 数据获取成功: {len(nav_data)} 个数据点")
                
            except Exception as e:
                failed_codes.append((fund_code, str(e)))
                logger.warning(f"处理基金 {fund_code} 失败: {e}")
        
        # 检查有效基金数量
        if len(fund_data) < 2:
            error_msg = f"有效基金数据不足2只，失败列表: {failed_codes}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 合并数据
        merged_df = None
        for fund_code, df in fund_data.items():
            df_renamed = df.rename(columns={'daily_return': fund_code})
            if merged_df is None:
                merged_df = df_renamed
            else:
                # 使用外连接保留所有日期
                merged_df = pd.merge(merged_df, df_renamed, on='date', how='outer')
        
        # 填充缺失值（使用前向填充和后向填充）
        merged_df = merged_df.fillna(method='ffill').fillna(method='bfill')
        
        # 再次检查是否有足够的数据
        if len(merged_df) < min_data_points:
            raise ValueError(f"合并后数据不足: {len(merged_df)} < {min_data_points}")
        
        # 计算相关性矩阵
        return_columns = list(fund_data.keys())
        correlation_matrix = merged_df[return_columns].corr().values.tolist()
        
        # 准备返回数据
        result = {
            'fund_codes': return_columns,
            'fund_names': [fund_names[code] for code in return_columns],
            'correlation_matrix': correlation_matrix,
            'data_points': len(merged_df),
            'failed_codes': failed_codes,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        logger.info(f"相关性分析完成，使用{len(merged_df)}个数据点，失败{len(failed_codes)}只基金")
        return result
    
    def _get_fund_name(self, fund_code: str) -> Optional[str]:
        """
        从数据库获取基金名称
        
        参数：
        fund_code: 基金代码
        
        返回：
        str: 基金名称，如果不存在则返回None
        """
        try:
            # 首先尝试从 fund_basic_info 表获取
            sql = "SELECT fund_name FROM fund_basic_info WHERE fund_code = :fund_code"
            result = self.db_manager.execute_query_raw(sql, {'fund_code': fund_code})
            if result and len(result) > 0 and result[0][0]:
                return result[0][0]
            
            # 如果 fund_basic_info 表中没有，尝试从 user_holdings 表获取
            sql = "SELECT fund_name FROM user_holdings WHERE fund_code = :fund_code LIMIT 1"
            result = self.db_manager.execute_query_raw(sql, {'fund_code': fund_code})
            if result and len(result) > 0 and result[0][0]:
                return result[0][0]
            
            # 如果 user_holdings 表中也没有，尝试从 fund_analysis_results 表获取
            sql = "SELECT fund_name FROM fund_analysis_results WHERE fund_code = :fund_code ORDER BY analysis_date DESC LIMIT 1"
            result = self.db_manager.execute_query_raw(sql, {'fund_code': fund_code})
            if result and len(result) > 0 and result[0][0]:
                return result[0][0]
            
            return None
        except Exception as e:
            logger.error(f"获取基金名称失败: {e}")
            return None
