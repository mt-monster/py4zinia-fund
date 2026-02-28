#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
缓存系统单元测试 - 测试项目中的实际缓存实现

此测试文件专门测试 fund_search/services/cache/memory_cache.py 中的实际代码。
为避免导入整个应用，我们使用动态导入策略。
"""

import pytest
import sys
import os
import time


def get_project_memory_cache():
    """
    获取项目中的 MemoryCache 类
    
    使用动态导入避免触发 services/__init__.py 和其他模块的初始化
    """
    import importlib.util
    
    # 项目根目录
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    fund_search_path = os.path.join(project_root, 'fund_search')
    
    # 1. 首先加载 base.py
    base_path = os.path.join(fund_search_path, 'services', 'cache', 'base.py')
    spec = importlib.util.spec_from_file_location("services.cache.base", base_path)
    base_module = importlib.util.module_from_spec(spec)
    
    # 注册到 sys.modules，让 memory_cache 的导入能找到它
    sys.modules['services'] = type(sys)('services')
    sys.modules['services.cache'] = type(sys)('services.cache')
    sys.modules['services.cache.base'] = base_module
    
    spec.loader.exec_module(base_module)
    
    # 2. 然后加载 memory_cache.py
    mem_path = os.path.join(fund_search_path, 'services', 'cache', 'memory_cache.py')
    spec = importlib.util.spec_from_file_location("services.cache.memory_cache", mem_path)
    mem_module = importlib.util.module_from_spec(spec)
    
    # 手动注入 base 模块
    mem_module.CacheBackend = base_module.CacheBackend
    mem_module.CacheEntry = base_module.CacheEntry
    
    spec.loader.exec_module(mem_module)
    
    return mem_module.MemoryCache


class TestMemoryCache:
    """
    测试项目中的 MemoryCache 实现
    """
    
    @pytest.fixture(scope='class')
    def MemoryCache(self):
        """获取项目中的 MemoryCache 类（只加载一次）"""
        return get_project_memory_cache()
    
    @pytest.fixture
    def cache(self, MemoryCache):
        """创建独立的 MemoryCache 实例"""
        return MemoryCache(max_size=100)
    
    def test_set_and_get(self, cache):
        """测试缓存设置和获取"""
        cache.set('test_key', 'test_value', ttl=60)
        value = cache.get('test_key')
        assert value == 'test_value'
    
    def test_get_nonexistent(self, cache):
        """测试获取不存在的键"""
        value = cache.get('nonexistent_key')
        assert value is None
    
    def test_ttl_expiration(self, cache):
        """测试TTL过期"""
        cache.set('expire_key', 'expire_value', ttl=1)
        assert cache.get('expire_key') == 'expire_value'
        
        time.sleep(1.5)
        
        assert cache.get('expire_key') is None
    
    def test_lru_eviction(self, cache):
        """测试LRU淘汰"""
        # 设置超过容量的数据
        for i in range(105):  # 超过 max_size=100
            cache.set(f'key{i}', f'value{i}', ttl=3600)
            time.sleep(0.001)
        
        # 验证容量限制
        stats = cache.get_stats()
        assert stats['size'] <= 100
    
    def test_delete(self, cache):
        """测试删除缓存"""
        cache.set('delete_key', 'delete_value', ttl=3600)
        assert cache.get('delete_key') == 'delete_value'
        
        result = cache.delete('delete_key')
        assert result is True
        
        assert cache.get('delete_key') is None
    
    def test_delete_nonexistent(self, cache):
        """测试删除不存在的键"""
        result = cache.delete('nonexistent_key')
        assert result is False
    
    def test_clear(self, cache):
        """测试清空缓存"""
        for i in range(10):
            cache.set(f'key{i}', f'value{i}', ttl=3600)
        
        result = cache.clear()
        assert result is True
        
        stats = cache.get_stats()
        assert stats['size'] == 0
    
    def test_stats(self, cache):
        """测试缓存统计"""
        for i in range(10):
            cache.set(f'key{i}', f'value{i}', ttl=3600)
        
        for i in range(5):
            cache.get(f'key{i}')
        
        for i in range(5):
            cache.get(f'nonexistent{i}')
        
        stats = cache.get_stats()
        
        assert 'size' in stats
        assert 'max_size' in stats
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'hit_rate' in stats
        
        assert stats['size'] == 10
        assert stats['max_size'] == 100
        assert stats['hits'] == 5
        assert stats['misses'] == 5
    
    def test_exists(self, cache):
        """测试检查键是否存在"""
        assert cache.exists('nonexistent') is False
        
        cache.set('exists_key', 'value', ttl=3600)
        assert cache.exists('exists_key') is True
        
        cache.set('expire_key', 'value', ttl=1)
        assert cache.exists('expire_key') is True
        time.sleep(1.5)
        assert cache.exists('expire_key') is False


class TestPerformanceCalculator:
    """
    测试项目中的 PerformanceCalculator
    使用延迟导入避免触发整个应用初始化
    """
    
    @pytest.fixture(scope='class')
    def PerformanceCalculator(self):
        """动态加载 PerformanceCalculator 类"""
        import importlib.util
        
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        fund_search_path = os.path.join(project_root, 'fund_search')
        
        # 加载 performance_metrics.py
        pm_path = os.path.join(fund_search_path, 'backtesting', 'analysis', 'performance_metrics.py')
        spec = importlib.util.spec_from_file_location("backtesting.performance_metrics", pm_path)
        pm_module = importlib.util.module_from_spec(spec)
        
        # 注入必要的依赖（numpy 等）
        import numpy as np
        pm_module.np = np
        
        # 执行模块
        spec.loader.exec_module(pm_module)
        
        return pm_module.PerformanceCalculator
    
    def test_sharpe_ratio_calculation(self, PerformanceCalculator):
        """测试夏普比率计算"""
        import numpy as np
        
        calculator = PerformanceCalculator(risk_free_rate=0.03)
        
        np.random.seed(42)
        daily_returns = np.random.normal(0.0005, 0.015, 252)
        
        sharpe = calculator.calculate_sharpe_ratio(daily_returns)
        
        assert isinstance(sharpe, (int, float))
        assert not np.isnan(sharpe)
        assert not np.isinf(sharpe)
    
    def test_sharpe_ratio_insufficient_data(self, PerformanceCalculator):
        """测试数据不足时的夏普比率"""
        import numpy as np
        
        calculator = PerformanceCalculator()
        
        daily_returns = np.array([0.001])
        sharpe = calculator.calculate_sharpe_ratio(daily_returns)
        
        assert sharpe == 0.0
    
    def test_volatility_calculation(self, PerformanceCalculator):
        """测试波动率计算"""
        import numpy as np
        
        calculator = PerformanceCalculator()
        
        np.random.seed(42)
        daily_returns = np.random.randn(252) * 0.01
        
        volatility = calculator.calculate_volatility(daily_returns)
        
        assert isinstance(volatility, (int, float))
        assert volatility >= 0
        assert not np.isnan(volatility)
    
    def test_max_drawdown_calculation(self, PerformanceCalculator):
        """测试最大回撤计算"""
        calculator = PerformanceCalculator()
        
        # 使用 list 而不是 numpy array，因为项目代码使用 "if not values" 检查
        equity_curve = [1.0, 1.05, 1.03, 1.08, 1.06, 1.10, 1.08]
        
        max_dd = calculator.calculate_max_drawdown(equity_curve)
        
        assert isinstance(max_dd, (int, float))
        assert max_dd >= 0
        assert max_dd <= 1
