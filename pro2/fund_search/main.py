#!/usr/bin/env python
# coding: utf-8

"""
基金组合回测系统主程序 (已优化)

该程序使用 fund_search/backtesting 模块中的功能，
替代了原 fund_backtest 模块的实现。

主要功能：
1. 单基金回测
2. 基金组合回测
3. 策略绩效分析
"""

import argparse
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtesting.backtest_engine import FundBacktest
from backtesting.enhanced_strategy import EnhancedInvestmentStrategy


def parse_args():
    """
    解析命令行参数
    
    返回：
        argparse.Namespace, 解析后的命令行参数
    """
    parser = argparse.ArgumentParser(description='基金组合回测系统')
    
    # 回测日期参数
    parser.add_argument('--start-date', type=str, default='2024-01-01',
                        help='回测开始日期，格式为YYYY-MM-DD，默认为2024-01-01')
    parser.add_argument('--end-date', type=str, default=None,
                        help='回测结束日期，格式为YYYY-MM-DD，默认为当前日期')
    
    # 回测参数
    parser.add_argument('--base-amount', type=float, default=100,
                        help='基准定投金额，默认为100元')
    parser.add_argument('--fund-code', type=str, default=None,
                        help='基金代码，如果不指定则使用示例基金')
    
    # 输出参数
    parser.add_argument('--output-dir', type=str, default='.',
                        help='输出文件保存目录，默认为当前目录')
    
    return parser.parse_args()


def main():
    """
    主程序入口
    """
    # 解析命令行参数
    args = parse_args()
    
    # 示例基金代码（如果未指定）
    fund_code = args.fund_code or '000001'  # 华夏成长混合
    
    print(f"开始回测基金: {fund_code}")
    print(f"回测区间: {args.start_date} 至 {args.end_date or '今天'}")
    print(f"基准定投金额: {args.base_amount}元")
    
    try:
        # 创建回测引擎实例
        backtest = FundBacktest(
            base_amount=args.base_amount,
            start_date=args.start_date,
            end_date=args.end_date,
            use_unified_strategy=True
        )
        
        # 执行单基金回测
        result, metrics = backtest.backtest_single_fund(fund_code)
        
        if result is not None:
            # 保存回测结果
            import pandas as pd
            
            result_path = f'{args.output_dir}/backtest_result.csv'
            result.to_csv(result_path, index=False)
            print(f"\n✓ 回测结果已保存到: {result_path}")
            
            # 显示关键指标
            print("\n=== 回测绩效指标 ===")
            for key, value in metrics.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.4f}")
                else:
                    print(f"  {key}: {value}")
        else:
            print("\n✗ 回测失败，请检查基金代码是否正确")
            
    except Exception as e:
        print(f"\n✗ 回测过程出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
