#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略优化回测对比框架
对比原始策略与优化后策略的性能差异
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

# 导入策略类
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ..strategies.advanced_strategies import (
    DualMAStrategy, MeanReversionStrategy, EnhancedRuleBasedStrategy,
    StrategySignal, BaseStrategy
)
# 统一引擎导入暂时注释，因为有相对导入问题
# from unified_strategy_engine import UnifiedStrategyEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    version: str  # 'original' or 'optimized'
    
    # 收益指标
    total_return: float
    annualized_return: float
    
    # 风险指标
    max_drawdown: float
    volatility: float
    sharpe_ratio: float
    
    # 交易统计
    total_trades: int
    buy_signals: int
    sell_signals: int
    hold_signals: int
    
    # 资金曲线
    equity_curve: List[float]
    
    # 详细交易记录
    trades: List[Dict]
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'strategy_name': self.strategy_name,
            'version': self.version,
            'total_return': f"{self.total_return:.2%}",
            'annualized_return': f"{self.annualized_return:.2%}",
            'max_drawdown': f"{self.max_drawdown:.2%}",
            'volatility': f"{self.volatility:.2%}",
            'sharpe_ratio': f"{self.sharpe_ratio:.2f}",
            'total_trades': self.total_trades,
            'buy_signals': self.buy_signals,
            'sell_signals': self.sell_signals,
            'hold_signals': self.hold_signals,
        }


class StrategyOptimizer:
    """策略优化器 - 创建优化前后的策略对比"""
    
    @staticmethod
    def get_original_mean_reversion() -> MeanReversionStrategy:
        """获取原始均值回归策略（修复前）"""
        strategy = MeanReversionStrategy()
        # 覆盖为原始逻辑（用于对比）
        strategy.generate_signal_original = strategy.generate_signal
        
        def original_generate_signal(history_df, current_index, **kwargs):
            """原始逻辑（有缺陷）"""
            if current_index < strategy.window:
                return StrategySignal('buy', 1.0, "累积期")
                
            nav = strategy._get_nav(history_df)
            subset = nav.iloc[current_index - strategy.window : current_index + 1]
            ma = subset.mean()
            current_price = nav.iloc[current_index]
            
            deviation = (current_price - ma) / ma
            
            if deviation < -strategy.threshold * 2:
                return StrategySignal('buy', 2.0, "极度低估")
            elif deviation < -strategy.threshold:
                return StrategySignal('buy', 1.5, "低估区域")
            elif deviation > strategy.threshold * 2:
                # 原始：只卖0.5
                return StrategySignal('sell', 0.5, "极度高估")
            elif deviation > strategy.threshold:
                # 原始：错误地买入
                return StrategySignal('buy', 0.5, "高估区域")
            else:
                return StrategySignal('buy', 1.0, "正常区域")
        
        strategy.generate_signal = original_generate_signal
        strategy.name += " (原始版)"
        return strategy
    
    @staticmethod
    def get_optimized_mean_reversion() -> MeanReversionStrategy:
        """获取优化后的均值回归策略"""
        strategy = MeanReversionStrategy()
        strategy.name += " (优化版)"
        return strategy


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital: float = 100000.0, base_investment: float = 1000.0):
        self.initial_capital = initial_capital
        self.base_investment = base_investment
        
    def run_backtest(
        self,
        strategy: BaseStrategy,
        price_data: pd.DataFrame,
        strategy_version: str = "unknown"
    ) -> BacktestResult:
        """
        运行回测
        
        Args:
            strategy: 策略实例
            price_data: 价格数据DataFrame，需包含'nav'或'close'列
            strategy_version: 策略版本标识
            
        Returns:
            BacktestResult: 回测结果
        """
        # 初始化
        capital = self.initial_capital
        position = 0.0  # 持仓市值
        cash = capital  # 现金
        
        equity_curve = [capital]
        trades = []
        
        buy_count = 0
        sell_count = 0
        hold_count = 0
        
        nav_col = 'nav' if 'nav' in price_data.columns else 'close'
        prices = price_data[nav_col].values
        
        # 逐日回测
        for i in range(len(price_data)):
            current_price = prices[i]
            
            # 生成信号
            signal = strategy.generate_signal(
                price_data, 
                i,
                current_holdings=position,
                cash=cash
            )
            
            # 执行交易
            if signal.action == 'buy' and signal.amount_multiplier > 0:
                # 买入
                invest_amount = self.base_investment * signal.amount_multiplier
                invest_amount = min(invest_amount, cash)  # 不能超过现金
                
                if invest_amount > 0:
                    shares = invest_amount / current_price
                    position += invest_amount
                    cash -= invest_amount
                    
                    trades.append({
                        'day': i,
                        'action': 'buy',
                        'price': current_price,
                        'amount': invest_amount,
                        'shares': shares,
                        'reason': signal.reason
                    })
                    buy_count += 1
                    
            elif signal.action == 'sell' and position > 0:
                # 卖出
                sell_ratio = min(signal.amount_multiplier, 1.0)
                sell_value = position * sell_ratio
                
                if sell_value > 0:
                    position -= sell_value
                    cash += sell_value
                    
                    trades.append({
                        'day': i,
                        'action': 'sell',
                        'price': current_price,
                        'amount': sell_value,
                        'ratio': sell_ratio,
                        'reason': signal.reason
                    })
                    sell_count += 1
            else:
                hold_count += 1
            
            # 更新持仓市值（随价格变化）
            if position > 0 and i > 0:
                price_change = (current_price - prices[i-1]) / prices[i-1]
                position = position * (1 + price_change)
            
            # 记录资金曲线
            total_value = cash + position
            equity_curve.append(total_value)
        
        # 计算回测指标
        final_value = equity_curve[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital
        
        # 计算年化收益（假设250个交易日）
        n_days = len(price_data)
        annualized_return = (1 + total_return) ** (250 / n_days) - 1 if n_days > 0 else 0
        
        # 计算最大回撤
        max_drawdown = self._calculate_max_drawdown(equity_curve)
        
        # 计算波动率
        daily_returns = np.diff(equity_curve) / np.array(equity_curve[:-1])
        volatility = np.std(daily_returns) * np.sqrt(250)
        
        # 计算夏普比率（假设无风险利率3%）
        risk_free_rate = 0.03
        sharpe_ratio = (annualized_return - risk_free_rate) / (volatility + 1e-10)
        
        return BacktestResult(
            strategy_name=strategy.name,
            version=strategy_version,
            total_return=total_return,
            annualized_return=annualized_return,
            max_drawdown=max_drawdown,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            total_trades=len(trades),
            buy_signals=buy_count,
            sell_signals=sell_count,
            hold_signals=hold_count,
            equity_curve=equity_curve,
            trades=trades
        )
    
    @staticmethod
    def _calculate_max_drawdown(equity_curve: List[float]) -> float:
        """计算最大回撤"""
        peak = equity_curve[0]
        max_dd = 0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            max_dd = max(max_dd, dd)
        
        return max_dd


class ComparisonReport:
    """对比报告生成器"""
    
    @staticmethod
    def generate_report(
        original_result: BacktestResult,
        optimized_result: BacktestResult
    ) -> str:
        """生成对比报告"""
        report = []
        report.append("=" * 60)
        report.append("策略优化回测对比报告")
        report.append("=" * 60)
        report.append("")
        
        # 基本信息
        report.append(f"策略名称: {original_result.strategy_name}")
        report.append(f"回测天数: {len(original_result.equity_curve) - 1}")
        report.append("")
        
        # 对比表格
        report.append("-" * 60)
        report.append(f"{'指标':<20} {'原始策略':<20} {'优化策略':<20} {'提升':<10}")
        report.append("-" * 60)
        
        metrics = [
            ('总收益率', original_result.total_return, optimized_result.total_return, True),
            ('年化收益率', original_result.annualized_return, optimized_result.annualized_return, True),
            ('最大回撤', original_result.max_drawdown, optimized_result.max_drawdown, False),  # 越低越好
            ('波动率', original_result.volatility, optimized_result.volatility, False),
            ('夏普比率', original_result.sharpe_ratio, optimized_result.sharpe_ratio, True),
        ]
        
        for name, orig_val, opt_val, higher_is_better in metrics:
            if isinstance(orig_val, float):
                if name in ['总收益率', '年化收益率', '最大回撤', '波动率']:
                    orig_str = f"{orig_val:.2%}"
                    opt_str = f"{opt_val:.2%}"
                else:
                    orig_str = f"{orig_val:.2f}"
                    opt_str = f"{opt_val:.2f}"
                
                # 计算提升
                if higher_is_better:
                    improvement = (opt_val - orig_val) / (abs(orig_val) + 1e-10) * 100
                else:
                    improvement = (orig_val - opt_val) / (abs(orig_val) + 1e-10) * 100
                
                improvement_str = f"{improvement:+.1f}%"
                
                report.append(f"{name:<20} {orig_str:<20} {opt_str:<20} {improvement_str:<10}")
        
        report.append("-" * 60)
        report.append("")
        
        # 交易统计
        report.append("交易统计:")
        report.append(f"  原始策略 - 买入: {original_result.buy_signals}, 卖出: {original_result.sell_signals}, 持有: {original_result.hold_signals}")
        report.append(f"  优化策略 - 买入: {optimized_result.buy_signals}, 卖出: {optimized_result.sell_signals}, 持有: {optimized_result.hold_signals}")
        report.append("")
        
        # 总结
        report.append("=" * 60)
        report.append("优化效果总结:")
        
        # 自动判断优化效果
        return_improved = optimized_result.total_return > original_result.total_return
        risk_improved = optimized_result.max_drawdown < original_result.max_drawdown
        sharpe_improved = optimized_result.sharpe_ratio > original_result.sharpe_ratio
        
        improvements = []
        if return_improved:
            improvements.append("收益率提升")
        if risk_improved:
            improvements.append("风险降低")
        if sharpe_improved:
            improvements.append("夏普比率改善")
        
        if improvements:
            report.append(f"  [OK] {'、'.join(improvements)}")
        else:
            report.append("  [WARNING] 优化效果不明显，建议调整参数")
        
        report.append("=" * 60)
        
        return "\n".join(report)


def generate_test_data(trend_type: str = "mixed", n_days: int = 252) -> pd.DataFrame:
    """
    生成测试数据
    
    Args:
        trend_type: 趋势类型 ('uptrend', 'downtrend', 'sideways', 'mixed')
        n_days: 天数
    """
    np.random.seed(42)
    
    if trend_type == "uptrend":
        # 上涨趋势：正收益偏多
        returns = np.random.normal(0.001, 0.015, n_days)
        returns += 0.0005  # 正向漂移
    elif trend_type == "downtrend":
        # 下跌趋势：负收益偏多
        returns = np.random.normal(-0.001, 0.015, n_days)
        returns -= 0.0005  # 负向漂移
    elif trend_type == "sideways":
        # 横盘：无明显趋势
        returns = np.random.normal(0, 0.01, n_days)
    else:  # mixed
        # 混合：多种市场环境
        returns = []
        for i in range(n_days):
            if i < n_days // 3:
                # 第一段：上涨
                r = np.random.normal(0.001, 0.015)
            elif i < 2 * n_days // 3:
                # 第二段：下跌
                r = np.random.normal(-0.001, 0.02)
            else:
                # 第三段：震荡
                r = np.random.normal(0, 0.012)
            returns.append(r)
        returns = np.array(returns)
    
    # 生成价格序列
    price = 1.0
    prices = [price]
    for r in returns:
        price *= (1 + r)
        prices.append(price)
    
    df = pd.DataFrame({
        'nav': prices[1:],
        'return': returns
    })
    
    return df


def run_comparison():
    """运行对比测试"""
    print("\n开始策略优化回测对比...\n")
    
    # 生成测试数据
    test_data = generate_test_data("mixed", 252 * 2)  # 2年数据
    
    # 初始化回测引擎
    engine = BacktestEngine(initial_capital=100000, base_investment=1000)
    
    results = {}
    
    # 1. 均值回归策略对比
    print("1. 测试均值回归策略...")
    
    original_mr = StrategyOptimizer.get_original_mean_reversion()
    optimized_mr = StrategyOptimizer.get_optimized_mean_reversion()
    
    original_result = engine.run_backtest(original_mr, test_data, "original")
    optimized_result = engine.run_backtest(optimized_mr, test_data, "optimized")
    
    results['mean_reversion'] = (original_result, optimized_result)
    
    print(ComparisonReport.generate_report(original_result, optimized_result))
    
    # 2. 双均线策略对比（ADX优化前后）
    print("\n2. 测试双均线策略（ADX优化）...")
    
    # 这里可以添加ADX优化前后的对比
    dual_ma = DualMAStrategy(short_window=20, long_window=60)
    dual_ma_result = engine.run_backtest(dual_ma, test_data, "standard")
    
    print(f"\n双均线策略结果:")
    print(f"  总收益: {dual_ma_result.total_return:.2%}")
    print(f"  最大回撤: {dual_ma_result.max_drawdown:.2%}")
    print(f"  夏普比率: {dual_ma_result.sharpe_ratio:.2f}")
    
    # 3. 增强规则策略对比
    print("\n3. 测试增强规则策略...")
    
    enhanced = EnhancedRuleBasedStrategy()
    enhanced_result = engine.run_backtest(enhanced, test_data, "enhanced")
    
    print(f"\n增强规则策略结果:")
    print(f"  总收益: {enhanced_result.total_return:.2%}")
    print(f"  最大回撤: {enhanced_result.max_drawdown:.2%}")
    print(f"  夏普比率: {enhanced_result.sharpe_ratio:.2f}")
    
    # 4. 统一策略引擎测试（暂时跳过，需要解决导入问题）
    print("\n4. 统一策略引擎测试（已跳过，需要解决模块导入）")
    
    return results


if __name__ == "__main__":
    results = run_comparison()
    
    # 同时将报告保存到文件
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    # 重新生成报告并保存
    test_data = generate_test_data("mixed", 252 * 2)
    engine = BacktestEngine(initial_capital=100000, base_investment=1000)
    
    original_mr = StrategyOptimizer.get_original_mean_reversion()
    optimized_mr = StrategyOptimizer.get_optimized_mean_reversion()
    
    original_result = engine.run_backtest(original_mr, test_data, "original")
    optimized_result = engine.run_backtest(optimized_mr, test_data, "optimized")
    
    report = ComparisonReport.generate_report(original_result, optimized_result)
    
    with open('strategy_backtest_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\nReport saved to: strategy_backtest_report.txt")
