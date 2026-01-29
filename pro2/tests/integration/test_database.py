"""
数据库集成测试
"""

import pytest
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'fund_search'))


@pytest.mark.database
class TestDatabaseManager:
    """数据库管理器测试"""

    @pytest.fixture(scope='class')
    def db_manager(self):
        """数据库管理器固件"""
        from data_retrieval.enhanced_database import EnhancedDatabaseManager
        
        # 使用测试数据库配置
        test_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'test'),
            'password': os.getenv('DB_PASSWORD', 'test'),
            'database': os.getenv('TEST_DB_NAME', 'fund_test_db'),
        }
        
        manager = EnhancedDatabaseManager(test_config)
        yield manager
        # 清理
        # manager.cleanup()

    def test_connection(self, db_manager):
        """测试数据库连接"""
        assert db_manager.engine is not None
        assert db_manager.Session is not None

    def test_create_tables(self, db_manager):
        """测试创建表"""
        # 验证表存在
        tables = db_manager.get_table_list()
        assert isinstance(tables, list)

    def test_insert_fund_data(self, db_manager):
        """测试插入基金数据"""
        fund_data = {
            'fund_code': 'TEST001',
            'fund_name': '测试基金',
            'fund_type': '股票型',
            'nav': 1.2345,
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        result = db_manager.insert_fund_data(fund_data)
        assert result is True

    def test_get_fund_list(self, db_manager):
        """测试获取基金列表"""
        funds = db_manager.get_fund_list()
        assert isinstance(funds, list)

    def test_get_fund_detail(self, db_manager):
        """测试获取基金详情"""
        # 先插入测试数据
        fund_data = {
            'fund_code': 'TEST002',
            'fund_name': '测试基金2',
            'fund_type': '混合型',
            'nav': 1.0,
        }
        db_manager.insert_fund_data(fund_data)
        
        # 查询
        detail = db_manager.get_fund_detail('TEST002')
        assert detail is not None
        assert detail['fund_code'] == 'TEST002'

    def test_update_fund_data(self, db_manager):
        """测试更新基金数据"""
        fund_data = {
            'fund_code': 'TEST003',
            'fund_name': '测试基金3',
            'nav': 1.0,
        }
        db_manager.insert_fund_data(fund_data)
        
        # 更新
        update_data = {
            'fund_code': 'TEST003',
            'nav': 1.5,
        }
        result = db_manager.update_fund_data(update_data)
        assert result is True

    def test_delete_fund_data(self, db_manager):
        """测试删除基金数据"""
        fund_data = {
            'fund_code': 'TEST004',
            'fund_name': '测试基金4',
            'nav': 1.0,
        }
        db_manager.insert_fund_data(fund_data)
        
        # 删除
        result = db_manager.delete_fund_data('TEST004')
        assert result is True


@pytest.mark.database
class TestHoldingsOperations:
    """持仓操作测试"""

    @pytest.fixture
    def holdings_manager(self):
        """持仓管理器固件"""
        from data_retrieval.enhanced_database import EnhancedDatabaseManager
        
        test_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'test'),
            'password': os.getenv('DB_PASSWORD', 'test'),
            'database': os.getenv('TEST_DB_NAME', 'fund_test_db'),
        }
        
        return EnhancedDatabaseManager(test_config)

    def test_insert_holding(self, holdings_manager):
        """测试插入持仓"""
        holding = {
            'fund_code': 'HOLD001',
            'fund_name': '持仓基金1',
            'holding_amount': 10000,
            'holding_shares': 1000,
            'nav': 1.0,
            'created_at': datetime.now()
        }
        
        result = holdings_manager.insert_holding(holding)
        assert result is True

    def test_get_user_holdings(self, holdings_manager):
        """测试获取用户持仓"""
        holdings = holdings_manager.get_user_holdings()
        assert isinstance(holdings, list)

    def test_update_holding(self, holdings_manager):
        """测试更新持仓"""
        # 先插入
        holding = {
            'fund_code': 'HOLD002',
            'fund_name': '持仓基金2',
            'holding_amount': 5000,
            'holding_shares': 500,
            'nav': 1.0,
        }
        holdings_manager.insert_holding(holding)
        
        # 更新
        update_data = {
            'holding_amount': 6000,
            'holding_shares': 600,
        }
        result = holdings_manager.update_holding('HOLD002', update_data)
        assert result is True

    def test_delete_holding(self, holdings_manager):
        """测试删除持仓"""
        # 先插入
        holding = {
            'fund_code': 'HOLD003',
            'fund_name': '持仓基金3',
            'holding_amount': 3000,
            'holding_shares': 300,
            'nav': 1.0,
        }
        holdings_manager.insert_holding(holding)
        
        # 删除
        result = holdings_manager.delete_holding('HOLD003')
        assert result is True

    def test_clear_all_holdings(self, holdings_manager):
        """测试清空所有持仓"""
        result = holdings_manager.clear_all_holdings()
        assert result is True


@pytest.mark.database
class TestStrategyStorage:
    """策略存储测试"""

    @pytest.fixture
    def strategy_manager(self):
        """策略管理器固件"""
        from data_retrieval.enhanced_database import EnhancedDatabaseManager
        
        test_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'test'),
            'password': os.getenv('DB_PASSWORD', 'test'),
            'database': os.getenv('TEST_DB_NAME', 'fund_test_db'),
        }
        
        return EnhancedDatabaseManager(test_config)

    def test_save_user_strategy(self, strategy_manager):
        """测试保存用户策略"""
        strategy = {
            'name': '测试策略',
            'description': '这是一个测试策略',
            'rules': [
                {'field': 'sharpe_ratio', 'operator': '>', 'value': 1.0}
            ],
            'created_at': datetime.now()
        }
        
        result = strategy_manager.save_user_strategy(strategy)
        assert result is not None

    def test_get_user_strategies(self, strategy_manager):
        """测试获取用户策略列表"""
        strategies = strategy_manager.get_user_strategies()
        assert isinstance(strategies, list)

    def test_get_strategy_by_id(self, strategy_manager):
        """测试根据ID获取策略"""
        # 先保存一个策略
        strategy = {
            'name': '测试策略2',
            'description': '测试',
            'rules': [],
        }
        strategy_id = strategy_manager.save_user_strategy(strategy)
        
        # 查询
        retrieved = strategy_manager.get_user_strategy_by_id(strategy_id)
        assert retrieved is not None
        assert retrieved['name'] == '测试策略2'

    def test_update_user_strategy(self, strategy_manager):
        """测试更新用户策略"""
        # 先保存
        strategy = {
            'name': '测试策略3',
            'description': '原描述',
            'rules': [],
        }
        strategy_id = strategy_manager.save_user_strategy(strategy)
        
        # 更新
        update_data = {
            'description': '新描述',
        }
        result = strategy_manager.update_user_strategy(strategy_id, update_data)
        assert result is True

    def test_delete_user_strategy(self, strategy_manager):
        """测试删除用户策略"""
        # 先保存
        strategy = {
            'name': '测试策略4',
            'description': '测试',
            'rules': [],
        }
        strategy_id = strategy_manager.save_user_strategy(strategy)
        
        # 删除
        result = strategy_manager.delete_user_strategy(strategy_id)
        assert result is True
