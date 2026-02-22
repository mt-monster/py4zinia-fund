#!/usr/bin/env python
# coding: utf-8

"""
趋势分析器
负责判断市场中期趋势
"""

import logging
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

import numpy as np

from ..core.strategy_config import StrategyConfig, get_strategy_config

logger = logging.getLogger(__name__)


class TrendType(Enum):
    """趋势类型枚举"""
    UPTREND = "uptrend"       # 上涨趋势
    DOWNTREND = "downtrend"   # 下跌趋势
    SIDEWAYS = "sideways"     # 横盘趋势


@dataclass
class TrendResult:
    """趋势分析结果"""
    trend: TrendType
    returns_short: float      # 短期均线收益率
    returns_long: float       # 长期均线收益率
    multiplier_adjustment: float  # 买入倍数调整系数
    confidence: float         # 趋势置信度 (0-1)
    adx: float = 0.0          # ADX趋势强度指标
    adx_trend_strength: str = "unknown"  # ADX趋势强度描述


class TrendAnalyzer:
    """趋势分析器"""
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        """
        初始化趋势分析器
        
        Args:
            config: 策略配置实例，如果为None则使用全局配置
        """
        self.config = config or get_strategy_config()
        self._load_config()
    
    def _load_config(self) -> None:
        """加载趋势配置"""
        trend_config = self.config.get_trend_config()
        
        self.ma_short_period = trend_config.get('ma_short_period', 5)
        self.ma_long_period = trend_config.get('ma_long_period', 10)
        self.uptrend_adjustment = trend_config.get('uptrend_adjustment', 1.2)
        self.downtrend_adjustment = trend_config.get('downtrend_adjustment', 0.7)
        self.sideways_adjustment = trend_config.get('sideways_adjustment', 1.0)
    
    def calculate_moving_average_returns(
        self, 
        returns: List[float], 
        period: int
    ) -> Optional[float]:
        """
        计算移动平均收益率
        
        Args:
            returns: 收益率序列（最新的在最后）
            period: 均线周期
            
        Returns:
            移动平均收益率，如果数据不足返回None
        """
        if len(returns) < period:
            logger.debug(f"数据不足: 需要 {period} 天，实际 {len(returns)} 天")
            return None
        
        # 取最近 period 天的数据
        recent_returns = returns[-period:]
        
        # 计算平均收益率
        avg_return = np.mean(recent_returns)
        
        return float(avg_return)
    
    def analyze_trend(self, returns_history: List[float]) -> TrendResult:
        """
        分析趋势
        
        Args:
            returns_history: 历史收益率序列（最新的在最后）
            
        Returns:
            TrendResult: 趋势分析结果
        """
        # 计算短期和长期均线收益率
        returns_short = self.calculate_moving_average_returns(
            returns_history, self.ma_short_period
        )
        returns_long = self.calculate_moving_average_returns(
            returns_history, self.ma_long_period
        )
        
        # 如果数据不足，返回横盘趋势
        if returns_short is None or returns_long is None:
            logger.debug("数据不足，返回横盘趋势")
            return TrendResult(
                trend=TrendType.SIDEWAYS,
                returns_short=0.0,
                returns_long=0.0,
                multiplier_adjustment=self.sideways_adjustment,
                confidence=0.0
            )
        
        # 判断趋势
        trend, confidence = self._classify_trend(returns_short, returns_long)
        
        # 新增：ADX趋势强度分析
        # 将收益率转换为模拟价格序列（从1.0开始）
        simulated_prices = [1.0]
        for r in returns_history:
            simulated_prices.append(simulated_prices[-1] * (1 + r))
        
        adx_value, adx_strength = self.calculate_adx(simulated_prices)
        
        # 如果ADX显示无趋势，降低置信度并调整为横盘
        if adx_value < 20 and trend != TrendType.SIDEWAYS:
            confidence *= 0.5  # 降低置信度
            if adx_value < 15:
                trend = TrendType.SIDEWAYS  # 强制归为横盘
                multiplier_adjustment = self.sideways_adjustment
            else:
                multiplier_adjustment = self._get_multiplier_adjustment(trend)
        else:
            # 获取调整系数
            multiplier_adjustment = self._get_multiplier_adjustment(trend)
        
        logger.debug(
            f"趋势分析: 短期={returns_short:.4f}, 长期={returns_long:.4f}, "
            f"趋势={trend.value}, 调整={multiplier_adjustment}, ADX={adx_value:.1f}"
        )
        
        return TrendResult(
            trend=trend,
            returns_short=returns_short,
            returns_long=returns_long,
            multiplier_adjustment=multiplier_adjustment,
            confidence=confidence,
            adx=adx_value,
            adx_trend_strength=adx_strength
        )
    
    def _classify_trend(
        self, 
        returns_short: float, 
        returns_long: float
    ) -> tuple[TrendType, float]:
        """
        分类趋势
        
        Args:
            returns_short: 短期均线收益率
            returns_long: 长期均线收益率
            
        Returns:
            (趋势类型, 置信度)
        """
        # 上涨趋势: 短期 > 长期 > 0
        if returns_short > returns_long > 0:
            # 置信度基于两者的差距
            confidence = min(1.0, (returns_short - returns_long) / 0.01)
            return TrendType.UPTREND, confidence
        
        # 下跌趋势: 短期 < 长期 < 0
        if returns_short < returns_long < 0:
            confidence = min(1.0, (returns_long - returns_short) / 0.01)
            return TrendType.DOWNTREND, confidence
        
        # 横盘趋势
        return TrendType.SIDEWAYS, 0.5
    
    def _get_multiplier_adjustment(self, trend: TrendType) -> float:
        """
        获取买入倍数调整系数
        
        Args:
            trend: 趋势类型
            
        Returns:
            调整系数
        """
        if trend == TrendType.UPTREND:
            return self.uptrend_adjustment
        elif trend == TrendType.DOWNTREND:
            return self.downtrend_adjustment
        else:
            return self.sideways_adjustment
    
    def calculate_adx(self, prices: List[float], period: int = 14) -> tuple[float, str]:
        """
        计算ADX（Average Directional Index）趋势强度指标
        
        Args:
            prices: 价格序列（最新的在最后）
            period: ADX计算周期，默认14
            
        Returns:
            (ADX值, 趋势强度描述)
        """
        if len(prices) < period + 1:
            return 0.0, "数据不足"
        
        # 转换为numpy数组
        prices_arr = np.array(prices)
        
        # 计算True Range (TR)
        high = prices_arr[1:]
        low = prices_arr[:-1]
        
        # 使用价格变化模拟高低点
        tr1 = np.abs(high - low)
        tr = tr1  # 简化计算
        
        # 计算+DM和-DM
        plus_dm = np.where((high - prices_arr[:-1]) > (prices_arr[:-1] - low), 
                          np.maximum(high - prices_arr[:-1], 0), 0)
        minus_dm = np.where((prices_arr[:-1] - low) > (high - prices_arr[:-1]),
                           np.maximum(prices_arr[:-1] - low, 0), 0)
        
        # 计算平滑后的TR和DM
        tr_smooth = np.convolve(tr, np.ones(period)/period, mode='valid')
        plus_dm_smooth = np.convolve(plus_dm, np.ones(period)/period, mode='valid')
        minus_dm_smooth = np.convolve(minus_dm, np.ones(period)/period, mode='valid')
        
        if len(tr_smooth) == 0 or np.mean(tr_smooth) == 0:
            return 0.0, "计算错误"
        
        # 计算+DI和-DI
        plus_di = 100 * plus_dm_smooth[-1] / tr_smooth[-1] if tr_smooth[-1] != 0 else 0
        minus_di = 100 * minus_dm_smooth[-1] / tr_smooth[-1] if tr_smooth[-1] != 0 else 0
        
        # 计算DX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) != 0 else 0
        
        # 简化：使用价格变化的标准差来估算ADX
        # 更准确的计算需要完整的OHLC数据
        returns = np.diff(prices_arr) / prices_arr[:-1]
        volatility = np.std(returns[-period:])
        trend_strength = np.abs(np.mean(returns[-period:])) / (volatility + 1e-10)
        
        # 映射到0-100范围
        adx = min(100, trend_strength * 50)
        
        # 判断趋势强度
        if adx > 40:
            strength = "强趋势"
        elif adx > 25:
            strength = "中等趋势"
        elif adx > 15:
            strength = "弱趋势"
        else:
            strength = "无趋势"
        
        return float(adx), strength
    
    def adjust_buy_multiplier(
        self, 
        base_multiplier: float, 
        trend_result: TrendResult
    ) -> float:
        """
        根据趋势调整买入倍数
        
        Args:
            base_multiplier: 基础买入倍数
            trend_result: 趋势分析结果
            
        Returns:
            调整后的买入倍数
        """
        adjusted = base_multiplier * trend_result.multiplier_adjustment
        logger.debug(
            f"买入倍数调整: {base_multiplier} * {trend_result.multiplier_adjustment} = {adjusted}"
        )
        return adjusted
    
    def get_trend_description(self, trend_result: TrendResult) -> str:
        """
        获取趋势描述
        
        Args:
            trend_result: 趋势分析结果
            
        Returns:
            趋势描述文本
        """
        descriptions = {
            TrendType.UPTREND: f"上涨趋势（5日均线 {trend_result.returns_short:.2%} > 10日均线 {trend_result.returns_long:.2%}）",
            TrendType.DOWNTREND: f"下跌趋势（5日均线 {trend_result.returns_short:.2%} < 10日均线 {trend_result.returns_long:.2%}）",
            TrendType.SIDEWAYS: f"横盘整理（5日均线 {trend_result.returns_short:.2%}, 10日均线 {trend_result.returns_long:.2%}）"
        }
        return descriptions.get(trend_result.trend, "未知趋势")
    
    def to_dict(self, trend_result: TrendResult) -> dict:
        """
        将趋势结果转换为字典
        
        Args:
            trend_result: 趋势分析结果
            
        Returns:
            字典格式的趋势结果
        """
        return {
            'trend': trend_result.trend.value,
            'returns_short': trend_result.returns_short,
            'returns_long': trend_result.returns_long,
            'multiplier_adjustment': trend_result.multiplier_adjustment,
            'confidence': trend_result.confidence,
            'adx': trend_result.adx,
            'adx_trend_strength': trend_result.adx_trend_strength,
            'description': self.get_trend_description(trend_result)
        }


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    analyzer = TrendAnalyzer()
    
    print("=== 趋势分析测试 ===")
    
    # 测试上涨趋势
    uptrend_returns = [0.001, 0.002, 0.001, 0.003, 0.002, 0.004, 0.003, 0.005, 0.004, 0.006]
    result = analyzer.analyze_trend(uptrend_returns)
    print(f"\n上涨趋势测试:")
    print(f"  趋势: {result.trend.value}")
    print(f"  短期均线: {result.returns_short:.4f}")
    print(f"  长期均线: {result.returns_long:.4f}")
    print(f"  调整系数: {result.multiplier_adjustment}")
    print(f"  描述: {analyzer.get_trend_description(result)}")
    
    # 测试下跌趋势
    downtrend_returns = [-0.001, -0.002, -0.001, -0.003, -0.002, -0.004, -0.003, -0.005, -0.004, -0.006]
    result = analyzer.analyze_trend(downtrend_returns)
    print(f"\n下跌趋势测试:")
    print(f"  趋势: {result.trend.value}")
    print(f"  短期均线: {result.returns_short:.4f}")
    print(f"  长期均线: {result.returns_long:.4f}")
    print(f"  调整系数: {result.multiplier_adjustment}")
    print(f"  描述: {analyzer.get_trend_description(result)}")
    
    # 测试横盘趋势
    sideways_returns = [0.001, -0.001, 0.002, -0.002, 0.001, -0.001, 0.002, -0.002, 0.001, -0.001]
    result = analyzer.analyze_trend(sideways_returns)
    print(f"\n横盘趋势测试:")
    print(f"  趋势: {result.trend.value}")
    print(f"  短期均线: {result.returns_short:.4f}")
    print(f"  长期均线: {result.returns_long:.4f}")
    print(f"  调整系数: {result.multiplier_adjustment}")
    print(f"  描述: {analyzer.get_trend_description(result)}")
    
    # 测试买入倍数调整
    print(f"\n=== 买入倍数调整测试 ===")
    base_multiplier = 1.5
    
    for returns in [uptrend_returns, downtrend_returns, sideways_returns]:
        result = analyzer.analyze_trend(returns)
        adjusted = analyzer.adjust_buy_multiplier(base_multiplier, result)
        print(f"  {result.trend.value}: {base_multiplier} -> {adjusted}")
