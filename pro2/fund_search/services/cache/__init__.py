#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
缓存模块
提供多级缓存支持
"""

from .base import CacheBackend, CacheEntry
from .memory_cache import MemoryCache
from .fund_cache import FundDataCache, fund_cache

__all__ = [
    'CacheBackend',
    'CacheEntry',
    'MemoryCache',
    'FundDataCache',
    'fund_cache'
]
