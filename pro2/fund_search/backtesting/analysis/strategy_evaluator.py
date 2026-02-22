#!/usr/bin/env python
# coding: utf-8

"""
策略评估器
负责评估投资策略的有效性
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """策略评估结果"""
    hit_rate: float                    # 命中率
    avg_profit_per_trade: float        # 平均每笔收益
    profit_factor: float               # 盈亏比
    max_consecutive_losses: int        # 最大连亏次数
    max_consecutive_wins: int          # 最大连赢次数
    win_loss_ratio: float              # 胜负比
    total_trades: int                  # 总交易次数
    winning_trades: int                # 盈利交易次数
    losing_trades: int                 # 亏损交易次数
    gross_profit: float                # 总盈利
    gross_loss: float                  # 总亏损
    net_profit: float                  # 净利润
    avg_win: float                     # 平均盈利
    avg_loss: float                    # 平均亏损
    largest_win: float                 # 最大单笔盈利
    largest_loss: float                # 最大单笔亏损
    expectancy: float                  # 期望值


class StrategyEvaluator:
    """策略评估器"""
    
    def __init__(self):
        """初始化策略评估器"""
        pass
    
    def calculate_hit_rate(self, predictions: List[Dict]) -> float:
        """
        计算命中率（正确预测 / 总预测）
        
        Args:
            predictions: 预测结果列表，每个元素包含 'predicted' 和 'actual' 字段
            
        Returns:
            命中率 (0-1)
        """
        if not predictions:
            return 0.0
        
        correct = sum(1 for p in predictions if p.get('predicted') == p.get('actual'))
        return correct / len(predictions)
    
    def calculate_avg_profit_per_trade(self, trades: List[Dict]) -> float:
        """
        计算平均每笔收益
        
        Args:
            trades: 交易记录列表，每个元素包含 'profit' 字段
            
        Returns:
            平均每笔收益
        """
        if not trades:
            return 0.0
        
        total_profit = sum(t.get('profit', 0) for t in trades)
        return total_profit / len(trades)
    
    def calculate_profit_factor(self, trades: List[Dict]) -> float:
        """
        计算盈亏比（总盈利 / 总亏损的绝对值）
        
        Args:
            trades: 交易记录列表，每个元素包含 'profit' 字段
            
        Returns:
            盈亏比，如果没有亏损返回 inf
        """
        if not trades:
            return 0.0
        
        gross_profit = sum(t.get('profit', 0) for t in trades if t.get('profit', 0) > 0)
        gross_loss = abs(sum(t.get('profit', 0) for t in trades if t.get('profit', 0) < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss
    
    def calculate_max_consecutive_losses(self, trades: List[Dict]) -> int:
        """
        计算最大连亏次数
        
        Args:
            trades: 交易记录列表，每个元素包含 'profit' 字段
            
        Returns:
            最大连亏次数
        """
        if not trades:
            return 0
        
        max_losses = 0
        current_losses = 0
        
        for trade in trades:
            if trade.get('profit', 0) < 0:
                current_losses += 1
                max_losses = max(max_losses, current_losses)
            else:
                current_losses = 0
        
        return max_losses
    
    def calculate_max_consecutive_wins(self, trades: List[Dict]) -> int:
        """
        计算最大连赢次数
        
        Args:
            trades: 交易记录列表，每个元素包含 'profit' 字段
            
        Returns:
            最大连赢次数
        """
        if not trades:
            return 0
        
        max_wins = 0
        current_wins = 0
        
        for trade in trades:
            if trade.get('profit', 0) > 0:
                current_wins += 1
                max_wins = max(max_wins, current_wins)
            else:
                current_wins = 0
        
        return max_wins
    
    def calculate_win_loss_ratio(self, trades: List[Dict]) -> float:
        """
        计算胜负比（盈利交易次数 / 亏损交易次数）
        
        Args:
            trades: 交易记录列表，每个元素包含 'profit' 字段
            
        Returns:
            胜负比
        """
        if not trades:
            return 0.0
        
        winning_trades = sum(1 for t in trades if t.get('profit', 0) > 0)
        losing_trades = sum(1 for t in trades if t.get('profit', 0) < 0)
        
        if losing_trades == 0:
            return float('inf') if winning_trades > 0 else 0.0
        
        return winning_trades / losing_trades
    
    def calculate_expectancy(self, trades: List[Dict]) -> float:
        """
        计算期望值
        期望值 = (胜率 × 平均盈利) - (败率 × 平均亏损)
        
        Args:
            trades: 交易记录列表
            
        Returns:
            期望值
        """
        if not trades:
            return 0.0
        
        winning_trades = [t for t in trades if t.get('profit', 0) > 0]
        losing_trades = [t for t in trades if t.get('profit', 0) < 0]
        
        total_trades = len(trades)
        
        if total_trades == 0:
            return 0.0
        
        win_rate = len(winning_trades) / total_trades
        loss_rate = len(losing_trades) / total_trades
        
        avg_win = np.mean([t.get('profit', 0) for t in winning_trades]) if winning_trades else 0
        avg_loss = abs(np.mean([t.get('profit', 0) for t in losing_trades])) if losing_trades else 0
        
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        
        return expectancy
    
    def evaluate(self, trades: List[Dict]) -> EvaluationResult:
        """
        综合评估策略
        
        Args:
            trades: 交易记录列表，每个元素包含 'profit' 字段
            
        Returns:
            EvaluationResult: 评估结果
        """
        if not trades:
            return EvaluationResult(
                hit_rate=0.0,
                avg_profit_per_trade=0.0,
                profit_factor=0.0,
                max_consecutive_losses=0,
                max_consecutive_wins=0,
                win_loss_ratio=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                gross_profit=0.0,
                gross_loss=0.0,
                net_profit=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                largest_win=0.0,
                largest_loss=0.0,
                expectancy=0.0
            )
        
        # 基础统计
        profits = [t.get('profit', 0) for t in trades]
        winning_profits = [p for p in profits if p > 0]
        losing_profits = [p for p in profits if p < 0]
        
        total_trades = len(trades)
        winning_trades = len(winning_profits)
        losing_trades = len(losing_profits)
        
        gross_profit = sum(winning_profits) if winning_profits else 0.0
        gross_loss = abs(sum(losing_profits)) if losing_profits else 0.0
        net_profit = gross_profit - gross_loss
        
        avg_win = np.mean(winning_profits) if winning_profits else 0.0
        avg_loss = abs(np.mean(losing_profits)) if losing_profits else 0.0
        
        largest_win = max(winning_profits) if winning_profits else 0.0
        largest_loss = abs(min(losing_profits)) if losing_profits else 0.0
        
        # 计算各项指标
        hit_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        return EvaluationResult(
            hit_rate=hit_rate,
            avg_profit_per_trade=self.calculate_avg_profit_per_trade(trades),
            profit_factor=self.calculate_profit_factor(trades),
            max_consecutive_losses=self.calculate_max_consecutive_losses(trades),
            max_consecutive_wins=self.calculate_max_consecutive_wins(trades),
            win_loss_ratio=self.calculate_win_loss_ratio(trades),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_profit=net_profit,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            expectancy=self.calculate_expectancy(trades)
        )
    
    def evaluate_from_returns(
        self, 
        returns: pd.Series,
        threshold: float = 0.0
    ) -> EvaluationResult:
        """
        从收益率序列评估策略
        
        Args:
            returns: 收益率序列
            threshold: 盈亏阈值，默认为0
            
        Returns:
            EvaluationResult: 评估结果
        """
        trades = [{'profit': r} for r in returns]
        return self.evaluate(trades)
    
    def to_dict(self, result: EvaluationResult) -> Dict:
        """
        将评估结果转换为字典
        
        Args:
            result: 评估结果
            
        Returns:
            字典格式的评估结果
        """
        return {
            'hit_rate': result.hit_rate,
            'avg_profit_per_trade': result.avg_profit_per_trade,
            'profit_factor': result.profit_factor,
            'max_consecutive_losses': result.max_consecutive_losses,
            'max_consecutive_wins': result.max_consecutive_wins,
            'win_loss_ratio': result.win_loss_ratio,
            'total_trades': result.total_trades,
            'winning_trades': result.winning_trades,
            'losing_trades': result.losing_trades,
            'gross_profit': result.gross_profit,
            'gross_loss': result.gross_loss,
            'net_profit': result.net_profit,
            'avg_win': result.avg_win,
            'avg_loss': result.avg_loss,
            'largest_win': result.largest_win,
            'largest_loss': result.largest_loss,
            'expectancy': result.expectancy
        }
    
    def generate_report(self, result: EvaluationResult) -> str:
        """
        生成评估报告
        
        Args:
            result: 评估结果
            
        Returns:
            报告文本
        """
        report = f"""
=== 策略评估报告 ===

【交易统计】
总交易次数: {result.total_trades}
盈利交易: {result.winning_trades} ({result.hit_rate:.1%})
亏损交易: {result.losing_trades} ({1-result.hit_rate:.1%})

【盈亏分析】
总盈利: ¥{result.gross_profit:.2f}
总亏损: ¥{result.gross_loss:.2f}
净利润: ¥{result.net_profit:.2f}

【平均收益】
平均每笔收益: ¥{result.avg_profit_per_trade:.2f}
平均盈利: ¥{result.avg_win:.2f}
平均亏损: ¥{result.avg_loss:.2f}

【极值】
最大单笔盈利: ¥{result.largest_win:.2f}
最大单笔亏损: ¥{result.largest_loss:.2f}

【连续性】
最大连赢: {result.max_consecutive_wins} 次
最大连亏: {result.max_consecutive_losses} 次

【风险指标】
盈亏比: {result.profit_factor:.2f}
胜负比: {result.win_loss_ratio:.2f}
期望值: ¥{result.expectancy:.2f}
"""
        return report


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    evaluator = StrategyEvaluator()
    
    # 模拟交易数据
    trades = [
        {'profit': 100},
        {'profit': -50},
        {'profit': 80},
        {'profit': -30},
        {'profit': 120},
        {'profit': -40},
        {'profit': -20},
        {'profit': -10},
        {'profit': 150},
        {'profit': 90},
        {'profit': -60},
        {'profit': 70},
    ]
    
    print("=== 单项指标测试 ===")
    print(f"平均每笔收益: {evaluator.calculate_avg_profit_per_trade(trades):.2f}")
    print(f"盈亏比: {evaluator.calculate_profit_factor(trades):.2f}")
    print(f"最大连亏: {evaluator.calculate_max_consecutive_losses(trades)}")
    print(f"最大连赢: {evaluator.calculate_max_consecutive_wins(trades)}")
    print(f"胜负比: {evaluator.calculate_win_loss_ratio(trades):.2f}")
    print(f"期望值: {evaluator.calculate_expectancy(trades):.2f}")
    
    print("\n=== 综合评估 ===")
    result = evaluator.evaluate(trades)
    print(evaluator.generate_report(result))
    
    print("\n=== 从收益率评估 ===")
    returns = pd.Series([0.01, -0.005, 0.008, -0.003, 0.012, -0.004, -0.002, -0.001, 0.015, 0.009])
    result = evaluator.evaluate_from_returns(returns)
    print(f"命中率: {result.hit_rate:.1%}")
    print(f"盈亏比: {result.profit_factor:.2f}")
