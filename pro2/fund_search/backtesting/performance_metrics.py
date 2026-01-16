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
from typing import List, Dict, Any, Optional, Tuple
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
        
        # 计算日收益率
        daily_returns = self.calculate_daily_returns(equity_curve)
        
        # 收益指标
        metrics.total_return = self.calculate_total_return(equity_curve)
        days = len(equity_curve)
        metrics.annual_return = self.calculate_annual_return(metrics.total_return, days)
        
        # 基准收益
        if benchmark_curve and len(benchmark_curve) >= 2:
            benchmark_returns = self.calculate_daily_returns(benchmark_curve)
            metrics.benchmark_return = self.calculate_total_return(benchmark_curve)
            metrics.excess_return = metrics.total_return - metrics.benchmark_return
            
            # 信息比率
            if len(daily_returns) == len(benchmark_returns):
                metrics.information_ratio = self.calculate_information_ratio(
                    daily_returns, benchmark_returns
                )
                metrics.alpha, metrics.beta = self.calculate_alpha_beta(
                    daily_returns, benchmark_returns
                )
        
        # 风险指标
        metrics.max_drawdown = self.calculate_max_drawdown(equity_curve)
        metrics.volatility = self.calculate_volatility(daily_returns)
        metrics.downside_volatility = self.calculate_downside_volatility(daily_returns)
        
        # 风险调整收益指标
        metrics.sharpe_ratio = self.calculate_sharpe_ratio(daily_returns)
        metrics.sortino_ratio = self.calculate_sortino_ratio(daily_returns, metrics.annual_return)
        metrics.calmar_ratio = self.calculate_calmar_ratio(metrics.annual_return, metrics.max_drawdown)
        
        # VaR
        metrics.var_95 = self.calculate_var(daily_returns, 0.95)
        metrics.var_99 = self.calculate_var(daily_returns, 0.99)
        
        # 交易统计
        if trades:
            profits, losses = self._extract_trade_pnl(trades)
            metrics.winning_trades = len(profits)
            metrics.losing_trades = len(losses)
            metrics.total_trades = len(profits) + len(losses)
            metrics.win_rate = self.calculate_win_rate(profits, losses)
            metrics.profit_loss_ratio = self.calculate_profit_loss_ratio(profits, losses)
        
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
