#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略对比分析主程序
Strategy Comparison Analysis Main Program

运行基金策略对比分析，生成绩效报告和操作建议
"""

import argparse
import math
import re
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
    parser.add_argument('--save-charts', dest='save_charts', action='store_true', default=True,
                        help='是否保存图表（默认生成）')
    parser.add_argument('--no-charts', dest='save_charts', action='store_false',
                        help='不生成图表')
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

def _safe_filename(name):
    """生成安全的文件名"""
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]+", "_", str(name)).strip("_").lower()
    return cleaned or "strategy"

def _calculate_drawdown_series(values: pd.Series) -> pd.Series:
    """计算回撤序列"""
    if values.empty:
        return pd.Series(dtype=float)
    cumulative = values / values.iloc[0]
    rolling_max = cumulative.cummax()
    return cumulative / rolling_max - 1

def _calculate_period_return(values: pd.Series, days: int):
    """计算指定窗口的区间收益率"""
    if values is None or values.empty or len(values) <= days:
        return None
    start_value = values.iloc[-days]
    end_value = values.iloc[-1]
    if start_value == 0:
        return None
    return end_value / start_value - 1

def _format_percent(value, digits: int = 2) -> str:
    """格式化百分比值"""
    if value is None:
        return "数据不足"
    try:
        if isinstance(value, float) and np.isnan(value):
            return "数据不足"
    except TypeError:
        return "数据不足"
    return f"{value * 100:.{digits}f}%"

def _format_number(value, digits: int = 2) -> str:
    """格式化数值"""
    if value is None:
        return "数据不足"
    try:
        if isinstance(value, float) and np.isnan(value):
            return "数据不足"
    except TypeError:
        return "数据不足"
    return f"{value:.{digits}f}"

def _build_period_return_table(strategy_results, periods):

    """构建多周期收益率对比表"""
    rows = []
    for strategy_name, df in strategy_results.items():
        if df.empty or 'portfolio_value' not in df.columns:
            continue
        values = df['portfolio_value']
        row = {'策略名称': strategy_name}
        for label, days in periods:
            period_return = _calculate_period_return(values, days)
            row[label] = _format_percent(period_return)
        rows.append(row)
    return pd.DataFrame(rows)

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
            
            metrics = results['strategy_metrics']
            strategies = list(metrics.keys())
            indicators = ['总收益率', '夏普比率', '胜率', '盈亏比', '稳定性']
            colors = plt.cm.Set3(np.linspace(0, 1, len(strategies)))
            
            for i, strategy in enumerate(strategies):
                values = metrics[strategy]
                normalized_values = [
                    min(max(values['total_return'] * 2, 0), 1),
                    min(max(values['sharpe_ratio'] / 2, 0), 1),
                    values['win_rate'],
                    min(max(values['profit_loss_ratio'] / 3, 0), 1),
                    1 - min(max(abs(values['max_drawdown']) * 10, 0), 1)
                ]
                
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
                df_metrics['max_drawdown'] * 100,
                df_metrics['annualized_return'] * 100,
                s=df_metrics['sharpe_ratio'] * 100,
                c=df_metrics['sharpe_ratio'],
                cmap='viridis',
                alpha=0.7,
                edgecolors='black'
            )
            
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
        
        # 4. 不同时间段收益曲线对比
        if 'strategy_results' in results and results['strategy_results']:
            non_empty_results = [df for df in results['strategy_results'].values() if not df.empty]
            if non_empty_results:
                max_length = max(len(df) for df in non_empty_results)
                period_windows = [('近1个月', 30), ('近3个月', 90), ('近6个月', 180), ('近1年', 365)]
                available_periods = [(label, days) for label, days in period_windows if max_length > days]
                
                if available_periods:
                    rows = math.ceil(len(available_periods) / 2)
                    cols = 2 if len(available_periods) > 1 else 1
                    fig, axes = plt.subplots(rows, cols, figsize=(14, 4 * rows))
                    if not isinstance(axes, np.ndarray):
                        axes = np.array([axes])
                    axes = axes.flatten()
                    
                    for idx, (label, days) in enumerate(available_periods):
                        ax = axes[idx]
                        for strategy_name, result_df in results['strategy_results'].items():
                            if result_df.empty or len(result_df) <= days:
                                continue
                            window_df = result_df.iloc[-days:]
                            values = window_df['portfolio_value']
                            returns = (values / values.iloc[0] - 1) * 100
                            ax.plot(window_df.index, returns, label=strategy_name, linewidth=1.6)
                        ax.set_title(f"{label}收益曲线", fontsize=12)
                        ax.grid(True, alpha=0.3)
                        ax.set_ylabel('累计收益率 (%)')
                    
                    for j in range(len(available_periods), len(axes)):
                        fig.delaxes(axes[j])
                    
                    handles, labels = axes[0].get_legend_handles_labels()
                    if handles:
                        fig.legend(handles, labels, loc='upper center', ncol=3)
                    fig.tight_layout(rect=[0, 0, 1, 0.95])
                    
                    chart_file = os.path.join(charts_dir, 'strategy_returns_by_period.png')
                    plt.savefig(chart_file, dpi=300, bbox_inches='tight')
                    plt.close()
                    print(f"✓ 多周期收益曲线图已保存: {chart_file}")

        
        # 5. 风险指标与关键统计对比
        if 'strategy_metrics' in results and results['strategy_metrics']:
            metrics_df = pd.DataFrame(results['strategy_metrics']).T
            if not metrics_df.empty:
                fig, axes = plt.subplots(2, 2, figsize=(14, 10))
                axes = axes.flatten()
                
                axes[0].bar(metrics_df.index, metrics_df['annualized_return'] * 100, color='#1f77b4', alpha=0.75)
                axes[0].set_title('年化收益率 (%)')
                axes[0].tick_params(axis='x', rotation=30)
                axes[0].grid(axis='y', alpha=0.3)
                
                axes[1].bar(metrics_df.index, metrics_df['annualized_volatility'] * 100, color='#ff7f0e', alpha=0.75)
                axes[1].set_title('年化波动率 (%)')
                axes[1].tick_params(axis='x', rotation=30)
                axes[1].grid(axis='y', alpha=0.3)
                
                axes[2].bar(metrics_df.index, metrics_df['max_drawdown'].abs() * 100, color='#d62728', alpha=0.75)
                axes[2].set_title('最大回撤 (%)')
                axes[2].tick_params(axis='x', rotation=30)
                axes[2].grid(axis='y', alpha=0.3)
                
                axes[3].bar(metrics_df.index, metrics_df['sharpe_ratio'], color='#2ca02c', alpha=0.75)
                axes[3].set_title('夏普比率')
                axes[3].tick_params(axis='x', rotation=30)
                axes[3].grid(axis='y', alpha=0.3)
                
                fig.tight_layout()
                chart_file = os.path.join(charts_dir, 'risk_metrics_comparison.png')
                plt.savefig(chart_file, dpi=300, bbox_inches='tight')
                plt.close()
                print(f"✓ 风险指标对比图已保存: {chart_file}")
        
        return True
        
    except ImportError:
        print("⚠️  未安装matplotlib，无法生成图表")
        return False
    except Exception as e:
        print(f"⚠️  生成图表时出错: {e}")
        return False


def create_strategy_detail_charts(results, output_dir):
    """为每个策略生成回测详情图表"""
    try:
        import matplotlib.pyplot as plt
        
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        charts_dir = os.path.join(output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        
        if 'strategy_results' not in results or not results['strategy_results']:
            return []
        
        saved_files = []
        for strategy_name, result_df in results['strategy_results'].items():
            if result_df.empty or 'portfolio_value' not in result_df.columns:
                continue
            
            values = result_df['portfolio_value']
            normalized = values / values.iloc[0]
            drawdown = _calculate_drawdown_series(values) * 100
            daily_returns = values.pct_change().dropna() * 100
            rolling_vol = values.pct_change().rolling(20, min_periods=5).std() * np.sqrt(252) * 100
            
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            
            # 净值走势
            axes[0, 0].plot(result_df.index, normalized, color='#1f77b4', linewidth=1.8)
            axes[0, 0].set_title('净值曲线 (起始=1.0)')
            axes[0, 0].grid(True, alpha=0.3)
            
            # 回撤曲线
            axes[0, 1].plot(result_df.index, drawdown, color='#d62728', linewidth=1.4)
            axes[0, 1].set_title('回撤曲线 (%)')
            axes[0, 1].grid(True, alpha=0.3)
            
            # 滚动波动率
            axes[1, 0].plot(result_df.index, rolling_vol, color='#ff7f0e', linewidth=1.4)
            axes[1, 0].set_title('20日滚动年化波动率 (%)')
            axes[1, 0].grid(True, alpha=0.3)
            
            # 日收益率分布
            axes[1, 1].hist(daily_returns, bins=30, color='#2ca02c', alpha=0.7)
            axes[1, 1].set_title('日收益率分布 (%)')
            axes[1, 1].grid(True, alpha=0.3)
            
            fig.suptitle(f"{strategy_name} 回测概览", fontsize=14)
            fig.tight_layout(rect=[0, 0, 1, 0.95])
            
            file_name = f"strategy_{_safe_filename(strategy_name)}_backtest_overview.png"
            chart_file = os.path.join(charts_dir, file_name)
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            saved_files.append(chart_file)
        
        return saved_files
    except ImportError:
        print("⚠️  未安装matplotlib，无法生成策略详情图表")
        return []
    except Exception as e:
        print(f"⚠️  生成策略详情图表时出错: {e}")
        return []

def generate_detailed_report(results, output_dir, include_charts: bool = True):
    """生成详细报告"""


    try:
        os.makedirs(output_dir, exist_ok=True)
        charts_dir = os.path.join(output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        
        # 生成图表（报告依赖）
        if include_charts:
            create_performance_charts(results, output_dir)
            create_strategy_detail_charts(results, output_dir)

        
        report_file = os.path.join(output_dir, 'strategy_comparison_report.md')
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 基金策略对比分析报告\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if 'portfolio' in results:
                f.write(f"**基金组合**: {', '.join(results['portfolio'])}\n\n")
            
            if 'comparison_report' in results:
                report = results['comparison_report']
                
                f.write("## 策略对比结果\n\n")
                
                if 'comparison_table' in report:
                    f.write("### 绩效指标对比\n\n")
                    f.write(report['comparison_table'].to_markdown(index=False))
                    f.write("\n\n")
                
                if results.get('strategy_results'):
                    period_windows = [('近1个月', 30), ('近3个月', 90), ('近6个月', 180), ('近1年', 365)]
                    period_table = _build_period_return_table(results['strategy_results'], period_windows)
                    if not period_table.empty:
                        f.write("### 多周期收益对比\n\n")
                        f.write(period_table.to_markdown(index=False))
                        f.write("\n\n")
                        period_chart = os.path.join(charts_dir, 'strategy_returns_by_period.png')
                        if os.path.exists(period_chart):
                            f.write("![多周期收益曲线](charts/strategy_returns_by_period.png)\n\n")
                
                if results.get('strategy_metrics'):
                    metrics_df = pd.DataFrame(results['strategy_metrics']).T
                    if not metrics_df.empty:
                        metrics_table = pd.DataFrame({
                            '策略名称': metrics_df.index,
                            '年化收益率': metrics_df['annualized_return'].apply(_format_percent),
                            '年化波动率': metrics_df['annualized_volatility'].apply(_format_percent),
                            '最大回撤': metrics_df['max_drawdown'].apply(_format_percent),
                            '夏普比率': metrics_df['sharpe_ratio'].apply(_format_number),
                            '胜率': metrics_df['win_rate'].apply(_format_percent),
                            '盈亏比': metrics_df['profit_loss_ratio'].apply(_format_number)
                        })

                        f.write("### 风险指标对比\n\n")
                        f.write(metrics_table.to_markdown(index=False))
                        f.write("\n\n")
                        risk_chart = os.path.join(charts_dir, 'risk_metrics_comparison.png')
                        if os.path.exists(risk_chart):
                            f.write("![风险指标对比](charts/risk_metrics_comparison.png)\n\n")
                
                summary_chart = os.path.join(charts_dir, 'strategy_returns_comparison.png')
                if os.path.exists(summary_chart):
                    f.write("### 收益曲线总览\n\n")
                    f.write("![收益率对比](charts/strategy_returns_comparison.png)\n\n")
                
                radar_chart = os.path.join(charts_dir, 'strategy_radar_chart.png')
                if os.path.exists(radar_chart):
                    f.write("### 综合指标雷达图\n\n")
                    f.write("![综合指标雷达图](charts/strategy_radar_chart.png)\n\n")
                
                scatter_chart = os.path.join(charts_dir, 'risk_return_scatter.png')
                if os.path.exists(scatter_chart):
                    f.write("### 风险收益散点图\n\n")
                    f.write("![风险收益散点图](charts/risk_return_scatter.png)\n\n")
                
                if 'best_strategy' in report:
                    best = report['best_strategy']
                    f.write("## 最佳策略推荐\n\n")
                    f.write(f"**策略名称**: {best['name']}\n\n")
                    f.write(f"**策略描述**: {best['description']}\n\n")
                    f.write(f"**综合评分**: {best['score']:.3f}\n\n")
                    
                    f.write("### 关键指标\n\n")
                    metrics = best['metrics']
                    f.write(f"- 总收益率: {_format_percent(metrics['total_return'])}\n")
                    f.write(f"- 年化收益率: {_format_percent(metrics['annualized_return'])}\n")
                    f.write(f"- 最大回撤: {_format_percent(metrics['max_drawdown'])}\n")
                    f.write(f"- 夏普比率: {_format_number(metrics['sharpe_ratio'])}\n")
                    f.write(f"- 胜率: {_format_percent(metrics['win_rate'])}\n")
                    f.write(f"- 盈亏比: {_format_number(metrics['profit_loss_ratio'])}\n\n")

                
                if results.get('strategy_results'):
                    f.write("## 单策略回测详情\n\n")
                    for strategy_name, result_df in results['strategy_results'].items():
                        f.write(f"### {strategy_name}\n\n")
                        metrics = results.get('strategy_metrics', {}).get(strategy_name, {})
                        if metrics:
                            f.write("**关键指标**\n\n")
                            f.write(f"- 总收益率: {_format_percent(metrics.get('total_return'))}\n")
                            f.write(f"- 年化收益率: {_format_percent(metrics.get('annualized_return'))}\n")
                            f.write(f"- 年化波动率: {_format_percent(metrics.get('annualized_volatility'))}\n")
                            f.write(f"- 最大回撤: {_format_percent(metrics.get('max_drawdown'))}\n")
                            f.write(f"- 夏普比率: {_format_number(metrics.get('sharpe_ratio'))}\n")
                            f.write(f"- 胜率: {_format_percent(metrics.get('win_rate'))}\n")
                            f.write(f"- 盈亏比: {_format_number(metrics.get('profit_loss_ratio'))}\n\n")

                        
                        chart_name = f"strategy_{_safe_filename(strategy_name)}_backtest_overview.png"
                        chart_path = os.path.join(charts_dir, chart_name)
                        if os.path.exists(chart_path):
                            f.write(f"![{strategy_name} 回测概览](charts/{chart_name})\n\n")
                
                if 'recommendations' in report:
                    f.write("## 操作建议\n\n")
                    for i, rec in enumerate(report['recommendations'], 1):
                        f.write(f"{i}. {rec}\n")
                    f.write("\n")
                
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
        report_file = generate_detailed_report(results, args.output_dir, include_charts=args.save_charts)
        if report_file:
            saved_files['detailed_report'] = report_file

        
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