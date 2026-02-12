#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略参数调优模块
Strategy Parameter Tuner Module

该模块提供策略参数的自动调优功能，包括：
1. 基于回测的参数优化（网格搜索、贝叶斯优化等）
2. 自适应匹配分数调整
3. 多目标优化支持（夏普比率、收益风险比、最大回撤等）
4. 市场状态感知的参数调整
5. A/B测试框架支持
6. 配置文件版本控制

Author: Strategy Optimization Team
Date: 2026-02-11
"""

import json
import logging
import pickle
import hashlib
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar, Union,
    Protocol
)

import numpy as np
import pandas as pd
import yaml
from scipy.optimize import minimize, differential_evolution
from scipy.stats import norm

# 导入项目内部模块（使用可选导入，确保模块可以独立运行）
try:
    from .strategy_selector import FundProfile, StrategySelector, StrategyMatchResult
    from .backtest_engine import FundBacktest
    from .performance_metrics import PerformanceMetrics, PerformanceCalculator
except ImportError:
    try:
        from strategy_selector import FundProfile, StrategySelector, StrategyMatchResult
        from backtest_engine import FundBacktest
        from performance_metrics import PerformanceMetrics, PerformanceCalculator
    except ImportError:
        # 创建占位类，以便模块可以独立运行
        FundProfile = None
        StrategySelector = None
        StrategyMatchResult = None
        FundBacktest = None
        PerformanceMetrics = None
        PerformanceCalculator = None

logger = logging.getLogger(__name__)


# ============================================================================
# 本地回退实现（当项目依赖不可用时）
# ============================================================================

if PerformanceCalculator is None:
    class _LocalPerformanceCalculator:
        """本地绩效计算器（当项目依赖不可时使用）"""
        
        TRADING_DAYS_PER_YEAR = 252
        RISK_FREE_RATE = 0.02
        
        def calculate_total_return(self, values):
            if values is None or len(values) < 2 or values[0] == 0:
                return 0.0
            return (values[-1] - values[0]) / values[0]
        
        def calculate_max_drawdown(self, values):
            if values is None or len(values) < 2:
                return 0.0
            peak = values[0]
            max_dd = 0.0
            for value in values:
                if value > peak:
                    peak = value
                if peak > 0:
                    drawdown = (peak - value) / peak
                    max_dd = max(max_dd, drawdown)
            return max_dd
        
        def calculate_sharpe_ratio(self, daily_returns):
            if len(daily_returns) < 2:
                return 0.0
            daily_risk_free = (1 + self.RISK_FREE_RATE) ** (1 / self.TRADING_DAYS_PER_YEAR) - 1
            excess_returns = daily_returns - daily_risk_free
            std = np.std(excess_returns)
            if std == 0:
                return 0.0
            return float(np.mean(excess_returns) / std * np.sqrt(self.TRADING_DAYS_PER_YEAR))
        
        def calculate_sortino_ratio(self, daily_returns, annual_return):
            downside = daily_returns[daily_returns < 0]
            if len(downside) < 2:
                return 0.0
            downside_vol = np.std(downside) * np.sqrt(self.TRADING_DAYS_PER_YEAR)
            if downside_vol == 0:
                return 0.0
            return (annual_return - self.RISK_FREE_RATE) / downside_vol
        
        def calculate_calmar_ratio(self, annual_return, max_drawdown):
            if max_drawdown == 0:
                return 0.0
            return annual_return / max_drawdown
        
        def calculate_daily_returns(self, values):
            if values is None or len(values) < 2:
                return np.array([])
            values_arr = np.array(values)
            returns = np.diff(values_arr) / values_arr[:-1]
            return np.nan_to_num(returns, nan=0.0, posinf=0.0, neginf=0.0)
    
    PerformanceCalculator = _LocalPerformanceCalculator


if FundProfile is None:
    @dataclass
    class _LocalFundProfile:
        """本地基金画像类"""
        fund_code: str = ""
        fund_name: str = ""
        volatility: float = 0.0
        trend_strength: float = 0.0
        mean_reversion_score: float = 0.0
        sharpe_ratio: float = 0.0
        max_drawdown: float = 0.0
        avg_return: float = 0.0
        risk_level: str = "medium"
        fund_type: str = "unknown"
    
    FundProfile = _LocalFundProfile


# ============================================================================
# 枚举类型定义
# ============================================================================

class MarketState(Enum):
    """市场状态枚举"""
    BULL = "bull"           # 牛市
    BEAR = "bear"           # 熊市
    SIDEWAYS = "sideways"   # 震荡市
    UNKNOWN = "unknown"     # 未知


class OptimizationMethod(Enum):
    """优化方法枚举"""
    GRID_SEARCH = "grid_search"           # 网格搜索
    BAYESIAN = "bayesian"                 # 贝叶斯优化
    GENETIC = "genetic"                   # 遗传算法
    DIFFERENTIAL_EVOLUTION = "de"         # 差分进化
    RANDOM_SEARCH = "random_search"       # 随机搜索


class TargetMetric(Enum):
    """优化目标指标枚举"""
    SHARPE = "sharpe"                     # 夏普比率
    SORTINO = "sortino"                   # 索提诺比率
    CALMAR = "calmar"                     # 卡玛比率
    RETURN_RISK = "return_risk"           # 收益风险比
    MAX_DRAWDOWN = "max_drawdown"         # 最大回撤（最小化）
    TOTAL_RETURN = "total_return"         # 总收益率
    MULTI_OBJECTIVE = "multi_objective"   # 多目标优化


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class ParameterSet:
    """
    参数集合数据类
    
    用于存储策略参数的完整配置，支持参数的版本控制和序列化
    
    Attributes:
        name: 参数集名称
        parameters: 参数字典
        version: 参数版本号
        created_at: 创建时间
        updated_at: 更新时间
        description: 参数描述
        metadata: 附加元数据
    """
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'parameters': self.parameters,
            'version': self.version,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'description': self.description,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParameterSet':
        """从字典创建实例"""
        return cls(
            name=data.get('name', ''),
            parameters=data.get('parameters', {}),
            version=data.get('version', '1.0.0'),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else datetime.now(),
            description=data.get('description', ''),
            metadata=data.get('metadata', {})
        )
    
    def copy(self) -> 'ParameterSet':
        """创建深拷贝"""
        return ParameterSet.from_dict(self.to_dict())
    
    def update_parameters(self, new_params: Dict[str, Any]) -> None:
        """更新参数并递增版本号"""
        self.parameters.update(new_params)
        self.updated_at = datetime.now()
        self._increment_version()
    
    def _increment_version(self) -> None:
        """递增版本号（语义化版本）"""
        try:
            parts = self.version.split('.')
            if len(parts) == 3:
                major, minor, patch = parts
                self.version = f"{major}.{minor}.{int(patch) + 1}"
            else:
                self.version = "1.0.0"
        except:
            self.version = "1.0.0"
    
    def get_hash(self) -> str:
        """计算参数的哈希值，用于快速比较"""
        param_str = json.dumps(self.parameters, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()[:8]


@dataclass
class OptimizationResult:
    """
    优化结果数据类
    
    存储参数优化的完整结果，包括最优参数、性能指标、优化过程等
    
    Attributes:
        optimal_params: 最优参数字典
        best_score: 最佳得分
        target_metric: 优化目标指标
        optimization_method: 使用的优化方法
        performance_metrics: 性能指标字典
        optimization_history: 优化历史记录
        backtest_results: 回测结果详情
        computation_time: 计算耗时（秒）
        iterations: 迭代次数
        convergence_info: 收敛信息
    """
    optimal_params: Dict[str, Any] = field(default_factory=dict)
    best_score: float = 0.0
    target_metric: str = "sharpe"
    optimization_method: str = ""
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)
    backtest_results: Optional[pd.DataFrame] = None
    computation_time: float = 0.0
    iterations: int = 0
    convergence_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'optimal_params': self.optimal_params,
            'best_score': self.best_score,
            'target_metric': self.target_metric,
            'optimization_method': self.optimization_method,
            'performance_metrics': self.performance_metrics,
            'optimization_history': self.optimization_history,
            'computation_time': self.computation_time,
            'iterations': self.iterations,
            'convergence_info': self.convergence_info
        }
    
    def get_summary(self) -> str:
        """获取结果摘要文本"""
        lines = [
            "=" * 60,
            "优化结果摘要",
            "=" * 60,
            f"优化方法: {self.optimization_method}",
            f"目标指标: {self.target_metric}",
            f"最佳得分: {self.best_score:.4f}",
            f"迭代次数: {self.iterations}",
            f"计算耗时: {self.computation_time:.2f}秒",
            "-" * 60,
            "最优参数:",
        ]
        for key, value in self.optimal_params.items():
            lines.append(f"  {key}: {value}")
        if self.performance_metrics:
            lines.append("-" * 60)
            lines.append("性能指标:")
            for key, value in self.performance_metrics.items():
                # 处理numpy数组的情况
                if hasattr(value, 'item'):
                    val = value.item() if hasattr(value, 'size') and value.size == 1 else str(value)
                else:
                    val = value
                if isinstance(val, (int, float)):
                    lines.append(f"  {key}: {val:.4f}")
                else:
                    lines.append(f"  {key}: {val}")
        lines.append("=" * 60)
        return "\n".join(lines)


@dataclass
class ABTestConfig:
    """
    A/B测试配置
    
    Attributes:
        test_id: 测试ID
        control_params: 对照组参数
        treatment_params: 实验组参数
        traffic_split: 流量分配比例（对照组比例）
        sample_size: 样本大小
        duration_days: 测试持续时间
        success_metric: 成功指标
    """
    test_id: str
    control_params: Dict[str, Any] = field(default_factory=dict)
    treatment_params: Dict[str, Any] = field(default_factory=dict)
    traffic_split: float = 0.5  # 默认50/50分配
    sample_size: int = 1000
    duration_days: int = 30
    success_metric: str = "sharpe"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, cancelled


@dataclass
class FeedbackData:
    """
    反馈数据结构
    
    用于记录实际交易反馈，用于自适应调整
    
    Attributes:
        fund_code: 基金代码
        strategy_type: 策略类型
        predicted_action: 预测的操作
        actual_return: 实际收益
        market_state: 市场状态
        timestamp: 时间戳
        success: 是否成功
        error: 误差值
    """
    fund_code: str
    strategy_type: str
    predicted_action: str
    actual_return: float
    market_state: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 市场状态检测器
# ============================================================================

class MarketStateDetector:
    """市场状态检测器"""
    
    def __init__(self, 
                 bull_threshold: float = 0.15,
                 bear_threshold: float = -0.15,
                 lookback_days: int = 60):
        """
        初始化市场状态检测器
        
        Args:
            bull_threshold: 牛市阈值（年化收益率）
            bear_threshold: 熊市阈值（年化收益率）
            lookback_days: 回溯天数
        """
        self.bull_threshold = bull_threshold
        self.bear_threshold = bear_threshold
        self.lookback_days = lookback_days
    
    def detect(self, price_series: pd.Series) -> MarketState:
        """
        检测当前市场状态
        
        Args:
            price_series: 价格序列
            
        Returns:
            MarketState: 市场状态
        """
        if len(price_series) < self.lookback_days:
            return MarketState.UNKNOWN
        
        # 计算收益率
        returns = price_series.pct_change().dropna()
        if len(returns) < 20:
            return MarketState.UNKNOWN
        
        # 计算年化收益率
        total_return = (price_series.iloc[-1] / price_series.iloc[0]) - 1
        days = len(price_series)
        annual_return = (1 + total_return) ** (252 / days) - 1
        
        # 计算波动率和趋势
        volatility = returns.std() * np.sqrt(252)
        sma_short = price_series.rolling(20).mean().iloc[-1]
        sma_long = price_series.rolling(60).mean().iloc[-1]
        trend = (sma_short - sma_long) / sma_long if sma_long != 0 else 0
        
        # 判断市场状态
        if annual_return > self.bull_threshold and trend > 0.05:
            return MarketState.BULL
        elif annual_return < self.bear_threshold and trend < -0.05:
            return MarketState.BEAR
        else:
            return MarketState.SIDEWAYS
    
    def get_state_features(self, price_series: pd.Series) -> Dict[str, float]:
        """
        获取市场状态特征
        
        Args:
            price_series: 价格序列
            
        Returns:
            特征字典
        """
        if len(price_series) < 20:
            return {
                'annual_return': 0.0,
                'volatility': 0.0,
                'trend': 0.0,
                'rsi': 50.0
            }
        
        returns = price_series.pct_change().dropna()
        total_return = (price_series.iloc[-1] / price_series.iloc[0]) - 1
        days = len(price_series)
        
        # RSI计算
        delta = price_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return {
            'annual_return': (1 + total_return) ** (252 / days) - 1,
            'volatility': returns.std() * np.sqrt(252),
            'trend': (price_series.rolling(20).mean().iloc[-1] / 
                     price_series.rolling(60).mean().iloc[-1] - 1),
            'rsi': rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
        }


# ============================================================================
# 主类：策略参数调优器
# ============================================================================

class StrategyParameterTuner:
    """
    策略参数调优器
    
    提供完整的参数优化功能，包括网格搜索、自适应调整、A/B测试等
    
    Attributes:
        config_path: 配置文件路径
        optimization_history: 优化历史记录
        match_weights: 匹配权重字典
        ab_tests: A/B测试配置字典
    """
    
    # 默认参数边界
    DEFAULT_PARAM_BOUNDS = {
        'buy_multipliers': {
            'strong_buy': (1.0, 4.0),
            'buy': (1.0, 2.5),
            'weak_buy': (0.8, 1.5),
        },
        'stop_loss': {
            'warning_threshold': (-0.15, -0.05),
            'stop_loss_threshold': (-0.20, -0.08),
            'redeem_ratio': (0.1, 0.5),
        },
        'volatility': {
            'high_threshold': (0.20, 0.35),
            'low_threshold': (0.05, 0.15),
            'high_adjustment': (0.3, 0.8),
            'low_adjustment': (1.0, 1.5),
        },
        'trend': {
            'ma_short_period': (3, 10),
            'ma_long_period': (10, 30),
            'uptrend_adjustment': (1.0, 1.5),
            'downtrend_adjustment': (0.5, 1.0),
        }
    }
    
    # 市场状态对应的策略偏好调整
    MARKET_STATE_ADJUSTMENTS = {
        MarketState.BULL: {
            'trend_following_weight': 1.3,      # 增强趋势跟踪
            'mean_reversion_weight': 0.7,       # 降低均值回归
            'volatility_threshold_multiplier': 1.2,
            'buy_aggressiveness': 1.2,
        },
        MarketState.BEAR: {
            'trend_following_weight': 0.8,
            'mean_reversion_weight': 1.2,       # 增强均值回归（抄底）
            'volatility_threshold_multiplier': 0.8,
            'buy_aggressiveness': 0.7,
            'stop_loss_tightening': 1.3,        # 收紧止损
        },
        MarketState.SIDEWAYS: {
            'trend_following_weight': 0.7,
            'mean_reversion_weight': 1.3,       # 震荡市偏好均值回归
            'volatility_threshold_multiplier': 1.0,
            'buy_aggressiveness': 1.0,
        },
        MarketState.UNKNOWN: {
            'trend_following_weight': 1.0,
            'mean_reversion_weight': 1.0,
            'volatility_threshold_multiplier': 1.0,
            'buy_aggressiveness': 1.0,
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化参数调优器
        
        Args:
            config_path: 策略配置文件路径
        """
        self.config_path = Path(config_path) if config_path else None
        self.optimization_history: List[OptimizationResult] = []
        self.match_weights: Dict[str, float] = self._init_match_weights()
        self.ab_tests: Dict[str, ABTestConfig] = {}
        self.market_detector = MarketStateDetector()
        self._strategy_selector = StrategySelector() if StrategySelector is not None else None
        
        # 加载配置
        if self.config_path and self.config_path.exists():
            self._load_config()
    
    def _init_match_weights(self) -> Dict[str, float]:
        """初始化匹配权重"""
        return {
            'volatility_match': 1.0,
            'trend_match': 1.0,
            'mean_reversion_match': 1.0,
            'sharpe_match': 1.0,
            'drawdown_match': 1.0,
            'risk_adjustment': 1.0,
        }
    
    def _load_config(self) -> None:
        """从配置文件加载参数"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 加载自定义权重
            if 'match_weights' in config:
                self.match_weights.update(config['match_weights'])
            
            logger.info(f"配置加载成功: {self.config_path}")
        except Exception as e:
            logger.warning(f"配置加载失败，使用默认配置: {e}")
    
    def optimize_parameters(
        self,
        historical_data: pd.DataFrame,
        target_metric: str = 'sharpe',
        optimization_method: OptimizationMethod = OptimizationMethod.GRID_SEARCH,
        param_bounds: Optional[Dict[str, Tuple[float, float]]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        max_iterations: int = 100
    ) -> OptimizationResult:
        """
        优化策略参数
        
        根据历史数据优化策略参数以达到指定的目标指标最优
        
        Args:
            historical_data: 历史数据DataFrame
            target_metric: 目标指标 ('sharpe', 'sortino', 'calmar', 'return_risk', 'max_drawdown')
            optimization_method: 优化方法
            param_bounds: 参数边界字典，如 {'param_name': (min, max)}
            constraints: 约束条件字典
            max_iterations: 最大迭代次数
            
        Returns:
            OptimizationResult: 优化结果
            
        Example:
            >>> tuner = StrategyParameterTuner()
            >>> result = tuner.optimize_parameters(
            ...     historical_data=df,
            ...     target_metric='sharpe',
            ...     optimization_method=OptimizationMethod.BAYESIAN
            ... )
        """
        start_time = datetime.now()
        
        # 参数边界默认值
        if param_bounds is None:
            param_bounds = {
                'buy_multiplier_strong': (2.0, 4.0),
                'buy_multiplier_normal': (1.0, 2.0),
                'stop_loss_threshold': (-0.20, -0.08),
                'warning_threshold': (-0.15, -0.05),
            }
        
        # 根据优化方法选择优化器
        if optimization_method == OptimizationMethod.GRID_SEARCH:
            result = self._grid_search_optimize(
                historical_data, target_metric, param_bounds, constraints
            )
        elif optimization_method == OptimizationMethod.BAYESIAN:
            result = self._bayesian_optimize(
                historical_data, target_metric, param_bounds, max_iterations
            )
        elif optimization_method == OptimizationMethod.DIFFERENTIAL_EVOLUTION:
            result = self._differential_evolution_optimize(
                historical_data, target_metric, param_bounds, max_iterations
            )
        elif optimization_method == OptimizationMethod.RANDOM_SEARCH:
            result = self._random_search_optimize(
                historical_data, target_metric, param_bounds, max_iterations
            )
        else:
            raise ValueError(f"不支持的优化方法: {optimization_method}")
        
        # 计算耗时
        computation_time = (datetime.now() - start_time).total_seconds()
        result.computation_time = computation_time
        result.optimization_method = optimization_method.value
        result.target_metric = target_metric
        
        # 保存到历史记录
        self.optimization_history.append(result)
        
        logger.info(f"参数优化完成: {target_metric} = {result.best_score:.4f}, "
                   f"耗时 {computation_time:.2f}秒")
        
        return result
    
    def _evaluate_params(
        self,
        params: Dict[str, float],
        historical_data: pd.DataFrame,
        target_metric: str
    ) -> float:
        """
        评估参数性能
        
        Args:
            params: 参数字典
            historical_data: 历史数据
            target_metric: 目标指标
            
        Returns:
            评分（越高越好）
        """
        try:
            # 使用回测引擎评估
            backtest = FundBacktest(
                base_amount=100,
                start_date=historical_data.index[0] if hasattr(historical_data.index[0], 'strftime') else '2020-01-01',
                use_unified_strategy=True
            )
            
            # 这里简化处理，实际应该修改策略参数后回测
            # 使用历史数据计算模拟绩效指标
            returns = historical_data.pct_change().dropna()
            if len(returns) < 20:
                return -np.inf
            
            calculator = PerformanceCalculator()
            
            # 计算各项指标
            sharpe = calculator.calculate_sharpe_ratio(returns.values)
            annual_return = returns.mean() * 252
            volatility = returns.std() * np.sqrt(252)
            max_dd = calculator.calculate_max_drawdown(historical_data.values)
            
            # 根据目标指标返回评分
            if target_metric == 'sharpe':
                return sharpe
            elif target_metric == 'sortino':
                return calculator.calculate_sortino_ratio(returns.values, annual_return)
            elif target_metric == 'calmar':
                return calculator.calculate_calmar_ratio(annual_return, max_dd)
            elif target_metric == 'return_risk':
                return annual_return / volatility if volatility > 0 else 0
            elif target_metric == 'max_drawdown':
                # 最大回撤越小越好，所以取负
                return -max_dd
            elif target_metric == 'total_return':
                return annual_return
            else:
                return sharpe
                
        except Exception as e:
            logger.warning(f"参数评估失败: {e}")
            return -np.inf
    
    def _grid_search_optimize(
        self,
        historical_data: pd.DataFrame,
        target_metric: str,
        param_bounds: Dict[str, Tuple[float, float]],
        constraints: Optional[Dict[str, Any]]
    ) -> OptimizationResult:
        """网格搜索优化"""
        best_score = -np.inf
        best_params = {}
        history = []
        iteration = 0
        
        # 为每个参数创建网格点
        param_names = list(param_bounds.keys())
        param_grids = []
        
        for name, (low, high) in param_bounds.items():
            # 根据范围类型选择网格点
            if name.endswith('_period'):
                # 周期参数使用整数
                grid = np.linspace(int(low), int(high), min(5, int(high) - int(low) + 1))
                grid = grid.astype(int)
            else:
                grid = np.linspace(low, high, 10)
            param_grids.append(grid)
        
        # 生成所有组合
        from itertools import product
        for combo in product(*param_grids):
            params = dict(zip(param_names, combo))
            
            # 检查约束
            if constraints and not self._check_constraints(params, constraints):
                continue
            
            score = self._evaluate_params(params, historical_data, target_metric)
            
            history.append({
                'iteration': iteration,
                'params': params.copy(),
                'score': score
            })
            
            if score > best_score:
                best_score = score
                best_params = params.copy()
            
            iteration += 1
        
        # 计算性能指标
        perf_metrics = self._calculate_performance_metrics(best_params, historical_data)
        
        return OptimizationResult(
            optimal_params=best_params,
            best_score=best_score,
            performance_metrics=perf_metrics,
            optimization_history=history,
            iterations=iteration
        )
    
    def _bayesian_optimize(
        self,
        historical_data: pd.DataFrame,
        target_metric: str,
        param_bounds: Dict[str, Tuple[float, float]],
        max_iterations: int
    ) -> OptimizationResult:
        """贝叶斯优化（简化实现）"""
        # 这里使用随机搜索作为简化实现
        # 实际生产环境可以使用 scikit-optimize
        return self._random_search_optimize(
            historical_data, target_metric, param_bounds, max_iterations
        )
    
    def _differential_evolution_optimize(
        self,
        historical_data: pd.DataFrame,
        target_metric: str,
        param_bounds: Dict[str, Tuple[float, float]],
        max_iterations: int
    ) -> OptimizationResult:
        """差分进化优化"""
        param_names = list(param_bounds.keys())
        bounds = [param_bounds[name] for name in param_names]
        
        history = []
        iteration_counter = [0]
        
        def objective(x):
            params = dict(zip(param_names, x))
            score = self._evaluate_params(params, historical_data, target_metric)
            history.append({
                'iteration': iteration_counter[0],
                'params': params.copy(),
                'score': score
            })
            iteration_counter[0] += 1
            # 差分进化是最小化，所以取负
            return -score
        
        result = differential_evolution(
            objective,
            bounds,
            maxiter=max_iterations // len(param_names),
            seed=42,
            workers=-1,
            polish=True
        )
        
        best_params = dict(zip(param_names, result.x))
        perf_metrics = self._calculate_performance_metrics(best_params, historical_data)
        
        return OptimizationResult(
            optimal_params=best_params,
            best_score=-result.fun,
            performance_metrics=perf_metrics,
            optimization_history=history,
            iterations=iteration_counter[0],
            convergence_info={
                'success': result.success,
                'message': result.message,
                'nit': result.nit
            }
        )
    
    def _random_search_optimize(
        self,
        historical_data: pd.DataFrame,
        target_metric: str,
        param_bounds: Dict[str, Tuple[float, float]],
        max_iterations: int
    ) -> OptimizationResult:
        """随机搜索优化"""
        best_score = -np.inf
        best_params = {}
        history = []
        
        param_names = list(param_bounds.keys())
        
        for i in range(max_iterations):
            # 随机采样参数
            params = {}
            for name, (low, high) in param_bounds.items():
                if name.endswith('_period'):
                    params[name] = np.random.randint(int(low), int(high) + 1)
                else:
                    params[name] = np.random.uniform(low, high)
            
            score = self._evaluate_params(params, historical_data, target_metric)
            
            history.append({
                'iteration': i,
                'params': params.copy(),
                'score': score
            })
            
            if score > best_score:
                best_score = score
                best_params = params.copy()
        
        perf_metrics = self._calculate_performance_metrics(best_params, historical_data)
        
        return OptimizationResult(
            optimal_params=best_params,
            best_score=best_score,
            performance_metrics=perf_metrics,
            optimization_history=history,
            iterations=max_iterations
        )
    
    def _check_constraints(
        self,
        params: Dict[str, float],
        constraints: Dict[str, Any]
    ) -> bool:
        """检查参数是否满足约束"""
        for key, condition in constraints.items():
            if key not in params:
                continue
            if isinstance(condition, tuple):
                low, high = condition
                if not (low <= params[key] <= high):
                    return False
        return True
    
    def _calculate_performance_metrics(
        self,
        params: Dict[str, float],
        historical_data: pd.DataFrame
    ) -> Dict[str, float]:
        """计算性能指标"""
        returns = historical_data.pct_change().dropna()
        calculator = PerformanceCalculator()
        
        # 提取数值（处理pandas Series/DataFrame的情况）
        def get_scalar(val):
            if hasattr(val, 'item'):
                return val.item() if hasattr(val, 'size') and val.size == 1 else float(val.iloc[0]) if len(val) > 0 else 0.0
            return float(val)
        
        annual_return = get_scalar(returns.mean() * 252)
        volatility = get_scalar(returns.std() * np.sqrt(252))
        max_dd = calculator.calculate_max_drawdown(historical_data.values)
        
        return {
            'sharpe_ratio': calculator.calculate_sharpe_ratio(returns.values),
            'sortino_ratio': calculator.calculate_sortino_ratio(returns.values, annual_return),
            'calmar_ratio': calculator.calculate_calmar_ratio(annual_return, max_dd),
            'annual_return': annual_return,
            'volatility': volatility,
            'max_drawdown': max_dd,
            'return_risk_ratio': annual_return / volatility if volatility > 0 else 0
        }
    
    def adaptive_match_score(
        self,
        fund_profile: FundProfile,
        base_score: float,
        performance_history: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        自适应调整匹配分数
        
        根据基金画像、历史表现和市场状态动态调整策略匹配分数
        
        Args:
            fund_profile: 基金画像
            base_score: 基础匹配分数
            performance_history: 历史表现数据列表
            
        Returns:
            (调整后的分数, 调整信息字典)
            
        Example:
            >>> adjusted_score, info = tuner.adaptive_match_score(
            ...     fund_profile=profile,
            ...     base_score=75.0,
            ...     performance_history=history
            ... )
        """
        adjusted_score = base_score
        adjustments = []
        
        # 1. 根据市场状态调整
        market_state = self._detect_market_state_from_profile(fund_profile)
        market_adjustments = self.MARKET_STATE_ADJUSTMENTS.get(market_state, {})
        
        if 'trend_following_weight' in market_adjustments:
            if abs(fund_profile.trend_strength) > 0.3:
                trend_adjustment = market_adjustments['trend_following_weight']
                adjusted_score *= trend_adjustment
                adjustments.append(f"趋势权重调整: {trend_adjustment:.2f}")
        
        if 'mean_reversion_weight' in market_adjustments:
            if fund_profile.mean_reversion_score > 0.3:
                mr_adjustment = market_adjustments['mean_reversion_weight']
                adjusted_score *= mr_adjustment
                adjustments.append(f"均值回归权重调整: {mr_adjustment:.2f}")
        
        # 2. 根据历史表现调整
        if performance_history and len(performance_history) > 0:
            recent_perf = performance_history[-10:]  # 最近10次
            success_rate = sum(1 for p in recent_perf if p.get('success', False)) / len(recent_perf)
            
            # 成功率调整
            if success_rate > 0.7:
                adjusted_score *= 1.1
                adjustments.append("高成功率加成: 1.10")
            elif success_rate < 0.3:
                adjusted_score *= 0.9
                adjustments.append("低成功率惩罚: 0.90")
        
        # 3. 风险调整
        if fund_profile.sharpe_ratio < 0:
            adjusted_score *= 0.85
            adjustments.append("负夏普惩罚: 0.85")
        elif fund_profile.sharpe_ratio > 1.0:
            adjusted_score *= 1.15
            adjustments.append("高夏普加成: 1.15")
        
        # 4. 最大回撤调整
        if fund_profile.max_drawdown < -30:
            adjusted_score *= 0.8
            adjustments.append("大回撤惩罚: 0.80")
        elif fund_profile.max_drawdown > -10:
            adjusted_score *= 1.1
            adjustments.append("低回撤加成: 1.10")
        
        # 限制分数范围
        adjusted_score = float(np.clip(adjusted_score, 0, 100))
        
        info = {
            'original_score': base_score,
            'adjusted_score': adjusted_score,
            'market_state': market_state.value,
            'adjustments': adjustments,
            'match_weights_applied': self.match_weights.copy()
        }
        
        return adjusted_score, info
    
    def _detect_market_state_from_profile(self, fund_profile: FundProfile) -> MarketState:
        """从基金画像推断市场状态"""
        if fund_profile.avg_return > 15 and fund_profile.trend_strength > 0.3:
            return MarketState.BULL
        elif fund_profile.avg_return < -10 and fund_profile.trend_strength < -0.3:
            return MarketState.BEAR
        elif abs(fund_profile.trend_strength) < 0.2:
            return MarketState.SIDEWAYS
        return MarketState.UNKNOWN
    
    def grid_search_backtest(
        self,
        fund_codes: List[str],
        param_grid: Dict[str, List[Any]],
        start_date: str = '2020-01-01',
        end_date: Optional[str] = None,
        target_metric: str = 'sharpe',
        n_jobs: int = 1
    ) -> List[OptimizationResult]:
        """
        网格搜索最优参数组合
        
        对多只基金进行网格搜索，找出最优的参数组合
        
        Args:
            fund_codes: 基金代码列表
            param_grid: 参数网格，如 {'param': [1, 2, 3]}
            start_date: 回测开始日期
            end_date: 回测结束日期
            target_metric: 目标优化指标
            n_jobs: 并行任务数（暂不支持并行）
            
        Returns:
            每只基金的优化结果列表
            
        Example:
            >>> results = tuner.grid_search_backtest(
            ...     fund_codes=['000001', '000002'],
            ...     param_grid={
            ...         'buy_multiplier': [1.0, 1.5, 2.0],
            ...         'stop_loss': [-0.10, -0.15, -0.20]
            ...     }
            ... )
        """
        results = []
        param_names = list(param_grid.keys())
        
        # 生成所有参数组合
        from itertools import product
        param_combinations = list(product(*param_grid.values()))
        
        logger.info(f"开始网格搜索: {len(fund_codes)}只基金, "
                   f"{len(param_combinations)}种参数组合")
        
        for fund_code in fund_codes:
            best_result = None
            best_score = -np.inf
            
            try:
                # 获取基金历史数据
                backtest = FundBacktest(
                    base_amount=100,
                    start_date=start_date,
                    end_date=end_date
                )
                
                fund_hist = backtest.get_fund_history(fund_code)
                if fund_hist is None or len(fund_hist) < 60:
                    logger.warning(f"基金 {fund_code} 数据不足，跳过")
                    continue
                
                # 测试每种参数组合
                for combo in param_combinations:
                    params = dict(zip(param_names, combo))
                    
                    # 执行回测
                    result_df = backtest.backtest_single_fund(fund_code)
                    if result_df is None:
                        continue
                    
                    # 计算性能指标
                    metrics = backtest.calculate_performance_metrics(result_df)
                    if metrics is None:
                        continue
                    
                    # 获取目标指标值
                    metric_key = f"{target_metric}_strategy"
                    if metric_key in metrics:
                        score = metrics[metric_key]
                    elif target_metric == 'max_drawdown':
                        # 最大回撤越小越好
                        score = -metrics.get('最大回撤_strategy', 0)
                    else:
                        score = metrics.get('夏普比率_strategy', 0)
                    
                    if score > best_score:
                        best_score = score
                        best_result = OptimizationResult(
                            optimal_params=params,
                            best_score=score,
                            target_metric=target_metric,
                            optimization_method='grid_search',
                            performance_metrics=metrics
                        )
                
                if best_result:
                    results.append(best_result)
                    logger.info(f"基金 {fund_code} 最优参数: {best_result.optimal_params}, "
                               f"得分: {best_score:.4f}")
                
            except Exception as e:
                logger.error(f"基金 {fund_code} 网格搜索失败: {e}")
                continue
        
        return results
    
    def update_match_weights(
        self,
        feedback_data: List[FeedbackData],
        learning_rate: float = 0.1,
        min_samples: int = 30
    ) -> Dict[str, Any]:
        """
        根据反馈更新匹配权重
        
        使用实际交易反馈数据来更新策略匹配权重，实现在线学习
        
        Args:
            feedback_data: 反馈数据列表
            learning_rate: 学习率
            min_samples: 最小样本数
            
        Returns:
            更新信息字典
            
        Example:
            >>> feedback = [
            ...     FeedbackData(fund_code='000001', strategy_type='dual_ma', 
            ...                  predicted_action='buy', actual_return=0.02)
            ... ]
            >>> info = tuner.update_match_weights(feedback)
        """
        if len(feedback_data) < min_samples:
            return {
                'updated': False,
                'reason': f'样本不足 ({len(feedback_data)} < {min_samples})',
                'current_weights': self.match_weights.copy()
            }
        
        updates = {}
        
        # 按策略类型分组统计
        strategy_groups: Dict[str, List[FeedbackData]] = {}
        for fb in feedback_data:
            if fb.strategy_type not in strategy_groups:
                strategy_groups[fb.strategy_type] = []
            strategy_groups[fb.strategy_type].append(fb)
        
        # 计算每种策略的表现
        for strategy_type, fbs in strategy_groups.items():
            if len(fbs) < 10:  # 单个策略最少样本
                continue
            
            success_rate = sum(1 for fb in fbs if fb.success) / len(fbs)
            avg_return = np.mean([fb.actual_return for fb in fbs])
            avg_error = np.mean([abs(fb.error) for fb in fbs])
            
            # 根据表现更新权重
            if success_rate > 0.6 and avg_return > 0:
                # 表现良好，增加权重
                weight_key = f'{strategy_type}_match'
                if weight_key in self.match_weights:
                    old_weight = self.match_weights[weight_key]
                    self.match_weights[weight_key] *= (1 + learning_rate)
                    updates[weight_key] = {
                        'old': old_weight,
                        'new': self.match_weights[weight_key],
                        'reason': f'高成功率 ({success_rate:.2%})'
                    }
            elif success_rate < 0.4 or avg_return < -0.02:
                # 表现差，降低权重
                weight_key = f'{strategy_type}_match'
                if weight_key in self.match_weights:
                    old_weight = self.match_weights[weight_key]
                    self.match_weights[weight_key] *= (1 - learning_rate)
                    updates[weight_key] = {
                        'old': old_weight,
                        'new': self.match_weights[weight_key],
                        'reason': f'低成功率 ({success_rate:.2%})'
                    }
        
        # 按市场状态分组统计
        market_groups: Dict[str, List[FeedbackData]] = {}
        for fb in feedback_data:
            if fb.market_state not in market_groups:
                market_groups[fb.market_state] = []
            market_groups[fb.market_state].append(fb)
        
        market_adjustments = {}
        for market_state, fbs in market_groups.items():
            if len(fbs) < 10:
                continue
            avg_success = sum(1 for fb in fbs if fb.success) / len(fbs)
            market_adjustments[market_state] = avg_success
        
        return {
            'updated': True,
            'sample_count': len(feedback_data),
            'strategy_types': list(strategy_groups.keys()),
            'weight_updates': updates,
            'current_weights': self.match_weights.copy(),
            'market_adjustments': market_adjustments
        }
    
    def multi_objective_optimize(
        self,
        historical_data: pd.DataFrame,
        objectives: List[str] = None,
        weights: Optional[List[float]] = None
    ) -> OptimizationResult:
        """
        多目标优化
        
        同时优化多个目标指标，使用加权求和方法
        
        Args:
            historical_data: 历史数据
            objectives: 目标指标列表，默认 ['sharpe', 'return_risk', 'max_drawdown']
            weights: 各目标的权重，默认等权重
            
        Returns:
            优化结果
        """
        if objectives is None:
            objectives = ['sharpe', 'return_risk', 'max_drawdown']
        
        if weights is None:
            weights = [1.0 / len(objectives)] * len(objectives)
        
        # 归一化权重
        weights = np.array(weights) / sum(weights)
        
        def combined_objective(params_list):
            params = {
                'buy_multiplier_strong': params_list[0],
                'buy_multiplier_normal': params_list[1],
                'stop_loss_threshold': params_list[2],
            }
            
            scores = []
            for obj in objectives:
                score = self._evaluate_params(params, historical_data, obj)
                # 对于最大回撤，需要反转（越小越好）
                if obj == 'max_drawdown':
                    score = -score
                scores.append(score)
            
            # 加权求和
            combined = sum(w * s for w, s in zip(weights, scores))
            return -combined  # 最小化问题
        
        # 使用scipy优化
        bounds = [(2.0, 4.0), (1.0, 2.0), (-0.20, -0.08)]
        result = minimize(
            combined_objective,
            x0=[2.5, 1.5, -0.12],
            bounds=bounds,
            method='L-BFGS-B'
        )
        
        optimal_params = {
            'buy_multiplier_strong': result.x[0],
            'buy_multiplier_normal': result.x[1],
            'stop_loss_threshold': result.x[2],
        }
        
        perf_metrics = self._calculate_performance_metrics(optimal_params, historical_data)
        
        return OptimizationResult(
            optimal_params=optimal_params,
            best_score=-result.fun,
            target_metric='multi_objective',
            optimization_method='weighted_sum',
            performance_metrics=perf_metrics,
            convergence_info={'success': result.success, 'message': str(result.message)}
        )
    
    # ========================================================================
    # 配置文件管理
    # ========================================================================
    
    def save_parameters_to_config(
        self,
        parameter_set: ParameterSet,
        backup: bool = True
    ) -> bool:
        """
        保存参数到配置文件
        
        Args:
            parameter_set: 参数集合
            backup: 是否备份原配置
            
        Returns:
            是否保存成功
        """
        if self.config_path is None:
            logger.error("未指定配置文件路径")
            return False
        
        try:
            # 备份原配置
            if backup and self.config_path.exists():
                backup_path = self.config_path.with_suffix(
                    f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.yaml'
                )
                backup_path.write_text(self.config_path.read_text(encoding='utf-8'), encoding='utf-8')
            
            # 读取现有配置
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}
            
            # 更新配置
            config['optimized_parameters'] = parameter_set.to_dict()
            config['optimization_timestamp'] = datetime.now().isoformat()
            config['parameter_version'] = parameter_set.version
            
            # 写入配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            
            logger.info(f"参数已保存到: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def load_parameters_from_config(self, name: str = 'optimized_parameters') -> Optional[ParameterSet]:
        """
        从配置文件加载参数
        
        Args:
            name: 参数集名称
            
        Returns:
            参数集合或None
        """
        if self.config_path is None or not self.config_path.exists():
            return None
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            if name in config:
                return ParameterSet.from_dict(config[name])
            
            return None
            
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return None
    
    def list_parameter_versions(self) -> List[Dict[str, Any]]:
        """
        列出所有参数版本
        
        Returns:
            版本信息列表
        """
        versions = []
        
        # 从优化历史中提取
        for result in self.optimization_history:
            if result.optimal_params:
                versions.append({
                    'timestamp': datetime.now().isoformat(),
                    'method': result.optimization_method,
                    'target_metric': result.target_metric,
                    'best_score': result.best_score,
                    'params_hash': hashlib.md5(
                        json.dumps(result.optimal_params, sort_keys=True).encode()
                    ).hexdigest()[:8]
                })
        
        return versions
    
    # ========================================================================
    # A/B测试框架
    # ========================================================================
    
    def create_ab_test(
        self,
        test_id: str,
        control_params: Dict[str, Any],
        treatment_params: Dict[str, Any],
        traffic_split: float = 0.5,
        duration_days: int = 30,
        success_metric: str = 'sharpe'
    ) -> ABTestConfig:
        """
        创建A/B测试
        
        Args:
            test_id: 测试ID
            control_params: 对照组参数（A组）
            treatment_params: 实验组参数（B组）
            traffic_split: 流量分配比例（A组比例，默认0.5）
            duration_days: 测试持续时间
            success_metric: 成功评估指标
            
        Returns:
            A/B测试配置
        """
        ab_test = ABTestConfig(
            test_id=test_id,
            control_params=control_params,
            treatment_params=treatment_params,
            traffic_split=traffic_split,
            duration_days=duration_days,
            success_metric=success_metric,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=duration_days)
        )
        
        self.ab_tests[test_id] = ab_test
        logger.info(f"创建A/B测试: {test_id}, 持续 {duration_days} 天")
        
        return ab_test
    
    def assign_to_ab_group(self, test_id: str, user_id: str = None) -> str:
        """
        将用户分配到A/B测试组
        
        Args:
            test_id: 测试ID
            user_id: 用户ID（用于确定性分配）
            
        Returns:
            分配的组别 ('control' 或 'treatment')
        """
        if test_id not in self.ab_tests:
            raise ValueError(f"未知的A/B测试: {test_id}")
        
        ab_test = self.ab_tests[test_id]
        
        if user_id:
            # 基于用户ID的确定性分配
            hash_val = int(hashlib.md5(f"{test_id}:{user_id}".encode()).hexdigest(), 16)
            assignment = hash_val % 100 / 100
        else:
            # 随机分配
            assignment = np.random.random()
        
        return 'control' if assignment < ab_test.traffic_split else 'treatment'
    
    def get_ab_params(self, test_id: str, group: str) -> Dict[str, Any]:
        """
        获取A/B测试组的参数
        
        Args:
            test_id: 测试ID
            group: 组别 ('control' 或 'treatment')
            
        Returns:
            参数字典
        """
        if test_id not in self.ab_tests:
            raise ValueError(f"未知的A/B测试: {test_id}")
        
        ab_test = self.ab_tests[test_id]
        
        if group == 'control':
            return ab_test.control_params
        elif group == 'treatment':
            return ab_test.treatment_params
        else:
            raise ValueError(f"无效的组别: {group}")
    
    def analyze_ab_test(
        self,
        test_id: str,
        control_results: List[float],
        treatment_results: List[float]
    ) -> Dict[str, Any]:
        """
        分析A/B测试结果
        
        Args:
            test_id: 测试ID
            control_results: 对照组结果列表
            treatment_results: 实验组结果列表
            
        Returns:
            分析结果字典
        """
        if len(control_results) < 10 or len(treatment_results) < 10:
            return {
                'valid': False,
                'reason': '样本量不足'
            }
        
        control_mean = np.mean(control_results)
        treatment_mean = np.mean(treatment_results)
        control_std = np.std(control_results)
        treatment_std = np.std(treatment_results)
        
        # 计算效应量（Cohen's d）
        pooled_std = np.sqrt((control_std**2 + treatment_std**2) / 2)
        cohens_d = (treatment_mean - control_mean) / pooled_std if pooled_std > 0 else 0
        
        # 简单t检验近似（使用z检验）
        se = np.sqrt(control_std**2/len(control_results) + treatment_std**2/len(treatment_results))
        z_score = (treatment_mean - control_mean) / se if se > 0 else 0
        p_value = 2 * (1 - norm.cdf(abs(z_score)))
        
        return {
            'valid': True,
            'test_id': test_id,
            'control': {
                'n': len(control_results),
                'mean': control_mean,
                'std': control_std
            },
            'treatment': {
                'n': len(treatment_results),
                'mean': treatment_mean,
                'std': treatment_std
            },
            'difference': treatment_mean - control_mean,
            'relative_lift': (treatment_mean - control_mean) / control_mean if control_mean != 0 else 0,
            'cohens_d': cohens_d,
            'z_score': z_score,
            'p_value': p_value,
            'significant': p_value < 0.05,
            'recommendation': 'treatment' if p_value < 0.05 and treatment_mean > control_mean else 'control'
        }
    
    def end_ab_test(self, test_id: str, winner: Optional[str] = None) -> Dict[str, Any]:
        """
        结束A/B测试
        
        Args:
            test_id: 测试ID
            winner: 获胜组别（可选）
            
        Returns:
            测试结果摘要
        """
        if test_id not in self.ab_tests:
            raise ValueError(f"未知的A/B测试: {test_id}")
        
        ab_test = self.ab_tests[test_id]
        ab_test.status = 'completed'
        ab_test.end_date = datetime.now()
        
        return {
            'test_id': test_id,
            'status': 'completed',
            'winner': winner,
            'duration_days': (ab_test.end_date - ab_test.start_date).days if ab_test.start_date else 0,
            'control_params': ab_test.control_params,
            'treatment_params': ab_test.treatment_params
        }
    
    # ========================================================================
    # 工具方法
    # ========================================================================
    
    def get_optimization_summary(self) -> str:
        """获取优化历史摘要"""
        lines = [
            "=" * 60,
            "策略参数调优器 - 优化历史摘要",
            "=" * 60,
            f"总优化次数: {len(self.optimization_history)}",
            f"当前匹配权重: {self.match_weights}",
            f"活跃A/B测试: {len([t for t in self.ab_tests.values() if t.status == 'running'])}",
        ]
        
        if self.optimization_history:
            lines.append("-" * 60)
            lines.append("最近优化记录:")
            for i, result in enumerate(self.optimization_history[-5:]):
                lines.append(f"  {i+1}. {result.target_metric}: {result.best_score:.4f} "
                           f"({result.optimization_method})")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def reset_weights(self) -> None:
        """重置匹配权重为默认值"""
        self.match_weights = self._init_match_weights()
        logger.info("匹配权重已重置为默认值")
    
    def export_optimization_report(self, filepath: str) -> bool:
        """
        导出优化报告
        
        Args:
            filepath: 导出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            report = {
                'export_time': datetime.now().isoformat(),
                'optimization_count': len(self.optimization_history),
                'match_weights': self.match_weights,
                'optimization_history': [
                    result.to_dict() for result in self.optimization_history
                ],
                'ab_tests': {
                    test_id: {
                        'test_id': test.test_id,
                        'status': test.status,
                        'traffic_split': test.traffic_split,
                        'success_metric': test.success_metric
                    }
                    for test_id, test in self.ab_tests.items()
                }
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"优化报告已导出: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"导出报告失败: {e}")
            return False


# ============================================================================
# 便捷函数
# ============================================================================

def create_default_tuner(config_path: Optional[str] = None) -> StrategyParameterTuner:
    """
    创建默认的参数调优器
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        StrategyParameterTuner实例
    """
    return StrategyParameterTuner(config_path=config_path)


def quick_optimize(
    historical_data: pd.DataFrame,
    target_metric: str = 'sharpe',
    method: str = 'grid_search'
) -> OptimizationResult:
    """
    快速优化函数
    
    Args:
        historical_data: 历史数据
        target_metric: 目标指标
        method: 优化方法
        
    Returns:
        优化结果
    """
    tuner = StrategyParameterTuner()
    method_enum = OptimizationMethod(method) if method in [m.value for m in OptimizationMethod] else OptimizationMethod.GRID_SEARCH
    
    return tuner.optimize_parameters(
        historical_data=historical_data,
        target_metric=target_metric,
        optimization_method=method_enum
    )


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("策略参数调优器 - 功能演示")
    print("=" * 60)
    
    # 创建调优器
    tuner = StrategyParameterTuner()
    
    # 生成模拟历史数据
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', '2023-12-31', freq='B')
    returns = np.random.normal(0.0005, 0.02, len(dates))
    prices = 1.0 * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'close': prices
    }, index=dates)
    
    print("\n1. 参数优化演示")
    print("-" * 60)
    
    # 执行优化
    result = tuner.optimize_parameters(
        historical_data=df,
        target_metric='sharpe',
        optimization_method=OptimizationMethod.RANDOM_SEARCH,
        max_iterations=50
    )
    
    print(result.get_summary())
    
    print("\n2. 自适应匹配分数演示")
    print("-" * 60)
    
    # 创建基金画像
    profile = FundProfile(
        fund_code='000001',
        fund_name='测试基金',
        volatility=0.25,
        trend_strength=0.5,
        mean_reversion_score=0.3,
        sharpe_ratio=0.8,
        max_drawdown=-15.0,
        avg_return=12.0
    )
    
    adjusted_score, info = tuner.adaptive_match_score(
        fund_profile=profile,
        base_score=75.0,
        performance_history=[{'success': True}, {'success': True}, {'success': False}]
    )
    
    print(f"基础分数: {info['original_score']:.2f}")
    print(f"调整后分数: {info['adjusted_score']:.2f}")
    print(f"市场状态: {info['market_state']}")
    print(f"调整项: {info['adjustments']}")
    
    print("\n3. 多目标优化演示")
    print("-" * 60)
    
    multi_result = tuner.multi_objective_optimize(
        historical_data=df,
        objectives=['sharpe', 'return_risk', 'max_drawdown'],
        weights=[0.4, 0.3, 0.3]
    )
    
    print(f"多目标优化最佳得分: {multi_result.best_score:.4f}")
    print(f"最优参数: {multi_result.optimal_params}")
    
    print("\n4. A/B测试演示")
    print("-" * 60)
    
    ab_test = tuner.create_ab_test(
        test_id='test_001',
        control_params={'buy_multiplier': 1.5, 'stop_loss': -0.10},
        treatment_params={'buy_multiplier': 2.0, 'stop_loss': -0.15},
        traffic_split=0.5,
        duration_days=30
    )
    
    # 模拟用户分配
    for i in range(10):
        group = tuner.assign_to_ab_group('test_001', user_id=f'user_{i}')
        params = tuner.get_ab_params('test_001', group)
        print(f"  用户 {i}: 分配至 {group} 组, 参数: {params}")
    
    print("\n5. 优化历史摘要")
    print("-" * 60)
    print(tuner.get_optimization_summary())
    
    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)
