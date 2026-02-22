#!/usr/bin/env python
# coding: utf-8

"""
Enhanced Risk Metrics Calculator

This module implements advanced risk metrics calculations including VaR, CVaR,
tracking error, information ratio, and various drawdown measures.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """Data class for storing risk metrics results"""
    calculation_date: pd.Timestamp
    portfolio_id: str
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    tracking_error: float
    information_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    ulcer_index: float
    downside_deviation: float
    upside_capture_ratio: float
    beta: float
    alpha: float


class EnhancedRiskMetrics:
    """Enhanced risk metrics calculator with multiple VaR methods and advanced indicators"""

    def __init__(
        self, 
        confidence_levels: List[float] = None,
        risk_free_rate: float = 0.03,
        trading_days_per_year: int = 252
    ):
        """
        Initialize the risk metrics calculator

        Args:
            confidence_levels: List of confidence levels for VaR calculations
            risk_free_rate: Annual risk-free rate
            trading_days_per_year: Number of trading days per year
        """
        self.confidence_levels = confidence_levels or [0.95, 0.99]
        self.risk_free_rate = risk_free_rate
        self.trading_days_per_year = trading_days_per_year
        self.methods = ["historical", "parametric", "monte_carlo"]

    def calculate_var(
        self, 
        returns: pd.Series, 
        method: str = "historical", 
        confidence: float = 0.95
    ) -> float:
        """
        Calculate Value at Risk using specified method

        Args:
            returns: Series of portfolio returns
            method: Calculation method ('historical', 'parametric', 'monte_carlo')
            confidence: Confidence level (e.g., 0.95 for 95% VaR)

        Returns:
            VaR value (positive number representing potential loss)
        """
        if returns is None or len(returns) < 2:
            logger.warning("Insufficient data for VaR calculation")
            return 0.0
        
        returns = pd.Series(returns).dropna()
        
        if method == "historical":
            return self._var_historical(returns, confidence)
        elif method == "parametric":
            return self._var_parametric(returns, confidence)
        elif method == "monte_carlo":
            return self._var_monte_carlo(returns, confidence)
        else:
            logger.warning(f"Unknown VaR method: {method}, using historical")
            return self._var_historical(returns, confidence)
    
    def _var_historical(self, returns: pd.Series, confidence: float) -> float:
        """
        Calculate VaR using historical simulation method
        
        Args:
            returns: Series of portfolio returns
            confidence: Confidence level
            
        Returns:
            VaR value (positive number)
        """
        # VaR is the (1-confidence) percentile of returns
        # For 95% confidence, we want the 5th percentile
        percentile = (1 - confidence) * 100
        var = -np.percentile(returns, percentile)
        return max(0, var)
    
    def _var_parametric(self, returns: pd.Series, confidence: float) -> float:
        """
        Calculate VaR using parametric (variance-covariance) method
        Assumes returns are normally distributed
        
        Args:
            returns: Series of portfolio returns
            confidence: Confidence level
            
        Returns:
            VaR value (positive number)
        """
        mean = returns.mean()
        std = returns.std()
        
        # Get z-score for the confidence level
        z_score = stats.norm.ppf(1 - confidence)
        
        # VaR = -(mean + z_score * std)
        var = -(mean + z_score * std)
        return max(0, var)
    
    def _var_monte_carlo(
        self, 
        returns: pd.Series, 
        confidence: float,
        num_simulations: int = 10000
    ) -> float:
        """
        Calculate VaR using Monte Carlo simulation
        
        Args:
            returns: Series of portfolio returns
            confidence: Confidence level
            num_simulations: Number of Monte Carlo simulations
            
        Returns:
            VaR value (positive number)
        """
        mean = returns.mean()
        std = returns.std()
        
        # Generate random returns from normal distribution
        simulated_returns = np.random.normal(mean, std, num_simulations)
        
        # Calculate VaR from simulated returns
        percentile = (1 - confidence) * 100
        var = -np.percentile(simulated_returns, percentile)
        return max(0, var)

    def calculate_cvar(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """
        Calculate Conditional Value at Risk (Expected Shortfall)
        CVaR is the expected loss given that the loss exceeds VaR

        Args:
            returns: Series of portfolio returns
            confidence: Confidence level

        Returns:
            CVaR value (expected loss beyond VaR threshold)
        """
        if returns is None or len(returns) < 2:
            logger.warning("Insufficient data for CVaR calculation")
            return 0.0
        
        returns = pd.Series(returns).dropna()
        
        # Calculate VaR threshold
        var = self.calculate_var(returns, "historical", confidence)
        
        # CVaR is the average of all losses worse than VaR
        # (returns that are more negative than -VaR)
        tail_returns = returns[returns <= -var]
        
        if len(tail_returns) == 0:
            return var
        
        cvar = -tail_returns.mean()
        return max(0, cvar)

    def calculate_tracking_error(
        self, 
        portfolio_returns: pd.Series, 
        benchmark_returns: pd.Series
    ) -> float:
        """
        Calculate tracking error (standard deviation of excess returns)

        Args:
            portfolio_returns: Portfolio return series
            benchmark_returns: Benchmark return series

        Returns:
            Tracking error (annualized)
        """
        if portfolio_returns is None or benchmark_returns is None:
            logger.warning("Insufficient data for tracking error calculation")
            return 0.0
        
        portfolio_returns = pd.Series(portfolio_returns).dropna()
        benchmark_returns = pd.Series(benchmark_returns).dropna()
        
        # Align the series
        min_len = min(len(portfolio_returns), len(benchmark_returns))
        portfolio_returns = portfolio_returns.iloc[:min_len]
        benchmark_returns = benchmark_returns.iloc[:min_len]
        
        # Calculate excess returns
        excess_returns = portfolio_returns.values - benchmark_returns.values
        
        # Tracking error is the standard deviation of excess returns
        daily_te = np.std(excess_returns, ddof=1)
        
        # Annualize
        annual_te = daily_te * np.sqrt(self.trading_days_per_year)
        
        return float(annual_te)

    def calculate_information_ratio(
        self, 
        portfolio_returns: pd.Series, 
        benchmark_returns: pd.Series
    ) -> float:
        """
        Calculate information ratio (excess return / tracking error)

        Args:
            portfolio_returns: Portfolio return series
            benchmark_returns: Benchmark return series

        Returns:
            Information ratio
        """
        tracking_error = self.calculate_tracking_error(portfolio_returns, benchmark_returns)
        
        if tracking_error == 0:
            return 0.0
        
        portfolio_returns = pd.Series(portfolio_returns).dropna()
        benchmark_returns = pd.Series(benchmark_returns).dropna()
        
        # Align the series
        min_len = min(len(portfolio_returns), len(benchmark_returns))
        portfolio_returns = portfolio_returns.iloc[:min_len]
        benchmark_returns = benchmark_returns.iloc[:min_len]
        
        # Calculate annualized excess return
        excess_returns = portfolio_returns.values - benchmark_returns.values
        annual_excess_return = np.mean(excess_returns) * self.trading_days_per_year
        
        # Information ratio = annualized excess return / tracking error
        ir = annual_excess_return / tracking_error
        
        return float(ir)

    def calculate_max_drawdown(self, returns: pd.Series) -> float:
        """
        Calculate maximum drawdown
        
        Args:
            returns: Series of portfolio returns
            
        Returns:
            Maximum drawdown (positive number)
        """
        if returns is None or len(returns) < 2:
            return 0.0
        
        returns = pd.Series(returns).dropna()
        
        # Calculate cumulative returns
        cumulative = (1 + returns).cumprod()
        
        # Calculate running maximum
        running_max = cumulative.cummax()
        
        # Calculate drawdown
        drawdown = (cumulative - running_max) / running_max
        
        # Maximum drawdown
        max_dd = -drawdown.min()
        
        return float(max_dd)

    def calculate_max_drawdown_duration(self, returns: pd.Series) -> int:
        """
        Calculate maximum drawdown duration in periods

        Args:
            returns: Series of portfolio returns

        Returns:
            Maximum drawdown duration in periods
        """
        if returns is None or len(returns) < 2:
            return 0
        
        returns = pd.Series(returns).dropna()
        
        # Calculate cumulative returns
        cumulative = (1 + returns).cumprod()
        
        # Calculate running maximum
        running_max = cumulative.cummax()
        
        # Find periods where we're in drawdown
        in_drawdown = cumulative < running_max
        
        # Calculate duration of each drawdown period
        max_duration = 0
        current_duration = 0
        
        for is_dd in in_drawdown:
            if is_dd:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0
        
        return max_duration

    def calculate_ulcer_index(self, returns: pd.Series) -> float:
        """
        Calculate Ulcer Index (measure of downside risk)
        Ulcer Index = sqrt(mean of squared drawdowns)

        Args:
            returns: Series of portfolio returns

        Returns:
            Ulcer Index value
        """
        if returns is None or len(returns) < 2:
            return 0.0
        
        returns = pd.Series(returns).dropna()
        
        # Calculate cumulative returns
        cumulative = (1 + returns).cumprod()
        
        # Calculate running maximum
        running_max = cumulative.cummax()
        
        # Calculate percentage drawdown
        drawdown_pct = ((cumulative - running_max) / running_max) * 100
        
        # Ulcer Index = sqrt(mean of squared drawdowns)
        ulcer_index = np.sqrt(np.mean(drawdown_pct ** 2))
        
        return float(ulcer_index)

    def calculate_downside_deviation(
        self, 
        returns: pd.Series, 
        target_return: float = 0
    ) -> float:
        """
        Calculate downside deviation (volatility of negative returns)

        Args:
            returns: Series of portfolio returns
            target_return: Target return threshold

        Returns:
            Downside deviation (annualized)
        """
        if returns is None or len(returns) < 2:
            return 0.0
        
        returns = pd.Series(returns).dropna()
        
        # Calculate returns below target
        downside_returns = returns[returns < target_return] - target_return
        
        if len(downside_returns) == 0:
            return 0.0
        
        # Calculate downside deviation
        daily_dd = np.sqrt(np.mean(downside_returns ** 2))
        
        # Annualize
        annual_dd = daily_dd * np.sqrt(self.trading_days_per_year)
        
        return float(annual_dd)

    def calculate_upside_capture_ratio(
        self, 
        portfolio_returns: pd.Series, 
        benchmark_returns: pd.Series
    ) -> float:
        """
        Calculate upside capture ratio
        Measures how well the portfolio captures benchmark gains

        Args:
            portfolio_returns: Portfolio return series
            benchmark_returns: Benchmark return series

        Returns:
            Upside capture ratio
        """
        if portfolio_returns is None or benchmark_returns is None:
            return 0.0
        
        portfolio_returns = pd.Series(portfolio_returns).dropna()
        benchmark_returns = pd.Series(benchmark_returns).dropna()
        
        # Align the series
        min_len = min(len(portfolio_returns), len(benchmark_returns))
        portfolio_returns = portfolio_returns.iloc[:min_len]
        benchmark_returns = benchmark_returns.iloc[:min_len]
        
        # Find periods where benchmark is positive
        up_periods = benchmark_returns > 0
        
        if up_periods.sum() == 0:
            return 0.0
        
        # Calculate average returns during up periods
        portfolio_up = portfolio_returns[up_periods].mean()
        benchmark_up = benchmark_returns[up_periods].mean()
        
        if benchmark_up == 0:
            return 0.0
        
        # Upside capture ratio
        ucr = portfolio_up / benchmark_up
        
        return float(ucr)
    
    def calculate_downside_capture_ratio(
        self, 
        portfolio_returns: pd.Series, 
        benchmark_returns: pd.Series
    ) -> float:
        """
        Calculate downside capture ratio
        Measures how much of benchmark losses the portfolio captures
        
        Args:
            portfolio_returns: Portfolio return series
            benchmark_returns: Benchmark return series
            
        Returns:
            Downside capture ratio (lower is better)
        """
        if portfolio_returns is None or benchmark_returns is None:
            return 0.0
        
        portfolio_returns = pd.Series(portfolio_returns).dropna()
        benchmark_returns = pd.Series(benchmark_returns).dropna()
        
        # Align the series
        min_len = min(len(portfolio_returns), len(benchmark_returns))
        portfolio_returns = portfolio_returns.iloc[:min_len]
        benchmark_returns = benchmark_returns.iloc[:min_len]
        
        # Find periods where benchmark is negative
        down_periods = benchmark_returns < 0
        
        if down_periods.sum() == 0:
            return 0.0
        
        # Calculate average returns during down periods
        portfolio_down = portfolio_returns[down_periods].mean()
        benchmark_down = benchmark_returns[down_periods].mean()
        
        if benchmark_down == 0:
            return 0.0
        
        # Downside capture ratio
        dcr = portfolio_down / benchmark_down
        
        return float(dcr)
    
    def calculate_beta(
        self, 
        portfolio_returns: pd.Series, 
        benchmark_returns: pd.Series
    ) -> float:
        """
        Calculate portfolio beta
        
        Args:
            portfolio_returns: Portfolio return series
            benchmark_returns: Benchmark return series
            
        Returns:
            Beta value
        """
        if portfolio_returns is None or benchmark_returns is None:
            return 0.0
        
        portfolio_returns = pd.Series(portfolio_returns).dropna()
        benchmark_returns = pd.Series(benchmark_returns).dropna()
        
        # Align the series
        min_len = min(len(portfolio_returns), len(benchmark_returns))
        portfolio_returns = portfolio_returns.iloc[:min_len].values
        benchmark_returns = benchmark_returns.iloc[:min_len].values
        
        # Calculate covariance and variance
        cov_matrix = np.cov(portfolio_returns, benchmark_returns)
        
        if cov_matrix[1, 1] == 0:
            return 0.0
        
        beta = cov_matrix[0, 1] / cov_matrix[1, 1]
        
        return float(beta)
    
    def calculate_alpha(
        self, 
        portfolio_returns: pd.Series, 
        benchmark_returns: pd.Series
    ) -> float:
        """
        Calculate Jensen's alpha (annualized)
        
        Args:
            portfolio_returns: Portfolio return series
            benchmark_returns: Benchmark return series
            
        Returns:
            Alpha value (annualized)
        """
        if portfolio_returns is None or benchmark_returns is None:
            return 0.0
        
        portfolio_returns = pd.Series(portfolio_returns).dropna()
        benchmark_returns = pd.Series(benchmark_returns).dropna()
        
        # Calculate beta
        beta = self.calculate_beta(portfolio_returns, benchmark_returns)
        
        # Calculate annualized returns
        portfolio_annual = portfolio_returns.mean() * self.trading_days_per_year
        benchmark_annual = benchmark_returns.mean() * self.trading_days_per_year
        
        # Jensen's alpha = portfolio return - (risk-free rate + beta * (benchmark return - risk-free rate))
        alpha = portfolio_annual - (self.risk_free_rate + beta * (benchmark_annual - self.risk_free_rate))
        
        return float(alpha)
    
    def calculate_all_metrics(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series = None,
        portfolio_id: str = "default"
    ) -> RiskMetrics:
        """
        Calculate all risk metrics
        
        Args:
            portfolio_returns: Portfolio return series
            benchmark_returns: Benchmark return series (optional)
            portfolio_id: Portfolio identifier
            
        Returns:
            RiskMetrics dataclass with all calculated metrics
        """
        portfolio_returns = pd.Series(portfolio_returns).dropna()
        
        # VaR and CVaR
        var_95 = self.calculate_var(portfolio_returns, "historical", 0.95)
        var_99 = self.calculate_var(portfolio_returns, "historical", 0.99)
        cvar_95 = self.calculate_cvar(portfolio_returns, 0.95)
        cvar_99 = self.calculate_cvar(portfolio_returns, 0.99)
        
        # Drawdown metrics
        max_drawdown = self.calculate_max_drawdown(portfolio_returns)
        max_drawdown_duration = self.calculate_max_drawdown_duration(portfolio_returns)
        ulcer_index = self.calculate_ulcer_index(portfolio_returns)
        downside_deviation = self.calculate_downside_deviation(portfolio_returns)
        
        # Benchmark-relative metrics
        if benchmark_returns is not None:
            benchmark_returns = pd.Series(benchmark_returns).dropna()
            tracking_error = self.calculate_tracking_error(portfolio_returns, benchmark_returns)
            information_ratio = self.calculate_information_ratio(portfolio_returns, benchmark_returns)
            upside_capture_ratio = self.calculate_upside_capture_ratio(portfolio_returns, benchmark_returns)
            beta = self.calculate_beta(portfolio_returns, benchmark_returns)
            alpha = self.calculate_alpha(portfolio_returns, benchmark_returns)
        else:
            tracking_error = 0.0
            information_ratio = 0.0
            upside_capture_ratio = 0.0
            beta = 0.0
            alpha = 0.0
        
        return RiskMetrics(
            calculation_date=pd.Timestamp.now(),
            portfolio_id=portfolio_id,
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            tracking_error=tracking_error,
            information_ratio=information_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            ulcer_index=ulcer_index,
            downside_deviation=downside_deviation,
            upside_capture_ratio=upside_capture_ratio,
            beta=beta,
            alpha=alpha
        )


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    calculator = EnhancedRiskMetrics()
    
    # 生成模拟收益率数据
    np.random.seed(42)
    portfolio_returns = pd.Series(np.random.normal(0.001, 0.02, 252))
    benchmark_returns = pd.Series(np.random.normal(0.0008, 0.015, 252))
    
    print("=== VaR 计算测试 ===")
    for method in ["historical", "parametric", "monte_carlo"]:
        var_95 = calculator.calculate_var(portfolio_returns, method, 0.95)
        var_99 = calculator.calculate_var(portfolio_returns, method, 0.99)
        print(f"{method}: VaR(95%)={var_95:.4f}, VaR(99%)={var_99:.4f}")
    
    print("\n=== CVaR 计算测试 ===")
    cvar_95 = calculator.calculate_cvar(portfolio_returns, 0.95)
    cvar_99 = calculator.calculate_cvar(portfolio_returns, 0.99)
    print(f"CVaR(95%)={cvar_95:.4f}, CVaR(99%)={cvar_99:.4f}")
    
    print("\n=== 跟踪误差和信息比率 ===")
    te = calculator.calculate_tracking_error(portfolio_returns, benchmark_returns)
    ir = calculator.calculate_information_ratio(portfolio_returns, benchmark_returns)
    print(f"跟踪误差: {te:.4f}")
    print(f"信息比率: {ir:.4f}")
    
    print("\n=== 回撤指标 ===")
    max_dd = calculator.calculate_max_drawdown(portfolio_returns)
    max_dd_duration = calculator.calculate_max_drawdown_duration(portfolio_returns)
    ulcer = calculator.calculate_ulcer_index(portfolio_returns)
    print(f"最大回撤: {max_dd:.4f}")
    print(f"最大回撤持续期: {max_dd_duration} 天")
    print(f"Ulcer Index: {ulcer:.4f}")
    
    print("\n=== 下行风险指标 ===")
    dd = calculator.calculate_downside_deviation(portfolio_returns)
    print(f"下行偏差: {dd:.4f}")
    
    print("\n=== 捕获比率 ===")
    ucr = calculator.calculate_upside_capture_ratio(portfolio_returns, benchmark_returns)
    dcr = calculator.calculate_downside_capture_ratio(portfolio_returns, benchmark_returns)
    print(f"上行捕获比率: {ucr:.4f}")
    print(f"下行捕获比率: {dcr:.4f}")
    
    print("\n=== Alpha 和 Beta ===")
    beta = calculator.calculate_beta(portfolio_returns, benchmark_returns)
    alpha = calculator.calculate_alpha(portfolio_returns, benchmark_returns)
    print(f"Beta: {beta:.4f}")
    print(f"Alpha: {alpha:.4f}")
    
    print("\n=== 完整风险指标 ===")
    metrics = calculator.calculate_all_metrics(portfolio_returns, benchmark_returns, "test_portfolio")
    print(f"VaR(95%): {metrics.var_95:.4f}")
    print(f"CVaR(95%): {metrics.cvar_95:.4f}")
    print(f"最大回撤: {metrics.max_drawdown:.4f}")
    print(f"信息比率: {metrics.information_ratio:.4f}")
