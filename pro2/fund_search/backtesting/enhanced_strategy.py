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
        import sys
        import os
        
        # 添加shared模块路径
        backtesting_dir = os.path.dirname(os.path.abspath(__file__))
        shared_path = os.path.normpath(os.path.join(backtesting_dir, '..', 'shared'))
        
        # 确保路径被正确添加
        if shared_path not in sys.path:
            sys.path.insert(0, shared_path)
        
        try:
            from shared.enhanced_config import INVESTMENT_STRATEGY_CONFIG
            self.config = INVESTMENT_STRATEGY_CONFIG
        except (ModuleNotFoundError, ImportError):
            # 如果找不到配置，使用默认配置
            self.config = self._get_default_config()
        
        # 从YAML配置文件加载策略规则
        self.strategy_rules = self._load_strategy_rules_from_yaml()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            'buy_multipliers': {
                'strong_buy': 1.5,
                'buy': 1.0,
                'weak_buy': 0.6,
                'hold': 0.0
            },
            'global_risk_control': {
                'max_single_fund_position': 0.3,
                'volatility_high_threshold': 0.25,
                'volatility_high_multiplier': 0.7,
                'small_fund_multiplier': 0.8
            },
            'fundamental_analysis': {
                'min_history_days': 90,
                'good_sharpe_threshold': 1.0,
                'good_max_drawdown_threshold': 0.15,
                'min_win_rate': 0.5
            },
            'technical_analysis': {
                'strong_trend_threshold': 1.0,
                'reversal_threshold': 0.8
            },
            'market_analysis': {
                'bullish_threshold': 0.5,
                'high_volatility_threshold': 0.25
            },
            'risk_management': {
                'max_position_ratio': 0.3,
                'max_drawdown_limit': 0.15,
                'concentration_limit': 0.4,
                'high_volatility_limit': 0.30,
                'min_scale_limit': 1e8
            }
        }

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
    
    def calculate_investment_score(self, fund_code: str, today_return: float, 
                                   prev_day_return: float, market_data: Optional[Dict] = None) -> Dict:
        """
        计算投资综合评分（多层过滤机制）
        
        参数：
        fund_code: 基金代码
        today_return: 当日收益率（%）
        prev_day_return: 前一日收益率（%）
        market_data: 市场数据（可选）
        
        返回：
        dict: 包含综合评分和各维度评分的字典
        """
        try:
            # 第一层：基金基本面评分（权重30%）
            fund_score = self._calculate_fund_score(fund_code)
            
            # 第二层：技术指标评分（权重40%）
            tech_score = self._calculate_technical_score(today_return, prev_day_return)
            
            # 第三层：市场环境评分（权重30%）
            market_score = self._calculate_market_score(market_data)
            
            # 计算综合评分
            composite_score = (
                fund_score['score'] * 0.30 +
                tech_score['score'] * 0.40 +
                market_score['score'] * 0.30
            )
            
            # 决定是否通过多层过滤
            passed_filters = composite_score >= 0.5
            
            return {
                'composite_score': composite_score,
                'passed_filters': passed_filters,
                'fund_score': fund_score,
                'tech_score': tech_score,
                'market_score': market_score,
                'weight_allocation': {
                    'fund': 0.30,
                    'technical': 0.40,
                    'market': 0.30
                }
            }
            
        except Exception as e:
            logger.error(f"计算投资评分失败: {str(e)}")
            return {
                'composite_score': 0.5,
                'passed_filters': True,
                'fund_score': {'score': 0.5, 'details': '计算失败，使用默认值'},
                'tech_score': {'score': 0.5, 'details': '计算失败，使用默认值'},
                'market_score': {'score': 0.5, 'details': '计算失败，使用默认值'},
                'weight_allocation': {'fund': 0.30, 'technical': 0.40, 'market': 0.30}
            }
    
    def _calculate_fund_score(self, fund_code: str) -> Dict:
        """
        计算基金基本面评分（第一层过滤）
        
        参数：
        fund_code: 基金代码
        
        返回：
        dict: 基金基本面评分和详细信息
        """
        try:
            # 从配置中获取基金评分参数
            fund_config = self.config.get('fundamental_analysis', {})
            min_history_days = fund_config.get('min_history_days', 90)
            good_sharpe_threshold = fund_config.get('good_sharpe_threshold', 1.0)
            good_max_drawdown_threshold = fund_config.get('good_max_drawdown_threshold', 0.15)
            min_win_rate = fund_config.get('min_win_rate', 0.5)
            
            # 这里应该从数据库获取基金的绩效数据
            # 暂时使用模拟数据进行演示
            fund_metrics = self._get_fund_metrics_from_db(fund_code)
            
            if not fund_metrics:
                return {
                    'score': 0.5,
                    'details': '无历史数据，使用中性评分',
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'win_rate': 0.0,
                    'annual_return': 0.0
                }
            
            sharpe_ratio = fund_metrics.get('sharpe_ratio', 0.0)
            max_drawdown = abs(fund_metrics.get('max_drawdown', 0.0))
            win_rate = fund_metrics.get('win_rate', 0.5)
            annual_return = fund_metrics.get('annual_return', 0.0)
            
            # 计算各维度得分
            sharpe_score = min(1.0, max(0.0, sharpe_ratio / (good_sharpe_threshold * 2)))
            drawdown_score = 1.0 if max_drawdown < good_max_drawdown_threshold else max(0.0, 1 - max_drawdown)
            win_rate_score = win_rate
            return_score = min(1.0, max(0.0, annual_return / 0.3))
            
            # 综合基金基本面评分
            fund_score = (
                sharpe_score * 0.30 +
                drawdown_score * 0.25 +
                win_rate_score * 0.25 +
                return_score * 0.20
            )
            
            details = []
            if sharpe_ratio > good_sharpe_threshold:
                details.append(f"夏普比率优秀({sharpe_ratio:.2f})")
            if max_drawdown < good_max_drawdown_threshold:
                details.append(f"最大回撤可控({max_drawdown:.1%})")
            if win_rate > min_win_rate:
                details.append(f"胜率良好({win_rate:.1%})")
            if annual_return > 0.1:
                details.append(f"年化收益可观({annual_return:.1%})")
            
            return {
                'score': fund_score,
                'details': '，'.join(details) if details else '表现一般',
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'annual_return': annual_return
            }
            
        except Exception as e:
            logger.error(f"计算基金基本面评分失败: {str(e)}")
            return {'score': 0.5, 'details': f'计算错误: {str(e)}'}
    
    def _get_fund_metrics_from_db(self, fund_code: str) -> Optional[Dict]:
        """
        从数据库获取基金绩效指标
        
        参数：
        fund_code: 基金代码
        
        返回：
        dict: 基金绩效指标或None
        """
        try:
            # 这里应该实现实际的数据库查询逻辑
            # 暂时返回None表示无数据
            return None
            
        except Exception as e:
            logger.error(f"获取基金绩效数据失败: {str(e)}")
            return None
    
    def _calculate_technical_score(self, today_return: float, prev_day_return: float) -> Dict:
        """
        计算技术指标评分（第二层过滤）
        
        参数：
        today_return: 当日收益率（%）
        prev_day_return: 前一日收益率（%）
        
        返回：
        dict: 技术指标评分和详细信息
        """
        try:
            tech_config = self.config.get('technical_analysis', {})
            strong_trend_threshold = tech_config.get('strong_trend_threshold', 1.0)
            reversal_threshold = tech_config.get('reversal_threshold', 0.8)
            
            return_diff = today_return - prev_day_return
            
            # 计算趋势强度
            abs_today = abs(today_return)
            abs_prev = abs(prev_day_return)
            
            # 趋势评分
            if today_return > 0 and prev_day_return > 0:
                if abs_today > strong_trend_threshold and abs_prev > strong_trend_threshold:
                    trend_score = 1.0
                    trend_type = "双涨强势"
                elif abs_today > 0.3 or abs_prev > 0.3:
                    trend_score = 0.8
                    trend_type = "温和上涨"
                else:
                    trend_score = 0.6
                    trend_type = "小幅上涨"
            elif today_return < 0 and prev_day_return < 0:
                trend_score = 0.3
                trend_type = "连续下跌"
            elif today_return > 0 and prev_day_return < 0:
                trend_score = 0.9 if today_return > reversal_threshold else 0.7
                trend_type = "反转上涨"
            elif today_return < 0 and prev_day_return > 0:
                trend_score = 0.2
                trend_type = "反转下跌"
            else:
                trend_score = 0.5
                trend_type = "横盘整理"
            
            # 动量评分
            if return_diff > 0.5:
                momentum_score = 1.0
                momentum_type = "加速上涨"
            elif return_diff > 0:
                momentum_score = 0.7
                momentum_type = "上涨放缓"
            elif return_diff > -0.5:
                momentum_score = 0.4
                momentum_type = "下跌放缓"
            else:
                momentum_score = 0.2
                momentum_type = "加速下跌"
            
            # 综合技术评分
            tech_score = trend_score * 0.6 + momentum_score * 0.4
            
            return {
                'score': tech_score,
                'details': f"{trend_type}，{momentum_type}",
                'trend_score': trend_score,
                'momentum_score': momentum_score,
                'return_diff': return_diff
            }
            
        except Exception as e:
            logger.error(f"计算技术指标评分失败: {str(e)}")
            return {'score': 0.5, 'details': f'计算错误: {str(e)}'}
    
    def _calculate_market_score(self, market_data: Optional[Dict] = None) -> Dict:
        """
        计算市场环境评分（第三层过滤）
        
        参数：
        market_data: 市场数据（可选），包含：
            - market_index_return: 大盘指数收益率
            - market_sentiment: 市场情绪指数(0-1)
            - volatility_index: 波动率指数
            - trading_volume_ratio: 成交量比率
        
        返回：
        dict: 市场环境评分和详细信息
        """
        try:
            market_config = self.config.get('market_analysis', {})
            bullish_threshold = market_config.get('bullish_threshold', 0.5)
            high_volatility_threshold = market_config.get('high_volatility_threshold', 0.25)
            
            if market_data is None:
                market_data = {}
            
            market_index_return = market_data.get('market_index_return', 0.0)
            market_sentiment = market_data.get('market_sentiment', 0.5)
            volatility_index = market_data.get('volatility_index', 0.15)
            volume_ratio = market_data.get('trading_volume_ratio', 1.0)
            
            # 指数评分
            if market_index_return > bullish_threshold:
                index_score = 1.0
                index_type = "大盘强势"
            elif market_index_return > 0:
                index_score = 0.7
                index_type = "大盘温和"
            elif market_index_return > -bullish_threshold:
                index_score = 0.4
                index_type = "大盘调整"
            else:
                index_score = 0.2
                index_type = "大盘弱势"
            
            # 情绪评分
            if market_sentiment > 0.7:
                sentiment_score = 0.8
                sentiment_type = "情绪乐观"
            elif market_sentiment > 0.4:
                sentiment_score = 0.6
                sentiment_type = "情绪中性"
            else:
                sentiment_score = 0.3
                sentiment_type = "情绪悲观"
            
            # 波动率评分（低波动是加分项）
            if volatility_index < high_volatility_threshold * 0.5:
                vol_score = 0.9
                vol_type = "波动稳定"
            elif volatility_index < high_volatility_threshold:
                vol_score = 0.7
                vol_type = "波动正常"
            elif volatility_index < 0.35:
                vol_score = 0.4
                vol_type = "波动较大"
            else:
                vol_score = 0.2
                vol_type = "波动剧烈"
            
            # 成交量评分
            if volume_ratio > 1.5:
                volume_score = 0.8
                volume_type = "放量活跃"
            elif volume_ratio > 0.8:
                volume_score = 0.6
                volume_type = "量能正常"
            else:
                volume_score = 0.4
                volume_type = "缩量低迷"
            
            # 综合市场评分
            market_score = (
                index_score * 0.35 +
                sentiment_score * 0.25 +
                vol_score * 0.25 +
                volume_score * 0.15
            )
            
            return {
                'score': market_score,
                'details': f"{index_type}，{sentiment_type}，{vol_type}，{volume_type}",
                'index_score': index_score,
                'sentiment_score': sentiment_score,
                'vol_score': vol_score,
                'volume_score': volume_score
            }
            
        except Exception as e:
            logger.error(f"计算市场环境评分失败: {str(e)}")
            return {'score': 0.5, 'details': f'计算错误: {str(e)}'}
    
    def get_dynamic_thresholds(self, fund_code: str, indicator: str = 'return_diff') -> Dict:
        """
        获取动态阈值（基于基金历史波动率）
        
        参数：
        fund_code: 基金代码
        indicator: 指标名称
        
        返回：
        dict: 动态阈值字典
        """
        try:
            # 获取基金历史波动率
            volatility = self._calculate_historical_volatility(fund_code)
            
            if volatility is None:
                # 使用默认配置
                return self._get_default_thresholds()
            
            # 基于波动率计算动态阈值
            volatility_config = self.config.get('dynamic_thresholds', {})
            base_multiplier = volatility_config.get('base_multiplier', 0.5)
            max_multiplier = volatility_config.get('max_multiplier', 1.5)
            min_multiplier = volatility_config.get('min_multiplier', 0.3)
            
            # 动态调整系数
            adjustment_factor = max(min_multiplier, min(max_multiplier, base_multiplier * (1 + volatility)))
            
            # 计算动态阈值
            default_thresholds = self._get_default_thresholds()
            dynamic_thresholds = {}
            
            for key, value in default_thresholds.items():
                if isinstance(value, tuple):
                    min_val, max_val = value
                    if isinstance(min_val, (int, float)) and isinstance(max_val, (int, float)):
                        # 调整阈值范围
                        new_min = min_val * adjustment_factor
                        new_max = max_val * adjustment_factor
                        dynamic_thresholds[key] = (new_min, new_max)
                    else:
                        dynamic_thresholds[key] = value
                else:
                    dynamic_thresholds[key] = value
            
            return dynamic_thresholds
            
        except Exception as e:
            logger.error(f"计算动态阈值失败: {str(e)}")
            return self._get_default_thresholds()
    
    def _get_default_thresholds(self) -> Dict:
        """
        获取默认阈值配置
        
        返回：
        dict: 默认阈值配置
        """
        return {
            'strong_trend_high': (1.0, float('inf')),
            'strong_trend_low': (0.5, float('inf')),
            'moderate_trend_high': (0.3, 1.0),
            'moderate_trend_low': (0.2, 0.5),
            'reversal_high': (0.5, float('inf')),
            'reversal_low': (-0.5, 0.5),
            'steady_high': (0.0, 0.1),
            'steady_low': (-0.3, 0.0),
            'decline_high': (-float('inf'), -0.5),
            'decline_low': (-float('inf'), -0.5)
        }
    
    def _calculate_historical_volatility(self, fund_code: str) -> Optional[float]:
        """
        计算基金历史波动率
        
        参数：
        fund_code: 基金代码
        
        返回：
        float: 年化波动率或None
        """
        try:
            # 这里应该从数据库获取历史净值计算波动率
            # 暂时返回None表示使用默认配置
            return None
            
        except Exception as e:
            logger.error(f"计算历史波动率失败: {str(e)}")
            return None
    
    def calculate_kelly_position(self, fund_code: str, total_capital: float, 
                                 base_position: float = 100.0) -> Dict:
        """
        使用凯利公式计算最优仓位
        
        参数：
        fund_code: 基金代码
        total_capital: 总资金
        base_position: 基础仓位金额
        
        返回：
        dict: 仓位计算结果
        """
        try:
            # 获取基金绩效指标
            fund_metrics = self._get_fund_metrics_from_db(fund_code)
            
            if not fund_metrics:
                # 使用默认配置
                return {
                    'kelly_fraction': 0.5,
                    'half_kelly_fraction': 0.25,
                    'recommended_position': base_position,
                    'max_position': total_capital * 0.3,
                    'position_ratio': base_position / total_capital,
                    'reason': '无历史数据，使用默认配置'
                }
            
            win_rate = fund_metrics.get('win_rate', 0.5)
            avg_win = fund_metrics.get('avg_win_return', 0.02)
            avg_loss = abs(fund_metrics.get('avg_loss_return', 0.02))
            
            # 避免除零错误
            if avg_loss <= 0:
                avg_loss = 0.01
            
            # 凯利公式: f* = (bp - q) / b
            # b = 盈亏比, p = 胜率, q = 1 - p
            win_loss_ratio = avg_win / avg_loss
            kelly_fraction = (win_loss_ratio * win_rate - (1 - win_rate)) / win_loss_ratio
            
            # 限制凯利比例在合理范围内
            kelly_fraction = max(0.0, min(0.95, kelly_fraction))
            
            # 半凯利（降低风险）
            half_kelly = kelly_fraction * 0.5
            
            # 计算推荐仓位
            kelly_position = total_capital * kelly_fraction
            half_kelly_position = total_capital * half_kelly
            
            # 全局仓位限制
            risk_config = self.config.get('risk_management', {})
            max_position_ratio = risk_config.get('max_position_ratio', 0.3)
            max_single_fund_position = risk_config.get('max_single_fund_position', 0.3)
            
            max_position = total_capital * max_position_ratio
            
            # 应用限制
            recommended_position = min(half_kelly_position, max_position)
            
            # 确保不低于基础仓位
            recommended_position = max(recommended_position, base_position)
            
            return {
                'kelly_fraction': kelly_fraction,
                'half_kelly_fraction': half_kelly,
                'win_rate': win_rate,
                'win_loss_ratio': win_loss_ratio,
                'kelly_position': kelly_position,
                'recommended_position': recommended_position,
                'max_position': max_position,
                'position_ratio': recommended_position / total_capital,
                'reason': '基于凯利公式计算' if kelly_fraction > 0 else '凯利公式建议空仓'
            }
            
        except Exception as e:
            logger.error(f"计算凯利仓位失败: {str(e)}")
            return {
                'kelly_fraction': 0.25,
                'half_kelly_fraction': 0.125,
                'recommended_position': base_position,
                'max_position': total_capital * 0.3,
                'position_ratio': base_position / total_capital,
                'reason': f'计算错误，使用默认配置: {str(e)}'
            }
    
    def risk_management_check(self, fund_code: str, proposed_action: str,
                             current_position: float, total_capital: float,
                             market_data: Optional[Dict] = None) -> Dict:
        """
        风险控制检查
        
        参数：
        fund_code: 基金代码
        proposed_action: 拟议操作（buy, sell, hold）
        current_position: 当前持仓金额
        total_capital: 总资金
        market_data: 市场数据（可选）
        
        返回：
        dict: 风险检查结果
        """
        try:
            checks = []
            all_passed = True
            
            # 获取基金绩效数据
            fund_metrics = self._get_fund_metrics_from_db(fund_code)
            
            # 1. 检查最大回撤
            max_drawdown = abs(fund_metrics.get('max_drawdown', 0.0)) if fund_metrics else 0.0
            risk_config = self.config.get('risk_management', {})
            max_drawdown_limit = risk_config.get('max_drawdown_limit', 0.15)
            
            if max_drawdown > max_drawdown_limit:
                checks.append({
                    'check_name': 'drawdown_risk',
                    'passed': False,
                    'message': f'当前回撤({max_drawdown:.1%})超过限制({max_drawdown_limit:.1%})',
                    'severity': 'high'
                })
                all_passed = False
            else:
                checks.append({
                    'check_name': 'drawdown_risk',
                    'passed': True,
                    'message': f'当前回撤({max_drawdown:.1%})在可控范围',
                    'severity': 'low'
                })
            
            # 2. 检查持仓集中度
            position_ratio = current_position / total_capital
            concentration_limit = risk_config.get('concentration_limit', 0.4)
            
            if position_ratio > concentration_limit:
                checks.append({
                    'check_name': 'concentration_risk',
                    'passed': False,
                    'message': f'持仓集中度({position_ratio:.1%})过高，建议不超过{concentration_limit:.0%}',
                    'severity': 'medium'
                })
                all_passed = False
            else:
                checks.append({
                    'check_name': 'concentration_risk',
                    'passed': True,
                    'message': f'持仓集中度({position_ratio:.1%})合理',
                    'severity': 'low'
                })
            
            # 3. 检查流动性（模拟）
            if proposed_action == 'sell':
                avg_volume = fund_metrics.get('avg_daily_volume', float('inf')) if fund_metrics else float('inf')
                if avg_volume != float('inf') and current_position > avg_volume * 0.1:
                    checks.append({
                        'check_name': 'liquidity_risk',
                        'passed': False,
                        'message': f'卖出金额({current_position:.0f})可能影响流动性（日均{avg_volume:.0f})',
                        'severity': 'medium'
                    })
                    all_passed = False
                else:
                    checks.append({
                        'check_name': 'liquidity_risk',
                        'passed': True,
                        'message': '流动性良好',
                        'severity': 'low'
                    })
            
            # 4. 检查市场环境
            if market_data:
                volatility_index = market_data.get('volatility_index', 0.15)
                high_volatility_limit = risk_config.get('high_volatility_limit', 0.30)
                
                if volatility_index > high_volatility_limit:
                    checks.append({
                        'check_name': 'market_volatility',
                        'passed': False,
                        'message': f'市场波动率({volatility_index:.1%})过高，建议谨慎操作',
                        'severity': 'medium'
                    })
                    all_passed = False
                else:
                    checks.append({
                        'check_name': 'market_volatility',
                        'passed': True,
                        'message': f'市场波动率({volatility_index:.1%})正常',
                        'severity': 'low'
                    })
            
            # 5. 检查基金规模（模拟）
            fund_scale = fund_metrics.get('fund_scale', 0) if fund_metrics else 0
            min_scale_limit = risk_config.get('min_scale_limit', 1e8)
            
            if fund_scale > 0 and fund_scale < min_scale_limit:
                checks.append({
                    'check_name': 'fund_scale_risk',
                    'passed': False,
                    'message': f'基金规模({fund_scale/1e8:.1f}亿)偏小，存在清盘风险',
                    'severity': 'medium'
                })
                all_passed = False
            else:
                checks.append({
                    'check_name': 'fund_scale_risk',
                    'passed': True,
                    'message': f'基金规模充足',
                    'severity': 'low'
                })
            
            # 生成最终建议
            if all_passed:
                final_action = proposed_action
                final_message = '通过所有风险检查，建议执行操作'
            else:
                # 根据失败的检查调整操作建议
                high_severity_failed = any(c['severity'] == 'high' and not c['passed'] for c in checks)
                if high_severity_failed:
                    final_action = 'hold'
                    final_message = '存在高风险因素，建议持有观望'
                else:
                    final_action = proposed_action
                    final_message = '存在中等风险因素，建议谨慎操作'
            
            return {
                'all_passed': all_passed,
                'final_action': final_action,
                'final_message': final_message,
                'checks': checks,
                'position_ratio': position_ratio,
                'max_drawdown': max_drawdown
            }
            
        except Exception as e:
            logger.error(f"风险控制检查失败: {str(e)}")
            return {
                'all_passed': True,
                'final_action': proposed_action,
                'final_message': f'风险检查出错，建议维持原操作: {str(e)}',
                'checks': [],
                'position_ratio': current_position / total_capital,
                'max_drawdown': 0.0
            }


if __name__ == "__main__":
    import sys
    import os
    
    # 添加shared模块路径（使用绝对路径）
    shared_path = r"d:\coding\trae_project\py4zinia\pro2\fund_search\shared"
    sys.path.insert(0, shared_path)
    
    print("=" * 80)
    print("增强版投资策略测试")
    print("=" * 80)
    
    strategy = EnhancedInvestmentStrategy()
    
    # 1. 测试基础策略分析
    print("\n【1. 基础策略分析测试】")
    print("-" * 40)
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
        print(f"今日: {today:+.1f}%, 昨日: {prev:+.1f}% -> {result['status_label']}")
        print(f"  操作: {result['execution_amount']}, 建议: {result['operation_suggestion']}")
    
    # 2. 测试绩效指标增强分析
    print("\n\n【2. 绩效增强策略分析测试】")
    print("-" * 40)
    performance_metrics = {
        'sharpe_ratio': 1.5,
        'max_drawdown': -0.1,
        'volatility': 0.15,
        'win_rate': 0.6,
        'composite_score': 0.8
    }
    
    result = strategy.analyze_strategy(1.2, -0.5, performance_metrics)
    print(f"绩效增强分析: {result['status_label']}")
    print(f"  操作: {result['execution_amount']}")
    print(f"  建议: {result['operation_suggestion']}")
    
    # 3. 测试多层过滤机制
    print("\n\n【3. 多层过滤机制测试】")
    print("-" * 40)
    fund_code = "000001"
    
    market_data = {
        'market_index_return': 0.8,
        'market_sentiment': 0.65,
        'volatility_index': 0.18,
        'trading_volume_ratio': 1.2
    }
    
    for today, prev in [(2.5, 1.2), (0.8, 0.6), (-0.8, 0.8)]:
        score_result = strategy.calculate_investment_score(fund_code, today, prev, market_data)
        print(f"\n今日: {today:+.1f}%, 昨日: {prev:+.1f}% 的多层过滤结果:")
        print(f"  综合评分: {score_result['composite_score']:.2f} (通过: {score_result['passed_filters']})")
        print(f"  基金基本面({score_result['weight_allocation']['fund']:.0%}): {score_result['fund_score']['score']:.2f} - {score_result['fund_score']['details']}")
        print(f"  技术指标({score_result['weight_allocation']['technical']:.0%}): {score_result['tech_score']['score']:.2f} - {score_result['tech_score']['details']}")
        print(f"  市场环境({score_result['weight_allocation']['market']:.0%}): {score_result['market_score']['score']:.2f} - {score_result['market_score']['details']}")
    
    # 4. 测试动态阈值调整
    print("\n\n【4. 动态阈值调整测试】")
    print("-" * 40)
    thresholds = strategy.get_dynamic_thresholds(fund_code)
    print(f"基金 {fund_code} 的动态阈值:")
    for key, value in thresholds.items():
        print(f"  {key}: {value}")
    
    # 5. 测试凯利公式仓位计算
    print("\n\n【5. 凯利公式仓位计算测试】")
    print("-" * 40)
    total_capital = 100000
    base_position = 500
    
    kelly_result = strategy.calculate_kelly_position(fund_code, total_capital, base_position)
    print(f"总资金: ¥{total_capital:,.0f}, 基础仓位: ¥{base_position:.0f}")
    print(f"  全凯利比例: {kelly_result['kelly_fraction']:.2%}")
    print(f"  半凯利比例: {kelly_result['half_kelly_fraction']:.2%}")
    print(f"  推荐仓位: ¥{kelly_result['recommended_position']:,.2f}")
    print(f"  仓位比例: {kelly_result['position_ratio']:.2%}")
    print(f"  最大仓位: ¥{kelly_result['max_position']:,.2f}")
    print(f"  原因: {kelly_result['reason']}")
    
    # 6. 测试风险控制检查
    print("\n\n【6. 风险控制检查测试】")
    print("-" * 40)
    
    risk_check = strategy.risk_management_check(
        fund_code="000001",
        proposed_action="buy",
        current_position=30000,
        total_capital=100000,
        market_data=market_data
    )
    
    print(f"拟议操作: {risk_check['final_action']}")
    print(f"最终建议: {risk_check['final_message']}")
    print(f"通过所有检查: {risk_check['all_passed']}")
    print(f"当前持仓比例: {risk_check['position_ratio']:.1%}")
    print(f"当前最大回撤: {risk_check['max_drawdown']:.1%}")
    print("\n详细检查:")
    for check in risk_check['checks']:
        status = "✓" if check['passed'] else "✗"
        print(f"  {status} {check['check_name']}: {check['message']} [{check['severity']}]")
    
    # 7. 测试策略汇总
    print("\n\n【7. 策略汇总测试】")
    print("-" * 40)
    strategy_results = [
        strategy.analyze_strategy(2.5, 1.2),
        strategy.analyze_strategy(0.8, 0.6),
        strategy.analyze_strategy(-0.8, 0.8),
        strategy.analyze_strategy(0.01, -0.2),
    ]
    
    summary = strategy.generate_strategy_summary(strategy_results)
    print(f"分析基金数量: {summary['total_funds']}")
    print(f"操作分布: {summary['action_distribution']}")
    print(f"平均买入倍数: {summary['avg_buy_multiplier']:.2f}")
    print(f"买入信号: {summary['buy_signals']}, 卖出信号: {summary['sell_signals']}, 持有信号: {summary['hold_signals']}")
    
    # 8. 综合测试：完整投资决策流程
    print("\n\n【8. 综合投资决策测试】")
    print("-" * 40)
    test_fund = "000001"
    test_market = {
        'market_index_return': 0.5,
        'market_sentiment': 0.6,
        'volatility_index': 0.2,
        'trading_volume_ratio': 1.0
    }
    
    for today, prev in [(1.5, 0.8), (-1.2, 0.5), (0.3, -0.2)]:
        print(f"\n--- 场景: 今日{today:+.1f}%, 昨日{prev:+.1f}% ---")
        
        # 步骤1: 基础策略分析
        base_result = strategy.analyze_strategy(today, prev)
        print(f"1. 基础策略: {base_result['status_label']}")
        
        # 步骤2: 多层过滤
        score_result = strategy.calculate_investment_score(test_fund, today, prev, test_market)
        print(f"2. 综合评分: {score_result['composite_score']:.2f} ({'通过' if score_result['passed_filters'] else '未通过'}过滤)")
        
        # 步骤3: 动态阈值
        thresholds = strategy.get_dynamic_thresholds(test_fund)
        
        # 步骤4: 凯利仓位
        kelly = strategy.calculate_kelly_position(test_fund, 100000, 500)
        print(f"3. 推荐仓位: ¥{kelly['recommended_position']:,.0f} ({kelly['position_ratio']:.1%})")
        
        # 步骤5: 风险检查
        risk = strategy.risk_management_check(test_fund, base_result['action'], 30000, 100000, test_market)
        print(f"4. 风险检查: {risk['final_action']} ({risk['final_message']})")
        
        # 最终决策
        final_decision = risk['final_action'] if risk['all_passed'] else 'hold'
        final_amount = kelly['recommended_position'] if final_decision == 'buy' else 0
        print(f"5. 最终决策: {final_decision.upper()} - {'买入' if final_decision == 'buy' else '持有' if final_decision == 'hold' else '赎回'} ¥{final_amount:,.0f}")
    
    print("\n" + "=" * 80)
    print("测试完成!")
    print("=" * 80)
    
    summary = strategy.generate_strategy_summary(strategy_results)
    print(f"\n策略汇总: {summary}")