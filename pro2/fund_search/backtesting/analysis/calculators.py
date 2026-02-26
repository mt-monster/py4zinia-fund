"""
计算工具模块
提供常用的金融计算函数
"""

import numpy as np
import pandas as pd
from typing import Union


def calculate_max_drawdown(prices: Union[np.ndarray, pd.Series]) -> float:
    """
    计算最大回撤
    
    参数:
        prices: 价格序列（numpy数组或pandas Series）
        
    返回:
        最大回撤值（负数表示回撤）
    """
    if isinstance(prices, pd.Series):
        prices = prices.values
    
    if len(prices) == 0:
        return 0.0
    
    # 计算累计最大值
    running_max = np.maximum.accumulate(prices)
    
    # 计算回撤
    drawdown = (prices - running_max) / running_max
    
    # 找到最大回撤
    max_dd = np.min(drawdown)
    
    return max_dd


def calculate_sharpe_ratio(returns: Union[np.ndarray, pd.Series], risk_free_rate: float = 0.02) -> float:
    """
    计算夏普比率
    
    参数:
        returns: 收益率数组（日收益率）
        risk_free_rate: 无风险利率（年化，默认2%）
        
    返回:
        夏普比率
    """
    if isinstance(returns, pd.Series):
        returns = returns.values
    
    if len(returns) == 0 or np.std(returns) == 0:
        return 0.0
    
    # 计算年化收益率（假设252个交易日）
    annual_return = np.mean(returns) * 252
    
    # 计算年化波动率
    annual_volatility = np.std(returns) * np.sqrt(252)
    
    if annual_volatility == 0:
        return 0.0
    
    # 计算夏普比率
    sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility
    
    return sharpe_ratio


def calculate_volatility(returns: Union[np.ndarray, pd.Series], annualized: bool = True) -> float:
    """
    计算波动率
    
    参数:
        returns: 收益率数组
        annualized: 是否年化（默认True）
        
    返回:
        波动率
    """
    if isinstance(returns, pd.Series):
        returns = returns.values
    
    if len(returns) == 0:
        return 0.0
    
    volatility = np.std(returns)
    
    if annualized:
        volatility *= np.sqrt(252)
    
    return volatility


def calculate_total_return(prices: Union[np.ndarray, pd.Series]) -> float:
    """
    计算总收益率
    
    参数:
        prices: 价格序列
        
    返回:
        总收益率
    """
    if isinstance(prices, pd.Series):
        prices = prices.values
    
    if len(prices) < 2:
        return 0.0
    
    return (prices[-1] - prices[0]) / prices[0]


def calculate_cagr(prices: Union[np.ndarray, pd.Series], periods_per_year: int = 252) -> float:
    """
    计算复合年均增长率（CAGR）
    
    参数:
        prices: 价格序列
        periods_per_year: 每年周期数（默认252个交易日）
        
    返回:
        复合年均增长率
    """
    if isinstance(prices, pd.Series):
        prices = prices.values
    
    if len(prices) < 2:
        return 0.0
    
    total_return = (prices[-1] / prices[0])
    n_periods = len(prices) / periods_per_year
    
    if n_periods == 0:
        return 0.0
    
    cagr = (total_return ** (1 / n_periods)) - 1
    return cagr
