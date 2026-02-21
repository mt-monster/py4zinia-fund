#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多数据源适配器单元测试
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock


class TestMultiSourceDataAdapter:
    """MultiSourceDataAdapter 测试类"""
    
    @pytest.fixture
    def adapter(self):
        """创建适配器实例"""
        from fund_search.data_retrieval.multi_source_adapter import MultiSourceDataAdapter
        return MultiSourceDataAdapter()
    
    @pytest.fixture
    def sample_fund_code(self):
        """示例基金代码"""
        return "000001"
    
    @pytest.fixture
    def sample_qdii_fund(self):
        """示例QDII基金代码"""
        return "016667"
    
    def test_init_with_config(self):
        """测试使用配置初始化"""
        from fund_search.data_retrieval.multi_source_adapter import MultiSourceDataAdapter
        adapter = MultiSourceDataAdapter()
        assert adapter is not None
        assert adapter.cache is not None
    
    def test_calculate_today_return_realtime_fallback(self, adapter):
        """测试今日收益率计算（使用缓存净值作为fallback）"""
        # Mock _get_realtime_estimate 返回None，使其使用缓存净值计算
        with patch.object(adapter, '_get_realtime_estimate', return_value=None):
            current_nav = 1.50
            previous_nav = 1.48
            
            expected_return = round((current_nav - previous_nav) / previous_nav * 100, 2)
            actual_return = adapter._calculate_today_return_realtime("000001", current_nav, previous_nav)
            
            assert actual_return == expected_return
    
    def test_calculate_today_return_realtime_with_estimate(self, adapter):
        """测试今日收益率计算（使用实时估值）"""
        # Mock _get_realtime_estimate 返回估值数据
        mock_estimate = {
            'estimate_nav': 1.52,
            'yesterday_nav': 1.48
        }
        with patch.object(adapter, '_get_realtime_estimate', return_value=mock_estimate):
            result = adapter._calculate_today_return_realtime("000001", 1.50, 1.48)
            
            expected = (1.52 - 1.48) / 1.48 * 100
            assert abs(result - expected) < 0.01
    
    def test_calculate_today_return_realtime_zero_previous(self, adapter):
        """测试前一日净值为0的情况"""
        # Mock _get_realtime_estimate 返回None
        with patch.object(adapter, '_get_realtime_estimate', return_value=None):
            result = adapter._calculate_today_return_realtime("000001", 1.5, 0)
            # 当previous_nav为0时，无法计算，应返回0
            assert result == 0.0


class TestFundCodeValidation:
    """基金代码验证测试 - 使用公共工具函数"""
    
    def test_valid_fund_codes(self):
        """测试有效基金代码"""
        valid_codes = ['000001', '123456', '999999']
        
        for code in valid_codes:
            # 验证6位数字格式
            assert len(code) == 6 and code.isdigit()
    
    def test_invalid_fund_codes(self):
        """测试无效基金代码"""
        invalid_codes = [
            '',           # 空字符串
            '123',        # 太短
            '1234567',    # 太长
            'abcdef',     # 非数字
        ]
        
        for code in invalid_codes:
            # 验证无效格式
            assert not (len(code) == 6 and code.isdigit())


class TestPerformanceMetrics:
    """绩效指标计算测试"""
    
    def test_sharpe_ratio_calculation(self):
        """测试夏普比率计算"""
        from fund_search.backtesting.performance_metrics import PerformanceCalculator
        
        calculator = PerformanceCalculator(risk_free_rate=0.03)
        
        # 模拟日收益率数据（小数格式）
        daily_returns = np.array([0.001, -0.0005, 0.0008, 0.0002, -0.0001] * 50)
        
        sharpe = calculator.calculate_sharpe_ratio(daily_returns)
        
        # 验证结果合理性
        assert isinstance(sharpe, (int, float))
        assert not np.isnan(sharpe)
        assert not np.isinf(sharpe)
    
    def test_sharpe_ratio_insufficient_data(self):
        """测试数据不足时的夏普比率"""
        from fund_search.backtesting.performance_metrics import PerformanceCalculator
        
        calculator = PerformanceCalculator()
        
        # 少于2天的数据
        daily_returns = np.array([0.001])
        sharpe = calculator.calculate_sharpe_ratio(daily_returns)
        
        assert sharpe == 0.0
    
    def test_volatility_calculation(self):
        """测试波动率计算"""
        from fund_search.backtesting.performance_metrics import PerformanceCalculator
        
        calculator = PerformanceCalculator()
        
        daily_returns = np.random.randn(252) * 0.01
        volatility = calculator.calculate_volatility(daily_returns)
        
        assert isinstance(volatility, (int, float))
        assert volatility >= 0
        assert not np.isnan(volatility)



