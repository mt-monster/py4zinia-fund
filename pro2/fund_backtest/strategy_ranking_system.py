#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略排名和推荐系统
Strategy Ranking and Recommendation System

基于多维度指标对策略进行综合排名，提供智能推荐
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

class RiskProfile(Enum):
    """风险偏好类型"""
    CONSERVATIVE = "保守型"
    MODERATE = "稳健型" 
    AGGRESSIVE = "激进型"

@dataclass
class RankingCriteria:
    """排名标准配置"""
    return_weight: float = 0.3      # 收益权重
    risk_weight: float = 0.2        # 风险权重
    sharpe_weight: float = 0.25     # 夏普比率权重
    consistency_weight: float = 0.15  # 稳定性权重
    trade_frequency_weight: float = 0.1  # 交易频率权重

class StrategyRankingSystem:
    """
    策略排名和推荐系统
    
    功能：
    1. 多维度策略排名
    2. 风险偏好匹配
    3. 智能策略推荐
    4. 组合策略建议
    """
    
    def __init__(self):
        """初始化排名系统"""
        self.ranking_criteria = RankingCriteria()
        self.strategy_scores = {}
        self.risk_profiles = {
            RiskProfile.CONSERVATIVE: RankingCriteria(
                return_weight=0.15, risk_weight=0.35, sharpe_weight=0.25,
                consistency_weight=0.20, trade_frequency_weight=0.05
            ),
            RiskProfile.MODERATE: RankingCriteria(
                return_weight=0.25, risk_weight=0.25, sharpe_weight=0.25,
                consistency_weight=0.15, trade_frequency_weight=0.10
            ),
            RiskProfile.AGGRESSIVE: RankingCriteria(
                return_weight=0.40, risk_weight=0.10, sharpe_weight=0.30,
                consistency_weight=0.10, trade_frequency_weight=0.10
            )
        }
    
    def normalize_metric(self, value: float, metric_type: str, all_values: List[float]) -> float:
        """
        标准化指标值到0-1范围
        
        参数：
        value: 原始值
        metric_type: 指标类型 ('return', 'risk', 'sharpe', 'consistency', 'trade_freq')
        all_values: 所有策略的该指标值
        
        返回：
        float: 标准化后的值 (0-1)
        """
        if not all_values or len(set(all_values)) == 1:
            return 0.5
        
        min_val, max_val = min(all_values), max(all_values)
        
        if max_val == min_val:
            return 0.5
        
        if metric_type in ['return', 'sharpe', 'consistency']:
            # 越大越好的指标
            return (value - min_val) / (max_val - min_val)
        elif metric_type in ['risk', 'trade_freq']:
            # 越小越好的指标
            return 1 - (value - min_val) / (max_val - min_val)
        else:
            return 0.5
    
    def calculate_consistency_score(self, metrics: Dict) -> float:
        """
        计算策略稳定性得分
        
        参数：
        metrics: 策略指标字典
        
        返回：
        float: 稳定性得分 (0-1)
        """
        # 基于多个指标计算稳定性
        sharpe = metrics.get('sharpe_ratio', 0)
        max_drawdown = abs(metrics.get('max_drawdown', 0))
        win_rate = metrics.get('win_rate', 0)
        
        # 夏普比率贡献 (0-0.4分)
        sharpe_score = min(max(sharpe / 2.0, 0), 1) * 0.4
        
        # 回撤控制贡献 (0-0.3分)
        drawdown_score = max(0, 1 - max_drawdown * 10) * 0.3
        
        # 胜率贡献 (0-0.3分)
        winrate_score = win_rate * 0.3
        
        return sharpe_score + drawdown_score + winrate_score
    
    def calculate_trade_frequency_score(self, metrics: Dict) -> float:
        """
        计算交易频率得分 (适中为好)
        
        参数：
        metrics: 策略指标字典
        
        返回：
        float: 交易频率得分 (0-1)
        """
        total_trades = metrics.get('total_trades', 0)
        
        # 假设回测期为252个交易日
        trading_days = 252
        
        if total_trades == 0:
            return 0
        
        # 计算交易频率 (每交易日交易次数)
        trade_frequency = total_trades / trading_days
        
        # 理想频率为每10-20个交易日交易一次
        if 0.05 <= trade_frequency <= 0.1:  # 10-20天一次
            return 1.0
        elif trade_frequency < 0.05:  # 交易太少
            return trade_frequency / 0.05
        elif trade_frequency > 0.1:  # 交易太频繁
            return max(0, 1 - (trade_frequency - 0.1) * 5)
        else:
            return 0.5
    
    def calculate_strategy_score(self, 
                                strategy_name: str,
                                metrics: Dict,
                                criteria: RankingCriteria) -> Dict:
        """
        计算策略综合得分
        
        参数：
        strategy_name: 策略名称
        metrics: 策略指标
        criteria: 评分标准
        
        返回：
        Dict: 包含各项得分和总分的字典
        """
        # 提取各项指标
        total_return = metrics.get('total_return', 0)
        max_drawdown = abs(metrics.get('max_drawdown', 0))
        sharpe_ratio = metrics.get('sharpe_ratio', 0)
        win_rate = metrics.get('win_rate', 0)
        total_trades = metrics.get('total_trades', 0)
        
        # 计算稳定性得分
        consistency_score = self.calculate_consistency_score(metrics)
        
        # 计算交易频率得分
        trade_freq_score = self.calculate_trade_frequency_score(metrics)
        
        # 计算综合得分
        total_score = (
            total_return * criteria.return_weight +
            (1 - max_drawdown) * criteria.risk_weight +
            min(max(sharpe_ratio / 2.0, 0), 1) * criteria.sharpe_weight +
            consistency_score * criteria.consistency_weight +
            trade_freq_score * criteria.trade_frequency_weight
        )
        
        return {
            'strategy_name': strategy_name,
            'total_score': total_score,
            'return_score': total_return,
            'risk_score': 1 - max_drawdown,
            'sharpe_score': min(max(sharpe_ratio / 2.0, 0), 1),
            'consistency_score': consistency_score,
            'trade_freq_score': trade_freq_score,
            'raw_metrics': metrics
        }
    
    def rank_strategies(self, 
                        strategy_metrics: Dict[str, Dict],
                        risk_profile: RiskProfile = RiskProfile.MODERATE) -> List[Dict]:
        """
        对策略进行排名
        
        参数：
        strategy_metrics: 策略指标字典
        risk_profile: 风险偏好
        
        返回：
        List[Dict]: 排名后的策略列表
        """
        # 获取对应风险偏好的评分标准
        criteria = self.risk_profiles[risk_profile]
        
        # 计算每个策略的得分
        strategy_scores = []
        for strategy_name, metrics in strategy_metrics.items():
            score_info = self.calculate_strategy_score(strategy_name, metrics, criteria)
            strategy_scores.append(score_info)
        
        # 按总分排序
        ranked_strategies = sorted(strategy_scores, key=lambda x: x['total_score'], reverse=True)
        
        # 添加排名
        for i, strategy in enumerate(ranked_strategies):
            strategy['rank'] = i + 1
        
        return ranked_strategies
    
    def recommend_strategy(self, 
                          ranked_strategies: List[Dict],
                          top_n: int = 3) -> Dict:
        """
        推荐最佳策略
        
        参数：
        ranked_strategies: 排名后的策略列表
        top_n: 推荐前N个策略
        
        返回：
        Dict: 推荐结果
        """
        if not ranked_strategies:
            return {'error': '没有可用的策略数据'}
        
        # 获取前N个策略
        top_strategies = ranked_strategies[:top_n]
        
        # 分析推荐理由
        best_strategy = top_strategies[0]
        recommendation_reasons = []
        
        # 基于得分分析推荐理由
        if best_strategy['sharpe_score'] > 0.7:
            recommendation_reasons.append("风险调整收益优秀")
        
        if best_strategy['consistency_score'] > 0.7:
            recommendation_reasons.append("策略表现稳定")
        
        if best_strategy['return_score'] > 0.3:
            recommendation_reasons.append("收益表现突出")
        
        if best_strategy['risk_score'] > 0.8:
            recommendation_reasons.append("风险控制良好")
        
        # 生成使用建议
        usage_suggestions = self.generate_usage_suggestions(best_strategy)
        
        return {
            'recommended_strategy': best_strategy,
            'alternative_strategies': top_strategies[1:] if len(top_strategies) > 1 else [],
            'recommendation_reasons': recommendation_reasons,
            'usage_suggestions': usage_suggestions,
            'confidence_level': self.calculate_confidence_level(best_strategy, ranked_strategies)
        }
    
    def generate_usage_suggestions(self, strategy: Dict) -> List[str]:
        """
        生成策略使用建议
        
        参数：
        strategy: 策略信息
        
        返回：
        List[str]: 使用建议列表
        """
        suggestions = []
        strategy_name = strategy['strategy_name'].lower()
        metrics = strategy['raw_metrics']
        
        # 基于策略类型的建议
        if 'dual_ma' in strategy_name:
            suggestions.append("适合趋势明显的市场环境")
            suggestions.append("建议关注均线交叉信号，严格执行")
            suggestions.append("可配合成交量分析提高准确性")
        
        elif 'mean_reversion' in strategy_name:
            suggestions.append("适合震荡市场，避免单边趋势")
            suggestions.append("建议设置合理的偏离阈值")
            suggestions.append("可结合支撑阻力位使用")
        
        elif 'target_value' in strategy_name:
            suggestions.append("适合长期稳健投资")
            suggestions.append("建议定期调整目标增长额")
            suggestions.append("适合定投投资者使用")
        
        elif 'grid' in strategy_name:
            suggestions.append("适合波动率适中的市场")
            suggestions.append("建议合理设置网格间距")
            suggestions.append("需要充足的资金支持")
        
        # 基于指标的建议
        if metrics['max_drawdown'] < -0.15:
            suggestions.append("注意：该策略回撤较大，建议控制仓位")
        
        if metrics['sharpe_ratio'] < 0.5:
            suggestions.append("建议：可考虑与其他策略组合使用")
        
        if metrics['total_trades'] > 100:
            suggestions.append("交易较频繁，注意交易成本影响")
        
        # 通用建议
        suggestions.append("建议：严格执行策略信号，避免情绪干扰")
        suggestions.append("建议：定期回顾策略表现，适时调整参数")
        
        return suggestions
    
    def calculate_confidence_level(self, best_strategy: Dict, all_strategies: List[Dict]) -> str:
        """
        计算推荐置信度
        
        参数：
        best_strategy: 最佳策略
        all_strategies: 所有策略
        
        返回：
        str: 置信度等级
        """
        if len(all_strategies) < 2:
            return "中等"
        
        # 计算最佳策略与第二名得分差距
        if len(all_strategies) > 1:
            second_best = all_strategies[1]
            score_gap = best_strategy['total_score'] - second_best['total_score']
            
            if score_gap > 0.15:
                return "很高"
            elif score_gap > 0.08:
                return "较高"
            elif score_gap > 0.03:
                return "中等"
            else:
                return "一般"
        
        return "中等"
    
    def create_portfolio_recommendation(self, 
                                       ranked_strategies: List[Dict],
                                       portfolio_size: int = 3) -> Dict:
        """
        创建策略组合建议
        
        参数：
        ranked_strategies: 排名后的策略列表
        portfolio_size: 组合大小
        
        返回：
        Dict: 组合建议
        """
        if len(ranked_strategies) < portfolio_size:
            portfolio_size = len(ranked_strategies)
        
        # 选择前N个策略
        selected_strategies = ranked_strategies[:portfolio_size]
        
        # 计算权重（基于得分）
        total_score = sum(s['total_score'] for s in selected_strategies)
        weights = [s['total_score'] / total_score for s in selected_strategies]
        
        # 分析组合特征
        portfolio_analysis = self.analyze_portfolio(selected_strategies, weights)
        
        return {
            'strategies': selected_strategies,
            'weights': weights,
            'analysis': portfolio_analysis,
            'diversification_benefit': self.calculate_diversification_benefit(selected_strategies)
        }
    
    def analyze_portfolio(self, strategies: List[Dict], weights: List[float]) -> Dict:
        """
        分析策略组合特征
        
        参数：
        strategies: 策略列表
        weights: 权重列表
        
        返回：
        Dict: 组合分析结果
        """
        # 加权平均指标
        weighted_return = sum(s['return_score'] * w for s, w in zip(strategies, weights))
        weighted_risk = sum(s['risk_score'] * w for s, w in zip(strategies, weights))
        weighted_sharpe = sum(s['sharpe_score'] * w for s, w in zip(strategies, weights))
        
        # 策略类型多样性
        strategy_types = set()
        for strategy in strategies:
            name = strategy['strategy_name'].lower()
            if 'dual_ma' in name:
                strategy_types.add('趋势')
            elif 'mean_reversion' in name:
                strategy_types.add('均值回归')
            elif 'target_value' in name:
                strategy_types.add('目标市值')
            elif 'grid' in name:
                strategy_types.add('网格')
        
        return {
            'expected_return_score': weighted_return,
            'expected_risk_score': weighted_risk,
            'expected_sharpe_score': weighted_sharpe,
            'strategy_diversity': len(strategy_types),
            'strategy_types': list(strategy_types)
        }
    
    def calculate_diversification_benefit(self, strategies: List[Dict]) -> str:
        """
        计算多样化收益
        
        参数：
        strategies: 策略列表
        
        返回：
        str: 多样化收益描述
        """
        if len(strategies) <= 1:
            return "无多样化收益"
        
        # 检查策略类型多样性
        strategy_types = set()
        for strategy in strategies:
            name = strategy['strategy_name'].lower()
            if 'dual_ma' in name:
                strategy_types.add('趋势')
            elif 'mean_reversion' in name:
                strategy_types.add('均值回归')
            elif 'target_value' in name:
                strategy_types.add('目标市值')
            elif 'grid' in name:
                strategy_types.add('网格')
        
        diversity_ratio = len(strategy_types) / len(strategies)
        
        if diversity_ratio >= 0.8:
            return "多样化收益很高"
        elif diversity_ratio >= 0.6:
            return "多样化收益较高"
        elif diversity_ratio >= 0.4:
            return "有一定多样化收益"
        else:
            return "多样化收益有限"

# 使用示例
if __name__ == "__main__":
    # 创建排名系统
    ranking_system = StrategyRankingSystem()
    
    # 模拟策略指标数据
    sample_metrics = {
        'dual_ma': {
            'total_return': 0.25,
            'max_drawdown': -0.12,
            'sharpe_ratio': 1.8,
            'win_rate': 0.65,
            'total_trades': 45
        },
        'mean_reversion': {
            'total_return': 0.18,
            'max_drawdown': -0.08,
            'sharpe_ratio': 1.5,
            'win_rate': 0.72,
            'total_trades': 38
        },
        'target_value': {
            'total_return': 0.15,
            'max_drawdown': -0.06,
            'sharpe_ratio': 1.3,
            'win_rate': 0.68,
            'total_trades': 25
        },
        'grid': {
            'total_return': 0.22,
            'max_drawdown': -0.10,
            'sharpe_ratio': 1.6,
            'win_rate': 0.70,
            'total_trades': 85
        }
    }
    
    # 对策略进行排名
    ranked_strategies = ranking_system.rank_strategies(sample_metrics, RiskProfile.MODERATE)
    
    # 生成推荐
    recommendation = ranking_system.recommend_strategy(ranked_strategies)
    
    # 创建组合建议
    portfolio_rec = ranking_system.create_portfolio_recommendation(ranked_strategies, 3)
    
    # 输出结果
    print("策略排名结果:")
    for strategy in ranked_strategies:
        print(f"{strategy['rank']}. {strategy['strategy_name']}: {strategy['total_score']:.3f}")
    
    print(f"\n推荐策略: {recommendation['recommended_strategy']['strategy_name']}")
    print(f"置信度: {recommendation['confidence_level']}")
    print("推荐理由:")
    for reason in recommendation['recommendation_reasons']:
        print(f"- {reason}")
    
    print(f"\n组合建议:")
    for i, (strategy, weight) in enumerate(zip(portfolio_rec['strategies'], portfolio_rec['weights'])):
        print(f"{i+1}. {strategy['strategy_name']}: {weight:.1%}")
    print(f"多样化收益: {portfolio_rec['diversification_benefit']}")