#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略回测验证系统
Strategy Backtest Validation System

验证策略选择器（StrategySelector）选择的策略在历史数据上的有效性。
通过历史数据分段回测，评估策略选择的准确性。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from collections import defaultdict

# 导入现有模块
from .strategy_selector import StrategySelector, StrategyMatchResult, get_strategy_selector
from .advanced_strategies import (
    BaseStrategy, DualMAStrategy, MeanReversionStrategy,
    TargetValueStrategy, GridTradingStrategy, EnhancedRuleBasedStrategy,
    StrategySignal
)
from .performance_metrics import PerformanceCalculator, PerformanceMetrics

logger = logging.getLogger(__name__)


class RebalanceFrequency(Enum):
    """再平衡频率"""
    DAILY = "daily"         # 每日
    WEEKLY = "weekly"       # 每周
    MONTHLY = "monthly"     # 每月
    QUARTERLY = "quarterly" # 每季度


@dataclass
class StrategyPerformance:
    """单策略回测绩效"""
    strategy_key: str
    strategy_name: str
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    win_rate: float
    final_value: float
    trades_count: int
    equity_curve: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'strategy_key': self.strategy_key,
            'strategy_name': self.strategy_name,
            'total_return': round(self.total_return, 4),
            'annual_return': round(self.annual_return, 4),
            'sharpe_ratio': round(self.sharpe_ratio, 4),
            'max_drawdown': round(self.max_drawdown, 4),
            'volatility': round(self.volatility, 4),
            'win_rate': round(self.win_rate, 4),
            'final_value': round(self.final_value, 2),
            'trades_count': self.trades_count
        }


@dataclass
class StrategyComparison:
    """策略对比结果"""
    fund_code: str
    start_date: str
    end_date: str
    selected_strategy: str
    strategies_performance: List[StrategyPerformance]
    best_strategy: str
    worst_strategy: str
    selection_rank: int  # 被选策略的排名（1为最佳）
    beat_average: bool   # 是否跑赢平均
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'fund_code': self.fund_code,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'selected_strategy': self.selected_strategy,
            'strategies_performance': [p.to_dict() for p in self.strategies_performance],
            'best_strategy': self.best_strategy,
            'worst_strategy': self.worst_strategy,
            'selection_rank': self.selection_rank,
            'beat_average': self.beat_average
        }


@dataclass
class SelectionRecord:
    """单次策略选择记录"""
    date: str
    selected_strategy: str
    actual_best_strategy: str
    is_correct: bool
    selected_return: float
    best_return: float
    all_returns: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'date': self.date,
            'selected_strategy': self.selected_strategy,
            'actual_best_strategy': self.actual_best_strategy,
            'is_correct': self.is_correct,
            'selected_return': round(self.selected_return, 4),
            'best_return': round(self.best_return, 4),
            'all_returns': {k: round(v, 4) for k, v in self.all_returns.items()}
        }


@dataclass
@dataclass
class BacktestResult:
    """回测验证结果"""
    fund_code: str
    start_date: str
    end_date: str
    selection_accuracy: float      # 选择准确率
    excess_return: float           # 超额收益率
    selected_sharpe: float         # 被选策略夏普比率
    benchmark_sharpe: float        # 基准策略夏普比率
    selected_max_drawdown: float   # 被选策略最大回撤
    benchmark_max_drawdown: float  # 基准策略最大回撤
    selection_records: List[SelectionRecord]
    strategy_comparison: Optional[StrategyComparison]
    
    # 统计信息
    total_selections: int
    correct_selections: int
    average_return_gap: float      # 平均收益差距
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'fund_code': self.fund_code,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'selection_accuracy': round(self.selection_accuracy, 4),
            'excess_return': round(self.excess_return, 4),
            'selected_sharpe': round(self.selected_sharpe, 4),
            'benchmark_sharpe': round(self.benchmark_sharpe, 4),
            'selected_max_drawdown': round(self.selected_max_drawdown, 4),
            'benchmark_max_drawdown': round(self.benchmark_max_drawdown, 4),
            'selection_records': [r.to_dict() for r in self.selection_records],
            'strategy_comparison': self.strategy_comparison.to_dict() if self.strategy_comparison else None,
            'total_selections': self.total_selections,
            'correct_selections': self.correct_selections,
            'average_return_gap': round(self.average_return_gap, 4)
        }


@dataclass
class BatchValidationResult:
    """批量验证结果"""
    fund_codes: List[str]
    period_days: int
    overall_accuracy: float
    fund_results: Dict[str, BacktestResult]
    summary: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'fund_codes': self.fund_codes,
            'period_days': self.period_days,
            'overall_accuracy': round(self.overall_accuracy, 4),
            'fund_results': {k: v.to_dict() for k, v in self.fund_results.items()},
            'summary': self.summary
        }


class StrategyBacktestValidator:
    """
    策略回测验证器
    
    用于验证策略选择器（StrategySelector）在历史数据上的表现。
    通过分段回测，评估策略选择的准确性和有效性。
    
    主要功能：
    1. 单基金回测 - backtest_strategy_selection
    2. 多策略对比 - compare_strategies
    3. 批量验证 - validate_selection_accuracy
    """
    
    # 策略映射表
    STRATEGY_MAP = {
        'dual_ma': DualMAStrategy,
        'mean_reversion': MeanReversionStrategy,
        'grid_trading': GridTradingStrategy,
        'target_value': TargetValueStrategy,
        'enhanced_rule': EnhancedRuleBasedStrategy
    }
    
    def __init__(self, 
                 base_amount: float = 100.0,
                 rebalance_freq: RebalanceFrequency = RebalanceFrequency.MONTHLY,
                 lookback_days: int = 60,
                 data_fetcher=None):
        """
        初始化验证器
        
        Args:
            base_amount: 基准定投金额
            rebalance_freq: 策略再平衡频率
            lookback_days: 策略选择时的回看天数
            data_fetcher: 数据获取函数，接收fund_code返回DataFrame
        """
        self.base_amount = base_amount
        self.rebalance_freq = rebalance_freq
        self.lookback_days = lookback_days
        self.data_fetcher = data_fetcher or self._default_data_fetcher
        self.selector = get_strategy_selector()
        self.calculator = PerformanceCalculator()
        
    def _default_data_fetcher(self, fund_code: str) -> Optional[pd.DataFrame]:
        """
        默认数据获取方法
        
        Args:
            fund_code: 基金代码
            
        Returns:
            DataFrame或None
        """
        try:
            import akshare as ak
            df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            if not df.empty:
                df['净值日期'] = pd.to_datetime(df['净值日期'])
                df = df.sort_values('净值日期').reset_index(drop=True)
                df['单位净值'] = pd.to_numeric(df['单位净值'], errors='coerce')
                return df
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 数据失败: {e}")
        return None
    
    def _get_rebalance_dates(self, start_date: str, end_date: str, 
                            df: pd.DataFrame) -> List[int]:
        """
        获取再平衡日期索引
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            df: 历史数据
            
        Returns:
            再平衡日期索引列表
        """
        dates = df['净值日期'] if '净值日期' in df.columns else df.index
        rebalance_indices = []
        
        if self.rebalance_freq == RebalanceFrequency.DAILY:
            # 每天再平衡
            rebalance_indices = list(range(len(df)))
        elif self.rebalance_freq == RebalanceFrequency.WEEKLY:
            # 每周一再平衡
            for i, date in enumerate(dates):
                if isinstance(date, str):
                    date = pd.to_datetime(date)
                if date.weekday() == 0:  # Monday
                    rebalance_indices.append(i)
        elif self.rebalance_freq == RebalanceFrequency.MONTHLY:
            # 每月第一个交易日再平衡
            prev_month = None
            for i, date in enumerate(dates):
                if isinstance(date, str):
                    date = pd.to_datetime(date)
                if date.month != prev_month:
                    rebalance_indices.append(i)
                    prev_month = date.month
        elif self.rebalance_freq == RebalanceFrequency.QUARTERLY:
            # 每季度第一个交易日再平衡
            prev_quarter = None
            for i, date in enumerate(dates):
                if isinstance(date, str):
                    date = pd.to_datetime(date)
                current_quarter = (date.month - 1) // 3
                if current_quarter != prev_quarter:
                    rebalance_indices.append(i)
                    prev_quarter = current_quarter
        
        # 确保至少包含起始和结束
        if not rebalance_indices or rebalance_indices[0] != 0:
            rebalance_indices = [0] + rebalance_indices
        if rebalance_indices[-1] != len(df) - 1:
            rebalance_indices.append(len(df) - 1)
            
        return rebalance_indices
    
    def _simulate_strategy(self, df: pd.DataFrame, strategy_key: str,
                          rebalance_indices: List[int]) -> StrategyPerformance:
        """
        模拟单一策略的回测
        
        Args:
            df: 历史数据
            strategy_key: 策略标识
            rebalance_indices: 再平衡日期索引
            
        Returns:
            StrategyPerformance
        """
        strategy_class = self.STRATEGY_MAP.get(strategy_key, EnhancedRuleBasedStrategy)
        strategy = strategy_class()
        
        cash = self.base_amount
        shares = 0.0
        trades_count = 0
        equity_curve = []
        
        nav_col = '单位净值' if '单位净值' in df.columns else df.select_dtypes(include=[np.number]).columns[0]
        nav = df[nav_col].values
        
        current_strategy = strategy
        
        for i in range(len(df)):
            current_nav = nav[i]
            
            # 在再平衡日重新选择策略
            if i in rebalance_indices and i >= self.lookback_days:
                lookback_df = df.iloc[max(0, i-self.lookback_days):i+1].copy()
                signal = current_strategy.generate_signal(lookback_df, -1)
                
                if signal.action == 'buy' and signal.amount_multiplier > 0:
                    buy_amount = self.base_amount * signal.amount_multiplier
                    buy_shares = buy_amount / current_nav
                    shares += buy_shares
                    cash -= buy_amount
                    trades_count += 1
                elif signal.action == 'sell' and shares > 0:
                    sell_shares = shares * signal.amount_multiplier
                    sell_amount = sell_shares * current_nav
                    shares -= sell_shares
                    cash += sell_amount
                    trades_count += 1
            elif i < self.lookback_days and i > 0:
                # 累积期使用基准定投
                buy_amount = self.base_amount
                buy_shares = buy_amount / current_nav
                shares += buy_shares
                cash -= buy_amount
                trades_count += 1
            
            total_value = cash + shares * current_nav
            equity_curve.append(total_value)
        
        # 计算绩效指标
        if len(equity_curve) >= 2:
            returns = np.diff(equity_curve) / equity_curve[:-1]
            returns = np.nan_to_num(returns, nan=0.0, posinf=0.0, neginf=0.0)
            
            total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0] if equity_curve[0] > 0 else 0
            days = len(equity_curve)
            annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 and total_return > -1 else 0
            sharpe = self.calculator.calculate_sharpe_ratio(returns)
            max_dd = self.calculator.calculate_max_drawdown(equity_curve)
            volatility = self.calculator.calculate_volatility(returns)
            win_rate = (returns > 0).mean() if len(returns) > 0 else 0
        else:
            total_return = annual_return = sharpe = max_dd = volatility = win_rate = 0
        
        return StrategyPerformance(
            strategy_key=strategy_key,
            strategy_name=self.selector.STRATEGIES.get(strategy_key, {}).get('name', strategy_key),
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            volatility=volatility,
            win_rate=win_rate,
            final_value=equity_curve[-1] if equity_curve else 0,
            trades_count=trades_count,
            equity_curve=equity_curve
        )
    
    def backtest_strategy_selection(self, fund_code: str, 
                                   start_date: str, 
                                   end_date: str) -> Optional[BacktestResult]:
        """
        对单只基金进行策略选择回测
        
        在每个再平衡日重新运行策略选择器，记录选择结果和实际表现，
        最终计算选择准确率。
        
        Args:
            fund_code: 基金代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            BacktestResult或None
        """
        # 获取数据
        df = self.data_fetcher(fund_code)
        if df is None or df.empty:
            logger.error(f"无法获取基金 {fund_code} 的数据")
            return None
        
        # 过滤日期范围
        date_col = '净值日期' if '净值日期' in df.columns else df.columns[0]
        df = df[(df[date_col] >= start_date) & (df[date_col] <= end_date)]
        df = df.reset_index(drop=True)
        
        if len(df) < self.lookback_days + 30:
            logger.warning(f"基金 {fund_code} 数据不足，需要至少 {self.lookback_days + 30} 天")
            return None
        
        # 获取再平衡日期
        rebalance_indices = self._get_rebalance_dates(start_date, end_date, df)
        
        selection_records = []
        correct_count = 0
        total_return_gap = 0.0
        
        # 对每次再平衡进行验证
        for idx in rebalance_indices[1:-1]:  # 跳过第一个和最后一个
            # 获取回看数据用于策略选择
            lookback_start = max(0, idx - self.lookback_days)
            lookback_df = df.iloc[lookback_start:idx+1].copy()
            
            # 选择策略
            match_result = self.selector.select_best_strategy(lookback_df)
            selected_strategy = match_result.strategy_type if match_result else 'enhanced_rule'
            
            # 获取前瞻数据用于验证（使用未来1个月的表现）
            forward_end = min(len(df), idx + 30)
            forward_df = df.iloc[idx:forward_end].copy()
            
            if len(forward_df) < 5:
                continue
            
            # 模拟各策略在前瞻期的表现
            strategy_returns = {}
            for key in self.STRATEGY_MAP.keys():
                perf = self._simulate_strategy(
                    forward_df.reset_index(drop=True), 
                    key, 
                    [0, len(forward_df)-1]
                )
                strategy_returns[key] = perf.total_return
            
            # 找出实际表现最好的策略
            actual_best = max(strategy_returns.items(), key=lambda x: x[1])
            selected_return = strategy_returns.get(selected_strategy, 0)
            
            is_correct = selected_strategy == actual_best[0]
            if is_correct:
                correct_count += 1
            
            return_gap = actual_best[1] - selected_return
            total_return_gap += return_gap
            
            record = SelectionRecord(
                date=str(df.iloc[idx][date_col]),
                selected_strategy=selected_strategy,
                actual_best_strategy=actual_best[0],
                is_correct=is_correct,
                selected_return=selected_return,
                best_return=actual_best[1],
                all_returns=strategy_returns.copy()
            )
            selection_records.append(record)
        
        # 计算整体回测结果（使用被选策略连续运行）
        strategy_comparison = self.compare_strategies(fund_code, start_date, end_date)
        
        total_selections = len(selection_records)
        accuracy = correct_count / total_selections if total_selections > 0 else 0
        avg_return_gap = total_return_gap / total_selections if total_selections > 0 else 0
        
        # 计算被选策略和基准策略的绩效对比
        if strategy_comparison:
            selected_perf = next(
                (p for p in strategy_comparison.strategies_performance 
                 if p.strategy_key == strategy_comparison.selected_strategy),
                None
            )
            benchmark_perf = next(
                (p for p in strategy_comparison.strategies_performance 
                 if p.strategy_key == 'enhanced_rule'),
                strategy_comparison.strategies_performance[0] if strategy_comparison.strategies_performance else None
            )
            
            excess_return = (selected_perf.total_return - benchmark_perf.total_return) if selected_perf and benchmark_perf else 0
            selected_sharpe = selected_perf.sharpe_ratio if selected_perf else 0
            benchmark_sharpe = benchmark_perf.sharpe_ratio if benchmark_perf else 0
            selected_dd = selected_perf.max_drawdown if selected_perf else 0
            benchmark_dd = benchmark_perf.max_drawdown if benchmark_perf else 0
        else:
            excess_return = selected_sharpe = benchmark_sharpe = 0
            selected_dd = benchmark_dd = 0
        
        return BacktestResult(
            fund_code=fund_code,
            start_date=start_date,
            end_date=end_date,
            selection_accuracy=accuracy,
            excess_return=excess_return,
            selected_sharpe=selected_sharpe,
            benchmark_sharpe=benchmark_sharpe,
            selected_max_drawdown=selected_dd,
            benchmark_max_drawdown=benchmark_dd,
            selection_records=selection_records,
            strategy_comparison=strategy_comparison,
            total_selections=total_selections,
            correct_selections=correct_count,
            average_return_gap=avg_return_gap
        )
    
    def compare_strategies(self, fund_code: str, 
                          start_date: str, 
                          end_date: str) -> Optional[StrategyComparison]:
        """
        对比不同策略在同一基金上的表现
        
        Args:
            fund_code: 基金代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            StrategyComparison或None
        """
        # 获取数据
        df = self.data_fetcher(fund_code)
        if df is None or df.empty:
            logger.error(f"无法获取基金 {fund_code} 的数据")
            return None
        
        # 过滤日期范围
        date_col = '净值日期' if '净值日期' in df.columns else df.columns[0]
        df = df[(df[date_col] >= start_date) & (df[date_col] <= end_date)]
        df = df.reset_index(drop=True)
        
        if len(df) < 30:
            logger.warning(f"基金 {fund_code} 数据不足")
            return None
        
        # 使用策略选择器选择最佳策略
        match_result = self.selector.select_best_strategy(df)
        selected_strategy = match_result.strategy_type if match_result else 'enhanced_rule'
        
        # 模拟各策略表现
        rebalance_indices = self._get_rebalance_dates(start_date, end_date, df)
        strategies_performance = []
        
        for key in self.STRATEGY_MAP.keys():
            perf = self._simulate_strategy(df, key, rebalance_indices)
            strategies_performance.append(perf)
        
        # 按总收益率排序
        strategies_performance.sort(key=lambda x: x.total_return, reverse=True)
        
        # 计算排名
        rank_map = {p.strategy_key: i+1 for i, p in enumerate(strategies_performance)}
        selection_rank = rank_map.get(selected_strategy, -1)
        
        # 计算是否跑赢平均
        avg_return = np.mean([p.total_return for p in strategies_performance])
        selected_return = next(
            (p.total_return for p in strategies_performance if p.strategy_key == selected_strategy),
            0
        )
        beat_average = selected_return > avg_return
        
        return StrategyComparison(
            fund_code=fund_code,
            start_date=start_date,
            end_date=end_date,
            selected_strategy=selected_strategy,
            strategies_performance=strategies_performance,
            best_strategy=strategies_performance[0].strategy_key,
            worst_strategy=strategies_performance[-1].strategy_key,
            selection_rank=selection_rank,
            beat_average=beat_average
        )
    
    def validate_selection_accuracy(self, 
                                   fund_codes: List[str], 
                                   period_days: int = 365) -> BatchValidationResult:
        """
        批量验证策略选择的准确性
        
        对多只基金进行回测验证，计算整体选择准确率。
        
        Args:
            fund_codes: 基金代码列表
            period_days: 回测周期天数
            
        Returns:
            BatchValidationResult
        """
        fund_results = {}
        total_correct = 0
        total_selections = 0
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=period_days)).strftime('%Y-%m-%d')
        
        for fund_code in fund_codes:
            logger.info(f"正在验证基金 {fund_code}...")
            try:
                result = self.backtest_strategy_selection(fund_code, start_date, end_date)
                if result:
                    fund_results[fund_code] = result
                    total_correct += result.correct_selections
                    total_selections += result.total_selections
            except Exception as e:
                logger.error(f"验证基金 {fund_code} 时出错: {e}")
                continue
        
        overall_accuracy = total_correct / total_selections if total_selections > 0 else 0
        
        # 生成汇总统计
        excess_returns = [r.excess_return for r in fund_results.values()]
        accuracies = [r.selection_accuracy for r in fund_results.values()]
        
        summary = {
            'total_funds': len(fund_codes),
            'successful_funds': len(fund_results),
            'overall_accuracy': round(overall_accuracy, 4),
            'avg_excess_return': round(np.mean(excess_returns), 4) if excess_returns else 0,
            'avg_selection_accuracy': round(np.mean(accuracies), 4) if accuracies else 0,
            'accuracy_std': round(np.std(accuracies), 4) if accuracies else 0,
            'funds_beat_benchmark': sum(1 for r in fund_results.values() if r.excess_return > 0),
            'funds_beat_average': sum(1 for r in fund_results.values() if r.strategy_comparison and r.strategy_comparison.beat_average)
        }
        
        return BatchValidationResult(
            fund_codes=fund_codes,
            period_days=period_days,
            overall_accuracy=overall_accuracy,
            fund_results=fund_results,
            summary=summary
        )


# ==================== API端点支持函数 ====================

def api_backtest_single_fund(fund_code: str, start_date: str, end_date: str,
                             rebalance_freq: str = 'monthly') -> Dict[str, Any]:
    """
    API端点：单基金回测
    
    Args:
        fund_code: 基金代码
        start_date: 开始日期
        end_date: 结束日期
        rebalance_freq: 再平衡频率 (daily/weekly/monthly/quarterly)
        
    Returns:
        API响应字典
    """
    try:
        freq_map = {
            'daily': RebalanceFrequency.DAILY,
            'weekly': RebalanceFrequency.WEEKLY,
            'monthly': RebalanceFrequency.MONTHLY,
            'quarterly': RebalanceFrequency.QUARTERLY
        }
        freq = freq_map.get(rebalance_freq, RebalanceFrequency.MONTHLY)
        
        validator = StrategyBacktestValidator(rebalance_freq=freq)
        result = validator.backtest_strategy_selection(fund_code, start_date, end_date)
        
        if result is None:
            return {'success': False, 'error': '回测失败，数据不足或获取失败'}
        
        return {
            'success': True,
            'data': result.to_dict()
        }
    except Exception as e:
        logger.error(f"API回测失败: {e}")
        return {'success': False, 'error': str(e)}


def api_compare_strategies(fund_code: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    API端点：策略对比
    
    Args:
        fund_code: 基金代码
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        API响应字典
    """
    try:
        validator = StrategyBacktestValidator()
        result = validator.compare_strategies(fund_code, start_date, end_date)
        
        if result is None:
            return {'success': False, 'error': '策略对比失败，数据不足'}
        
        return {
            'success': True,
            'data': result.to_dict()
        }
    except Exception as e:
        logger.error(f"API策略对比失败: {e}")
        return {'success': False, 'error': str(e)}


def api_validate_batch(fund_codes: List[str], period_days: int = 365) -> Dict[str, Any]:
    """
    API端点：批量验证
    
    Args:
        fund_codes: 基金代码列表
        period_days: 回测周期天数
        
    Returns:
        API响应字典
    """
    try:
        validator = StrategyBacktestValidator()
        result = validator.validate_selection_accuracy(fund_codes, period_days)
        
        return {
            'success': True,
            'data': result.to_dict()
        }
    except Exception as e:
        logger.error(f"API批量验证失败: {e}")
        return {'success': False, 'error': str(e)}


def api_get_validation_summary(fund_code: str, 
                               start_date: str, 
                               end_date: str) -> Dict[str, Any]:
    """
    API端点：获取验证摘要
    
    提供简化的验证结果摘要，适合前端展示。
    
    Args:
        fund_code: 基金代码
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        API响应字典
    """
    try:
        validator = StrategyBacktestValidator()
        result = validator.backtest_strategy_selection(fund_code, start_date, end_date)
        
        if result is None:
            return {'success': False, 'error': '获取摘要失败'}
        
        summary = {
            'fund_code': fund_code,
            'period': f"{start_date} to {end_date}",
            'selection_accuracy': round(result.selection_accuracy, 2),
            'excess_return': round(result.excess_return, 4),
            'selected_strategy': result.strategy_comparison.selected_strategy if result.strategy_comparison else 'unknown',
            'selection_rank': result.strategy_comparison.selection_rank if result.strategy_comparison else -1,
            'beat_average': result.strategy_comparison.beat_average if result.strategy_comparison else False,
            'total_selections': result.total_selections,
            'correct_selections': result.correct_selections,
            'key_metrics': {
                'selected_sharpe': round(result.selected_sharpe, 2),
                'benchmark_sharpe': round(result.benchmark_sharpe, 2),
                'selected_max_drawdown': round(result.selected_max_drawdown, 4),
                'benchmark_max_drawdown': round(result.benchmark_max_drawdown, 4)
            }
        }
        
        return {
            'success': True,
            'data': summary
        }
    except Exception as e:
        logger.error(f"API获取摘要失败: {e}")
        return {'success': False, 'error': str(e)}


# ==================== 单例模式 ====================

_validator_instance = None

def get_validator(base_amount: float = 100.0,
                 rebalance_freq: RebalanceFrequency = RebalanceFrequency.MONTHLY,
                 lookback_days: int = 60) -> StrategyBacktestValidator:
    """
    获取策略回测验证器单例
    
    Args:
        base_amount: 基准定投金额
        rebalance_freq: 再平衡频率
        lookback_days: 回看天数
        
    Returns:
        StrategyBacktestValidator实例
    """
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = StrategyBacktestValidator(
            base_amount=base_amount,
            rebalance_freq=rebalance_freq,
            lookback_days=lookback_days
        )
    return _validator_instance


# ==================== 测试代码 ====================

if __name__ == "__main__":
    """测试策略回测验证器"""
    logging.basicConfig(level=logging.INFO)
    
    # 测试单基金回测
    fund_code = "005827"  # 易方达蓝筹精选混合
    validator = StrategyBacktestValidator()
    
    print(f"\n{'='*60}")
    print(f"测试单基金回测: {fund_code}")
    print(f"{'='*60}")
    
    result = validator.backtest_strategy_selection(
        fund_code=fund_code,
        start_date="2023-01-01",
        end_date="2024-01-01"
    )
    
    if result:
        print(f"\n回测结果:")
        print(f"  基金代码: {result.fund_code}")
        print(f"  回测期间: {result.start_date} 至 {result.end_date}")
        print(f"  选择准确率: {result.selection_accuracy:.2%}")
        print(f"  超额收益率: {result.excess_return:.2%}")
        print(f"  总选择次数: {result.total_selections}")
        print(f"  正确次数: {result.correct_selections}")
        print(f"  平均收益差距: {result.average_return_gap:.2%}")
        
        if result.strategy_comparison:
            print(f"\n  策略对比:")
            print(f"    被选策略: {result.strategy_comparison.selected_strategy}")
            print(f"    排名: {result.strategy_comparison.selection_rank}")
            print(f"    跑赢平均: {result.strategy_comparison.beat_average}")
            print(f"    最佳策略: {result.strategy_comparison.best_strategy}")
            print(f"    最差策略: {result.strategy_comparison.worst_strategy}")
    else:
        print("回测失败，请检查数据和网络连接")
    
    # 测试策略对比
    print(f"\n{'='*60}")
    print(f"测试策略对比: {fund_code}")
    print(f"{'='*60}")
    
    comparison = validator.compare_strategies(
        fund_code=fund_code,
        start_date="2023-01-01",
        end_date="2024-01-01"
    )
    
    if comparison:
        print(f"\n策略对比结果:")
        print(f"  被选策略: {comparison.selected_strategy}")
        print(f"  策略排名: {comparison.selection_rank}")
        print(f"  跑赢平均: {comparison.beat_average}")
        print(f"\n  各策略表现:")
        for perf in comparison.strategies_performance:
            print(f"    {perf.strategy_name}: 收益率={perf.total_return:.2%}, 夏普={perf.sharpe_ratio:.2f}")
