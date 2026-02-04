#!/usr/bin/env python
# coding: utf-8

"""
调试策略加载失败问题
"""

import sys
import os
sys.path.append('.')

try:
    from backtesting.strategy_report_parser import StrategyReportParser
    print("✅ 成功导入 StrategyReportParser")
    
    # 测试解析器
    report_path = '../fund_backtest/strategy_results/strategy_comparison_report.md'
    print(f"📁 报告路径: {report_path}")
    
    if os.path.exists(report_path):
        print("✅ 报告文件存在")
        
        parser = StrategyReportParser(report_path)
        print("✅ 解析器初始化成功")
        
        try:
            strategies = parser.parse()
            print(f"✅ 成功解析 {len(strategies)} 个策略:")
            
            for i, strategy in enumerate(strategies, 1):
                print(f"  {i}. {strategy['strategy_id']}: {strategy['name']}")
                print(f"     收益率: {strategy['total_return']}%")
                print(f"     描述: {strategy['description']}")
                print()
                
        except Exception as e:
            print(f"❌ 解析策略时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
    else:
        print(f"❌ 报告文件不存在: {report_path}")
        
except ImportError as e:
    print(f"❌ 导入失败: {str(e)}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ 其他错误: {str(e)}")
    import traceback
    traceback.print_exc()