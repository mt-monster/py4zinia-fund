#!/usr/bin/env python
# coding: utf-8

"""
策略适配器
为旧的回测引擎提供统一策略引擎的适配接口
"""

import logging
from typing import List, Optional, Tuple

from .unified_strategy_engine import UnifiedStrategyEngine, UnifiedStrategyResult

logger = logging.getLogger(__name__)


class StrategyAdapter:
    """
    策略适配器
    
    将 UnifiedStrategyEngine 的接口适配为旧的 get_investment_strategy 接口格式，
    以便与现有的回测引擎兼容。
    """
    
    def __init__(self, base_amount: float = 100):
        """
        初始化策略适配器
        
        Args:
            base_amount: 基准定投金额
        """
        self.base_amount = base_amount
        self.engine = UnifiedStrategyEngine()
        self._returns_history: List[float] = []
        self._cumulative_pnl: float = 0.0
    
    def get_investment_strategy(
        self, 
        today_return: float, 
        prev_day_return: float
    ) -> Tuple[str, bool, float, float, str, float, float]:
        """
        获取投资策略建议（兼容旧接口）
        
        Args:
            today_return: 当日收益率（小数形式，如0.01表示1%）
            prev_day_return: 前一日收益率（小数形式）
            
        Returns:
            tuple: 包含7个元素
                status_label: str, 策略状态标签
                is_buy: bool, 是否买入标志
                redeem_amount: float, 赎回金额
                comparison_value: float, 用于策略决策的比较值
                operation_suggestion: str, 操作建议文本
                execution_amount: float, 执行金额（正为买入，负为赎回）
                buy_multiplier: float, 买入乘数
        """
        # 更新历史收益率
        self._returns_history.append(today_return)
        if len(self._returns_history) > 20:
            self._returns_history = self._returns_history[-20:]
        
        # 转换为百分比形式（统一策略引擎使用百分比）
        today_pct = today_return * 100
        prev_pct = prev_day_return * 100
        
        # 调用统一策略引擎
        result = self.engine.analyze(
            today_return=today_pct,
            prev_day_return=prev_pct,
            returns_history=self._returns_history if len(self._returns_history) >= 10 else None,
            cumulative_pnl=self._cumulative_pnl if self._cumulative_pnl != 0 else None
        )
        
        # 转换为旧接口格式
        return self._convert_result(result)
    
    def _convert_result(
        self, 
        result: UnifiedStrategyResult
    ) -> Tuple[str, bool, float, float, str, float, float]:
        """
        将统一策略结果转换为旧接口格式
        
        Args:
            result: UnifiedStrategyResult
            
        Returns:
            旧接口格式的元组
        """
        # 判断是否买入
        is_buy = result.action in ['strong_buy', 'buy', 'weak_buy']
        
        # 计算执行金额
        if is_buy:
            execution_amount = self.base_amount * result.final_buy_multiplier
        elif result.action in ['sell', 'weak_sell', 'stop_loss']:
            execution_amount = -result.redeem_amount
        else:
            execution_amount = 0
        
        # 生成操作建议
        if is_buy:
            operation_suggestion = f"定投金额 {execution_amount:.0f} 元"
        elif result.redeem_amount > 0:
            operation_suggestion = f"赎回 {result.redeem_amount:.0f} 元"
        else:
            operation_suggestion = "持有不动"
        
        # 提取状态标签（去除 markdown 格式）
        status_label = result.status_label.replace('**', '').replace('🟢 ', '').replace('🟡 ', '')
        status_label = status_label.replace('🟠 ', '').replace('🔵 ', '').replace('🔴 ', '')
        status_label = status_label.replace('⚪ ', '').replace('🟣 ', '').replace('🟦 ', '')
        status_label = status_label.replace('🛑 ', '').strip()
        
        return (
            status_label,
            is_buy,
            result.redeem_amount,
            0.0,  # comparison_value
            operation_suggestion,
            execution_amount,
            result.final_buy_multiplier
        )
    
    def update_cumulative_pnl(self, pnl: float) -> None:
        """
        更新累计盈亏
        
        Args:
            pnl: 累计盈亏率
        """
        self._cumulative_pnl = pnl
    
    def reset(self) -> None:
        """重置适配器状态"""
        self._returns_history = []
        self._cumulative_pnl = 0.0
    
    def get_full_analysis(
        self,
        today_return: float,
        prev_day_return: float,
        returns_history: Optional[List[float]] = None,
        cumulative_pnl: Optional[float] = None
    ) -> UnifiedStrategyResult:
        """
        获取完整的策略分析结果
        
        Args:
            today_return: 当日收益率（小数形式）
            prev_day_return: 前一日收益率（小数形式）
            returns_history: 历史收益率序列
            cumulative_pnl: 累计盈亏率
            
        Returns:
            UnifiedStrategyResult: 完整的策略分析结果
        """
        # 转换为百分比形式
        today_pct = today_return * 100
        prev_pct = prev_day_return * 100
        
        return self.engine.analyze(
            today_return=today_pct,
            prev_day_return=prev_pct,
            returns_history=returns_history,
            cumulative_pnl=cumulative_pnl
        )


# 创建全局适配器实例的工厂函数
def create_strategy_adapter(base_amount: float = 100) -> StrategyAdapter:
    """
    创建策略适配器实例
    
    Args:
        base_amount: 基准定投金额
        
    Returns:
        StrategyAdapter 实例
    """
    return StrategyAdapter(base_amount)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    adapter = StrategyAdapter(base_amount=100)
    
    print("=== 策略适配器测试 ===")
    
    # 测试各种情况
    test_cases = [
        (0.025, 0.012, "强势上涨"),
        (0.008, 0.006, "持续上涨"),
        (0.001, 0.008, "上涨放缓"),
        (0.012, -0.005, "反转上涨"),
        (-0.008, 0.008, "反转下跌"),
        (-0.025, 0.0005, "首次大跌"),
    ]
    
    for today, prev, desc in test_cases:
        result = adapter.get_investment_strategy(today, prev)
        status_label, is_buy, redeem_amount, _, operation_suggestion, execution_amount, buy_multiplier = result
        
        print(f"\n{desc}: 今日={today*100:.1f}%, 昨日={prev*100:.1f}%")
        print(f"  状态: {status_label}")
        print(f"  买入: {is_buy}")
        print(f"  倍数: {buy_multiplier:.1f}")
        print(f"  建议: {operation_suggestion}")
    
    print("\n=== 完整分析测试 ===")
    
    # 模拟历史数据
    history = [0.001, 0.002, 0.001, 0.003, 0.002, 0.004, 0.003, 0.005, 0.004, 0.006]
    
    full_result = adapter.get_full_analysis(
        today_return=0.008,
        prev_day_return=0.006,
        returns_history=history,
        cumulative_pnl=-0.05
    )
    
    print(f"策略: {full_result.strategy_name}")
    print(f"趋势: {full_result.trend}")
    print(f"波动率: {full_result.volatility:.1%}")
    print(f"最终倍数: {full_result.final_buy_multiplier:.2f}")
    print(f"建议: {full_result.final_suggestion}")
