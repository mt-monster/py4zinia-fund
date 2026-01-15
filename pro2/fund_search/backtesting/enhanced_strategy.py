#!/usr/bin/env python
# coding: utf-8

"""
增强版投资策略模块
提供优化的基金投资策略逻辑
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from datetime import datetime
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnhancedInvestmentStrategy:
    """增强版投资策略类"""
    
    def __init__(self):
        from shared.enhanced_config import INVESTMENT_STRATEGY_CONFIG
        self.config = INVESTMENT_STRATEGY_CONFIG
        
        # 策略规则定义
        self.strategy_rules = {
            # 强势上涨策略
            'strong_bull': {
                'conditions': [
                    {'today_return': (1.0, float('inf')), 'prev_day_return': (0.5, float('inf'))},
                    {'today_return': (0.5, float('inf')), 'prev_day_return': (1.0, float('inf'))}
                ],
                'action': 'strong_buy',
                'redeem_amount': 0,
                'label': "🟢 **强势突破**",
                'description': "基金强势上涨，建议积极买入"
            },
            
            # 持续上涨策略
            'bull_continuation': {
                'conditions': [
                    {'today_return': (0.3, 1.0), 'prev_day_return': (0.3, 1.0)},
                    {'today_return': (0.2, 0.5), 'prev_day_return': (0.5, 1.0)}
                ],
                'action': 'buy',
                'redeem_amount': 15,
                'label': "🟡 **连涨加速**",
                'description': "基金持续上涨，建议适量买入，小额赎回"
            },
            
            # 上涨放缓策略
            'bull_slowing': {
                'conditions': [
                    {'today_return': (0.0, 0.3), 'prev_day_return': (0.3, float('inf'))},
                    {'today_return': (-0.3, 0.0), 'prev_day_return': (0.5, float('inf'))}
                ],
                'action': 'hold',
                'redeem_amount': 0,
                'label': "🟠 **连涨放缓**",
                'description': "上涨势头放缓，建议持有观望"
            },
            
            # 反转上涨策略
            'bull_reversal': {
                'conditions': [
                    {'today_return': (0.3, float('inf')), 'prev_day_return': (-float('inf'), 0.0)}
                ],
                'action': 'buy',
                'redeem_amount': 0,
                'label': "🔵 **反转上涨**",
                'description': "基金由跌转涨，建议买入"
            },
            
            # 转势休整策略
            'consolidation': {
                'conditions': [
                    {'today_return': (0.0, 0.01), 'prev_day_return': (0.3, float('inf'))}
                ],
                'action': 'weak_sell',
                'redeem_amount': 30,
                'label': "🔴 **转势休整**",
                'description': "上涨后休整，建议部分赎回"
            },
            
            # 反转下跌策略
            'bear_reversal': {
                'conditions': [
                    {'today_return': (-float('inf'), 0.0), 'prev_day_return': (0.3, float('inf'))}
                ],
                'action': 'sell',
                'redeem_amount': 30,
                'label': "🔴 **反转下跌**",
                'description': "基金由涨转跌，建议卖出"
            },
            
            # 绝对企稳策略
            'absolute_bottom': {
                'conditions': [
                    {'today_return': (0.0, 0.01), 'prev_day_return': (-0.3, 0.0)}
                ],
                'action': 'strong_buy',
                'redeem_amount': 0,
                'label': "⚪ **绝对企稳**",
                'description': "基金企稳，建议积极买入"
            },
            
            # 首次大跌策略
            'first_major_drop': {
                'conditions': [
                    {'today_return': (-float('inf'), -2.0), 'prev_day_return': (-0.1, 0.1)}
                ],
                'action': 'buy',
                'redeem_amount': 0,
                'label': "🔴 **首次大跌**",
                'description': "基金首次大跌，建议逢低买入"
            },
            
            # 持续下跌策略
            'bear_continuation': {
                'conditions': [
                    {'today_return': (-float('inf'), -0.5), 'prev_day_return': (-float('inf'), -0.5)}
                ],
                'action': 'weak_buy',
                'redeem_amount': 0,
                'label': "🟣 **持续下跌**",
                'description': "基金持续下跌，建议谨慎买入"
            },
            
            # 跌速放缓策略
            'bear_slowing': {
                'conditions': [
                    {'today_return': (-0.5, 0.0), 'prev_day_return': (-float('inf'), -1.0)}
                ],
                'action': 'buy',
                'redeem_amount': 0,
                'label': "🟦 **跌速放缓**",
                'description': "下跌速度放缓，建议买入"
            }
        }
    
    def analyze_strategy(self, today_return: float, prev_day_return: float, 
                        performance_metrics: Optional[Dict] = None) -> Dict:
        """
        分析投资策略
        
        参数：
        today_return: 当日收益率（%）
        prev_day_return: 前一日收益率（%）
        performance_metrics: 绩效指标（可选）
        
        返回：
        dict: 策略分析结果
        """
        try:
            # 基础策略分析
            strategy_result = self._basic_strategy_analysis(today_return, prev_day_return)
            
            # 如果提供了绩效指标，进行增强分析
            if performance_metrics:
                enhanced_result = self._enhanced_strategy_analysis(
                    today_return, prev_day_return, performance_metrics, strategy_result
                )
                return enhanced_result
            
            return strategy_result
            
        except Exception as e:
            logger.error(f"投资策略分析失败: {str(e)}")
            return self._get_default_strategy()
    
    def _basic_strategy_analysis(self, today_return: float, prev_day_return: float) -> Dict:
        """
        基础策略分析
        
        参数：
        today_return: 当日收益率（%）
        prev_day_return: 前一日收益率（%）
        
        返回：
        dict: 基础策略结果
        """
        # 遍历所有策略规则
        for strategy_name, rule in self.strategy_rules.items():
            for condition in rule['conditions']:
                today_min, today_max = condition['today_return']
                prev_min, prev_max = condition['prev_day_return']
                
                # 检查是否满足条件
                if (today_min <= today_return <= today_max and 
                    prev_min <= prev_day_return <= prev_max):
                    
                    action = rule['action']
                    return {
                        'strategy_name': strategy_name,
                        'action': action,
                        'buy_multiplier': self.config['buy_multipliers'].get(action, 1.0),
                        'redeem_amount': rule['redeem_amount'],
                        'status_label': rule['label'],
                        'operation_suggestion': rule['description'],
                        'execution_amount': self._get_execution_amount(action, rule['redeem_amount']),
                        'comparison_value': today_return - prev_day_return
                    }
        
        # 默认策略
        return self._get_default_strategy()
    
    def _enhanced_strategy_analysis(self, today_return: float, prev_day_return: float, 
                                  performance_metrics: Dict, base_result: Dict) -> Dict:
        """
        增强策略分析（结合绩效指标）
        
        参数：
        today_return: 当日收益率（%）
        prev_day_return: 前一日收益率（%）
        performance_metrics: 绩效指标
        base_result: 基础策略结果
        
        返回：
        dict: 增强策略结果
        """
        # 获取绩效指标
        sharpe_ratio = performance_metrics.get('sharpe_ratio', 0.0)
        max_drawdown = performance_metrics.get('max_drawdown', 0.0)
        volatility = performance_metrics.get('volatility', 0.0)
        win_rate = performance_metrics.get('win_rate', 0.0)
        composite_score = performance_metrics.get('composite_score', 0.0)
        
        # 根据绩效指标调整策略
        enhanced_result = base_result.copy()
        
        # 如果基金绩效优秀，增强买入信号
        if composite_score > 0.7 and sharpe_ratio > 1.0:
            if base_result['action'] in ['buy', 'strong_buy']:
                enhanced_result['buy_multiplier'] = min(3.0, base_result['buy_multiplier'] * 1.5)
                enhanced_result['status_label'] += " ⭐"
                enhanced_result['operation_suggestion'] += "（基于优秀绩效）"
        
        # 如果基金波动率过高，降低买入倍数
        if volatility > 0.3:  # 30%波动率
            enhanced_result['buy_multiplier'] = max(0.5, base_result['buy_multiplier'] * 0.7)
            enhanced_result['status_label'] += " ⚠️"
            enhanced_result['operation_suggestion'] += "（注意高波动风险）"
        
        # 如果最大回撤过大，谨慎操作
        if abs(max_drawdown) > 0.2:  # 20%最大回撤
            if base_result['action'] in ['strong_buy', 'buy']:
                enhanced_result['action'] = 'weak_buy'
                enhanced_result['buy_multiplier'] = min(1.0, base_result['buy_multiplier'] * 0.5)
                enhanced_result['status_label'] += " 🛡️"
                enhanced_result['operation_suggestion'] += "（考虑回撤风险）"
        
        # 如果胜率较低，降低买入信号
        if win_rate < 0.5:
            enhanced_result['buy_multiplier'] = max(0.3, base_result['buy_multiplier'] * 0.6)
            enhanced_result['status_label'] += " 📉"
            enhanced_result['operation_suggestion'] += "（胜率偏低，谨慎操作）"
        
        return enhanced_result
    
    def _get_execution_amount(self, action: str, redeem_amount: int) -> str:
        """
        获取执行金额描述
        
        参数：
        action: 操作类型
        redeem_amount: 赎回金额
        
        返回：
        str: 执行金额描述
        """
        if action == 'strong_buy':
            return "买入3.0×定额"
        elif action == 'buy':
            return "买入1.5×定额"
        elif action == 'weak_buy':
            return "买入1.0×定额"
        elif action in ['sell', 'weak_sell']:
            return f"赎回¥{redeem_amount}"
        else:
            return "持有不动"
    
    def _get_default_strategy(self) -> Dict:
        """
        获取默认策略
        
        返回：
        dict: 默认策略结果
        """
        return {
            'strategy_name': 'default',
            'action': 'hold',
            'buy_multiplier': 0.0,
            'redeem_amount': 0,
            'status_label': "🔴 **未知状态**",
            'operation_suggestion': "不买入，不赎回",
            'execution_amount': "持有不动",
            'comparison_value': 0.0
        }
    
    def generate_strategy_summary(self, strategy_results: list) -> Dict:
        """
        生成策略汇总
        
        参数：
        strategy_results: 策略结果列表
        
        返回：
        dict: 策略汇总
        """
        if not strategy_results:
            return {}
        
        # 统计各种操作的数量
        action_counts = {}
        total_buy_multiplier = 0.0
        total_redeem_amount = 0
        
        for result in strategy_results:
            action = result['action']
            action_counts[action] = action_counts.get(action, 0) + 1
            total_buy_multiplier += result['buy_multiplier']
            total_redeem_amount += result['redeem_amount']
        
        # 计算平均买入倍数
        avg_buy_multiplier = total_buy_multiplier / len(strategy_results) if strategy_results else 0.0
        
        return {
            'total_funds': len(strategy_results),
            'action_distribution': action_counts,
            'avg_buy_multiplier': avg_buy_multiplier,
            'total_redeem_amount': total_redeem_amount,
            'buy_signals': action_counts.get('strong_buy', 0) + action_counts.get('buy', 0) + action_counts.get('weak_buy', 0),
            'sell_signals': action_counts.get('sell', 0) + action_counts.get('weak_sell', 0),
            'hold_signals': action_counts.get('hold', 0)
        }


if __name__ == "__main__":
    # 测试代码
    strategy = EnhancedInvestmentStrategy()
    
    # 测试各种情况
    test_cases = [
        (2.5, 1.2),   # 强势上涨
        (0.8, 0.6),   # 持续上涨
        (0.1, 0.8),   # 上涨放缓
        (1.2, -0.5),  # 反转上涨
        (0.01, 0.8),  # 转势休整
        (-0.8, 0.8),  # 反转下跌
        (0.01, -0.2), # 绝对企稳
        (-2.5, 0.05), # 首次大跌
        (-0.8, -0.6), # 持续下跌
        (-0.2, -1.5), # 跌速放缓
    ]
    
    for today, prev in test_cases:
        result = strategy.analyze_strategy(today, prev)
        print(f"今日: {today}%, 昨日: {prev}% -> {result['status_label']} | {result['operation_suggestion']}")
    
    # 测试绩效指标增强分析
    performance_metrics = {
        'sharpe_ratio': 1.5,
        'max_drawdown': -0.1,
        'volatility': 0.15,
        'win_rate': 0.6,
        'composite_score': 0.8
    }
    
    result = strategy.analyze_strategy(1.2, -0.5, performance_metrics)
    print(f"\n增强策略分析: {result}")
    
    # 测试策略汇总
    strategy_results = [
        strategy.analyze_strategy(2.5, 1.2),
        strategy.analyze_strategy(0.8, 0.6),
        strategy.analyze_strategy(-0.8, 0.8),
        strategy.analyze_strategy(0.01, -0.2),
    ]
    
    summary = strategy.generate_strategy_summary(strategy_results)
    print(f"\n策略汇总: {summary}")