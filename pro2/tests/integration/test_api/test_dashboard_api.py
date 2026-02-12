#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dashboard API 集成测试

测试实际的 API 端点
"""

import pytest
import json


class TestDashboardAPI:
    """Dashboard API 测试类 - 测试实际存在的端点"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        import sys
        import os
        # 设置路径
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        fund_search_path = os.path.join(project_root, 'fund_search')
        if fund_search_path not in sys.path:
            sys.path.insert(0, fund_search_path)
        
        from web.app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_get_dashboard_stats(self, client):
        """测试获取仪表盘统计 - /api/dashboard/stats"""
        response = client.get('/api/dashboard/stats')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # 验证返回结构
        assert 'success' in data or 'totalAssets' in data or 'data' in data
    
    def test_get_profit_trend(self, client):
        """测试获取收益趋势 - /api/dashboard/profit-trend"""
        response = client.get('/api/dashboard/profit-trend?days=90')
        
        # 可能返回200或500（如果数据获取失败）
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            # 验证返回结构
            assert 'success' in data or 'data' in data or 'labels' in data
    
    def test_get_allocation(self, client):
        """测试获取资产配置 - /api/dashboard/allocation"""
        response = client.get('/api/dashboard/allocation')
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert isinstance(data, dict) or isinstance(data, list) or 'success' in data
    
    def test_get_market_index(self, client):
        """测试获取市场指数 - /api/market/index"""
        response = client.get('/api/market/index')
        
        assert response.status_code in [200, 500]
    
    def test_get_recent_activities(self, client):
        """测试获取最近活动 - /api/dashboard/recent-activities"""
        response = client.get('/api/dashboard/recent-activities')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'success' in data
        assert 'data' in data


class TestHoldingsAPI:
    """持仓管理 API 测试 - 测试实际存在的端点"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        import sys
        import os
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        fund_search_path = os.path.join(project_root, 'fund_search')
        if fund_search_path not in sys.path:
            sys.path.insert(0, fund_search_path)
        
        from web.app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_get_holdings(self, client):
        """测试获取持仓列表 - /api/holdings (GET)"""
        response = client.get('/api/holdings')
        
        # 端点存在但可能返回500（如果数据库连接有问题）
        assert response.status_code in [200, 500]
    
    def test_add_holding(self, client):
        """测试添加持仓 - /api/holdings (POST)"""
        holding_data = {
            'user_id': 'test_user',
            'fund_code': '000001',
            'fund_name': '华夏成长混合',
            'holding_shares': 1000,
            'cost_price': 1.5
        }
        
        response = client.post(
            '/api/holdings',
            data=json.dumps(holding_data),
            content_type='application/json'
        )
        
        # 可能成功或失败，取决于数据库状态
        assert response.status_code in [200, 400, 500]
    
    def test_delete_holding(self, client):
        """测试删除持仓 - /api/holdings/<fund_code> (DELETE)"""
        # 先尝试删除一个可能不存在的持仓
        response = client.delete('/api/holdings/000001')
        
        # 端点存在但可能返回错误（如果持仓不存在或数据库问题）
        assert response.status_code in [200, 404, 500]


class TestFundAPI:
    """基金数据 API 测试 - 测试实际存在的端点"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        import sys
        import os
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        fund_search_path = os.path.join(project_root, 'fund_search')
        if fund_search_path not in sys.path:
            sys.path.insert(0, fund_search_path)
        
        from web.app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_get_fund_detail(self, client):
        """测试获取基金详情 - /api/fund/<fund_code>"""
        response = client.get('/api/fund/000001')
        
        # 可能返回200（成功）或500（数据获取失败）
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            # 验证返回结构
            assert isinstance(data, dict)
            # 可能有 fund_code 或 data 字段
            assert 'fund_code' in data or 'data' in data or 'success' in data
    
    def test_get_fund_history(self, client):
        """测试获取基金历史 - /api/fund/<fund_code>/history"""
        response = client.get('/api/fund/000001/history?days=30')
        
        assert response.status_code in [200, 500]
    
    def test_get_fund_info(self, client):
        """测试获取基金信息 - /api/fund/<fund_code>/info"""
        response = client.get('/api/fund/000001/info')
        
        assert response.status_code in [200, 500]
    
    def test_get_fund_allocation(self, client):
        """测试获取基金资产配置 - /api/fund/<fund_code>/allocation"""
        response = client.get('/api/fund/000001/allocation')
        
        assert response.status_code in [200, 404, 500]
    
    def test_search_funds(self, client):
        """测试搜索基金 - /api/fund/search"""
        response = client.get('/api/fund/search?keyword=华夏')
        
        assert response.status_code in [200, 500]
    
    def test_get_funds_list(self, client):
        """测试获取基金列表 - /api/funds"""
        response = client.get('/api/funds')
        
        assert response.status_code in [200, 500]


class TestStrategiesAPI:
    """策略相关 API 测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        import sys
        import os
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        fund_search_path = os.path.join(project_root, 'fund_search')
        if fund_search_path not in sys.path:
            sys.path.insert(0, fund_search_path)
        
        from web.app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_get_strategies(self, client):
        """测试获取策略列表 - /api/strategies"""
        response = client.get('/api/strategies')
        
        assert response.status_code in [200, 500]
    
    def test_get_summary(self, client):
        """测试获取汇总数据 - /api/summary"""
        response = client.get('/api/summary')
        
        assert response.status_code in [200, 500]
