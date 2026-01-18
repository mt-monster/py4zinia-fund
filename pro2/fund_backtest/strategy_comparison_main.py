#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略对比分析主程序
Strategy Comparison Analysis Main Program

运行基金策略对比分析，生成绩效报告和操作建议
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# 导入策略对比引擎
from strategy_comparison_engine import StrategyComparisonEngine

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='基金策略对比分析系统')
    
    # 时间参数
    parser.add_argument('--start-date', type=str, default='2024-01-01',
                        help='回测开始日期，格式YYYY-MM-DD，默认2024-01-01')
    parser.add_argument('--end-date', type=str, default=None,
                        help='回测结束日期，格式YYYY-MM-DD，默认当前日期')
    
    # 基金参数
    parser.add_argument('--top-n', type=int, default=20,
                        help='获取前N只基金，默认20')
    parser.add_argument('--portfolio-size', type=int, default=8,
                        help='基金组合大小，默认8')
    parser.add_argument('--rank-type', type=str, default='daily',
                        choices=['daily', 'weekly', 'monthly'],
                        help='排名类型，默认daily')
    
    # 投资参数
    parser.add_argument('--base-amount', type=float, default=1000,
                        help='基准定投金额，默认1000元')
    
    # 输出参数
    parser.add_argument('--output-dir', type=str, default='./strategy_results',
                        help='输出目录，默认./strategy_results')
    parser.add_argument('--save-charts', action='store_true',
                        help='是否保存图表')
    parser.add_argument('--verbose', action='store_true',
                        help='详细输出模式')
    
    return parser.parse_args()

def print_summary(results):
    """打印结果摘要"""
    if not results or 'comparison_report' not in results:
        print("无有效结果可显示")
        return
    
    report = results['comparison_report']
    
    print("\n" + "=" * 80)
    print("策略对比分析结果摘要")
    print("=" * 80)
    
    # 基本统计
    print(f"参与对比的策略数量: {report['strategy_count']}")
    print(f"基金组合: {results['portfolio']}")
    
    # 对比表格
    print(f"\n策略绩效对比:")
    print("-" * 80)
    comparison_df = report['comparison_table']
    
    # 调整列宽以更好显示
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 20)
    
    print(comparison_df.to_string(index=False))
    
    # 最佳策略
    best = report['best_strategy']
    print(f"\n最佳策略:")
    print("-" * 40)
    print(f"策略名称: {best['name']}")
    print(f"策略描述: {best['description']}")
    print(f"综合评分: {best['score']:.3f}")
    print(f"总收益率: {best['metrics']['total_return']:.2%}")
    print(f"夏普比率: {best['metrics']['sharpe_ratio']:.2f}")
    print(f"最大回撤: {best['metrics']['max_drawdown']:.2%}")
    
    # 操作建议
    print(f"\n操作建议:")
    print("-" * 40)
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"{i}. {rec}")

def create_performance_charts(results, output_dir):
    """创建绩效图表"""
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 创建图表目录
        charts_dir = os.path.join(output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        
        # 1. 策略收益率对比图
        if 'strategy_results' in results and results['strategy_results']:
            plt.figure(figsize=(12, 8))
            
            for strategy_name, result_df in results['strategy_results'].items():
                if not result_df.empty:
                    # 计算累计收益率
                    values = result_df['portfolio_value']
                    returns = (values / values.iloc[0] - 1) * 100
                    plt.plot(result_df.index, returns, label=strategy_name, linewidth=2)
            
            plt.title('各策略累计收益率对比', fontsize=16)
            plt.xlabel('日期', fontsize=12)
            plt.ylabel('累计收益率 (%)', fontsize=12)
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            chart_file = os.path.join(charts_dir, 'strategy_returns_comparison.png')
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✓ 收益率对比图已保存: {chart_file}")
        
        # 2. 策略指标雷达图
        if 'comparison_report' in results and 'best_strategy' in results['comparison_report']:
            fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
            
            # 准备数据
            metrics = results['strategy_metrics']
            strategies = list(metrics.keys())
            
            # 指标名称
            indicators = ['总收益率', '夏普比率', '胜率', '盈亏比', '稳定性']
            
            # 为每个策略绘制雷达图
            colors = plt.cm.Set3(np.linspace(0, 1, len(strategies)))
            
            for i, strategy in enumerate(strategies):
                values = metrics[strategy]
                
                # 标准化指标值到0-1范围
                normalized_values = [
                    min(max(values['total_return'] * 2, 0), 1),  # 总收益率，50%为满分
                    min(max(values['sharpe_ratio'] / 2, 0), 1),  # 夏普比率，2为满分
                    values['win_rate'],  # 胜率
                    min(max(values['profit_loss_ratio'] / 3, 0), 1),  # 盈亏比，3为满分
                    1 - min(max(abs(values['max_drawdown']) * 10, 0), 1)  # 稳定性，10%回撤为0分
                ]
                
                # 闭合雷达图
                normalized_values += normalized_values[:1]
                angles = np.linspace(0, 2 * np.pi, len(indicators), endpoint=False).tolist()
                angles += angles[:1]
                
                ax.plot(angles, normalized_values, 'o-', linewidth=2, label=strategy, color=colors[i])
                ax.fill(angles, normalized_values, alpha=0.25, color=colors[i])
            
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(indicators)
            ax.set_ylim(0, 1)
            ax.set_title('策略综合指标雷达图', fontsize=16, pad=20)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax.grid(True)
            
            chart_file = os.path.join(charts_dir, 'strategy_radar_chart.png')
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✓ 策略雷达图已保存: {chart_file}")
        
        # 3. 风险收益散点图
        if 'strategy_metrics' in results and results['strategy_metrics']:
            plt.figure(figsize=(10, 8))
            
            metrics_data = []
            strategy_names = []
            
            for strategy_name, metrics in results['strategy_metrics'].items():
                metrics_data.append({
                    'annualized_return': metrics['annualized_return'],
                    'max_drawdown': abs(metrics['max_drawdown']),
                    'sharpe_ratio': metrics['sharpe_ratio']
                })
                strategy_names.append(strategy_name)
            
            df_metrics = pd.DataFrame(metrics_data)
            
            scatter = plt.scatter(
                df_metrics['max_drawdown'] * 100,  # X轴：最大回撤
                df_metrics['annualized_return'] * 100,  # Y轴：年化收益率
                s=df_metrics['sharpe_ratio'] * 100,  # 点大小：夏普比率
                c=df_metrics['sharpe_ratio'],  # 颜色：夏普比率
                cmap='viridis',
                alpha=0.7,
                edgecolors='black'
            )
            
            # 添加策略标签
            for i, name in enumerate(strategy_names):
                plt.annotate(
                    name,
                    (df_metrics['max_drawdown'].iloc[i] * 100, df_metrics['annualized_return'].iloc[i] * 100),
                    xytext=(5, 5),
                    textcoords='offset points',
                    fontsize=9
                )
            
            plt.colorbar(scatter, label='夏普比率')
            plt.xlabel('最大回撤 (%)', fontsize=12)
            plt.ylabel('年化收益率 (%)', fontsize=12)
            plt.title('策略风险收益散点图', fontsize=16)
            plt.grid(True, alpha=0.3)
            
            chart_file = os.path.join(charts_dir, 'risk_return_scatter.png')
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✓ 风险收益散点图已保存: {chart_file}")
        
        return True
        
    except ImportError:
        print("⚠️  未安装matplotlib，无法生成图表")
        return False
    except Exception as e:
        print(f"⚠️  生成图表时出错: {e}")
        return False

def generate_detailed_report(results, output_dir):
    """生成详细报告"""
    try:
        # 创建报告目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成Markdown报告
        report_file = os.path.join(output_dir, 'strategy_comparison_report.md')
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 基金策略对比分析报告\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if 'portfolio' in results:
                f.write(f"**基金组合**: {', '.join(results['portfolio'])}\n\n")
            
            if 'comparison_report' in results:
                report = results['comparison_report']
                
                f.write("## 策略对比结果\n\n")
                
                # 对比表格
                if 'comparison_table' in report:
                    f.write("### 绩效指标对比\n\n")
                    f.write(report['comparison_table'].to_markdown(index=False))
                    f.write("\n\n")
                
                # 最佳策略
                if 'best_strategy' in report:
                    best = report['best_strategy']
                    f.write("## 最佳策略推荐\n\n")
                    f.write(f"**策略名称**: {best['name']}\n\n")
                    f.write(f"**策略描述**: {best['description']}\n\n")
                    f.write(f"**综合评分**: {best['score']:.3f}\n\n")
                    
                    f.write("### 关键指标\n\n")
                    metrics = best['metrics']
                    f.write(f"- 总收益率: {metrics['total_return']:.2%}\n")
                    f.write(f"- 年化收益率: {metrics['annualized_return']:.2%}\n")
                    f.write(f"- 最大回撤: {metrics['max_drawdown']:.2%}\n")
                    f.write(f"- 夏普比率: {metrics['sharpe_ratio']:.2f}\n")
                    f.write(f"- 胜率: {metrics['win_rate']:.2%}\n")
                    f.write(f"- 盈亏比: {metrics['profit_loss_ratio']:.2f}\n\n")
                
                # 操作建议
                if 'recommendations' in report:
                    f.write("## 操作建议\n\n")
                    for i, rec in enumerate(report['recommendations'], 1):
                        f.write(f"{i}. {rec}\n")
                    f.write("\n")
                
                # 风险提示
                f.write("## 风险提示\n\n")
                f.write("- 过往业绩不代表未来表现\n")
                f.write("- 投资有风险，入市需谨慎\n")
                f.write("- 建议根据个人风险承受能力选择策略\n")
                f.write("- 可考虑多策略组合以分散风险\n\n")
        
        print(f"✓ 详细报告已保存: {report_file}")
        return report_file
        
    except Exception as e:
        print(f"⚠️  生成详细报告时出错: {e}")
        return None

def main():
    """主程序"""
    # 解析参数
    args = parse_args()
    
    print("=" * 80)
    print("基金策略对比分析系统")
    print("=" * 80)
    print(f"回测时间: {args.start_date} 至 {args.end_date or '当前'}")
    print(f"基金数量: 前{args.top_n}只，组合大小{args.portfolio_size}")
    print(f"基准金额: {args.base_amount} 元")
    print(f"输出目录: {args.output_dir}")
    print("=" * 80)
    
    try:
        # 创建策略对比引擎
        engine = StrategyComparisonEngine(
            backtest_start_date=args.start_date,
            backtest_end_date=args.end_date,
            base_amount=args.base_amount,
            portfolio_size=args.portfolio_size
        )
        
        # 运行策略对比
        print("\n开始运行策略对比分析...")
        results = engine.run_strategy_comparison(
            top_n=args.top_n,
            rank_type=args.rank_type
        )
        
        if not results or not results.get('strategy_results'):
            print("❌ 策略对比失败，无有效结果")
            return
        
        # 创建输出目录
        os.makedirs(args.output_dir, exist_ok=True)
        
        # 保存结果
        print("\n保存分析结果...")
        saved_files = engine.save_results(args.output_dir)
        
        # 生成详细报告
        report_file = generate_detailed_report(results, args.output_dir)
        if report_file:
            saved_files['detailed_report'] = report_file
        
        # 生成图表
        if args.save_charts:
            print("\n生成绩效图表...")
            create_performance_charts(results, args.output_dir)
        
        # 显示结果摘要
        if args.verbose:
            print_summary(results)
        
        # 显示保存的文件
        print(f"\n✓ 分析完成！文件已保存到: {args.output_dir}")
        print("保存的文件:")
        for file_type, file_path in saved_files.items():
            print(f"  - {file_type}: {file_path}")
        
        # 快速查看最佳策略
        if 'comparison_report' in results and 'best_strategy' in results['comparison_report']:
            best = results['comparison_report']['best_strategy']
            print(f"\n🏆 推荐策略: {best['name']}")
            print(f"   综合评分: {best['score']:.3f}")
            print(f"   总收益率: {best['metrics']['total_return']:.2%}")
            print(f"   夏普比率: {best['metrics']['sharpe_ratio']:.2f}")
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断操作")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()