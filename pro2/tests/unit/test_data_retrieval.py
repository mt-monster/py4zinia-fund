"""
数据检索模块单元测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'fund_search'))

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock


class TestFundDataParser:
    """基金数据解析测试"""

    def test_parse_fund_code_valid(self):
        """测试解析有效的基金代码"""
        from data_retrieval.parsers.smart_fund_parser import parse_fund_code
        
        # 测试标准6位数字代码
        assert parse_fund_code('000001') == '000001'
        assert parse_fund_code(' 000001 ') == '000001'
        assert parse_fund_code('000001.OF') == '000001'

    def test_parse_fund_code_invalid(self):
        """测试解析无效的基金代码"""
        from data_retrieval.parsers.smart_fund_parser import parse_fund_code
        
        # 测试无效代码
        assert parse_fund_code('') is None
        assert parse_fund_code('123') is None  # 太短
        assert parse_fund_code('12345678') is None  # 太长
        assert parse_fund_code('abcdef') is None  # 非数字

    def test_validate_fund_data_complete(self):
        """测试验证完整的数据"""
        from data_retrieval.parsers.smart_fund_parser import validate_fund_data
        
        data = {
            'fund_code': '000001',
            'fund_name': '测试基金',
            'nav': 1.2345,
            'date': '2024-01-01'
        }
        
        is_valid, errors = validate_fund_data(data)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_fund_data_incomplete(self):
        """测试验证不完整的数据"""
        from data_retrieval.parsers.smart_fund_parser import validate_fund_data
        
        data = {
            'fund_code': '',
            'fund_name': '测试基金',
        }
        
        is_valid, errors = validate_fund_data(data)
        assert is_valid is False
        assert len(errors) > 0


class TestFieldMapping:
    """字段映射测试"""

    def test_standardize_field_names(self):
        """测试标准化字段名"""
        from data_retrieval.utils.field_mapping import standardize_field_names
        
        raw_data = {
            '基金代码': '000001',
            '基金名称': '测试基金',
            '单位净值': '1.2345',
            '累计净值': '2.3456',
        }
        
        standardized = standardize_field_names(raw_data)
        
        assert 'fund_code' in standardized
        assert 'fund_name' in standardized
        assert 'nav' in standardized
        assert 'accumulated_nav' in standardized

    def test_calculate_derived_fields(self):
        """测试计算派生字段"""
        from data_retrieval.utils.field_mapping import calculate_derived_fields
        
        data = {
            'fund_code': '000001',
            'nav': 1.0,
            'prev_nav': 0.95,
            'holding_amount': 10000,
        }
        
        result = calculate_derived_fields(data)
        
        assert 'daily_return' in result
        assert 'holding_value' in result
        assert result['daily_return'] == pytest.approx(0.0526, rel=0.01)
        assert result['holding_value'] == 10000


class TestEnhancedDatabase:
    """增强数据库模块测试"""

    @pytest.fixture
    def mock_db_config(self):
        """模拟数据库配置"""
        return {
            'host': 'localhost',
            'port': 3306,
            'user': 'test',
            'password': 'test',
            'database': 'test_db'
        }

    def test_build_connection_string(self, mock_db_config):
        """测试构建连接字符串"""
        from data_access.enhanced_database import build_connection_string
        
        conn_str = build_connection_string(mock_db_config)
        
        assert 'mysql+pymysql' in conn_str
        assert 'localhost' in conn_str
        assert 'test_db' in conn_str

    def test_sanitize_fund_code(self):
        """测试清理基金代码"""
        from data_access.enhanced_database import sanitize_fund_code
        
        assert sanitize_fund_code('000001') == '000001'
        assert sanitize_fund_code(' 000001 ') == '000001'
        assert sanitize_fund_code('000001.OF') == '000001'
        assert sanitize_fund_code('') == ''


class TestDateUtils:
    """日期工具测试"""

    def test_date_parsing(self):
        """测试日期解析"""
        from datetime import datetime
        
        # 测试标准格式解析
        date1 = datetime.strptime('2024-01-15', '%Y-%m-%d')
        assert date1.year == 2024
        assert date1.month == 1
        assert date1.day == 15
        
        # 测试其他格式
        date2 = datetime.strptime('2024/01/15', '%Y/%m/%d')
        assert date2.year == 2024

    def test_trading_days_logic(self):
        """测试交易日逻辑"""
        from datetime import datetime, timedelta
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        # 生成所有日期
        all_days = []
        current = start_date
        while current <= end_date:
            all_days.append(current)
            current += timedelta(days=1)
        
        # 过滤交易日（周一到周五）
        trading_days = [d for d in all_days if d.weekday() < 5]
        
        # 应该排除周末
        assert len(trading_days) <= 23  # 1月最多23个交易日
        
        # 验证都是工作日
        for day in trading_days:
            assert day.weekday() < 5  # 0-4 是周一到周五


class TestPortfolioImporter:
    """持仓导入测试"""

    def test_parse_excel_file(self, tmp_path):
        """测试解析Excel文件"""
        from services.portfolio_importer import parse_excel_file
        
        # 创建测试Excel文件
        test_file = tmp_path / 'test_holdings.xlsx'
        df = pd.DataFrame({
            '基金代码': ['000001', '000002'],
            '基金名称': ['基金A', '基金B'],
            '持仓金额': [10000, 20000],
        })
        df.to_excel(test_file, index=False)
        
        result = parse_excel_file(str(test_file))
        
        assert len(result) == 2
        assert result[0]['fund_code'] == '000001'
        assert result[1]['fund_code'] == '000002'

    def test_validate_holding_data(self):
        """测试验证持仓数据"""
        from services.portfolio_importer import validate_holding_data
        
        valid_data = {
            'fund_code': '000001',
            'fund_name': '测试基金',
            'holding_amount': 10000,
        }
        
        is_valid, errors = validate_holding_data(valid_data)
        assert is_valid is True
        
        invalid_data = {
            'fund_code': '',
            'holding_amount': -100,
        }
        
        is_valid, errors = validate_holding_data(invalid_data)
        assert is_valid is False
        assert len(errors) > 0
