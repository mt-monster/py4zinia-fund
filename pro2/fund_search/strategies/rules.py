#!/usr/bin/env python
# coding: utf-8

"""
投资策略规则模块

将原有的投资策略逻辑从 enhanced_main.py 中提取出来，实现策略与执行的分离。
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum


class ActionType(Enum):
    """操作类型枚举"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    WEAK_BUY = "weak_buy"


@dataclass
class StrategyResult:
    """策略结果数据类"""
    status_label: str
    action: ActionType
    is_buy: bool
    redeem_amount: float
    comparison_value: float
    operation_suggestion: str
    execution_amount: str
    buy_multiplier: float


class InvestmentStrategyRules:
    """
    投资策略规则类
    
    基于当日和昨日收益率生成投资建议。
    包含16种不同的市场状态判断逻辑。
    """
    
    # 买入倍数配置
    MULTIPLIERS = {
        'strong_buy': 2.0,
        'buy': 1.5,
        'weak_buy': 1.0,
        'hold': 0.0,
        'small_buy': 0.5
    }
    
    # 赎回金额配置
    REDEEM_AMOUNTS = {
        'small': 15,
        'medium': 30,
        'large': 50,
        'none': 0
    }
    
    @classmethod
    def get_investment_strategy(cls, today_return: float, prev_day_return: float) -> StrategyResult:
        """
        根据当日和昨日收益率，返回投资策略结果
        
        参数：
            today_return: 当日收益率（%）
            prev_day_return: 昨日收益率（%）
            
        返回：
            StrategyResult: 策略结果对象
        """
        return_diff = today_return - prev_day_return
        
        # 情况1-4: 今日>0 昨日>0
        if today_return > 0 and prev_day_return > 0:
            return cls._handle_both_positive(today_return, prev_day_return, return_diff)
        
        # 情况5: 今日>0 昨日≤0
        elif today_return > 0 and prev_day_return <= 0:
            return cls._handle_today_positive(today_return, prev_day_return, return_diff)
        
        # 情况6: 今日=0 昨日>0
        elif today_return == 0 and prev_day_return > 0:
            return cls._handle_today_zero_positive_prev(today_return, prev_day_return, return_diff)
        
        # 情况7: 今日<0 昨日>0
        elif today_return < 0 and prev_day_return > 0:
            return cls._handle_today_negative_positive_prev(today_return, prev_day_return, return_diff)
        
        # 情况8: 今日=0 昨日≤0
        elif today_return == 0 and prev_day_return <= 0:
            return cls._handle_today_zero_negative_prev(today_return, prev_day_return, return_diff)
        
        # 情况9-11: 今日<0 昨日=0
        elif today_return < 0 and prev_day_return == 0:
            return cls._handle_prev_zero(today_return, prev_day_return, return_diff)
        
        # 情况12-16: 今日<0 昨日<0
        elif today_return < 0 and prev_day_return < 0:
            return cls._handle_both_negative(today_return, prev_day_return, return_diff)
        
        # 默认情况
        return cls._create_result(
            status_label="🔴 下跌",
            action=ActionType.BUY,
            is_buy=True,
            redeem_amount=0,
            comparison_value=return_diff,
            operation_suggestion="定投买入，不赎回",
            execution_amount=f"买入{cls.MULTIPLIERS['weak_buy']}×定额",
            buy_multiplier=cls.MULTIPLIERS['weak_buy']
        )
    
    @classmethod
    def _handle_both_positive(cls, today_return: float, prev_day_return: float, 
                              return_diff: float) -> StrategyResult:
        """处理今日>0 昨日>0的情况"""
        
        # 情况1: today-prev > 1%
        if return_diff > 1:
            return cls._create_result(
                status_label="🟢 大涨",
                action=ActionType.HOLD,
                is_buy=False,
                redeem_amount=cls.REDEEM_AMOUNTS['none'],
                comparison_value=return_diff,
                operation_suggestion="不买入，不赎回",
                execution_amount="持有不动",
                buy_multiplier=cls.MULTIPLIERS['hold']
            )
        
        # 情况2: 0 < today-prev ≤ 1%
        elif 0 < return_diff <= 1:
            return cls._create_result(
                status_label="🟡 连涨",
                action=ActionType.SELL,
                is_buy=False,
                redeem_amount=cls.REDEEM_AMOUNTS['small'],
                comparison_value=return_diff,
                operation_suggestion="不买入，赎回15元",
                execution_amount="赎回¥15",
                buy_multiplier=cls.MULTIPLIERS['hold']
            )
        
        # 情况3: -1% ≤ today-prev ≤ 0
        elif -1 <= return_diff <= 0:
            return cls._create_result(
                status_label="🟠 连涨放缓",
                action=ActionType.HOLD,
                is_buy=False,
                redeem_amount=cls.REDEEM_AMOUNTS['none'],
                comparison_value=return_diff,
                operation_suggestion="不买入，不赎回",
                execution_amount="持有不动",
                buy_multiplier=cls.MULTIPLIERS['hold']
            )
        
        # 情况4: today-prev < -1%
        else:  # return_diff < -1
            return cls._create_result(
                status_label="🟠 连涨回落",
                action=ActionType.HOLD,
                is_buy=False,
                redeem_amount=cls.REDEEM_AMOUNTS['none'],
                comparison_value=return_diff,
                operation_suggestion="不买入，不赎回",
                execution_amount="持有不动",
                buy_multiplier=cls.MULTIPLIERS['hold']
            )
    
    @classmethod
    def _handle_today_positive(cls, today_return: float, prev_day_return: float,
                               return_diff: float) -> StrategyResult:
        """处理今日>0 昨日≤0的情况"""
        return cls._create_result(
            status_label="🔵 反转涨",
            action=ActionType.BUY,
            is_buy=True,
            redeem_amount=cls.REDEEM_AMOUNTS['none'],
            comparison_value=return_diff,
            operation_suggestion="定投买入，不赎回",
            execution_amount=f"买入{cls.MULTIPLIERS['buy']}×定额",
            buy_multiplier=cls.MULTIPLIERS['buy']
        )
    
    @classmethod
    def _handle_today_zero_positive_prev(cls, today_return: float, prev_day_return: float,
                                          return_diff: float) -> StrategyResult:
        """处理今日=0 昨日>0的情况"""
        return cls._create_result(
            status_label="🔴 转势休整",
            action=ActionType.SELL,
            is_buy=False,
            redeem_amount=cls.REDEEM_AMOUNTS['medium'],
            comparison_value=return_diff,
            operation_suggestion="不买入，赎回30元",
            execution_amount="赎回¥30",
            buy_multiplier=cls.MULTIPLIERS['hold']
        )
    
    @classmethod
    def _handle_today_negative_positive_prev(cls, today_return: float, prev_day_return: float,
                                              return_diff: float) -> StrategyResult:
        """处理今日<0 昨日>0的情况"""
        return cls._create_result(
            status_label="🔴 反转跌",
            action=ActionType.SELL,
            is_buy=False,
            redeem_amount=cls.REDEEM_AMOUNTS['medium'],
            comparison_value=return_diff,
            operation_suggestion="不买入，赎回30元",
            execution_amount="赎回¥30",
            buy_multiplier=cls.MULTIPLIERS['hold']
        )
    
    @classmethod
    def _handle_today_zero_negative_prev(cls, today_return: float, prev_day_return: float,
                                          return_diff: float) -> StrategyResult:
        """处理今日=0 昨日≤0的情况"""
        return cls._create_result(
            status_label="⚪ 持平",
            action=ActionType.BUY,
            is_buy=True,
            redeem_amount=cls.REDEEM_AMOUNTS['none'],
            comparison_value=return_diff,
            operation_suggestion="定投买入，不赎回",
            execution_amount=f"买入{cls.MULTIPLIERS['strong_buy']}×定额",
            buy_multiplier=cls.MULTIPLIERS['strong_buy']
        )
    
    @classmethod
    def _handle_prev_zero(cls, today_return: float, prev_day_return: float,
                          return_diff: float) -> StrategyResult:
        """处理今日<0 昨日=0的情况"""
        
        # 情况9: today ≤ -2%
        if today_return <= -2:
            return cls._create_result(
                status_label="🔴 首次大跌",
                action=ActionType.BUY,
                is_buy=True,
                redeem_amount=cls.REDEEM_AMOUNTS['none'],
                comparison_value=return_diff,
                operation_suggestion="定投买入，不赎回",
                execution_amount=f"买入{cls.MULTIPLIERS['small_buy']}×定额",
                buy_multiplier=cls.MULTIPLIERS['small_buy']
            )
        
        # 情况10: -2% < today ≤ -0.5%
        elif -2 < today_return <= -0.5:
            return cls._create_result(
                status_label="🟠 首次下跌",
                action=ActionType.BUY,
                is_buy=True,
                redeem_amount=cls.REDEEM_AMOUNTS['none'],
                comparison_value=return_diff,
                operation_suggestion="定投买入，不赎回",
                execution_amount=f"买入{cls.MULTIPLIERS['buy']}×定额",
                buy_multiplier=cls.MULTIPLIERS['buy']
            )
        
        # 情况11: today > -0.5%
        else:  # today_return > -0.5
            return cls._create_result(
                status_label="🔵 微跌试探",
                action=ActionType.BUY,
                is_buy=True,
                redeem_amount=cls.REDEEM_AMOUNTS['none'],
                comparison_value=return_diff,
                operation_suggestion="定投买入，不赎回",
                execution_amount=f"买入{cls.MULTIPLIERS['weak_buy']}×定额",
                buy_multiplier=cls.MULTIPLIERS['weak_buy']
            )
    
    @classmethod
    def _handle_both_negative(cls, today_return: float, prev_day_return: float,
                              return_diff: float) -> StrategyResult:
        """处理今日<0 昨日<0的情况"""
        prev_minus_today = prev_day_return - today_return
        
        # 情况12: (today-prev) > 1% & today ≤ -2%
        if return_diff > 1 and today_return <= -2:
            return cls._create_result(
                status_label="🔴 暴跌加速",
                action=ActionType.BUY,
                is_buy=True,
                redeem_amount=cls.REDEEM_AMOUNTS['none'],
                comparison_value=return_diff,
                operation_suggestion="定投买入，不赎回",
                execution_amount=f"买入{cls.MULTIPLIERS['small_buy']}×定额",
                buy_multiplier=cls.MULTIPLIERS['small_buy']
            )
        
        # 情况13: (today-prev) > 1% & today > -2%
        elif return_diff > 1 and today_return > -2:
            return cls._create_result(
                status_label="🟣 跌速扩大",
                action=ActionType.BUY,
                is_buy=True,
                redeem_amount=cls.REDEEM_AMOUNTS['none'],
                comparison_value=return_diff,
                operation_suggestion="定投买入，不赎回",
                execution_amount=f"买入{cls.MULTIPLIERS['weak_buy']}×定额",
                buy_multiplier=cls.MULTIPLIERS['weak_buy']
            )
        
        # 情况14: (prev-today) > 0 & prev ≤ -2%
        elif prev_minus_today > 0 and prev_day_return <= -2:
            return cls._create_result(
                status_label="🔵 暴跌回升",
                action=ActionType.BUY,
                is_buy=True,
                redeem_amount=cls.REDEEM_AMOUNTS['none'],
                comparison_value=return_diff,
                operation_suggestion="定投买入，不赎回",
                execution_amount=f"买入{cls.MULTIPLIERS['buy']}×定额",
                buy_multiplier=cls.MULTIPLIERS['buy']
            )
        
        # 情况15: (prev-today) > 0 & prev > -2%
        elif prev_minus_today > 0 and prev_day_return > -2:
            return cls._create_result(
                status_label="🟦 跌速放缓",
                action=ActionType.BUY,
                is_buy=True,
                redeem_amount=cls.REDEEM_AMOUNTS['none'],
                comparison_value=return_diff,
                operation_suggestion="定投买入，不赎回",
                execution_amount=f"买入{cls.MULTIPLIERS['weak_buy']}×定额",
                buy_multiplier=cls.MULTIPLIERS['weak_buy']
            )
        
        # 情况16: abs(差值) ≤ 1%
        else:  # abs(return_diff) <= 1
            return cls._create_result(
                status_label="🟣 阴跌筑底",
                action=ActionType.BUY,
                is_buy=True,
                redeem_amount=cls.REDEEM_AMOUNTS['none'],
                comparison_value=return_diff,
                operation_suggestion="定投买入，不赎回",
                execution_amount=f"买入{cls.MULTIPLIERS['weak_buy']}×定额",
                buy_multiplier=cls.MULTIPLIERS['weak_buy']
            )
    
    @classmethod
    def _create_result(cls, status_label: str, action: ActionType, is_buy: bool,
                       redeem_amount: float, comparison_value: float,
                       operation_suggestion: str, execution_amount: str,
                       buy_multiplier: float) -> StrategyResult:
        """创建策略结果对象"""
        return StrategyResult(
            status_label=status_label,
            action=action,
            is_buy=is_buy,
            redeem_amount=redeem_amount,
            comparison_value=comparison_value,
            operation_suggestion=operation_suggestion,
            execution_amount=execution_amount,
            buy_multiplier=buy_multiplier
        )
