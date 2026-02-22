#!/usr/bin/env python
# coding: utf-8

"""
绩效指标计算模块
Performance Metrics Calculator

计算回测结果的各种绩效指标：
- 总收益率、年化收益率
- 最大回撤、波动率
- 夏普比率、索提诺比率、卡玛比率
- 胜率、盈亏比
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple, Callable
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """绩效指标数据类"""
    # 收益指标
    total_return: float = 0.0           # 总收益率
    annual_return: float = 0.0          # 年化收益率
    benchmark_return: float = 0.0       # 基准收益率
    excess_return: float = 0.0          # 超额收益率
    
    # 风险指标
    max_drawdown: float = 0.0           # 最大回撤
    volatility: float = 0.0             # 年化波动率
    downside_volatility: float = 0.0    # 下行波动率
    
    # 风险调整收益指标
    sharpe_ratio: float = 0.0           # 夏普比率
    sortino_ratio: float = 0.0          # 索提诺比率
    calmar_ratio: float = 0.0           # 卡玛比率
    information_ratio: float = 0.0      # 信息比率
    
    # 交易统计
    win_rate: float = 0.0               # 胜率
    profit_loss_ratio: float = 0.0      # 盈亏比
    total_trades: int = 0               # 总交易次数
    winning_trades: int = 0             # 盈利交易次数
    losing_trades: int = 0              # 亏损交易次数
    
    # 其他指标
    alpha: float = 0.0                  # Alpha
    beta: float = 0.0                   # Beta
    var_95: float = 0.0                 # 95% VaR
    var_99: float = 0.0                 # 99% VaR
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'benchmark_return': self.benchmark_return,
            'excess_return': self.excess_return,
            'max_drawdown': self.max_drawdown,
            'volatility': self.volatility,
            'downside_volatility': self.downside_volatility,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'calmar_ratio': self.calmar_ratio,
            'information_ratio': self.information_ratio,
            'win_rate': self.win_rate,
            'profit_loss_ratio': self.profit_loss_ratio,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'alpha': self.alpha,
            'beta': self.beta,
            'var_95': self.var_95,
            'var_99': self.var_99
        }




@dataclass
class MetricsInput:
    """标准化指标输入数据格式"""
    equity_curve: List[float]
    benchmark_curve: Optional[List[float]] = None
    trades: Optional[List[Dict[str, Any]]] = None
    risk_free_rate: float = 0.02
    trading_days: int = 252
    metadata: Optional[Dict[str, Any]] = None
    dimensions: Optional[Dict[str, "MetricsInput"]] = None


@dataclass
class MetricRuleSet:
    """业务规则配置，用于动态调整指标计算"""
    enabled_metrics: Optional[List[str]] = None
    risk_free_rate: Optional[float] = None
    trading_days: Optional[int] = None
    annualization_days: Optional[int] = None
    overrides: Optional[Dict[str, Dict[str, Any]]] = None

    def is_enabled(self, metric_id: str) -> bool:
        if self.enabled_metrics is None:
            return True
        return metric_id in self.enabled_metrics

    def get_param(self, metric_id: str, key: str, default: Any) -> Any:
        if self.overrides and metric_id in self.overrides and key in self.overrides[metric_id]:
            return self.overrides[metric_id][key]
        if key == 'risk_free_rate' and self.risk_free_rate is not None:
            return self.risk_free_rate
        if key == 'trading_days' and self.trading_days is not None:
            return self.trading_days
        if key == 'annualization_days' and self.annualization_days is not None:
            return self.annualization_days
        return default


@dataclass
class MetricValue:
    """单个指标标准化输出"""
    metric_id: str
    name: str
    value: float
    category: str
    unit: str
    description: str
    meta: Optional[Dict[str, Any]] = None


@dataclass
class MetricBundle:
    """指标集合（统一输出格式）"""
    metrics: Dict[str, MetricValue]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'metrics': {
                metric_id: {
                    'id': metric.metric_id,
                    'name': metric.name,
                    'value': metric.value,
                    'category': metric.category,
                    'unit': metric.unit,
                    'description': metric.description,
                    'meta': metric.meta or {}
                }
                for metric_id, metric in self.metrics.items()
            }
        }

    def to_flat_dict(self) -> Dict[str, float]:
        return {metric_id: metric.value for metric_id, metric in self.metrics.items()}


@dataclass
class MetricReport:
    """指标报告（支持多维度）"""
    summary: MetricBundle
    dimensions: Optional[Dict[str, MetricBundle]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'summary': self.summary.to_dict(),
            'dimensions': {name: bundle.to_dict() for name, bundle in (self.dimensions or {}).items()},
            'metadata': self.metadata or {}
        }

    def to_flat_dict(self) -> Dict[str, Any]:
        data = {'summary': self.summary.to_flat_dict()}
        if self.dimensions:
            data['dimensions'] = {name: bundle.to_flat_dict() for name, bundle in self.dimensions.items()}
        if self.metadata:
            data['metadata'] = self.metadata
        return data


@dataclass
class MetricDefinition:
    """指标定义（接口描述）"""
    metric_id: str
    name: str
    category: str
    unit: str
    description: str
    compute: Callable[[MetricsInput, "PerformanceCalculator", MetricRuleSet, Dict[str, Any]], float]


class MetricEngine:
    """可扩展指标引擎（核心计算逻辑与业务规则解耦）"""

    DEFAULT_METRIC_ORDER = [
        'total_return',
        'annual_return',
        'benchmark_return',
        'excess_return',
        'max_drawdown',
        'volatility',
        'downside_volatility',
        'sharpe_ratio',
        'sortino_ratio',
        'calmar_ratio',
        'information_ratio',
        'alpha',
        'beta',
        'var_95',
        'var_99',
        'win_rate',
        'profit_loss_ratio',
        'total_trades',
        'winning_trades',
        'losing_trades'
    ]

    def __init__(self, rule_set: Optional[MetricRuleSet] = None):
        self.rule_set = rule_set or MetricRuleSet()
        self.registry: Dict[str, MetricDefinition] = {}
        self.register_defaults()

    def register(self, definition: MetricDefinition) -> None:
        self.registry[definition.metric_id] = definition

    def register_defaults(self) -> None:
        self.register(MetricDefinition(
            metric_id='total_return',
            name='总收益率',
            category='收益',
            unit='ratio',
            description='期间总收益率',
            compute=self._compute_total_return
        ))
        self.register(MetricDefinition(
            metric_id='annual_return',
            name='年化收益率',
            category='收益',
            unit='ratio',
            description='按年度折算的收益率',
            compute=self._compute_annual_return
        ))
        self.register(MetricDefinition(
            metric_id='benchmark_return',
            name='基准收益率',
            category='收益',
            unit='ratio',
            description='基准净值的收益率',
            compute=self._compute_benchmark_return
        ))
        self.register(MetricDefinition(
            metric_id='excess_return',
            name='超额收益',
            category='收益',
            unit='ratio',
            description='组合收益率减去基准收益率',
            compute=self._compute_excess_return
        ))
        self.register(MetricDefinition(
            metric_id='max_drawdown',
            name='最大回撤',
            category='风险',
            unit='ratio',
            description='期间最大回撤幅度',
            compute=self._compute_max_drawdown
        ))
        self.register(MetricDefinition(
            metric_id='volatility',
            name='年化波动率',
            category='风险',
            unit='ratio',
            description='收益率年化波动率',
            compute=self._compute_volatility
        ))
        self.register(MetricDefinition(
            metric_id='downside_volatility',
            name='下行波动率',
            category='风险',
            unit='ratio',
            description='下行收益的年化波动率',
            compute=self._compute_downside_volatility
        ))
        self.register(MetricDefinition(
            metric_id='sharpe_ratio',
            name='夏普比率',
            category='风险调整',
            unit='ratio',
            description='单位风险超额收益',
            compute=self._compute_sharpe_ratio
        ))
        self.register(MetricDefinition(
            metric_id='sortino_ratio',
            name='索提诺比率',
            category='风险调整',
            unit='ratio',
            description='仅考虑下行风险的收益评价',
            compute=self._compute_sortino_ratio
        ))
        self.register(MetricDefinition(
            metric_id='calmar_ratio',
            name='卡玛比率',
            category='风险调整',
            unit='ratio',
            description='年化收益与最大回撤之比',
            compute=self._compute_calmar_ratio
        ))
        self.register(MetricDefinition(
            metric_id='information_ratio',
            name='信息比率',
            category='风险调整',
            unit='ratio',
            description='超额收益与跟踪误差之比',
            compute=self._compute_information_ratio
        ))
        self.register(MetricDefinition(
            metric_id='alpha',
            name='Alpha',
            category='风险调整',
            unit='ratio',
            description='超额收益回归截距',
            compute=self._compute_alpha
        ))
        self.register(MetricDefinition(
            metric_id='beta',
            name='Beta',
            category='风险调整',
            unit='ratio',
            description='与基准收益的敏感度',
            compute=self._compute_beta
        ))
        self.register(MetricDefinition(
            metric_id='var_95',
            name='VaR 95%',
            category='风险',
            unit='ratio',
            description='95%置信水平的VaR',
            compute=self._compute_var_95
        ))
        self.register(MetricDefinition(
            metric_id='var_99',
            name='VaR 99%',
            category='风险',
            unit='ratio',
            description='99%置信水平的VaR',
            compute=self._compute_var_99
        ))
        self.register(MetricDefinition(
            metric_id='win_rate',
            name='胜率',
            category='交易',
            unit='ratio',
            description='盈利交易占比',
            compute=self._compute_win_rate
        ))
        self.register(MetricDefinition(
            metric_id='profit_loss_ratio',
            name='盈亏比',
            category='交易',
            unit='ratio',
            description='盈利与亏损的比值',
            compute=self._compute_profit_loss_ratio
        ))
        self.register(MetricDefinition(
            metric_id='total_trades',
            name='交易次数',
            category='交易',
            unit='count',
            description='交易总次数',
            compute=self._compute_total_trades
        ))
        self.register(MetricDefinition(
            metric_id='winning_trades',
            name='盈利交易次数',
            category='交易',
            unit='count',
            description='盈利交易数量',
            compute=self._compute_winning_trades
        ))
        self.register(MetricDefinition(
            metric_id='losing_trades',
            name='亏损交易次数',
            category='交易',
            unit='count',
            description='亏损交易数量',
            compute=self._compute_losing_trades
        ))

    def compute(self, metrics_input: MetricsInput) -> MetricReport:
        summary_bundle = self._compute_bundle(metrics_input, self.rule_set)
        dimensions_report = {}
        if metrics_input.dimensions:
            for name, dimension_input in metrics_input.dimensions.items():
                dimensions_report[name] = self._compute_bundle(dimension_input, self.rule_set)
        return MetricReport(
            summary=summary_bundle,
            dimensions=dimensions_report or None,
            metadata=metrics_input.metadata
        )

    def _compute_bundle(self, metrics_input: MetricsInput, rule_set: MetricRuleSet) -> MetricBundle:
        metrics: Dict[str, MetricValue] = {}
        if not metrics_input.equity_curve or len(metrics_input.equity_curve) < 2:
            return MetricBundle(metrics=metrics)

        trading_days = rule_set.get_param('global', 'trading_days', metrics_input.trading_days)
        risk_free_rate = rule_set.get_param('global', 'risk_free_rate', metrics_input.risk_free_rate)
        annualization_days = rule_set.get_param('annual_return', 'annualization_days', 365)

        calculator = PerformanceCalculator(
            risk_free_rate=risk_free_rate,
            trading_days=trading_days
        )

        context = {
            'calculator': calculator,
            'trading_days': trading_days,
            'risk_free_rate': risk_free_rate,
            'annualization_days': annualization_days,
            'daily_returns': calculator.calculate_daily_returns(metrics_input.equity_curve),
            'benchmark_returns': calculator.calculate_daily_returns(metrics_input.benchmark_curve)
            if metrics_input.benchmark_curve else np.array([]),
            'trade_pnl': calculator._extract_trade_pnl(metrics_input.trades) if metrics_input.trades else ([], [])
        }

        for metric_id in self.DEFAULT_METRIC_ORDER:
            if metric_id not in self.registry:
                continue
            if not rule_set.is_enabled(metric_id):
                continue
            definition = self.registry[metric_id]
            value = definition.compute(metrics_input, calculator, rule_set, context)
            metrics[metric_id] = MetricValue(
                metric_id=metric_id,
                name=definition.name,
                value=float(value) if value is not None else 0.0,
                category=definition.category,
                unit=definition.unit,
                description=definition.description,
                meta={
                    'risk_free_rate': risk_free_rate,
                    'trading_days': trading_days,
                    'annualization_days': annualization_days
                }
            )

        return MetricBundle(metrics=metrics)

    @staticmethod
    def _annualize_return(total_return: float, days: int, annualization_days: int) -> float:
        if days <= 0:
            return 0.0
        if total_return <= -1:
            return -1.0
        return (1 + total_return) ** (annualization_days / days) - 1

    def _compute_total_return(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        return calculator.calculate_total_return(metrics_input.equity_curve)

    def _compute_annual_return(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        total_return = context.get('computed_total_return')
        if total_return is None:
            total_return = calculator.calculate_total_return(metrics_input.equity_curve)
            context['computed_total_return'] = total_return
        days = len(metrics_input.equity_curve)
        annualization_days = rule_set.get_param('annual_return', 'annualization_days', context.get('annualization_days', 365))
        return self._annualize_return(total_return, days, annualization_days)

    def _compute_benchmark_return(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        if not metrics_input.benchmark_curve or len(metrics_input.benchmark_curve) < 2:
            return 0.0
        return calculator.calculate_total_return(metrics_input.benchmark_curve)

    def _compute_excess_return(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        total_return = context.get('computed_total_return')
        if total_return is None:
            total_return = calculator.calculate_total_return(metrics_input.equity_curve)
            context['computed_total_return'] = total_return
        benchmark_return = self._compute_benchmark_return(metrics_input, calculator, rule_set, context)
        return total_return - benchmark_return

    def _compute_max_drawdown(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        return calculator.calculate_max_drawdown(metrics_input.equity_curve)

    def _compute_volatility(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        return calculator.calculate_volatility(context['daily_returns'])

    def _compute_downside_volatility(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        return calculator.calculate_downside_volatility(context['daily_returns'])

    def _compute_sharpe_ratio(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        return calculator.calculate_sharpe_ratio(context['daily_returns'])

    def _compute_sortino_ratio(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        annual_return = self._compute_annual_return(metrics_input, calculator, rule_set, context)
        return calculator.calculate_sortino_ratio(context['daily_returns'], annual_return)

    def _compute_calmar_ratio(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        annual_return = self._compute_annual_return(metrics_input, calculator, rule_set, context)
        max_drawdown = calculator.calculate_max_drawdown(metrics_input.equity_curve)
        return calculator.calculate_calmar_ratio(annual_return, max_drawdown)

    def _compute_information_ratio(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        benchmark_returns = context.get('benchmark_returns', np.array([]))
        if len(benchmark_returns) == 0:
            return 0.0
        return calculator.calculate_information_ratio(context['daily_returns'], benchmark_returns)

    def _compute_alpha(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        benchmark_returns = context.get('benchmark_returns', np.array([]))
        if len(benchmark_returns) == 0:
            return 0.0
        alpha, _ = calculator.calculate_alpha_beta(context['daily_returns'], benchmark_returns)
        return alpha

    def _compute_beta(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        benchmark_returns = context.get('benchmark_returns', np.array([]))
        if len(benchmark_returns) == 0:
            return 0.0
        _, beta = calculator.calculate_alpha_beta(context['daily_returns'], benchmark_returns)
        return beta

    def _compute_var_95(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        return calculator.calculate_var(context['daily_returns'], 0.95)

    def _compute_var_99(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        return calculator.calculate_var(context['daily_returns'], 0.99)

    def _compute_win_rate(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        profits, losses = context.get('trade_pnl', ([], []))
        return calculator.calculate_win_rate(profits, losses)

    def _compute_profit_loss_ratio(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        profits, losses = context.get('trade_pnl', ([], []))
        return calculator.calculate_profit_loss_ratio(profits, losses)

    def _compute_total_trades(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        profits, losses = context.get('trade_pnl', ([], []))
        return len(profits) + len(losses)

    def _compute_winning_trades(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        profits, _ = context.get('trade_pnl', ([], []))
        return len(profits)

    def _compute_losing_trades(self, metrics_input: MetricsInput, calculator: "PerformanceCalculator", rule_set: MetricRuleSet, context: Dict[str, Any]) -> float:
        _, losses = context.get('trade_pnl', ([], []))
        return len(losses)


class PerformanceCalculator:
    """
    绩效指标计算器
    
    提供各种绩效指标的计算方法
    """
    
    # 默认参数
    TRADING_DAYS_PER_YEAR = 252
    RISK_FREE_RATE = 0.02  # 2% 年化无风险利率
    
    def __init__(
        self,
        risk_free_rate: float = 0.02,
        trading_days: int = 252
    ):
        """
        初始化计算器
        
        Args:
            risk_free_rate: 年化无风险利率
            trading_days: 每年交易日数
        """
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days
        self.daily_risk_free = (1 + risk_free_rate) ** (1 / trading_days) - 1
    
    def calculate_total_return(
        self, 
        values: List[float]
    ) -> float:
        """
        计算总收益率
        
        Args:
            values: 净值序列
            
        Returns:
            总收益率
        """
        if not values or len(values) < 2:
            return 0.0
        
        if values[0] == 0:
            return 0.0
        
        return (values[-1] - values[0]) / values[0]
    
    def calculate_annual_return(
        self, 
        total_return: float, 
        days: int
    ) -> float:
        """
        计算年化收益率
        
        Args:
            total_return: 总收益率
            days: 投资天数
            
        Returns:
            年化收益率
        """
        if days <= 0:
            return 0.0
        
        if total_return <= -1:
            return -1.0
        
        return (1 + total_return) ** (365 / days) - 1
    
    def calculate_daily_returns(
        self, 
        values: List[float]
    ) -> np.ndarray:
        """
        计算日收益率序列
        
        Args:
            values: 净值序列
            
        Returns:
            日收益率数组
        """
        if not values or len(values) < 2:
            return np.array([])
        
        values_arr = np.array(values)
        returns = np.diff(values_arr) / values_arr[:-1]
        
        # 处理无穷大和NaN
        returns = np.nan_to_num(returns, nan=0.0, posinf=0.0, neginf=0.0)
        
        return returns
    
    def calculate_max_drawdown(
        self, 
        values: List[float]
    ) -> float:
        """
        计算最大回撤
        
        Args:
            values: 净值序列
            
        Returns:
            最大回撤（正数）
        """
        if not values or len(values) < 2:
            return 0.0
        
        peak = values[0]
        max_dd = 0.0
        
        for value in values:
            if value > peak:
                peak = value
            
            if peak > 0:
                drawdown = (peak - value) / peak
                if drawdown > max_dd:
                    max_dd = drawdown
        
        return max_dd
    
    def calculate_volatility(
        self, 
        daily_returns: np.ndarray
    ) -> float:
        """
        计算年化波动率
        
        Args:
            daily_returns: 日收益率数组
            
        Returns:
            年化波动率
        """
        if len(daily_returns) < 2:
            return 0.0
        
        return float(np.std(daily_returns) * np.sqrt(self.trading_days))
    
    def calculate_downside_volatility(
        self, 
        daily_returns: np.ndarray,
        target_return: float = 0.0
    ) -> float:
        """
        计算下行波动率
        
        Args:
            daily_returns: 日收益率数组
            target_return: 目标收益率（默认为0）
            
        Returns:
            年化下行波动率
        """
        if len(daily_returns) < 2:
            return 0.0
        
        # 只考虑低于目标收益的部分
        downside_returns = daily_returns[daily_returns < target_return]
        
        if len(downside_returns) < 2:
            return 0.0
        
        return float(np.std(downside_returns) * np.sqrt(self.trading_days))
    
    def calculate_sharpe_ratio(
        self, 
        daily_returns: np.ndarray
    ) -> float:
        """
        计算夏普比率
        
        Sharpe Ratio = (年化收益率 - 无风险利率) / 年化波动率
        
        Args:
            daily_returns: 日收益率数组
            
        Returns:
            夏普比率
        """
        if len(daily_returns) < 2:
            return 0.0
        
        excess_returns = daily_returns - self.daily_risk_free
        std = np.std(excess_returns)
        
        if std == 0:
            return 0.0
        
        return float(np.mean(excess_returns) / std * np.sqrt(self.trading_days))
    
    def calculate_sortino_ratio(
        self, 
        daily_returns: np.ndarray,
        annual_return: float
    ) -> float:
        """
        计算索提诺比率
        
        Sortino Ratio = (年化收益率 - 无风险利率) / 下行波动率
        
        Args:
            daily_returns: 日收益率数组
            annual_return: 年化收益率
            
        Returns:
            索提诺比率
        """
        downside_vol = self.calculate_downside_volatility(daily_returns)
        
        if downside_vol == 0:
            return 0.0
        
        return (annual_return - self.risk_free_rate) / downside_vol
    
    def calculate_calmar_ratio(
        self, 
        annual_return: float, 
        max_drawdown: float
    ) -> float:
        """
        计算卡玛比率
        
        Calmar Ratio = 年化收益率 / 最大回撤
        
        Args:
            annual_return: 年化收益率
            max_drawdown: 最大回撤
            
        Returns:
            卡玛比率
        """
        if max_drawdown == 0:
            return 0.0
        
        return annual_return / max_drawdown
    
    def calculate_information_ratio(
        self,
        strategy_returns: np.ndarray,
        benchmark_returns: np.ndarray
    ) -> float:
        """
        计算信息比率
        
        Information Ratio = 超额收益均值 / 跟踪误差
        
        Args:
            strategy_returns: 策略日收益率
            benchmark_returns: 基准日收益率
            
        Returns:
            信息比率
        """
        if len(strategy_returns) != len(benchmark_returns) or len(strategy_returns) < 2:
            return 0.0
        
        excess_returns = strategy_returns - benchmark_returns
        tracking_error = np.std(excess_returns) * np.sqrt(self.trading_days)
        
        if tracking_error == 0:
            return 0.0
        
        annual_excess = np.mean(excess_returns) * self.trading_days
        return float(annual_excess / tracking_error)
    
    def calculate_alpha_beta(
        self,
        strategy_returns: np.ndarray,
        benchmark_returns: np.ndarray
    ) -> Tuple[float, float]:
        """
        计算Alpha和Beta
        
        Args:
            strategy_returns: 策略日收益率
            benchmark_returns: 基准日收益率
            
        Returns:
            (Alpha, Beta)
        """
        if len(strategy_returns) != len(benchmark_returns) or len(strategy_returns) < 2:
            return 0.0, 0.0
        
        # 计算协方差矩阵
        cov_matrix = np.cov(strategy_returns, benchmark_returns)
        
        # Beta = Cov(策略, 基准) / Var(基准)
        benchmark_var = cov_matrix[1, 1]
        if benchmark_var == 0:
            return 0.0, 0.0
        
        beta = cov_matrix[0, 1] / benchmark_var
        
        # 计算年化收益率
        strategy_annual = (1 + np.mean(strategy_returns)) ** self.trading_days - 1
        benchmark_annual = (1 + np.mean(benchmark_returns)) ** self.trading_days - 1
        
        # Alpha = 策略年化收益 - 无风险利率 - Beta * (基准年化收益 - 无风险利率)
        alpha = (strategy_annual - self.risk_free_rate) - beta * (benchmark_annual - self.risk_free_rate)
        
        return float(alpha), float(beta)
    
    def calculate_var(
        self,
        daily_returns: np.ndarray,
        confidence_level: float = 0.95
    ) -> float:
        """
        计算VaR (Value at Risk)
        
        Args:
            daily_returns: 日收益率数组
            confidence_level: 置信水平
            
        Returns:
            VaR值（正数表示损失）
        """
        if len(daily_returns) < 2:
            return 0.0
        
        percentile = (1 - confidence_level) * 100
        var = -np.percentile(daily_returns, percentile)
        
        return float(var)
    
    def calculate_win_rate(
        self,
        profits: List[float],
        losses: List[float]
    ) -> float:
        """
        计算胜率
        
        Args:
            profits: 盈利交易列表
            losses: 亏损交易列表
            
        Returns:
            胜率
        """
        total = len(profits) + len(losses)
        if total == 0:
            return 0.0
        
        return len(profits) / total
    
    def calculate_profit_loss_ratio(
        self,
        profits: List[float],
        losses: List[float]
    ) -> float:
        """
        计算盈亏比
        
        Args:
            profits: 盈利交易列表
            losses: 亏损交易列表
            
        Returns:
            盈亏比
        """
        total_profit = sum(profits) if profits else 0
        total_loss = sum(losses) if losses else 0
        
        if total_loss == 0:
            return float('inf') if total_profit > 0 else 0.0
        
        return total_profit / total_loss
    
    def calculate_all_metrics(
        self,
        equity_curve: List[float],
        benchmark_curve: Optional[List[float]] = None,
        trades: Optional[List[Dict]] = None
    ) -> PerformanceMetrics:
        """
        计算所有绩效指标
        
        Args:
            equity_curve: 策略净值曲线
            benchmark_curve: 基准净值曲线（可选）
            trades: 交易记录列表（可选）
            
        Returns:
            绩效指标对象
        """
        metrics = PerformanceMetrics()
        if not equity_curve or len(equity_curve) < 2:
            return metrics

        metrics_input = MetricsInput(
            equity_curve=equity_curve,
            benchmark_curve=benchmark_curve,
            trades=trades,
            risk_free_rate=self.risk_free_rate,
            trading_days=self.trading_days,
            metadata={'source': 'performance_metrics'}
        )

        rule_set = MetricRuleSet(
            risk_free_rate=self.risk_free_rate,
            trading_days=self.trading_days
        )

        engine = MetricEngine(rule_set=rule_set)
        report = engine.compute(metrics_input)
        flat = report.summary.to_flat_dict()

        metrics.total_return = flat.get('total_return', 0.0)
        metrics.annual_return = flat.get('annual_return', 0.0)
        metrics.benchmark_return = flat.get('benchmark_return', 0.0)
        metrics.excess_return = flat.get('excess_return', 0.0)
        metrics.max_drawdown = flat.get('max_drawdown', 0.0)
        metrics.volatility = flat.get('volatility', 0.0)
        metrics.downside_volatility = flat.get('downside_volatility', 0.0)
        metrics.sharpe_ratio = flat.get('sharpe_ratio', 0.0)
        metrics.sortino_ratio = flat.get('sortino_ratio', 0.0)
        metrics.calmar_ratio = flat.get('calmar_ratio', 0.0)
        metrics.information_ratio = flat.get('information_ratio', 0.0)
        metrics.alpha = flat.get('alpha', 0.0)
        metrics.beta = flat.get('beta', 0.0)
        metrics.var_95 = flat.get('var_95', 0.0)
        metrics.var_99 = flat.get('var_99', 0.0)
        metrics.win_rate = flat.get('win_rate', 0.0)
        metrics.profit_loss_ratio = flat.get('profit_loss_ratio', 0.0)
        metrics.total_trades = int(flat.get('total_trades', 0))
        metrics.winning_trades = int(flat.get('winning_trades', 0))
        metrics.losing_trades = int(flat.get('losing_trades', 0))

        return metrics
    
    def _extract_trade_pnl(
        self, 
        trades: List[Dict]
    ) -> Tuple[List[float], List[float]]:
        """
        从交易记录中提取盈亏
        
        Args:
            trades: 交易记录列表
            
        Returns:
            (盈利列表, 亏损列表)
        """
        profits = []
        losses = []
        
        # 按基金分组
        fund_trades: Dict[str, List[Dict]] = {}
        for trade in trades:
            fund_code = trade.get('fund_code', '')
            if fund_code not in fund_trades:
                fund_trades[fund_code] = []
            fund_trades[fund_code].append(trade)
        
        # 计算每只基金的盈亏
        for fund_code, fund_trade_list in fund_trades.items():
            buy_cost = 0.0
            buy_shares = 0.0
            
            for trade in fund_trade_list:
                action = trade.get('action', '')
                amount = trade.get('amount', 0)
                shares = trade.get('shares', 0)
                price = trade.get('price', 0)
                
                if action == 'buy':
                    buy_cost += amount
                    buy_shares += shares
                elif action in ['sell', 'stop_loss', 'take_profit', 
                               'daily_stop_loss', 'daily_take_profit',
                               'total_stop_loss', 'trailing_stop']:
                    if buy_shares > 0:
                        avg_cost = buy_cost / buy_shares
                        pnl = (price - avg_cost) * shares
                        if pnl > 0:
                            profits.append(pnl)
                        elif pnl < 0:
                            losses.append(abs(pnl))
        
        return profits, losses


# 便捷函数
def calculate_performance_metrics(
    equity_curve: List[float],
    benchmark_curve: Optional[List[float]] = None,
    trades: Optional[List[Dict]] = None,
    risk_free_rate: float = 0.02
) -> PerformanceMetrics:
    """
    计算绩效指标的便捷函数
    
    Args:
        equity_curve: 策略净值曲线
        benchmark_curve: 基准净值曲线
        trades: 交易记录
        risk_free_rate: 无风险利率
        
    Returns:
        绩效指标对象
    """
    calculator = PerformanceCalculator(risk_free_rate=risk_free_rate)
    return calculator.calculate_all_metrics(equity_curve, benchmark_curve, trades)


def calculate_metrics_report(
    equity_curve: List[float],
    benchmark_curve: Optional[List[float]] = None,
    trades: Optional[List[Dict]] = None,
    risk_free_rate: float = 0.02,
    trading_days: int = 252,
    metadata: Optional[Dict[str, Any]] = None,
    dimensions: Optional[Dict[str, MetricsInput]] = None,
    rule_set: Optional[MetricRuleSet] = None
) -> MetricReport:
    """生成标准化指标报告（支持多维度与规则配置）"""
    metrics_input = MetricsInput(
        equity_curve=equity_curve,
        benchmark_curve=benchmark_curve,
        trades=trades,
        risk_free_rate=risk_free_rate,
        trading_days=trading_days,
        metadata=metadata,
        dimensions=dimensions
    )
    engine = MetricEngine(rule_set=rule_set)
    return engine.compute(metrics_input)
