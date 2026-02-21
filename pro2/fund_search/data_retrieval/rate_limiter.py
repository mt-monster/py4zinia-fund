#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API速率限制器
控制Tushare等API的调用频率，避免触发频率限制

使用示例:
    limiter = RateLimiter(max_calls=80, period=60)  # 每分钟最多80次
    
    # 方式1: 使用装饰器
    @rate_limited(limiter)
    def call_api():
        pass
    
    # 方式2: 使用上下文管理器
    with limiter.acquire():
        call_api()
    
    # 方式3: 手动控制
    limiter.wait_if_needed()
    call_api()
    limiter.record_call()
"""

import time
import threading
from typing import Optional, Callable, Any
from functools import wraps
from collections import deque
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    令牌桶算法实现的速率限制器
    
    特性:
    1. 线程安全
    2. 支持突发流量平滑处理
    3. 支持等待超时配置
    """
    
    def __init__(self, max_calls: int = 80, period: int = 60, 
                 burst_size: Optional[int] = None, name: str = "default"):
        """
        初始化速率限制器
        
        Args:
            max_calls: 周期内最大调用次数（默认80次）
            period: 时间周期（秒，默认60秒）
            burst_size: 突发流量大小（默认等于max_calls）
            name: 限制器名称，用于日志区分
        """
        self.max_calls = max_calls
        self.period = period
        self.burst_size = burst_size or max_calls
        self.name = name
        
        # 调用时间记录队列
        self._call_times = deque()
        self._lock = threading.RLock()
        
        # 统计信息
        self._stats = {
            'total_calls': 0,
            'throttled_calls': 0,
            'total_wait_time': 0.0
        }
        
        logger.info(f"速率限制器 '{name}' 初始化: {max_calls}次/{period}秒")
    
    def wait_if_needed(self, timeout: Optional[float] = None) -> bool:
        """
        检查是否需要等待，如需等待则阻塞
        
        Args:
            timeout: 最大等待时间（秒），None表示无限等待
            
        Returns:
            bool: True表示可以调用，False表示超时
        """
        with self._lock:
            now = time.time()
            
            # 清理过期记录
            cutoff_time = now - self.period
            while self._call_times and self._call_times[0] < cutoff_time:
                self._call_times.popleft()
            
            # 检查当前调用次数
            if len(self._call_times) < self.max_calls:
                return True
            
            # 需要等待
            if not self._call_times:
                return True
            
            # 计算需要等待的时间
            oldest_call = self._call_times[0]
            wait_time = oldest_call + self.period - now
            
            if wait_time <= 0:
                return True
            
            if timeout is not None and wait_time > timeout:
                logger.warning(f"速率限制器 '{self.name}': 等待时间{wait_time:.2f}s超过超时{timeout}s")
                return False
            
            self._stats['throttled_calls'] += 1
            logger.debug(f"速率限制器 '{self.name}': 等待 {wait_time:.2f}s")
        
        # 在锁外等待
        start_wait = time.time()
        time.sleep(wait_time)
        actual_wait = time.time() - start_wait
        
        with self._lock:
            self._stats['total_wait_time'] += actual_wait
        
        return True
    
    def record_call(self):
        """记录一次API调用"""
        with self._lock:
            self._call_times.append(time.time())
            self._stats['total_calls'] += 1
    
    def acquire(self, timeout: Optional[float] = None):
        """
        获取调用许可的上下文管理器
        
        使用示例:
            with limiter.acquire():
                api_call()
        """
        return _RateLimiterContext(self, timeout)
    
    def get_current_usage(self) -> int:
        """获取当前周期内的调用次数"""
        with self._lock:
            now = time.time()
            cutoff_time = now - self.period
            while self._call_times and self._call_times[0] < cutoff_time:
                self._call_times.popleft()
            return len(self._call_times)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            return {
                'name': self.name,
                'max_calls': self.max_calls,
                'period': self.period,
                'current_usage': self.get_current_usage(),
                'total_calls': self._stats['total_calls'],
                'throttled_calls': self._stats['throttled_calls'],
                'total_wait_time': round(self._stats['total_wait_time'], 2),
                'usage_percent': round(self.get_current_usage() / self.max_calls * 100, 1)
            }
    
    def reset_stats(self):
        """重置统计信息"""
        with self._lock:
            self._stats = {
                'total_calls': 0,
                'throttled_calls': 0,
                'total_wait_time': 0.0
            }


class _RateLimiterContext:
    """速率限制器上下文管理器"""
    
    def __init__(self, limiter: RateLimiter, timeout: Optional[float]):
        self.limiter = limiter
        self.timeout = timeout
        self.acquired = False
    
    def __enter__(self):
        self.acquired = self.limiter.wait_if_needed(self.timeout)
        if self.acquired:
            self.limiter.record_call()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def rate_limited(limiter: RateLimiter, timeout: Optional[float] = None):
    """
    速率限制装饰器
    
    使用示例:
        limiter = RateLimiter(max_calls=80, period=60)
        
        @rate_limited(limiter)
        def call_tushare_api():
            return pro.fund_nav(ts_code='000001.OF')
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not limiter.wait_if_needed(timeout):
                raise RateLimitExceeded(f"速率限制器 '{limiter.name}': 获取调用许可超时")
            limiter.record_call()
            return func(*args, **kwargs)
        return wrapper
    return decorator


class RateLimitExceeded(Exception):
    """速率限制超出异常"""
    pass


class MultiRateLimiter:
    """
    多接口速率限制管理器
    
    为不同API接口配置不同的速率限制
    """
    
    # 默认配置
    DEFAULT_LIMITS = {
        'fund_nav': {'max_calls': 80, 'period': 60},      # 净值接口: 80次/分钟
        'fund_basic': {'max_calls': 80, 'period': 60},    # 基础信息接口: 80次/分钟
        'fund_daily': {'max_calls': 80, 'period': 60},    # 日线数据: 80次/分钟
        'default': {'max_calls': 80, 'period': 60}        # 默认: 80次/分钟
    }
    
    def __init__(self, config: Optional[dict] = None):
        """
        初始化多接口限制器
        
        Args:
            config: 自定义配置，格式为 {api_name: {'max_calls': x, 'period': y}}
        """
        self._limiters = {}
        self._config = config or self.DEFAULT_LIMITS
        
        # 初始化各个接口的限制器
        for api_name, settings in self._config.items():
            self._limiters[api_name] = RateLimiter(
                max_calls=settings['max_calls'],
                period=settings['period'],
                name=api_name
            )
    
    def get_limiter(self, api_name: str) -> RateLimiter:
        """获取指定接口的速率限制器"""
        if api_name not in self._limiters:
            # 使用默认配置创建
            default = self._config.get('default', {'max_calls': 80, 'period': 60})
            self._limiters[api_name] = RateLimiter(
                max_calls=default['max_calls'],
                period=default['period'],
                name=api_name
            )
        return self._limiters[api_name]
    
    def get_all_stats(self) -> dict:
        """获取所有接口的统计信息"""
        return {name: limiter.get_stats() for name, limiter in self._limiters.items()}


# 全局速率限制器实例
tushare_limiter = MultiRateLimiter()


def get_tushare_limiter(api_name: str = 'default') -> RateLimiter:
    """
    获取Tushare指定接口的速率限制器
    
    Args:
        api_name: API接口名称，如 'fund_nav', 'fund_basic' 等
        
    Returns:
        RateLimiter: 对应的速率限制器
    """
    return tushare_limiter.get_limiter(api_name)


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    print("=" * 60)
    print("速率限制器测试")
    print("=" * 60)
    
    # 测试1: 基础功能
    limiter = RateLimiter(max_calls=5, period=10, name="test")
    
    print("\n测试1: 连续调用")
    for i in range(7):
        with limiter.acquire():
            print(f"  调用 {i+1}, 当前使用: {limiter.get_current_usage()}")
    
    print(f"\n统计信息: {limiter.get_stats()}")
    
    # 测试2: 装饰器
    print("\n测试2: 装饰器模式")
    api_limiter = RateLimiter(max_calls=3, period=10, name="api_test")
    
    @rate_limited(api_limiter)
    def mock_api_call():
        print(f"  API调用成功, 统计: {api_limiter.get_stats()}")
        return "success"
    
    for i in range(5):
        result = mock_api_call()
    
    print(f"\n最终统计: {api_limiter.get_stats()}")
