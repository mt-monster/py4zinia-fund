#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高级基金定投策略库
Advanced Fund Investment Strategies

提供多种经典的基金定投和交易策略实现，包括动量、均值回归、网格交易等。
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class StrategySignal:
    """策略信号"""
    action: str  # 'buy', 'sell', 'hold'
    amount_multiplier: float = 1.0  # 基础金额的倍数
    reason: str = ""
    description: str = ""
    suggestion: str = ""
    
    # 兼容性属性，用于策略适配器
    @property
    def buy_multiplier(self):
        """买入倍数（兼容性属性）"""
        if self.action == 'buy':
            return self.amount_multiplier
        return 0.0
    
    @property
    def redeem_amount(self):
        """赎回金额/比例（兼容性属性）"""
        if self.action == 'sell':
            return self.amount_multiplier
        return 0.0

class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    def generate_signal(self, 
                       history_df: pd.DataFrame, 
                       current_index: int,
                       current_holdings: float = 0,
                       cash: float = 0) -> StrategySignal:
        """
        生成交易信号
        
        Args:
            history_df: 历史数据DataFrame (必须包含 'nav' 或 '单位净值' 列)
            current_index: 当前交易日的索引
            current_holdings: 当前持仓市值
            cash: 当前可用现金
            
        Returns:
            StrategySignal: 交易信号对象
        """
        pass
    
    def _get_nav(self, df: pd.DataFrame) -> pd.Series:
        """获取净值序列"""
        if '单位净值' in df.columns:
            return df['单位净值']
        elif 'nav' in df.columns:
            return df['nav']
        elif 'close' in df.columns:
            return df['close']
        elif 'current_estimate' in df.columns:
            return df['current_estimate']
        elif 'yesterday_nav' in df.columns:
            return df['yesterday_nav']
        else:
            # 尝试使用第一个数值列
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                return df[numeric_cols[0]]
            raise ValueError("DataFrame必须包含 '单位净值', 'nav', 'close', 'current_estimate' 或 'yesterday_nav' 列")

# 1. 双均线动量策略 (Trend Following)
class DualMAStrategy(BaseStrategy):
    """
    双均线动量策略
    
    逻辑：
    - 短期均线(如20日) > 长期均线(如60日) -> 金叉，趋势向上 -> 加大定投或买入
    - 短期均线 < 长期均线 -> 死叉，趋势向下 -> 减少定投或卖出/持有
    - 归类：趋势跟踪 / 动量策略
    """
    
    def __init__(self, short_window: int = 20, long_window: int = 60):
        super().__init__(
            name="双均线动量策略", 
            description=f"基于{short_window}日和{long_window}日均线交叉判断趋势"
        )
        self.short_window = short_window
        self.long_window = long_window
        
    def generate_signal(self, history_df: pd.DataFrame, current_index: int, **kwargs) -> StrategySignal:
        # 需要足够的数据计算均线
        if current_index < self.long_window:
            return StrategySignal('hold', 1.0, "数据不足，累积期")
            
        nav = self._get_nav(history_df)
        
        # 计算截至当天的均线（注意不要用到未来数据，这里假设history_df切片到current_index是安全的，或者在计算时只取到current_index）
        # 为提高效率，实际回测中应预先计算好MA，这里为了独立性实时计算切片
        subset = nav.iloc[current_index - self.long_window : current_index + 1]
        
        ma_short = subset.iloc[-self.short_window:].mean()
        ma_long = subset.mean()
        
        current_nav = nav.iloc[current_index]
        
        # 判断金叉/死叉状态
        if ma_short > ma_long:
            # 趋势向上，判断是刚形成的突破还是持续
            # 简单的逻辑：金叉状态下倍投
            return StrategySignal('buy', 1.5, "金叉趋势中", "短期均线位于长期均线上方，趋势看涨")
        else:
            # 趋势向下，减少定投或暂停
            return StrategySignal('buy', 0.5, "死叉趋势中", "短期均线位于长期均线下方，趋势看跌，减少投入")

# 2. 均值回归定投策略 (Mean Reversion)
class MeanReversionStrategy(BaseStrategy):
    """
    均值回归定投策略 (智能定投)
    
    逻辑：
    - 价格低于均线一定幅度 -> 低估 -> 大额买入
    - 价格高于均线一定幅度 -> 高估 -> 减少买入或卖出
    - 归类：均值回归 / 逆向投资
    """
    
    def __init__(self, window: int = 250, threshold: float = 0.05):
        super().__init__(
            name="均值回归智能定投", 
            description=f"基于{window}日均线偏离度，偏离{threshold*100}%时调整仓位"
        )
        self.window = window
        self.threshold = threshold
        
    def generate_signal(self, history_df: pd.DataFrame, current_index: int, **kwargs) -> StrategySignal:
        if current_index < self.window:
            return StrategySignal('buy', 1.0, "累积期")
            
        nav = self._get_nav(history_df)
        subset = nav.iloc[current_index - self.window : current_index + 1]
        ma = subset.mean()
        current_price = nav.iloc[current_index]
        
        # 计算偏离度
        deviation = (current_price - ma) / ma
        
        # 新增：趋势过滤器 - 避免在强趋势中错误操作
        if current_index >= 60:
            ma_short = nav.iloc[current_index-20:current_index+1].mean()
            ma_long = nav.iloc[current_index-60:current_index+1].mean()
            
            # 强上涨趋势中，暂停均值回归卖出（让利润奔跑）
            if ma_short > ma_long * 1.05 and deviation > 0:
                return StrategySignal('hold', 0.0, "强上涨趋势", "趋势强劲，暂停止盈，让利润奔跑")
            
            # 强下跌趋势中，暂停均值回归买入（避免接飞刀）
            if ma_short < ma_long * 0.95 and deviation < -self.threshold:
                return StrategySignal('hold', 0.0, "强下跌趋势", "下跌趋势未止，暂停抄底")
        
        if deviation < -self.threshold * 2:
            # 极度低估 (例如低于均线10%)
            return StrategySignal('buy', 2.0, "极度低估", f"当前价格低于均线 {abs(deviation)*100:.1f}%")
        elif deviation < -self.threshold:
            # 低估
            return StrategySignal('buy', 1.5, "低估区域", f"当前价格低于均线 {abs(deviation)*100:.1f}%")
        elif deviation > self.threshold * 2:
            # 极度高估 - 修正：从0.5改为1.0（清仓）
            return StrategySignal('sell', 1.0, "极度高估", f"当前价格高于均线 {deviation*100:.1f}%", "建议全部止盈")
        elif deviation > self.threshold:
            # 高估 - 修正：从买入改为卖出
            return StrategySignal('sell', 0.5, "高估区域", f"当前价格高于均线 {deviation*100:.1f}%", "建议部分止盈")
        else:
            # 正常区域
            return StrategySignal('buy', 1.0, "正常区域", "价格在均线附近波动")

# 3. 目标市值策略 (Value Averaging)
class TargetValueStrategy(BaseStrategy):
    """
    目标市值策略 (Value Averaging)
    
    逻辑：
    - 设定每月/每期目标资产增长额（如每月增加1000元）
    - 应买金额 = 目标市值 - 当前市值
    - 如果市值自然增长超过目标，则买入更少甚至卖出
    - 归类：成本平均 / 动态平衡
    """
    
    def __init__(self, target_growth_per_period: float = 1000.0):
        super().__init__(
            name="目标市值策略", 
            description=f"每期目标资产增加{target_growth_per_period}元"
        )
        self.target_growth = target_growth_per_period
        self.total_periods = 0
        
    def generate_signal(self, history_df: pd.DataFrame, current_index: int, current_holdings: float = 0, **kwargs) -> StrategySignal:
        self.total_periods += 1
        target_value = self.total_periods * self.target_growth
        
        diff = target_value - current_holdings
        
        if diff > 0:
            # 需要买入
            multiplier = diff / self.target_growth  # 相对于基准定投额的倍数
            return StrategySignal('buy', multiplier, "市值低于目标", f"目标市值{target_value}，当前{current_holdings}，需补足{diff}")
        elif diff < 0:
            # 市值超标，可以选择持有或卖出
            # 这里保守策略是卖出超额部分，或者仅停止买入
            return StrategySignal('sell', abs(diff), "市值超标", f"目标市值{target_value}，当前{current_holdings}，超出{abs(diff)}")
        else:
            return StrategySignal('hold', 0, "市值达标")

# 4. 网格交易策略 (Grid Trading)
class GridTradingStrategy(BaseStrategy):
    """
    动态网格交易策略
    
    逻辑：
    - 基于近期波动率设定网格密度
    - 价格下跌突破网格线买入
    - 价格上涨突破网格线卖出
    - 归类：波动率策略 / 震荡套利
    """
    
    def __init__(self, grid_size: float = 0.03):
        super().__init__(
            name="网格交易策略", 
            description=f"网格大小 {grid_size*100}%"
        )
        self.grid_size = grid_size
        self.last_trade_price = None
        
    def generate_signal(self, history_df: pd.DataFrame, current_index: int, **kwargs) -> StrategySignal:
        nav = self._get_nav(history_df)
        current_price = nav.iloc[current_index]
        
        if self.last_trade_price is None:
            self.last_trade_price = current_price
            return StrategySignal('buy', 1.0, "建仓", "初始建仓")
            
        change = (current_price - self.last_trade_price) / self.last_trade_price
        
        if change <= -self.grid_size:
            # 下跌超过一个网格 -> 买入一份
            self.last_trade_price = current_price
            return StrategySignal('buy', 1.0, "网格买入", f"下跌 {change*100:.2f}% 触发买入")
        elif change >= self.grid_size:
            # 上涨超过一个网格 -> 卖出一份
            self.last_trade_price = current_price
            return StrategySignal('sell', 1.0, "网格卖出", f"上涨 {change*100:.2f}% 触发卖出")
        else:
            return StrategySignal('hold', 0, "网格内波动", f"当前波动 {change*100:.2f}% 未触发网格")


# 5. 增强规则基准策略 (Enhanced Rule-Based Strategy)
class EnhancedRuleBasedStrategy(BaseStrategy):
    """
    增强规则基准策略
    
    逻辑：
    - 基于今日和昨日收益率的组合判断市场状态
    - 10种市场状态：强势突破、持续上涨、反转上涨、反转下跌、首次大跌等
    - 上涨时持有（让利润奔跑），下跌时补仓（摊低成本）
    - 包含止损机制
    """
    
    def __init__(self):
        super().__init__(
            name="增强规则基准策略", 
            description="基于涨跌幅规则的综合策略，上涨持有，下跌补仓"
        )
        
        # 定义策略规则（基于strategy_config.yaml的逻辑）
        self.rules = [
            # 1. 强势突破 - 上涨时持有
            {
                'name': 'strong_bull',
                'label': '🟢 强势突破',
                'conditions': [
                    {'today_min': 1.0, 'today_max': float('inf'), 'prev_min': 0.5, 'prev_max': float('inf')},
                    {'today_min': 0.5, 'today_max': float('inf'), 'prev_min': 1.0, 'prev_max': float('inf')}
                ],
                'action': 'hold',
                'multiplier': 0.0,
                'description': '基金强势上涨，建议持有不动（让利润奔跑）'
            },
            # 2. 持续上涨 - 上涨时持有
            {
                'name': 'bull_continuation',
                'label': '🟡 连涨加速',
                'conditions': [
                    {'today_min': 0.3, 'today_max': 1.0, 'prev_min': 0.3, 'prev_max': 1.0},
                    {'today_min': 0.2, 'today_max': 0.5, 'prev_min': 0.5, 'prev_max': 1.0}
                ],
                'action': 'hold',
                'multiplier': 0.0,
                'description': '基金持续上涨，建议持有不动（让利润奔跑）'
            },
            # 3. 上涨放缓 - 持有观望
            {
                'name': 'bull_slowing',
                'label': '🟠 连涨放缓',
                'conditions': [
                    {'today_min': 0.0, 'today_max': 0.3, 'prev_min': 0.3, 'prev_max': float('inf')},
                    {'today_min': -0.3, 'today_max': 0.0, 'prev_min': 0.5, 'prev_max': float('inf')}
                ],
                'action': 'hold',
                'multiplier': 0.0,
                'description': '上涨势头放缓，建议持有观望'
            },
            # 4. 反转上涨 - 持有观望
            {
                'name': 'bull_reversal',
                'label': '🔵 反转上涨',
                'conditions': [
                    {'today_min': 0.3, 'today_max': float('inf'), 'prev_min': float('-inf'), 'prev_max': 0.0}
                ],
                'action': 'hold',
                'multiplier': 0.0,
                'description': '基金由跌转涨，建议持有观望（确认趋势）'
            },
            # 5. 反转下跌 - 止盈
            {
                'name': 'bear_reversal',
                'label': '🔴 反转下跌',
                'conditions': [
                    {'today_min': float('-inf'), 'today_max': 0.0, 'prev_min': 0.3, 'prev_max': float('inf')}
                ],
                'action': 'sell',
                'multiplier': 0.08,  # 赎回8%
                'description': '基金由涨转跌，建议止盈（赎回8%仓位）'
            },
            # 6. 绝对企稳 - 买入
            {
                'name': 'absolute_bottom',
                'label': '⚪ 绝对企稳',
                'conditions': [
                    {'today_min': 0.0, 'today_max': 0.01, 'prev_min': -0.3, 'prev_max': 0.0}
                ],
                'action': 'buy',
                'multiplier': 1.8,
                'description': '基金企稳，建议买入（抄底机会）'
            },
            # 7. 首次大跌 - 积极买入
            {
                'name': 'first_major_drop',
                'label': '🔴 首次大跌',
                'conditions': [
                    {'today_min': float('-inf'), 'today_max': -2.0, 'prev_min': -0.1, 'prev_max': 0.1}
                ],
                'action': 'buy',
                'multiplier': 2.5,
                'description': '基金首次大跌，建议积极买入（抄底良机）'
            },
            # 8. 持续下跌 - 买入补仓（优化：更严格的条件）
            {
                'name': 'bear_continuation',
                'label': '🟣 持续下跌',
                'conditions': [
                    # 原条件：连续2日下跌各超过0.5%
                    # 新条件A：连续2日且累计跌幅>2%
                    # 新条件B：单日大跌超过2%
                    {'today_min': float('-inf'), 'today_max': -1.0, 'prev_min': float('-inf'), 'prev_max': -1.0},  # 两日各跌1%+
                    {'today_min': float('-inf'), 'today_max': -2.0, 'prev_min': float('-inf'), 'prev_max': float('inf')}  # 单日大跌2%+
                ],
                'action': 'buy',
                'multiplier': 1.5,
                'description': '基金持续下跌（两日累计跌2%+ 或 单日大跌2%+），建议逢低买入（摊低成本）'
            },
            # 9. 跌速放缓 - 积极买入
            {
                'name': 'bear_slowing',
                'label': '🟦 跌速放缓',
                'conditions': [
                    {'today_min': -0.5, 'today_max': 0.0, 'prev_min': float('-inf'), 'prev_max': -1.0}
                ],
                'action': 'buy',
                'multiplier': 2.0,
                'description': '下跌速度放缓，建议积极买入（抄底机会）'
            }
        ]
        
        # 止损配置
        self.stop_loss_threshold = -0.12  # 累计亏损12%触发止损
        self.warning_threshold = -0.08    # 累计亏损8%触发警告
    
    def generate_signal(self, history_df: pd.DataFrame, current_index: int, 
                       current_holdings: float = 0, cash: float = 0, **kwargs) -> StrategySignal:
        """生成交易信号"""
        
        # 需要至少2天数据
        if current_index < 1:
            return StrategySignal('hold', 0.0, "数据不足", "累积期")
        
        nav = self._get_nav(history_df)
        
        # 计算收益率
        current_nav = nav.iloc[current_index]
        prev_nav = nav.iloc[current_index - 1]
        
        if current_index >= 2:
            prev2_nav = nav.iloc[current_index - 2]
            prev_day_return = (prev_nav - prev2_nav) / prev2_nav * 100
        else:
            prev_day_return = 0.0
        
        today_return = (current_nav - prev_nav) / prev_nav * 100
        
        # 新增：计算累计跌幅用于持续下跌判定
        cumulative_decline = today_return + prev_day_return
        
        # 优化：更严格的持续下跌判定
        # 如果累计跌幅超过2%，标记为急跌
        if cumulative_decline < -2.0 and today_return < -0.5:
            # 优先匹配"持续下跌"规则（需要检查是否在规则列表中）
            for rule in self.rules:
                if rule['name'] == 'bear_continuation':
                    # 检查是否符合单日大跌条件
                    if today_return <= -2.0 or (today_return <= -1.0 and prev_day_return <= -1.0):
                        return StrategySignal(
                            rule['action'], 
                            rule['multiplier'],
                            rule['label'],
                            f"累计跌幅{cumulative_decline:.1f}%，{rule['description']}"
                        )
        
        # 检查止损
        if current_holdings > 0:
            initial_amount = kwargs.get('initial_amount', 10000)
            cumulative_pnl = (current_holdings + cash - initial_amount) / initial_amount
            
            if cumulative_pnl <= self.stop_loss_threshold:
                return StrategySignal(
                    'sell', 
                    1.0,  # 全部卖出
                    "🛑 止损触发", 
                    f"累计亏损{cumulative_pnl*100:.1f}%，触发止损，建议全部赎回"
                )
            elif cumulative_pnl <= self.warning_threshold:
                # 警告但不止损，继续执行策略
                pass
        
        # 匹配规则
        for rule in self.rules:
            for condition in rule['conditions']:
                today_min = condition['today_min']
                today_max = condition['today_max']
                prev_min = condition['prev_min']
                prev_max = condition['prev_max']
                
                if (today_min <= today_return <= today_max and 
                    prev_min <= prev_day_return <= prev_max):
                    
                    action = rule['action']
                    multiplier = rule['multiplier']
                    label = rule['label']
                    description = rule['description']
                    
                    return StrategySignal(action, multiplier, label, description)
        
        # 默认：持有
        return StrategySignal('hold', 0.0, "🔴 未知状态", "不买入，不赎回")


def get_all_advanced_strategies() -> Dict[str, BaseStrategy]:
    """获取所有高级策略实例"""
    return {
        'dual_ma': DualMAStrategy(),
        'mean_reversion': MeanReversionStrategy(),
        'target_value': TargetValueStrategy(),
        'grid': GridTradingStrategy(),
        'enhanced_rule_based': EnhancedRuleBasedStrategy()
    }

