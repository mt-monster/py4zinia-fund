#!/usr/bin/env python
# coding: utf-8

"""
基金组合回测系统主程序

该程序是整个基金组合回测系统的入口点，允许用户通过命令行配置不同的回测参数。
"""

import argparse
from top_funds_backtest import TopFundsBacktest

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
    
    # 相似性分析参数
    parser.add_argument('--lookback-days', type=int, default=180,
                        help='相似性分析的回溯天数，默认为180天')
    parser.add_argument('--n-clusters', type=int, default=4,
                        help='聚类数量，默认为4')
    parser.add_argument('--correlation-threshold', type=float, default=0.5,
                        help='相关性阈值，默认为0.5')
    
    # 回测参数
    parser.add_argument('--base-amount', type=float, default=100,
                        help='基准定投金额，默认为100元')
    parser.add_argument('--portfolio-size', type=int, default=8,
                        help='组合中基金数量，默认为8')
    
    # 基金筛选参数
    parser.add_argument('--top-n', type=int, default=20,
                        help='获取排名前N的基金，默认为20')
    parser.add_argument('--rank-type', type=str, default='daily',
                        choices=['daily', 'weekly', 'monthly'],
                        help='排名类型，可选值为daily、weekly、monthly，默认为daily')
    
    # 组合构建参数
    parser.add_argument('--portfolio-method', type=str, default='diversified',
                        choices=['diversified', 'low_corr'],
                        help='组合构建方法，可选值为diversified、low_corr，默认为diversified')
    
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
    
    # 创建回测实例
    backtest = TopFundsBacktest(
        backtest_start_date=args.start_date,
        backtest_end_date=args.end_date,
        lookback_days=args.lookback_days,
        base_amount=args.base_amount,
        portfolio_size=args.portfolio_size,
        n_clusters=args.n_clusters,
        correlation_threshold=args.correlation_threshold
    )
    
    # 运行完整回测流程
    result, metrics, portfolio = backtest.run_full_backtest_flow(
        top_n=args.top_n,
        rank_type=args.rank_type,
        portfolio_method=args.portfolio_method
    )
    
    # 保存回测结果
    if result is not None:
        result_path = f'{args.output_dir}/top_funds_backtest_result.csv'
        result.to_csv(result_path, index=False)
        print(f"回测结果已保存到{result_path}")
    
    # 保存绩效指标
    if metrics:
        import pandas as pd
        metrics_df = pd.DataFrame([metrics])
        metrics_path = f'{args.output_dir}/top_funds_performance_metrics.csv'
        metrics_df.to_csv(metrics_path, index=False)
        print(f"绩效指标已保存到{metrics_path}")
    
    # 保存基金组合
    if portfolio:
        import pandas as pd
        portfolio_df = pd.DataFrame({'fund_code': portfolio})
        portfolio_path = f'{args.output_dir}/top_funds_portfolio.csv'
        portfolio_df.to_csv(portfolio_path, index=False)
        print(f"基金组合已保存到{portfolio_path}")

if __name__ == "__main__":
    main()
