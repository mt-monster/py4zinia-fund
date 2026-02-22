#!/usr/bin/env python
# coding: utf-8

"""
仓位管理器
负责根据市场状态动态调整投资仓位
"""

import logging
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

import numpy as np

from .strategy_config import StrategyConfig, get_strategy_config

logger = logging.getLogger(__name__)


class VolatilityLevel(Enum):
    """波动率级别枚举"""
    HIGH = "high"       # 高波动
    NORMAL = "normal"   # 正常波动
    LOW = "low"         # 低波动


@dataclass
class PositionAdjustment:
    """仓位调整结果"""
    volatility: float
    volatility_level: VolatilityLevel
    adjustment_factor: float
    adjusted_multiplier: float
    original_multiplier: float


class PositionManager:
    """仓位管理器"""
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        """
        初始化仓位管理器
        
        Args:
            config: 策略配置实例，如果为None则使用全局配置
        """
        self.config = config or get_strategy_config()
        self._load_config()
    
    def _load_config(self) -> None:
        """加载波动率配置"""
        volatility_config = self.config.get_volatility_config()
        
        self.high_threshold = volatility_config.get('high_threshold', 0.25)
        self.low_threshold = volatility_config.get('low_threshold', 0.10)
        self.high_adjustment = volatility_config.get('high_adjustment', 0.5)
        self.low_adjustment = volatility_config.get('low_adjustment', 1.2)
        self.normal_adjustment = volatility_config.get('normal_adjustment', 1.0)
        self.lookback_days = volatility_config.get('lookback_days', 20)
    
    def calculate_volatility(self, returns: List[float]) -> Optional[float]:
        """
        计算波动率（年化标准差）
        
        Args:
            returns: 日收益率序列
            
        Returns:
            年化波动率，如果数据不足返回None
        """
        if len(returns) < 2:
            logger.debug("数据不足，无法计算波动率")
            return None
        
        # 使用最近 lookback_days 天的数据
        recent_returns = returns[-self.lookback_days:] if len(returns) >= self.lookback_days else returns
        
        # 计算日波动率（标准差）
        daily_volatility = np.std(recent_returns, ddof=1)
        
        # 年化波动率 = 日波动率 * sqrt(252)
        annual_volatility = daily_volatility * np.sqrt(252)
        
        logger.debug(f"波动率计算: 日波动率={daily_volatility:.4f}, 年化波动率={annual_volatility:.4f}")
        
        return float(annual_volatility)
    
    def classify_volatility(self, volatility: float) -> VolatilityLevel:
        """
        分类波动率级别
        
        Args:
            volatility: 年化波动率
            
        Returns:
            波动率级别
        """
        if volatility > self.high_threshold:
            return VolatilityLevel.HIGH
        elif volatility < self.low_threshold:
            return VolatilityLevel.LOW
        else:
            return VolatilityLevel.NORMAL
    
    def get_position_adjustment(self, volatility: float) -> float:
        """
        获取仓位调整系数
        
        Args:
            volatility: 年化波动率
            
        Returns:
            仓位调整系数 (0.5 ~ 1.2)
        """
        level = self.classify_volatility(volatility)
        
        if level == VolatilityLevel.HIGH:
            return self.high_adjustment
        elif level == VolatilityLevel.LOW:
            return self.low_adjustment
        else:
            return self.normal_adjustment
    
    def adjust_buy_multiplier(
        self, 
        base_multiplier: float, 
        volatility: float
    ) -> PositionAdjustment:
        """
        根据波动率调整买入倍数
        
        Args:
            base_multiplier: 基础买入倍数
            volatility: 年化波动率
            
        Returns:
            PositionAdjustment: 仓位调整结果
        """
        level = self.classify_volatility(volatility)
        adjustment_factor = self.get_position_adjustment(volatility)
        adjusted_multiplier = base_multiplier * adjustment_factor
        
        logger.debug(
            f"仓位调整: 波动率={volatility:.2%}, 级别={level.value}, "
            f"调整系数={adjustment_factor}, 倍数={base_multiplier} -> {adjusted_multiplier}"
        )
        
        return PositionAdjustment(
            volatility=volatility,
            volatility_level=level,
            adjustment_factor=adjustment_factor,
            adjusted_multiplier=adjusted_multiplier,
            original_multiplier=base_multiplier
        )
    
    def adjust_from_returns(
        self, 
        base_multiplier: float, 
        returns: List[float]
    ) -> PositionAdjustment:
        """
        根据收益率序列调整买入倍数
        
        Args:
            base_multiplier: 基础买入倍数
            returns: 日收益率序列
            
        Returns:
            PositionAdjustment: 仓位调整结果
        """
        volatility = self.calculate_volatility(returns)
        
        if volatility is None:
            # 数据不足，返回无调整
            return PositionAdjustment(
                volatility=0.0,
                volatility_level=VolatilityLevel.NORMAL,
                adjustment_factor=1.0,
                adjusted_multiplier=base_multiplier,
                original_multiplier=base_multiplier
            )
        
        return self.adjust_buy_multiplier(base_multiplier, volatility)
    
    def get_volatility_description(self, adjustment: PositionAdjustment) -> str:
        """
        获取波动率描述
        
        Args:
            adjustment: 仓位调整结果
            
        Returns:
            波动率描述文本
        """
        descriptions = {
            VolatilityLevel.HIGH: f"高波动（{adjustment.volatility:.1%}），仓位减少{(1-adjustment.adjustment_factor)*100:.0f}%",
            VolatilityLevel.LOW: f"低波动（{adjustment.volatility:.1%}），仓位增加{(adjustment.adjustment_factor-1)*100:.0f}%",
            VolatilityLevel.NORMAL: f"正常波动（{adjustment.volatility:.1%}），仓位不变"
        }
        return descriptions.get(adjustment.volatility_level, "未知波动率")
    
    def to_dict(self, adjustment: PositionAdjustment) -> dict:
        """
        将仓位调整结果转换为字典
        
        Args:
            adjustment: 仓位调整结果
            
        Returns:
            字典格式的仓位调整结果
        """
        return {
            'volatility': adjustment.volatility,
            'volatility_level': adjustment.volatility_level.value,
            'adjustment_factor': adjustment.adjustment_factor,
            'adjusted_multiplier': adjustment.adjusted_multiplier,
            'original_multiplier': adjustment.original_multiplier,
            'description': self.get_volatility_description(adjustment)
        }
    
    def calculate_position_size(
        self,
        base_amount: float,
        buy_multiplier: float,
        returns: List[float]
    ) -> dict:
        """
        计算最终仓位大小
        
        Args:
            base_amount: 基准定投金额
            buy_multiplier: 策略买入倍数
            returns: 日收益率序列
            
        Returns:
            仓位计算结果字典
        """
        adjustment = self.adjust_from_returns(buy_multiplier, returns)
        
        final_amount = base_amount * adjustment.adjusted_multiplier
        
        return {
            'base_amount': base_amount,
            'strategy_multiplier': buy_multiplier,
            'volatility_adjustment': adjustment.adjustment_factor,
            'final_multiplier': adjustment.adjusted_multiplier,
            'final_amount': final_amount,
            'volatility': adjustment.volatility,
            'volatility_level': adjustment.volatility_level.value
        }


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    manager = PositionManager()
    
    print("=== 波动率分类测试 ===")
    
    # 测试不同波动率级别
    test_volatilities = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40]
    
    for vol in test_volatilities:
        level = manager.classify_volatility(vol)
        adjustment = manager.get_position_adjustment(vol)
        print(f"波动率: {vol:.0%} -> 级别: {level.value}, 调整系数: {adjustment}")
    
    print("\n=== 仓位调整测试 ===")
    
    base_multiplier = 1.5
    
    for vol in test_volatilities:
        result = manager.adjust_buy_multiplier(base_multiplier, vol)
        print(f"波动率: {vol:.0%} -> {result.original_multiplier} * {result.adjustment_factor} = {result.adjusted_multiplier}")
        print(f"  描述: {manager.get_volatility_description(result)}")
    
    print("\n=== 从收益率计算波动率测试 ===")
    
    # 模拟高波动收益率
    high_vol_returns = [0.02, -0.03, 0.04, -0.02, 0.03, -0.04, 0.02, -0.03, 0.04, -0.02]
    result = manager.adjust_from_returns(base_multiplier, high_vol_returns)
    print(f"高波动收益率:")
    print(f"  波动率: {result.volatility:.2%}")
    print(f"  级别: {result.volatility_level.value}")
    print(f"  调整: {result.original_multiplier} -> {result.adjusted_multiplier}")
    
    # 模拟低波动收益率
    low_vol_returns = [0.001, 0.002, 0.001, 0.002, 0.001, 0.002, 0.001, 0.002, 0.001, 0.002]
    result = manager.adjust_from_returns(base_multiplier, low_vol_returns)
    print(f"\n低波动收益率:")
    print(f"  波动率: {result.volatility:.2%}")
    print(f"  级别: {result.volatility_level.value}")
    print(f"  调整: {result.original_multiplier} -> {result.adjusted_multiplier}")
    
    print("\n=== 完整仓位计算测试 ===")
    
    base_amount = 100
    position = manager.calculate_position_size(base_amount, base_multiplier, high_vol_returns)
    print(f"高波动场景:")
    print(f"  基准金额: ¥{position['base_amount']}")
    print(f"  策略倍数: {position['strategy_multiplier']}")
    print(f"  波动率调整: {position['volatility_adjustment']}")
    print(f"  最终倍数: {position['final_multiplier']}")
    print(f"  最终金额: ¥{position['final_amount']:.2f}")
