"""
Pytest 配置文件
提供测试固件和共享配置
"""

import os
import sys
import pytest
import tempfile
import shutil
from datetime import datetime, timedelta

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'fund_search'))

# 测试数据
TEST_FUND_CODES = ['000001', '000002', '000003']
TEST_FUND_DATA = {
    '000001': {
        'fund_code': '000001',
        'fund_name': '测试基金1',
        'fund_type': '股票型',
        'nav': 1.2345,
        'accumulated_nav': 2.3456,
        'daily_return': 0.0123,
    },
    '000002': {
        'fund_code': '000002',
        'fund_name': '测试基金2',
        'fund_type': '混合型',
        'nav': 0.9876,
        'accumulated_nav': 1.8765,
        'daily_return': -0.0056,
    },
    '000003': {
        'fund_code': '000003',
        'fund_name': '测试基金3',
        'fund_type': '债券型',
        'nav': 1.1000,
        'accumulated_nav': 1.5000,
        'daily_return': 0.0023,
    }
}


@pytest.fixture(scope='session')
def test_data_dir():
    """测试数据目录"""
    data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


@pytest.fixture(scope='session')
def report_dir():
    """测试报告目录"""
    report_dir = os.path.join(os.path.dirname(__file__), 'reports')
    os.makedirs(report_dir, exist_ok=True)
    return report_dir


@pytest.fixture(scope='function')
def temp_dir():
    """临时目录，每个测试函数结束后自动清理"""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(scope='function')
def mock_fund_data():
    """模拟基金数据"""
    return TEST_FUND_DATA.copy()


@pytest.fixture(scope='function')
def sample_date_range():
    """样本日期范围"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    return {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d')
    }


@pytest.fixture(scope='session')
def test_config():
    """测试配置"""
    return {
        'database': {
            'host': 'localhost',
            'port': 3306,
            'user': 'test_user',
            'password': 'test_pass',
            'database': 'fund_test_db',
        },
        'api_timeout': 30,
        'max_retries': 3,
    }


@pytest.fixture(scope='function')
def mock_db_manager(mocker):
    """模拟数据库管理器"""
    mock = mocker.MagicMock()
    mock.get_fund_list.return_value = list(TEST_FUND_DATA.values())
    mock.get_fund_detail.return_value = TEST_FUND_DATA['000001']
    return mock


def pytest_configure(config):
    """Pytest配置钩子"""
    config.addinivalue_line(
        "markers", "integration: 标记为集成测试"
    )
    config.addinivalue_line(
        "markers", "unit: 标记为单元测试"
    )
    config.addinivalue_line(
        "markers", "slow: 标记为慢速测试"
    )
    config.addinivalue_line(
        "markers", "api: 标记为API测试"
    )
    config.addinivalue_line(
        "markers", "database: 标记为数据库测试"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试项，添加自定义标记"""
    for item in items:
        # 自动添加标记
        if "test_api" in item.nodeid:
            item.add_marker(pytest.mark.api)
        if "test_db" in item.nodeid or "database" in item.nodeid:
            item.add_marker(pytest.mark.database)
