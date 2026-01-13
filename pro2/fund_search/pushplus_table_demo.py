#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PushPlus表格发送功能演示程序
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from enhanced_notification import EnhancedNotificationManager
from enhanced_config import NOTIFICATION_CONFIG


def demo_pushplus_table_sending():
    """
    演示PushPlus表格发送功能
    """
    print("PushPlus表格发送功能演示程序")
    print()
    print("=" * 60)
    print("现有通知功能演示")
    print("=" * 60)
    
    # 创建通知管理器实例
    notification_manager = EnhancedNotificationManager(NOTIFICATION_CONFIG)
    
    # 创建模拟基金数据
    sample_fund_data = pd.DataFrame({
        'fund_code': ['005918', '006373', '008015', '008286', '010809'],
        'fund_name': ['广发科技先锋混合', '中欧医疗创新股票C', '汇添富消费行业混合', '易方达蓝筹精选混合', '景顺长城新能源产业股票'],
        'today_return': [0.025, -0.012, 0.008, 0.015, -0.005],
        'annualized_return': [0.25, 0.18, 0.22, 0.30, 0.15],
        'sharpe_ratio': [1.25, 0.95, 1.15, 1.45, 0.85],
        'max_drawdown': [-0.15, -0.18, -0.12, -0.20, -0.10],
        'volatility': [0.18, 0.22, 0.16, 0.25, 0.14],
        'win_rate': [0.68, 0.62, 0.65, 0.72, 0.58],
        'composite_score': [0.82, 0.72, 0.78, 0.85, 0.68],
        'operation_suggestion': ['积极买入', '谨慎观望', '适量买入', '积极买入', '持有']
    })
    
    # 创建策略汇总数据
    sample_strategy_summary = {
        'action_distribution': {'买入': 3, '持有': 1, '卖出': 1},
        'avg_buy_multiplier': 1.5,
        'total_redeem_amount': 15000,
        'buy_signals': 2,
        'sell_signals': 1,
        'hold_signals': 2
    }
    
    # 创建报告文件信息
    sample_report_files = {
        'performance_overview': '图表1.png',
        'return_analysis': '图表2.png',
        'risk_analysis': '图表3.png',
        'composite_score': '图表4.png'
    }
    
    # 测试生成综合报告
    print("1. 测试生成综合报告:")
    report_data = notification_manager.generate_comprehensive_report(
        sample_fund_data, sample_strategy_summary, sample_report_files, "2026-01-13"
    )
    print(f"报告生成状态: {report_data['generated_at']}")
    print(f"HTML报告长度: {len(report_data['html'])} 字符")
    print()
    
    # 测试发送简单通知
    print("2. 测试发送简单通知:")
    simple_success = notification_manager.send_simple_notification("测试标题", "这是测试内容")
    print(f"简单通知发送结果: {simple_success}")
    print()
    
    # 测试发送综合通知
    print("3. 测试发送综合通知:")
    # 首先生成报告数据，然后发送综合通知
    report_data = notification_manager.generate_comprehensive_report(
        sample_fund_data, sample_strategy_summary, sample_report_files, "2026-01-13"
    )
    comprehensive_success = notification_manager.send_comprehensive_notification(
        report_data, sample_report_files
    )
    print(f"综合通知发送结果: {comprehensive_success}")
    print()
    
    print("=" * 60)
    print("PushPlus表格发送功能演示")
    print("=" * 60)
    
    print("1. 模拟基金数据:")
    print(sample_fund_data.to_string(index=False))
    print()
    
    print("2. 发送基金表格通知...")
    success = notification_manager.send_fund_table_notification(
        fund_data=sample_fund_data,
        title="📊 基金分析表格 - Demo",
        strategy_summary=sample_strategy_summary
    )
    
    if success:
        print("✅ 表格通知发送成功!")
    else:
        print("❌ 表格通知发送失败!")
    
    print()
    print("3. 单独发送基金数据表格...")
    simple_table_success = notification_manager.send_fund_table_notification(
        fund_data=sample_fund_data.head(3),
        title="🔍 精选基金表格",
        strategy_summary=None
    )
    
    if simple_table_success:
        print("✅ 精选表格通知发送成功!")
    else:
        print("❌ 精选表格通知发送失败!")
    
    print()
    print("演示完成！")


def demo_report_format():
    """
    演示报告格式已统一为表格格式
    """
    print("所有演示完成！")


if __name__ == "__main__":
    demo_pushplus_table_sending()
    demo_report_format()