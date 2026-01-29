#!/usr/bin/env python
# coding: utf-8

"""
策略数据模型和验证逻辑
Strategy Data Models and Validation Logic

提供用户自定义策略的数据结构定义和配置验证功能
"""

import re
import json
import logging
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Union, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class FilterOperator(str, Enum):
    """筛选条件操作符"""
    GT = '>'
    LT = '<'
    GTE = '>='
    LTE = '<='
    EQ = '=='
    NEQ = '!='


class FilterLogic(str, Enum):
    """筛选条件组合逻辑"""
    AND = 'AND'
    OR = 'OR'


class SortOrder(str, Enum):
    """排序方向"""
    ASC = 'ASC'
    DESC = 'DESC'


class WeightMode(str, Enum):
    """权重模式"""
    EQUAL = 'equal'
    CUSTOM = 'custom'


# 支持的筛选字段及其类型
SUPPORTED_FILTER_FIELDS = {
    'list_days': {'type': 'numeric', 'description': '上市天数'},
    'pe_ttm': {'type': 'numeric', 'description': '市盈率TTM'},
    'pb': {'type': 'numeric', 'description': '市净率'},
    'market_cap': {'type': 'numeric', 'description': '市值'},
    'market_cap_rank': {'type': 'numeric', 'description': '市值排名百分比'},
    'volatility': {'type': 'numeric', 'description': '波动率'},
    'sharpe_ratio': {'type': 'numeric', 'description': '夏普比率'},
    'max_drawdown': {'type': 'numeric', 'description': '最大回撤'},
    'annualized_return': {'type': 'numeric', 'description': '年化收益率'},
    'composite_score': {'type': 'numeric', 'description': '综合评分'},
    'is_st': {'type': 'boolean', 'description': '是否ST'},
    'is_suspended': {'type': 'boolean', 'description': '是否停牌'},
    'fund_type': {'type': 'string', 'description': '基金类型'},
}

# 支持的排序字段
SUPPORTED_SORT_FIELDS = [
    'composite_score', 'sharpe_ratio', 'annualized_return', 
    'max_drawdown', 'volatility', 'market_cap', 'pe_ttm', 'pb'
]


@dataclass
class FilterCondition:
    """
    筛选条件数据类
    
    Attributes:
        field: 筛选字段名
        operator: 操作符 ('>', '<', '>=', '<=', '==', '!=')
        value: 比较值
    """
    field: str
    operator: str
    value: Union[float, str, bool]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'field': self.field,
            'operator': self.operator,
            'value': self.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilterCondition':
        """从字典创建实例"""
        return cls(
            field=data.get('field', ''),
            operator=data.get('operator', '=='),
            value=data.get('value', 0)
        )
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.field} {self.operator} {self.value}"


@dataclass
class StrategyConfig:
    """
    策略配置数据类
    
    包含策略的所有配置参数，包括筛选条件、排序选股、交易规则和风险控制
    """
    # 基本信息
    name: str = ''
    description: str = ''
    strategy_type: str = 'momentum'  # 策略类型: momentum, mean_reversion, etc.
    
    # 策略参数
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 筛选条件
    filter_conditions: List[FilterCondition] = field(default_factory=list)
    filter_logic: str = 'AND'  # 'AND' | 'OR'
    
    # 排序选股
    sort_field: str = 'composite_score'
    sort_order: str = 'DESC'  # 'ASC' | 'DESC'
    select_count: int = 10
    weight_mode: str = 'equal'  # 'equal' | 'custom'
    custom_weights: List[float] = field(default_factory=list)
    
    # 交易规则
    max_positions: int = 10
    trade_on_hold_day: bool = False
    buy_condition: str = ''
    sell_condition: str = ''
    
    # 风险控制
    daily_stop_loss: float = -0.05  # 每日止损阈值 (-5%)
    daily_take_profit: float = 0.10  # 每日止盈阈值 (10%)
    total_stop_loss: float = -0.15  # 累计止损阈值 (-15%)
    trailing_stop: float = 0.0  # 追踪止损比例
    volatility_adjustment: bool = False  # 是否启用波动率调整
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON序列化）"""
        return {
            'name': self.name,
            'description': self.description,
            'strategy_type': self.strategy_type,
            'parameters': self.parameters,
            'filter_conditions': [fc.to_dict() for fc in self.filter_conditions],
            'filter_logic': self.filter_logic,
            'sort_field': self.sort_field,
            'sort_order': self.sort_order,
            'select_count': self.select_count,
            'weight_mode': self.weight_mode,
            'custom_weights': self.custom_weights,
            'max_positions': self.max_positions,
            'trade_on_hold_day': self.trade_on_hold_day,
            'buy_condition': self.buy_condition,
            'sell_condition': self.sell_condition,
            'daily_stop_loss': self.daily_stop_loss,
            'daily_take_profit': self.daily_take_profit,
            'total_stop_loss': self.total_stop_loss,
            'trailing_stop': self.trailing_stop,
            'volatility_adjustment': self.volatility_adjustment
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyConfig':
        """从字典创建实例"""
        filter_conditions = []
        for fc_data in data.get('filter_conditions', []):
            if isinstance(fc_data, dict):
                filter_conditions.append(FilterCondition.from_dict(fc_data))
            elif isinstance(fc_data, FilterCondition):
                filter_conditions.append(fc_data)

        return cls(
            name=data.get('name', ''),
            description=data.get('description', ''),
            strategy_type=data.get('strategy_type', 'momentum'),
            parameters=data.get('parameters', {}),
            filter_conditions=filter_conditions,
            filter_logic=data.get('filter_logic', 'AND'),
            sort_field=data.get('sort_field', 'composite_score'),
            sort_order=data.get('sort_order', 'DESC'),
            select_count=data.get('select_count', 10),
            weight_mode=data.get('weight_mode', 'equal'),
            custom_weights=data.get('custom_weights', []),
            max_positions=data.get('max_positions', 10),
            trade_on_hold_day=data.get('trade_on_hold_day', False),
            buy_condition=data.get('buy_condition', ''),
            sell_condition=data.get('sell_condition', ''),
            daily_stop_loss=data.get('daily_stop_loss', -0.05),
            daily_take_profit=data.get('daily_take_profit', 0.10),
            total_stop_loss=data.get('total_stop_loss', -0.15),
            trailing_stop=data.get('trailing_stop', 0.0),
            volatility_adjustment=data.get('volatility_adjustment', False)
        )
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'StrategyConfig':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class BacktestResult:
    """
    回测结果数据类
    
    Attributes:
        strategy_name: 策略名称
        start_date: 回测开始日期
        end_date: 回测结束日期
        total_return: 总收益率
        annualized_return: 年化收益率
        max_drawdown: 最大回撤
        sharpe_ratio: 夏普比率
        trades: 交易记录列表
    """
    strategy_name: str
    start_date: datetime
    end_date: datetime
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    trades: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'strategy_name': self.strategy_name,
            'start_date': self.start_date.isoformat() if hasattr(self.start_date, 'isoformat') else str(self.start_date),
            'end_date': self.end_date.isoformat() if hasattr(self.end_date, 'isoformat') else str(self.end_date),
            'total_return': self.total_return,
            'annualized_return': self.annualized_return,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'trades': self.trades
        }


class ValidationError:
    """验证错误信息"""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
    
    def to_dict(self) -> Dict[str, str]:
        return {'field': self.field, 'message': self.message}
    
    def __str__(self) -> str:
        return f"{self.field}: {self.message}"


class StrategyValidator:
    """
    策略配置验证器
    
    提供筛选条件和策略配置的验证功能
    """
    
    # 有效的操作符
    VALID_OPERATORS = ['>', '<', '>=', '<=', '==', '!=']
    
    @classmethod
    def validate_filter_condition(cls, condition: FilterCondition) -> Tuple[bool, List[ValidationError]]:
        """
        验证单个筛选条件
        
        Args:
            condition: 筛选条件对象
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        # 验证字段名
        if not condition.field:
            errors.append(ValidationError('field', '字段名不能为空'))
        elif condition.field not in SUPPORTED_FILTER_FIELDS:
            errors.append(ValidationError(
                'field', 
                f"不支持的字段: {condition.field}。支持的字段: {', '.join(SUPPORTED_FILTER_FIELDS.keys())}"
            ))
        
        # 验证操作符
        if not condition.operator:
            errors.append(ValidationError('operator', '操作符不能为空'))
        elif condition.operator not in cls.VALID_OPERATORS:
            errors.append(ValidationError(
                'operator',
                f"无效的操作符: {condition.operator}。有效操作符: {', '.join(cls.VALID_OPERATORS)}"
            ))
        
        # 验证值类型
        if condition.field in SUPPORTED_FILTER_FIELDS:
            field_info = SUPPORTED_FILTER_FIELDS[condition.field]
            field_type = field_info['type']
            
            if field_type == 'numeric':
                if not isinstance(condition.value, (int, float)):
                    try:
                        float(condition.value)
                    except (ValueError, TypeError):
                        errors.append(ValidationError(
                            'value',
                            f"字段 {condition.field} 需要数值类型，但得到: {type(condition.value).__name__}"
                        ))
            elif field_type == 'boolean':
                if not isinstance(condition.value, bool):
                    if condition.value not in [0, 1, '0', '1', 'true', 'false', 'True', 'False']:
                        errors.append(ValidationError(
                            'value',
                            f"字段 {condition.field} 需要布尔类型"
                        ))
            elif field_type == 'string':
                if not isinstance(condition.value, str):
                    errors.append(ValidationError(
                        'value',
                        f"字段 {condition.field} 需要字符串类型"
                    ))
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_filter_condition_string(cls, condition_str: str) -> Tuple[bool, Optional[FilterCondition], List[ValidationError]]:
        """
        验证并解析筛选条件字符串
        
        Args:
            condition_str: 条件字符串，格式如 "list_days > 365"
            
        Returns:
            (是否有效, 解析后的FilterCondition或None, 错误列表)
        """
        errors = []
        
        if not condition_str or not condition_str.strip():
            errors.append(ValidationError('condition', '条件字符串不能为空'))
            return False, None, errors
        
        # 解析条件字符串
        # 支持的格式: field operator value
        pattern = r'^\s*(\w+)\s*(>=|<=|==|!=|>|<)\s*(.+)\s*$'
        match = re.match(pattern, condition_str.strip())
        
        if not match:
            errors.append(ValidationError(
                'condition',
                f"无效的条件格式: '{condition_str}'。期望格式: 'field operator value' (如 'list_days > 365')"
            ))
            return False, None, errors
        
        field_name = match.group(1)
        operator = match.group(2)
        value_str = match.group(3).strip()
        
        # 解析值
        value: Union[float, str, bool]
        if value_str.lower() in ['true', 'false']:
            value = value_str.lower() == 'true'
        elif value_str.startswith('"') and value_str.endswith('"'):
            value = value_str[1:-1]
        elif value_str.startswith("'") and value_str.endswith("'"):
            value = value_str[1:-1]
        else:
            try:
                if '.' in value_str:
                    value = float(value_str)
                else:
                    value = int(value_str)
            except ValueError:
                value = value_str
        
        condition = FilterCondition(field=field_name, operator=operator, value=value)
        
        # 验证解析后的条件
        is_valid, validation_errors = cls.validate_filter_condition(condition)
        
        return is_valid, condition if is_valid else None, validation_errors
    
    @classmethod
    def validate_strategy_config(cls, config: StrategyConfig) -> Tuple[bool, List[ValidationError]]:
        """
        验证完整的策略配置
        
        Args:
            config: 策略配置对象
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        # 验证基本信息
        if not config.name or not config.name.strip():
            errors.append(ValidationError('name', '策略名称不能为空'))
        elif len(config.name) > 100:
            errors.append(ValidationError('name', '策略名称不能超过100个字符'))
        
        # 验证筛选条件
        for i, fc in enumerate(config.filter_conditions):
            is_valid, fc_errors = cls.validate_filter_condition(fc)
            if not is_valid:
                for err in fc_errors:
                    errors.append(ValidationError(
                        f'filter_conditions[{i}].{err.field}',
                        err.message
                    ))
        
        # 验证筛选逻辑
        if config.filter_logic not in ['AND', 'OR']:
            errors.append(ValidationError(
                'filter_logic',
                f"无效的筛选逻辑: {config.filter_logic}。有效值: AND, OR"
            ))
        
        # 验证排序字段
        if config.sort_field and config.sort_field not in SUPPORTED_SORT_FIELDS:
            errors.append(ValidationError(
                'sort_field',
                f"不支持的排序字段: {config.sort_field}。支持的字段: {', '.join(SUPPORTED_SORT_FIELDS)}"
            ))
        
        # 验证排序方向
        if config.sort_order not in ['ASC', 'DESC']:
            errors.append(ValidationError(
                'sort_order',
                f"无效的排序方向: {config.sort_order}。有效值: ASC, DESC"
            ))
        
        # 验证选股数量
        if config.select_count < 1:
            errors.append(ValidationError('select_count', '选股数量必须大于0'))
        elif config.select_count > 100:
            errors.append(ValidationError('select_count', '选股数量不能超过100'))
        
        # 验证权重模式
        if config.weight_mode not in ['equal', 'custom']:
            errors.append(ValidationError(
                'weight_mode',
                f"无效的权重模式: {config.weight_mode}。有效值: equal, custom"
            ))
        
        # 验证自定义权重
        if config.weight_mode == 'custom':
            if not config.custom_weights:
                errors.append(ValidationError('custom_weights', '自定义权重模式下必须提供权重列表'))
            elif len(config.custom_weights) != config.select_count:
                errors.append(ValidationError(
                    'custom_weights',
                    f"权重数量({len(config.custom_weights)})必须等于选股数量({config.select_count})"
                ))
            else:
                weight_sum = sum(config.custom_weights)
                if abs(weight_sum - 1.0) > 0.001:
                    errors.append(ValidationError(
                        'custom_weights',
                        f"权重之和必须等于1.0，当前为: {weight_sum:.4f}"
                    ))
                for i, w in enumerate(config.custom_weights):
                    if w < 0 or w > 1:
                        errors.append(ValidationError(
                            f'custom_weights[{i}]',
                            f"权重值必须在0到1之间，当前为: {w}"
                        ))
        
        # 验证最大持仓数
        if config.max_positions < 1:
            errors.append(ValidationError('max_positions', '最大持仓数必须大于0'))
        elif config.max_positions > 100:
            errors.append(ValidationError('max_positions', '最大持仓数不能超过100'))
        
        # 验证止损止盈阈值
        if config.daily_stop_loss >= 0:
            errors.append(ValidationError('daily_stop_loss', '每日止损阈值必须为负数'))
        if config.daily_take_profit <= 0:
            errors.append(ValidationError('daily_take_profit', '每日止盈阈值必须为正数'))
        if config.total_stop_loss >= 0:
            errors.append(ValidationError('total_stop_loss', '累计止损阈值必须为负数'))
        if config.trailing_stop < 0:
            errors.append(ValidationError('trailing_stop', '追踪止损比例不能为负数'))
        
        return len(errors) == 0, errors


def calculate_equal_weights(n: int) -> List[float]:
    """
    计算等权重
    
    Args:
        n: 基金数量
        
    Returns:
        权重列表，每个权重为 1/n
    """
    if n <= 0:
        return []
    weight = 1.0 / n
    return [weight] * n


def validate_weights_sum(weights: List[float], tolerance: float = 1e-9) -> bool:
    """
    验证权重之和是否等于1.0
    
    Args:
        weights: 权重列表
        tolerance: 浮点数容差
        
    Returns:
        权重之和是否在容差范围内等于1.0
    """
    if not weights:
        return False
    return abs(sum(weights) - 1.0) <= tolerance


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 测试筛选条件验证
    print("=== 测试筛选条件验证 ===")
    
    # 有效条件
    valid_condition = FilterCondition(field='list_days', operator='>', value=365)
    is_valid, errors = StrategyValidator.validate_filter_condition(valid_condition)
    print(f"有效条件测试: {is_valid}, 错误: {[str(e) for e in errors]}")
    
    # 无效条件 - 不支持的字段
    invalid_condition = FilterCondition(field='unknown_field', operator='>', value=100)
    is_valid, errors = StrategyValidator.validate_filter_condition(invalid_condition)
    print(f"无效字段测试: {is_valid}, 错误: {[str(e) for e in errors]}")
    
    # 测试条件字符串解析
    print("\n=== 测试条件字符串解析 ===")
    test_strings = [
        "list_days > 365",
        "pe_ttm >= 0",
        "is_st == false",
        "invalid format",
        "unknown_field > 100"
    ]
    for s in test_strings:
        is_valid, condition, errors = StrategyValidator.validate_filter_condition_string(s)
        print(f"'{s}': 有效={is_valid}, 条件={condition}, 错误={[str(e) for e in errors]}")
    
    # 测试策略配置验证
    print("\n=== 测试策略配置验证 ===")
    config = StrategyConfig(
        name="测试策略",
        description="这是一个测试策略",
        filter_conditions=[
            FilterCondition(field='list_days', operator='>', value=365),
            FilterCondition(field='pe_ttm', operator='>', value=0)
        ],
        filter_logic='AND',
        sort_field='composite_score',
        sort_order='DESC',
        select_count=10,
        weight_mode='equal'
    )
    is_valid, errors = StrategyValidator.validate_strategy_config(config)
    print(f"策略配置验证: {is_valid}, 错误: {[str(e) for e in errors]}")
    
    # 测试等权重计算
    print("\n=== 测试等权重计算 ===")
    weights = calculate_equal_weights(5)
    print(f"5只基金等权重: {weights}")
    print(f"权重之和: {sum(weights)}")
    print(f"权重验证: {validate_weights_sum(weights)}")
