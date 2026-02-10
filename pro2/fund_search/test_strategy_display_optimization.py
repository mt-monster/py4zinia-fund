#!/usr/bin/env python
# coding: utf-8
"""
测试策略显示优化效果

验证优化后的策略分析功能：
1. 买入操作显示"今日买入"及具体金额
2. 赎回操作显示具体赎回金额
3. 无需操作时显示明确提示
"""

import sys
import os
import logging
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.unified_strategy_engine import UnifiedStrategyEngine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_execution_amount_generation():
    """测试执行金额生成逻辑"""
    print("=" * 60)
    print("测试执行金额生成逻辑")
    print("=" * 60)
    
    engine = UnifiedStrategyEngine()
    
    # 测试用例：不同的操作场景
    test_cases = [
        # 买入场景
        {
            'name': '强烈买入',
            'action': 'strong_buy',
            'multiplier': 2.0,
            'redeem_amount': 0,
            'base_invest': 100,
            'expected_contains': ['今日买入', '¥200.00']
        },
        {
            'name': '普通买入',
            'action': 'buy',
            'multiplier': 1.5,
            'redeem_amount': 0,
            'base_invest': 100,
            'expected_contains': ['今日买入', '¥150.00']
        },
        {
            'name': '弱买入',
            'action': 'weak_buy',
            'multiplier': 0.5,
            'redeem_amount': 0,
            'base_invest': 100,
            'expected_contains': ['今日买入', '¥50.00']
        },
        # 无需买入场景
        {
            'name': '持有不动',
            'action': 'hold',
            'multiplier': 0,
            'redeem_amount': 0,
            'base_invest': 100,
            'expected_contains': ['无需买入']
        },
        # 赎回场景
        {
            'name': '部分赎回',
            'action': 'sell',
            'multiplier': 0,
            'redeem_amount': 500,
            'base_invest': 100,
            'expected_contains': ['赎回金额', '¥500.00']
        },
        {
            'name': '比例赎回',
            'action': 'sell',
            'multiplier': 0,
            'redeem_amount': 0.3,
            'base_invest': 100,
            'expected_contains': ['赎回 30% 持仓']
        },
        # 无需赎回场景
        {
            'name': '无需赎回',
            'action': 'sell',
            'multiplier': 0,
            'redeem_amount': 0,
            'base_invest': 100,
            'expected_contains': ['无需赎回']
        },
        # 止损场景
        {
            'name': '止损',
            'action': 'stop_loss',
            'multiplier': 0,
            'redeem_amount': 100,
            'base_invest': 100,
            'expected_contains': ['全部赎回']
        }
    ]
    
    print(f"{'场景':<12} {'预期包含':<20} {'实际结果':<30} {'测试结果'}")
    print("-" * 80)
    
    passed = 0
    failed = 0
    
    for case in test_cases:
        try:
            # 调用优化后的执行金额生成方法
            result = engine._get_execution_amount(
                action=case['action'],
                multiplier=case['multiplier'],
                redeem_amount=case['redeem_amount'],
                base_invest=case['base_invest']
            )
            
            # 检查是否包含预期的内容
            success = all(keyword in result for keyword in case['expected_contains'])
            
            status = "✅ 通过" if success else "❌ 失败"
            if success:
                passed += 1
            else:
                failed += 1
            
            print(f"{case['name']:<12} {', '.join(case['expected_contains']):<20} {result:<30} {status}")
            
        except Exception as e:
            failed += 1
            print(f"{case['name']:<12} {', '.join(case['expected_contains']):<20} 错误: {str(e):<30} ❌ 失败")
    
    print("-" * 80)
    print(f"总计: {passed + failed}个测试用例, {passed}个通过, {failed}个失败")
    return failed == 0

def test_strategy_analysis_integration():
    """测试策略分析集成效果"""
    print("\n" + "=" * 60)
    print("测试策略分析集成效果")
    print("=" * 60)
    
    engine = UnifiedStrategyEngine()
    
    # 测试不同的收益率组合
    test_scenarios = [
        {
            'name': '强势上涨',
            'today_return': 2.5,
            'prev_day_return': 1.2,
            'base_invest': 100,
            'expected_action': 'strong_buy'
        },
        {
            'name': '温和上涨',
            'today_return': 0.8,
            'prev_day_return': 0.6,
            'base_invest': 100,
            'expected_action': 'buy'
        },
        {
            'name': '小幅回调',
            'today_return': -0.5,
            'prev_day_return': 0.8,
            'base_invest': 100,
            'expected_action': 'buy'
        },
        {
            'name': '明显下跌',
            'today_return': -2.0,
            'prev_day_return': -1.0,
            'base_invest': 100,
            'expected_action': 'buy'  # 定投策略通常在下跌时买入
        }
    ]
    
    print(f"{'场景':<12} {'今日收益率':<10} {'昨日收益率':<10} {'操作类型':<12} {'执行金额':<25} {'测试结果'}")
    print("-" * 90)
    
    passed = 0
    failed = 0
    
    for scenario in test_scenarios:
        try:
            # 执行策略分析
            result = engine.analyze(
                today_return=scenario['today_return'],
                prev_day_return=scenario['prev_day_return'],
                base_invest=scenario['base_invest']
            )
            
            # 检查结果
            action_match = result.action == scenario['expected_action']
            amount_not_empty = bool(result.execution_amount and result.execution_amount.strip())
            
            success = action_match and amount_not_empty
            
            status = "✅ 通过" if success else "❌ 失败"
            if success:
                passed += 1
            else:
                failed += 1
            
            print(f"{scenario['name']:<12} {scenario['today_return']:>8.1f}% {scenario['prev_day_return']:>8.1f}% "
                  f"{result.action:<12} {result.execution_amount:<25} {status}")
            
            # 输出详细信息
            if not success:
                print(f"  详细信息: 策略={result.strategy_name}, 倍数={result.final_buy_multiplier}, "
                      f"建议='{result.operation_suggestion}'")
            
        except Exception as e:
            failed += 1
            print(f"{scenario['name']:<12} {scenario['today_return']:>8.1f}% {scenario['prev_day_return']:>8.1f}% "
                  f"{'错误':<12} 错误: {str(e):<25} ❌ 失败")
    
    print("-" * 90)
    print(f"总计: {passed + failed}个测试场景, {passed}个通过, {failed}个失败")
    return failed == 0

def test_edge_cases():
    """测试边界情况"""
    print("\n" + "=" * 60)
    print("测试边界情况")
    print("=" * 60)
    
    engine = UnifiedStrategyEngine()
    
    edge_cases = [
        {
            'name': '零倍数买入',
            'action': 'buy',
            'multiplier': 0.0,
            'redeem_amount': 0,
            'base_invest': 100,
            'expected_contains': ['无需买入']
        },
        {
            'name': '负倍数买入',
            'action': 'buy',
            'multiplier': -1.0,
            'redeem_amount': 0,
            'base_invest': 100,
            'expected_contains': ['无需买入']
        },
        {
            'name': '极大倍数买入',
            'action': 'buy',
            'multiplier': 10.0,
            'redeem_amount': 0,
            'base_invest': 100,
            'expected_contains': ['今日买入', '¥1000.00']
        },
        {
            'name': '零赎回金额',
            'action': 'sell',
            'multiplier': 0,
            'redeem_amount': 0,
            'base_invest': 100,
            'expected_contains': ['无需赎回']
        }
    ]
    
    print(f"{'测试用例':<15} {'预期结果':<20} {'实际结果':<30} {'测试结果'}")
    print("-" * 80)
    
    passed = 0
    failed = 0
    
    for case in edge_cases:
        try:
            result = engine._get_execution_amount(
                action=case['action'],
                multiplier=case['multiplier'],
                redeem_amount=case['redeem_amount'],
                base_invest=case['base_invest']
            )
            
            success = all(keyword in result for keyword in case['expected_contains'])
            
            status = "✅ 通过" if success else "❌ 失败"
            if success:
                passed += 1
            else:
                failed += 1
            
            print(f"{case['name']:<15} {', '.join(case['expected_contains']):<20} {result:<30} {status}")
            
        except Exception as e:
            failed += 1
            print(f"{case['name']:<15} {', '.join(case['expected_contains']):<20} 错误: {str(e):<30} ❌ 失败")
    
    print("-" * 80)
    print(f"总计: {passed + failed}个边界测试, {passed}个通过, {failed}个失败")
    return failed == 0

def main():
    """主测试函数"""
    print("开始策略显示优化测试...")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_passed = True
    
    # 执行各项测试
    test_results = [
        test_execution_amount_generation(),
        test_strategy_analysis_integration(),
        test_edge_cases()
    ]
    
    # 汇总结果
    all_passed = all(result for result in test_results)
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    if all_passed:
        print("🎉 所有测试通过！策略显示优化功能正常工作。")
        print("\n优化效果:")
        print("✅ 买入操作明确显示'今日买入'及具体金额")
        print("✅ 赎回操作显示具体赎回金额或比例")
        print("✅ 无需操作时给出明确提示")
        print("✅ 界面显示更加直观易懂")
    else:
        print("❌ 部分测试失败，请检查相关代码实现。")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)