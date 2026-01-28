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

from .strategy_config import StrategyConfig, get_strategy_config
from .stop_loss_manager import StopLossManager, StopLossLevel, StopLossResult
from .trend_analyzer import TrendAnalyzer, TrendType, TrendResult
from .position_manager import PositionManager, VolatilityLevel, PositionAdjustment
from .strategy_evaluator import StrategyEvaluator, EvaluationResult
from .unified_strategy_engine import UnifiedStrategyEngine, UnifiedStrategyResult
from .strategy_adapter import StrategyAdapter, get_strategy_adapter
from .custom_strategy_backtest import (
    CustomStrategyBacktest, BacktestResult, TradeRecord,
    FilterEngine, SortingEngine, WeightCalculator, RiskController,
    run_custom_backtest
)
from .performance_metrics import (
    PerformanceMetrics, PerformanceCalculator, calculate_performance_metrics
)
from .backtest_api import (
    BacktestAPIHandler, BacktestTaskManager, BacktestTask, BacktestStatus,
    TradeRecordFilter, CSVExporter, get_task_manager
)

__all__ = [
    # 配置
    'StrategyConfig',
    'get_strategy_config',
    
    # 止损管理
    'StopLossManager',
    'StopLossLevel',
    'StopLossResult',
    
    # 趋势分析
    'TrendAnalyzer',
    'TrendType',
    'TrendResult',
    
    # 仓位管理
    'PositionManager',
    'VolatilityLevel',
    'PositionAdjustment',
    
    # 策略评估
    'StrategyEvaluator',
    'EvaluationResult',
    
    # 统一策略引擎
    'UnifiedStrategyEngine',
    'UnifiedStrategyResult',
    
    # 策略适配器
    'StrategyAdapter',
    'create_strategy_adapter',
    
    # 自定义策略回测
    'CustomStrategyBacktest',
    'BacktestResult',
    'TradeRecord',
    'FilterEngine',
    'SortingEngine',
    'WeightCalculator',
    'RiskController',
    'run_custom_backtest',
    
    # 绩效指标计算
    'PerformanceMetrics',
    'PerformanceCalculator',
    'calculate_performance_metrics',
    
    # 回测API
    'BacktestAPIHandler',
    'BacktestTaskManager',
    'BacktestTask',
    'BacktestStatus',
    'TradeRecordFilter',
    'CSVExporter',
    'get_task_manager',
]
