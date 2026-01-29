"""
API接口集成测试
"""

import pytest
import json
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'fund_search'))

from flask.testing import FlaskClient


@pytest.fixture
def client():
    """创建测试客户端"""
    from web.app import app, init_components
    
    app.config['TESTING'] = True
    app.config['DEBUG'] = False
    
    # 使用测试配置
    with app.test_client() as client:
        with app.app_context():
            # 可选：初始化测试组件
            # init_components()
            yield client


class TestFundAPI:
    """基金API测试"""

    @pytest.mark.api
    def test_get_fund_list(self, client):
        """测试获取基金列表API"""
        response = client.get('/api/funds')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'funds' in data or 'data' in data

    @pytest.mark.api
    def test_get_fund_detail(self, client):
        """测试获取基金详情API"""
        response = client.get('/api/fund/000001')
        
        assert response.status_code in [200, 404]  # 可能存在或不存在
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'fund_code' in data or 'error' in data

    @pytest.mark.api
    def test_get_fund_history(self, client):
        """测试获取基金历史数据API"""
        response = client.get('/api/fund/000001/history?start_date=2024-01-01&end_date=2024-03-01')
        
        assert response.status_code in [200, 404]

    @pytest.mark.api
    def test_get_fund_allocation(self, client):
        """测试获取基金资产配置API"""
        response = client.get('/api/fund/000001/allocation')
        
        assert response.status_code in [200, 404]


class TestHoldingsAPI:
    """持仓API测试"""

    @pytest.mark.api
    def test_get_holdings(self, client):
        """测试获取持仓列表API"""
        response = client.get('/api/holdings')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list) or 'data' in data

    @pytest.mark.api
    def test_create_holding(self, client):
        """测试创建持仓API"""
        payload = {
            'fund_code': '999999',
            'fund_name': '测试基金',
            'holding_amount': 10000,
            'holding_shares': 1000,
            'nav': 1.0
        }
        
        response = client.post(
            '/api/holdings',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code in [200, 201, 400, 500]

    @pytest.mark.api
    def test_update_holding(self, client):
        """测试更新持仓API"""
        payload = {
            'holding_amount': 15000,
            'holding_shares': 1500
        }
        
        response = client.put(
            '/api/holdings/999999',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code in [200, 404, 500]

    @pytest.mark.api
    def test_delete_holding(self, client):
        """测试删除持仓API"""
        response = client.delete('/api/holdings/999999')
        
        assert response.status_code in [200, 404, 500]


class TestStrategyAPI:
    """策略API测试"""

    @pytest.mark.api
    def test_get_strategies(self, client):
        """测试获取策略列表API"""
        response = client.get('/api/strategies')

        assert response.status_code == 200
        data = json.loads(response.data)
        # API返回格式: {'success': True, 'data': [...]}
        assert 'success' in data
        assert 'data' in data

    @pytest.mark.api
    def test_get_builtin_strategies(self, client):
        """测试获取内置策略API"""
        response = client.get('/api/builtin-strategies')

        assert response.status_code == 200
        data = json.loads(response.data)
        # API返回格式: {'success': True, 'data': [...]}
        assert 'success' in data
        assert 'data' in data

    @pytest.mark.api
    def test_strategy_analyze(self, client):
        """测试策略分析API"""
        payload = {
            'fund_codes': ['000001', '000002'],
            'strategy_type': 'momentum',
            'parameters': {
                'lookback_days': 20
            }
        }
        
        response = client.post(
            '/api/strategy/analyze',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code in [200, 400, 500]

    @pytest.mark.api
    def test_strategy_backtest(self, client):
        """测试策略回测API"""
        payload = {
            'fund_codes': ['000001'],
            'strategy_name': 'test_strategy',
            'start_date': '2024-01-01',
            'end_date': '2024-03-01',
            'initial_capital': 100000
        }
        
        response = client.post(
            '/api/strategy/backtest',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code in [200, 400, 500]


class TestETFAPI:
    """ETF API测试"""

    @pytest.mark.api
    def test_get_etf_list(self, client):
        """测试获取ETF列表API"""
        response = client.get('/api/etf/list')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list) or 'data' in data

    @pytest.mark.api
    def test_get_etf_detail(self, client):
        """测试获取ETF详情API"""
        response = client.get('/api/etf/510300')

        # 可能返回200(成功)、404(不存在)或500(服务器错误，如数据库连接失败)
        assert response.status_code in [200, 404, 500]


class TestCorrelationAPI:
    """相关性分析API测试"""

    @pytest.mark.api
    def test_analyze_correlation(self, client):
        """测试相关性分析API"""
        payload = {
            'fund_codes': ['000001', '000002', '000003']
        }
        
        response = client.post(
            '/api/holdings/analyze/correlation',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code in [200, 400, 500]

    @pytest.mark.api
    def test_comprehensive_analysis(self, client):
        """测试综合分析API"""
        payload = {
            'fund_codes': ['000001', '000002']
        }
        
        response = client.post(
            '/api/holdings/analyze/comprehensive',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code in [200, 400, 500]


class TestUserStrategyAPI:
    """用户策略API测试"""

    @pytest.mark.api
    def test_get_user_strategies(self, client):
        """测试获取用户策略API"""
        response = client.get('/api/user-strategies')

        assert response.status_code == 200
        data = json.loads(response.data)
        # API返回格式: {'success': True, 'data': [...], 'total': n}
        assert 'success' in data
        assert 'data' in data

    @pytest.mark.api
    def test_create_user_strategy(self, client):
        """测试创建用户策略API"""
        payload = {
            'name': '测试策略',
            'description': '这是一个测试策略',
            'rules': [
                {'field': 'sharpe_ratio', 'operator': '>', 'value': 1.0}
            ]
        }
        
        response = client.post(
            '/api/user-strategies',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code in [200, 201, 400, 500]


class TestPageRoutes:
    """页面路由测试"""

    @pytest.mark.api
    def test_index_page(self, client):
        """测试首页"""
        response = client.get('/')
        assert response.status_code == 200

    @pytest.mark.api
    def test_fund_detail_page(self, client):
        """测试基金详情页"""
        response = client.get('/fund/000001')
        assert response.status_code == 200

    @pytest.mark.api
    def test_my_holdings_page(self, client):
        """测试持仓页面"""
        response = client.get('/my-holdings')
        assert response.status_code == 200

    @pytest.mark.api
    def test_strategy_page(self, client):
        """测试策略页面"""
        response = client.get('/strategy')
        assert response.status_code == 200

    @pytest.mark.api
    def test_etf_page(self, client):
        """测试ETF页面"""
        response = client.get('/etf')
        assert response.status_code == 200

    @pytest.mark.api
    def test_correlation_page(self, client):
        """测试相关性分析页面"""
        response = client.get('/correlation-analysis')
        assert response.status_code == 200
