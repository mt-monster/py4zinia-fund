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

        # 从YAML配置文件加载策略规则
        self.strategy_rules = self._load_strategy_rules_from_yaml()

    def _load_strategy_rules_from_yaml(self) -> Dict:
        """
        从YAML配置文件加载策略规则

        返回：
        dict: 策略规则字典
        """
        import yaml
        import os

        try:
            # 构建策略配置文件路径
            config_dir = os.path.join(os.path.dirname(__file__), '..', 'shared')
            config_path = os.path.join(config_dir, 'strategy_config.yaml')

            # 读取YAML配置文件
            with open(config_path, 'r', encoding='utf-8') as file:
                yaml_config = yaml.safe_load(file)

            strategies = yaml_config.get('strategies', {})

            # 转换YAML格式为代码使用的格式
            strategy_rules = {}
            for strategy_name, strategy_config in strategies.items():
                # 处理多条件情况
                conditions = []
                for condition in strategy_config['conditions']:
                    # YAML中可能有单个条件或多个条件
                    if isinstance(condition, dict):
                        # 单个条件：直接使用
                        conditions.append(condition)
                    else:
                        # 多个条件：展开
                        conditions.extend(strategy_config['conditions'])

                # 转换条件格式为元组
                converted_conditions = []
                for condition in conditions:
                    converted_condition = {}

                    # 处理 YAML 中 _min/_max 对的格式
                    keys_to_process = list(condition.keys())
                    i = 0
                    while i < len(keys_to_process):
                        key = keys_to_process[i]
                        if key.endswith('_min') and i + 1 < len(keys_to_process):
                            base_key = key[:-4]  # 移除 '_min'
                            max_key = base_key + '_max'
                            if max_key in keys_to_process[i+1:]:
                                # 找到对应的 _max 键
                                min_val = condition[key]
                                max_val = condition[max_key]

                                # 处理特殊值
                                if min_val == '-.inf':
                                    min_val = float('-inf')
                                if max_val == '.inf':
                                    max_val = float('inf')

                                converted_condition[base_key] = (float(min_val), float(max_val))
                                # 跳过下一个 _max 键
                                i += 2
                                continue

                        # 处理单个键的情况（向后兼容）
                        value = condition[key]
                        if isinstance(value, list) and len(value) == 2:
                            # 处理 [min, max] 格式
                            converted_condition[key] = tuple(value)
                        elif isinstance(value, dict) and 'min' in value and 'max' in value:
                            # 处理 min/max 格式
                            min_val = value['min']
                            max_val = value['max']
                            if min_val == '-inf':
                                min_val = float('-inf')
                            if max_val == 'inf':
                                max_val = float('inf')
                            converted_condition[key] = (min_val, max_val)
                        else:
                            # 处理单个值或特殊格式
                            if value == '.inf':
                                converted_condition[key] = (0, float('inf'))
                            elif value == '-.inf':
                                converted_condition[key] = (float('-inf'), 0)
                            else:
                                converted_condition[key] = (value, value)
                        i += 1

                    if converted_condition:
                        converted_conditions.append(converted_condition)

                # 构建策略规则
                strategy_rules[strategy_name] = {
                    'conditions': converted_conditions,
                    'action': strategy_config['action'],
                    'redeem_amount': strategy_config['redeem_amount'],
                    'buy_multiplier': strategy_config.get('buy_multiplier', 1.0),
                    'label': strategy_config['label'],
                    'description': strategy_config['description']
                }

            logger.info(f"成功从YAML加载了 {len(strategy_rules)} 个策略规则")
            return strategy_rules

        except Exception as e:
            logger.error(f"从YAML加载策略规则失败: {str(e)}，使用默认规则")
            # 返回默认的硬编码规则作为fallback
            return self._get_default_strategy_rules()


    def _get_default_strategy_rules(self) -> Dict:
        """
        获取默认的策略规则（作为YAML加载失败时的fallback）

        返回：
        dict: 默认策略规则
        """
        return {
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
                'redeem_amount': 0.02,  # 改为比例赎回
                'label': "🟡 **连涨加速**",
                'description': "基金持续上涨，建议适量买入（胜率偏低，谨慎操作）"
            },

            # 绝对企稳策略
            'absolute_bottom': {
                'conditions': [
                    {'today_return': (0.0, 0.01), 'prev_day_return': (-0.3, 0.0)}
                ],
                'action': 'buy',
                'redeem_amount': 0,
                'label': "⚪ **绝对企稳**",
                'description': "基金企稳，建议适量买入（需观察确认）"
            },

            # 持续下跌策略
            'bear_continuation': {
                'conditions': [
                    {'today_return': (-float('inf'), -0.5), 'prev_day_return': (-float('inf'), -0.5)}
                ],
                'action': 'hold',  # 改为持有
                'redeem_amount': 0,
                'label': "🟣 **持续下跌**",
                'description': "基金持续下跌，建议持有观望（避免抄底风险）"
            },

            # 默认策略
            'default': {
                'conditions': [],
                'action': 'hold',
                'redeem_amount': 0,
                'label': "🔴 **未知状态**",
                'description': "不买入，不赎回"
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
            return self._get_default_strategy(today_return, prev_day_return)
    
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

                    # 获取买入倍数（从规则配置或全局配置）
                    buy_multiplier = rule.get('buy_multiplier', self.config['buy_multipliers'].get(action, 1.0))

                    # 处理赎回金额（支持比例赎回）
                    redeem_amount = rule['redeem_amount']
                    if isinstance(redeem_amount, float) and redeem_amount < 1:
                        # 如果是小于1的小数，当作比例赎回
                        execution_amount = f"赎回{redeem_amount:.0%}仓位"
                    else:
                        execution_amount = self._get_execution_amount(action, redeem_amount, buy_multiplier)

                    # 添加仓位比例限制（如果有的话）
                    max_position_ratio = rule.get('max_position_ratio', 1.0)

                    return {
                        'strategy_name': strategy_name,
                        'action': action,
                        'buy_multiplier': buy_multiplier,
                        'redeem_amount': redeem_amount,
                        'max_position_ratio': max_position_ratio,
                        'status_label': rule['label'],
                        'operation_suggestion': rule['description'],
                        'execution_amount': execution_amount,
                        'comparison_value': today_return - prev_day_return
                    }
        
        # 默认策略
        return self._get_default_strategy(today_return, prev_day_return)
    
    def _enhanced_strategy_analysis(self, today_return: float, prev_day_return: float,
                                   performance_metrics: Dict, base_result: Dict) -> Dict:
        """
        增强策略分析（结合绩效指标和全局风险控制）

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

        # 获取全局风险控制配置
        global_risk_config = self.config.get('global_risk_control', {})
        volatility_high_threshold = global_risk_config.get('volatility_high_threshold', 0.25)
        volatility_high_multiplier = global_risk_config.get('volatility_high_multiplier', 0.7)
        small_fund_multiplier = global_risk_config.get('small_fund_multiplier', 0.8)

        # 根据绩效指标调整策略
        enhanced_result = base_result.copy()

        # 如果基金绩效优秀，增强买入信号（但不超过全局限制）
        if composite_score > 0.8 and sharpe_ratio > 1.5:
            if base_result['action'] in ['buy', 'strong_buy']:
                max_multiplier = global_risk_config.get('max_single_fund_position', 0.3) * 10  # 转换为倍数
                enhanced_result['buy_multiplier'] = min(max_multiplier, base_result['buy_multiplier'] * 1.2)
                enhanced_result['status_label'] += " ⭐"
                enhanced_result['operation_suggestion'] += "（基于优秀绩效）"

        # 如果基金波动率过高，降低买入倍数
        if volatility > volatility_high_threshold:
            enhanced_result['buy_multiplier'] = max(0.5, base_result['buy_multiplier'] * volatility_high_multiplier)
            enhanced_result['status_label'] += " ⚠️"
            enhanced_result['operation_suggestion'] += "（注意高波动风险）"

        # 如果最大回撤过大，谨慎操作
        if abs(max_drawdown) > 0.15:  # 15%最大回撤
            if base_result['action'] in ['strong_buy', 'buy']:
                enhanced_result['action'] = 'weak_buy'
                enhanced_result['buy_multiplier'] = min(1.0, base_result['buy_multiplier'] * 0.6)
                # 重新计算执行金额
                enhanced_result['execution_amount'] = self._get_execution_amount(
                    enhanced_result['action'],
                    base_result.get('redeem_amount', 0),
                    enhanced_result['buy_multiplier']
                )
                enhanced_result['operation_suggestion'] += "（注意回撤风险）"

        # 应用仓位比例限制
        max_position_ratio = base_result.get('max_position_ratio', 1.0)
        if max_position_ratio < 1.0:
            # 如果有限制，调整买入倍数
            position_adjusted_multiplier = base_result['buy_multiplier'] * max_position_ratio
            enhanced_result['buy_multiplier'] = min(enhanced_result['buy_multiplier'], position_adjusted_multiplier)
            enhanced_result['operation_suggestion'] += f"（仓位限制{max_position_ratio:.0%}）"
            enhanced_result['status_label'] += " 🛡️"
            enhanced_result['operation_suggestion'] += "（考虑回撤风险）"

        # 最终确保 execution_amount 与最终的 buy_multiplier 一致
        if enhanced_result['action'] in ['strong_buy', 'buy', 'weak_buy'] and enhanced_result['buy_multiplier'] != base_result.get('buy_multiplier', 1.0):
            enhanced_result['execution_amount'] = self._get_execution_amount(
                enhanced_result['action'],
                enhanced_result.get('redeem_amount', 0),
                enhanced_result['buy_multiplier']
            )

        return enhanced_result
    
    def _get_execution_amount(self, action: str, redeem_amount: float, buy_multiplier: float = 1.0) -> str:
        """
        获取执行金额描述

        参数：
        action: 操作类型
        redeem_amount: 赎回金额
        buy_multiplier: 买入倍数

        返回：
        str: 执行金额描述
        """
        if action == 'strong_buy':
            return f"买入{buy_multiplier:.1f}×定额"
        elif action == 'buy':
            return f"买入{buy_multiplier:.1f}×定额"
        elif action == 'weak_buy':
            return f"买入{buy_multiplier:.1f}×定额"
        elif action in ['sell', 'weak_sell']:
            if isinstance(redeem_amount, float) and redeem_amount < 1:
                # 比例赎回
                return f"赎回{redeem_amount:.0%}仓位"
            else:
                # 固定金额赎回
                return f"赎回¥{redeem_amount}"
        else:
            return "持有不动"
    
    def _get_default_strategy(self, today_return: float = 0.0, prev_day_return: float = 0.0) -> Dict:
        """
        获取默认策略
        
        参数：
        today_return: 当日收益率（%）
        prev_day_return: 前一日收益率（%）
        
        返回：
        dict: 默认策略结果
        """
        # 根据收益率情况生成更具体的状态标签
        if today_return > 0:
            if prev_day_return > 0:
                status_label = "🟢 **温和上涨**"
                operation_suggestion = "基金温和上涨，建议持有"
            else:
                status_label = "🔵 **小幅反转**"
                operation_suggestion = "基金小幅反转，建议观望"
        elif today_return < 0:
            if prev_day_return < 0:
                status_label = "🔴 **温和下跌**"
                operation_suggestion = "基金温和下跌，建议观望"
            else:
                status_label = "🟣 **小幅回调**"
                operation_suggestion = "基金小幅回调，建议观望"
        else:
            status_label = "⚪ **平稳**"
            operation_suggestion = "基金走势平稳，建议持有"
        
        return {
            'strategy_name': 'default',
            'action': 'hold',
            'buy_multiplier': 0.0,
            'redeem_amount': 0,
            'status_label': status_label,
            'operation_suggestion': operation_suggestion,
            'execution_amount': "持有不动",
            'comparison_value': today_return - prev_day_return
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