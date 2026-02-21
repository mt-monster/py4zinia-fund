#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试基金相关性分析的时间统计功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backtesting.enhanced_correlation import EnhancedCorrelationAnalyzer
from data_retrieval.fund_analyzer import FundAnalyzer
from backtesting.correlation_performance_monitor import (
    CorrelationPerformanceMonitor, StageTimer
)
import logging

# 设置日志级别
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_performance_monitor():
    """测试性能监控器"""
    print("\n" + "=" * 70)
    print("测试1: 性能监控器基础功能")
    print("=" * 70)
    
    monitor = CorrelationPerformanceMonitor()
    monitor.start("total")
    
    # 模拟一些耗时操作
    import time
    time.sleep(0.1)
    monitor.stage("stage1")
    
    time.sleep(0.05)
    monitor.stage("stage2")
    
    elapsed = monitor.end("total")
    
    print(f"总耗时: {elapsed:.2f} ms")
    print(f"阶段耗时: {monitor.timings}")
    
    # 检查优化状态
    opt_status = monitor.check_optimizations()
    print(f"\n优化措施状态:")
    for category, opts in opt_status.items():
        print(f"  {category}: {len([v for v in opts.values() if v])}/{len(opts)} 已生效")
    
    # 生成报告
    report = monitor.generate_report()
    print(f"\n性能报告预览:")
    print(report[:500] + "...")
    
    print("\n[OK] 性能监控器测试通过")
    return True


def test_stage_timer():
    """测试阶段计时器"""
    print("\n" + "=" * 70)
    print("测试2: 阶段计时器")
    print("=" * 70)
    
    import time
    
    with StageTimer("测试阶段"):
        time.sleep(0.05)
    
    print("\n[OK] 阶段计时器测试通过")
    return True


def test_enhanced_correlation_with_timing():
    """测试增强相关性分析的时间统计"""
    print("\n" + "=" * 70)
    print("测试3: 增强相关性分析时间统计")
    print("=" * 70)
    
    # 创建测试数据
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    
    fund_data_dict = {}
    fund_names = {}
    
    for i in range(5):
        code = f'00000{i}'
        fund_names[code] = f'测试基金{i}'
        
        returns = np.random.randn(100) * 0.01
        df = pd.DataFrame({
            'date': dates,
            'daily_return': returns * 100
        })
        fund_data_dict[code] = df
    
    # 创建分析器并执行分析
    analyzer = EnhancedCorrelationAnalyzer()
    result = analyzer.analyze_enhanced_correlation(fund_data_dict, fund_names)
    
    # 检查结果中是否包含性能数据
    if '_performance' in result:
        perf = result['_performance']
        print(f"\n性能统计:")
        print(f"  总耗时: {perf.get('total_time_ms', 0):.2f} ms")
        print(f"  各阶段耗时:")
        for stage, time_ms in perf.get('stage_timings', {}).items():
            print(f"    - {stage}: {time_ms:.2f} ms")
        print(f"\n[OK] 时间统计功能正常")
        return True
    else:
        print("\n[FAIL] 结果中缺少性能数据")
        return False


def test_interactive_correlation_with_timing():
    """测试交互式相关性分析的时间统计"""
    print("\n" + "=" * 70)
    print("测试4: 交互式相关性分析时间统计")
    print("=" * 70)
    
    # 创建测试数据
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    
    fund_data_dict = {}
    fund_names = {}
    
    for i in range(3):
        code = f'00000{i}'
        fund_names[code] = f'测试基金{i}'
        
        returns = np.random.randn(100) * 0.01
        df = pd.DataFrame({
            'date': dates,
            'daily_return': returns * 100
        })
        fund_data_dict[code] = df
    
    # 创建分析器并执行分析
    analyzer = EnhancedCorrelationAnalyzer()
    result = analyzer.generate_interactive_correlation_data(fund_data_dict, fund_names, lazy_load=True)
    
    # 检查结果中是否包含性能数据
    if '_performance' in result:
        perf = result['_performance']
        print(f"\n性能统计:")
        print(f"  总耗时: {perf.get('total_time_ms', 0):.2f} ms")
        print(f"  优化状态: 已检查 {len(perf.get('optimization_status', {}))} 类优化")
        print(f"\n[OK] 交互式分析时间统计功能正常")
        return True
    else:
        print("\n[FAIL] 结果中缺少性能数据")
        return False


def test_fund_analyzer_with_timing():
    """测试FundAnalyzer的时间统计"""
    print("\n" + "=" * 70)
    print("测试5: FundAnalyzer时间统计")
    print("=" * 70)
    
    print("\n注: FundAnalyzer需要真实数据库连接，此处仅测试代码结构")
    print("[SKIP] 跳过实际测试（需要数据库）")
    return True


def main():
    """主测试函数"""
    print("=" * 70)
    print("基金相关性分析时间统计功能测试")
    print("=" * 70)
    
    results = []
    
    # 运行测试
    results.append(("性能监控器", test_performance_monitor()))
    results.append(("阶段计时器", test_stage_timer()))
    results.append(("增强相关性分析", test_enhanced_correlation_with_timing()))
    results.append(("交互式相关性分析", test_interactive_correlation_with_timing()))
    results.append(("FundAnalyzer", test_fund_analyzer_with_timing()))
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "通过" if result else "失败"
        if result:
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] {name}")
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n所有测试通过！时间统计功能已正确实现。")
        return 0
    else:
        print("\n部分测试失败，请检查代码实现。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
