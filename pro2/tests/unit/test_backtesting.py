"""
回测引擎单元测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'fund_search'))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch


class TestBacktestEngine:
    """回测引擎测试"""

    @pytest.fixture
    def sample_price_data(self):
        """样本价格数据"""
        dates = pd.date_range(start='2024-01-01', end='2024-03-01', freq='D')
        np.random.seed(42)
        prices = 1.0 + np.cumsum(np.random.randn(len(dates)) * 0.01)
        
        return pd.DataFrame({
            'date': dates,
            'nav': prices,
            'daily_return': np.random.randn(len(dates)) * 0.01
        })

    def test_calculate_cumulative_returns(self, sample_price_data):
        """测试计算累计收益"""
        from backtesting.core.backtest_engine import calculate_cumulative_returns
        
        returns = sample_price_data['daily_return'].values
        cumulative = calculate_cumulative_returns(returns)
        
        assert len(cumulative) == len(returns)
        assert cumulative[0] == pytest.approx(0, abs=0.01)

    def test_calculate_max_drawdown(self, sample_price_data):
        """测试计算最大回撤"""
        from backtesting.core.backtest_engine import calculate_max_drawdown
        
        prices = sample_price_data['nav'].values
        max_dd, start_idx, end_idx = calculate_max_drawdown(prices)
        
        assert max_dd <= 0  # 回撤应该是负数或零
        assert start_idx >= 0
        assert end_idx >= start_idx

    def test_calculate_sharpe_ratio(self):
        """测试计算夏普比率"""
        from backtesting.core.backtest_engine import calculate_sharpe_ratio
        
        # 生成模拟收益数据
        np.random.seed(42)
        returns = np.random.randn(252) * 0.01  # 252个交易日
        
        sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        
        # 夏普比率应该是一个数值
        assert isinstance(sharpe, (int, float))

    def test_calculate_volatility(self):
        """测试计算波动率"""
        from backtesting.core.backtest_engine import calculate_volatility
        
        np.random.seed(42)
        returns = np.random.randn(252) * 0.01
        
        vol = calculate_volatility(returns)
        
        # 波动率应该是正数
        assert vol >= 0


class TestUnifiedStrategyEngine:
    """统一策略引擎测试"""

    def test_strategy_engine_initialization(self):
        """测试策略引擎初始化"""
        from backtesting.core.unified_strategy_engine import UnifiedStrategyEngine
        
        engine = UnifiedStrategyEngine()
        assert engine is not None


class TestPerformanceCalculator:
    """绩效计算器测试"""

    def test_calculate_sharpe_ratio(self):
        """测试计算夏普比率"""
        from backtesting.analysis.performance_metrics import PerformanceCalculator
        
        calculator = PerformanceCalculator()
        
        # 模拟日收益率数据
        np.random.seed(42)
        daily_returns = np.random.randn(252) * 0.01
        
        sharpe = calculator.calculate_sharpe_ratio(daily_returns)
        
        assert isinstance(sharpe, (int, float))
        assert not np.isnan(sharpe)

    def test_calculate_volatility(self):
        """测试计算波动率"""
        from backtesting.analysis.performance_metrics import PerformanceCalculator
        
        calculator = PerformanceCalculator()
        
        np.random.seed(42)
        daily_returns = np.random.randn(252) * 0.01
        
        volatility = calculator.calculate_volatility(daily_returns)
        
        assert isinstance(volatility, (int, float))
        assert volatility >= 0

    def test_calculate_max_drawdown(self):
        """测试计算最大回撤"""
        from backtesting.analysis.performance_metrics import PerformanceCalculator
        
        calculator = PerformanceCalculator()
        
        # 使用净值曲线
        equity_curve = [1.0, 1.05, 1.03, 1.08, 1.06, 1.10, 1.08]
        
        max_dd = calculator.calculate_max_drawdown(equity_curve)
        
        assert isinstance(max_dd, (int, float))
        assert max_dd >= 0
