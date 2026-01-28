#!/usr/bin/env python
# coding: utf-8

"""
策略适配器模块
Strategy Adapter Module

将UI展示的策略ID映射到实际的策略实现，解决策略定义不匹配的问题。
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StrategySignal:
    """统一的策略信号格式"""
    action: str  # 'buy', 'sell', 'hold'
    buy_multiplier: float = 0.0  # 买入倍数
    redeem_amount: float = 0.0  # 赎回金额
    reason: str = ""
    description: str = ""


class StrategyAdapter:
    """
    策略适配器
    
    将UI策略ID（dual_ma, mean_reversion等）映射到实际的策略实现。
    提供统一的接口供回测引擎调用。
    """
    
    def __init__(self):
        """初始化策略适配器"""
        self.strategies = {}
        self._init_strategies()
        logger.info("策略适配器初始化完成")
    
    def _init_strategies(self):
        """初始化所有策略"""
        try:
            from .advanced_strategies import (
                DualMAStrategy,
                MeanReversionStrategy,
                TargetValueStrategy,
                GridTradingStrategy,
                EnhancedRuleBasedStrategy
            )
            
            self.strategies = {
                'dual_ma': DualMAStrategy(short_window=20, long_window=60),
                'mean_reversion': MeanReversionStrategy(window=250, threshold=0.05),
                'target_value': TargetValueStrategy(target_growth_per_period=1000),
                'grid': GridTradingStrategy(grid_size=0.03),
                'enhanced_rule_based': EnhancedRuleBasedStrategy()
            }
            
            logger.info(f"已加载 {len(self.strategies)} 个策略")
            
        except Exception as e:
            logger.error(f"初始化策略失败: {str(e)}")
            raise
    
    def get_available_strategies(self) -> list:
        """获取可用的策略列表"""
        return list(self.strategies.keys())
    
    def is_advanced_strategy(self, strategy_id: str) -> bool:
        """
        判断是否为高级策略（需要使用advanced_strategies实现）
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            bool: True表示是高级策略，False表示使用unified_strategy_engine
        """
        return strategy_id in self.strategies
    
    def generate_signal(
        self,
        strategy_id: str,
        history_df: pd.DataFrame,
        current_index: int,
        current_holdings: float = 0,
        cash: float = 0,
        base_invest: float = 100
    ) -> StrategySignal:
        """
        生成策略信号
        
        Args:
            strategy_id: 策略ID
            history_df: 历史数据DataFrame（必须包含'nav'列）
            current_index: 当前索引
            current_holdings: 当前持仓市值
            cash: 当前现金
            base_invest: 基准定投金额
            
        Returns:
            StrategySignal: 统一的策略信号
        """
        if strategy_id not in self.strategies:
            raise ValueError(f"未知的策略ID: {strategy_id}")
        
        strategy = self.strategies[strategy_id]
        
        try:
            # 调用策略的generate_signal方法
            signal = strategy.generate_signal(
                history_df=history_df,
                current_index=current_index,
                current_holdings=current_holdings,
                cash=cash
            )
            
            # 转换为统一格式
            unified_signal = self._convert_to_unified_signal(signal, base_invest)
            
            logger.debug(f"策略 {strategy_id} 生成信号: {unified_signal.action}, "
                        f"买入倍数: {unified_signal.buy_multiplier}, "
                        f"赎回金额: {unified_signal.redeem_amount}")
            
            return unified_signal
            
        except Exception as e:
            logger.error(f"策略 {strategy_id} 生成信号失败: {str(e)}")
            # 返回默认信号（持有）
            return StrategySignal(
                action='hold',
                buy_multiplier=0.0,
                redeem_amount=0.0,
                reason="策略执行失败",
                description=str(e)
            )
    
    def _convert_to_unified_signal(self, signal, base_invest: float) -> StrategySignal:
        """
        将策略信号转换为统一格式
        
        Args:
            signal: 原始策略信号
            base_invest: 基准定投金额
            
        Returns:
            StrategySignal: 统一格式的信号
        """
        action = signal.action
        buy_multiplier = 0.0
        redeem_amount = 0.0
        
        if action == 'buy':
            # 买入信号：使用amount_multiplier作为买入倍数
            buy_multiplier = signal.amount_multiplier
        elif action == 'sell':
            # 卖出信号：转换为赎回金额
            # signal.amount_multiplier在卖出时表示卖出的金额或比例
            if hasattr(signal, 'amount_multiplier'):
                # 如果是比例（0-1之间），转换为实际金额
                if 0 < signal.amount_multiplier <= 1:
                    redeem_amount = signal.amount_multiplier  # 作为比例
                else:
                    # 如果是绝对金额
                    redeem_amount = signal.amount_multiplier
            else:
                # 默认卖出10%
                redeem_amount = 0.1
        
        return StrategySignal(
            action=action,
            buy_multiplier=buy_multiplier,
            redeem_amount=redeem_amount,
            reason=signal.reason,
            description=signal.description
        )


# 全局单例
_strategy_adapter: Optional[StrategyAdapter] = None


def get_strategy_adapter() -> StrategyAdapter:
    """
    获取策略适配器单例
    
    Returns:
        StrategyAdapter: 策略适配器实例
    """
    global _strategy_adapter
    if _strategy_adapter is None:
        _strategy_adapter = StrategyAdapter()
    return _strategy_adapter


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    print("=== 测试策略适配器 ===\n")
    
    adapter = StrategyAdapter()
    
    print(f"可用策略: {adapter.get_available_strategies()}\n")
    
    # 创建测试数据
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    navs = np.cumsum(np.random.randn(100) * 0.01) + 1.0  # 模拟净值走势
    test_df = pd.DataFrame({'date': dates, 'nav': navs})
    
    print("=== 测试各策略信号生成 ===\n")
    
    for strategy_id in ['dual_ma', 'mean_reversion', 'target_value', 'grid']:
        print(f"\n策略: {strategy_id}")
        try:
            signal = adapter.generate_signal(
                strategy_id=strategy_id,
                history_df=test_df,
                current_index=80,
                current_holdings=10000,
                cash=5000,
                base_invest=100
            )
            print(f"  操作: {signal.action}")
            print(f"  买入倍数: {signal.buy_multiplier}")
            print(f"  赎回金额: {signal.redeem_amount}")
            print(f"  原因: {signal.reason}")
        except Exception as e:
            print(f"  错误: {str(e)}")
    
    print("\n=== 测试完成 ===")
