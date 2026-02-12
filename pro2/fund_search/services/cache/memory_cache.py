#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
内存缓存实现
基于线程安全的字典实现
"""

import threading
import logging
from typing import Any, Optional
from datetime import datetime, timedelta

try:
    from .base import CacheBackend, CacheEntry
except ImportError:
    # 支持直接作为脚本运行或测试时使用
    from services.cache.base import CacheBackend, CacheEntry

logger = logging.getLogger(__name__)


class MemoryCache(CacheBackend):
    """
    线程安全的内存缓存
    
    特性：
    - 支持过期时间（TTL）
    - 自动清理过期数据
    - 最大容量限制
    - LRU 淘汰策略
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        cleanup_interval: int = 100
    ):
        """
        初始化内存缓存
        
        Args:
            max_size: 最大缓存条目数
            cleanup_interval: 清理间隔（每N次操作清理一次）
        """
        self._cache = {}
        self._lock = threading.RLock()
        self._max_size = max_size
        self._cleanup_interval = cleanup_interval
        self._operation_count = 0
        
        # 统计信息
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._deletes = 0
        
        logger.info(f"内存缓存初始化完成，最大容量: {max_size}")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            self._operation_count += 1
            
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                return None
            
            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            
            # 触发清理
            self._maybe_cleanup()
            
            return entry.value
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """设置缓存值"""
        with self._lock:
            self._operation_count += 1
            self._sets += 1
            
            # 计算过期时间
            expires_at = None
            if ttl is not None:
                expires_at = datetime.now() + timedelta(seconds=ttl)
            
            # 创建条目
            entry = CacheEntry(
                value=value,
                created_at=datetime.now(),
                expires_at=expires_at
            )
            
            # 检查容量
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_lru()
            
            self._cache[key] = entry
            
            # 触发清理
            self._maybe_cleanup()
            
            return True
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            self._operation_count += 1
            
            if key in self._cache:
                del self._cache[key]
                self._deletes += 1
                return True
            
            return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                return False
            
            if entry.is_expired:
                del self._cache[key]
                return False
            
            return True
    
    def clear(self) -> bool:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            logger.info("内存缓存已清空")
            return True
    
    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(hit_rate, 4),
                'sets': self._sets,
                'deletes': self._deletes
            }
    
    def _maybe_cleanup(self):
        """触发清理（如果达到间隔）"""
        if self._operation_count % self._cleanup_interval == 0:
            self._cleanup_expired()
    
    def _cleanup_expired(self):
        """清理过期数据"""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"清理过期缓存: {len(expired_keys)} 条")
    
    def _evict_lru(self):
        """LRU 淘汰策略：删除最旧的条目"""
        if not self._cache:
            return
        
        # 找到最旧的条目
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].created_at
        )
        
        del self._cache[oldest_key]
        logger.debug(f"LRU淘汰: {oldest_key}")


# 全局内存缓存实例
memory_cache = MemoryCache(max_size=2000)
