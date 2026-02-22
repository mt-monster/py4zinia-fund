#!/usr/bin/env python
# coding: utf-8

"""
内置策略模块
Builtin Strategies Module

提供系统预定义的投资策略模板，用户可以快速选择并应用这些策略
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ..core.strategy_models import CustomStrategyConfig, FilterCondition, StrategyValidator

logger = logging.getLogger(__name__)


@dataclass
class BuiltinStrategy:
    """
    内置策略模板数据类
    
    Attributes:
        key: 策略唯一标识（英文）
        name: 策略显示名称（中文）
        description: 策略描述
        config: 策略配置对象
    """
    key: str
    name: str
    description: str
    config: CustomStrategyConfig
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'key': self.key,
            'name': self.name,
            'description': self.description,
            'config': self.config.to_dict()
        }
    
    def to_summary_dict(self) -> Dict[str, str]:
        """转换为摘要字典（不含完整配置）"""
        return {
            'key': self.key,
            'name': self.name,
            'description': self.description
        }


class BuiltinStrategiesManager:
    """
    内置策略管理器
    
    负责加载、验证和提供内置策略模板
    """
    
    def __init__(self):
        self._strategies: Dict[str, BuiltinStrategy] = {}
        self._load_builtin_strategies()
        self._validate_strategies()
    
    def _load_builtin_strategies(self) -> None:
        """加载所有内置策略"""
        builtin_configs = self._get_builtin_strategy_configs()
        
        for key, config_data in builtin_configs.items():
            try:
                # 创建筛选条件列表
                filter_conditions = [
                    FilterCondition.from_dict(fc) 
                    for fc in config_data.get('filter_conditions', [])
                ]
                
                # 创建策略配置
                config = CustomStrategyConfig(
                    name=config_data['name'],
                    description=config_data.get('description', ''),
                    filter_conditions=filter_conditions,
                    filter_logic=config_data.get('filter_logic', 'AND'),
                    sort_field=config_data.get('sort_field', 'composite_score'),
                    sort_order=config_data.get('sort_order', 'DESC'),
                    select_count=config_data.get('select_count', 10),
                    weight_mode=config_data.get('weight_mode', 'equal'),
                    custom_weights=config_data.get('custom_weights', []),
                    max_positions=config_data.get('max_positions', 10),
                    trade_on_hold_day=config_data.get('trade_on_hold_day', False),
                    buy_condition=config_data.get('buy_condition', ''),
                    sell_condition=config_data.get('sell_condition', ''),
                    daily_stop_loss=config_data.get('daily_stop_loss', -0.05),
                    daily_take_profit=config_data.get('daily_take_profit', 0.10),
                    total_stop_loss=config_data.get('total_stop_loss', -0.15),
                    trailing_stop=config_data.get('trailing_stop', 0.0),
                    volatility_adjustment=config_data.get('volatility_adjustment', False)
                )
                
                # 创建内置策略对象
                strategy = BuiltinStrategy(
                    key=key,
                    name=config_data['name'],
                    description=config_data.get('description', ''),
                    config=config
                )
                
                self._strategies[key] = strategy
                
            except Exception as e:
                logger.error(f"加载内置策略 {key} 失败: {e}")
                continue
    
    def _validate_strategies(self) -> None:
        """验证加载的策略配置"""
        for key, strategy in self._strategies.items():
            is_valid, errors = StrategyValidator.validate_strategy_config(strategy.config)
            if not is_valid:
                error_msg = "; ".join([str(e) for e in errors])
                logger.warning(f"内置策略 {key} 配置验证失败: {error_msg}")
    
    def get_all(self) -> List[Dict[str, str]]:
        """获取所有内置策略摘要"""
        return [s.to_summary_dict() for s in self._strategies.values()]
    
    def get_by_key(self, key: str) -> Optional[BuiltinStrategy]:
        """根据key获取策略详情"""
        return self._strategies.get(key)
    
    def has_strategy(self, key: str) -> bool:
        """检查策略是否存在"""
        return key in self._strategies

    def _get_builtin_strategy_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        获取内置策略配置字典
        这里硬编码了一些经典策略，也可以改为从配置文件加载
        """
        return {
            # 1. 动量轮动策略
            'momentum': {
                'name': '动量轮动策略',
                'description': '基于近期涨幅进行轮动，选择强势上涨的标的。适合牛市和震荡市。',
                'filter_conditions': [
                    {'field': 'annualized_return', 'operator': '>=', 'value': 0.10},
                    {'field': 'max_drawdown', 'operator': '>=', 'value': -0.20},
                    {'field': 'list_days', 'operator': '>=', 'value': 180},
                    {'field': 'is_st', 'operator': '==', 'value': False}
                ],
                'filter_logic': 'AND',
                'sort_field': 'composite_score',
                'sort_order': 'DESC',
                'select_count': 10,
                'weight_mode': 'equal',
                'max_positions': 10,
                'daily_stop_loss': -0.05,
                'daily_take_profit': 0.10,
                'total_stop_loss': -0.15,
                'trailing_stop': 0.0,
                'volatility_adjustment': False
            },
            
            # 2. 均值回归策略
            'mean_reversion': {
                'name': '均值回归策略',
                'description': '寻找短期超跌但长期基本面良好的标的，博取反弹收益。适合震荡市。',
                'filter_conditions': [
                    {'field': 'max_drawdown', 'operator': '<=', 'value': -0.10},
                    {'field': 'sharpe_ratio', 'operator': '>=', 'value': 0.5},
                    {'field': 'list_days', 'operator': '>=', 'value': 365},
                    {'field': 'is_st', 'operator': '==', 'value': False}
                ],
                'filter_logic': 'AND',
                'sort_field': 'max_drawdown',
                'sort_order': 'ASC',
                'select_count': 10,
                'weight_mode': 'equal',
                'max_positions': 10,
                'daily_stop_loss': -0.03,
                'daily_take_profit': 0.05,
                'total_stop_loss': -0.10,
                'trailing_stop': 0.02,
                'volatility_adjustment': True
            },
            
            # 3. 低波稳健策略
            'low_volatility': {
                'name': '低波稳健策略',
                'description': '优先选择波动率低的标的，追求稳健收益。适合保守型投资者。',
                'filter_conditions': [
                    {'field': 'volatility', 'operator': '<=', 'value': 0.20},
                    {'field': 'max_drawdown', 'operator': '>=', 'value': -0.15},
                    {'field': 'sharpe_ratio', 'operator': '>=', 'value': 1.0},
                    {'field': 'list_days', 'operator': '>=', 'value': 365},
                    {'field': 'is_st', 'operator': '==', 'value': False}
                ],
                'filter_logic': 'AND',
                'sort_field': 'sharpe_ratio',
                'sort_order': 'DESC',
                'select_count': 10,
                'weight_mode': 'equal',
                'max_positions': 10,
                'daily_stop_loss': -0.03,
                'daily_take_profit': 0.08,
                'total_stop_loss': -0.10,
                'trailing_stop': 0.01,
                'volatility_adjustment': False
            },
            
            # 4. 高成长策略
            'high_growth': {
                'name': '高成长策略',
                'description': '选择近期涨幅大、波动率适中的标的，追求高收益。风险较高。',
                'filter_conditions': [
                    {'field': 'annualized_return', 'operator': '>=', 'value': 0.20},
                    {'field': 'sharpe_ratio', 'operator': '>=', 'value': 0.8},
                    {'field': 'list_days', 'operator': '>=', 'value': 180},
                    {'field': 'is_st', 'operator': '==', 'value': False}
                ],
                'filter_logic': 'AND',
                'sort_field': 'annualized_return',
                'sort_order': 'DESC',
                'select_count': 10,
                'weight_mode': 'equal',
                'max_positions': 10,
                'daily_stop_loss': -0.08,
                'daily_take_profit': 0.15,
                'total_stop_loss': -0.20,
                'trailing_stop': 0.05,
                'volatility_adjustment': False
            },
            
            # 5. 综合优选策略 (默认)
            'comprehensive': {
                'name': '综合优选策略',
                'description': '综合考虑收益、风险、规模等多个因子，平衡收益与风险。适合长期定投。',
                'filter_conditions': [
                    {'field': 'sharpe_ratio', 'operator': '>=', 'value': 0.6},
                    {'field': 'max_drawdown', 'operator': '>=', 'value': -0.25},
                    {'field': 'annualized_return', 'operator': '>=', 'value': 0.08},
                    {'field': 'list_days', 'operator': '>=', 'value': 365},
                    {'field': 'is_st', 'operator': '==', 'value': False}
                ],
                'filter_logic': 'AND',
                'sort_field': 'composite_score',
                'sort_order': 'DESC',
                'select_count': 10,
                'weight_mode': 'equal',
                'max_positions': 10,
                'daily_stop_loss': -0.05,
                'daily_take_profit': 0.10,
                'total_stop_loss': -0.15,
                'trailing_stop': 0.0,
                'volatility_adjustment': False
            },
            
            # 6. 超跌反弹策略
            'oversold_rebound': {
                'name': '超跌反弹策略',
                'description': '选择近期大幅回撤的标的，捕捉超跌反弹机会。适合短线操作，风险控制严格。',
                'filter_conditions': [
                    {'field': 'max_drawdown', 'operator': '<=', 'value': -0.20},
                    {'field': 'max_drawdown', 'operator': '>=', 'value': -0.50},
                    {'field': 'list_days', 'operator': '>=', 'value': 180},
                    {'field': 'is_st', 'operator': '==', 'value': False}
                ],
                'filter_logic': 'AND',
                'sort_field': 'max_drawdown',
                'sort_order': 'ASC',
                'select_count': 10,
                'weight_mode': 'equal',
                'max_positions': 10,
                'daily_stop_loss': -0.03,
                'daily_take_profit': 0.06,
                'total_stop_loss': -0.10,
                'trailing_stop': 0.02,
                'volatility_adjustment': False
            },
            
            # 7. 基本面选股策略
            'fundamental': {
                'name': '基本面选股策略',
                'description': '综合考虑市盈率、市净率、夏普比率等基本面指标，选择估值合理、质量优良的标的。',
                'filter_conditions': [
                    {'field': 'pe_ttm', 'operator': '>', 'value': 0},
                    {'field': 'pe_ttm', 'operator': '<=', 'value': 30},
                    {'field': 'pb', 'operator': '>', 'value': 0},
                    {'field': 'pb', 'operator': '<=', 'value': 5.0},
                    {'field': 'sharpe_ratio', 'operator': '>=', 'value': 0.5},
                    {'field': 'list_days', 'operator': '>=', 'value': 365},
                    {'field': 'is_st', 'operator': '==', 'value': False}
                ],
                'filter_logic': 'AND',
                'sort_field': 'composite_score',
                'sort_order': 'DESC',
                'select_count': 10,
                'weight_mode': 'equal',
                'max_positions': 10,
                'daily_stop_loss': -0.05,
                'daily_take_profit': 0.10,
                'total_stop_loss': -0.15,
                'trailing_stop': 0.0,
                'volatility_adjustment': False
            }
        }


# 全局单例实例
_builtin_strategies_manager: Optional[BuiltinStrategiesManager] = None


def get_builtin_strategies_manager() -> BuiltinStrategiesManager:
    """
    获取内置策略管理器单例
    
    Returns:
        BuiltinStrategiesManager 实例
    """
    global _builtin_strategies_manager
    if _builtin_strategies_manager is None:
        _builtin_strategies_manager = BuiltinStrategiesManager()
    return _builtin_strategies_manager

# 为了向后兼容，提供 BuiltinStrategies 别名
BuiltinStrategies = BuiltinStrategiesManager

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    print("=== 测试内置策略模块 ===\n")
    
    manager = BuiltinStrategiesManager()
    
    print(f"已加载 {len(manager._strategies)} 个内置策略\n")
    
    print("=== 策略列表 ===")
    for strategy_info in manager.get_all():
        print(f"- {strategy_info['key']}: {strategy_info['name']}")
        print(f"  描述: {strategy_info['description'][:50]}...")
    
    print("\n=== 获取单个策略详情 ===")
    strategy = manager.get_by_key('comprehensive')
    if strategy:
        print(f"策略: {strategy.name}")
        print(f"描述: {strategy.description}")
        print(f"筛选条件数量: {len(strategy.config.filter_conditions)}")
        print(f"排序字段: {strategy.config.sort_field}")
        print(f"选股数量: {strategy.config.select_count}")
    
    print("\n=== 测试不存在的策略 ===")
    not_found = manager.get_by_key('not_exist')
    print(f"不存在的策略: {not_found}")
