#!/usr/bin/env python
# coding: utf-8
"""
MultiSourceFundData 适配器 (已优化)
基于 OptimizedFundData 实现，兼容 EnhancedFundData 的接口

优化特性：
1. 批量数据预加载 - 大幅减少API调用次数
2. API速率限制 - 避免触发频率限制（80次/分钟）
3. 多级缓存策略 - 内存缓存+数据库缓存
4. 智能降级 - 自动切换到备用数据源

缓存策略：
1. 首次访问：从 Tushare 批量获取数据，存入缓存
2. 非首次访问：优先使用缓存数据，但 today_return 实时计算
3. prev_day_return 可缓存（1天有效期）
4. current_nav 可缓存（1小时有效期）
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import time

from data_retrieval.fetchers.optimized_fund_data import OptimizedFundData
from services.cache.persistent_cache import FundDataCache

logger = logging.getLogger(__name__)


class MultiSourceDataAdapter(OptimizedFundData):
    """
    MultiSourceFundData 适配器类 (已优化版本)
    基于 OptimizedFundData，兼容 EnhancedFundData 的接口方法
    
    优化特性：
    - 批量数据获取：一次API调用获取多只基金
    - 速率限制保护：自动控制API调用频率
    - 多级缓存：内存+数据库双层缓存
    
    缓存策略：
    - prev_day_return: 缓存1天（昨日数据不常变）
    - current_nav: 缓存1小时（净值相对稳定）
    - today_return: 实时计算（必须实时）
    """
    
    def __init__(self, tushare_token: Optional[str] = None, timeout: int = 10, db_manager=None):
        """
        初始化适配器
        
        Args:
            tushare_token: Tushare API token，如果不提供则从配置中读取
            timeout: 请求超时时间(秒)
            db_manager: 数据库管理器，用于持久化缓存
        """
        # 如果没有提供token，则从配置中获取
        if tushare_token is None:
            try:
                from shared.enhanced_config import DATA_SOURCE_CONFIG
                tushare_token = DATA_SOURCE_CONFIG.get('tushare', {}).get('token')
                logger.info(f"从配置文件获取Tushare token: {tushare_token[:10]}...")
            except ImportError:
                logger.warning("无法导入配置文件，使用默认Tushare token")
                tushare_token = '5ff19facae0e5b26a407d491d33707a9884a39a714a0d76b6495725b'
        
        # 调用 OptimizedFundData 的初始化（启用批量优化和速率限制）
        super().__init__(
            tushare_token=tushare_token, 
            timeout=timeout,
            enable_batch=True,       # 启用批量获取优化
            enable_rate_limit=True   # 启用速率限制
        )
        
        # 初始化缓存管理器（保持原有缓存逻辑兼容）
        self.cache = FundDataCache(db_manager)
        
        logger.info("MultiSourceDataAdapter 初始化完成 (已优化版本)")
        logger.info("  - 批量数据获取: 启用")
        logger.info("  - API速率限制: 启用")
        logger.info("  - Tushare优先级: 启用")
        logger.info("  - 缓存系统: 已启动")
    
    def warmup_realtime_cache(self, fund_codes: List[str]) -> Dict[str, int]:
        """
        预热实时数据缓存
        
        批量获取多只基金的实时数据并保存到缓存，避免逐个请求时缓存未命中
        
        Args:
            fund_codes: 基金代码列表
            
        Returns:
            dict: 统计信息 {success_count, fail_count}
        """
        logger.info(f"开始预热实时数据缓存，共 {len(fund_codes)} 只基金")
        
        success_count = 0
        fail_count = 0
        
        # 使用批量获取方法（内部有缓存优化）
        try:
            batch_results = self.get_batch_realtime_data(fund_codes)
            
            for code, data in batch_results.items():
                if data and data.get('current_nav'):
                    success_count += 1
                else:
                    fail_count += 1
                    
            logger.info(f"缓存预热完成: 成功 {success_count} 只，失败 {fail_count} 只")
            return {'success_count': success_count, 'fail_count': fail_count}
            
        except Exception as e:
            logger.error(f"缓存预热失败: {e}")
            return {'success_count': 0, 'fail_count': len(fund_codes)}
    
    def get_realtime_data(self, fund_code: str, fund_name: str = None) -> Dict:
        """
        获取基金实时数据（带缓存策略）
        
        缓存策略：
        1. 首次访问：从 Tushare 获取完整数据，存入缓存
        2. 非首次访问：优先使用缓存数据，但 today_return 实时计算
        3. prev_day_return 可缓存（1天有效期）
        4. QDII基金特殊处理：昨日收益率为0时前向追溯
        
        Args:
            fund_code: 基金代码
            fund_name: 基金名称（可选）
            
        Returns:
            dict: 基金实时数据
        """
        try:
            from datetime import datetime
            today_str = datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"开始获取基金 {fund_code} 实时数据（带缓存策略）")
            
            # 判断是否为QDII基金
            is_qdii = self.is_qdii_fund(fund_code, fund_name)
            logger.debug(f"基金 {fund_code} 是否为QDII: {is_qdii}")
            
            # 步骤1：尝试从缓存获取可缓存数据
            cached_prev_return = self.cache.get_cached_data(fund_code, 'prev_day_return')
            cached_current_nav = self.cache.get_cached_data(fund_code, 'current_nav')
            cached_previous_nav = self.cache.get_cached_data(fund_code, 'previous_nav')
            
            cache_hit = cached_prev_return is not None and cached_current_nav is not None
            
            if cache_hit:
                logger.info(f"基金 {fund_code} 缓存命中，使用缓存数据并实时计算 today_return")
                
                # 获取实时估值数据
                estimate_data = self._get_realtime_estimate(fund_code)
                
                # 优先使用实时估值数据
                if estimate_data and estimate_data.get('estimate_nav', 0) > 0 and estimate_data.get('yesterday_nav', 0) > 0:
                    current_nav = estimate_data['estimate_nav']
                    previous_nav = estimate_data['yesterday_nav']
                    today_return = estimate_data.get('daily_return', 0)
                    if today_return == 0:
                        today_return = round((current_nav - previous_nav) / previous_nav * 100, 2)
                    logger.info(f"基金 {fund_code} 缓存命中时使用实时估值: current={current_nav}, previous={previous_nav}, today_return={today_return}%")
                else:
                    # 无实时估值，使用缓存数据
                    # 注意：cached_current_nav 实际上是昨日净值
                    current_nav = cached_current_nav
                    if cached_previous_nav and cached_previous_nav != cached_current_nav:
                        previous_nav = cached_previous_nav
                    elif cached_prev_return and cached_prev_return != 0:
                        previous_nav = cached_current_nav / (1 + cached_prev_return / 100)
                    else:
                        previous_nav = cached_current_nav
                    today_return = round((current_nav - previous_nav) / previous_nav * 100, 2) if previous_nav > 0 else 0.0
                    logger.info(f"基金 {fund_code} 缓存命中时使用缓存数据: current={current_nav}, previous={previous_nav}, today_return={today_return}%")
                
                # 昨日收益率从缓存获取，如果缓存值为0则重新计算
                prev_day_return = cached_prev_return
                if prev_day_return == 0 or prev_day_return is None:
                    logger.debug(f"基金 {fund_code} 缓存的 prev_day_return 为0，重新计算")
                    prev_day_return = self._calculate_yesterday_return_from_history(fund_code)
                
                result = {
                    'fund_code': fund_code,
                    'fund_name': fund_name or f'基金{fund_code}',
                    'current_nav': current_nav,
                    'previous_nav': previous_nav,
                    'daily_return': today_return,
                    'today_return': today_return,
                    'prev_day_return': prev_day_return,
                    'nav_date': today_str,
                    'data_source': 'cache_with_realtime',
                    'estimate_nav': estimate_data.get('estimate_nav', current_nav) if estimate_data else current_nav,
                    'estimate_return': today_return
                }
                logger.info(f"基金 {fund_code} 缓存数据使用成功: today_return={today_return}%, prev_day_return={prev_day_return}%")
                return result
            
            # 步骤2：缓存未命中，从数据源获取
            logger.info(f"基金 {fund_code} 缓存未命中，从 Tushare 获取数据")
            
            if is_qdii:
                # QDII基金使用专门方法
                result = self._get_qdii_data_with_cache(fund_code, fund_name, today_str)
            else:
                # 普通基金使用最新净值数据
                result = self._get_normal_fund_data_with_cache(fund_code, fund_name, today_str)
            
            # 保存到缓存（供下次使用）
            if result and result.get('current_nav', 0) > 0:
                self._save_fund_data_to_cache(fund_code, result)
            
            return result
            
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 实时数据失败: {e}", exc_info=True)
            return self._get_default_fund_data(fund_code, fund_name)
    
    def _calculate_today_return_realtime(self, fund_code: str, current_nav: float, previous_nav: float) -> float:
        """
        实时计算今日收益率
        
        优先使用实时估值接口计算，如果失败则使用缓存的净值计算
        
        Args:
            fund_code: 基金代码
            current_nav: 当前净值（缓存值）
            previous_nav: 昨日净值（缓存值）
            
        Returns:
            float: 今日收益率（百分比）
        """
        try:
            # 尝试获取实时估值
            estimate_data = self._get_realtime_estimate(fund_code)
            
            if estimate_data and estimate_data.get('estimate_nav', 0) > 0:
                estimate_nav = estimate_data['estimate_nav']
                yesterday_nav = estimate_data.get('yesterday_nav', previous_nav)
                
                if yesterday_nav and yesterday_nav > 0:
                    today_return = (estimate_nav - yesterday_nav) / yesterday_nav * 100
                    today_return = round(today_return, 2)
                    logger.debug(f"基金 {fund_code} 使用实时估值计算 today_return: {today_return}%")
                    return today_return
            
            # 无法获取实时估值，使用缓存净值计算
            # 注意：这里的 previous_nav 已经是昨日净值，不是前天净值
            # 所以这个计算实际上计算的是 "今日相对昨日的收益率"，也就是 today_return
            if previous_nav and previous_nav > 0 and current_nav and current_nav > 0:
                today_return = (current_nav - previous_nav) / previous_nav * 100
                today_return = round(today_return, 2)
                logger.debug(f"基金 {fund_code} 使用缓存净值计算 today_return: {today_return}%")
                return today_return
            
            logger.warning(f"基金 {fund_code} 无法计算 today_return，净值数据无效")
            return 0.0
            
        except Exception as e:
            logger.warning(f"基金 {fund_code} 计算 today_return 失败: {e}")
            return 0.0

    def _calculate_yesterday_return_from_history(self, fund_code: str) -> float:
        """
        从历史净值数据中计算昨日收益率
        
        昨日收益率 = (T-1净值 - T-2净值) / T-2净值 * 100
        
        Args:
            fund_code: 基金代码
            
        Returns:
            float: 昨日收益率（百分比）
        """
        try:
            from datetime import timedelta
            
            # 获取最近3天的历史数据
            df = self.get_fund_nav_history(fund_code, days=5)
            
            if df is None or df.empty or len(df) < 2:
                logger.debug(f"基金 {fund_code} 历史数据不足，无法计算昨日收益率")
                return 0.0
            
            # 确保数据按日期排序（最新在前）
            if 'date' in df.columns:
                df = df.sort_values('date', ascending=False)
            
            # T-1 净值（昨日净值）
            nav_t1 = float(df.iloc[0]['nav'])
            # T-2 净值（前天净值）
            nav_t2 = float(df.iloc[1]['nav']) if len(df) > 1 else nav_t1
            
            if nav_t2 > 0:
                yesterday_return = (nav_t1 - nav_t2) / nav_t2 * 100
                yesterday_return = round(yesterday_return, 2)
                logger.debug(f"基金 {fund_code} 从历史数据计算昨日收益率: {yesterday_return}%")
                return yesterday_return
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"基金 {fund_code} 计算昨日收益率失败: {e}")
            return 0.0
    
    def _get_qdii_data_with_cache(self, fund_code: str, fund_name: str, today_str: str) -> Dict:
        """
        获取QDII基金数据（带缓存逻辑）
        
        Args:
            fund_code: 基金代码
            fund_name: 基金名称
            today_str: 今日日期字符串
            
        Returns:
            dict: 基金数据
        """
        logger.debug(f"使用QDII专用方法获取基金 {fund_code} 数据")
        qdii_data = self.get_qdii_fund_data(fund_code)
        
        if not qdii_data or not pd.notna(qdii_data.get('current_nav')) or qdii_data.get('current_nav', 0) <= 0:
            logger.warning(f"QDII基金 {fund_code} 数据获取失败或净值无效")
            return self._get_default_fund_data(fund_code, fund_name)
        
        # 获取昨日收益率（带前向追溯）
        return_result = self._get_yesterday_return(fund_code, qdii_data.get('nav_date'))
        prev_day_return = return_result.get('value', 0.0)
        
        # 如果昨日收益率为0且是QDII基金，尝试前向追溯
        if prev_day_return == 0.0:
            logger.info(f"QDII基金 {fund_code} 昨日收益率为0，尝试前向追溯")
            df = self.get_fund_nav_history(fund_code, source='auto')
            if df is not None and not df.empty and len(df) >= 2:
                traced_result = self._get_previous_nonzero_return_with_date(df, fund_code)
                if traced_result.get('value', 0.0) != 0.0:
                    prev_day_return = traced_result.get('value')
                    logger.info(f"QDII基金 {fund_code} 前向追溯成功，使用收益率: {prev_day_return}%")
        
        # 获取实时估值并计算 today_return
        today_return = self._calculate_today_return_realtime(
            fund_code,
            qdii_data['current_nav'],
            qdii_data.get('previous_nav', qdii_data['current_nav'])
        )
        # 估值涨跌幅为0（开盘前），fallback 到历史净值最新一条的 daily_return
        if today_return == 0 and qdii_data.get('daily_return', 0) != 0:
            today_return = round(float(qdii_data['daily_return']), 2)
            logger.info(f"QDII基金 {fund_code} 估值涨跌幅为0，使用历史净值涨跌幅: {today_return}%")
        
        result = {
            'fund_code': fund_code,
            'fund_name': fund_name or f'基金{fund_code}',
            'current_nav': qdii_data['current_nav'],
            'previous_nav': qdii_data.get('previous_nav', qdii_data['current_nav']),
            'daily_return': today_return,
            'today_return': today_return,
            'prev_day_return': prev_day_return,
            'nav_date': qdii_data.get('nav_date', today_str),
            'data_source': f"tushare_qdii_{qdii_data.get('data_source', 'unknown')}",
            'estimate_nav': qdii_data['current_nav'],
            'estimate_return': today_return
        }
        
        logger.info(f"QDII基金 {fund_code} 数据获取完成: today_return={today_return}%, prev_day_return={prev_day_return}%")
        return result
    
    def _get_normal_fund_data_with_cache(self, fund_code: str, fund_name: str, today_str: str) -> Dict:
        """
        获取普通基金数据（带缓存逻辑）
        
        Args:
            fund_code: 基金代码
            fund_name: 基金名称
            today_str: 今日日期字符串
            
        Returns:
            dict: 基金数据
        """
        logger.debug(f"使用普通方法获取基金 {fund_code} 数据")
        latest_nav = self.get_fund_latest_nav(fund_code)
        
        if not latest_nav:
            logger.warning(f"基金 {fund_code} 最新净值数据获取失败")
            return self._get_default_fund_data(fund_code, fund_name)
        
        logger.debug(f"基金 {fund_code} 最新净值数据获取成功: {latest_nav}")
        
        # 获取昨日收益率（从历史数据计算 T-1 相对 T-2 的变化）
        return_result = self._get_yesterday_return(fund_code, latest_nav.get('date'))
        prev_day_return = return_result.get('value', 0.0)
        logger.debug(f"基金 {fund_code} 昨日收益率: {prev_day_return}%")
        
        # 获取实时估值数据
        estimate_data = self._get_realtime_estimate(fund_code)
        
        # 优先使用实时估值数据计算今日收益
        if estimate_data and estimate_data.get('estimate_nav', 0) > 0 and estimate_data.get('yesterday_nav', 0) > 0:
            # 有实时估值：current=estimate_nav, previous=yesterday_nav
            current_nav = estimate_data['estimate_nav']
            previous_nav = estimate_data['yesterday_nav']
            today_return = estimate_data.get('daily_return', 0)  # 新浪已经计算好了
            if today_return == 0:
                today_return = round((current_nav - previous_nav) / previous_nav * 100, 2)
            logger.info(f"基金 {fund_code} 使用实时估值: current={current_nav}, previous={previous_nav}, today_return={today_return}%")
        else:
            # 无实时估值：使用 Tushare 数据
            # Tushare 的 nav 是昨日已确认净值，daily_return 是昨日收益率
            current_nav = latest_nav['nav']
            if latest_nav.get('daily_return', 0) != 0:
                # 从昨日收益率反推前日净值
                previous_nav = current_nav / (1 + latest_nav['daily_return'] / 100)
                today_return = round(latest_nav['daily_return'], 2)
            else:
                previous_nav = current_nav
                today_return = 0.0
            logger.info(f"基金 {fund_code} 使用Tushare数据: current={current_nav}, previous={previous_nav}, today_return={today_return}%")
        
        result = {
            'fund_code': fund_code,
            'fund_name': fund_name or f'基金{fund_code}',
            'current_nav': current_nav,
            'previous_nav': previous_nav,
            'daily_return': today_return,
            'today_return': today_return,
            'prev_day_return': prev_day_return,
            'nav_date': latest_nav.get('date', today_str),
            'data_source': f"tushare_{latest_nav.get('source', 'unknown')}",
            'estimate_nav': estimate_data.get('estimate_nav', current_nav) if estimate_data else current_nav,
            'estimate_return': today_return
        }
        
        logger.info(f"普通基金 {fund_code} 数据获取完成: today_return={today_return}%, prev_day_return={prev_day_return}%")
        return result
    
    def _save_fund_data_to_cache(self, fund_code: str, data: Dict):
        """
        保存基金数据到缓存
        
        Args:
            fund_code: 基金代码
            data: 基金数据字典
        """
        try:
            # 保存到内存缓存
            self.cache.save_cached_data(fund_code, 'prev_day_return', data.get('prev_day_return'))
            self.cache.save_cached_data(fund_code, 'current_nav', data.get('current_nav'))
            self.cache.save_cached_data(fund_code, 'previous_nav', data.get('previous_nav'))
            
            # 持久化到数据库缓存
            self.cache.save_cached_data(fund_code, 'full_data', data, persist=True)
            
            logger.debug(f"基金 {fund_code} 数据已保存到缓存")
        except Exception as e:
            logger.warning(f"保存基金 {fund_code} 数据到缓存失败: {e}")
    
    def _get_default_fund_data(self, fund_code: str, fund_name: str = None) -> Dict:
        """
        获取默认基金数据（当所有数据源都失败时）
        
        Args:
            fund_code: 基金代码
            fund_name: 基金名称
            
        Returns:
            dict: 默认基金数据
        """
        logger.warning(f"基金 {fund_code} 所有数据源都失败，返回默认值")
        return {
            'fund_code': fund_code,
            'fund_name': fund_name or f'基金{fund_code}',
            'current_nav': 0.0,
            'previous_nav': 0.0,
            'daily_return': 0.0,
            'today_return': 0.0,
            'prev_day_return': 0.0,
            'nav_date': datetime.now().strftime('%Y-%m-%d'),
            'data_source': 'tushare_failed',
            'estimate_nav': 0.0,
            'estimate_return': 0.0
        }
    
    def _get_yesterday_return(self, fund_code: str, latest_date: str = None) -> Dict:
        """
        获取昨日收益率（前一天净值相对于再前一天净值的变化率）
        带前向追溯功能，当获取到零值时会向前查找非零的历史收益率
        
        计算公式: (nav_prev - nav_prev_prev) / nav_prev_prev * 100
        其中:
            nav_prev = 前一天的净值 (数据中的第1条)
            nav_prev_prev = 再前一天的净值 (数据中的第2条)
        
        Args:
            fund_code: 基金代码
            latest_date: 最新净值日期（可选）
            
        Returns:
            Dict: 包含以下字段的字典
                - value: 昨日收益率（百分比）
                - date: 用于计算昨日收益率的净值日期
                - days_diff: 与最新净值的日期差（T-1=1, T-2=2, 等）
                - is_stale: 是否为延迟数据（days_diff > 1）
        """
        from datetime import datetime, timedelta
        
        default_result = {
            'value': 0.0,
            'date': None,
            'days_diff': None,
            'is_stale': False
        }
        
        try:
            # 获取最近几天的历史数据
            df = self.get_fund_nav_history(fund_code, source='auto')
            
            if df is None or df.empty or len(df) < 3:
                logger.debug(f"基金 {fund_code} 历史数据不足，无法计算昨日收益率")
                return default_result
            
            # 确保数据按日期倒序排列（最新在前）
            if 'date' in df.columns:
                df = df.sort_values('date', ascending=False)
            
            # 获取最新净值日期
            latest_date_str = str(df.iloc[0].get('date', ''))
            latest_date_obj = None
            try:
                if len(latest_date_str) == 8:  # YYYYMMDD
                    latest_date_obj = datetime.strptime(latest_date_str, '%Y%m%d')
                elif '-' in latest_date_str:  # YYYY-MM-DD
                    latest_date_obj = datetime.strptime(latest_date_str, '%Y-%m-%d')
            except:
                latest_date_obj = datetime.now()
            
            # 计算昨日收益率：使用第1条（前一天）和第2条（再前一天）的数据
            # 第0条是最新净值，第1条是前一天净值，第2条是再前一天净值
            prev_nav = float(df.iloc[1]['nav'])  # 前一天净值
            prev_prev_nav = float(df.iloc[2]['nav'])  # 再前一天净值
            prev_date = str(df.iloc[1].get('date', ''))  # 前一天日期
            
            logger.debug(f"基金 {fund_code} 计算昨日收益率: 前一天净值={prev_nav}({prev_date}), 再前一天净值={prev_prev_nav}")
            
            # 计算日期差（与最新净值日期的差）
            days_diff = 1  # 默认为T-1
            try:
                if prev_date:
                    if len(prev_date) == 8:
                        y_date_obj = datetime.strptime(prev_date, '%Y%m%d')
                    elif '-' in prev_date:
                        y_date_obj = datetime.strptime(prev_date, '%Y-%m-%d')
                    else:
                        y_date_obj = latest_date_obj - timedelta(days=1)
                    
                    days_diff = (latest_date_obj - y_date_obj).days
                    if days_diff <= 0:
                        days_diff = 1
            except:
                days_diff = 1
            
            # 计算收益率: (前一天 - 再前一天) / 再前一天 * 100
            if prev_prev_nav > 0:
                yesterday_return = (prev_nav - prev_prev_nav) / prev_prev_nav * 100
                result_value = round(yesterday_return, 2)
                logger.debug(f"基金 {fund_code} 直接计算昨日收益率: {result_value}%, 使用日期: {prev_date}, 日期差: T-{days_diff}")
                
                # 如果计算结果为0，且是QDII基金，则进行前向追溯
                if result_value == 0.0 and self.is_qdii_fund(fund_code):
                    logger.info(f"QDII基金 {fund_code} 昨日收益率为0，开始前向追溯获取非零值")
                    traced_result = self._get_previous_nonzero_return_with_date(df, fund_code, latest_date_obj)
                    if traced_result['value'] != 0.0:
                        logger.info(f"QDII基金 {fund_code} 前向追溯成功，使用收益率: {traced_result['value']}%")
                        return traced_result
                
                return {
                    'value': result_value,
                    'date': prev_date,
                    'days_diff': days_diff,
                    'is_stale': days_diff > 1
                }
            else:
                logger.warning(f"基金 {fund_code} 再前一天净值为0或负数: {prev_prev_nav}")
                # 尝试前向追溯获取有效数据
                traced_result = self._get_previous_nonzero_return_with_date(df, fund_code, latest_date_obj)
                if traced_result['value'] != 0.0:
                    logger.info(f"基金 {fund_code} 前向追溯成功获取有效收益率: {traced_result['value']}%")
                    return traced_result
                return default_result
            
        except Exception as e:
            logger.warning(f"获取基金 {fund_code} 昨日收益率失败: {e}")
            return default_result
    
    def _get_previous_nonzero_return(self, fund_nav: pd.DataFrame, fund_code: str) -> float:
        """
        向前追溯获取非零的昨日收益率
        
        Args:
            fund_nav: 基金历史净值数据DataFrame
            fund_code: 基金代码
            
        Returns:
            float: 非零的昨日收益率，如果找不到则返回0.0
        """
        try:
            # 查找包含daily_return或日增长率的列
            return_column = None
            if 'daily_return' in fund_nav.columns:
                return_column = 'daily_return'
            elif '日增长率' in fund_nav.columns:
                return_column = '日增长率'
            
            if return_column is None:
                logger.debug(f"基金 {fund_code} 数据中未找到收益率列")
                return 0.0
            
            # 从较早的数据开始向前查找非零值（避免使用最新数据）
            # 从倒数第三条开始往前查找（跳过最新的两条）
            start_index = min(len(fund_nav) - 3, 5)  # 最多向前查找5条数据
            start_index = max(start_index, 0)
            
            for i in range(start_index, -1, -1):
                data_row = fund_nav.iloc[i]
                return_raw = data_row.get(return_column, None)
                
                if pd.notna(return_raw):
                    try:
                        return_value = float(return_raw)
                        # 格式转换处理（如果是小数格式则乘以100）
                        if abs(return_value) < 0.1:
                            return_value = return_value * 100
                        return_value = round(return_value, 2)
                        
                        # 检查是否为有效非零值（在合理范围内）
                        if return_value != 0.0 and abs(return_value) <= 100:
                            nav_date = data_row.get('date', data_row.get('净值日期', 'Unknown'))
                            logger.debug(f"基金 {fund_code} 在 {nav_date} 找到有效收益率: {return_value}%")
                            return return_value
                    except (ValueError, TypeError) as parse_error:
                        logger.debug(f"基金 {fund_code} 解析收益率数据失败: {parse_error}")
                        continue
                
                # 限制追溯范围
                if start_index - i > 10:
                    break
            
            logger.debug(f"基金 {fund_code} 未找到有效的非零收益率")
            return 0.0
            
        except Exception as e:
            logger.warning(f"基金 {fund_code} 前向追溯获取收益率时出错: {str(e)}")
            return 0.0
    
    def _get_previous_nonzero_return_with_date(self, fund_nav: pd.DataFrame, fund_code: str, latest_date: datetime = None) -> Dict:
        """
        向前追溯获取非零的昨日收益率（带日期信息）
        
        Args:
            fund_nav: 基金历史净值数据DataFrame
            fund_code: 基金代码
            latest_date: 最新净值日期
            
        Returns:
            Dict: 包含以下字段的字典
                - value: 昨日收益率（百分比）
                - date: 用于计算昨日收益率的净值日期
                - days_diff: 与最新净值的日期差（T-1=1, T-2=2, 等）
                - is_stale: 是否为延迟数据（days_diff > 1）
        """
        from datetime import datetime, timedelta
        
        default_result = {
            'value': 0.0,
            'date': None,
            'days_diff': None,
            'is_stale': False
        }
        
        try:
            # 查找包含daily_return或日增长率的列
            return_column = None
            date_column = None
            if 'daily_return' in fund_nav.columns:
                return_column = 'daily_return'
                date_column = 'date'
            elif '日增长率' in fund_nav.columns:
                return_column = '日增长率'
                date_column = '净值日期'
            
            if return_column is None:
                logger.debug(f"基金 {fund_code} 数据中未找到收益率列")
                return default_result
            
            # 从较早的数据开始向前查找非零值（避免使用最新数据）
            # 从倒数第三条开始往前查找（跳过最新的两条）
            start_index = min(len(fund_nav) - 3, 5)  # 最多向前查找5条数据
            start_index = max(start_index, 0)
            
            for i in range(start_index, -1, -1):
                data_row = fund_nav.iloc[i]
                return_raw = data_row.get(return_column, None)
                nav_date = str(data_row.get(date_column, ''))
                
                if pd.notna(return_raw):
                    try:
                        return_value = float(return_raw)
                        # 格式转换处理（如果是小数格式则乘以100）
                        if abs(return_value) < 0.1:
                            return_value = return_value * 100
                        return_value = round(return_value, 2)
                        
                        # 检查是否为有效非零值（在合理范围内）
                        if return_value != 0.0 and abs(return_value) <= 100:
                            # 计算日期差
                            days_diff = i + 1  # 默认为相对位置
                            if latest_date and nav_date:
                                try:
                                    if len(nav_date) == 8:
                                        nav_date_obj = datetime.strptime(nav_date, '%Y%m%d')
                                    elif '-' in nav_date:
                                        nav_date_obj = datetime.strptime(nav_date, '%Y-%m-%d')
                                    else:
                                        nav_date_obj = latest_date - timedelta(days=i+1)
                                    
                                    days_diff = (latest_date - nav_date_obj).days
                                    if days_diff <= 0:
                                        days_diff = i + 1
                                except:
                                    days_diff = i + 1
                            
                            logger.debug(f"基金 {fund_code} 在 {nav_date} 找到有效收益率: {return_value}%, 日期差: T-{days_diff}")
                            return {
                                'value': return_value,
                                'date': nav_date,
                                'days_diff': days_diff,
                                'is_stale': days_diff > 1
                            }
                    except (ValueError, TypeError) as parse_error:
                        logger.debug(f"基金 {fund_code} 解析收益率数据失败: {parse_error}")
                        continue
                
                # 限制追溯范围
                if start_index - i > 10:
                    break
            
            logger.debug(f"基金 {fund_code} 未找到有效的非零收益率")
            return default_result
            
        except Exception as e:
            logger.warning(f"基金 {fund_code} 前向追溯获取收益率时出错: {str(e)}")
            return default_result
    
    def _get_realtime_estimate(self, fund_code: str) -> Optional[Dict]:
        """
        获取基金实时估值数据
        
        尝试从多个数据源获取实时估值（按优先级）：
        1. 天天基金网（最实时，有当日估值）
        2. 新浪接口
        3. 东方财富估算接口
        
        Args:
            fund_code: 基金代码
            
        Returns:
            dict: 包含实时估值数据，失败返回None
            {
                'estimate_nav': 实时估值,
                'yesterday_nav': 昨日净值,
                'estimate_time': 估值时间
            }
        """
        import json
        from datetime import datetime
        import requests
        
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        # 1. 优先尝试天天基金网（有实时估值）
        try:
            url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200 and 'jsonpgz' in response.text:
                # 解析jsonp格式
                json_str = response.text.replace('jsonpgz(', '').replace(');', '')
                data = json.loads(json_str)
                
                gztime = data.get('gztime', '')
                dwjz = float(data.get('dwjz', 0))   # 最新确认单位净值
                gsz = float(data.get('gsz', 0))     # 实时估算净值
                gszzl = float(data.get('gszzl', 0)) # 估算涨跌幅（%）
                # 检查是否是今天的数据
                if today_str in gztime:
                    logger.info(f"天天基金网获取 {fund_code} 实时估值成功: {gsz} ({gztime})")
                    return {
                        'estimate_nav': gsz,
                        'yesterday_nav': dwjz,
                        'estimate_time': gztime,
                        'daily_return': gszzl,
                        'source': 'tiantian'
                    }
                else:
                    # 非交易时段：用最新确认净值和其日涨跌幅（dwjz/gszzl 对应最后一个交易日）
                    # gszzl 此时是上一个确认净值对应的日涨跌幅，作为"最近已知涨跌幅"使用
                    if dwjz > 0 and gszzl != 0:
                        logger.info(f"天天基金网 {fund_code} 使用最近已知涨跌幅(非今日估值): {gszzl}% ({gztime})")
                        return {
                            'estimate_nav': dwjz,   # 用确认净值代替估值
                            'yesterday_nav': round(dwjz / (1 + gszzl / 100), 4),  # 反推前日净值
                            'estimate_time': gztime,
                            'daily_return': gszzl,
                            'source': 'tiantian_confirmed'
                        }
                    else:
                        logger.debug(f"天天基金网 {fund_code} 估值不是今天且涨跌幅为0: {gztime}")
        except Exception as e:
            logger.debug(f"天天基金网实时估值获取失败 {fund_code}: {e}")
        
        # 2. 尝试新浪接口
        try:
            url = f"https://hq.sinajs.cn/list=f_{fund_code}"
            headers = {'Referer': 'https://finance.sina.com.cn'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.text
                key = f'f_{fund_code}="'
                if key in data:
                    parts = data.split('"')[1].split(',')
                    if len(parts) >= 6:
                        # 新浪返回: [名称, 单位净值, 累计净值, 昨日净值, 日期, 日增长率]
                        return {
                            'estimate_nav': float(parts[1]) if len(parts) > 1 else 0.0,
                            'yesterday_nav': float(parts[3]) if len(parts) > 3 else 0.0,
                            'estimate_time': parts[4] if len(parts) > 4 else '',
                            'daily_return': float(parts[5]) if len(parts) > 5 else 0.0,
                            'source': 'sina'
                        }
        except Exception as e:
            logger.debug(f"新浪实时估值获取失败 {fund_code}: {e}")
        
        # 尝试东方财富估值接口
        try:
            import akshare as ak
            # 使用akshare获取估值数据
            df = ak.fund_value_estimation_em(symbol=fund_code)
            if not df.empty:
                latest = df.iloc[0]
                return {
                    'estimate_nav': float(latest.get('gsz', 0)),  # 估算值
                    'yesterday_nav': float(latest.get('dwjz', 0)),  # 单位净值
                    'estimate_time': str(latest.get('gztime', '')),
                    'daily_return': float(latest.get('gszzl', 0)),  # 估算增长率
                    'source': 'eastmoney_estimate'
                }
        except Exception as e:
            logger.debug(f"东方财富估值获取失败 {fund_code}: {e}")
        
        return None
    
    def get_batch_realtime_data(self, fund_codes: List[str], fund_names: Dict[str, str] = None) -> Dict[str, Dict]:
        """
        批量获取基金实时数据（带缓存优化）
        
        优先使用缓存数据，减少API调用次数
        
        Args:
            fund_codes: 基金代码列表
            fund_names: 基金名称字典 {code: name}
            
        Returns:
            Dict[基金代码, 基金数据]
        """
        if fund_names is None:
            fund_names = {}
        
        results = {}
        missing_codes = []
        
        logger.info(f"批量获取 {len(fund_codes)} 只基金数据")
        
        # 步骤1：尝试从缓存获取
        for code in fund_codes:
            cached_prev = self.cache.get_cached_data(code, 'prev_day_return')
            cached_nav = self.cache.get_cached_data(code, 'current_nav')
            cached_prev_nav = self.cache.get_cached_data(code, 'previous_nav')
            
            if cached_prev is not None and cached_nav is not None:
                # 缓存命中，实时计算 today_return
                today_return = self._calculate_today_return_realtime(
                    code, cached_nav, cached_prev_nav
                )
                
                results[code] = {
                    'fund_code': code,
                    'fund_name': fund_names.get(code, f'基金{code}'),
                    'current_nav': cached_nav,
                    'previous_nav': cached_prev_nav or cached_nav,
                    'daily_return': today_return,
                    'today_return': today_return,
                    'prev_day_return': cached_prev,
                    'nav_date': datetime.now().strftime('%Y-%m-%d'),
                    'data_source': 'cache',
                    'estimate_nav': cached_nav,
                    'estimate_return': today_return
                }
            else:
                missing_codes.append(code)
        
        logger.info(f"缓存命中: {len(results)}/{len(fund_codes)}, 需从API获取: {len(missing_codes)}")
        
        # 步骤2：对未命中的基金，批量从API获取
        if missing_codes:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            def fetch_single(code):
                try:
                    return code, self.get_realtime_data(code, fund_names.get(code))
                except Exception as e:
                    logger.error(f"获取基金 {code} 数据失败: {e}")
                    return code, self._get_default_fund_data(code, fund_names.get(code))
            
            # 使用线程池并行获取（最多5个并发）
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_code = {executor.submit(fetch_single, code): code for code in missing_codes}
                
                for future in as_completed(future_to_code):
                    code, data = future.result()
                    results[code] = data
        
        return results
    
    def invalidate_fund_cache(self, fund_code: str = None):
        """
        使基金缓存失效
        
        Args:
            fund_code: 基金代码，如果为None则清除所有缓存
        """
        self.cache.invalidate_cache(fund_code)
        logger.info(f"基金 {fund_code or 'all'} 缓存已清除")
    
    def get_cache_statistics(self) -> Dict:
        """
        获取缓存统计信息
        
        Returns:
            dict: 缓存统计
        """
        return self.cache.get_cache_stats()
    
    def get_historical_data(self, fund_code: str, days: int = 30, 
                          start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取基金历史数据（兼容 EnhancedFundData 接口）
        
        Args:
            fund_code: 基金代码
            days: 历史数据天数
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame: 历史数据
        """
        try:
            # 使用 MultiSourceFundData 的历史数据方法
            df = self.get_fund_nav_history(
                fund_code, 
                source='auto',
                start_date=start_date,
                end_date=end_date
            )
            
            if df is not None and not df.empty:
                # 转换列名为 EnhancedFundData 格式
                # Tushare 返回的是中文列名，需要映射为英文列名
                column_mapping = {
                    '净值日期': 'date',
                    '单位净值': 'nav',
                    '累计净值': 'accum_nav',
                    '日增长率': 'daily_return'
                }
                
                # 只映射存在的列（检查中文列名是否在 df 中）
                existing_mapping = {k: v for k, v in column_mapping.items() if k in df.columns}
                df = df.rename(columns=existing_mapping)
                
                # 如果指定了天数限制，进行截取
                # 先按日期升序排列，再取最后days条记录，确保获取最新的数据
                if days and len(df) > days:
                    df = df.sort_values('date', ascending=True).tail(days)
                
                logger.info(f"成功获取基金 {fund_code} 的 {len(df)} 条历史数据 (Tushare优先)")
                return df
            
            logger.warning(f"基金 {fund_code} 历史数据获取为空")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 历史数据失败: {e}")
            return pd.DataFrame()
    
    def get_performance_metrics(self, fund_code: str, days: int = 3650) -> Dict:
        """
        获取基金绩效指标（兼容 EnhancedFundData 接口）
        
        Args:
            fund_code: 基金代码
            days: 历史数据天数
            
        Returns:
            dict: 绩效指标
        """
        try:
            # 获取历史数据
            hist_data = self.get_historical_data(fund_code, days)
            
            if hist_data.empty or len(hist_data) < 2:
                return self._get_default_metrics()
            
            # 提取日收益率（需要转换列名）
            daily_growth_col = '日增长率' if '日增长率' in hist_data.columns else 'daily_return'
            if daily_growth_col in hist_data.columns:
                daily_returns = hist_data[daily_growth_col].dropna()
                # 处理百分比格式
                daily_returns = pd.to_numeric(daily_returns, errors='coerce')
                # 如果数值较大，是百分比格式，需要转换为小数
                if abs(daily_returns).mean() >= 0.01:
                    daily_returns = daily_returns / 100
            else:
                daily_returns = pd.Series([0.0])
            
            if len(daily_returns) < 2:
                return self._get_default_metrics()
            
            # 计算各种绩效指标
            return self._calculate_metrics(daily_returns, hist_data)
            
        except Exception as e:
            logger.error(f"计算基金 {fund_code} 绩效指标失败: {e}")
            return self._get_default_metrics()
    
    def _calculate_metrics(self, daily_returns: pd.Series, hist_data: pd.DataFrame) -> Dict:
        """
        计算绩效指标（与 EnhancedFundData 保持一致）
        分别计算不同时期的夏普比率：成立以来、近一年、今年以来
        """
        try:
            from shared.enhanced_config import PERFORMANCE_CONFIG, INVESTMENT_STRATEGY_CONFIG
        except ImportError:
            # 如果无法导入配置，使用默认值
            PERFORMANCE_CONFIG = {
                'trading_days_per_year': 250,
                'var_confidence': 0.05,
                'weights': {
                    'annualized_return': 0.3,
                    'sharpe_ratio': 0.25,
                    'max_drawdown': 0.2,
                    'volatility': 0.15,
                    'win_rate': 0.1
                }
            }
            INVESTMENT_STRATEGY_CONFIG = {
                'risk_free_rate': 0.02
            }
        
        # 获取配置参数
        risk_free_rate = INVESTMENT_STRATEGY_CONFIG['risk_free_rate']
        trading_days = PERFORMANCE_CONFIG['trading_days_per_year']
        var_confidence = PERFORMANCE_CONFIG['var_confidence']
        
        # 获取净值列名
        nav_col = '单位净值' if '单位净值' in hist_data.columns else 'nav'
        date_col = '日期' if '日期' in hist_data.columns else 'date'
        
        # 确保数据按日期升序排列（最早的在前）
        if date_col in hist_data.columns:
            hist_data = hist_data.sort_values(date_col, ascending=True).reset_index(drop=True)
        
        # 计算总收益率（成立以来）
        if nav_col in hist_data.columns:
            start_nav = float(hist_data[nav_col].iloc[0])
            end_nav = float(hist_data[nav_col].iloc[-1])
            total_return = (end_nav - start_nav) / start_nav if start_nav != 0 else 0.0
        else:
            total_return = 0.0
        
        # 计算年化收益率（成立以来）
        days = len(hist_data)
        if days > 0:
            annualized_return = (1 + total_return) ** (trading_days / days) - 1
        else:
            annualized_return = 0.0
        
        # 计算年化波动率（成立以来）
        volatility = daily_returns.std() * np.sqrt(trading_days)
        
        # 计算夏普比率（成立以来）- 使用全部数据
        sharpe_ratio_all = (annualized_return - risk_free_rate) / volatility if volatility != 0 else 0.0
        
        # 计算不同时期的夏普比率
        sharpe_ratio_1y = sharpe_ratio_all  # 默认使用全部数据
        sharpe_ratio_ytd = sharpe_ratio_all  # 默认使用全部数据
        
        # 获取日期列
        if date_col in hist_data.columns:
            hist_data_copy = hist_data.copy()
            hist_data_copy[date_col] = pd.to_datetime(hist_data_copy[date_col])
            now = pd.Timestamp.now()
            
            # 计算近一年夏普比率
            one_year_ago = now - pd.DateOffset(years=1)
            last_year_data = hist_data_copy[hist_data_copy[date_col] >= one_year_ago]
            if len(last_year_data) >= 30:  # 至少30个交易日数据
                last_year_returns = daily_returns[-len(last_year_data):]
                if len(last_year_returns) > 0:
                    vol_1y = last_year_returns.std() * np.sqrt(trading_days)
                    # 计算近一年年化收益率
                    start_nav_1y = float(last_year_data[nav_col].iloc[0]) if nav_col in last_year_data.columns else start_nav
                    end_nav_1y = float(last_year_data[nav_col].iloc[-1]) if nav_col in last_year_data.columns else end_nav
                    if start_nav_1y != 0:
                        total_return_1y = (end_nav_1y - start_nav_1y) / start_nav_1y
                        annualized_return_1y = (1 + total_return_1y) ** (trading_days / len(last_year_data)) - 1
                        sharpe_ratio_1y = (annualized_return_1y - risk_free_rate) / vol_1y if vol_1y != 0 else 0.0
            
            # 计算今年以来夏普比率
            ytd_start = pd.Timestamp(year=now.year, month=1, day=1)
            ytd_data = hist_data_copy[hist_data_copy[date_col] >= ytd_start]
            if len(ytd_data) >= 10:  # 至少10个交易日数据
                ytd_returns = daily_returns[-len(ytd_data):]
                if len(ytd_returns) > 0:
                    vol_ytd = ytd_returns.std() * np.sqrt(trading_days)
                    # 计算今年以来年化收益率
                    start_nav_ytd = float(ytd_data[nav_col].iloc[0]) if nav_col in ytd_data.columns else start_nav
                    end_nav_ytd = float(ytd_data[nav_col].iloc[-1]) if nav_col in ytd_data.columns else end_nav
                    if start_nav_ytd != 0:
                        total_return_ytd = (end_nav_ytd - start_nav_ytd) / start_nav_ytd
                        days_ytd = len(ytd_data)
                        annualized_return_ytd = (1 + total_return_ytd) ** (trading_days / days_ytd) - 1 if days_ytd > 0 else 0.0
                        sharpe_ratio_ytd = (annualized_return_ytd - risk_free_rate) / vol_ytd if vol_ytd != 0 else 0.0
        
        # 计算最大回撤
        if nav_col in hist_data.columns:
            nav_series = pd.to_numeric(hist_data[nav_col], errors='coerce')
            cumulative_max = nav_series.expanding().max()
            drawdown = (nav_series - cumulative_max) / cumulative_max
            max_drawdown = drawdown.min()
        else:
            max_drawdown = 0.0
        
        # 计算Calmar比率
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
        
        # 计算Sortino比率
        negative_returns = daily_returns[daily_returns < 0]
        downside_deviation = negative_returns.std() * np.sqrt(trading_days) if len(negative_returns) > 0 else volatility
        sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation if downside_deviation != 0 else 0.0
        
        # 计算VaR (95%)
        var_95 = daily_returns.quantile(var_confidence) if not daily_returns.empty else 0.0
        
        # 计算胜率
        win_rate = (daily_returns > 0).sum() / len(daily_returns) if len(daily_returns) > 0 else 0.0
        
        # 计算盈亏比
        positive_returns = daily_returns[daily_returns > 0]
        negative_returns = daily_returns[daily_returns < 0]
        avg_positive = positive_returns.mean() if len(positive_returns) > 0 else 0.0
        avg_negative = abs(negative_returns.mean()) if len(negative_returns) > 0 else 0.0
        profit_loss_ratio = avg_positive / avg_negative if avg_negative != 0 else 0.0
        
        # 计算综合评分
        weights = PERFORMANCE_CONFIG['weights']
        composite_score = (
            weights['annualized_return'] * max(0, min(1, (annualized_return + 0.5) / 1.0)) +
            weights['sharpe_ratio'] * max(0, min(1, (sharpe_ratio_all + 2) / 4.0)) +
            weights['max_drawdown'] * max(0, min(1, 1 - abs(max_drawdown) / 0.5)) +
            weights['volatility'] * max(0, min(1, 1 - volatility / 0.5)) +
            weights['win_rate'] * win_rate
        )
        
        return {
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio_all,  # 默认使用成立以来
            'sharpe_ratio_ytd': sharpe_ratio_ytd,
            'sharpe_ratio_1y': sharpe_ratio_1y,
            'sharpe_ratio_all': sharpe_ratio_all,
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'calmar_ratio': calmar_ratio,
            'sortino_ratio': sortino_ratio,
            'var_95': var_95,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'composite_score': composite_score,
            'total_return': total_return,
            'data_days': days
        }
    
    def _get_default_metrics(self) -> Dict:
        """
        获取默认绩效指标
        """
        return {
            'annualized_return': 0.0,
            'sharpe_ratio': 0.0,
            'sharpe_ratio_ytd': 0.0,
            'sharpe_ratio_1y': 0.0,
            'sharpe_ratio_all': 0.0,
            'max_drawdown': 0.0,
            'volatility': 0.0,
            'calmar_ratio': 0.0,
            'sortino_ratio': 0.0,
            'var_95': 0.0,
            'win_rate': 0.0,
            'profit_loss_ratio': 0.0,
            'composite_score': 0.0,
            'total_return': 0.0,
            'data_days': 0
        }
    
    def get_fund_basic_info(self, fund_code: str) -> Dict:
        """
        获取基金基本信息（兼容 EnhancedFundData 接口）
        
        Args:
            fund_code: 基金代码
            
        Returns:
            dict: 基金基本信息
        """
        try:
            basic_info = super().get_fund_basic_info(fund_code, source='auto')
            if basic_info:
                return basic_info
            
            # 降级到默认值
            return {
                'fund_code': fund_code,
                'fund_name': f'基金{fund_code}',
                'fund_type': '未知',
                'establish_date': None,
                'fund_company': '未知',
                'fund_manager': '未知',
                'management_fee': 0.0,
                'custody_fee': 0.0
            }
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 基本信息失败: {e}")
            return {
                'fund_code': fund_code,
                'fund_name': f'基金{fund_code}',
                'fund_type': '未知',
                'establish_date': None,
                'fund_company': '未知',
                'fund_manager': '未知',
                'management_fee': 0.0,
                'custody_fee': 0.0
            }

    def get_etf_list(self, max_retries: int = 3, retry_delay: float = 2.0) -> pd.DataFrame:
        """
        获取ETF列表数据
        
        优先使用akshare获取实时行情，失败时回退到tushare基础数据
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 初始重试延迟（秒），使用指数退避
            
        Returns:
            DataFrame: ETF列表数据，包含以下列：
                - etf_code: ETF代码
                - etf_name: ETF名称
                - current_price: 当前价格
                - change: 涨跌额
                - change_percent: 涨跌幅
                - volume: 成交量
                - turnover: 成交额
                - pe: 市盈率
                - pb: 市净率
        """
        # 第一步：尝试从akshare获取（带重试）
        etf_df = self._get_etf_list_from_akshare(max_retries, retry_delay)
        
        if not etf_df.empty:
            return etf_df
        
        # 第二步：akshare失败，尝试从tushare获取
        logger.warning("Akshare获取失败，尝试从Tushare获取ETF列表...")
        etf_df = self._get_etf_list_from_tushare()
        
        return etf_df
    
    def _get_etf_list_from_akshare(self, max_retries: int = 3, retry_delay: float = 2.0) -> pd.DataFrame:
        """
        从akshare获取ETF列表
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 初始重试延迟（秒）
            
        Returns:
            DataFrame: ETF列表数据
        """
        try:
            import akshare as ak
        except ImportError:
            logger.warning("akshare未安装，跳过akshare数据源")
            return pd.DataFrame()
        
        for attempt in range(max_retries):
            try:
                logger.info(f"从akshare获取ETF列表... (尝试 {attempt + 1}/{max_retries})")
                
                # 使用akshare获取ETF实时行情数据
                etf_df = ak.fund_etf_spot_em()
                
                if etf_df is None or etf_df.empty:
                    logger.warning("akshare返回空数据")
                    return pd.DataFrame()
                
                # 标准化列名映射
                column_mapping = {
                    '代码': 'etf_code',
                    '名称': 'etf_name',
                    '最新价': 'current_price',
                    '涨跌额': 'change',
                    '涨跌幅': 'change_percent',
                    '成交量': 'volume',
                    '成交额': 'turnover',
                    '市盈率': 'pe',
                    '市净率': 'pb'
                }
                
                # 只映射存在的列
                existing_mapping = {k: v for k, v in column_mapping.items() if k in etf_df.columns}
                etf_df = etf_df.rename(columns=existing_mapping)
                
                # 数据类型转换
                numeric_columns = ['current_price', 'change', 'change_percent', 'volume', 'turnover', 'pe', 'pb']
                for col in numeric_columns:
                    if col in etf_df.columns:
                        etf_df[col] = pd.to_numeric(etf_df[col], errors='coerce')
                
                # 添加数据源标识
                etf_df['data_source'] = 'akshare'
                
                logger.info(f"成功从akshare获取ETF列表，共 {len(etf_df)} 只ETF")
                return etf_df
                
            except Exception as e:
                if attempt < max_retries - 1:
                    sleep_time = retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(f"akshare获取失败 (尝试 {attempt + 1}/{max_retries}): {e}, {sleep_time}秒后重试...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"akshare获取ETF列表失败，已重试{max_retries}次: {e}")
        
        return pd.DataFrame()
    
    def _get_etf_list_from_tushare(self) -> pd.DataFrame:
        """
        从tushare获取ETF基础列表
        
        Returns:
            DataFrame: ETF列表数据（基础信息，无实时行情）
        """
        try:
            import tushare as ts
            
            logger.info("从tushare获取ETF列表...")
            
            # 获取tushare pro api（优先使用父类初始化的pro对象）
            if hasattr(self, 'tushare_pro') and self.tushare_pro is not None:
                pro = self.tushare_pro
            else:
                pro = ts.pro_api()
            
            # 获取ETF基础信息（market='E'表示场内，status='L'表示上市）
            etf_df = pro.fund_basic(market='E', status='L')
            
            if etf_df is None or etf_df.empty:
                logger.warning("tushare返回空数据")
                return pd.DataFrame()
            
            # 标准化列名映射
            column_mapping = {
                'ts_code': 'etf_code',
                'name': 'etf_name',
                'management': 'management',
                'custodian': 'custodian',
                'fund_type': 'fund_type',
                'found_date': 'found_date',
            }
            
            # 只映射存在的列
            existing_mapping = {k: v for k, v in column_mapping.items() if k in etf_df.columns}
            etf_df = etf_df.rename(columns=existing_mapping)
            
            # 尝试获取最新行情数据（如果可能）
            try:
                from datetime import datetime
                trade_date = datetime.now().strftime('%Y%m%d')
                daily_df = pro.fund_daily(trade_date=trade_date)
                
                if daily_df is not None and not daily_df.empty:
                    # 合并行情数据
                    daily_df = daily_df.rename(columns={
                        'ts_code': 'etf_code',
                        'close': 'current_price',
                        'change': 'change',
                        'pct_chg': 'change_percent',
                        'vol': 'volume',
                        'amount': 'turnover'
                    })
                    etf_df = etf_df.merge(
                        daily_df[['etf_code', 'current_price', 'change', 'change_percent', 'volume', 'turnover']],
                        on='etf_code',
                        how='left'
                    )
                    logger.info(f"成功合并tushare行情数据")
            except Exception as e:
                logger.warning(f"获取tushare行情数据失败: {e}，仅返回基础信息")
            
            # 添加数据源标识
            etf_df['data_source'] = 'tushare'
            
            logger.info(f"成功从tushare获取ETF列表，共 {len(etf_df)} 只ETF")
            return etf_df
            
        except Exception as e:
            logger.error(f"从tushare获取ETF列表失败: {e}")
            return pd.DataFrame()
    
    def get_etf_nav_history(self, etf_code: str, days: int = 30, 
                           start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取ETF净值历史数据
        
        Args:
            etf_code: ETF代码
            days: 历史数据天数
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame: ETF净值历史数据
        """
        try:
            import akshare as ak
            
            logger.info(f"开始获取ETF {etf_code} 净值历史数据...")
            
            # 使用akshare获取ETF历史净值
            # 注意：ETF基金代码通常需要加后缀，这里假设传入的是纯数字代码
            fund_code_with_suffix = f"{etf_code}" if etf_code.endswith('.OF') else f"{etf_code}.OF"
            
            # 获取历史净值数据
            df = ak.fund_open_fund_info_em(symbol=etf_code, indicator="单位净值走势", period="最大值")
            
            if df is None or df.empty:
                logger.warning(f"ETF {etf_code} 净值历史数据获取为空")
                return pd.DataFrame()
            
            # 标准化列名
            column_mapping = {
                '净值日期': 'date',
                '单位净值': 'nav',
                '累计净值': 'accum_nav',
                '日增长率': 'daily_return'
            }
            
            existing_mapping = {k: v for k, v in column_mapping.items() if k in df.columns}
            df = df.rename(columns=existing_mapping)
            
            # 数据类型转换
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
            numeric_columns = ['nav', 'accum_nav', 'daily_return']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 日期过滤
            if start_date:
                df = df[df['date'] >= start_date]
            if end_date:
                df = df[df['date'] <= end_date]
            
            # 天数限制
            if days and len(df) > days:
                df = df.tail(days)
            
            logger.info(f"成功获取ETF {etf_code} 净值历史数据 {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取ETF {etf_code} 净值历史数据失败: {e}")
            return pd.DataFrame()
    
    def get_etf_history(self, etf_code: str, days: int = 30) -> pd.DataFrame:
        """
        获取ETF行情历史数据
        
        Args:
            etf_code: ETF代码
            days: 历史数据天数
            
        Returns:
            DataFrame: ETF行情历史数据
        """
        try:
            import akshare as ak
            
            logger.info(f"开始获取ETF {etf_code} 行情历史数据...")
            
            # 使用akshare获取ETF历史行情
            df = ak.fund_etf_hist_em(symbol=etf_code, period="daily", start_date="", end_date="", adjust="")
            
            if df is None or df.empty:
                logger.warning(f"ETF {etf_code} 行情历史数据获取为空")
                return pd.DataFrame()
            
            # 标准化列名
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'turnover',
                '振幅': 'amplitude',
                '涨跌幅': 'change_percent',
                '涨跌额': 'change',
                '换手率': 'turnover_rate'
            }
            
            existing_mapping = {k: v for k, v in column_mapping.items() if k in df.columns}
            df = df.rename(columns=existing_mapping)
            
            # 数据类型转换
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'turnover', 
                             'amplitude', 'change_percent', 'change', 'turnover_rate']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 天数限制
            if days and len(df) > days:
                df = df.tail(days)
            
            logger.info(f"成功获取ETF {etf_code} 行情历史数据 {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取ETF {etf_code} 行情历史数据失败: {e}")
            return pd.DataFrame()
    
    # 类级别的QDII基金代码缓存（动态加载）
    _qdii_cache = None
    _cache_loaded = False
    
    @staticmethod
    def is_qdii_fund(fund_code: str, fund_name: str = None, use_dynamic: bool = True) -> bool:
        """
        判断是否为QDII基金
        
        采用多层检测策略：
        1. 静态代码列表（快速匹配已知QDII）
        2. 名称关键词匹配（无需网络请求）
        3. 动态数据源查询（akshare基金类型信息）
        
        Args:
            fund_code: 基金代码
            fund_name: 基金名称（可选，提高准确性）
            use_dynamic: 是否使用动态数据源查询（默认True）
        
        Returns:
            bool: 是否为QDII基金
        """
        # 第1层：静态代码列表（快速路径）
        if MultiSourceDataAdapter._is_in_static_qdii_list(fund_code):
            return True
        
        # 第2层：名称关键词匹配
        if fund_name and MultiSourceDataAdapter._is_qdii_by_name_keywords(fund_name):
            return True
        
        # 第3层：动态数据源查询
        if use_dynamic:
            return MultiSourceDataAdapter._is_qdii_by_data_source(fund_code)
        
        return False
    
    @staticmethod
    def _is_in_static_qdii_list(fund_code: str) -> bool:
        """静态代码列表检测（快速路径）"""
        # 常见QDII基金代码前缀/特征
        QDII_FUND_CODES = {
            # 大成标普500
            '096001', '008401', '008402',
            # 富国全球科技互联网
            '100055', 
            # 富国全球消费精选
            '012061', '012060', '012062',
            # 广发道琼斯石油
            '006680', '006679', '006681',
            # 国富全球科技互联
            '006373', '006374',
            # 宏利印度股票
            '006105', '006106',
            # 华安法国CAC40
            '021539', '021540',
            # 华安国际龙头(DAX)
            '015015', '015016',
            # 华安纳斯达克100
            '040046', '040047', '014978', '014979',
            # 华宝油气
            '007844', '007845',
            # 建信富时100
            '008708', '008707', '008706',
            # 景顺长城全球半导体芯片
            '501225', '501226',
            # 美国消费
            '162415', 
            # 天弘标普500
            '007721', '007722',
        }
        return fund_code in QDII_FUND_CODES
    
    @staticmethod
    def _is_qdii_by_name_keywords(fund_name: str) -> bool:
        """
        通过基金名称关键词判断是否为QDII基金
        
        检测关键词包括：
        - QDII标识
        - 海外市场关键词
        - 国际指数关键词
        """
        if not fund_name:
            return False
            
        fund_name_upper = fund_name.upper()
        
        # 直接QDII标识
        if 'QDII' in fund_name_upper:
            return True
        
        # 海外市场关键词（中英文）
        overseas_keywords = [
            # 市场关键词
            '全球', '国际', '海外', '环球', '世界',
            'GLOBAL', 'INTERNATIONAL', 'OVERSEAS', 'WORLD', 'WORLDWIDE',
            # 地区关键词
            '美国', '美股', '港股', '香港', '日本', '欧洲', '德国', '法国', '英国',
            'US', 'USA', 'AMERICA', 'HONG KONG', 'JAPAN', 'EUROPE', 'GERMANY', 'FRANCE', 'UK',
            # 指数关键词
            '纳斯达克', '标普', '道琼斯', '印度', '越南', '富时', 'CAC40', 'DAX', 'MSCI',
            'NASDAQ', 'S&P', 'DOW JONES', 'INDIA', 'VIETNAM', 'FTSE', 'MSCI',
            # 商品/另类投资
            '原油', '石油', '黄金', '商品', 'REITs',
            'OIL', 'CRUDE', 'GOLD', 'COMMODITY',
        ]
        
        for keyword in overseas_keywords:
            if keyword in fund_name_upper:
                return True
        
        return False
    
    @staticmethod
    def _is_qdii_by_data_source(fund_code: str) -> bool:
        """
        通过数据源动态查询基金类型
        
        使用akshare获取基金基本信息，检查基金类型字段
        """
        # 先检查缓存
        if MultiSourceDataAdapter._qdii_cache is not None:
            return fund_code in MultiSourceDataAdapter._qdii_cache
        
        try:
            import akshare as ak
            
            # 加载基金列表（带缓存）
            fund_list = ak.fund_name_em()
            
            # 检查基金类型列是否包含QDII
            if '基金类型' in fund_list.columns:
                qdii_funds = fund_list[fund_list['基金类型'].str.contains('QDII', na=False)]
                MultiSourceDataAdapter._qdii_cache = set(qdii_funds['基金代码'].tolist())
                MultiSourceDataAdapter._cache_loaded = True
                
                logger.info(f"QDII基金缓存已加载，共 {len(MultiSourceDataAdapter._qdii_cache)} 只基金")
                return fund_code in MultiSourceDataAdapter._qdii_cache
                
        except Exception as e:
            logger.warning(f"动态获取QDII基金列表失败: {e}")
        
        return False
    
    @staticmethod
    def refresh_qdii_cache():
        """
        刷新QDII基金缓存
        
        手动刷新缓存以获取最新的QDII基金列表
        """
        MultiSourceDataAdapter._qdii_cache = None
        MultiSourceDataAdapter._cache_loaded = False
        # 触发重新加载
        return MultiSourceDataAdapter._is_qdii_by_data_source('000000')  # 传入无效代码仅触发缓存加载