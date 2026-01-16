#!/usr/bin/env python
# coding: utf-8

"""
投资策略优化模块集成测试

测试所有新增组件的协作和完整策略分析流程
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_strategy_config():
    """测试策略配置模块"""
    print("\n=== 测试策略配置模块 ===")
    from backtesting.strategy_config import StrategyConfig, get_strategy_config
    
    config = get_strategy_config()
    print(f"✓ 配置加载成功")
    print(f"  - 止损阈值: {config.get('stop_loss.stop_loss_threshold')}%")
    print(f"  - 警告阈值: {config.get('stop_loss.warning_threshold')}%")
    print(f"  - 高波动阈值: {config.get('volatility.high_volatility_threshold')}%")
    print(f"  - 短期MA周期: {config.get('trend.short_ma_period')}天")
    return True


def test_stop_loss_manager():
    """测试止损管理模块"""
    print("\n=== 测试止损管理模块 ===")
    from backtesting.stop_loss_manager import StopLossManager, StopLossLevel
    
    manager = StopLossManager()
    
    # 测试正常情况
    result = manager.check_stop_loss(-0.05)
    assert result.level == StopLossLevel.NONE
    print(f"✓ 正常情况: 亏损-5% -> {result.level.value}")
    
    # 测试警告情况
    result = manager.check_stop_loss(-0.12)
    assert result.level == StopLossLevel.WARNING
    print(f"✓ 警告情况: 亏损-12% -> {result.level.value}")
    
    # 测试止损情况
    result = manager.check_stop_loss(-0.18)
    assert result.level == StopLossLevel.STOP_LOSS
    print(f"✓ 止损情况: 亏损-18% -> {result.level.value}")
    
    return True


def test_trend_analyzer():
    """测试趋势分析模块"""
    print("\n=== 测试趋势分析模块 ===")
    from backtesting.trend_analyzer import TrendAnalyzer, TrendType
    
    analyzer = TrendAnalyzer()
    
    # 上涨趋势数据
    uptrend_data = [0.001, 0.002, 0.001, 0.003, 0.002, 0.004, 0.003, 0.005, 0.004, 0.006]
    result = analyzer.analyze_trend(uptrend_data)
    print(f"✓ 上涨趋势: {result.trend.value}, 倍数调整: {result.multiplier_adjustment:.2f}")
    
    # 下跌趋势数据
    downtrend_data = [-0.001, -0.002, -0.001, -0.003, -0.002, -0.004, -0.003, -0.005, -0.004, -0.006]
    result = analyzer.analyze_trend(downtrend_data)
    print(f"✓ 下跌趋势: {result.trend.value}, 倍数调整: {result.multiplier_adjustment:.2f}")
    
    # 横盘趋势数据
    sideways_data = [0.001, -0.001, 0.002, -0.002, 0.001, -0.001, 0.002, -0.002, 0.001, -0.001]
    result = analyzer.analyze_trend(sideways_data)
    print(f"✓ 横盘趋势: {result.trend.value}, 倍数调整: {result.multiplier_adjustment:.2f}")
    
    return True


def test_position_manager():
    """测试仓位管理模块"""
    print("\n=== 测试仓位管理模块 ===")
    from backtesting.position_manager import PositionManager, VolatilityLevel
    
    manager = PositionManager()
    
    # 高波动数据
    high_vol_data = [0.05, -0.04, 0.06, -0.05, 0.07, -0.06, 0.08, -0.07, 0.09, -0.08]
    result = manager.adjust_from_returns(1.5, high_vol_data)
    print(f"✓ 高波动: {result.volatility_level.value}, 仓位调整: {result.adjustment_factor:.2f}")
    
    # 低波动数据
    low_vol_data = [0.001, 0.002, 0.001, 0.002, 0.001, 0.002, 0.001, 0.002, 0.001, 0.002]
    result = manager.adjust_from_returns(1.5, low_vol_data)
    print(f"✓ 低波动: {result.volatility_level.value}, 仓位调整: {result.adjustment_factor:.2f}")
    
    return True


def test_strategy_evaluator():
    """测试策略评估模块"""
    print("\n=== 测试策略评估模块 ===")
    from backtesting.strategy_evaluator import StrategyEvaluator
    
    evaluator = StrategyEvaluator()
    
    # 模拟交易记录
    trades = [
        {'profit': 100, 'return': 0.05},
        {'profit': -50, 'return': -0.02},
        {'profit': 80, 'return': 0.04},
        {'profit': -30, 'return': -0.015},
        {'profit': 120, 'return': 0.06},
        {'profit': 60, 'return': 0.03},
        {'profit': -40, 'return': -0.02},
        {'profit': 90, 'return': 0.045},
    ]
    
    result = evaluator.evaluate(trades)
    print(f"✓ 策略评估结果:")
    print(f"  - 命中率: {result.hit_rate:.1%}")
    print(f"  - 盈亏比: {result.profit_factor:.2f}")
    print(f"  - 最大连亏: {result.max_consecutive_losses}次")
    print(f"  - 期望收益: {result.expectancy:.2f}")
    
    return True


def test_unified_strategy_engine():
    """测试统一策略引擎"""
    print("\n=== 测试统一策略引擎 ===")
    from backtesting.unified_strategy_engine import UnifiedStrategyEngine
    
    engine = UnifiedStrategyEngine()
    
    # 测试各种市场情况
    test_cases = [
        (2.5, 1.2, "强势上涨"),
        (0.8, 0.6, "持续上涨"),
        (0.1, 0.8, "上涨放缓"),
        (1.2, -0.5, "反转上涨"),
        (-0.8, 0.8, "反转下跌"),
        (-2.5, 0.05, "首次大跌"),
        (-1.5, -1.0, "持续下跌"),
    ]
    
    for today, prev, desc in test_cases:
        result = engine.analyze(today, prev)
        print(f"✓ {desc}: 今日={today}%, 昨日={prev}%")
        print(f"    策略: {result.strategy_name}, 动作: {result.action}, 倍数: {result.final_buy_multiplier:.2f}")
    
    return True


def test_strategy_adapter():
    """测试策略适配器"""
    print("\n=== 测试策略适配器 ===")
    from backtesting.strategy_adapter import StrategyAdapter
    
    adapter = StrategyAdapter(base_amount=100)
    
    # 测试旧接口兼容性
    result = adapter.get_investment_strategy(0.02, 0.01)
    status_label, is_buy, redeem_amount, _, operation_suggestion, execution_amount, buy_multiplier = result
    
    print(f"✓ 旧接口兼容性测试:")
    print(f"  - 状态: {status_label}")
    print(f"  - 买入: {is_buy}")
    print(f"  - 倍数: {buy_multiplier:.2f}")
    print(f"  - 建议: {operation_suggestion}")
    
    # 测试完整分析
    history = [0.001, 0.002, 0.001, 0.003, 0.002, 0.004, 0.003, 0.005, 0.004, 0.006]
    full_result = adapter.get_full_analysis(0.008, 0.006, history, -0.05)
    
    print(f"✓ 完整分析测试:")
    print(f"  - 趋势: {full_result.trend}")
    print(f"  - 波动率: {full_result.volatility:.1%}")
    print(f"  - 最终倍数: {full_result.final_buy_multiplier:.2f}")
    
    return True


def test_backtest_engine_integration():
    """测试回测引擎集成"""
    print("\n=== 测试回测引擎集成 ===")
    from backtesting.backtest_engine import FundBacktest
    
    # 测试使用统一策略引擎
    backtester = FundBacktest(base_amount=100, use_unified_strategy=True)
    
    result = backtester.get_investment_strategy(0.02, 0.01)
    status_label, is_buy, redeem_amount, _, operation_suggestion, execution_amount, buy_multiplier = result
    
    print(f"✓ 统一策略引擎模式:")
    print(f"  - 状态: {status_label}")
    print(f"  - 买入: {is_buy}")
    print(f"  - 倍数: {buy_multiplier:.2f}")
    
    # 测试使用原始策略
    backtester_legacy = FundBacktest(base_amount=100, use_unified_strategy=False)
    
    result_legacy = backtester_legacy.get_investment_strategy(0.02, 0.01)
    status_label_legacy, is_buy_legacy, _, _, _, _, buy_multiplier_legacy = result_legacy
    
    print(f"✓ 原始策略模式:")
    print(f"  - 状态: {status_label_legacy}")
    print(f"  - 买入: {is_buy_legacy}")
    print(f"  - 倍数: {buy_multiplier_legacy:.2f}")
    
    # 测试完整分析功能
    full_result = backtester.get_full_analysis(0.02, 0.01)
    if full_result:
        print(f"✓ 完整分析功能可用")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("投资策略优化模块集成测试")
    print("=" * 60)
    
    tests = [
        ("策略配置", test_strategy_config),
        ("止损管理", test_stop_loss_manager),
        ("趋势分析", test_trend_analyzer),
        ("仓位管理", test_position_manager),
        ("策略评估", test_strategy_evaluator),
        ("统一策略引擎", test_unified_strategy_engine),
        ("策略适配器", test_strategy_adapter),
        ("回测引擎集成", test_backtest_engine_integration),
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
