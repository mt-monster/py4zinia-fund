#!/usr/bin/env python
# coding: utf-8

"""
基金组合回测模块

该模块整合了基金筛选、相似性分析和回测引擎，实现了从获取每日加仓前二十基金到回测分析的完整流程。
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 导入自定义模块
from fund_top_picker import FundTopPicker
from fund_similarity import FundSimilarityAnalyzer
from backtest_engine import FundBacktest

class TopFundsBacktest:
    """
    每日加仓前二十基金组合回测类
    
    该类整合了基金筛选、相似性分析和回测引擎，实现了从获取每日加仓前二十基金到回测分析的完整流程。
    """
    
    def __init__(self, 
                 backtest_start_date=None, 
                 backtest_end_date=None,
                 lookback_days=180,
                 base_amount=100,
                 portfolio_size=10,
                 n_clusters=5,
                 correlation_threshold=0.5):
        """
        初始化每日加仓前二十基金组合回测类
        
        参数：
        backtest_start_date: str, 回测开始日期，格式为'YYYY-MM-DD'
        backtest_end_date: str, 回测结束日期，格式为'YYYY-MM-DD'
        lookback_days: int, 相似性分析的回溯天数，默认为180天
        base_amount: float, 基准定投金额，默认为100元
        portfolio_size: int, 组合中基金数量，默认为10
        n_clusters: int, 聚类数量，默认为5
        correlation_threshold: float, 相关性阈值，默认为0.5
        """
        # 回测日期设置
        self.backtest_start_date = backtest_start_date
        self.backtest_end_date = backtest_end_date if backtest_end_date else datetime.now().strftime('%Y-%m-%d')
        
        # 相似性分析参数
        self.lookback_days = lookback_days
        self.n_clusters = n_clusters
        self.correlation_threshold = correlation_threshold
        
        # 回测参数
        self.base_amount = base_amount
        self.portfolio_size = portfolio_size
        
        # 初始化各个模块
        self.picker = FundTopPicker()
        self.similarity_analyzer = FundSimilarityAnalyzer(
            lookback_days=lookback_days
        )
        self.backtester = FundBacktest(
            base_amount=base_amount,
            start_date=backtest_start_date,
            end_date=backtest_end_date
        )
    
    def get_top_funds(self, top_n=20, rank_type='daily'):
        """
        获取排名前top_n的基金
        
        参数：
        top_n: int, 要获取的基金数量，默认为20
        rank_type: str, 排名类型，可选值为'daily'、'weekly'、'monthly'，默认为'daily'
        
        返回：
        pandas.DataFrame, 排名前top_n的基金数据
        """
        try:
            if rank_type == 'daily':
                top_funds = self.picker.get_top_funds_by_daily_return(top_n=top_n)
            elif rank_type == 'weekly':
                top_funds = self.picker.get_top_funds_by_weekly_return(top_n=top_n)
            elif rank_type == 'monthly':
                top_funds = self.picker.get_top_funds_by_monthly_return(top_n=top_n)
            else:
                print(f"不支持的排名类型: {rank_type}")
                return None
            
            return top_funds
        except Exception as e:
            print(f"获取排名前{top_n}的基金时出错: {e}")
            return None
    
    def build_portfolio(self, fund_codes, method='diversified'):
        """
        构建基金组合
        
        参数：
        fund_codes: list, 基金代码列表
        method: str, 组合构建方法，可选值为'diversified'、'low_corr'，默认为'diversified'
        
        返回：
        list, 构建好的基金组合
        """
        try:
            if method == 'diversified':
                # 构建多样化组合
                portfolio = self.similarity_analyzer.build_diversified_portfolio(
                    fund_codes,
                    n_clusters=self.n_clusters,
                    portfolio_size=self.portfolio_size
                )
            elif method == 'low_corr':
                # 构建低相关性组合
                portfolio = self.similarity_analyzer.select_low_correlation_funds(
                    fund_codes,
                    portfolio_size=self.portfolio_size,
                    correlation_threshold=self.correlation_threshold
                )
            else:
                print(f"不支持的组合构建方法: {method}")
                return []
            
            return portfolio
        except Exception as e:
            print(f"构建基金组合时出错: {e}")
            return []
    
    def run_backtest(self, portfolio, weights=None):
        """
        运行基金组合回测
        
        参数：
        portfolio: list, 基金组合
        weights: list, 基金权重，默认为等权重
        
        返回：
        pandas.DataFrame, 回测结果
        """
        try:
            # 检查组合是否为空
            if not portfolio:
                print("基金组合为空，无法进行回测")
                return None
            
            # 运行回测
            result = self.backtester.backtest_portfolio(portfolio, weights=weights)
            
            return result
        except Exception as e:
            print(f"运行回测时出错: {e}")
            return None
    
    def analyze_performance(self, result):
        """
        分析回测绩效
        
        参数：
        result: pandas.DataFrame, 回测结果
        
        返回：
        dict, 绩效指标
        """
        try:
            if result is None or result.empty:
                print("回测结果为空，无法进行绩效分析")
                return None
            
            # 计算绩效指标
            metrics = self.backtester.calculate_performance_metrics(result)
            
            return metrics
        except Exception as e:
            print(f"分析绩效时出错: {e}")
            return None
    
    def visualize_results(self, result, portfolio):
        """
        可视化回测结果
        
        参数：
        result: pandas.DataFrame, 回测结果
        portfolio: list, 基金组合
        """
        try:
            if result is None or result.empty:
                print("回测结果为空，无法进行可视化")
                return
            
            # 可视化回测结果
            self.backtester.visualize_portfolio(result)
        except Exception as e:
            print(f"可视化回测结果时出错: {e}")
    
    def run_full_backtest_flow(self, top_n=20, rank_type='daily', portfolio_method='diversified', weights=None):
        """
        运行完整的回测流程
        
        参数：
        top_n: int, 要获取的基金数量，默认为20
        rank_type: str, 排名类型，可选值为'daily'、'weekly'、'monthly'，默认为'daily'
        portfolio_method: str, 组合构建方法，可选值为'diversified'、'low_corr'，默认为'diversified'
        weights: list, 基金权重，默认为等权重
        
        返回：
        tuple, 包含回测结果、绩效指标和基金组合
        """
        print("=" * 80)
        print("开始运行完整回测流程")
        print(f"回测时间范围: {self.backtest_start_date} 至 {self.backtest_end_date}")
        print(f"基准定投金额: {self.base_amount} 元")
        print(f"排名类型: {rank_type}，获取前 {top_n} 只基金")
        print(f"组合构建方法: {portfolio_method}，组合大小: {self.portfolio_size}")
        print("=" * 80)
        
        # 1. 获取排名前top_n的基金
        print(f"\n1. 获取{rank_type}排名前{top_n}的基金...")
        top_funds = self.get_top_funds(top_n=top_n, rank_type=rank_type)
        
        if top_funds is None:
            print("获取排名前20的基金失败")
            return None, None, None
        
        print(f"成功获取到{len(top_funds)}只基金")
        print("前10只基金:")
        print(top_funds[['基金代码', '基金简称', '日增长率']].head(10))
        
        # 2. 提取基金代码
        fund_codes = top_funds['基金代码'].tolist()
        
        # 3. 构建基金组合
        print(f"\n2. 构建{portfolio_method}基金组合...")
        portfolio = self.build_portfolio(fund_codes, method=portfolio_method)
        
        if not portfolio:
            print("构建基金组合失败")
            return None, None, None
        
        print(f"成功构建包含{len(portfolio)}只基金的组合:")
        print(portfolio)
        
        # 4. 运行回测
        print(f"\n3. 运行基金组合回测...")
        result = self.run_backtest(portfolio, weights=weights)
        
        if result is None:
            print("运行回测失败")
            return None, None, None
        
        print(f"成功完成回测，共{len(result)}个交易日数据")
        
        # 5. 分析绩效
        print(f"\n4. 分析回测绩效...")
        metrics = self.analyze_performance(result)
        
        if metrics:
            print("绩效指标:")
            print(f"总收益率(策略): {metrics['总收益率_strategy']:.2%}")
            print(f"总收益率(基准): {metrics['总收益率_benchmark']:.2%}")
            print(f"年化收益率(策略): {metrics['年化收益率_strategy']:.2%}")
            print(f"年化收益率(基准): {metrics['年化收益率_benchmark']:.2%}")
            print(f"最大回撤(策略): {metrics['最大回撤_strategy']:.2%}")
            print(f"最大回撤(基准): {metrics['最大回撤_benchmark']:.2%}")
            print(f"夏普比率(策略): {metrics['夏普比率_strategy']:.2f}")
            print(f"夏普比率(基准): {metrics['夏普比率_benchmark']:.2f}")
        
        # 6. 可视化结果
        print(f"\n5. 可视化回测结果...")
        self.visualize_results(result, portfolio)
        
        print("\n" + "=" * 80)
        print("完整回测流程结束")
        print("=" * 80)
        
        return result, metrics, portfolio

# 示例用法
if __name__ == "__main__":
    # 创建回测实例
    backtest = TopFundsBacktest(
        backtest_start_date='2024-01-01',
        backtest_end_date='2025-12-31',
        lookback_days=180,
        base_amount=100,
        portfolio_size=8,
        n_clusters=4,
        correlation_threshold=0.5
    )
    
    # 运行完整回测流程
    result, metrics, portfolio = backtest.run_full_backtest_flow(
        top_n=20,
        rank_type='daily',
        portfolio_method='diversified'
    )
    
    # 保存回测结果
    if result is not None:
        result.to_csv('top_funds_backtest_result.csv', index=False)
        print(f"回测结果已保存到top_funds_backtest_result.csv")
    
    # 保存绩效指标
    if metrics:
        metrics_df = pd.DataFrame([metrics])
        metrics_df.to_csv('top_funds_performance_metrics.csv', index=False)
        print(f"绩效指标已保存到top_funds_performance_metrics.csv")
    
    # 保存基金组合
    if portfolio:
        portfolio_df = pd.DataFrame({'fund_code': portfolio})
        portfolio_df.to_csv('top_funds_portfolio.csv', index=False)
        print(f"基金组合已保存到top_funds_portfolio.csv")
