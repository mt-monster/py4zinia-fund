#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量基金数据获取器
优化Tushare API调用，通过批量获取减少API调用次数

核心优化策略:
1. 预加载全量基金列表，本地过滤所需基金
2. 批量获取多只基金的历史净值
3. 智能缓存和预加载
4. 自动降级到备用数据源

使用示例:
    fetcher = BatchFundDataFetcher(tushare_token="your_token")
    
    # 批量获取多只基金的净值
    results = fetcher.batch_get_nav_history(['000001', '000002', '000003'])
    
    # 批量获取最新净值
    latest_navs = fetcher.batch_get_latest_nav(['000001', '000002', '000003'])
"""

import pandas as pd
import numpy as np
import tushare as ts
import akshare as ak
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Union, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

from .rate_limiter import get_tushare_limiter, rate_limited

logger = logging.getLogger(__name__)


class BatchFundDataFetcher:
    """
    批量基金数据获取器
    
    主要优化点:
    1. 全量数据预加载: 一次性获取所有基金数据，本地过滤
    2. 智能缓存: 多级缓存策略减少重复调用
    3. 批量API调用: 尽可能使用批量接口
    4. 速率控制: 自动处理API频率限制
    """
    
    # 缓存配置
    CACHE_TTL = {
        'full_nav_dump': 3600,      # 全量净值缓存1小时
        'fund_basic': 86400,         # 基金基本信息缓存1天
        'latest_nav': 1800,          # 最新净值缓存30分钟
        'nav_history': 3600          # 净值历史缓存1小时
    }
    
    def __init__(self, tushare_token: Optional[str] = None, 
                 use_cache: bool = True, max_workers: int = 3):
        """
        初始化批量获取器
        
        Args:
            tushare_token: Tushare API token
            use_cache: 是否启用缓存
            max_workers: 并行处理的最大线程数（降低以避免频率限制）
        """
        self.tushare_token = tushare_token
        self.use_cache = use_cache
        self.max_workers = max_workers
        
        # 初始化Tushare
        self.pro = None
        if tushare_token:
            try:
                ts.set_token(tushare_token)
                self.pro = ts.pro_api()
                logger.info("Tushare初始化成功")
            except Exception as e:
                logger.warning(f"Tushare初始化失败: {e}")
        
        # 内存缓存
        self._cache = {}
        self._cache_time = {}
        self._cache_lock = threading.RLock()
        
        # 全量数据缓存
        self._all_fund_nav_cache = None
        self._all_fund_basic_cache = None
        self._last_full_update = None
        
        # 统计信息
        self._stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'bulk_loads': 0
        }
        
        logger.info(f"BatchFundDataFetcher初始化完成 (缓存: {use_cache}, 最大线程: {max_workers})")
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if not self.use_cache:
            return None
        
        with self._cache_lock:
            if key in self._cache:
                cache_time = self._cache_time.get(key, 0)
                ttl = self.CACHE_TTL.get(key.split(':')[0], 3600)
                
                if time.time() - cache_time < ttl:
                    self._stats['cache_hits'] += 1
                    logger.debug(f"缓存命中: {key}")
                    return self._cache[key]
                else:
                    # 缓存过期
                    del self._cache[key]
                    del self._cache_time[key]
        
        self._stats['cache_misses'] += 1
        return None
    
    def _set_cache(self, key: str, value: Any):
        """设置缓存"""
        if not self.use_cache:
            return
        
        with self._cache_lock:
            self._cache[key] = value
            self._cache_time[key] = time.time()
            
            # 清理过期缓存
            if len(self._cache) > 1000:
                self._cleanup_cache()
    
    def _cleanup_cache(self):
        """清理过期缓存"""
        now = time.time()
        expired_keys = []
        
        for key, cache_time in list(self._cache_time.items()):
            ttl = self.CACHE_TTL.get(key.split(':')[0], 3600)
            if now - cache_time > ttl:
                expired_keys.append(key)
        
        for key in expired_keys[:100]:
            self._cache.pop(key, None)
            self._cache_time.pop(key, None)
        
        logger.debug(f"清理 {len(expired_keys)} 条过期缓存")
    
    def _call_tushare_with_rate_limit(self, api_func, *args, **kwargs) -> pd.DataFrame:
        """
        带速率限制的Tushare API调用
        
        Args:
            api_func: Tushare API函数
            *args, **kwargs: API参数
            
        Returns:
            pd.DataFrame: API返回数据
        """
        limiter = get_tushare_limiter('fund_nav')
        
        with limiter.acquire(timeout=65):  # 最多等待65秒
            self._stats['api_calls'] += 1
            return api_func(*args, **kwargs)
    
    def preload_all_fund_nav(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        预加载所有基金的最新净值数据
        
        这是核心优化方法: 使用 fund_nav 接口不带 ts_code 参数
        可以一次性获取多只基金的数据，大幅减少API调用
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            pd.DataFrame: 所有基金的最新净值数据
        """
        cache_key = 'full_nav_dump'
        
        if not force_refresh:
            cached = self._get_cache(cache_key)
            if cached is not None:
                logger.info(f"使用缓存的全量净值数据 ({len(cached)} 条)")
                return cached
        
        if self.pro is None:
            logger.warning("Tushare未初始化，无法获取全量数据")
            return pd.DataFrame()
        
        try:
            logger.info("开始从Tushare获取全量基金净值数据...")
            start_time = time.time()
            
            # 获取最近一个交易日
            trade_date = self._get_latest_trade_date()
            
            # 批量获取基金净值 - 核心优化: 不带ts_code参数获取所有基金
            # Tushare API要求使用 nav_date 参数名
            df = self._call_tushare_with_rate_limit(
                self.pro.fund_nav,
                nav_date=trade_date
            )
            
            elapsed = time.time() - start_time
            self._stats['bulk_loads'] += 1
            
            if df is not None and not df.empty:
                # 标准化列名
                df = df.rename(columns={
                    'ts_code': 'fund_code',
                    'nav_date': 'date',
                    'unit_nav': 'nav',
                    'accum_nav': 'accum_nav'
                })
                
                # 处理日增长率（如果Tushare返回）
                if 'nv_daily_growth' in df.columns:
                    df = df.rename(columns={'nv_daily_growth': 'daily_return'})
                elif 'daily_profit' in df.columns:
                    df = df.rename(columns={'daily_profit': 'daily_return'})
                
                # 移除.OF后缀
                df['fund_code'] = df['fund_code'].str.replace('.OF', '', regex=False)
                
                # 缓存数据
                self._set_cache(cache_key, df)
                self._last_full_update = datetime.now()
                
                logger.info(f"全量净值数据获取成功: {len(df)} 只基金, 耗时 {elapsed:.2f}s")
                return df
            else:
                logger.warning("Tushare返回空数据")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"获取全量净值数据失败: {e}")
            return pd.DataFrame()
    
    def batch_get_latest_nav(self, fund_codes: List[str], 
                            use_preload: bool = True) -> Dict[str, Dict]:
        """
        批量获取多只基金的最新净值
        
        Args:
            fund_codes: 基金代码列表
            use_preload: 是否使用预加载的全量数据
            
        Returns:
            Dict[str, Dict]: 基金代码 -> 净值数据
        """
        if not fund_codes:
            return {}
        
        results = {}
        missing_codes = set(fund_codes)
        
        # 步骤1: 尝试从预加载的全量数据获取
        if use_preload:
            all_nav = self.preload_all_fund_nav()
            if not all_nav.empty:
                for code in list(missing_codes):
                    fund_data = all_nav[all_nav['fund_code'] == code]
                    if not fund_data.empty:
                        row = fund_data.iloc[0]
                        # 获取日增长率（如果存在）
                        daily_return = 0.0
                        if 'daily_return' in row:
                            daily_return = float(row['daily_return']) if pd.notna(row['daily_return']) else 0.0
                        
                        results[code] = {
                            'fund_code': code,
                            'date': row.get('date'),
                            'nav': float(row.get('nav', 0)),
                            'accum_nav': float(row.get('accum_nav', 0)),
                            'daily_return': daily_return,
                            'source': 'tushare_bulk'
                        }
                        missing_codes.remove(code)
                
                logger.info(f"从全量数据获取: {len(results)}/{len(fund_codes)} 只基金")
        
        # 步骤2: 补充获取日增长率（对于从Tushare获取但缺少daily_return的基金）
        codes_need_daily_return = [code for code in results if results[code].get('daily_return', 0) == 0]
        if codes_need_daily_return:
            logger.debug(f"为 {len(codes_need_daily_return)} 只基金补充获取日增长率")
            for code in codes_need_daily_return:
                try:
                    # 从Akshare获取日增长率
                    nav_data = self._get_nav_from_akshare(code)
                    if nav_data and nav_data.get('daily_return', 0) != 0:
                        results[code]['daily_return'] = nav_data['daily_return']
                        results[code]['source'] = 'tushare_bulk+akshare'
                except Exception as e:
                    logger.debug(f"补充获取 {code} 日增长率失败: {e}")
        
        # 步骤3: 对缺失的基金，使用备用数据源
        if missing_codes:
            logger.info(f"从备用数据源获取 {len(missing_codes)} 只基金")
            
            for code in missing_codes:
                try:
                    # 优先使用Akshare
                    nav_data = self._get_nav_from_akshare(code)
                    if nav_data:
                        results[code] = nav_data
                    else:
                        logger.warning(f"无法获取基金 {code} 的净值数据")
                except Exception as e:
                    logger.warning(f"获取基金 {code} 失败: {e}")
        
        return results
    
    def batch_get_nav_history(self, fund_codes: List[str], 
                             days: int = 365) -> Dict[str, pd.DataFrame]:
        """
        批量获取多只基金的历史净值
        
        策略:
        1. 首先尝试从缓存获取
        2. 然后使用Akshare批量获取（Akshare对单只基金获取较好）
        3. 最后并行获取缺失的数据
        
        Args:
            fund_codes: 基金代码列表
            days: 历史数据天数
            
        Returns:
            Dict[str, pd.DataFrame]: 基金代码 -> 历史数据DataFrame
        """
        if not fund_codes:
            return {}
        
        results = {}
        missing_codes = []
        
        # 步骤1: 尝试从缓存获取
        for code in fund_codes:
            cache_key = f"nav_history:{code}:{days}"
            cached = self._get_cache(cache_key)
            if cached is not None:
                results[code] = cached
            else:
                missing_codes.append(code)
        
        if not missing_codes:
            logger.info(f"所有 {len(fund_codes)} 只基金数据均来自缓存")
            return results
        
        logger.info(f"批量获取 {len(missing_codes)}/{len(fund_codes)} 只基金历史数据")
        
        # 步骤2: 并行获取缺失的数据（使用Akshare，限制并发数）
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_code = {
                executor.submit(self._get_nav_history_from_akshare, code, days): code 
                for code in missing_codes
            }
            
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    df = future.result()
                    if df is not None and not df.empty:
                        results[code] = df
                        # 缓存结果
                        cache_key = f"nav_history:{code}:{days}"
                        self._set_cache(cache_key, df)
                except Exception as e:
                    logger.error(f"获取基金 {code} 历史数据失败: {e}")
        
        return results
    
    def _get_nav_from_akshare(self, fund_code: str) -> Optional[Dict]:
        """从Akshare获取单只基金的最新净值"""
        try:
            df = ak.fund_open_fund_info_em(symbol=fund_code, indicator='单位净值走势', period='1年')
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                return {
                    'fund_code': fund_code,
                    'date': str(latest.get('净值日期', '')),
                    'nav': float(latest.get('单位净值', 0)),
                    'daily_return': float(latest.get('日增长率', 0)),
                    'source': 'akshare'
                }
        except Exception as e:
            logger.debug(f"Akshare获取 {fund_code} 失败: {e}")
        return None
    
    def _get_nav_history_from_akshare(self, fund_code: str, days: int) -> Optional[pd.DataFrame]:
        """从Akshare获取基金历史净值"""
        try:
            df = ak.fund_open_fund_info_em(symbol=fund_code, indicator='单位净值走势', period='最大值')
            if df is not None and not df.empty:
                # 标准化列名
                df = df.rename(columns={
                    '净值日期': 'date',
                    '单位净值': 'nav',
                    '日增长率': 'daily_return'
                })
                
                # 转换日期格式
                df['date'] = pd.to_datetime(df['date'])
                
                # 按日期排序
                df = df.sort_values('date', ascending=True)
                
                # 过滤日期范围
                if days < 9999:
                    start_date = datetime.now() - timedelta(days=days)
                    df = df[df['date'] >= start_date]
                
                # 确保数值类型正确
                df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
                df['daily_return'] = pd.to_numeric(df['daily_return'], errors='coerce')
                
                return df.dropna(subset=['nav'])
        except Exception as e:
            logger.debug(f"Akshare获取 {fund_code} 历史数据失败: {e}")
        return None
    
    def _get_latest_trade_date(self) -> str:
        """获取最近一个交易日"""
        try:
            # 尝试从Tushare获取
            if self.pro:
                df = self.pro.trade_cal(exchange='SSE', is_open='1', 
                                       end_date=datetime.now().strftime('%Y%m%d'),
                                       limit=1)
                if not df.empty:
                    return df.iloc[0]['cal_date']
        except Exception:
            pass
        
        # 默认返回今天或昨天
        now = datetime.now()
        if now.weekday() >= 5:  # 周末
            days_back = now.weekday() - 4
            return (now - timedelta(days=days_back)).strftime('%Y%m%d')
        return now.strftime('%Y%m%d')
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'api_calls': self._stats['api_calls'],
            'cache_hits': self._stats['cache_hits'],
            'cache_misses': self._stats['cache_misses'],
            'bulk_loads': self._stats['bulk_loads'],
            'cache_size': len(self._cache),
            'last_full_update': self._last_full_update.isoformat() if self._last_full_update else None
        }
    
    def clear_cache(self):
        """清除所有缓存"""
        with self._cache_lock:
            self._cache.clear()
            self._cache_time.clear()
            self._all_fund_nav_cache = None
            self._last_full_update = None
        logger.info("缓存已清除")


# 便捷函数
def batch_get_fund_nav(fund_codes: List[str], 
                      tushare_token: Optional[str] = None,
                      use_cache: bool = True) -> Dict[str, Dict]:
    """
    批量获取基金净值的便捷函数
    
    Args:
        fund_codes: 基金代码列表
        tushare_token: Tushare token
        use_cache: 是否使用缓存
        
    Returns:
        Dict[str, Dict]: 基金代码 -> 净值数据
    """
    fetcher = BatchFundDataFetcher(tushare_token=tushare_token, use_cache=use_cache)
    return fetcher.batch_get_latest_nav(fund_codes)


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("=" * 60)
    print("批量基金数据获取器测试")
    print("=" * 60)
    
    # 测试基金列表
    test_codes = ['000001', '000002', '000003', '021539', '100055']
    
    fetcher = BatchFundDataFetcher()
    
    # 测试批量获取
    print("\n测试批量获取最新净值:")
    results = fetcher.batch_get_latest_nav(test_codes)
    
    for code, data in results.items():
        print(f"  {code}: NAV={data.get('nav')}, Date={data.get('date')}, Source={data.get('source')}")
    
    print(f"\n统计信息: {fetcher.get_stats()}")
