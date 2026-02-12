#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pytest 配置文件
提供测试 fixtures 和共享配置
"""

import os
import sys

# 获取项目根目录（pro2/）
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# 将 fund_search 目录添加到路径，使 data_retrieval 可以作为顶层模块导入
fund_search_path = os.path.join(project_root, 'fund_search')
if fund_search_path not in sys.path:
    sys.path.insert(0, fund_search_path)

# 同时将项目根目录添加到路径
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 现在可以安全地导入项目模块
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# =============================================================================
# 基础 Fixtures
# =============================================================================

@pytest.fixture
def sample_fund_code():
    """示例基金代码 - 华夏成长混合"""
    return "000001"


@pytest.fixture
def sample_qdii_fund_code():
    """示例QDII基金代码 - 景顺长城全球半导体"""
    return "016667"


@pytest.fixture
def sample_fund_name():
    """示例基金名称"""
    return "华夏成长混合"


@pytest.fixture
def test_user_id():
    """测试用户ID"""
    return "test_user_001"


# =============================================================================
# 数据 Fixtures
# =============================================================================

@pytest.fixture
def sample_historical_data():
    """
    示例历史净值数据
    
    Returns:
        pd.DataFrame: 包含日期、净值、日收益率的数据
    """
    np.random.seed(42)  # 保证可重复性
    
    # 生成一年的交易日数据
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='B')
    n_days = len(dates)
    
    # 生成随机收益率
    daily_returns = np.random.normal(0.0005, 0.015, n_days)
    
    # 计算净值
    nav_values = 1.0 * np.cumprod(1 + daily_returns)
    
    return pd.DataFrame({
        'date': dates,
        'nav': nav_values,
        'accum_nav': nav_values * 1.05,
        'daily_return': daily_returns
    })


@pytest.fixture
def sample_holding_data():
    """示例持仓数据"""
    return {
        'user_id': 'test_user',
        'fund_code': '000001',
        'fund_name': '华夏成长混合',
        'holding_shares': 1000.0,
        'cost_price': 1.5,
        'holding_amount': 1500.0,
        'buy_date': '2024-01-15',
        'notes': '测试持仓'
    }


@pytest.fixture
def sample_fund_list():
    """示例基金列表"""
    return [
        {'fund_code': '000001', 'fund_name': '华夏成长混合', 'fund_type': '混合型'},
        {'fund_code': '000002', 'fund_name': '华夏大盘精选', 'fund_type': '股票型'},
        {'fund_code': '000003', 'fund_name': '华夏债券', 'fund_type': '债券型'},
        {'fund_code': '016667', 'fund_name': '景顺长城全球半导体', 'fund_type': 'QDII'},
        {'fund_code': '006373', 'fund_name': '华安智能生活', 'fund_type': '混合型'},
    ]


# =============================================================================
# 项目模块 Fixtures - 使用直接模块导入避免 __init__.py 问题
# =============================================================================

@pytest.fixture
def memory_cache():
    """
    创建项目中的 MemoryCache 实例
    
    直接导入 memory_cache 模块，避免触发 services/__init__.py
    """
    import importlib.util
    
    # 直接加载 base.py
    base_path = os.path.join(fund_search_path, 'services', 'cache', 'base.py')
    spec = importlib.util.spec_from_file_location("cache_base", base_path)
    base_module = importlib.util.module_from_spec(spec)
    sys.modules["cache_base"] = base_module
    spec.loader.exec_module(base_module)
    
    # 直接加载 memory_cache.py
    mem_path = os.path.join(fund_search_path, 'services', 'cache', 'memory_cache.py')
    spec = importlib.util.spec_from_file_location("memory_cache", mem_path)
    mem_module = importlib.util.module_from_spec(spec)
    
    # 手动注入 base 模块的类
    mem_module.CacheBackend = base_module.CacheBackend
    mem_module.CacheEntry = base_module.CacheEntry
    
    spec.loader.exec_module(mem_module)
    
    # 返回新实例
    return mem_module.MemoryCache(max_size=100)


@pytest.fixture
def performance_calculator():
    """创建项目中的 PerformanceCalculator 实例"""
    from backtesting.performance_metrics import PerformanceCalculator
    return PerformanceCalculator(risk_free_rate=0.03)


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_db_manager():
    """模拟数据库管理器"""
    class MockDBManager:
        def __init__(self):
            self._data = {}
        
        def execute_query(self, sql, params=None):
            """模拟查询"""
            return pd.DataFrame()
        
        def execute_sql(self, sql, params=None):
            """模拟执行SQL"""
            return True
        
        def get_user_holdings(self, user_id):
            """模拟获取用户持仓"""
            return []
    
    return MockDBManager()


# =============================================================================
# Flask App Fixtures
# =============================================================================

@pytest.fixture
def app():
    """创建Flask应用实例（用于测试）"""
    # 延迟导入，避免在配置路径前导入
    from web.app import app
    app.config.update({
        'TESTING': True,
        'DEBUG': False,
    })
    yield app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


# =============================================================================
# Pytest 配置
# =============================================================================

def pytest_configure(config):
    """Pytest 配置钩子"""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "performance: marks tests as performance tests")
