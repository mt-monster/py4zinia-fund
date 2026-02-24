#!/usr/bin/env python
# coding: utf-8

"""
基金分析器模块
用于分析基金的各种指标，包括相关性分析

时间统计功能：记录各阶段耗时并输出优化状态报告
"""

import logging
import time
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from ..data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
from ..data_access.enhanced_database import EnhancedDatabaseManager
from shared.enhanced_config import DATABASE_CONFIG

# 导入性能监控工具
from backtesting.correlation_performance_monitor import (
    CorrelationPerformanceMonitor,
    StageTimer
)

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
        self.fund_data = MultiSourceDataAdapter()
        self.db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        self.enable_cache = enable_cache
        self._cache = {}  # 缓存相关性结果
        self._cache_time = {}  # 缓存时间
    
    def analyze_correlation(self, fund_codes: List[str], use_cache: bool = True, 
                          min_data_points: int = 30) -> Dict:
        """
        分析多只基金之间的相关性（含时间统计）
        
        参数：
        fund_codes: 基金代码列表
        use_cache: 是否使用缓存
        min_data_points: 最少数据点数
        
        返回：
        dict: 包含相关性矩阵和基金信息的字典（含性能数据）
        """
        # 初始化性能监控
        monitor = CorrelationPerformanceMonitor()
        monitor.start("total")
        
        try:
            logger.info(f"[Performance] 开始分析基金相关性: {fund_codes}")
            
            # 验证输入
            with StageTimer("输入验证", monitor):
                fund_codes = self._validate_fund_codes(fund_codes)
            
            # 检查缓存
            if use_cache and self.enable_cache:
                cache_key = tuple(sorted(fund_codes))
                if cache_key in self._cache:
                    cache_time = self._cache_time.get(cache_key)
                    if cache_time and (datetime.now() - cache_time).total_seconds() < 86400:
                        elapsed = monitor.end("total")
                        logger.info(f"[Performance] 使用缓存结果，总耗时: {elapsed:.2f} ms")
                        cached_result = self._cache[cache_key]
                        # 添加性能标记
                        cached_result['_performance'] = {
                            'from_cache': True,
                            'total_time_ms': elapsed,
                            'timestamp': datetime.now().isoformat()
                        }
                        return cached_result
            
            # 执行分析
            result = self._analyze_correlation_impl(fund_codes, min_data_points, monitor)
            
            # 记录总耗时
            total_time = monitor.end("total")
            
            # 添加性能数据到结果
            if '_performance' not in result:
                result['_performance'] = {}
            result['_performance'].update({
                'total_time_ms': total_time,
                'stage_timings': monitor.timings,
                'optimization_status': monitor.check_optimizations(),
                'timestamp': datetime.now().isoformat()
            })
            
            # 保存到缓存
            if self.enable_cache:
                cache_key = tuple(sorted(fund_codes))
                self._cache[cache_key] = result
                self._cache_time[cache_key] = datetime.now()
            
            # 输出性能报告
            logger.info(f"[Performance] 基金相关性分析完成，总耗时: {total_time:.2f} ms")
            monitor.log_report()
            
            return result
            
        except Exception as e:
            elapsed = monitor.end("total")
            logger.error(f"[Performance] 分析基金相关性失败，耗时: {elapsed:.2f} ms, 错误: {e}")
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
                                 min_data_points: int = 30,
                                 monitor: CorrelationPerformanceMonitor = None) -> Dict:
        """
        相关性分析的实现方法（含时间统计）
        
        参数：
        fund_codes: 基金代码列表
        min_data_points: 最少数据点数
        monitor: 性能监控器（可选）
        
        返回：
        dict: 相关性分析结果
        """
        # 如果没有提供监控器，创建一个
        if monitor is None:
            monitor = CorrelationPerformanceMonitor()
            monitor.start("impl_total")
        
        # 获取基金数据
        fund_data = {}
        fund_names = {}
        failed_codes = []
        
        with StageTimer("基金数据获取", monitor):
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
                    
                    # 选择需要的列
                    nav_data = nav_data[['date', 'daily_return']].copy()
                    
                    # 移除日期重复的行（保留第一个）
                    nav_data = nav_data.drop_duplicates(subset=['date'], keep='first')
                    
                    # 限制单个基金数据量，避免内存溢出
                    max_single_fund_points = 500
                    if len(nav_data) > max_single_fund_points:
                        logger.warning(f"基金 {fund_code} 数据过多({len(nav_data)})，限制为最近{max_single_fund_points}个")
                        nav_data = nav_data.sort_values('date').tail(max_single_fund_points)
                    
                    # 保存数据
                    fund_data[fund_code] = nav_data
                    logger.info(f"基金 {fund_code} 数据获取成功: {len(fund_data[fund_code])} 个数据点，日期范围: {nav_data['date'].min()} 至 {nav_data['date'].max()}")
                    
                except Exception as e:
                    failed_codes.append((fund_code, str(e)))
                    logger.warning(f"处理基金 {fund_code} 失败: {e}")
        
        # 检查有效基金数量
        if len(fund_data) < 2:
            error_msg = f"有效基金数据不足2只，失败列表: {failed_codes}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 合并数据
        with StageTimer("数据合并", monitor):
            merged_df = None
            for fund_code, df in fund_data.items():
                df_renamed = df.rename(columns={'daily_return': fund_code})
                if merged_df is None:
                    merged_df = df_renamed
                    logger.info(f"初始化合并数据: {len(merged_df)} 行")
                else:
                    # 使用内连接只保留共同日期，避免数据量爆炸
                    logger.info(f"合并前: {len(merged_df)} 行，正在合并 {fund_code}: {len(df_renamed)} 行")
                    
                    # 紧急检查：如果数据量已经过大，直接报错
                    if len(merged_df) > 10000:
                        raise ValueError(f"合并前数据量过大({len(merged_df)})，可能存在数据质量问题")
                    
                    merged_df = pd.merge(merged_df, df_renamed, on='date', how='inner')
                    logger.info(f"合并后: {len(merged_df)} 行")
                    
                    # 如果合并后数据为空，提前退出
                    if len(merged_df) == 0:
                        logger.error(f"与基金 {fund_code} 合并后无共同日期")
                        break
            
            # 检查合并后数据是否为空
            if merged_df is None or len(merged_df) == 0:
                raise ValueError("合并后数据为空，基金可能没有共同的交易日")
            
            # 限制数据点数量，避免内存溢出（最多使用最近500个交易日）
            max_data_points = 500
            if len(merged_df) > max_data_points:
                logger.warning(f"数据点过多({len(merged_df)})，限制为最近{max_data_points}个交易日")
                merged_df = merged_df.sort_values('date').tail(max_data_points)
            
            # 再次检查是否有足够的数据
            if len(merged_df) < min_data_points:
                raise ValueError(f"合并后数据不足: {len(merged_df)} < {min_data_points}")
            
            # 最终检查：确保数据量不会导致内存溢出
            if len(merged_df) > 1000:
                logger.warning(f"最终数据量过大({len(merged_df)})，强制限制为1000行")
                merged_df = merged_df.sort_values('date').tail(1000)
        
        # 计算相关性矩阵
        with StageTimer("相关性矩阵计算", monitor):
            return_columns = list(fund_data.keys())
            logger.info(f"开始计算相关性矩阵: {len(return_columns)}只基金 x {len(merged_df)}个数据点")
            correlation_matrix = merged_df[return_columns].corr().values.tolist()
        
        # 记录实现方法的总耗时（如果这是独立的监控器）
        if monitor and 'impl_total' in monitor.stage_timings:
            impl_time = monitor.end("impl_total")
            logger.info(f"[Performance] 相关性分析实现方法耗时: {impl_time:.2f} ms")
        
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
