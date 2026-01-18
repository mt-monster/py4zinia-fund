#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金策略对比回测引擎
Fund Strategy Comparison Backtest Engine

整合advanced_strategies.py中的高级策略，实现多策略绩效对比分析
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import sys
import os

# 添加路径以导入advanced_strategies
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'fund_search', 'backtesting'))
# 添加路径以导入shared (for enhanced_strategy)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'fund_search'))

from advanced_strategies import get_all_advanced_strategies, BaseStrategy, StrategySignal

# 导入现有模块
from top_funds_backtest import TopFundsBacktest

class StrategyComparisonEngine:
    """
    策略对比回测引擎
    
    功能：
    1. 整合多种高级策略
    2. 对同一基金组合进行多策略回测
    3. 生成策略绩效对比报告
    4. 推荐最佳策略和操作建议
    """
    
    def __init__(self, 
                 backtest_start_date: str = None,
                 backtest_end_date: str = None,
                 base_amount: float = 1000,
                 portfolio_size: int = 8):
        """
        初始化策略对比引擎
        
        参数：
        backtest_start_date: 回测开始日期
        backtest_end_date: 回测结束日期
        base_amount: 基准定投金额
        portfolio_size: 基金组合大小
        """
        self.backtest_start_date = backtest_start_date or '2024-01-01'
        self.backtest_end_date = backtest_end_date or datetime.now().strftime('%Y-%m-%d')
        self.base_amount = base_amount
        self.portfolio_size = portfolio_size
        
        # 初始化高级策略
        self.strategies = get_all_advanced_strategies()
        
        # 初始化基金回测系统
        self.fund_backtest = TopFundsBacktest(
            backtest_start_date=self.backtest_start_date,
            backtest_end_date=self.backtest_end_date,
            base_amount=self.base_amount,
            portfolio_size=self.portfolio_size
        )
        
        # 存储回测结果
        self.strategy_results = {}
        self.strategy_metrics = {}
        
    def prepare_fund_data(self, portfolio: List[str]) -> Dict[str, pd.DataFrame]:
        """
        准备基金数据，为每个策略获取历史数据
        
        参数：
        portfolio: 基金组合代码列表
        
        返回：
        Dict[str, pd.DataFrame]: 每个基金的历史数据
        """
        fund_data = {}
        
        for fund_code in portfolio:
            try:
                # 这里需要实现获取基金历史数据的逻辑
                # 暂时使用模拟数据，实际应该从数据库或API获取
                dates = pd.date_range(start=self.backtest_start_date, end=self.backtest_end_date, freq='D')
                
                # 模拟净值数据（实际应该从数据源获取）
                np.random.seed(hash(fund_code) % 1000)
                initial_nav = 1.0
                daily_returns = np.random.normal(0.0005, 0.02, len(dates))
                nav_series = initial_nav * (1 + daily_returns).cumprod()
                
                fund_df = pd.DataFrame({
                    'date': dates,
                    'nav': nav_series,
                    '单位净值': nav_series  # 兼容性
                }).set_index('date')
                
                fund_data[fund_code] = fund_df
                
            except Exception as e:
                print(f"获取基金 {fund_code} 数据时出错: {e}")
                continue
                
        return fund_data
    
    def backtest_strategy(self, 
                         strategy_name: str,
                         strategy: BaseStrategy,
                         portfolio: List[str],
                         fund_data: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, Dict]:
        """
        对单个策略进行回测
        
        参数：
        strategy_name: 策略名称
        strategy: 策略实例
        portfolio: 基金组合
        fund_data: 基金历史数据
        
        返回：
        Tuple[pd.DataFrame, Dict]: 回测结果和绩效指标
        """
        print(f"\n开始回测策略: {strategy_name}")
        
        # 初始化回测数据
        all_dates = []
        portfolio_values = []
        cash_flows = []
        holdings = []
        signals = []
        
        # 初始状态
        cash = 10000.0  # 初始现金
        current_holdings_value = 0.0
        fund_units = {fund_code: 0.0 for fund_code in portfolio}
        
        # 获取所有交易日期
        if fund_data:
            sample_fund = list(fund_data.values())[0]
            all_dates = sample_fund.index.tolist()
        else:
            return pd.DataFrame(), {}
        
        # 逐日回测
        for i, date in enumerate(all_dates):
            # 计算当前持仓价值
            current_holdings_value = 0.0
            for fund_code in portfolio:
                if fund_code in fund_data and fund_units[fund_code] > 0:
                    current_nav = fund_data[fund_code].loc[date, 'nav']
                    current_holdings_value += fund_units[fund_code] * current_nav
            
            # 为每个基金生成策略信号（简化处理，使用第一个基金的数据）
            signal = StrategySignal('hold', 1.0, "默认持有")
            if portfolio and portfolio[0] in fund_data:
                try:
                    signal = strategy.generate_signal(
                        fund_data[portfolio[0]], 
                        i, 
                        current_holdings=current_holdings_value,
                        cash=cash
                    )
                except Exception as e:
                    print(f"生成策略信号时出错: {e}")
                    signal = StrategySignal('hold', 1.0, "信号生成失败")
            
            # 执行交易
            trade_amount = 0.0
            if signal.action == 'buy':
                trade_amount = self.base_amount * signal.amount_multiplier
                if cash >= trade_amount:
                    # 买入（简化处理，平均分配到各基金）
                    for fund_code in portfolio:
                        if fund_code in fund_data:
                            current_nav = fund_data[fund_code].loc[date, 'nav']
                            units_to_buy = (trade_amount / len(portfolio)) / current_nav
                            fund_units[fund_code] += units_to_buy
                    cash -= trade_amount
            elif signal.action == 'sell':
                # 卖出（简化处理，按比例卖出各基金）
                sell_ratio = min(signal.amount_multiplier, 1.0)
                for fund_code in portfolio:
                    if fund_units[fund_code] > 0:
                        units_to_sell = fund_units[fund_code] * sell_ratio
                        current_nav = fund_data[fund_code].loc[date, 'nav']
                        cash += units_to_sell * current_nav
                        fund_units[fund_code] -= units_to_sell
            
            # 记录当日状态
            total_value = cash + current_holdings_value
            portfolio_values.append(total_value)
            cash_flows.append(trade_amount if signal.action == 'buy' else -trade_amount if signal.action == 'sell' else 0)
            holdings.append(current_holdings_value)
            signals.append(f"{signal.action}: {signal.reason}")
        
        # 构建回测结果DataFrame
        result_df = pd.DataFrame({
            'date': all_dates,
            'portfolio_value': portfolio_values,
            'cash_flow': cash_flows,
            'holdings_value': holdings,
            'signal': signals
        }).set_index('date')
        
        # 计算绩效指标
        metrics = self.calculate_strategy_metrics(result_df)
        
        return result_df, metrics
    
    def calculate_strategy_metrics(self, result_df: pd.DataFrame) -> Dict:
        """
        计算策略绩效指标
        
        参数：
        result_df: 回测结果DataFrame
        
        返回：
        Dict: 绩效指标字典
        """
        if result_df.empty:
            return {}
        
        portfolio_values = result_df['portfolio_value']
        
        # 基本指标
        total_return = (portfolio_values.iloc[-1] - portfolio_values.iloc[0]) / portfolio_values.iloc[0]
        
        # 计算日收益率
        daily_returns = portfolio_values.pct_change().dropna()
        
        # 年化收益率（假设252个交易日）
        annualized_return = (1 + total_return) ** (252 / len(portfolio_values)) - 1
        
        # 年化波动率
        annualized_volatility = daily_returns.std() * np.sqrt(252)
        
        # 最大回撤
        cumulative_returns = (1 + daily_returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()
        
        # 夏普比率（假设无风险利率为3%）
        risk_free_rate = 0.03
        sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility if annualized_volatility > 0 else 0
        
        # 胜率
        win_rate = (daily_returns > 0).mean()
        
        # 平均盈亏比
        positive_returns = daily_returns[daily_returns > 0]
        negative_returns = daily_returns[daily_returns < 0]
        avg_win = positive_returns.mean() if len(positive_returns) > 0 else 0
        avg_loss = abs(negative_returns.mean()) if len(negative_returns) > 0 else 0
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'annualized_volatility': annualized_volatility,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'final_value': portfolio_values.iloc[-1],
            'total_trades': len(result_df[result_df['cash_flow'] != 0])
        }
    
    def run_strategy_comparison(self, top_n: int = 20, rank_type: str = 'daily') -> Dict:
        """
        运行策略对比回测
        
        参数：
        top_n: 获取前N只基金
        rank_type: 排名类型
        
        返回：
        Dict: 包含所有策略结果的字典
        """
        print("=" * 80)
        print("开始基金策略对比回测")
        print(f"回测时间: {self.backtest_start_date} 至 {self.backtest_end_date}")
        print(f"基准金额: {self.base_amount} 元")
        print(f"基金组合大小: {self.portfolio_size}")
        print("=" * 80)
        
        # 1. 获取优质基金组合
        print(f"\n1. 获取前{top_n}只基金...")
        top_funds = self.fund_backtest.get_top_funds(top_n=top_n, rank_type=rank_type)
        
        if top_funds is None or len(top_funds) == 0:
            print("获取基金失败，使用模拟数据")
            # 使用模拟基金代码
            portfolio = [f"Fund_{i:03d}" for i in range(1, self.portfolio_size + 1)]
        else:
            fund_codes = top_funds['基金代码'].tolist()
            portfolio = self.fund_backtest.build_portfolio(fund_codes, method='diversified')
        
        if not portfolio:
            print("构建基金组合失败，使用模拟组合")
            portfolio = [f"Fund_{i:03d}" for i in range(1, self.portfolio_size + 1)]
        
        print(f"基金组合: {portfolio}")
        
        # 2. 准备基金数据
        print(f"\n2. 准备基金历史数据...")
        fund_data = self.prepare_fund_data(portfolio)
        
        # 3. 对每个策略进行回测
        print(f"\n3. 开始策略回测对比...")
        print(f"共{len(self.strategies)}个策略参与对比")
        
        for strategy_name, strategy in self.strategies.items():
            try:
                result_df, metrics = self.backtest_strategy(
                    strategy_name, strategy, portfolio, fund_data
                )
                
                if not result_df.empty:
                    self.strategy_results[strategy_name] = result_df
                    self.strategy_metrics[strategy_name] = metrics
                    
                    print(f"[成功] {strategy_name}: 总收益率 {metrics['total_return']:.2%}, 夏普比率 {metrics['sharpe_ratio']:.2f}")
                else:
                    print(f"[失败] {strategy_name}: 回测失败")

            except Exception as e:
                print(f"[错误] {strategy_name}: 回测出错 - {e}")
        
        # 4. 生成对比报告
        print(f"\n4. 生成策略对比报告...")
        comparison_report = self.generate_comparison_report()
        
        return {
            'portfolio': portfolio,
            'strategy_results': self.strategy_results,
            'strategy_metrics': self.strategy_metrics,
            'comparison_report': comparison_report
        }
    
    def generate_comparison_report(self) -> Dict:
        """
        生成策略对比报告
        
        返回：
        Dict: 对比报告
        """
        if not self.strategy_metrics:
            return {}
        
        # 构建对比表格
        comparison_data = []
        for strategy_name, metrics in self.strategy_metrics.items():
            comparison_data.append({
                '策略名称': strategy_name,
                '策略描述': self.strategies[strategy_name].description,
                '总收益率': f"{metrics['total_return']:.2%}",
                '年化收益率': f"{metrics['annualized_return']:.2%}",
                '年化波动率': f"{metrics['annualized_volatility']:.2%}",
                '最大回撤': f"{metrics['max_drawdown']:.2%}",
                '夏普比率': f"{metrics['sharpe_ratio']:.2f}",
                '胜率': f"{metrics['win_rate']:.2%}",
                '盈亏比': f"{metrics['profit_loss_ratio']:.2f}",
                '交易次数': metrics['total_trades'],
                '最终价值': f"{metrics['final_value']:.2f}"
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        
        # 找出最佳策略
        best_strategy = self.find_best_strategy()
        
        # 生成操作建议
        recommendations = self.generate_recommendations(best_strategy)
        
        return {
            'comparison_table': comparison_df,
            'best_strategy': best_strategy,
            'recommendations': recommendations,
            'strategy_count': len(self.strategy_metrics)
        }
    
    def find_best_strategy(self) -> Dict:
        """
        找出最佳策略
        
        返回：
        Dict: 最佳策略信息
        """
        if not self.strategy_metrics:
            return {}
        
        # 综合评分（可以调整权重）
        strategy_scores = {}
        for strategy_name, metrics in self.strategy_metrics.items():
            # 评分标准：夏普比率40% + 总收益率30% + 最大回撤20% + 胜率10%
            sharpe_score = min(metrics['sharpe_ratio'] / 2.0, 1.0) * 0.4  # 夏普比率2.0为满分
            return_score = min(max(metrics['total_return'], 0) / 0.5, 1.0) * 0.3  # 50%收益为满分
            drawdown_score = (1 - min(abs(metrics['max_drawdown']), 0.5) / 0.5) * 0.2  # 回撤50%为0分
            winrate_score = metrics['win_rate'] * 0.1
            
            total_score = sharpe_score + return_score + drawdown_score + winrate_score
            strategy_scores[strategy_name] = total_score
        
        best_strategy_name = max(strategy_scores, key=strategy_scores.get)
        
        return {
            'name': best_strategy_name,
            'description': self.strategies[best_strategy_name].description,
            'score': strategy_scores[best_strategy_name],
            'metrics': self.strategy_metrics[best_strategy_name]
        }
    
    def generate_recommendations(self, best_strategy: Dict) -> List[str]:
        """
        生成操作建议
        
        参数：
        best_strategy: 最佳策略信息
        
        返回：
        List[str]: 操作建议列表
        """
        if not best_strategy:
            return ["无法生成操作建议：缺少有效的策略数据"]
        
        recommendations = []
        strategy_name = best_strategy['name']
        metrics = best_strategy['metrics']
        
        # 基于策略类型的建议
        if 'dual_ma' in strategy_name:
            recommendations.append(f"推荐使用双均线动量策略：当前市场趋势性较强，适合趋势跟踪")
            recommendations.append(f"建议关注20日和60日均线交叉信号，金叉时加仓，死叉时减仓")
        elif 'mean_reversion' in strategy_name:
            recommendations.append(f"推荐使用均值回归策略：市场震荡特征明显，适合低买高卖")
            recommendations.append(f"建议在价格偏离250日均线5%以上时进行反向操作")
        elif 'target_value' in strategy_name:
            recommendations.append(f"推荐使用目标市值策略：适合稳健投资，定期平衡资产配置")
            recommendations.append(f"建议每月设定目标资产增长额，动态调整投资金额")
        elif 'grid' in strategy_name:
            recommendations.append(f"推荐使用网格交易策略：市场波动率适中，适合区间操作")
            recommendations.append(f"建议设置3%的网格间距，下跌买入，上涨卖出")
        
        # 基于绩效指标的建议
        if metrics['sharpe_ratio'] > 1.5:
            recommendations.append(f"该策略夏普比率为{metrics['sharpe_ratio']:.2f}，风险调整收益优秀")
        elif metrics['sharpe_ratio'] < 0.5:
            recommendations.append(f"该策略夏普比率较低({metrics['sharpe_ratio']:.2f})，建议谨慎使用或结合其他策略")
        
        if metrics['max_drawdown'] < -0.1:
            recommendations.append(f"注意：该策略最大回撤为{metrics['max_drawdown']:.2%}，建议控制仓位")
        
        if metrics['win_rate'] > 0.6:
            recommendations.append(f"该策略胜率较高({metrics['win_rate']:.2%})，适合严格执行")
        
        # 风险提示
        recommendations.append("风险提示：过往业绩不代表未来表现，请根据个人风险承受能力选择")
        recommendations.append("建议：可结合多种策略使用，分散投资风险")
        
        return recommendations
    
    def plot_strategy_comparison(self, output_dir: str = '.'):
        """
        绘制策略对比图表
        
        参数：
        output_dir: 输出目录
        """
        if not self.strategy_results:
            return
            
        # 设置绘图风格
        try:
            plt.style.use('seaborn-v0_8')
        except:
            sns.set()
            
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        try:
            # 1. 策略净值走势对比
            plt.figure(figsize=(12, 8))
            
            for strategy_name, df in self.strategy_results.items():
                # 计算累计收益率（归一化）
                if 'portfolio_value' in df.columns:
                    initial_value = df['portfolio_value'].iloc[0]
                    normalized_value = df['portfolio_value'] / initial_value
                    plt.plot(df.index, normalized_value, label=strategy_name, linewidth=2)
            
            plt.title('基金策略绩效走势对比', fontsize=16)
            plt.xlabel('日期', fontsize=12)
            plt.ylabel('净值 (起始=1.0)', fontsize=12)
            plt.legend(loc='best')
            plt.grid(True, alpha=0.3)
            
            # 保存图表
            chart_path = os.path.join(output_dir, 'strategy_performance_comparison.png')
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"图表已保存: {chart_path}")
            
            # 2. 关键指标对比 (柱状图)
            if self.strategy_metrics:
                metrics_df = pd.DataFrame(self.strategy_metrics).T
                
                # 选择关键指标
                key_metrics = ['annualized_return', 'max_drawdown', 'sharpe_ratio']
                metric_names = ['年化收益率', '最大回撤', '夏普比率']
                
                fig, axes = plt.subplots(1, 3, figsize=(18, 6))
                
                for i, (metric, name) in enumerate(zip(key_metrics, metric_names)):
                    if metric in metrics_df.columns:
                        ax = axes[i]
                        values = metrics_df[metric]
                        colors = ['#d62728' if v < 0 else '#1f77b4' for v in values] # Red for negative, Blue for positive
                        
                        bars = ax.bar(metrics_df.index, values, color=colors, alpha=0.7)
                        ax.set_title(name, fontsize=14)
                        ax.tick_params(axis='x', rotation=45)
                        ax.grid(axis='y', alpha=0.3)
                        
                        # Add labels
                        for bar in bars:
                            height = bar.get_height()
                            # 避免文字重叠
                            y_pos = height + (0.01 if height >= 0 else -0.05)
                            ax.text(bar.get_x() + bar.get_width()/2., y_pos,
                                    f'{height:.2%}' if metric != 'sharpe_ratio' else f'{height:.2f}',
                                    ha='center', va='bottom' if height >= 0 else 'top', fontsize=9)
                                
                plt.tight_layout()
                metrics_chart_path = os.path.join(output_dir, 'strategy_metrics_comparison.png')
                plt.savefig(metrics_chart_path, dpi=300, bbox_inches='tight')
                plt.close()
                print(f"指标对比图已保存: {metrics_chart_path}")
                
        except Exception as e:
            print(f"绘制图表时出错: {e}")

    def save_results(self, output_dir: str = '.') -> Dict:
        """
        保存回测结果
        
        参数：
        output_dir: 输出目录
        
        返回：
        Dict: 保存的文件路径
        """
        saved_files = {}
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # 保存策略对比表
            if hasattr(self, 'comparison_report') and self.comparison_report and 'comparison_table' in self.comparison_report:
                comparison_file = os.path.join(output_dir, "strategy_comparison.csv")
                self.comparison_report['comparison_table'].to_csv(comparison_file, index=False, encoding='utf-8-sig')
                saved_files['comparison'] = comparison_file
            
            # 保存各策略详细结果
            for strategy_name, result_df in self.strategy_results.items():
                strategy_file = os.path.join(output_dir, f"strategy_{strategy_name}_result.csv")
                result_df.to_csv(strategy_file, encoding='utf-8-sig')
                saved_files[f'strategy_{strategy_name}'] = strategy_file
            
            # 保存绩效指标
            if self.strategy_metrics:
                metrics_df = pd.DataFrame(self.strategy_metrics).T
                metrics_file = os.path.join(output_dir, "strategy_metrics.csv")
                metrics_df.to_csv(metrics_file, encoding='utf-8-sig')
                saved_files['metrics'] = metrics_file
                
            # 生成并保存图表
            self.plot_strategy_comparison(output_dir)
            
            print(f"结果已保存到 {output_dir} 目录")
            
        except Exception as e:
            print(f"保存结果时出错: {e}")
        
        return saved_files

# 主程序示例
if __name__ == "__main__":
    # 创建策略对比引擎
    engine = StrategyComparisonEngine(
        backtest_start_date='2024-01-01',
        backtest_end_date='2024-12-31',
        base_amount=1000,
        portfolio_size=6
    )
    
    # 运行策略对比
    results = engine.run_strategy_comparison(top_n=15, rank_type='daily')
    
    # 显示结果
    if 'comparison_report' in results:
        print("\n" + "=" * 80)
        print("策略对比结果")
        print("=" * 80)
        
        comparison_df = results['comparison_report']['comparison_table']
        print(comparison_df.to_string(index=False))
        
        print(f"\n最佳策略: {results['comparison_report']['best_strategy']['name']}")
        print(f"综合评分: {results['comparison_report']['best_strategy']['score']:.3f}")
        
        print("\n操作建议:")
        for i, rec in enumerate(results['comparison_report']['recommendations'], 1):
            print(f"{i}. {rec}")
    
    # 保存结果
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
    saved_files = engine.save_results(output_dir=output_dir)
    print(f"\n已保存文件: {list(saved_files.keys())}")