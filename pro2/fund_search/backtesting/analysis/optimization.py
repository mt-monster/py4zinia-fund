"""
Portfolio Optimization Engine

This module implements various portfolio optimization algorithms including
mean-variance, Black-Litterman, risk parity, and constrained optimization.
"""

import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import cvxpy as cp
import numpy as np
import pandas as pd
from scipy.optimize import minimize

# 添加 tushare 支持
try:
    import tushare as ts
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from shared.enhanced_config import DATA_SOURCE_CONFIG
    ts.set_token(DATA_SOURCE_CONFIG.get('tushare', {}).get('token', ''))
    tushare_pro = ts.pro_api() if DATA_SOURCE_CONFIG.get('tushare', {}).get('token') else None
except:
    tushare_pro = None


def fetch_nav_from_tushare_realtime(fund_code, start_date, end_date):
    """从 tushare 实时获取基金净值数据"""
    if not tushare_pro:
        return pd.DataFrame()
    
    try:
        ts_code = f"{fund_code}.OF"
        df = tushare_pro.fund_nav(ts_code=ts_code, start_date=start_date.replace('-', ''), end_date=end_date.replace('-', ''))
        
        if df is not None and not df.empty:
            df = df.rename(columns={
                'nav_date': 'nav_date',
                'unit_nav': 'nav',
                'accum_nav': 'accum_nav',
                'daily_profit': 'daily_return'
            })
            df['nav_date'] = pd.to_datetime(df['nav_date'])
            df = df.sort_values('nav_date')
            return df[['nav', 'nav_date']]
    except Exception as e:
        pass
    
    return pd.DataFrame()


@dataclass
class OptimizationResult:
    """Data class for storing optimization results"""

    optimal_weights: pd.Series
    expected_return: float
    expected_risk: float
    sharpe_ratio: float
    optimization_method: str
    constraints_satisfied: bool
    optimization_status: str


class PortfolioOptimizer:
    """Portfolio optimization engine with multiple algorithms"""

    def __init__(self):
        """Initialize the portfolio optimizer"""
        self.optimization_methods = [
            "mean_variance",
            "black_litterman",
            "risk_parity",
            "minimum_variance",
            "maximum_diversification",
        ]

    def mean_variance_optimization(
        self,
        expected_returns: pd.Series,
        covariance_matrix: pd.DataFrame,
        risk_aversion: float = 1.0,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> OptimizationResult:
        """
        Perform mean-variance optimization

        Args:
            expected_returns: Expected returns for each asset
            covariance_matrix: Covariance matrix of asset returns
            risk_aversion: Risk aversion parameter
            constraints: Dictionary of optimization constraints

        Returns:
            OptimizationResult with optimal portfolio weights
        """
        # Placeholder implementation - will be implemented in subsequent tasks
        pass

    def black_litterman_optimization(
        self,
        market_caps: pd.Series,
        expected_returns: pd.Series,
        covariance_matrix: pd.DataFrame,
        views: pd.DataFrame,
        view_confidence: pd.DataFrame,
    ) -> OptimizationResult:
        """
        Perform Black-Litterman optimization

        Args:
            market_caps: Market capitalizations for equilibrium returns
            expected_returns: Prior expected returns
            covariance_matrix: Covariance matrix of returns
            views: Investor views on expected returns
            view_confidence: Confidence matrix for views

        Returns:
            OptimizationResult with Black-Litterman optimal weights
        """
        # Placeholder implementation - will be implemented in subsequent tasks
        pass

    def risk_parity_optimization(
        self,
        covariance_matrix: pd.DataFrame,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> OptimizationResult:
        """
        Perform risk parity optimization

        Args:
            covariance_matrix: Covariance matrix of asset returns
            constraints: Dictionary of optimization constraints

        Returns:
            OptimizationResult with risk parity weights
        """
        n_assets = len(covariance_matrix)
        asset_names = covariance_matrix.index.tolist()

        # 使用优化求解风险平价权重
        # 目标：各资产对组合风险的贡献相等
        def risk_parity_objective(weights, cov_matrix):
            """计算风险平价目标函数"""
            weights = np.array(weights)
            portfolio_vol = np.sqrt(weights @ cov_matrix.values @ weights)
            # 各资产的风险贡献
            risk_contrib = weights * (cov_matrix.values @ weights) / portfolio_vol
            target_risk = portfolio_vol / n_assets
            # 最小化各资产风险贡献与目标风险的偏离
            return np.sum((risk_contrib - target_risk) ** 2)

        # 约束条件
        constraints_list = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]  # 权重和为1
        bounds = [(0.01, 1.0) for _ in range(n_assets)]  # 每个资产至少1%

        # 初始权重（等权重）
        x0 = np.ones(n_assets) / n_assets

        # 优化
        from scipy.optimize import minimize
        result = minimize(
            risk_parity_objective,
            x0,
            args=(covariance_matrix,),
            method='SLSQP',
            bounds=bounds,
            constraints=constraints_list,
            options={'maxiter': 1000, 'ftol': 1e-9}
        )

        if result.success:
            optimal_weights = pd.Series(result.x, index=asset_names)
            # 计算组合预期收益和风险
            expected_return = 0  # 风险平价不直接给出预期收益
            expected_risk = np.sqrt(result.x @ covariance_matrix.values @ result.x)
            sharpe_ratio = 0  # 需要外部提供无风险利率计算

            return OptimizationResult(
                optimal_weights=optimal_weights,
                expected_return=expected_return,
                expected_risk=expected_risk,
                sharpe_ratio=sharpe_ratio,
                optimization_method='risk_parity',
                constraints_satisfied=True,
                optimization_status='optimal'
            )
        else:
            # 如果优化失败，返回等权重
            return OptimizationResult(
                optimal_weights=pd.Series(1.0/n_assets, index=asset_names),
                expected_return=0,
                expected_risk=np.sqrt(np.ones(n_assets)/n_assets @ covariance_matrix.values @ np.ones(n_assets)/n_assets),
                sharpe_ratio=0,
                optimization_method='risk_parity',
                constraints_satisfied=False,
                optimization_status='fallback_to_equal_weight'
            )

    def equal_weight_optimization(
        self,
        covariance_matrix: pd.DataFrame,
        expected_returns: Optional[pd.Series] = None,
    ) -> OptimizationResult:
        """
        Perform equal weight optimization

        Args:
            covariance_matrix: Covariance matrix of asset returns
            expected_returns: Expected returns for each asset (optional)

        Returns:
            OptimizationResult with equal weight portfolio
        """
        n_assets = len(covariance_matrix)
        asset_names = covariance_matrix.index.tolist()

        # 等权重
        weights = np.ones(n_assets) / n_assets
        optimal_weights = pd.Series(weights, index=asset_names)

        # 计算预期风险
        expected_risk = np.sqrt(weights @ covariance_matrix.values @ weights)

        # 如果提供了预期收益率，计算组合收益
        expected_return = 0
        if expected_returns is not None:
            expected_return = weights @ expected_returns.values
            # 计算夏普比率（假设无风险利率为2%）
            risk_free_rate = 0.02
            if expected_risk > 0:
                sharpe_ratio = (expected_return - risk_free_rate) / expected_risk
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0

        return OptimizationResult(
            optimal_weights=optimal_weights,
            expected_return=expected_return,
            expected_risk=expected_risk,
            sharpe_ratio=sharpe_ratio,
            optimization_method='equal_weight',
            constraints_satisfied=True,
            optimization_status='optimal'
        )

    def maximum_sharpe_optimization(
        self,
        expected_returns: pd.Series,
        covariance_matrix: pd.DataFrame,
        risk_free_rate: float = 0.02,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> OptimizationResult:
        """
        Perform maximum Sharpe ratio optimization

        Args:
            expected_returns: Expected returns for each asset
            covariance_matrix: Covariance matrix of asset returns
            risk_free_rate: Risk-free rate for Sharpe ratio calculation
            constraints: Dictionary of optimization constraints

        Returns:
            OptimizationResult with maximum Sharpe ratio weights
        """
        n_assets = len(covariance_matrix)
        asset_names = covariance_matrix.index.tolist()

        # 直接使用scipy优化器，避免CVXPY的DCP规则问题
        def negative_sharpe(weights):
            w = np.array(weights)
            port_return = w @ expected_returns.values
            port_std = np.sqrt(w @ covariance_matrix.values @ w)
            if port_std <= 0:
                return 0
            sharpe = (port_return - risk_free_rate) / port_std
            return -sharpe

        constraints_list = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        bounds = [(0.01, 1.0) for _ in range(n_assets)]
        x0 = np.ones(n_assets) / n_assets

        result = minimize(
            negative_sharpe,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints_list,
            options={'maxiter': 1000, 'ftol': 1e-9}
        )

        if result.success:
            optimal_weights = pd.Series(result.x, index=asset_names)
            optimal_weights = optimal_weights / optimal_weights.sum()
            expected_risk = np.sqrt(result.x @ covariance_matrix.values @ result.x)
            sharpe_ratio = -result.fun

            return OptimizationResult(
                optimal_weights=optimal_weights,
                expected_return=float(optimal_weights.values @ expected_returns.values),
                expected_risk=float(expected_risk),
                sharpe_ratio=float(sharpe_ratio),
                optimization_method='maximum_sharpe',
                constraints_satisfied=True,
                optimization_status='optimal'
            )
        else:
            # 返回等权重作为后备
            return self.equal_weight_optimization(covariance_matrix, expected_returns)

    def minimum_variance_optimization(
        self,
        covariance_matrix: pd.DataFrame,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> OptimizationResult:
        """
        Perform minimum variance optimization

        Args:
            covariance_matrix: Covariance matrix of asset returns
            constraints: Dictionary of optimization constraints

        Returns:
            OptimizationResult with minimum variance weights
        """
        # Placeholder implementation - will be implemented in subsequent tasks
        pass

    def maximum_diversification_optimization(
        self,
        expected_returns: pd.Series,
        covariance_matrix: pd.DataFrame,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> OptimizationResult:
        """
        Perform maximum diversification optimization

        Args:
            expected_returns: Expected returns for each asset
            covariance_matrix: Covariance matrix of asset returns
            constraints: Dictionary of optimization constraints

        Returns:
            OptimizationResult with maximum diversification weights
        """
        # Placeholder implementation - will be implemented in subsequent tasks
        pass

    def apply_constraints(
        self,
        optimization_problem: Any,
        position_limits: Optional[Tuple[float, float]] = None,
        sector_limits: Optional[Dict[str, Tuple[float, float]]] = None,
        turnover_limit: Optional[float] = None,
    ) -> Any:
        """
        Apply investment constraints to optimization problem

        Args:
            optimization_problem: CVXPY optimization problem
            position_limits: Min/max position limits as (min, max) tuple
            sector_limits: Sector exposure limits as dict of (min, max) tuples
            turnover_limit: Maximum portfolio turnover constraint

        Returns:
            Modified optimization problem with constraints
        """
        # Placeholder implementation - will be implemented in subsequent tasks
        pass

    def rebalancing_optimization(
        self,
        current_weights: pd.Series,
        target_weights: pd.Series,
        transaction_costs: pd.Series,
        tolerance: float = 0.01,
    ) -> OptimizationResult:
        """
        Optimize portfolio rebalancing considering transaction costs

        Args:
            current_weights: Current portfolio weights
            target_weights: Target portfolio weights
            transaction_costs: Transaction cost rates for each asset
            tolerance: Rebalancing tolerance threshold

        Returns:
            OptimizationResult with optimal rebalancing weights
        """
        # Placeholder implementation - will be implemented in subsequent tasks
        pass

    def calculate_efficient_frontier(
        self,
        expected_returns: pd.Series,
        covariance_matrix: pd.DataFrame,
        num_points: int = 50,
    ) -> pd.DataFrame:
        """
        Calculate efficient frontier points

        Args:
            expected_returns: Expected returns for each asset
            covariance_matrix: Covariance matrix of asset returns
            num_points: Number of points to calculate on efficient frontier

        Returns:
            DataFrame with efficient frontier risk/return points
        """
        # Placeholder implementation - will be implemented in subsequent tasks
        pass


def calculate_portfolio_performance(returns_dict: Dict[str, np.ndarray], weights: Dict[str, float]) -> Dict[str, Any]:
    """
    根据各资产的收益率数据和权重计算组合绩效指标

    Args:
        returns_dict: 字典，key为基金代码，value为收益率数组
        weights: 字典，key为基金代码，value为权重

    Returns:
        包含绩效指标的字典
    """
    # 安全处理函数
    def safe_float(val, default=0):
        if val is None:
            return default
        try:
            v = float(val)
            if np.isnan(v) or np.isinf(v):
                return default
            return v
        except:
            return default

    def safe_round(val, decimals=2):
        return round(safe_float(val), decimals)

    # 对齐所有收益率数组到相同长度
    min_len = min(len(r) for r in returns_dict.values()) if returns_dict else 0
    if min_len == 0:
        return {
            'annualized_return': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'volatility': 0,
            'win_rate': 0
        }

    aligned_returns = {}
    for code, ret in returns_dict.items():
        aligned_returns[code] = ret[-min_len:]

    # 计算组合加权收益率
    portfolio_returns = np.zeros(min_len)
    for code, ret in aligned_returns.items():
        w = weights.get(code, 0)
        portfolio_returns += w * ret

    if len(portfolio_returns) < 2:
        return {
            'annualized_return': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'volatility': 0,
            'win_rate': 0
        }

    # 计算各项指标
    # 年化收益率
    avg_daily_return = np.mean(portfolio_returns)
    annualized_return = avg_daily_return * 252

    # 波动率
    volatility = np.std(portfolio_returns) * np.sqrt(252)

    # 夏普比率（假设无风险利率2%）
    risk_free_rate = 0.02
    if volatility > 0:
        sharpe_ratio = (annualized_return - risk_free_rate) / volatility
    else:
        sharpe_ratio = 0

    # 最大回撤
    cumulative = (1 + portfolio_returns).cumprod()
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = abs(np.min(drawdown))

    # 胜率
    win_rate = (portfolio_returns > 0).sum() / len(portfolio_returns) * 100

    return {
        'annualized_return': safe_round(annualized_return * 100),  # 转换为百分比
        'sharpe_ratio': safe_round(sharpe_ratio),
        'max_drawdown': safe_round(max_drawdown * 100),
        'volatility': safe_round(volatility * 100),
        'win_rate': safe_round(win_rate)
    }


def calculate_portfolio_nav_series(
    returns_df: pd.DataFrame,
    weights: Dict[str, float],
    initial_value: float = 1.0
) -> pd.Series:
    """
    计算组合净值序列

    Args:
        returns_df: 收益率DataFrame，index为日期，columns为基金代码
        weights: 权重字典
        initial_value: 初始净值，默认为1.0

    Returns:
        净值序列Series，index为日期
    """
    if returns_df.empty:
        return pd.Series()

    # 计算加权组合收益率
    portfolio_returns = pd.Series(0.0, index=returns_df.index)
    for code in returns_df.columns:
        w = weights.get(code, 0)
        portfolio_returns += w * returns_df[code]

    # 计算净值序列
    nav_series = (1 + portfolio_returns).cumprod() * initial_value

    return nav_series


def get_fund_returns_matrix(fund_codes: List[str], start_date: str, end_date: str, db_manager) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """
    获取基金收益率矩阵和协方差矩阵

    Args:
        fund_codes: 基金代码列表
        start_date: 开始日期
        end_date: 结束日期
        db_manager: 数据库管理器

    Returns:
        (收益率DataFrame, 协方差矩阵, 预期收益率)
    """
    import pandas as pd
    from datetime import datetime

    all_nav_data = {}

    for fund_code in fund_codes:
        # 获取基金净值数据
        nav_sql = """
            SELECT nav_value as nav, nav_date FROM fund_nav_cache
            WHERE fund_code = :fund_code
            AND nav_date >= :start_date
            AND nav_date <= :end_date
            ORDER BY nav_date
        """
        # 先尝试从 tushare 实时获取
        nav_df = fetch_nav_from_tushare_realtime(fund_code, start_date, end_date)
        
        # 如果 tushare 无数据，再从 fund_nav_cache 获取
        if nav_df.empty:
            nav_sql = """
                SELECT nav_value as nav, nav_date FROM fund_nav_cache
                WHERE fund_code = :fund_code
                AND nav_date >= :start_date
                AND nav_date <= :end_date
                ORDER BY nav_date
            """
            nav_df = db_manager.execute_query(nav_sql, {
                'fund_code': fund_code,
                'start_date': start_date,
                'end_date': end_date
            })

        if not nav_df.empty:
            nav_df = nav_df.set_index('nav_date')
            # 删除重复的日期索引
            nav_df = nav_df[~nav_df.index.duplicated(keep='first')]
            nav_df['return'] = nav_df['nav'].pct_change()
            all_nav_data[fund_code] = nav_df['return'].dropna()

    if not all_nav_data:
        return pd.DataFrame(), pd.DataFrame(), pd.Series()

    # 合并所有基金的收益率（按日期对齐）
    returns_df = pd.DataFrame(all_nav_data)
    returns_df = returns_df.dropna()

    # 计算协方差矩阵
    if len(returns_df) > 1:
        cov_matrix = returns_df.cov() * 252  # 年化协方差
    else:
        cov_matrix = pd.DataFrame()

    # 计算预期收益率（使用历史平均收益率年化）
    expected_returns = returns_df.mean() * 252

    return returns_df, cov_matrix, expected_returns
