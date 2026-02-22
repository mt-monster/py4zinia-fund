#!/usr/bin/env python
# coding: utf-8
"""
策略显示优化效果演示

展示优化后的策略分析功能：
1. 买入操作显示"今日买入"及具体金额
2. 赎回操作显示具体赎回金额
3. 无需操作时显示明确提示
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting import UnifiedStrategyEngine

def demo_optimization_effects():
    """演示优化效果"""
    print("=" * 60)
    print("智能策略分析显示优化效果演示")
    print("=" * 60)
    
    engine = UnifiedStrategyEngine()
    
    # 演示不同的市场场景
    scenarios = [
        {
            'name': '📈 强势上涨场景',
            'today_return': 2.5,
            'prev_day_return': 1.8,
            'base_invest': 100,
            'description': '基金连续大涨，策略建议'
        },
        {
            'name': '📉 明显下跌场景', 
            'today_return': -2.0,
            'prev_day_return': -1.2,
            'base_invest': 100,
            'description': '基金连续下跌，定投买入建议'
        },
        {
            'name': '🔄 趋势反转场景',
            'today_return': 1.5,
            'prev_day_return': -0.8,
            'base_invest': 100,
            'description': '由跌转涨，策略建议'
        },
        {
            'name': '⏸️ 横盘整理场景',
            'today_return': 0.2,
            'prev_day_return': 0.1,
            'base_invest': 100,
            'description': '小幅波动，策略建议'
        }
    ]
    
    print("优化前的显示方式：")
    print("  - 买入1.5×定额")
    print("  - 赎回¥500")
    print("  - 持有不动")
    print()
    
    print("优化后的显示方式：")
    print("-" * 60)
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['name']}")
        print(f"   市场情况: 今日{scenario['today_return']:+.1f}%, 昨日{scenario['prev_day_return']:+.1f}%")
        
        # 执行策略分析
        result = engine.analyze(
            today_return=scenario['today_return'],
            prev_day_return=scenario['prev_day_return'],
            base_invest=scenario['base_invest']
        )
        
        print(f"   策略建议: {result.status_label}")
        print(f"   操作指示: {result.execution_amount}")
        print(f"   详细说明: {result.operation_suggestion}")
        print(f"   最终倍数: {result.final_buy_multiplier:.2f}×")
        if result.redeem_amount > 0:
            print(f"   赎回金额: ¥{result.redeem_amount:.2f}")
        print()

    print("=" * 60)
    print("优化亮点总结:")
    print("✅ 买入操作明确显示'今日买入'及具体金额")
    print("✅ 赎回操作显示具体赎回金额或比例")
    print("✅ 无需操作时给出明确提示")
    print("✅ 界面显示更加直观易懂")
    print("✅ 支持自定义基准定投金额")
    print("=" * 60)

if __name__ == "__main__":
    demo_optimization_effects()