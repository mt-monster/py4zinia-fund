#!/usr/bin/env python
# coding: utf-8

"""
回测脚本：使用search_01.py的投资策略和backtest_engine.py的回测引擎
评估操作建议后总持仓的绩效表现
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 添加项目路径
project_path = "d:/codes/py4zinia"
sys.path.append(project_path)

# 导入所需模块
from fund_search.search_01 import get_investment_strategy
from fund_search.backtest_engine import FundBacktest

class StrategyBacktest:
    """使用search_01.py的投资策略进行回测的类"""
    
    def __init__(self, base_amount=100, start_date='2020-01-01', end_date=None):
        """
        初始化回测类
        
        参数：
        base_amount: 基准定投金额
        start_date: 回测开始日期
        end_date: 回测结束日期
        """
        self.base_amount = base_amount
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')
        
        # 创建回测引擎实例
        self.backtest = FundBacktest(
            base_amount=base_amount,
            start_date=start_date,
            end_date=end_date
        )
        
    def run_single_fund_backtest(self, fund_code):
        """
        回测单只基金使用search_01.py策略的绩效
        
        参数：
        fund_code: 基金代码
        
        返回：
        result_df: 回测结果DataFrame
        metrics: 绩效指标
        """
        print(f"\n开始回测基金 {fund_code}...")
        
        # 获取基金历史数据
        fund_hist = self.backtest.get_fund_history(fund_code)
        if fund_hist is None or len(fund_hist) < 2:
            print(f"基金 {fund_code} 数据不足，无法进行回测")
            return None, None
        
        # 初始化回测变量
        cash = self.base_amount  # 初始现金
        shares = 0  # 初始份额
        total_asset = []  # 总资产记录
        benchmark_asset = []  # 基准策略总资产记录
        benchmark_shares = 0  # 基准策略份额
        benchmark_cash = self.base_amount  # 基准策略现金
        
        print(f"开始日期: {self.start_date}")
        print(f"结束日期: {self.end_date}")
        print(f"基准定投金额: {self.base_amount}元")
        print(f"总交易天数: {len(fund_hist) - 1}")
        
        # 模拟每日交易
        for i in range(1, len(fund_hist)):
            today = fund_hist.iloc[i]
            yesterday = fund_hist.iloc[i-1]
            
            today_nav = today['单位净值']
            today_return = today['日增长率'] * 100  # 转换为百分比
            prev_day_return = yesterday['日增长率'] * 100  # 转换为百分比
            
            # 获取search_01.py的投资策略建议
            status_label, is_buy, redeem_amount, _, operation_suggestion, execution_amount, buy_multiplier = get_investment_strategy(today_return, prev_day_return)
            
            # 执行买入操作
            if is_buy:
                # 根据buy_multiplier计算买入金额
                buy_amount = self.base_amount * buy_multiplier
                if cash >= buy_amount or i == 1:  # 第一天允许现金不足
                    buy_shares = buy_amount / today_nav
                    shares += buy_shares
                    cash -= buy_amount
                    # print(f"{today['净值日期'].date()}: 买入 {buy_amount:.2f}元 ({buy_shares:.4f}份), 现金剩余 {cash:.2f}元")
            
            # 执行赎回操作
            if redeem_amount > 0 and shares > 0:
                redeem_shares = redeem_amount / today_nav
                shares = max(0, shares - redeem_shares)
                cash += redeem_amount
                # print(f"{today['净值日期'].date()}: 赎回 {redeem_amount:.2f}元 ({redeem_shares:.4f}份), 现金剩余 {cash:.2f}元")
            
            # 计算总资产
            current_asset = cash + shares * today_nav
            total_asset.append({
                'date': today['净值日期'],
                'total_value_strategy': current_asset,
                'cash': cash,
                'shares': shares,
                'nav': today_nav,
                'strategy': status_label
            })
            
            # 基准策略：固定金额定投
            benchmark_buy_amount = self.base_amount
            if benchmark_cash >= benchmark_buy_amount or i == 1:
                benchmark_buy_shares = benchmark_buy_amount / today_nav
                benchmark_shares += benchmark_buy_shares
                benchmark_cash -= benchmark_buy_amount
            benchmark_current_asset = benchmark_cash + benchmark_shares * today_nav
            benchmark_asset.append({
                'date': today['净值日期'],
                'total_value_benchmark': benchmark_current_asset
            })
        
        # 转换为DataFrame
        result_df = pd.DataFrame(total_asset)
        benchmark_df = pd.DataFrame(benchmark_asset)
        
        # 合并结果
        result_df = result_df.merge(benchmark_df, on='date')
        
        # 计算每日收益率
        result_df['daily_return_strategy'] = result_df['total_value_strategy'].pct_change().fillna(0)
        result_df['daily_return_benchmark'] = result_df['total_value_benchmark'].pct_change().fillna(0)
        
        # 计算绩效指标
        metrics = self.backtest.calculate_performance_metrics(result_df)
        
        print(f"回测完成！")
        return result_df, metrics
    
    def run_portfolio_backtest(self, fund_codes, weights=None):
        """
        回测基金组合使用search_01.py策略的绩效
        
        参数：
        fund_codes: 基金代码列表
        weights: 基金权重列表
        
        返回：
        portfolio_result: 组合回测结果DataFrame
        portfolio_metrics: 组合绩效指标
        """
        print(f"\n开始回测基金组合: {fund_codes}")
        
        if weights is None:
            weights = [1/len(fund_codes)] * len(fund_codes)
        
        if len(fund_codes) != len(weights):
            print("基金代码数量与权重数量不匹配")
            return None, None
        
        # 确保权重和为1
        weights = np.array(weights) / np.sum(weights)
        
        # 回测每只基金
        fund_results = {}
        for fund_code in fund_codes:
            result_df, metrics = self.run_single_fund_backtest(fund_code)
            if result_df is not None:
                fund_results[fund_code] = result_df
        
        if not fund_results:
            print("没有基金数据可以进行组合回测")
            return None, None
        
        # 合并所有基金的结果
        dates = None
        portfolio_asset = []
        benchmark_asset = []
        
        for i, (fund_code, result_df) in enumerate(fund_results.items()):
            if i == 0:
                dates = result_df['date']
                portfolio_asset = result_df['total_value_strategy'].values * weights[i]
                benchmark_asset = result_df['total_value_benchmark'].values * weights[i]
            else:
                # 对齐日期
                aligned_df = result_df.set_index('date').reindex(dates).reset_index()
                portfolio_asset += aligned_df['total_value_strategy'].fillna(0).values * weights[i]
                benchmark_asset += aligned_df['total_value_benchmark'].fillna(0).values * weights[i]
        
        # 创建组合结果DataFrame
        portfolio_result = pd.DataFrame({
            'date': dates,
            'total_value_strategy': portfolio_asset,
            'total_value_benchmark': benchmark_asset
        })
        
        # 计算每日收益率
        portfolio_result['daily_return_strategy'] = portfolio_result['total_value_strategy'].pct_change().fillna(0)
        portfolio_result['daily_return_benchmark'] = portfolio_result['total_value_benchmark'].pct_change().fillna(0)
        
        # 计算组合绩效指标
        portfolio_metrics = self.backtest.calculate_performance_metrics(portfolio_result)
        
        print(f"\n基金组合回测完成！")
        return portfolio_result, portfolio_metrics
    
    def print_metrics(self, metrics, title="绩效指标"):
        """打印绩效指标"""
        if metrics is None:
            return

        print('\n' + '='*80)
        print(title)
        print('总收益率_strategy: {:.4%}'.format(metrics['总收益率_strategy']))
        print('总收益率_benchmark: {:.4%}'.format(metrics['总收益率_benchmark']))
        print('年化收益率_strategy: {:.4%}'.format(metrics['年化收益率_strategy']))
        print('年化收益率_benchmark: {:.4%}'.format(metrics['年化收益率_benchmark']))
        print('最大回撤_strategy: {:.4%}'.format(metrics['最大回撤_strategy']))
        print('最大回撤_benchmark: {:.4%}'.format(metrics['最大回撤_benchmark']))
        print('夏普比率_strategy: {:.4f}'.format(metrics['夏普比率_strategy']))
        print('夏普比率_benchmark: {:.4f}'.format(metrics['夏普比率_benchmark']))
        print('胜率_strategy: {:.4%}'.format(metrics['胜率_strategy']))
        print('胜率_benchmark: {:.4%}'.format(metrics['胜率_benchmark']))
        print('年化波动率_strategy: {:.4%}'.format(metrics['年化波动率_strategy']))
        print('年化波动率_benchmark: {:.4%}'.format(metrics['年化波动率_benchmark']))
        print('Alpha_strategy: {:.4f}'.format(metrics['Alpha_strategy']))
        print('Beta_strategy: {:.4f}'.format(metrics['Beta_strategy']))
        print('索提诺比率_strategy: {:.4f}'.format(metrics['索提诺比率_strategy']))
        print('索提诺比率_benchmark: {:.4f}'.format(metrics['索提诺比率_benchmark']))
        print('卡玛比率_strategy: {:.4f}'.format(metrics['卡玛比率_strategy']))
        print('卡玛比率_benchmark: {:.4f}'.format(metrics['卡玛比率_benchmark']))
        print('='*80)

    def visualize_backtest(self, result_df, fund_code=None):
        """可视化回测结果"""
        if result_df is None or result_df.empty:
            print("没有数据可以可视化")
            return

        # 调用backtest_engine的可视化方法
        self.backtest.visualize_backtest(result_df, fund_code)

if __name__ == "__main__":
    # 示例用法
    # 读取Excel文件中的基金代码
    import pandas as pd
    file_path = "d:/codes/py4zinia/京东金融.xlsx"
    position_data = pd.read_excel(file_path, sheet_name='持仓数据')
    
    # 获取持仓数据中的基金代码
    fund_codes = position_data['代码'].astype(str).tolist()
    
    # 过滤掉"汇总"和空字符串
    fund_codes = [code for code in fund_codes if code != "汇总" and code.strip() != ""]
    
    # 初始化回测
    backtest = StrategyBacktest(base_amount=100, start_date='2023-01-01', end_date='2024-12-31')
    
    # 运行组合回测
    portfolio_result, portfolio_metrics = backtest.run_portfolio_backtest(fund_codes)
    
    if portfolio_result is not None:
        # 打印绩效指标
        backtest.print_metrics(portfolio_metrics, title="基金组合回测结果")
        
        # 可视化结果
        backtest.visualize_backtest(portfolio_result)