#!/usr/bin/env python
# coding: utf-8

"""
回测模块
包含投资策略、风险管理和回测引擎

主要组件：
- StrategyConfig: 策略配置管理
- StopLossManager: 止损管理
- TrendAnalyzer: 趋势分析
- PositionManager: 仓位管理
- StrategyEvaluator: 策略评估
- UnifiedStrategyEngine: 统一策略引擎
- StrategyAdapter: 策略适配器（向后兼容）
- BacktestAPIHandler: 回测API处理器
"""

# Core components
from .core.strategy_models import CustomStrategyConfig, StrategyValidator, FilterCondition
from .core.strategy_config import StrategyConfig, get_strategy_config
from .core.stop_loss_manager import StopLossManager, StopLossLevel, StopLossResult
from .core.position_manager import PositionManager, VolatilityLevel, PositionAdjustment
from .core.unified_strategy_engine import UnifiedStrategyEngine, UnifiedStrategyResult
from .core.backtest_api import (
    BacktestAPIHandler, BacktestTaskManager, BacktestTask, BacktestStatus,
    get_task_manager
)
from .core.backtest_engine import FundBacktest
from .core.akshare_data_fetcher import fetch_fund_history_from_akshare

# Strategies
from .strategies.trend_analyzer import TrendAnalyzer, TrendType, TrendResult
from .strategies.strategy_adapter import StrategyAdapter, get_strategy_adapter
from .strategies.custom_strategy_backtest import (
    CustomStrategyBacktest, BacktestResult, TradeRecord,
    run_custom_backtest
)
from .strategies.builtin_strategies import BuiltinStrategies, get_builtin_strategies_manager
from .strategies.advanced_strategies import BaseStrategy, get_all_advanced_strategies
from .strategies.enhanced_strategy import EnhancedInvestmentStrategy
from .strategies.strategy_selector import StrategySelector, get_strategy_selector

# Analysis
from .analysis.enhanced_analytics import EnhancedFundAnalytics
from .analysis.strategy_evaluator import StrategyEvaluator, EvaluationResult
from .analysis.performance_metrics import (
    PerformanceMetrics, PerformanceCalculator, calculate_performance_metrics
)
from .analysis.risk_metrics import calculate_var, calculate_cvar
from .analysis.advanced_risk_metrics import EnhancedRiskMetrics, RiskMetrics
from .analysis.visualization import StrategyVisualizer
from .analysis.monte_carlo import MonteCarloSimulator

# Utils
from .utils.strategy_parameter_tuner import StrategyParameterTuner

__all__ = [
    # Core
    'CustomStrategyConfig', 'StrategyValidator', 'FilterCondition',
    'StrategyConfig', 'get_strategy_config',
    'StopLossManager', 'StopLossLevel', 'StopLossResult',
    'PositionManager', 'VolatilityLevel', 'PositionAdjustment',
    'UnifiedStrategyEngine', 'UnifiedStrategyResult',
    'BacktestAPIHandler', 'BacktestTaskManager', 'BacktestTask', 'BacktestStatus',
    'FundBacktest', 'fetch_fund_history_from_akshare',
    
    # Strategies
    'TrendAnalyzer', 'TrendType', 'TrendResult',
    'StrategyAdapter', 'get_strategy_adapter',
    'CustomStrategyBacktest', 'BacktestResult', 'TradeRecord', 'run_custom_backtest',
    'BuiltinStrategies', 'get_builtin_strategies_manager', 'BaseStrategy', 'get_all_advanced_strategies',
    'EnhancedInvestmentStrategy', 'StrategySelector', 'get_strategy_selector',
    
    # Analysis
    'EnhancedFundAnalytics',
    'StrategyEvaluator', 'EvaluationResult',
    'PerformanceMetrics', 'PerformanceCalculator', 'calculate_performance_metrics',
    'calculate_var', 'calculate_cvar',
    'EnhancedRiskMetrics', 'RiskMetrics',
    'StrategyVisualizer', 'MonteCarloSimulator',
    
    # Utils
    'StrategyParameterTuner'
]
