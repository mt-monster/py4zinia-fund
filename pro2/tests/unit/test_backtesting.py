"""
回测引擎单元测试
"""

<<<<<<< HEAD
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'fund_search'))

=======
>>>>>>> e7314991467ef81fa7ebe96d0b2fafdd7a30d714
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
<<<<<<< HEAD
        from backtesting.core.backtest_engine import calculate_cumulative_returns
=======
        from backtesting.backtest_engine import calculate_cumulative_returns
>>>>>>> e7314991467ef81fa7ebe96d0b2fafdd7a30d714
        
        returns = sample_price_data['daily_return'].values
        cumulative = calculate_cumulative_returns(returns)
        
        assert len(cumulative) == len(returns)
        assert cumulative[0] == pytest.approx(0, abs=0.01)

    def test_calculate_max_drawdown(self, sample_price_data):
        """测试计算最大回撤"""
<<<<<<< HEAD
        from backtesting.core.backtest_engine import calculate_max_drawdown
=======
        from backtesting.backtest_engine import calculate_max_drawdown
>>>>>>> e7314991467ef81fa7ebe96d0b2fafdd7a30d714
        
        prices = sample_price_data['nav'].values
        max_dd, start_idx, end_idx = calculate_max_drawdown(prices)
        
        assert max_dd <= 0  # 回撤应该是负数或零
        assert start_idx >= 0
        assert end_idx >= start_idx

    def test_calculate_sharpe_ratio(self):
        """测试计算夏普比率"""
<<<<<<< HEAD
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
=======
        from backtesting.backtest_engine import calculate_sharpe_ratio
        
        # 生成正收益序列
        returns = np.array([0.01, 0.02, 0.015, 0.01, 0.025])
        sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.02/252)
        
        assert sharpe > 0  # 正收益应该有正夏普比率

    def test_calculate_volatility(self):
        """测试计算波动率"""
        from backtesting.backtest_engine import calculate_volatility
        
        returns = np.array([0.01, -0.01, 0.02, -0.015, 0.01])
        vol = calculate_volatility(returns)
        
        assert vol > 0  # 波动率应该为正


class TestStrategyModels:
    """策略模型测试"""

    def test_strategy_config_validation(self):
        """测试策略配置验证"""
        from backtesting.strategy_models import StrategyConfig
        
        config = StrategyConfig(
            name='测试策略',
            strategy_type='momentum',
            parameters={
                'lookback_days': 20,
                'threshold': 0.05
            }
        )
        
        assert config.name == '测试策略'
        assert config.strategy_type == 'momentum'
        assert 'lookback_days' in config.parameters

    def test_backtest_result_structure(self):
        """测试回测结果结构"""
        from backtesting.strategy_models import BacktestResult
        
        result = BacktestResult(
            strategy_name='测试策略',
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 3, 1),
            total_return=0.15,
            annualized_return=0.60,
            max_drawdown=-0.10,
            sharpe_ratio=1.5,
            trades=[]
        )
        
        assert result.total_return == pytest.approx(0.15)
        assert result.sharpe_ratio == pytest.approx(1.5)


class TestEnhancedStrategy:
    """增强策略测试"""

    @pytest.fixture
    def mock_fund_data(self):
        """模拟基金数据"""
        return pd.DataFrame({
            'fund_code': ['000001'] * 60,
            'date': pd.date_range(start='2024-01-01', periods=60, freq='D'),
            'nav': np.cumsum(np.random.randn(60) * 0.01) + 1.0,
            'daily_return': np.random.randn(60) * 0.01
        })

    def test_momentum_strategy_signals(self, mock_fund_data):
        """测试动量策略信号生成"""
        from backtesting.enhanced_strategy import MomentumStrategy
        
        strategy = MomentumStrategy(lookback_period=20)
        signals = strategy.generate_signals(mock_fund_data)
        
        assert len(signals) == len(mock_fund_data)
        assert all(signal in [-1, 0, 1] for signal in signals)

    def test_mean_reversion_strategy(self, mock_fund_data):
        """测试均值回归策略"""
        from backtesting.enhanced_strategy import MeanReversionStrategy
        
        strategy = MeanReversionStrategy(window=20, threshold=0.02)
        signals = strategy.generate_signals(mock_fund_data)
        
        assert len(signals) == len(mock_fund_data)

    def test_strategy_performance_metrics(self):
        """测试策略性能指标"""
        from backtesting.enhanced_strategy import calculate_performance_metrics
        
        returns = np.array([0.01, 0.02, -0.01, 0.015, 0.01])
        
        metrics = calculate_performance_metrics(returns)
        
        assert 'total_return' in metrics
        assert 'volatility' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics


class TestRiskMetrics:
    """风险指标测试"""

    def test_value_at_risk(self):
        """测试风险价值(VaR)"""
        from backtesting.risk_metrics import calculate_var
        
        returns = np.random.normal(0.001, 0.02, 1000)
        var_95 = calculate_var(returns, confidence_level=0.95)
        var_99 = calculate_var(returns, confidence_level=0.99)
        
        assert var_95 < 0  # VaR应该是负数（损失）
        assert var_99 < var_95  # 99%置信度的VaR应该更保守

    def test_conditional_var(self):
        """测试条件风险价值(CVaR)"""
        from backtesting.risk_metrics import calculate_cvar
        
        returns = np.random.normal(0.001, 0.02, 1000)
        cvar = calculate_cvar(returns, confidence_level=0.95)
        
        assert cvar < 0  # CVaR应该是负数

    def test_beta_calculation(self):
        """测试Beta计算"""
        from backtesting.risk_metrics import calculate_beta
        
        # 生成相关收益序列
        np.random.seed(42)
        market_returns = np.random.randn(100) * 0.02
        stock_returns = 0.5 * market_returns + np.random.randn(100) * 0.01
        
        beta = calculate_beta(stock_returns, market_returns)
        
        assert beta > 0  # 正相关应该有正Beta
        assert beta < 2  # 合理的Beta范围
>>>>>>> e7314991467ef81fa7ebe96d0b2fafdd7a30d714


class TestUnifiedStrategyEngine:
    """统一策略引擎测试"""

<<<<<<< HEAD
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
=======
    def test_strategy_registry(self):
        """测试策略注册表"""
        from backtesting.unified_strategy_engine import StrategyRegistry
        
        registry = StrategyRegistry()
        
        # 注册测试策略
        @registry.register('test_strategy')
        class TestStrategy:
            pass
        
        assert 'test_strategy' in registry
        assert registry.get('test_strategy') == TestStrategy

    def test_strategy_execution_context(self):
        """测试策略执行上下文"""
        from backtesting.unified_strategy_engine import ExecutionContext
        
        context = ExecutionContext(
            initial_capital=100000,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 3, 1)
        )
        
        assert context.initial_capital == 100000
        assert context.current_capital == 100000

    def test_portfolio_allocation(self):
        """测试投资组合配置"""
        from backtesting.unified_strategy_engine import calculate_portfolio_allocation
        
        signals = {
            '000001': 1.0,
            '000002': 0.5,
            '000003': -0.5
        }
        
        allocation = calculate_portfolio_allocation(signals, total_capital=100000)
        
        assert sum(allocation.values()) <= 100000
        assert allocation['000001'] > allocation['000002']  # 信号强的应该配置更多
>>>>>>> e7314991467ef81fa7ebe96d0b2fafdd7a30d714
