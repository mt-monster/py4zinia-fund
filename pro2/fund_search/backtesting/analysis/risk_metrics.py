#!/usr/bin/env python
# coding: utf-8

"""
风险指标计算模块
提供各种风险度量指标的计算
"""

import numpy as np
from typing import Optional


def calculate_var(returns: np.ndarray, confidence_level: float = 0.95) -> float:
    """
    计算风险价值 (Value at Risk)
    
    参数:
        returns: 收益率数组
        confidence_level: 置信水平（默认95%）
        
    返回:
        VaR值（负数表示损失）
    """
    if len(returns) == 0:
        return 0.0
    
    # 使用历史模拟法计算VaR
    var = np.percentile(returns, (1 - confidence_level) * 100)
    return var


def calculate_cvar(returns: np.ndarray, confidence_level: float = 0.95) -> float:
    """
    计算条件风险价值 (Conditional Value at Risk) / 期望损失
    
    参数:
        returns: 收益率数组
        confidence_level: 置信水平（默认95%）
        
    返回:
        CVaR值（负数表示损失）
    """
    if len(returns) == 0:
        return 0.0
    
    var = calculate_var(returns, confidence_level)
    # CVaR是超过VaR阈值的损失的均值
    cvar = np.mean(returns[returns <= var])
    return cvar


def calculate_beta(stock_returns: np.ndarray, market_returns: np.ndarray) -> float:
    """
    计算Beta系数
    
    参数:
        stock_returns: 股票/基金收益率数组
        market_returns: 市场收益率数组
        
    返回:
        Beta值
    """
    if len(stock_returns) == 0 or len(market_returns) == 0:
        return 1.0
    
    # 确保长度相同
    min_len = min(len(stock_returns), len(market_returns))
    stock_returns = stock_returns[:min_len]
    market_returns = market_returns[:min_len]
    
    # 计算协方差和市场方差
    covariance = np.cov(stock_returns, market_returns)[0, 1]
    market_variance = np.var(market_returns)
    
    if market_variance == 0:
        return 1.0
    
    beta = covariance / market_variance
    return beta


def calculate_alpha(stock_returns: np.ndarray, market_returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
    """
    计算Alpha系数（超额收益）
    
    参数:
        stock_returns: 股票/基金收益率数组
        market_returns: 市场收益率数组
        risk_free_rate: 无风险利率（年化）
        
    返回:
        Alpha值
    """
    beta = calculate_beta(stock_returns, market_returns)
    
    # 年化收益率
    stock_annual_return = np.mean(stock_returns) * 252
    market_annual_return = np.mean(market_returns) * 252
    
    # CAPM: Alpha = 实际收益 - (无风险利率 + Beta * (市场收益 - 无风险利率))
    alpha = stock_annual_return - (risk_free_rate + beta * (market_annual_return - risk_free_rate))
    return alpha


def calculate_tracking_error(stock_returns: np.ndarray, benchmark_returns: np.ndarray) -> float:
    """
    计算跟踪误差
    
    参数:
        stock_returns: 股票/基金收益率数组
        benchmark_returns: 基准收益率数组
        
    返回:
        跟踪误差（年化）
    """
    if len(stock_returns) == 0 or len(benchmark_returns) == 0:
        return 0.0
    
    min_len = min(len(stock_returns), len(benchmark_returns))
    stock_returns = stock_returns[:min_len]
    benchmark_returns = benchmark_returns[:min_len]
    
    # 收益率差异的标准差
    return_diff = stock_returns - benchmark_returns
    tracking_error = np.std(return_diff) * np.sqrt(252)
    
    return tracking_error


def calculate_information_ratio(stock_returns: np.ndarray, benchmark_returns: np.ndarray) -> float:
    """
    计算信息比率
    
    参数:
        stock_returns: 股票/基金收益率数组
        benchmark_returns: 基准收益率数组
        
    返回:
        信息比率
    """
    if len(stock_returns) == 0 or len(benchmark_returns) == 0:
        return 0.0
    
    min_len = min(len(stock_returns), len(benchmark_returns))
    stock_returns = stock_returns[:min_len]
    benchmark_returns = benchmark_returns[:min_len]
    
    # 超额收益
    excess_return = np.mean(stock_returns - benchmark_returns) * 252
    
    # 跟踪误差
    te = calculate_tracking_error(stock_returns, benchmark_returns)
    
    if te == 0:
        return 0.0
    
    information_ratio = excess_return / te
    return information_ratio


def calculate_downside_deviation(returns: np.ndarray, target_return: float = 0.0) -> float:
    """
    计算下行标准差（用于Sortino比率）
    
    参数:
        returns: 收益率数组
        target_return: 目标收益率（默认0）
        
    返回:
        下行标准差（年化）
    """
    if len(returns) == 0:
        return 0.0
    
    # 只考虑低于目标收益率的偏差
    downside_returns = returns[returns < target_return]
    
    if len(downside_returns) == 0:
        return 0.0
    
    downside_deviation = np.std(downside_returns) * np.sqrt(252)
    return downside_deviation


def calculate_sortino_ratio(returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
    """
    计算Sortino比率
    
    参数:
        returns: 收益率数组
        risk_free_rate: 无风险利率（年化）
        
    返回:
        Sortino比率
    """
    if len(returns) == 0:
        return 0.0
    
    # 年化收益率
    annual_return = np.mean(returns) * 252
    
    # 下行标准差
    downside_dev = calculate_downside_deviation(returns, risk_free_rate / 252)
    
    if downside_dev == 0:
        return 0.0
    
    sortino_ratio = (annual_return - risk_free_rate) / downside_dev
    return sortino_ratio


def calculate_calmar_ratio(returns: np.ndarray) -> float:
    """
    计算Calmar比率
    
    参数:
        returns: 收益率数组
        
    返回:
        Calmar比率
    """
    if len(returns) == 0:
        return 0.0
    
    # 年化收益率
    annual_return = np.mean(returns) * 252
    
    # 最大回撤
    cumulative = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = abs(np.min(drawdown))
    
    if max_drawdown == 0:
        return 0.0
    
    calmar_ratio = annual_return / max_drawdown
    return calmar_ratio
