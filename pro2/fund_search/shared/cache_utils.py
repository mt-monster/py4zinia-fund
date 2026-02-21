#!/usr/bin/env python
# coding: utf-8
"""
缓存工具 - 兼容层

已重构：现在使用 services.cache.memory_cache 作为后端实现
保留此模块以维持向后兼容性
"""

import functools
import logging
from typing import Any, Dict, Optional, Callable

# 使用标准缓存实现作为后端
from services.cache.memory_cache import memory_cache

logger = logging.getLogger(__name__)


class MemoryCache:
    """
    内存缓存兼容类
    
    包装 services.cache.memory_cache，提供兼容的 API
    新代码应直接使用 services.cache.memory_cache
    """
    
    def __init__(self):
        self._backend = memory_cache
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        return self._backend.get(key)
    
    def set(self, key: str, value: Any, ttl: int = 60) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），默认60秒
        """
        self._backend.set(key, value, ttl=ttl)
    
    def delete(self, key: str) -> None:
        """删除缓存"""
        self._backend.delete(key)
    
    def clear(self) -> None:
        """清空所有缓存"""
        self._backend.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        stats = self._backend.get_stats()
        return {
            'total_items': stats.get('size', 0),
            'expired_removed': 0  # 兼容旧接口
        }


# 全局缓存实例（向后兼容）
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
            cached_value = memory_cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            memory_cache.set(cache_key, result, ttl=ttl)
            logger.debug(f"缓存写入: {cache_key}, ttl={ttl}s")
            
            return result
        
        # 附加缓存控制方法
        wrapper.cache_clear = lambda: memory_cache.delete(
            f"{key_prefix or func.__name__}:"
        )
        
        return wrapper
    return decorator


def get_cache_stats() -> Dict[str, int]:
    """获取全局缓存统计"""
    return _global_cache.get_stats()


def clear_all_cache():
    """清空所有缓存"""
    memory_cache.clear()
    logger.info("所有缓存已清空")
