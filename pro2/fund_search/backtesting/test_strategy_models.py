#!/usr/bin/env python
# coding: utf-8

"""
策略数据模型和验证逻辑测试
Tests for Strategy Data Models and Validation Logic

验证任务 2.1 和 2.3 的实现正确性
"""

import sys
import os
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.strategy_models import (
    StrategyConfig, FilterCondition, StrategyValidator,
    calculate_equal_weights, validate_weights_sum,
    SUPPORTED_FILTER_FIELDS, SUPPORTED_SORT_FIELDS
)


def test_filter_condition_creation():
    """测试筛选条件创建"""
    print("\n=== 测试筛选条件创建 ===")
    
    # 测试基本创建
    fc = FilterCondition(field='list_days', operator='>', value=365)
    assert fc.field == 'list_days'
    assert fc.operator == '>'
    assert fc.value == 365
    print("✓ 基本创建测试通过")
    
    # 测试字符串表示
    assert str(fc) == "list_days > 365"
    print("✓ 字符串表示测试通过")
    
    # 测试字典转换
    fc_dict = fc.to_dict()
    assert fc_dict['field'] == 'list_days'
    assert fc_dict['operator'] == '>'
    assert fc_dict['value'] == 365
    print("✓ 字典转换测试通过")
    
    # 测试从字典创建
    fc2 = FilterCondition.from_dict(fc_dict)
    assert fc2.field == fc.field
    assert fc2.operator == fc.operator
    assert fc2.value == fc.value
    print("✓ 从字典创建测试通过")
    
    return True


def test_filter_condition_validation():
    """测试筛选条件验证"""
    print("\n=== 测试筛选条件验证 ===")
    
    # 有效条件测试
    valid_conditions = [
        FilterCondition(field='list_days', operator='>', value=365),
        FilterCondition(field='pe_ttm', operator='>=', value=0),
        FilterCondition(field='is_st', operator='==', value=False),
        FilterCondition(field='sharpe_ratio', operator='<', value=2.0),
        FilterCondition(field='fund_type', operator='==', value='股票型'),
    ]
    
    for fc in valid_conditions:
        is_valid, errors = StrategyValidator.validate_filter_condition(fc)
        assert is_valid, f"条件 {fc} 应该有效，但验证失败: {[str(e) for e in errors]}"
    print(f"✓ {len(valid_conditions)} 个有效条件验证通过")
    
    # 无效条件测试 - 不支持的字段
    invalid_fc = FilterCondition(field='unknown_field', operator='>', value=100)
    is_valid, errors = StrategyValidator.validate_filter_condition(invalid_fc)
    assert not is_valid
    assert any('不支持的字段' in str(e) for e in errors)
    print("✓ 无效字段验证测试通过")
    
    # 无效条件测试 - 无效操作符
    invalid_fc2 = FilterCondition(field='list_days', operator='~', value=100)
    is_valid, errors = StrategyValidator.validate_filter_condition(invalid_fc2)
    assert not is_valid
    assert any('无效的操作符' in str(e) for e in errors)
    print("✓ 无效操作符验证测试通过")
    
    # 无效条件测试 - 类型不匹配
    invalid_fc3 = FilterCondition(field='list_days', operator='>', value='abc')
    is_valid, errors = StrategyValidator.validate_filter_condition(invalid_fc3)
    assert not is_valid
    assert any('数值类型' in str(e) for e in errors)
    print("✓ 类型不匹配验证测试通过")
    
    return True


def test_filter_condition_string_parsing():
    """测试筛选条件字符串解析"""
    print("\n=== 测试筛选条件字符串解析 ===")
    
    # 有效字符串测试
    valid_strings = [
        ("list_days > 365", 'list_days', '>', 365),
        ("pe_ttm >= 0", 'pe_ttm', '>=', 0),
        ("sharpe_ratio < 2.5", 'sharpe_ratio', '<', 2.5),
        ("is_st == false", 'is_st', '==', False),
        ("is_st == true", 'is_st', '==', True),
    ]
    
    for condition_str, expected_field, expected_op, expected_value in valid_strings:
        is_valid, fc, errors = StrategyValidator.validate_filter_condition_string(condition_str)
        assert is_valid, f"字符串 '{condition_str}' 应该有效: {[str(e) for e in errors]}"
        assert fc.field == expected_field
        assert fc.operator == expected_op
        assert fc.value == expected_value
    print(f"✓ {len(valid_strings)} 个有效字符串解析通过")
    
    # 无效字符串测试
    invalid_strings = [
        "",
        "invalid format",
        "no operator here",
        "unknown_field > 100",
    ]
    
    for condition_str in invalid_strings:
        is_valid, fc, errors = StrategyValidator.validate_filter_condition_string(condition_str)
        assert not is_valid, f"字符串 '{condition_str}' 应该无效"
    print(f"✓ {len(invalid_strings)} 个无效字符串拒绝通过")
    
    return True


def test_strategy_config_creation():
    """测试策略配置创建"""
    print("\n=== 测试策略配置创建 ===")
    
    # 测试默认值创建
    config = StrategyConfig()
    assert config.name == ''
    assert config.filter_logic == 'AND'
    assert config.sort_order == 'DESC'
    assert config.weight_mode == 'equal'
    print("✓ 默认值创建测试通过")
    
    # 测试完整配置创建
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
        weight_mode='equal',
        max_positions=10,
        daily_stop_loss=-0.05,
        daily_take_profit=0.10,
        total_stop_loss=-0.15
    )
    
    assert config.name == "测试策略"
    assert len(config.filter_conditions) == 2
    assert config.select_count == 10
    print("✓ 完整配置创建测试通过")
    
    return True


def test_strategy_config_serialization():
    """测试策略配置序列化"""
    print("\n=== 测试策略配置序列化 ===")
    
    # 创建配置
    config = StrategyConfig(
        name="序列化测试策略",
        description="测试序列化功能",
        filter_conditions=[
            FilterCondition(field='list_days', operator='>', value=365),
            FilterCondition(field='sharpe_ratio', operator='>=', value=0.5)
        ],
        filter_logic='AND',
        sort_field='composite_score',
        sort_order='DESC',
        select_count=5,
        weight_mode='equal'
    )
    
    # 测试 to_dict
    config_dict = config.to_dict()
    assert config_dict['name'] == "序列化测试策略"
    assert len(config_dict['filter_conditions']) == 2
    print("✓ to_dict 测试通过")
    
    # 测试 from_dict
    config2 = StrategyConfig.from_dict(config_dict)
    assert config2.name == config.name
    assert config2.description == config.description
    assert len(config2.filter_conditions) == len(config.filter_conditions)
    assert config2.select_count == config.select_count
    print("✓ from_dict 测试通过")
    
    # 测试 to_json / from_json
    json_str = config.to_json()
    config3 = StrategyConfig.from_json(json_str)
    assert config3.name == config.name
    assert config3.select_count == config.select_count
    print("✓ JSON 序列化/反序列化测试通过")
    
    # 验证 JSON 格式正确
    parsed = json.loads(json_str)
    assert 'name' in parsed
    assert 'filter_conditions' in parsed
    print("✓ JSON 格式验证通过")
    
    return True


def test_strategy_config_validation():
    """测试策略配置验证"""
    print("\n=== 测试策略配置验证 ===")
    
    # 有效配置测试
    valid_config = StrategyConfig(
        name="有效策略",
        description="测试有效配置",
        filter_conditions=[
            FilterCondition(field='list_days', operator='>', value=365)
        ],
        filter_logic='AND',
        sort_field='composite_score',
        sort_order='DESC',
        select_count=10,
        weight_mode='equal',
        max_positions=10,
        daily_stop_loss=-0.05,
        daily_take_profit=0.10,
        total_stop_loss=-0.15
    )
    
    is_valid, errors = StrategyValidator.validate_strategy_config(valid_config)
    assert is_valid, f"有效配置验证失败: {[str(e) for e in errors]}"
    print("✓ 有效配置验证通过")
    
    # 无效配置测试 - 空名称
    invalid_config1 = StrategyConfig(name="", select_count=10)
    is_valid, errors = StrategyValidator.validate_strategy_config(invalid_config1)
    assert not is_valid
    assert any('名称' in str(e) for e in errors)
    print("✓ 空名称验证测试通过")
    
    # 无效配置测试 - 无效排序字段
    invalid_config2 = StrategyConfig(name="测试", sort_field='invalid_field')
    is_valid, errors = StrategyValidator.validate_strategy_config(invalid_config2)
    assert not is_valid
    assert any('排序字段' in str(e) for e in errors)
    print("✓ 无效排序字段验证测试通过")
    
    # 无效配置测试 - 选股数量为0
    invalid_config3 = StrategyConfig(name="测试", select_count=0)
    is_valid, errors = StrategyValidator.validate_strategy_config(invalid_config3)
    assert not is_valid
    assert any('选股数量' in str(e) for e in errors)
    print("✓ 无效选股数量验证测试通过")
    
    # 无效配置测试 - 止损阈值为正数
    invalid_config4 = StrategyConfig(name="测试", daily_stop_loss=0.05)
    is_valid, errors = StrategyValidator.validate_strategy_config(invalid_config4)
    assert not is_valid
    assert any('止损' in str(e) for e in errors)
    print("✓ 无效止损阈值验证测试通过")
    
    return True


def test_equal_weight_calculation():
    """测试等权重计算"""
    print("\n=== 测试等权重计算 ===")
    
    # 测试正常情况
    test_cases = [1, 2, 3, 5, 10, 20, 100]
    
    for n in test_cases:
        weights = calculate_equal_weights(n)
        assert len(weights) == n
        assert all(abs(w - 1.0/n) < 1e-10 for w in weights)
        assert validate_weights_sum(weights)
    print(f"✓ {len(test_cases)} 个等权重计算测试通过")
    
    # 测试边界情况
    weights_zero = calculate_equal_weights(0)
    assert weights_zero == []
    print("✓ 零基金数量测试通过")
    
    weights_negative = calculate_equal_weights(-1)
    assert weights_negative == []
    print("✓ 负数基金数量测试通过")
    
    return True


def test_weights_sum_validation():
    """测试权重之和验证"""
    print("\n=== 测试权重之和验证 ===")
    
    # 有效权重
    valid_weights = [0.2, 0.2, 0.2, 0.2, 0.2]
    assert validate_weights_sum(valid_weights)
    print("✓ 有效权重验证通过")
    
    # 无效权重 - 和不为1
    invalid_weights = [0.3, 0.3, 0.3]
    assert not validate_weights_sum(invalid_weights)
    print("✓ 无效权重（和不为1）验证通过")
    
    # 空权重
    assert not validate_weights_sum([])
    print("✓ 空权重验证通过")
    
    # 浮点数精度测试
    precise_weights = [1.0/3, 1.0/3, 1.0/3]
    assert validate_weights_sum(precise_weights)
    print("✓ 浮点数精度测试通过")
    
    return True


def test_custom_weights_validation():
    """测试自定义权重验证"""
    print("\n=== 测试自定义权重验证 ===")
    
    # 有效自定义权重
    valid_config = StrategyConfig(
        name="自定义权重策略",
        select_count=3,
        weight_mode='custom',
        custom_weights=[0.5, 0.3, 0.2]
    )
    is_valid, errors = StrategyValidator.validate_strategy_config(valid_config)
    assert is_valid, f"有效自定义权重验证失败: {[str(e) for e in errors]}"
    print("✓ 有效自定义权重验证通过")
    
    # 无效自定义权重 - 数量不匹配
    invalid_config1 = StrategyConfig(
        name="测试",
        select_count=3,
        weight_mode='custom',
        custom_weights=[0.5, 0.5]  # 只有2个权重
    )
    is_valid, errors = StrategyValidator.validate_strategy_config(invalid_config1)
    assert not is_valid
    assert any('权重数量' in str(e) for e in errors)
    print("✓ 权重数量不匹配验证通过")
    
    # 无效自定义权重 - 和不为1
    invalid_config2 = StrategyConfig(
        name="测试",
        select_count=3,
        weight_mode='custom',
        custom_weights=[0.3, 0.3, 0.3]  # 和为0.9
    )
    is_valid, errors = StrategyValidator.validate_strategy_config(invalid_config2)
    assert not is_valid
    assert any('权重之和' in str(e) for e in errors)
    print("✓ 权重之和不为1验证通过")
    
    # 无效自定义权重 - 负数权重
    invalid_config3 = StrategyConfig(
        name="测试",
        select_count=3,
        weight_mode='custom',
        custom_weights=[-0.1, 0.6, 0.5]
    )
    is_valid, errors = StrategyValidator.validate_strategy_config(invalid_config3)
    assert not is_valid
    assert any('0到1之间' in str(e) for e in errors)
    print("✓ 负数权重验证通过")
    
    return True


def test_supported_fields():
    """测试支持的字段列表"""
    print("\n=== 测试支持的字段列表 ===")
    
    # 验证筛选字段
    expected_filter_fields = [
        'list_days', 'pe_ttm', 'pb', 'market_cap', 'market_cap_rank',
        'volatility', 'sharpe_ratio', 'max_drawdown', 'annualized_return',
        'composite_score', 'is_st', 'is_suspended', 'fund_type'
    ]
    
    for field in expected_filter_fields:
        assert field in SUPPORTED_FILTER_FIELDS, f"字段 {field} 应该在支持列表中"
    print(f"✓ {len(expected_filter_fields)} 个筛选字段验证通过")
    
    # 验证排序字段
    expected_sort_fields = [
        'composite_score', 'sharpe_ratio', 'annualized_return',
        'max_drawdown', 'volatility', 'market_cap', 'pe_ttm', 'pb'
    ]
    
    for field in expected_sort_fields:
        assert field in SUPPORTED_SORT_FIELDS, f"字段 {field} 应该在排序字段列表中"
    print(f"✓ {len(expected_sort_fields)} 个排序字段验证通过")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("策略数据模型和验证逻辑测试")
    print("=" * 60)
    
    tests = [
        ("筛选条件创建", test_filter_condition_creation),
        ("筛选条件验证", test_filter_condition_validation),
        ("筛选条件字符串解析", test_filter_condition_string_parsing),
        ("策略配置创建", test_strategy_config_creation),
        ("策略配置序列化", test_strategy_config_serialization),
        ("策略配置验证", test_strategy_config_validation),
        ("等权重计算", test_equal_weight_calculation),
        ("权重之和验证", test_weights_sum_validation),
        ("自定义权重验证", test_custom_weights_validation),
        ("支持的字段列表", test_supported_fields),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n✗ {name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
