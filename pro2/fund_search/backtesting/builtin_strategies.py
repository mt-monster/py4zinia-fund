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

from .strategy_models import StrategyConfig, FilterCondition, StrategyValidator

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
    config: StrategyConfig
    
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
                config = StrategyConfig(
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
                logger.debug(f"已加载内置策略: {key} - {config_data['name']}")
                
            except Exception as e:
                logger.error(f"加载内置策略 {key} 失败: {e}")
    
    def _validate_strategies(self) -> None:
        """验证所有策略配置，移除无效策略"""
        invalid_keys = []
        
        for key, strategy in self._strategies.items():
            is_valid, errors = StrategyValidator.validate_strategy_config(strategy.config)
            
            if not is_valid:
                error_messages = [str(e) for e in errors]
                logger.warning(f"内置策略 {key} 配置无效，将被排除: {error_messages}")
                invalid_keys.append(key)
        
        # 移除无效策略
        for key in invalid_keys:
            del self._strategies[key]
        
        logger.info(f"内置策略验证完成，有效策略数量: {len(self._strategies)}")
    
    def _get_builtin_strategy_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有内置策略的配置定义"""
        return {
            # 1. 小市值策略
            'small_cap': {
                'name': '小市值策略',
                'description': '选择市值较小的股票，追求高成长潜力。通过市值排名筛选小盘股，排除ST和新上市股票。',
                'filter_conditions': [
                    {'field': 'market_cap_rank', 'operator': '<=', 'value': 30},
                    {'field': 'list_days', 'operator': '>=', 'value': 60},
                    {'field': 'is_st', 'operator': '==', 'value': False}
                ],
                'filter_logic': 'AND',
                'sort_field': 'market_cap',
                'sort_order': 'ASC',
                'select_count': 10,
                'weight_mode': 'equal',
                'max_positions': 10,
                'daily_stop_loss': -0.05,
                'daily_take_profit': 0.10,
                'total_stop_loss': -0.15,
                'trailing_stop': 0.0,
                'volatility_adjustment': False
            },
            
            # 2. 成长因子选股策略
            'growth_factor': {
                'name': '成长因子选股策略',
                'description': '基于成长性指标选股，关注高年化收益率和夏普比率，筛选具有高增长潜力的标的。',
                'filter_conditions': [
                    {'field': 'annualized_return', 'operator': '>=', 'value': 0.15},
                    {'field': 'sharpe_ratio', 'operator': '>=', 'value': 1.0},
                    {'field': 'list_days', 'operator': '>=', 'value': 180}
                ],
                'filter_logic': 'AND',
                'sort_field': 'annualized_return',
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
            
            # 3. 换手率波动性策略
            'turnover_volatility': {
                'name': '换手率波动性策略',
                'description': '基于波动率筛选，选择波动率适中的标的，追求稳定收益与风险平衡。',
                'filter_conditions': [
                    {'field': 'volatility', 'operator': '>=', 'value': 0.10},
                    {'field': 'volatility', 'operator': '<=', 'value': 0.30},
                    {'field': 'list_days', 'operator': '>=', 'value': 120},
                    {'field': 'is_st', 'operator': '==', 'value': False}
                ],
                'filter_logic': 'AND',
                'sort_field': 'sharpe_ratio',
                'sort_order': 'DESC',
                'select_count': 10,
                'weight_mode': 'equal',
                'max_positions': 10,
                'daily_stop_loss': -0.04,
                'daily_take_profit': 0.08,
                'total_stop_loss': -0.12,
                'trailing_stop': 0.0,
                'volatility_adjustment': True
            },
            
            # 4. 破净股策略
            'below_book_value': {
                'name': '破净股策略',
                'description': '选择市净率低于1的股票，寻找被低估的价值投资机会。',
                'filter_conditions': [
                    {'field': 'pb', 'operator': '<', 'value': 1.0},
                    {'field': 'pb', 'operator': '>', 'value': 0},
                    {'field': 'list_days', 'operator': '>=', 'value': 365},
                    {'field': 'is_st', 'operator': '==', 'value': False}
                ],
                'filter_logic': 'AND',
                'sort_field': 'pb',
                'sort_order': 'ASC',
                'select_count': 10,
                'weight_mode': 'equal',
                'max_positions': 10,
                'daily_stop_loss': -0.05,
                'daily_take_profit': 0.10,
                'total_stop_loss': -0.15,
                'trailing_stop': 0.0,
                'volatility_adjustment': False
            },
            
            # 5. 红利策略
            'dividend': {
                'name': '红利策略',
                'description': '选择高分红、低估值的稳健型股票，追求稳定的股息收入和长期价值增长。',
                'filter_conditions': [
                    {'field': 'pe_ttm', 'operator': '>', 'value': 0},
                    {'field': 'pe_ttm', 'operator': '<=', 'value': 20},
                    {'field': 'pb', 'operator': '<=', 'value': 3.0},
                    {'field': 'list_days', 'operator': '>=', 'value': 365},
                    {'field': 'is_st', 'operator': '==', 'value': False}
                ],
                'filter_logic': 'AND',
                'sort_field': 'pe_ttm',
                'sort_order': 'ASC',
                'select_count': 10,
                'weight_mode': 'equal',
                'max_positions': 10,
                'daily_stop_loss': -0.04,
                'daily_take_profit': 0.08,
                'total_stop_loss': -0.12,
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
    
    def get_all(self) -> List[Dict[str, str]]:
        """
        获取所有内置策略列表（摘要信息）
        
        Returns:
            策略摘要列表，每个元素包含 key, name, description
        """
        return [strategy.to_summary_dict() for strategy in self._strategies.values()]
    
    def get_by_key(self, key: str) -> Optional[BuiltinStrategy]:
        """
        根据 key 获取内置策略
        
        Args:
            key: 策略唯一标识
            
        Returns:
            BuiltinStrategy 对象，如果不存在则返回 None
        """
        return self._strategies.get(key)
    
    def get_config_dict(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取策略的完整配置字典
        
        Args:
            key: 策略唯一标识
            
        Returns:
            策略配置字典，如果不存在则返回 None
        """
        strategy = self.get_by_key(key)
        if strategy:
            return strategy.to_dict()
        return None
    
    def get_strategy_keys(self) -> List[str]:
        """
        获取所有策略的 key 列表
        
        Returns:
            策略 key 列表
        """
        return list(self._strategies.keys())
    
    def __len__(self) -> int:
        """返回内置策略数量"""
        return len(self._strategies)
    
    def __contains__(self, key: str) -> bool:
        """检查策略是否存在"""
        return key in self._strategies


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


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    print("=== 测试内置策略模块 ===\n")
    
    manager = BuiltinStrategiesManager()
    
    print(f"已加载 {len(manager)} 个内置策略\n")
    
    print("=== 策略列表 ===")
    for strategy_info in manager.get_all():
        print(f"- {strategy_info['key']}: {strategy_info['name']}")
        print(f"  描述: {strategy_info['description'][:50]}...")
    
    print("\n=== 获取单个策略详情 ===")
    strategy = manager.get_by_key('small_cap')
    if strategy:
        print(f"策略: {strategy.name}")
        print(f"描述: {strategy.description}")
        print(f"筛选条件数量: {len(strategy.config.filter_conditions)}")
        print(f"排序字段: {strategy.config.sort_field}")
        print(f"选股数量: {strategy.config.select_count}")
    
    print("\n=== 测试不存在的策略 ===")
    not_found = manager.get_by_key('not_exist')
    print(f"不存在的策略: {not_found}")
