#!/usr/bin/env python
# coding: utf-8

"""
止损管理器
负责监控和触发止损规则
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

from .strategy_config import StrategyConfig, get_strategy_config

logger = logging.getLogger(__name__)


class StopLossLevel(Enum):
    """止损级别枚举"""
    NONE = "none"           # 无止损
    WARNING = "warning"     # 警告
    STOP_LOSS = "stop_loss" # 止损触发


@dataclass
class StopLossResult:
    """止损检查结果"""
    triggered: bool
    level: StopLossLevel
    action: str
    label: str
    suggestion: str
    cumulative_loss: float


class StopLossManager:
    """止损管理器"""
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        """
        初始化止损管理器
        
        Args:
            config: 策略配置实例，如果为None则使用全局配置
        """
        self.config = config or get_strategy_config()
        self._position_pnl: Dict[str, float] = {}  # 持仓盈亏跟踪
        self._load_thresholds()
    
    def _load_thresholds(self) -> None:
        """加载止损阈值配置"""
        stop_loss_config = self.config.get_stop_loss_config()
        
        self.warning_threshold = stop_loss_config.get('warning_threshold', -0.10)
        self.stop_loss_threshold = stop_loss_config.get('stop_loss_threshold', -0.15)
        self.full_redeem = stop_loss_config.get('full_redeem', True)
        self.stop_loss_label = stop_loss_config.get('stop_loss_label', "🛑 **止损触发**")
        self.warning_label = stop_loss_config.get('warning_label', "⚠️ **亏损警告**")
        self.stop_loss_suggestion = stop_loss_config.get(
            'stop_loss_suggestion', 
            "累计亏损超过阈值，建议全部赎回止损"
        )
        self.warning_suggestion = stop_loss_config.get(
            'warning_suggestion',
            "累计亏损接近止损线，请密切关注"
        )
    
    def check_stop_loss(self, cumulative_loss: float) -> StopLossResult:
        """
        检查是否触发止损
        
        Args:
            cumulative_loss: 累计亏损率（负数表示亏损，如 -0.15 表示亏损15%）
            
        Returns:
            StopLossResult: 止损检查结果
        """
        # 检查止损触发
        if cumulative_loss <= self.stop_loss_threshold:
            logger.warning(f"止损触发: 累计亏损 {cumulative_loss:.2%} 超过阈值 {self.stop_loss_threshold:.2%}")
            return StopLossResult(
                triggered=True,
                level=StopLossLevel.STOP_LOSS,
                action='stop_loss',
                label=self.stop_loss_label,
                suggestion=self.stop_loss_suggestion,
                cumulative_loss=cumulative_loss
            )
        
        # 检查警告触发
        if cumulative_loss <= self.warning_threshold:
            logger.info(f"亏损警告: 累计亏损 {cumulative_loss:.2%} 超过警告阈值 {self.warning_threshold:.2%}")
            return StopLossResult(
                triggered=False,
                level=StopLossLevel.WARNING,
                action='warning',
                label=self.warning_label,
                suggestion=self.warning_suggestion,
                cumulative_loss=cumulative_loss
            )
        
        # 无止损
        return StopLossResult(
            triggered=False,
            level=StopLossLevel.NONE,
            action='none',
            label='',
            suggestion='',
            cumulative_loss=cumulative_loss
        )
    
    def update_position_pnl(self, fund_code: str, pnl: float) -> None:
        """
        更新持仓盈亏
        
        Args:
            fund_code: 基金代码
            pnl: 累计盈亏率（负数表示亏损）
        """
        self._position_pnl[fund_code] = pnl
        logger.debug(f"更新持仓盈亏: {fund_code} = {pnl:.2%}")
    
    def get_position_pnl(self, fund_code: str) -> Optional[float]:
        """
        获取持仓累计盈亏
        
        Args:
            fund_code: 基金代码
            
        Returns:
            累计盈亏率，如果不存在返回None
        """
        return self._position_pnl.get(fund_code)
    
    def check_position_stop_loss(self, fund_code: str) -> StopLossResult:
        """
        检查指定持仓是否触发止损
        
        Args:
            fund_code: 基金代码
            
        Returns:
            StopLossResult: 止损检查结果
        """
        pnl = self.get_position_pnl(fund_code)
        
        if pnl is None:
            return StopLossResult(
                triggered=False,
                level=StopLossLevel.NONE,
                action='none',
                label='',
                suggestion='无持仓数据',
                cumulative_loss=0.0
            )
        
        return self.check_stop_loss(pnl)
    
    def get_all_stop_loss_positions(self) -> Dict[str, StopLossResult]:
        """
        获取所有触发止损的持仓
        
        Returns:
            触发止损的持仓字典 {fund_code: StopLossResult}
        """
        stop_loss_positions = {}
        
        for fund_code, pnl in self._position_pnl.items():
            result = self.check_stop_loss(pnl)
            if result.level != StopLossLevel.NONE:
                stop_loss_positions[fund_code] = result
        
        return stop_loss_positions
    
    def clear_position(self, fund_code: str) -> None:
        """
        清除持仓记录
        
        Args:
            fund_code: 基金代码
        """
        if fund_code in self._position_pnl:
            del self._position_pnl[fund_code]
            logger.debug(f"清除持仓记录: {fund_code}")
    
    def clear_all_positions(self) -> None:
        """清除所有持仓记录"""
        self._position_pnl.clear()
        logger.debug("清除所有持仓记录")
    
    def get_redeem_action(self, stop_loss_result: StopLossResult) -> Dict:
        """
        获取止损赎回操作
        
        Args:
            stop_loss_result: 止损检查结果
            
        Returns:
            赎回操作字典
        """
        if stop_loss_result.level == StopLossLevel.STOP_LOSS and self.full_redeem:
            return {
                'action': 'full_redeem',
                'redeem_percentage': 1.0,
                'label': self.stop_loss_label,
                'suggestion': self.stop_loss_suggestion
            }
        
        return {
            'action': 'none',
            'redeem_percentage': 0.0,
            'label': '',
            'suggestion': ''
        }
    
    def to_dict(self, stop_loss_result: StopLossResult) -> Dict:
        """
        将止损结果转换为字典
        
        Args:
            stop_loss_result: 止损检查结果
            
        Returns:
            字典格式的止损结果
        """
        return {
            'triggered': stop_loss_result.triggered,
            'level': stop_loss_result.level.value,
            'action': stop_loss_result.action,
            'label': stop_loss_result.label,
            'suggestion': stop_loss_result.suggestion,
            'cumulative_loss': stop_loss_result.cumulative_loss
        }


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    manager = StopLossManager()
    
    print("=== 止损检查测试 ===")
    
    # 测试不同亏损级别
    test_cases = [
        0.05,    # 盈利5%
        -0.05,   # 亏损5%
        -0.10,   # 亏损10% (警告)
        -0.12,   # 亏损12% (警告)
        -0.15,   # 亏损15% (止损)
        -0.20,   # 亏损20% (止损)
    ]
    
    for loss in test_cases:
        result = manager.check_stop_loss(loss)
        print(f"累计盈亏: {loss:+.2%} -> 级别: {result.level.value}, 触发: {result.triggered}")
        if result.label:
            print(f"  标签: {result.label}")
            print(f"  建议: {result.suggestion}")
    
    print("\n=== 持仓跟踪测试 ===")
    
    # 更新持仓盈亏
    manager.update_position_pnl("000001", -0.08)
    manager.update_position_pnl("000002", -0.12)
    manager.update_position_pnl("000003", -0.18)
    
    # 获取所有触发止损的持仓
    stop_loss_positions = manager.get_all_stop_loss_positions()
    print(f"触发止损/警告的持仓数: {len(stop_loss_positions)}")
    
    for fund_code, result in stop_loss_positions.items():
        print(f"  {fund_code}: {result.level.value} ({result.cumulative_loss:.2%})")
