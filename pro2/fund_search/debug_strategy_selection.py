#!/usr/bin/env python
# coding: utf-8
"""
调试策略选择逻辑
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.unified_strategy_engine import UnifiedStrategyEngine

def debug_strategy_matching():
    """调试策略匹配逻辑"""
    print("=" * 60)
    print("调试策略匹配逻辑")
    print("=" * 60)
    
    engine = UnifiedStrategyEngine()
    
    # 测试用例
    test_cases = [
        {
            'name': '强势上涨',
            'today_return': 2.5,
            'prev_day_return': 1.2,
            'expected_strategy': 'strong_bull'
        },
        {
            'name': '温和上涨', 
            'today_return': 0.8,
            'prev_day_return': 0.6,
            'expected_strategy': 'bull_continuation'
        },
        {
            'name': '小幅回调',
            'today_return': -0.5,
            'prev_day_return': 0.8,
            'expected_strategy': 'bear_reversal'
        },
        {
            'name': '明显下跌',
            'today_return': -2.0,
            'prev_day_return': -1.0,
            'expected_strategy': 'bear_continuation'
        }
    ]
    
    print("策略规则详情:")
    for strategy_name, rule in engine.strategy_rules.items():
        print(f"\n策略: {strategy_name}")
        print(f"  Action: {rule.get('action', 'N/A')}")
        print(f"  Buy Multiplier: {rule.get('buy_multiplier', 'N/A')}")
        print(f"  Description: {rule.get('description', 'N/A')}")
        print("  条件:")
        for i, condition in enumerate(rule.get('conditions', [])):
            today_min = condition.get('today_return_min', '-∞')
            today_max = condition.get('today_return_max', '+∞')
            prev_min = condition.get('prev_day_return_min', '-∞')
            prev_max = condition.get('prev_day_return_max', '+∞')
            print(f"    {i+1}. 今日: [{today_min}, {today_max}], 昨日: [{prev_min}, {prev_max}]")
    
    print("\n" + "=" * 60)
    print("测试结果:")
    print("=" * 60)
    
    for case in test_cases:
        print(f"\n测试场景: {case['name']}")
        print(f"输入: 今日收益率={case['today_return']}%, 昨日收益率={case['prev_day_return']}%")
        
        # 执行基础策略分析
        result = engine._basic_strategy_analysis(case['today_return'], case['prev_day_return'])
        
        print(f"匹配策略: {result['strategy_name']}")
        print(f"操作类型: {result['action']}")
        print(f"买入倍数: {result['buy_multiplier']}")
        print(f"状态标签: {result['status_label']}")
        print(f"操作建议: {result['operation_suggestion']}")
        
        # 检查是否符合预期
        match_expected = result['strategy_name'] == case['expected_strategy']
        print(f"策略匹配: {'✅' if match_expected else '❌'} (期望: {case['expected_strategy']})")
        
        # 检查倍数是否合理
        multiplier_ok = result['buy_multiplier'] > 0 if result['action'] in ['buy', 'strong_buy'] else result['buy_multiplier'] == 0
        print(f"倍数合理: {'✅' if multiplier_ok else '❌'}")

def debug_full_analysis():
    """调试完整分析流程"""
    print("\n" + "=" * 60)
    print("调试完整分析流程")
    print("=" * 60)
    
    engine = UnifiedStrategyEngine()
    
    # 测试明显下跌场景（应该买入）
    print("测试明显下跌场景 (-2.0%, -1.0%):")
    result = engine.analyze(
        today_return=-2.0,
        prev_day_return=-1.0,
        base_invest=100.0
    )
    
    print(f"最终策略: {result.strategy_name}")
    print(f"操作类型: {result.action}")
    print(f"最终倍数: {result.final_buy_multiplier}")
    print(f"执行金额: {result.execution_amount}")
    print(f"状态标签: {result.status_label}")
    print(f"操作建议: {result.operation_suggestion}")

if __name__ == "__main__":
    debug_strategy_matching()
    debug_full_analysis()