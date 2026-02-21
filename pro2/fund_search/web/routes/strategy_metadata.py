#!/usr/bin/env python
# coding: utf-8

"""
策略元数据模块
提供策略基本信息的获取功能
"""

import json
import logging

# 设置日志
logger = logging.getLogger(__name__)

def get_strategy_metadata():
    """获取策略元数据
    
    返回预定义的策略信息列表
    """
    try:
        # 预定义的策略数据
        strategies = [
            {
                'strategy_id': 'dual_ma',
                'name': '双均线策略',
                'description': '基于短期与长期移动平均线交叉信号进行交易。当短期均线上穿长期均线时产生买入信号，反之产生卖出信号。适合捕捉中长期趋势行情。',
                'total_return': 45.2,
                'annualized_return': 15.8,
                'annualized_volatility': 18.5,
                'max_drawdown': -22.3,
                'sharpe_ratio': 0.85,
                'win_rate': 58.7,
                'profit_loss_ratio': 1.42,
                'trades_count': 156,
                'final_value': 145200.0
            },
            {
                'strategy_id': 'mean_reversion',
                'name': '均值回归策略',
                'description': '基于价格偏离均值程度进行交易。当价格显著高于均值时卖出，低于均值时买入。适合震荡市场环境。',
                'total_return': 38.7,
                'annualized_return': 13.2,
                'annualized_volatility': 16.8,
                'max_drawdown': -18.9,
                'sharpe_ratio': 0.78,
                'win_rate': 62.3,
                'profit_loss_ratio': 1.28,
                'trades_count': 234,
                'final_value': 138700.0
            },
            {
                'strategy_id': 'target_value',
                'name': '目标市值策略',
                'description': '设定目标市值水平，当实际市值低于目标时补仓，高于目标时减仓。适合长期定投优化。',
                'total_return': 52.1,
                'annualized_return': 17.9,
                'annualized_volatility': 14.2,
                'max_drawdown': -15.6,
                'sharpe_ratio': 1.26,
                'win_rate': 67.8,
                'profit_loss_ratio': 1.65,
                'trades_count': 89,
                'final_value': 152100.0
            },
            {
                'strategy_id': 'grid',
                'name': '网格交易策略',
                'description': '在预设价格区间内设置多个买卖点位，价格触及相应价位时自动交易。适合波动较大的市场。',
                'total_return': 31.5,
                'annualized_return': 10.8,
                'annualized_volatility': 22.1,
                'max_drawdown': -28.4,
                'sharpe_ratio': 0.49,
                'win_rate': 54.2,
                'profit_loss_ratio': 1.15,
                'trades_count': 312,
                'final_value': 131500.0
            },
            {
                'strategy_id': 'enhanced_rule_based',
                'name': '增强型规则策略',
                'description': '综合多种技术指标和市场特征的复合策略。结合趋势判断、波动率调整和风险控制机制。',
                'total_return': 58.9,
                'annualized_return': 19.2,
                'annualized_volatility': 16.7,
                'max_drawdown': -20.1,
                'sharpe_ratio': 1.15,
                'win_rate': 65.4,
                'profit_loss_ratio': 1.78,
                'trades_count': 187,
                'final_value': 158900.0
            }
        ]
        
        logger.info(f"成功加载 {len(strategies)} 个策略元数据")
        return {'success': True, 'data': strategies}
        
    except Exception as e:
        logger.error(f"获取策略元数据失败: {str(e)}")
        return {'success': False, 'error': str(e)}