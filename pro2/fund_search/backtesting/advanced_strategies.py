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
        else:
            raise ValueError("DataFrame必须包含 '单位净值', 'nav' 或 'close' 列")

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
        
        if deviation < -self.threshold * 2:
            # 极度低估 (例如低于均线10%)
            return StrategySignal('buy', 2.0, "极度低估", f"当前价格低于均线 {abs(deviation)*100:.1f}%")
        elif deviation < -self.threshold:
            # 低估
            return StrategySignal('buy', 1.5, "低估区域", f"当前价格低于均线 {abs(deviation)*100:.1f}%")
        elif deviation > self.threshold * 2:
            # 极度高估
            return StrategySignal('sell', 0.5, "极度高估", f"当前价格高于均线 {deviation*100:.1f}%")
        elif deviation > self.threshold:
            # 高估
            return StrategySignal('buy', 0.5, "高估区域", f"当前价格高于均线 {deviation*100:.1f}%")
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
class EnhancedRuleBasedAdapter(BaseStrategy):
    """
    增强规则基准策略适配器
    
    逻辑：
    - 适配当前系统使用的 EnhancedInvestmentStrategy
    - 基于短期涨跌幅规则 (如: 连涨、反转、大跌等)
    - 结合滚动绩效指标 (夏普、回撤等) 进行增强
    """
    
    def __init__(self):
        super().__init__(
            name="增强规则基准策略", 
            description="当前系统使用的复合规则策略，基于短期涨跌幅与趋势判断"
        )
        # 延迟导入以避免循环依赖或路径问题
        try:
            from enhanced_strategy import EnhancedInvestmentStrategy
            self.strategy = EnhancedInvestmentStrategy()
        except ImportError:
            # 尝试从当前包导入
            from .enhanced_strategy import EnhancedInvestmentStrategy
            self.strategy = EnhancedInvestmentStrategy()
        
    def generate_signal(self, history_df: pd.DataFrame, current_index: int, current_holdings: float = 0, **kwargs) -> StrategySignal:
        # 需要至少2天历史数据计算当日和昨日收益率
        if current_index < 2:
            return StrategySignal('hold', 0, "数据不足")
        
        nav = self._get_nav(history_df)
        
        # 获取价格
        current_nav = nav.iloc[current_index]
        prev_nav = nav.iloc[current_index - 1]
        prev2_nav = nav.iloc[current_index - 2]
        
        # 计算百分比收益率
        today_return = (current_nav - prev_nav) / prev_nav * 100
        prev_day_return = (prev_nav - prev2_nav) / prev2_nav * 100
        
        # 计算简单的滚动绩效指标 (模拟EnhancedData的performance_metrics)
        # 使用过去252天的数据 (约一年)
        metrics = None
        lookback = 252
        start_idx = max(0, current_index - lookback)
        
        # 只有数据足够时才计算完整指标，否则使用默认值或None
        if current_index - start_idx > 30:
            subset_nav = nav.iloc[start_idx : current_index + 1]
            returns = subset_nav.pct_change().dropna()
            
            if not returns.empty:
                # 年化波动率
                volatility = returns.std() * np.sqrt(252)
                
                # 年化收益率
                total_ret = (subset_nav.iloc[-1] / subset_nav.iloc[0]) - 1
                days = len(subset_nav)
                annualized_return = (1 + total_ret) ** (252 / days) - 1
                
                # 夏普比率 (假设无风险利率3%)
                rf = 0.03
                sharpe_ratio = (annualized_return - rf) / volatility if volatility > 0 else 0
                
                # 最大回撤
                cum_ret = (1 + returns).cumprod()
                rolling_max = cum_ret.expanding().max()
                drawdowns = (cum_ret - rolling_max) / rolling_max
                max_drawdown = drawdowns.min()
                
                # 胜率
                win_rate = (returns > 0).mean()
                
                # 简单综合评分 (示例)
                composite_score = (sharpe_ratio * 0.4 + (1 if total_ret > 0 else 0) * 0.3 + (1 + max_drawdown) * 0.3)
                
                metrics = {
                    'sharpe_ratio': sharpe_ratio,
                    'max_drawdown': max_drawdown,
                    'volatility': volatility,
                    'win_rate': win_rate,
                    'composite_score': composite_score
                }
        
        # 调用原始策略
        result = self.strategy.analyze_strategy(today_return, prev_day_return, metrics)
        
        action = result['action']
        buy_multiplier = result['buy_multiplier']
        description = result['operation_suggestion']
        status_label = result['status_label']
        redeem_amount = result['redeem_amount']
        
        # 转换为 StrategySignal
        signal_action = 'hold'
        signal_multiplier = 0.0
        
        if action in ['strong_buy', 'buy', 'weak_buy']:
            signal_action = 'buy'
            signal_multiplier = buy_multiplier
        elif action in ['sell', 'weak_sell']:
            signal_action = 'sell'
            # 策略返回的是固定赎回金额(redeem_amount)，在此框架下需要转换为持有比例
            # 这比较困难，因为需要知道当前持仓总值
            # 幸好 generate_signal 接收 current_holdings
            if current_holdings > 0:
                # 计算赎回比例 (限制在 0-1 之间)
                # 如果redeem_amount为0但action是sell，可能意味着全仓卖出? 
                # 查看 enhanced_strategy 源码，redeem_amount 通常是 30, 15 等固定小额
                # 或者全仓卖出逻辑。
                if redeem_amount > 0:
                    sell_ratio = min(redeem_amount / current_holdings, 1.0)
                else:
                    # 如果没有指定金额但要求卖出，假设卖出 10% 或根据 multiplier?
                    # 原始策略中 action='sell' 对应 '反转下跌'，redeem_amount=30
                    # 只有极度情况可能大额卖出。
                    # 为了回测效果，我们假设 multiplier 用于卖出比例?
                    # 原始策略中 sell 没有用到 multiplier (default 1.0 in config maybe?)
                    # 让我们保守一点，如果 redeem_amount > 0 用金额，否则用 20%?
                    sell_ratio = 0.2 
                signal_multiplier = sell_ratio
            else:
                signal_multiplier = 0.0
        
        return StrategySignal(signal_action, signal_multiplier, status_label, description)

def get_all_advanced_strategies() -> Dict[str, BaseStrategy]:
    """获取所有高级策略实例"""
    return {
        'dual_ma': DualMAStrategy(),
        'mean_reversion': MeanReversionStrategy(),
        'target_value': TargetValueStrategy(),
        'grid': GridTradingStrategy(),
        'enhanced_rule_based': EnhancedRuleBasedAdapter()
    }

