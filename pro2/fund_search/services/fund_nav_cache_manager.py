#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金净值缓存管理器

三级缓存策略：
1. L1 - 内存缓存（15分钟TTL）：使用LRU缓存最近访问的基金数据
2. L2 - 数据库缓存（1天有效）：按日期存储每只基金的历史净值
3. L3 - 数据源（降级方案）：当缓存缺失时从Tushare/AKShare获取
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import threading
from functools import wraps
import hashlib
from sqlalchemy import text

logger = logging.getLogger(__name__)


class MemoryCacheEntry:
    """内存缓存条目"""
    def __init__(self, data: Any, ttl_minutes: int = 15):
        self.data = data
        self.timestamp = datetime.now()
        self.ttl = timedelta(minutes=ttl_minutes)
        self.access_count = 1
    
    def is_expired(self) -> bool:
        return datetime.now() - self.timestamp > self.ttl


class FundNavCacheManager:
    """
    基金净值缓存管理器
    
    使用说明：
    1. 实时数据（日涨跌幅）：不缓存，直接调用get_fund_realtime
    2. 昨日数据：使用get_yesterday_data，内存缓存15分钟
    3. 绩效指标：使用get_performance_metrics，数据库缓存1天
    4. 历史净值：使用get_fund_nav_history，数据库缓存1天
    """
    
    # 单例模式
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_manager=None, default_ttl_minutes: int = 15):
        if self._initialized:
            return
            
        self.db = db_manager
        self.default_ttl = default_ttl_minutes
        self._memory_cache: Dict[str, MemoryCacheEntry] = {}
        self._cache_lock = threading.RLock()
        self._max_memory_entries = 200
        self._initialized = True
        
        logger.info(f"FundNavCacheManager 初始化完成，默认内存缓存TTL={default_ttl_minutes}分钟")
    
    def _get_cache_key(self, fund_code: str, data_type: str, date_str: str = None) -> str:
        """生成缓存键"""
        if date_str is None:
            date_str = datetime.now().strftime('%Y%m%d')
        return f"{data_type}:{fund_code}:{date_str}"
    
    # ==================== L1 内存缓存操作 ====================
    
    def get_from_memory(self, key: str) -> Optional[Any]:
        """从内存缓存获取数据"""
        with self._cache_lock:
            entry = self._memory_cache.get(key)
            if entry is None:
                return None
            
            if entry.is_expired():
                del self._memory_cache[key]
                logger.debug(f"内存缓存过期清除: {key}")
                return None
            
            entry.access_count += 1
            logger.debug(f"内存缓存命中: {key}, 访问次数: {entry.access_count}")
            return entry.data
    
    def set_to_memory(self, key: str, data: Any, ttl_minutes: int = None):
        """写入内存缓存"""
        if ttl_minutes is None:
            ttl_minutes = self.default_ttl
            
        with self._cache_lock:
            self._memory_cache[key] = MemoryCacheEntry(data, ttl_minutes)
            
            # LRU清理：当内存缓存超过上限时，清理最久未访问的
            if len(self._memory_cache) > self._max_memory_entries:
                oldest_key = min(
                    self._memory_cache.keys(),
                    key=lambda k: self._memory_cache[k].timestamp
                )
                del self._memory_cache[oldest_key]
                logger.debug(f"内存缓存LRU清理: {oldest_key}")
    
    def invalidate_memory_cache(self, pattern: str = None):
        """使内存缓存失效"""
        with self._cache_lock:
            if pattern is None:
                count = len(self._memory_cache)
                self._memory_cache.clear()
                logger.info(f"清除所有内存缓存，共{count}条")
            else:
                keys_to_remove = [
                    k for k in list(self._memory_cache.keys())
                    if pattern in k
                ]
                for key in keys_to_remove:
                    del self._memory_cache[key]
                logger.info(f"清除匹配'{pattern}'的内存缓存，共{len(keys_to_remove)}条")
    
    # ==================== L2 数据库缓存操作 ====================
    
    def get_fund_nav_from_db(self, fund_code: str, days: int = 365) -> Optional[pd.DataFrame]:
        """从数据库缓存获取净值数据（最近1天内的缓存有效）"""
        if not self.db:
            return None
        
        try:
            # 只获取最近1天的数据（缓存策略：1天有效）
            start_date = (datetime.now() - timedelta(days=days + 5)).strftime('%Y-%m-%d')
            
            sql = """
                SELECT nav_date, nav_value, accum_nav, daily_return, data_source
                FROM fund_nav_cache
                WHERE fund_code = :fund_code
                  AND nav_date >= :start_date
                ORDER BY nav_date ASC
            """
            
            df = self.db.execute_query(sql, {
                'fund_code': fund_code,
                'start_date': start_date
            })
            
            if df.empty:
                logger.debug(f"数据库缓存未命中: {fund_code}")
                return None
            
            # 检查数据新鲜度（最新数据应该是昨天或今天）
            latest_date = df['nav_date'].max()
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            # 对于QDII基金，允许延迟2天
            is_qdii = self._is_qdii_fund(fund_code)
            max_acceptable_date = today - timedelta(days=3 if is_qdii else 2)
            
            if pd.to_datetime(latest_date).date() < max_acceptable_date:
                logger.warning(f"基金 {fund_code} 缓存数据过期: 最新数据{latest_date}，需要更新")
                return None
            
            logger.info(f"数据库缓存命中: {fund_code}, {len(df)}条记录, 最新{latest_date}")
            return df
            
        except Exception as e:
            logger.error(f"从数据库获取缓存失败 {fund_code}: {e}")
            return None
    
    def save_fund_nav_to_db(self, fund_code: str, df: pd.DataFrame, source: str):
        """保存净值数据到数据库缓存"""
        if not self.db or df.empty:
            return
        
        try:
            insert_sql = """
                INSERT INTO fund_nav_cache 
                (fund_code, nav_date, nav_value, accum_nav, daily_return, data_source)
                VALUES (:fund_code, :nav_date, :nav_value, 
                        :accum_nav, :daily_return, :source)
                ON DUPLICATE KEY UPDATE
                nav_value = VALUES(nav_value),
                accum_nav = VALUES(accum_nav),
                daily_return = VALUES(daily_return),
                data_source = VALUES(data_source),
                updated_at = NOW()
            """
            
            records = []
            for _, row in df.iterrows():
                nav_date = row['date']
                if isinstance(nav_date, pd.Timestamp):
                    nav_date = nav_date.strftime('%Y-%m-%d')
                elif isinstance(nav_date, datetime):
                    nav_date = nav_date.strftime('%Y-%m-%d')
                
                records.append({
                    'fund_code': fund_code,
                    'nav_date': nav_date,
                    'nav_value': float(row['nav']) if pd.notna(row.get('nav')) else None,
                    'accum_nav': float(row['accum_nav']) if pd.notna(row.get('accum_nav')) else None,
                    'daily_return': float(row['daily_return']) if pd.notna(row.get('daily_return')) else None,
                    'source': source
                })
            
            # 批量插入
            with self.db.engine.connect() as conn:
                for record in records:
                    conn.execute(text(insert_sql), record)
                conn.commit()
            
            # 更新元数据
            self._update_cache_metadata(fund_code, df, source)
            
            logger.info(f"保存到数据库缓存: {fund_code}, {len(records)}条记录")
            
        except Exception as e:
            logger.error(f"保存到数据库缓存失败 {fund_code}: {e}")
    
    def get_performance_from_db(self, fund_code: str) -> Optional[Dict]:
        """从数据库获取绩效指标（1天内有效）- 使用 fund_analysis_results 表"""
        if not self.db:
            return None
        
        try:
            sql = """
                SELECT 
                    annualized_return, max_drawdown, volatility,
                    sharpe_ratio, sharpe_ratio_1y, sharpe_ratio_ytd, sharpe_ratio_all,
                    calmar_ratio, sortino_ratio, var_95,
                    composite_score, total_return,
                    analysis_date as calc_date
                FROM fund_analysis_results
                WHERE fund_code = :fund_code
                  AND analysis_date >= DATE_SUB(CURDATE(), INTERVAL 1 DAY)
                ORDER BY analysis_date DESC, updated_at DESC
                LIMIT 1
            """
            
            df = self.db.execute_query(sql, {'fund_code': fund_code})
            
            if df.empty:
                return None
            
            row = df.iloc[0]
            return {
                'annualized_return': float(row['annualized_return']) if pd.notna(row['annualized_return']) else None,
                'max_drawdown': float(row['max_drawdown']) if pd.notna(row['max_drawdown']) else None,
                'volatility': float(row['volatility']) if pd.notna(row['volatility']) else None,
                'sharpe_ratio': float(row['sharpe_ratio']) if pd.notna(row['sharpe_ratio']) else None,
                'sharpe_ratio_1y': float(row['sharpe_ratio_1y']) if pd.notna(row['sharpe_ratio_1y']) else None,
                'sharpe_ratio_ytd': float(row['sharpe_ratio_ytd']) if pd.notna(row['sharpe_ratio_ytd']) else None,
                'sharpe_ratio_all': float(row['sharpe_ratio_all']) if pd.notna(row['sharpe_ratio_all']) else None,
                'calmar_ratio': float(row['calmar_ratio']) if pd.notna(row['calmar_ratio']) else None,
                'sortino_ratio': float(row['sortino_ratio']) if pd.notna(row['sortino_ratio']) else None,
                'var_95': float(row['var_95']) if pd.notna(row['var_95']) else None,
                'composite_score': float(row['composite_score']) if pd.notna(row['composite_score']) else None,
                'risk_score': None,  # fund_analysis_results 无此字段
                'return_score': None,  # fund_analysis_results 无此字段
                'calc_date': row['calc_date'].strftime('%Y-%m-%d') if hasattr(row['calc_date'], 'strftime') else str(row['calc_date'])
            }
            
        except Exception as e:
            logger.error(f"获取绩效缓存失败 {fund_code}: {e}")
            return None
    
    def save_performance_to_db(self, fund_code: str, metrics: Dict, calc_date: str = None):
        """保存绩效指标到数据库 - 使用 fund_analysis_results 表"""
        if not self.db:
            return
        
        if calc_date is None:
            calc_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # 获取基金名称
            fund_name = None
            try:
                name_sql = "SELECT fund_name FROM fund_basic_info WHERE fund_code = :fund_code LIMIT 1"
                name_df = self.db.execute_query(name_sql, {'fund_code': fund_code})
                if not name_df.empty:
                    fund_name = name_df.iloc[0]['fund_name']
            except:
                pass
            
            if not fund_name:
                fund_name = f"基金{fund_code}"
            
            sql = """
                INSERT INTO fund_analysis_results (
                    fund_code, fund_name, analysis_date,
                    annualized_return, max_drawdown, volatility,
                    sharpe_ratio, sharpe_ratio_1y, sharpe_ratio_ytd, sharpe_ratio_all,
                    calmar_ratio, sortino_ratio, var_95,
                    composite_score, total_return
                ) VALUES (
                    :fund_code, :fund_name, :analysis_date,
                    :annualized_return, :max_drawdown, :volatility,
                    :sharpe_ratio, :sharpe_ratio_1y, :sharpe_ratio_ytd, :sharpe_ratio_all,
                    :calmar_ratio, :sortino_ratio, :var_95,
                    :composite_score, :total_return
                )
                ON DUPLICATE KEY UPDATE
                fund_name = VALUES(fund_name),
                annualized_return = VALUES(annualized_return),
                max_drawdown = VALUES(max_drawdown),
                volatility = VALUES(volatility),
                sharpe_ratio = VALUES(sharpe_ratio),
                sharpe_ratio_1y = VALUES(sharpe_ratio_1y),
                sharpe_ratio_ytd = VALUES(sharpe_ratio_ytd),
                sharpe_ratio_all = VALUES(sharpe_ratio_all),
                calmar_ratio = VALUES(calmar_ratio),
                sortino_ratio = VALUES(sortino_ratio),
                var_95 = VALUES(var_95),
                composite_score = VALUES(composite_score),
                total_return = VALUES(total_return),
                updated_at = NOW()
            """
            
            params = {
                'fund_code': fund_code,
                'fund_name': fund_name,
                'analysis_date': calc_date,
                'annualized_return': metrics.get('annualized_return'),
                'max_drawdown': metrics.get('max_drawdown'),
                'volatility': metrics.get('volatility'),
                'sharpe_ratio': metrics.get('sharpe_ratio'),
                'sharpe_ratio_1y': metrics.get('sharpe_ratio_1y'),
                'sharpe_ratio_ytd': metrics.get('sharpe_ratio_ytd'),
                'sharpe_ratio_all': metrics.get('sharpe_ratio_all'),
                'calmar_ratio': metrics.get('calmar_ratio'),
                'sortino_ratio': metrics.get('sortino_ratio'),
                'var_95': metrics.get('var_95'),
                'composite_score': metrics.get('composite_score'),
                'total_return': metrics.get('annualized_return')  # 使用年化收益作为总收益
            }
            
            with self.db.engine.connect() as conn:
                conn.execute(text(sql), params)
                conn.commit()
            
            logger.info(f"保存绩效缓存到 fund_analysis_results: {fund_code}, 日期{calc_date}")
            
        except Exception as e:
            logger.error(f"保存绩效缓存失败 {fund_code}: {e}")
    
    def _update_cache_metadata(self, fund_code: str, df: pd.DataFrame, source: str):
        """更新缓存元数据"""
        if df.empty:
            return
        
        try:
            earliest = df['date'].min()
            latest = df['date'].max()
            
            if isinstance(earliest, pd.Timestamp):
                earliest = earliest.strftime('%Y-%m-%d')
            if isinstance(latest, pd.Timestamp):
                latest = latest.strftime('%Y-%m-%d')
            
            # 下次同步时间：QDII基金T+2晚上，普通基金T+1晚上
            is_qdii = self._is_qdii_fund(fund_code)
            next_sync = datetime.now() + timedelta(days=2 if is_qdii else 1)
            next_sync = next_sync.replace(hour=22, minute=0, second=0)
            
            sql = """
                INSERT INTO fund_cache_metadata 
                (fund_code, earliest_date, latest_date, total_records, 
                 last_sync_at, next_sync_at, sync_status, data_source)
                VALUES (:fund_code, :earliest, :latest, :count,
                        NOW(), :next_sync, 'completed', :source)
                ON DUPLICATE KEY UPDATE
                earliest_date = LEAST(earliest_date, :earliest),
                latest_date = GREATEST(latest_date, :latest),
                total_records = total_records + :new_count,
                last_sync_at = NOW(),
                next_sync_at = :next_sync,
                sync_status = 'completed',
                sync_fail_count = 0,
                data_source = :source
            """
            
            with self.db.engine.connect() as conn:
                conn.execute(text(sql), {
                    'fund_code': fund_code,
                    'earliest': earliest,
                    'latest': latest,
                    'count': len(df),
                    'new_count': len(df),
                    'next_sync': next_sync,
                    'source': source
                })
                conn.commit()
                
        except Exception as e:
            logger.error(f"更新缓存元数据失败 {fund_code}: {e}")
    
    # ==================== L3 数据源获取 ====================
    
    def fetch_fund_nav_from_source(self, fund_code: str, days: int = 365) -> pd.DataFrame:
        """从数据源获取基金净值（AKShare）"""
        try:
            import akshare as ak
            
            logger.info(f"从数据源获取 {fund_code} 净值数据...")
            
            # 获取净值历史
            df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            
            if df is None or df.empty:
                logger.warning(f"数据源返回空数据: {fund_code}")
                return pd.DataFrame()
            
            # 处理数据
            df = df.rename(columns={
                '净值日期': 'date',
                '单位净值': 'nav',
                '日增长率': 'daily_return'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
            df['daily_return'] = pd.to_numeric(df['daily_return'], errors='coerce')
            
            # 过滤日期
            start_date = datetime.now() - timedelta(days=days + 10)
            df = df[df['date'] >= start_date].tail(days)
            
            return df.dropna(subset=['nav'])
            
        except Exception as e:
            logger.error(f"从数据源获取 {fund_code} 失败: {e}")
            return pd.DataFrame()
    
    # ==================== 公共接口 ====================
    
    def get_fund_nav_history(self, fund_code: str, days: int = 365, 
                            force_refresh: bool = False) -> pd.DataFrame:
        """
        获取基金历史净值（带三级缓存）
        
        Args:
            fund_code: 基金代码
            days: 获取天数
            force_refresh: 强制刷新缓存
        
        Returns:
            DataFrame with columns: date, nav, daily_return
        """
        cache_key = self._get_cache_key(fund_code, 'nav')
        
        # L1: 内存缓存
        if not force_refresh:
            mem_data = self.get_from_memory(cache_key)
            if mem_data is not None and isinstance(mem_data, pd.DataFrame):
                return mem_data
        
        # L2: 数据库缓存（1天有效）
        if not force_refresh:
            db_data = self.get_fund_nav_from_db(fund_code, days)
            if db_data is not None and not db_data.empty:
                df = db_data.rename(columns={
                    'nav_date': 'date',
                    'nav_value': 'nav'
                })
                self.set_to_memory(cache_key, df, ttl_minutes=15)
                return df
        
        # L3: 从数据源获取
        fresh_data = self.fetch_fund_nav_from_source(fund_code, days)
        
        if not fresh_data.empty:
            # 保存到各级缓存
            self.save_fund_nav_to_db(fund_code, fresh_data, 'akshare')
            self.set_to_memory(cache_key, fresh_data, ttl_minutes=15)
        
        return fresh_data
    
    def get_performance_metrics(self, fund_code: str, days: int = 365,
                                force_refresh: bool = False) -> Dict:
        """
        获取基金绩效指标（带缓存，1天有效）
        
        Args:
            fund_code: 基金代码
            days: 历史数据天数
            force_refresh: 强制刷新
        
        Returns:
            Dict with performance metrics
        """
        cache_key = self._get_cache_key(fund_code, 'perf')
        
        # L1: 内存缓存
        if not force_refresh:
            mem_data = self.get_from_memory(cache_key)
            if mem_data is not None and isinstance(mem_data, dict):
                return mem_data
        
        # L2: 数据库缓存（1天有效）
        if not force_refresh:
            db_data = self.get_performance_from_db(fund_code)
            if db_data is not None:
                self.set_to_memory(cache_key, db_data, ttl_minutes=30)
                return db_data
        
        # L3: 计算并缓存
        metrics = self._calculate_performance_metrics(fund_code, days)
        
        if metrics:
            self.save_performance_to_db(fund_code, metrics)
            self.set_to_memory(cache_key, metrics, ttl_minutes=30)
        
        return metrics or self._empty_performance_metrics()
    
    def get_yesterday_data(self, fund_code: str) -> Dict:
        """
        获取昨日数据（准实时，内存缓存15分钟）
        
        Returns:
            Dict with yesterday_nav, yesterday_return
        """
        cache_key = self._get_cache_key(fund_code, 'yesterday')
        
        # L1: 内存缓存
        mem_data = self.get_from_memory(cache_key)
        if mem_data is not None:
            return mem_data
        
        # L2: 从净值缓存表查询
        if self.db:
            try:
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                
                sql = """
                    SELECT nav_value, daily_return
                    FROM fund_nav_cache
                    WHERE fund_code = %(fund_code)s
                      AND nav_date = %(yesterday)s
                    LIMIT 1
                """
                
                df = self.db.execute_query(sql, {
                    'fund_code': fund_code,
                    'yesterday': yesterday
                })
                
                if not df.empty:
                    data = {
                        'yesterday_nav': float(df.iloc[0]['nav_value']) if pd.notna(df.iloc[0]['nav_value']) else None,
                        'yesterday_return': float(df.iloc[0]['daily_return']) if pd.notna(df.iloc[0]['daily_return']) else 0.0
                    }
                    self.set_to_memory(cache_key, data, ttl_minutes=15)
                    return data
                    
            except Exception as e:
                logger.error(f"获取昨日数据失败 {fund_code}: {e}")
        
        return {'yesterday_nav': None, 'yesterday_return': 0.0}
    
    def _calculate_performance_metrics(self, fund_code: str, days: int = 365) -> Optional[Dict]:
        """计算绩效指标"""
        try:
            # 获取历史数据
            df = self.get_fund_nav_history(fund_code, days)
            if df.empty or len(df) < 30:
                return None
            
            # 确保数据排序
            df = df.sort_values('date')
            
            # 提取收益率序列
            daily_returns = pd.to_numeric(df['daily_return'], errors='coerce').dropna()
            
            if len(daily_returns) < 30:
                return None
            
            # 处理百分比格式
            if abs(daily_returns.mean()) < 0.1:
                daily_returns = daily_returns * 100
            
            # 获取配置
            risk_free_rate = 0.02
            trading_days = 250
            
            # 计算指标
            nav_values = pd.to_numeric(df['nav'], errors='coerce').dropna()
            
            # 总收益率
            total_return = (nav_values.iloc[-1] - nav_values.iloc[0]) / nav_values.iloc[0]
            
            # 年化收益率
            years = len(df) / trading_days
            annualized_return = (1 + total_return) ** (1 / max(years, 0.01)) - 1 if years > 0 else 0
            
            # 年化波动率
            volatility = daily_returns.std() * np.sqrt(trading_days) / 100  # 转换为小数
            
            # 夏普比率（成立以来）- 使用全部数据
            sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility != 0 else 0
            
            # 计算不同时期的夏普比率
            sharpe_ratio_1y = sharpe_ratio  # 默认使用全部数据
            sharpe_ratio_ytd = sharpe_ratio  # 默认使用全部数据
            sharpe_ratio_all = sharpe_ratio  # 成立以来
            
            # 根据日期范围分别计算近一年和今年以来的夏普比率
            if 'date' in df.columns:
                df_copy = df.copy()
                df_copy['date'] = pd.to_datetime(df_copy['date'])
                now = pd.Timestamp.now()
                
                # 计算近一年夏普比率
                one_year_ago = now - pd.DateOffset(years=1)
                last_year_data = df_copy[df_copy['date'] >= one_year_ago]
                if len(last_year_data) >= 30:  # 至少30个交易日数据
                    # 获取近一年的收益率序列
                    start_idx = max(0, len(daily_returns) - len(last_year_data))
                    last_year_returns = daily_returns.iloc[start_idx:]
                    if len(last_year_returns) > 0:
                        vol_1y = last_year_returns.std() * np.sqrt(trading_days) / 100
                        # 计算近一年年化收益率
                        nav_1y_start = pd.to_numeric(last_year_data['nav'].iloc[0], errors='coerce')
                        nav_1y_end = pd.to_numeric(last_year_data['nav'].iloc[-1], errors='coerce')
                        if pd.notna(nav_1y_start) and nav_1y_start != 0 and pd.notna(nav_1y_end):
                            total_return_1y = (nav_1y_end - nav_1y_start) / nav_1y_start
                            days_1y = len(last_year_data)
                            annualized_return_1y = (1 + total_return_1y) ** (trading_days / max(days_1y, 1)) - 1
                            sharpe_ratio_1y = (annualized_return_1y - risk_free_rate) / vol_1y if vol_1y != 0 else 0.0
                
                # 计算今年以来夏普比率
                ytd_start = pd.Timestamp(year=now.year, month=1, day=1)
                ytd_data = df_copy[df_copy['date'] >= ytd_start]
                if len(ytd_data) >= 10:  # 至少10个交易日数据
                    # 获取今年以来的收益率序列
                    start_idx = max(0, len(daily_returns) - len(ytd_data))
                    ytd_returns = daily_returns.iloc[start_idx:]
                    if len(ytd_returns) > 0:
                        vol_ytd = ytd_returns.std() * np.sqrt(trading_days) / 100
                        # 计算今年以来年化收益率
                        nav_ytd_start = pd.to_numeric(ytd_data['nav'].iloc[0], errors='coerce')
                        nav_ytd_end = pd.to_numeric(ytd_data['nav'].iloc[-1], errors='coerce')
                        if pd.notna(nav_ytd_start) and nav_ytd_start != 0 and pd.notna(nav_ytd_end):
                            total_return_ytd = (nav_ytd_end - nav_ytd_start) / nav_ytd_start
                            days_ytd = len(ytd_data)
                            annualized_return_ytd = (1 + total_return_ytd) ** (trading_days / max(days_ytd, 1)) - 1 if days_ytd > 0 else 0.0
                            sharpe_ratio_ytd = (annualized_return_ytd - risk_free_rate) / vol_ytd if vol_ytd != 0 else 0.0
            
            # 最大回撤
            cumulative_max = nav_values.expanding().max()
            drawdown = (nav_values - cumulative_max) / cumulative_max
            max_drawdown = drawdown.min()
            
            # 卡玛比率
            calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            # 索提诺比率
            negative_returns = daily_returns[daily_returns < 0] / 100  # 转换为小数
            downside_deviation = negative_returns.std() * np.sqrt(trading_days) if len(negative_returns) > 0 else volatility
            sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation if downside_deviation != 0 else 0
            
            # VaR (95%)
            var_95 = daily_returns.quantile(0.05) / 100  # 转换为小数
            
            # 综合评分
            return_score = max(0, min(1, (annualized_return + 0.5) / 1.0))
            risk_score = max(0, min(1, 1 - abs(max_drawdown) / 0.5))
            sharpe_score = max(0, min(1, (sharpe_ratio + 2) / 4.0))
            volatility_score = max(0, min(1, 1 - volatility / 0.5))
            
            composite_score = (
                0.3 * return_score +
                0.25 * sharpe_score +
                0.2 * risk_score +
                0.15 * volatility_score +
                0.1 * risk_score
            )
            
            return {
                'annualized_return': round(annualized_return * 100, 2),  # 转回百分比
                'max_drawdown': round(max_drawdown * 100, 2),
                'volatility': round(volatility * 100, 2),
                'sharpe_ratio': round(sharpe_ratio_1y, 4) if sharpe_ratio_1y != sharpe_ratio else round(sharpe_ratio, 4),  # 默认使用近一年
                'sharpe_ratio_1y': round(sharpe_ratio_1y, 4),
                'sharpe_ratio_ytd': round(sharpe_ratio_ytd, 4),
                'sharpe_ratio_all': round(sharpe_ratio_all, 4),
                'calmar_ratio': round(calmar_ratio, 4),
                'sortino_ratio': round(sortino_ratio, 4),
                'var_95': round(var_95 * 100, 2),
                'composite_score': round(composite_score, 4),
                'risk_score': round(risk_score, 4),
                'return_score': round(return_score, 4),
                'data_days': len(df)
            }
            
        except Exception as e:
            logger.error(f"计算绩效指标失败 {fund_code}: {e}")
            return None
    
    def _is_qdii_fund(self, fund_code: str) -> bool:
        """判断是否为QDII基金"""
        qdii_prefixes = ('096', '100', '006', '008', '015', '021', '040', '007')
        return fund_code.startswith(qdii_prefixes)
    
    def _empty_performance_metrics(self) -> Dict:
        """空绩效指标"""
        return {
            'annualized_return': None,
            'max_drawdown': None,
            'volatility': None,
            'sharpe_ratio': None,
            'sharpe_ratio_1y': None,
            'sharpe_ratio_ytd': None,
            'sharpe_ratio_all': None,
            'calmar_ratio': None,
            'sortino_ratio': None,
            'var_95': None,
            'composite_score': None,
            'risk_score': None,
            'return_score': None,
            'data_days': 0
        }
    
    # ==================== 统计和清理 ====================
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        with self._cache_lock:
            mem_stats = {
                'total_entries': len(self._memory_cache),
                'total_access': sum(e.access_count for e in self._memory_cache.values()),
            }
        
        db_stats = {'total_funds': 0, 'total_records': 0, 'perf_records': 0}
        
        if self.db:
            try:
                # 净值缓存统计
                df_nav = self.db.execute_query("""
                    SELECT COUNT(DISTINCT fund_code) as funds, COUNT(*) as records
                    FROM fund_nav_cache
                    WHERE nav_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                """)
                if not df_nav.empty:
                    db_stats['total_funds'] = int(df_nav.iloc[0]['funds'])
                    db_stats['total_records'] = int(df_nav.iloc[0]['records'])
                
                # 绩效缓存统计 - 使用 fund_analysis_results
                df_perf = self.db.execute_query("""
                    SELECT COUNT(*) as records
                    FROM fund_analysis_results
                    WHERE analysis_date >= DATE_SUB(CURDATE(), INTERVAL 1 DAY)
                """)
                if not df_perf.empty:
                    db_stats['perf_records'] = int(df_perf.iloc[0]['records'])
                    
            except Exception as e:
                logger.error(f"获取数据库统计失败: {e}")
        
        return {
            'memory_cache': mem_stats,
            'database_cache': db_stats,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


# 装饰器：缓存API响应
class ApiCacheDecorator:
    """API响应缓存装饰器"""
    
    def __init__(self, ttl_minutes: int = 5):
        self.ttl = ttl_minutes
        self.cache = {}
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key_parts = [func.__name__]
            key_parts.extend(str(a) for a in args[1:])  # 跳过self
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(':'.join(key_parts).encode()).hexdigest()
            
            now = datetime.now()
            
            # 检查缓存
            if cache_key in self.cache:
                entry = self.cache[cache_key]
                if now - entry['timestamp'] < timedelta(minutes=self.ttl):
                    logger.debug(f"API缓存命中: {func.__name__}")
                    return entry['data']
            
            # 执行原函数
            result = func(*args, **kwargs)
            
            # 保存到缓存
            self.cache[cache_key] = {
                'data': result,
                'timestamp': now
            }
            
            # 清理过期缓存
            expired = [
                k for k, v in self.cache.items()
                if now - v['timestamp'] > timedelta(minutes=self.ttl)
            ]
            for k in expired:
                del self.cache[k]
            
            return result
        return wrapper


# 全局实例
cache_manager = None

def init_cache_manager(db_manager):
    """初始化缓存管理器"""
    global cache_manager
    cache_manager = FundNavCacheManager(db_manager)
    return cache_manager
