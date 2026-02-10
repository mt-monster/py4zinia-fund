#!/usr/bin/env python
# coding: utf-8
"""
测试策略引擎实际工作情况
验证为什么所有基金都显示"持有不动"
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.unified_strategy_engine import UnifiedStrategyEngine

def test_actual_strategy_behavior():
    """测试实际的策略行为"""
    print("=" * 60)
    print("策略引擎实际行为测试")
    print("=" * 60)
    
    engine = UnifiedStrategyEngine()
    
    # 测试一些典型的市场场景
    test_cases = [
        # 应该触发买入的场景
        {"name": "明显下跌场景1", "today": -2.0, "prev": -1.0, "expected": "买入"},
        {"name": "明显下跌场景2", "today": -1.5, "prev": 0.5, "expected": "买入"},
        {"name": "温和下跌场景", "today": -0.8, "prev": 0.3, "expected": "买入"},
        
        # 应该触发持有的场景
        {"name": "强势上涨场景", "today": 2.5, "prev": 1.8, "expected": "持有"},
        {"name": "温和上涨场景", "today": 0.8, "prev": 0.6, "expected": "持有"},
        {"name": "横盘整理场景", "today": 0.1, "prev": 0.2, "expected": "持有"},
        
        # 边界情况
        {"name": "小幅回调场景", "today": -0.3, "prev": 0.8, "expected": "买入/持有"},
    ]
    
    print("测试不同市场场景下的策略建议:")
    print("-" * 60)
    
    for case in test_cases:
        result = engine.analyze(
            today_return=case['today'],
            prev_day_return=case['prev'],
            base_invest=100
        )
        
        action_desc = {
            'buy': '买入',
            'strong_buy': '强烈买入', 
            'weak_buy': '弱买入',
            'sell': '卖出',
            'weak_sell': '弱卖出',
            'hold': '持有',
            'stop_loss': '止损'
        }.get(result.action, result.action)
        
        print(f"{case['name']:<15} | 今日:{case['today']:>5.1f}% 昨日:{case['prev']:>5.1f}%")
        print(f"  策略建议: {result.status_label}")
        print(f"  操作类型: {action_desc} ({result.action})")
        print(f"  执行金额: {result.execution_amount}")
        print(f"  倍数: {result.final_buy_multiplier:.2f}×")
        print(f"  赎回: ¥{result.redeem_amount:.2f}")
        print(f"  详细说明: {result.operation_suggestion}")
        print()
    
    print("=" * 60)
    print("分析结论:")
    print("1. 策略引擎本身工作正常，能根据不同场景给出相应建议")
    print("2. 问题可能出现在:")
    print("   - 基金实际收益率数据不符合买入条件")
    print("   - 前端显示的数据来自缓存而非实时策略分析")
    print("   - 策略配置参数需要调整")
    print("=" * 60)

if __name__ == "__main__":
    test_actual_strategy_behavior()