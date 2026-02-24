#!/usr/bin/env python
# coding: utf-8

"""
Prometheus监控集成模块
提供应用性能监控和指标收集
"""

import logging
import time
from typing import Callable
from functools import wraps

try:
    from prometheus_flask_exporter import PrometheusMetrics
    from prometheus_client import Counter, Histogram, Gauge, Info
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    PrometheusMetrics = None
    Counter = Histogram = Gauge = Info = None

logger = logging.getLogger(__name__)


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, app=None, prefix: str = 'fund_analysis'):
        """
        初始化指标收集器
        
        Args:
            app: Flask应用实例
            prefix: 指标前缀
        """
        self.prefix = prefix
        self._metrics = {}
        self._prometheus_metrics = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化Flask应用监控"""
        if not PROMETHEUS_AVAILABLE:
            logger.warning("prometheus_flask_exporter 未安装，监控功能将被禁用")
            return
        
        self._prometheus_metrics = PrometheusMetrics(
            app,
            group_by_endpoint=True,
            bucket_pattern='.*',
            prefix=self.prefix
        )
        
        self._register_custom_metrics(app)
        
        logger.info("Prometheus监控已初始化，访问 /metrics 查看指标")
    
    def _register_custom_metrics(self, app):
        """注册自定义指标"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self._metrics['fund_queries_total'] = Counter(
            f'{self.prefix}_fund_queries_total',
            '基金查询总次数',
            ['query_type', 'status']
        )
        
        self._metrics['data_fetch_duration'] = Histogram(
            f'{self.prefix}_data_fetch_duration_seconds',
            '数据获取耗时',
            ['source', 'fund_code'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        self._metrics['cache_operations'] = Counter(
            f'{self.prefix}_cache_operations_total',
            '缓存操作次数',
            ['operation', 'result']
        )
        
        self._metrics['active_users'] = Gauge(
            f'{self.prefix}_active_users',
            '活跃用户数'
        )
        
        self._metrics['database_connections'] = Gauge(
            f'{self.prefix}_database_connections',
            '数据库连接数',
            ['pool_name']
        )
        
        self._metrics['backtest_runs'] = Counter(
            f'{self.prefix}_backtest_runs_total',
            '回测运行次数',
            ['strategy_name', 'status']
        )
        
        self._metrics['strategy_performance'] = Histogram(
            f'{self.prefix}_strategy_performance',
            '策略绩效指标',
            ['strategy_name', 'metric_name'],
            buckets=[-50, -20, -10, -5, 0, 5, 10, 20, 50, 100]
        )
        
        app_info = Info(f'{self.prefix}_app', '应用信息')
        app_info.info({
            'version': '1.0.0',
            'service': 'fund_analysis'
        })
    
    def track_fund_query(self, query_type: str, status: str = 'success'):
        """记录基金查询"""
        if PROMETHEUS_AVAILABLE and 'fund_queries_total' in self._metrics:
            self._metrics['fund_queries_total'].labels(
                query_type=query_type,
                status=status
            ).inc()
    
    def track_data_fetch(self, source: str, fund_code: str, duration: float):
        """记录数据获取"""
        if PROMETHEUS_AVAILABLE and 'data_fetch_duration' in self._metrics:
            self._metrics['data_fetch_duration'].labels(
                source=source,
                fund_code=fund_code
            ).observe(duration)
    
    def track_cache_operation(self, operation: str, result: str):
        """记录缓存操作"""
        if PROMETHEUS_AVAILABLE and 'cache_operations' in self._metrics:
            self._metrics['cache_operations'].labels(
                operation=operation,
                result=result
            ).inc()
    
    def track_backtest_run(self, strategy_name: str, status: str = 'success'):
        """记录回测运行"""
        if PROMETHEUS_AVAILABLE and 'backtest_runs' in self._metrics:
            self._metrics['backtest_runs'].labels(
                strategy_name=strategy_name,
                status=status
            ).inc()
    
    def set_active_users(self, count: int):
        """设置活跃用户数"""
        if PROMETHEUS_AVAILABLE and 'active_users' in self._metrics:
            self._metrics['active_users'].set(count)
    
    def set_database_connections(self, pool_name: str, count: int):
        """设置数据库连接数"""
        if PROMETHEUS_AVAILABLE and 'database_connections' in self._metrics:
            self._metrics['database_connections'].labels(
                pool_name=pool_name
            ).set(count)


def track_time(metric_name: str = None):
    """
    执行时间追踪装饰器
    
    Args:
        metric_name: 指标名称
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                logger.debug(f"{func.__name__} executed in {duration:.3f}s")
        return wrapper
    return decorator


def track_async_time(metric_name: str = None):
    """
    异步执行时间追踪装饰器
    
    Args:
        metric_name: 指标名称
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                logger.debug(f"{func.__name__} executed in {duration:.3f}s")
        return wrapper
    return decorator


metrics_collector = MetricsCollector()


def init_monitoring(app):
    """
    初始化监控
    
    Args:
        app: Flask应用实例
    """
    metrics_collector.init_app(app)
    return metrics_collector
