#!/usr/bin/env python
# coding: utf-8
"""
简单的内存缓存工具
用于优化仪表盘等频繁访问的接口性能
"""

import time
import functools
import logging
from typing import Any, Dict, Optional, Callable
from threading import Lock

logger = logging.getLogger(__name__)


class MemoryCache:
    """线程安全的内存缓存"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                return None
            
            item = self._cache[key]
            # 检查是否过期
            if item['expire_time'] < time.time():
                del self._cache[key]
                return None
            
            return item['value']
    
    def set(self, key: str, value: Any, ttl: int = 60) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），默认60秒
        """
        with self._lock:
            self._cache[key] = {
                'value': value,
                'expire_time': time.time() + ttl
            }
    
    def delete(self, key: str) -> None:
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        with self._lock:
            # 清理过期项
            now = time.time()
            expired_keys = [k for k, v in self._cache.items() if v['expire_time'] < now]
            for k in expired_keys:
                del self._cache[k]
            
            return {
                'total_items': len(self._cache),
                'expired_removed': len(expired_keys)
            }


# 全局缓存实例
_global_cache = MemoryCache()


def cached(ttl: int = 60, key_prefix: str = None):
    """
    缓存装饰器
    
    Args:
        ttl: 缓存过期时间（秒）
        key_prefix: 缓存键前缀，默认为函数名
        
    Example:
        @cached(ttl=300)  # 缓存5分钟
        def get_dashboard_stats():
            return expensive_query()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            prefix = key_prefix or func.__name__
            # 包含参数在缓存键中（简化版本）
            cache_key = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # 尝试从缓存获取
            cached_value = _global_cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            _global_cache.set(cache_key, result, ttl)
            logger.debug(f"缓存写入: {cache_key}, ttl={ttl}s")
            
            return result
        
        # 附加缓存控制方法
        wrapper.cache_clear = lambda: _global_cache.delete(
            f"{key_prefix or func.__name__}:"
        )
        
        return wrapper
    return decorator


def get_cache_stats() -> Dict[str, int]:
    """获取全局缓存统计"""
    return _global_cache.get_stats()


def clear_all_cache():
    """清空所有缓存"""
    _global_cache.clear()
    logger.info("所有缓存已清空")
