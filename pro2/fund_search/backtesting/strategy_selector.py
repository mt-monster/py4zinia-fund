#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略选择器模块
根据基金的历史数据和特征，从策略库中选择最适合的策略
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Type
from dataclasses import dataclass
from enum import Enum
import logging

from .advanced_strategies import (
    BaseStrategy, DualMAStrategy, MeanReversionStrategy, 
    TargetValueStrategy, GridTradingStrategy, EnhancedRuleBasedStrategy,
    StrategySignal
)
from .ml_prediction_strategy import MLPredictionStrategy, get_ml_prediction_strategy

logger = logging.getLogger(__name__)


class FundCharacteristics(Enum):
    """基金特征类型"""
    TRENDING = "趋势型"           # 有明显趋势
    MEAN_REVERTING = "均值回归型"  # 围绕均值波动
    HIGH_VOLATILITY = "高波动型"   # 波动大
    LOW_VOLATILITY = "低波动型"    # 波动小
    BREAKOUT = "突破型"           # 有突破特征


@dataclass
class FundProfile:
    """基金画像"""
    fund_code: str
    fund_name: str
    volatility: float           # 年化波动率
    trend_strength: float       # 趋势强度 (-1到1)
    mean_reversion_score: float # 均值回归特征分数
    sharpe_ratio: float         # 夏普比率
    max_drawdown: float         # 最大回撤
    avg_return: float           # 平均收益率
    # 添加风险评估字段
    risk_level: str = "medium"  # 风险等级: low, medium, high
    fund_type: str = "unknown"  # 基金类型


@dataclass
class StrategyMatchResult:
    """策略匹配结果"""
    strategy_name: str
    strategy_type: str
    match_score: float          # 匹配度分数 (0-100)
    reason: str                 # 选择理由
    signal: StrategySignal      # 当前信号
    backtest_score: float       # 回测评分


class StrategySelector:
    """策略选择器"""
    
    # 策略注册表
    STRATEGIES = {
        'dual_ma': {
            'class': DualMAStrategy,
            'name': '双均线动量策略',
            'description': '适用于有明显趋势的基金',
            'best_for': [FundCharacteristics.TRENDING, FundCharacteristics.BREAKOUT],
            'min_volatility': 0.15,
            'max_volatility': 0.35,
        },
        'mean_reversion': {
            'class': MeanReversionStrategy,
            'name': '均值回归智能定投',
            'description': '适用于震荡波动的基金',
            'best_for': [FundCharacteristics.MEAN_REVERTING],
            'min_volatility': 0.10,
            'max_volatility': 0.30,
        },
        'grid_trading': {
            'class': GridTradingStrategy,
            'name': '网格交易策略',
            'description': '适用于高波动震荡市',
            'best_for': [FundCharacteristics.HIGH_VOLATILITY, FundCharacteristics.MEAN_REVERTING],
            'min_volatility': 0.20,
            'max_volatility': 0.40,
        },
        'enhanced_rule': {
            'class': EnhancedRuleBasedStrategy,
            'name': '增强规则基准策略',
            'description': '综合策略，适用于大多数基金',
            'best_for': [],  # 通用策略
            'min_volatility': 0.0,
            'max_volatility': 1.0,
        },
        'target_value': {
            'class': TargetValueStrategy,
            'name': '目标市值策略',
            'description': '适用于定投计划',
            'best_for': [FundCharacteristics.LOW_VOLATILITY],
            'min_volatility': 0.0,
            'max_volatility': 0.25,
        },
        'ml_prediction': {
            'class': MLPredictionStrategy,
            'name': '机器学习预测策略',
            'description': '基于多模型集成的收益率预测策略，适用于数据充足的基金',
            'best_for': [FundCharacteristics.TRENDING, FundCharacteristics.BREAKOUT, 
                        FundCharacteristics.MEAN_REVERTING],
            'min_volatility': 0.10,
            'max_volatility': 0.40,
            'min_data_points': 100,  # 需要较多历史数据
            'requires_ml': True,     # 标记为ML策略
        }
    }
    
    def __init__(self):
        self.strategies = {}
        self._init_strategies()
    
    def _init_strategies(self):
        """初始化策略实例"""
        for key, config in self.STRATEGIES.items():
            try:
                self.strategies[key] = config['class']()
            except Exception as e:
                logger.warning(f"初始化策略 {key} 失败: {e}")
    
    def analyze_fund_characteristics(self, history_df: pd.DataFrame) -> FundProfile:
        """
        分析基金特征
        
        Args:
            history_df: 历史净值数据DataFrame
            
        Returns:
            FundProfile: 基金画像
        """
        if history_df.empty or len(history_df) < 30:
            return None
        
        # 获取净值序列 - 支持多种列名
        if '单位净值' in history_df.columns:
            nav = history_df['单位净值']
        elif 'nav' in history_df.columns:
            nav = history_df['nav']
        elif 'close' in history_df.columns:
            nav = history_df['close']
        elif 'current_estimate' in history_df.columns:
            nav = history_df['current_estimate']
        elif 'yesterday_nav' in history_df.columns:
            nav = history_df['yesterday_nav']
        else:
            # 尝试使用第三列作为净值（假设第一列是日期）
            numeric_cols = history_df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                nav = history_df[numeric_cols[0]]
            else:
                return None
        
        # 计算日收益率
        returns = nav.pct_change().dropna()
        
        if len(returns) < 20:
            return None
        
        # 1. 计算波动率 (年化)
        volatility = returns.std() * np.sqrt(252) * 100
        
        # 2. 计算趋势强度
        # 使用20日均线和60日均线的关系
        ma20 = nav.rolling(20).mean()
        ma60 = nav.rolling(60).mean()
        
        if not ma20.isna().all() and not ma60.isna().all():
            trend_strength = (ma20.iloc[-1] - ma60.iloc[-1]) / ma60.iloc[-1] * 10
            trend_strength = float(np.clip(trend_strength, -1, 1))  # 限制在-1到1之间
        else:
            trend_strength = 0.0
        
        # 3. 计算均值回归特征
        # 计算价格与均线的偏离度的自回归特性
        ma250 = nav.rolling(250).mean()
        if not ma250.isna().all():
            deviation = (nav - ma250) / ma250
            # 均值回归分数：偏离度与后续收益率的负相关性
            future_return = nav.shift(-5) / nav - 1
            correlation = deviation.corr(future_return)
            mean_reversion_score = -correlation if not np.isnan(correlation) else 0.0
            mean_reversion_score = float(np.clip(mean_reversion_score, -1, 1))
        else:
            mean_reversion_score = 0.0
        
        # 4. 计算夏普比率
        risk_free_rate = 0.03 / 252  # 日无风险收益率
        excess_return = returns.mean() - risk_free_rate
        sharpe = (excess_return / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        
        # 5. 计算最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() * 100
        
        # 6. 平均收益率 (年化)
        avg_return = returns.mean() * 252 * 100
        
        # 确定风险等级
        if volatility < 0.15:
            risk_level = "low"
        elif volatility < 0.25:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        return FundProfile(
            fund_code=history_df.get('fund_code', ['unknown'])[0] if 'fund_code' in history_df.columns else 'unknown',
            fund_name=history_df.get('fund_name', ['unknown'])[0] if 'fund_name' in history_df.columns else 'unknown',
            volatility=float(round(volatility, 4)),
            trend_strength=float(round(trend_strength, 4)),
            mean_reversion_score=float(round(mean_reversion_score, 4)),
            sharpe_ratio=float(round(sharpe, 4)),
            max_drawdown=float(round(max_drawdown, 4)),
            avg_return=float(round(avg_return, 4)),
            risk_level=str(risk_level)
        )
    
    def select_best_strategy(self, history_df: pd.DataFrame, 
                            current_index: int = -1) -> StrategyMatchResult:
        """
        选择最适合的策略
        
        Args:
            history_df: 历史数据
            current_index: 当前索引，默认-1表示最后一天
            
        Returns:
            StrategyMatchResult: 最佳策略匹配结果
        """
        if history_df.empty:
            return None
        
        # 分析基金特征
        profile = self.analyze_fund_characteristics(history_df)
        if profile is None:
            # 使用默认策略
            default_strategy = EnhancedRuleBasedStrategy()
            signal = default_strategy.generate_signal(history_df, current_index)
            return StrategyMatchResult(
                strategy_name='增强规则基准策略',
                strategy_type='enhanced_rule',
                match_score=50.0,
                reason='数据不足，使用默认综合策略',
                signal=signal,
                backtest_score=50.0
            )
        
        # 评估每个策略
        strategy_scores = []
        
        for key, strategy in self.strategies.items():
            try:
                score, reason = self._evaluate_strategy_fit(strategy, profile, key)
                
                # 生成当前信号
                signal = strategy.generate_signal(history_df, current_index)
                
                strategy_scores.append({
                    'key': key,
                    'strategy': strategy,
                    'score': score,
                    'reason': reason,
                    'signal': signal
                })
            except Exception as e:
                logger.warning(f"评估策略 {key} 失败: {e}")
                continue
        
        if not strategy_scores:
            # 如果没有策略匹配，使用默认策略
            default_strategy = EnhancedRuleBasedStrategy()
            signal = default_strategy.generate_signal(history_df, current_index)
            return StrategyMatchResult(
                strategy_name='增强规则基准策略',
                strategy_type='enhanced_rule',
                match_score=50.0,
                reason='无匹配策略，使用默认策略',
                signal=signal,
                backtest_score=50.0
            )
        
        # 选择得分最高的策略
        best = max(strategy_scores, key=lambda x: x['score'])
        
        return StrategyMatchResult(
            strategy_name=self.STRATEGIES[best['key']]['name'],
            strategy_type=best['key'],
            match_score=round(best['score'], 2),
            reason=best['reason'],
            signal=best['signal'],
            backtest_score=round(best['score'], 2)
        )
    
    def _evaluate_strategy_fit(self, strategy: BaseStrategy, 
                              profile: FundProfile, 
                              strategy_key: str) -> Tuple[float, str]:
        """
        评估策略与基金的匹配度
        
        Returns:
            (匹配分数, 选择理由)
        """
        config = self.STRATEGIES.get(strategy_key, {})
        score = 50.0  # 基础分
        reasons = []
        
        # 1. 波动率匹配
        min_vol = config.get('min_volatility', 0)
        max_vol = config.get('max_volatility', 1)
        
        if min_vol <= profile.volatility <= max_vol:
            score += 20
            reasons.append("波动率匹配")
        else:
            # 波动率不匹配扣分
            if profile.volatility < min_vol:
                score -= 10
                reasons.append("波动率偏低")
            elif profile.volatility > max_vol:
                score -= 10
                reasons.append("波动率偏高")
        
        # 2. 趋势特征匹配
        if isinstance(strategy, DualMAStrategy):
            if abs(profile.trend_strength) > 0.3:
                score += 20
                reasons.append("趋势明显，适合动量策略")
            if profile.sharpe_ratio > 0.5:
                score += 10
                reasons.append("夏普比率良好")
                
        elif isinstance(strategy, MeanReversionStrategy):
            if profile.mean_reversion_score > 0.3:
                score += 20
                reasons.append("均值回归特征明显")
            if 0.10 <= profile.volatility <= 0.25:
                score += 15
                reasons.append("波动适中，适合均值回归")
                
        elif isinstance(strategy, GridTradingStrategy):
            if profile.volatility > 0.25:
                score += 25
                reasons.append("高波动适合网格交易")
            if abs(profile.trend_strength) < 0.3:
                score += 15
                reasons.append("震荡市适合网格交易")
                
        elif isinstance(strategy, EnhancedRuleBasedStrategy):
            # 通用策略，基础分较高
            score += 15
            reasons.append("综合策略适应性强")
            
        elif isinstance(strategy, TargetValueStrategy):
            if profile.volatility < 0.20:
                score += 15
                reasons.append("低波动适合目标市值策略")
            if profile.max_drawdown > -15:
                score += 10
                reasons.append("回撤可控")
        
        elif isinstance(strategy, MLPredictionStrategy):
            # ML预测策略评估
            score += 10  # 基础分
            reasons.append("机器学习预测策略")
            
            # 数据充足度加分
            if profile.volatility > 0.15:
                score += 10
                reasons.append("波动适中，ML模型可学习")
            
            # 趋势特征加分
            if abs(profile.trend_strength) > 0.2:
                score += 10
                reasons.append("趋势特征明显，利于预测")
            
            # 夏普比率良好
            if profile.sharpe_ratio > 0.3:
                score += 5
                reasons.append("历史表现稳定")
            
            # 高波动数据充足时更适合
            if profile.volatility > 0.20 and profile.volatility < 0.35:
                score += 10
                reasons.append("波动率适合ML模型训练")
        
        # 3. 风险调整
        if profile.sharpe_ratio < 0:
            score -= 10
            reasons.append("夏普比率为负，需谨慎")
        
        if profile.max_drawdown < -30:
            score -= 10
            reasons.append("历史回撤较大")
        
        # 4. 综合评分调整
        score = float(np.clip(score, 0, 100))
        
        reason_text = "；".join(reasons) if reasons else "综合评估"
        return score, reason_text
    
    def get_all_strategy_signals(self, history_df: pd.DataFrame, 
                                 current_index: int = -1) -> List[Dict]:
        """
        获取所有策略的信号（用于对比展示）
        
        Returns:
            所有策略的信号列表
        """
        results = []
        
        for key, strategy in self.strategies.items():
            try:
                signal = strategy.generate_signal(history_df, current_index)
                config = self.STRATEGIES[key]
                
                results.append({
                    'strategy_key': key,
                    'strategy_name': config['name'],
                    'strategy_description': config['description'],
                    'signal': signal,
                    'action': signal.action,
                    'multiplier': signal.amount_multiplier,
                    'reason': signal.reason,
                    'suggestion': signal.suggestion if hasattr(signal, 'suggestion') else ""
                })
            except Exception as e:
                logger.warning(f"获取策略 {key} 信号失败: {e}")
                continue
        
        return results


# 单例模式
_strategy_selector = None

def get_strategy_selector() -> StrategySelector:
    """获取策略选择器单例"""
    global _strategy_selector
    if _strategy_selector is None:
        _strategy_selector = StrategySelector()
    return _strategy_selector
