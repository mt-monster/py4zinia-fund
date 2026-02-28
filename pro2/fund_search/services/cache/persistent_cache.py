#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金数据缓存管理器
实现内存缓存 + 数据库缓存两级缓存策略

缓存策略：
1. 昨日盈亏率(prev_day_return): 可缓存，变动频率低
2. 日涨跌幅(today_return): 实时计算，不缓存
3. 净值(nav): 可缓存，但需确保时效性
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import threading

logger = logging.getLogger(__name__)


class FundDataCache:
    """
    基金数据缓存管理器
    
    实现两级缓存：
    1. 内存缓存：高性能，短期有效（15分钟）
    2. 数据库缓存：持久化，长期有效（1天）
    """
    
    # 内存缓存（类级别共享）
    _memory_cache = {}
    _cache_lock = threading.RLock()
    
    # 缓存有效期配置（分钟）
    CACHE_TTL = {
        'prev_day_return': 1440,    # 昨日盈亏率：1天
        'current_nav': 60,           # 当前净值：1小时
        'previous_nav': 1440,        # 昨日净值：1天
        'nav_history': 30,           # 净值历史：30分钟
        'fund_basic_info': 1440,     # 基金基本信息：1天
        'performance_metrics': 1440  # 绩效指标：1天
    }
    
    def __init__(self, db_manager=None):
        """
        初始化缓存管理器
        
        Args:
            db_manager: 数据库管理器，用于持久化缓存
        """
        self.db = db_manager
        self._init_db_cache_table()
    
    def _init_db_cache_table(self):
        """初始化数据库缓存表"""
        if self.db is None:
            return
        
        try:
            # 检查表是否存在
            sql = """
            CREATE TABLE IF NOT EXISTS fund_data_cache (
                fund_code VARCHAR(20) NOT NULL,
                cache_date DATE NOT NULL,
                current_nav FLOAT,
                previous_nav FLOAT,
                prev_day_return FLOAT,
                nav_date VARCHAR(10),
                data_source VARCHAR(50),
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (fund_code, cache_date),
                INDEX idx_cached_at (cached_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
            self.db.execute_sql(sql)
            logger.info("基金数据缓存表初始化完成")
        except Exception as e:
            logger.warning(f"初始化缓存表失败: {e}")
    
    def _get_memory_key(self, fund_code: str, data_type: str) -> str:
        """生成内存缓存键"""
        today = datetime.now().strftime('%Y%m%d')
        return f"{fund_code}:{data_type}:{today}"
    
    def _get_from_memory(self, fund_code: str, data_type: str) -> Optional[Any]:
        """从内存缓存获取数据"""
        with self._cache_lock:
            key = self._get_memory_key(fund_code, data_type)
            cached = self._memory_cache.get(key)
            
            if cached is None:
                return None
            
            data, timestamp, ttl = cached
            age_minutes = (datetime.now() - timestamp).total_seconds() / 60
            
            if age_minutes > ttl:
                # 缓存过期
                del self._memory_cache[key]
                return None
            
            logger.debug(f"内存缓存命中: {fund_code} {data_type}")
            return data
    
    def _save_to_memory(self, fund_code: str, data_type: str, data: Any, ttl_minutes: int = None):
        """保存数据到内存缓存"""
        if ttl_minutes is None:
            ttl_minutes = self.CACHE_TTL.get(data_type, 15)
        
        with self._cache_lock:
            key = self._get_memory_key(fund_code, data_type)
            self._memory_cache[key] = (data, datetime.now(), ttl_minutes)
            
            # 清理过期缓存（如果缓存过大）
            if len(self._memory_cache) > 1000:
                self._cleanup_memory_cache()
    
    def _cleanup_memory_cache(self):
        """清理过期内存缓存"""
        now = datetime.now()
        expired_keys = []
        
        for key, (data, timestamp, ttl) in self._memory_cache.items():
            age_minutes = (now - timestamp).total_seconds() / 60
            if age_minutes > ttl:
                expired_keys.append(key)
        
        for key in expired_keys[:100]:  # 每次最多清理100条
            del self._memory_cache[key]
        
        logger.debug(f"清理 {len(expired_keys)} 条过期内存缓存")
    
    def _get_from_db(self, fund_code: str, data_type: str) -> Optional[Any]:
        """从数据库缓存获取数据"""
        if self.db is None or data_type not in ['prev_day_return', 'current_nav', 'previous_nav']:
            return None
        
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            sql = """
            SELECT * FROM fund_data_cache
            WHERE fund_code = :fund_code AND cache_date = :today
            """
            result = self.db.execute_query(sql, {'fund_code': fund_code, 'today': today})
            
            if result.empty:
                return None
            
            row = result.iloc[0]
            cached_at = row.get('cached_at')
            
            # 检查缓存时效性
            if cached_at:
                cache_age = (datetime.now() - pd.to_datetime(cached_at)).total_seconds() / 60
                ttl = self.CACHE_TTL.get(data_type, 1440)
                
                if cache_age > ttl:
                    logger.debug(f"数据库缓存过期: {fund_code} {data_type}")
                    return None
            
            # 返回对应字段
            field_map = {
                'prev_day_return': 'prev_day_return',
                'current_nav': 'current_nav',
                'previous_nav': 'previous_nav'
            }
            
            field = field_map.get(data_type)
            if field and field in row:
                value = row[field]
                if pd.notna(value):
                    logger.debug(f"数据库缓存命中: {fund_code} {data_type}={value}")
                    return float(value)
            
            return None
            
        except Exception as e:
            logger.warning(f"从数据库缓存获取数据失败: {e}")
            return None
    
    def _save_to_db(self, fund_code: str, data: Dict):
        """保存数据到数据库缓存"""
        if self.db is None:
            return
        
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            sql = """
            INSERT INTO fund_data_cache (
                fund_code, cache_date, current_nav, previous_nav, 
                prev_day_return, nav_date, data_source
            ) VALUES (
                :fund_code, :cache_date, :current_nav, :previous_nav,
                :prev_day_return, :nav_date, :data_source
            ) ON DUPLICATE KEY UPDATE
                current_nav = VALUES(current_nav),
                previous_nav = VALUES(previous_nav),
                prev_day_return = VALUES(prev_day_return),
                nav_date = VALUES(nav_date),
                data_source = VALUES(data_source),
                cached_at = CURRENT_TIMESTAMP
            """
            
            params = {
                'fund_code': fund_code,
                'cache_date': today,
                'current_nav': data.get('current_nav'),
                'previous_nav': data.get('previous_nav'),
                'prev_day_return': data.get('prev_day_return'),
                'nav_date': data.get('nav_date'),
                'data_source': data.get('data_source', 'unknown')
            }
            
            self.db.execute_sql(sql, params)
            logger.debug(f"数据已保存到数据库缓存: {fund_code}")
            
        except Exception as e:
            logger.warning(f"保存数据到数据库缓存失败: {e}")
    
    def get_cached_data(self, fund_code: str, data_type: str) -> Optional[Any]:
        """
        获取缓存数据（先内存后数据库）
        
        Args:
            fund_code: 基金代码
            data_type: 数据类型（prev_day_return, current_nav等）
            
        Returns:
            缓存数据或None
        """
        # 1. 先尝试内存缓存
        memory_data = self._get_from_memory(fund_code, data_type)
        if memory_data is not None:
            return memory_data
        
        # 2. 再尝试数据库缓存
        db_data = self._get_from_db(fund_code, data_type)
        if db_data is not None:
            # 回填内存缓存
            self._save_to_memory(fund_code, data_type, db_data)
            return db_data
        
        return None
    
    def save_cached_data(self, fund_code: str, data_type: str, data: Any, persist: bool = False):
        """
        保存数据到缓存
        
        Args:
            fund_code: 基金代码
            data_type: 数据类型
            data: 要缓存的数据
            persist: 是否持久化到数据库
        """
        # 保存到内存缓存
        self._save_to_memory(fund_code, data_type, data)
        
        # 如果需要持久化且是完整数据字典
        if persist and isinstance(data, dict):
            self._save_to_db(fund_code, data)
    
    def get_batch_cached_data(self, fund_codes: List[str], data_type: str) -> Dict[str, Any]:
        """
        批量获取缓存数据
        
        Args:
            fund_codes: 基金代码列表
            data_type: 数据类型
            
        Returns:
            Dict[基金代码, 缓存数据]
        """
        results = {}
        for code in fund_codes:
            data = self.get_cached_data(code, data_type)
            if data is not None:
                results[code] = data
        return results
    
    def invalidate_cache(self, fund_code: str = None, data_type: str = None):
        """
        使缓存失效
        
        Args:
            fund_code: 基金代码，如果为None则清除所有
            data_type: 数据类型，如果为None则清除该基金所有类型
        """
        with self._cache_lock:
            if fund_code is None:
                # 清除所有缓存
                self._memory_cache.clear()
                logger.info("所有内存缓存已清除")
            else:
                # 清除指定基金或类型的缓存
                keys_to_remove = []
                for key in self._memory_cache.keys():
                    if key.startswith(f"{fund_code}:"):
                        if data_type is None or f":{data_type}:" in key:
                            keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self._memory_cache[key]
                
                logger.debug(f"清除 {len(keys_to_remove)} 条缓存: {fund_code} {data_type or 'all'}")
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        with self._cache_lock:
            total_keys = len(self._memory_cache)
            
            # 按类型统计
            type_stats = {}
            for key in self._memory_cache.keys():
                parts = key.split(':')
                if len(parts) >= 2:
                    data_type = parts[1]
                    type_stats[data_type] = type_stats.get(data_type, 0) + 1
            
            return {
                'memory_cache_keys': total_keys,
                'type_distribution': type_stats
            }
