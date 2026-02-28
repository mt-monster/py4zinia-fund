#!/usr/bin/env python
# coding: utf-8

"""
基金回测引擎

该模块实现了一个完整的基金回测框架，支持单基金和基金组合的定投策略回测。
核心功能包括：
1. 从akshare获取基金历史数据
2. 实现基于search_01.py的投资策略（已升级为统一策略引擎）
3. 单基金定投回测
4. 基金组合定投回测
5. 全面的绩效指标计算
6. 可视化回测结果

使用说明：
- 创建FundBacktest实例，配置回测参数
- 调用backtest_single_fund或backtest_portfolio方法执行回测
- 调用calculate_performance_metrics计算绩效指标
- 调用visualize_backtest或visualize_portfolio可视化结果

更新日志：
- 2026-01-16: 集成统一策略引擎，支持止损、趋势分析、动态仓位管理
"""

# 导入必要的库
import pandas as pd  # 用于数据处理和分析
import numpy as np   # 用于数值计算
import matplotlib.pyplot as plt  # 用于数据可视化
import akshare as ak  # 用于获取金融数据
import datetime       # 用于日期处理
from services.fund_realtime import FundRealTime  # 导入实时基金数据模块

# 导入统一策略引擎适配器
try:
    from ..strategies.strategy_adapter import StrategyAdapter
    UNIFIED_STRATEGY_AVAILABLE = True
except ImportError:
    UNIFIED_STRATEGY_AVAILABLE = False

class FundBacktest:
    """
    基金回测核心类
    
    该类封装了基金回测的完整流程，包括数据获取、策略执行、绩效计算和可视化。
    支持单基金和基金组合的回测，可自定义回测时间范围、基准定投金额等参数。
    """
    
    def __init__(self, base_amount=100, start_date='2020-01-01', end_date=None, initial_cash=None, use_unified_strategy=True):
        """
        初始化回测引擎
        
        参数：
        base_amount: float, 基准定投金额（单位：元），默认为100元
        start_date: str, 回测开始日期，格式为'YYYY-MM-DD'，默认为'2020-01-01'
        end_date: str, 回测结束日期，格式为'YYYY-MM-DD'，默认为当前日期
        initial_cash: float, 初始现金，默认为base_amount
        use_unified_strategy: bool, 是否使用统一策略引擎，默认为True
        """
        self.base_amount = base_amount  # 基准定投金额
        self.start_date = start_date  # 回测开始日期
        # 如果未指定结束日期，则使用当前日期
        self.end_date = end_date if end_date else datetime.datetime.now().strftime('%Y-%m-%d')
        # 如果未指定初始现金，则使用基准定投金额
        self.initial_cash = initial_cash if initial_cash is not None else base_amount
        
        # 初始化统一策略引擎适配器
        self.use_unified_strategy = use_unified_strategy and UNIFIED_STRATEGY_AVAILABLE
        self._strategy_adapter = None
        if self.use_unified_strategy:
            self._strategy_adapter = StrategyAdapter(base_amount=base_amount)
        
    def get_fund_history(self, fund_code):
        """
        从akshare获取基金历史数据
        
        参数：
        fund_code: str, 基金代码
        
        返回：
        pandas.DataFrame, 基金历史数据，包含日期、单位净值、日增长率等字段
        如果获取失败或数据为空，返回None
        """
        try:
            # 从akshare获取基金单位净值走势数据
            fund_hist = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            
            # 检查数据是否为空
            if fund_hist.empty:
                print(f"基金 {fund_code} 没有获取到历史数据")
                return None
            
            # 将日期字符串转换为datetime类型
            fund_hist['净值日期'] = pd.to_datetime(fund_hist['净值日期'])
            
            # 过滤指定日期范围内的数据
            fund_hist = fund_hist[(fund_hist['净值日期'] >= self.start_date) & (fund_hist['净值日期'] <= self.end_date)]
            
            # 转换数据类型，确保数值型字段正确
            fund_hist['单位净值'] = pd.to_numeric(fund_hist['单位净值'], errors='coerce')
            # 将日增长率从百分比字符串转换为小数
            fund_hist['日增长率'] = pd.to_numeric(fund_hist['日增长率'].astype(str).str.rstrip('%'), errors='coerce') / 100
            
            # 重置索引，确保索引连续
            fund_hist = fund_hist.reset_index(drop=True)
            
            return fund_hist
        except Exception as e:
            # 捕获并打印异常信息
            print(f"获取基金 {fund_code} 历史数据时出错: {e}")
            return None
    
    def get_hs300_history(self):
        """
        从akshare获取沪深300指数历史数据
        
        返回：
        pandas.DataFrame, 沪深300指数历史数据，包含日期、收盘价、日增长率等字段
        如果获取失败或数据为空，返回None
        """
        try:
            # 从akshare获取沪深300指数历史数据
            # 沪深300指数代码为 "000300"，使用股票指数数据接口
            hs300_hist = ak.stock_zh_index_daily(symbol="sh000300")
            
            # 检查数据是否为空
            if hs300_hist.empty:
                print("沪深300指数没有获取到历史数据")
                return None
            
            # 将日期字符串转换为datetime类型
            hs300_hist['date'] = pd.to_datetime(hs300_hist['date'])
            
            # 过滤指定日期范围内的数据
            hs300_hist = hs300_hist[(hs300_hist['date'] >= self.start_date) & (hs300_hist['date'] <= self.end_date)]
            
            # 计算日增长率（基于收盘价）
            hs300_hist['pct_change'] = hs300_hist['close'].pct_change().fillna(0)
            
            # 重置索引，确保索引连续
            hs300_hist = hs300_hist.reset_index(drop=True)
            
            return hs300_hist
        except Exception as e:
            # 捕获并打印异常信息
            print(f"获取沪深300指数历史数据时出错: {e}")
            return None
    
    def get_investment_strategy(self, today_return, prev_day_return):
        """
        获取投资策略建议
        
        基于今日和昨日收益率，生成定投策略建议，包括是否买入、买入金额、
        赎回金额等。
        
        如果启用了统一策略引擎（use_unified_strategy=True），将使用增强版策略，
        包含止损管理、趋势分析和动态仓位调整功能。
        否则使用原始的基础策略逻辑。
        
        参数：
        today_return: float, 当日收益率（小数形式，如0.01表示1%）
        prev_day_return: float, 前一日收益率（小数形式）
        
        返回：
        tuple: 包含7个元素
            status_label: str, 策略状态标签（如"反转涨"、"持续跌增强"等）
            is_buy: bool, 是否买入标志
            redeem_amount: float, 赎回金额
            comparison_value: float, 用于策略决策的比较值
            operation_suggestion: str, 操作建议文本
            execution_amount: float, 执行金额（正为买入，负为赎回）
            buy_multiplier: float, 买入乘数（基准金额的倍数）
        """
        # 如果启用了统一策略引擎，使用适配器
        if self.use_unified_strategy and self._strategy_adapter is not None:
            return self._strategy_adapter.get_investment_strategy(today_return, prev_day_return)
        
        # 否则使用原始策略逻辑（向后兼容）
        return self._get_legacy_strategy(today_return, prev_day_return)
    
    def _get_legacy_strategy(self, today_return, prev_day_return):
        """
        原始投资策略逻辑（向后兼容）
        
        基于今日和昨日收益率，生成定投策略建议。
        该策略复制自search_01.py中的逻辑。
        
        参数：
        today_return: float, 当日收益率（小数形式，如0.01表示1%）
        prev_day_return: float, 前一日收益率（小数形式）
        
        返回：
        tuple: 包含7个元素
        """
        # 初始化策略返回值
        status_label = ""          # 策略状态标签
        is_buy = False             # 是否买入标志
        redeem_amount = 0          # 赎回金额
        comparison_value = 0       # 比较值
        operation_suggestion = ""  # 操作建议
        execution_amount = 0       # 执行金额
        buy_multiplier = 1.0       # 买入乘数
        
        # 计算今日与昨日的收益率差值
        return_diff = today_return - prev_day_return
        
        # 根据不同的收益率情况，制定不同的投资策略
        if today_return > 0 and prev_day_return <= 0:
            # 今日上涨，昨日下跌或持平：反转上涨
            status_label = "反转涨"
            is_buy = True
            buy_multiplier = 1.5  # 增加定投金额
            comparison_value = today_return
            operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
            execution_amount = self.base_amount * buy_multiplier
        elif today_return <= 0 and prev_day_return > 0:
            # 今日下跌或持平，昨日上涨：反转下跌
            status_label = "反转跌"
            is_buy = False
            redeem_amount = 30  # 赎回固定金额
            comparison_value = today_return
            operation_suggestion = f"赎回 {redeem_amount} 元"
            execution_amount = -redeem_amount
        elif today_return > 0 and prev_day_return > 0:
            # 今日和昨日均上涨
            if return_diff > 0:
                # 上涨加速：持续涨增强
                status_label = "持续涨增强"
                is_buy = True
                buy_multiplier = 1.2
                comparison_value = return_diff
                operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
                execution_amount = self.base_amount * buy_multiplier
            else:
                # 上涨减速：持续涨减弱
                status_label = "持续涨减弱"
                is_buy = True
                buy_multiplier = 1.0
                comparison_value = return_diff
                operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
                execution_amount = self.base_amount * buy_multiplier
        elif today_return < 0 and prev_day_return < 0:
            # 今日和昨日均下跌
            if return_diff > 0:
                # 下跌减速：持续跌减弱
                status_label = "持续跌减弱"
                is_buy = True
                buy_multiplier = 1.5
                comparison_value = return_diff
                operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
                execution_amount = self.base_amount * buy_multiplier
            else:
                # 下跌加速：持续跌增强
                status_label = "持续跌增强"
                is_buy = True
                buy_multiplier = 2.0  # 大幅增加定投金额
                comparison_value = return_diff
                operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
                execution_amount = self.base_amount * buy_multiplier
        elif today_return == 0 and prev_day_return > 0:
            # 今日持平，昨日上涨：转势持平
            status_label = "转势持平"
            is_buy = True
            buy_multiplier = 1.0
            comparison_value = today_return
            operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
            execution_amount = self.base_amount * buy_multiplier
        elif today_return == 0 and prev_day_return < 0:
            # 今日持平，昨日下跌：转势休整
            status_label = "转势休整"
            is_buy = True
            buy_multiplier = 1.2
            comparison_value = today_return
            operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
            execution_amount = self.base_amount * buy_multiplier
        elif today_return > 0 and prev_day_return == 0:
            # 今日上涨，昨日持平：突破上涨
            status_label = "突破上涨"
            is_buy = True
            buy_multiplier = 1.5
            comparison_value = today_return
            operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
            execution_amount = self.base_amount * buy_multiplier
        elif today_return < 0 and prev_day_return == 0:
            # 今日下跌，昨日持平：突破下跌
            status_label = "突破下跌"
            is_buy = True
            buy_multiplier = 1.5
            comparison_value = today_return
            operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
            execution_amount = self.base_amount * buy_multiplier
        else:
            # 其他情况：震荡持平
            status_label = "震荡持平"
            is_buy = True
            buy_multiplier = 1.0
            comparison_value = today_return
            operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
            execution_amount = self.base_amount * buy_multiplier
        
        return status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, execution_amount, buy_multiplier
    
    def reset_strategy(self):
        """
        重置策略状态
        
        在开始新的回测之前调用，清除策略适配器的历史状态
        """
        if self._strategy_adapter is not None:
            self._strategy_adapter.reset()
    
    def update_cumulative_pnl(self, pnl: float):
        """
        更新累计盈亏率
        
        用于止损管理功能，在回测过程中更新当前持仓的累计盈亏
        
        参数：
        pnl: float, 累计盈亏率（小数形式）
        """
        if self._strategy_adapter is not None:
            self._strategy_adapter.update_cumulative_pnl(pnl)
    
    def get_full_analysis(self, today_return, prev_day_return, returns_history=None, cumulative_pnl=None):
        """
        获取完整的策略分析结果
        
        返回统一策略引擎的完整分析结果，包含趋势、波动率、止损状态等详细信息
        
        参数：
        today_return: float, 当日收益率（小数形式）
        prev_day_return: float, 前一日收益率（小数形式）
        returns_history: list, 历史收益率序列（可选）
        cumulative_pnl: float, 累计盈亏率（可选）
        
        返回：
        UnifiedStrategyResult 或 None（如果未启用统一策略引擎）
        """
        if self._strategy_adapter is not None:
            return self._strategy_adapter.get_full_analysis(
                today_return, prev_day_return, returns_history, cumulative_pnl
            )
        return None
    
    def backtest_single_fund(self, fund_code):
        """
        回测单只基金的定投策略
        
        参数：
        fund_code: str, 基金代码
        
        返回：
        pandas.DataFrame, 回测结果数据，包含每日总资产、收益率等信息
        如果回测失败，返回None
        """
        # 获取基金历史数据
        fund_hist = self.get_fund_history(fund_code)
        
        # 检查数据是否足够进行回测（至少需要2天数据）
        if fund_hist is None or len(fund_hist) < 2:
            print(f"基金 {fund_code} 数据不足，无法进行回测")
            return None
        
        # 初始化回测变量
        cash = self.initial_cash  # 初始现金
        shares = 0  # 初始基金份额
        total_asset = []  # 存储每日总资产数据
        benchmark_asset = []  # 存储基准策略每日总资产数据
        benchmark_cash = self.initial_cash  # 基准策略初始现金
        benchmark_shares = 0  # 基准策略初始份额
        
        # 模拟每日交易，从第二天开始（需要前一天的数据）
        for i in range(1, len(fund_hist)):
            today = fund_hist.iloc[i]  # 今日数据
            yesterday = fund_hist.iloc[i-1]  # 昨日数据
            
            today_nav = today['单位净值']  # 今日单位净值
            today_return = today['日增长率']  # 今日收益率（小数）
            prev_day_return = yesterday['日增长率']  # 昨日收益率（小数）
            
            # 获取投资策略建议
            status_label, is_buy, redeem_amount, _, _, _, buy_multiplier = self.get_investment_strategy(today_return, prev_day_return)
            
            # 执行买入操作
            if is_buy:
                # 计算买入金额 = 基准金额 * 买入乘数
                buy_amount = self.base_amount * buy_multiplier
                # 第一天允许现金不足，其他天必须有足够现金
                if cash >= buy_amount or i == 1:
                    buy_shares = buy_amount / today_nav  # 计算可购买份额
                    shares += buy_shares  # 更新总份额
                    cash -= buy_amount  # 更新剩余现金
            
            # 执行赎回操作
            if redeem_amount > 0 and shares > 0:
                redeem_shares = redeem_amount / today_nav  # 计算赎回份额
                shares = max(0, shares - redeem_shares)  # 更新剩余份额（不允许为负）
                cash += redeem_amount  # 更新剩余现金
            
            # 计算当前总资产（现金 + 基金市值）
            current_asset = cash + shares * today_nav
            # 记录每日资产数据
            total_asset.append({
                'date': today['净值日期'],  # 日期
                'total_value': current_asset,  # 总资产
                'cash': cash,  # 剩余现金
                'shares': shares,  # 持有份额
                'nav': today_nav,  # 单位净值
                'strategy': status_label  # 策略标签
            })
            
            # 基准策略：固定金额定投（每天定投base_amount）
            benchmark_buy_amount = self.base_amount
            if benchmark_cash >= benchmark_buy_amount or i == 1:
                benchmark_buy_shares = benchmark_buy_amount / today_nav
                benchmark_shares += benchmark_buy_shares
                benchmark_cash -= benchmark_buy_amount
            # 计算基准策略当前总资产
            benchmark_current_asset = benchmark_cash + benchmark_shares * today_nav
            # 记录基准策略每日资产数据
            benchmark_asset.append({
                'date': today['净值日期'],
                'total_value': benchmark_current_asset
            })
        
        # 将资产数据转换为DataFrame格式
        result_df = pd.DataFrame(total_asset)
        benchmark_df = pd.DataFrame(benchmark_asset)
        
        # 合并策略和基准的结果，添加后缀区分
        result_df = result_df.merge(benchmark_df, on='date', suffixes=('_strategy', '_benchmark'))
        
        # 计算每日收益率（百分比变化）
        result_df['daily_return_strategy'] = result_df['total_value_strategy'].pct_change().fillna(0)
        result_df['daily_return_benchmark'] = result_df['total_value_benchmark'].pct_change().fillna(0)
        
        return result_df
    
    def backtest_portfolio(self, fund_codes, weights=None):
        """
        回测基金组合的定投策略
        
        参数：
        fund_codes: list, 基金代码列表
        weights: list, 基金权重列表，默认为等权重
        
        返回：
        pandas.DataFrame, 组合回测结果数据
        如果回测失败，返回None
        """
        # 如果未指定权重，使用等权重
        if weights is None:
            weights = [1/len(fund_codes)] * len(fund_codes)
        
        # 检查基金代码数量与权重数量是否匹配
        if len(fund_codes) != len(weights):
            print("基金代码数量与权重数量不匹配")
            return None
        
        # 确保权重和为1（归一化）
        weights = np.array(weights) / np.sum(weights)
        
        # 回测每只基金，保存有效的回测结果
        fund_results = {}
        for fund_code in fund_codes:
            result = self.backtest_single_fund(fund_code)
            if result is not None:
                fund_results[fund_code] = result
        
        # 检查是否有有效的回测结果
        if not fund_results:
            print("没有基金数据可以进行组合回测")
            return None
        
        # 合并所有基金的策略结果
        dates = None  # 基准日期序列
        portfolio_asset = []  # 组合策略总资产
        
        # 首先获取沪深300指数历史数据作为基准（优先使用）
        hs300_hist = self.get_hs300_history()
        
        # 获取所有基金的日期范围
        all_fund_dates = set()
        for fund_code, result_df in fund_results.items():
            all_fund_dates.update(result_df['date'].tolist())
        
        if hs300_hist is not None:
            # 使用沪深300指数和基金数据的交集日期作为基准日期序列
            print("使用沪深300指数日期作为基准日期序列")
            hs300_dates = set(hs300_hist['date'].tolist())
            # 计算日期交集
            common_dates = sorted(list(all_fund_dates.intersection(hs300_dates)))
            
            if common_dates:
                dates = pd.to_datetime(common_dates)
            else:
                # 如果没有交集，回退使用第一只基金的日期
                print("沪深300指数与基金数据无日期交集，回退使用第一只基金日期作为基准")
                for i, (fund_code, result_df) in enumerate(fund_results.items()):
                    if i == 0:
                        dates = result_df['date']
                        break
        else:
            # 沪深300数据获取失败，回退使用第一只基金的日期作为基准
            print("获取沪深300指数日期失败，回退使用第一只基金日期作为基准")
            for i, (fund_code, result_df) in enumerate(fund_results.items()):
                if i == 0:
                    # 第一只基金作为基准日期序列
                    dates = result_df['date']
                    break
        
        # 基于基准日期序列计算组合资产
        for i, (fund_code, result_df) in enumerate(fund_results.items()):
            # 对齐基金的日期序列到基准日期
            aligned_df = result_df.set_index('date').reindex(dates).reset_index()
            
            if i == 0:
                # 初始化组合资产（基金资产 * 权重）
                portfolio_asset = aligned_df['total_value_strategy'].fillna(0).values * weights[i]
            else:
                # 累加组合资产（考虑权重）
                portfolio_asset += aligned_df['total_value_strategy'].fillna(0).values * weights[i]
        
        if hs300_hist is None:
            # 如果获取沪深300数据失败，使用原有的基金基准方法
            print("获取沪深300指数数据失败，使用基金基准方法")
            # 重新初始化基准资产
            benchmark_asset = []
            for i, (fund_code, result_df) in enumerate(fund_results.items()):
                if i == 0:
                    benchmark_asset = result_df['total_value_benchmark'].values * weights[i]
                else:
                    aligned_df = result_df.set_index('date').reindex(dates).reset_index()
                    benchmark_asset += aligned_df['total_value_benchmark'].fillna(0).values * weights[i]
        else:
            # 使用沪深300指数作为基准
            print("使用沪深300指数作为回测基准")
            # 对齐沪深300指数日期到基金组合日期
            hs300_aligned = hs300_hist.set_index('date').reindex(dates).reset_index()
            
            # 初始化基准资产（与策略初始资产相同）
            initial_asset = portfolio_asset[0]
            # 计算基于沪深300指数的基准资产
            hs300_returns = hs300_aligned['pct_change'].fillna(0)
            benchmark_asset = [initial_asset]
            
            # 基于沪深300指数计算基准资产变化
            for i in range(1, len(hs300_returns)):
                # 基准资产 = 前一日资产 * (1 + 沪深300日收益率)
                benchmark_asset.append(benchmark_asset[i-1] * (1 + hs300_returns.iloc[i]))
        
        # 创建组合回测结果DataFrame
        portfolio_result = pd.DataFrame({
            'date': dates,
            'total_value_strategy': portfolio_asset,
            'total_value_benchmark': benchmark_asset
        })
        
        # 计算组合每日收益率
        portfolio_result['daily_return_strategy'] = portfolio_result['total_value_strategy'].pct_change().fillna(0)
        portfolio_result['daily_return_benchmark'] = portfolio_result['total_value_benchmark'].pct_change().fillna(0)
        
        return portfolio_result
    
    def calculate_performance_metrics(self, result_df):
        """
        计算绩效指标
        
        参数：
        result_df: pandas.DataFrame, 回测结果数据
        
        返回：
        dict, 包含各种绩效指标的字典
        如果输入数据无效，返回None
        """
        if result_df is None or result_df.empty:
            return None
        
        # 1. 总收益率 = (期末资产 / 期初资产) - 1
        total_return_strategy = (result_df['total_value_strategy'].iloc[-1] / result_df['total_value_strategy'].iloc[0]) - 1
        total_return_benchmark = (result_df['total_value_benchmark'].iloc[-1] / result_df['total_value_benchmark'].iloc[0]) - 1
        
        # 2. 年化收益率 = (1 + 总收益率) ^ (365 / 回测天数) - 1
        days = (result_df['date'].iloc[-1] - result_df['date'].iloc[0]).days
        annual_return_strategy = (1 + total_return_strategy) ** (365 / days) - 1
        annual_return_benchmark = (1 + total_return_benchmark) ** (365 / days) - 1
        
        # 3. 最大回撤计算
        def max_drawdown(asset_values):
            """计算最大回撤
            
            参数：
            asset_values: array, 资产价值序列
            
            返回：
            float, 最大回撤（小数形式，如0.1表示10%）
            """
            peak = asset_values[0]  # 初始峰值
            drawdown = 0  # 当前回撤
            max_dd = 0  # 最大回撤
            for value in asset_values:
                if value > peak:
                    peak = value  # 更新峰值
                drawdown = (peak - value) / peak  # 计算当前回撤
                if drawdown > max_dd:
                    max_dd = drawdown  # 更新最大回撤
            return max_dd
        
        max_dd_strategy = max_drawdown(result_df['total_value_strategy'].values)
        max_dd_benchmark = max_drawdown(result_df['total_value_benchmark'].values)
        
        # 4. 夏普比率 = (年化超额收益) / (年化波动率)
        risk_free_rate = 0.02  # 假设无风险利率为2%
        daily_risk_free = (1 + risk_free_rate) ** (1/252) - 1  # 日无风险利率（使用252个交易日）
        
        # 计算超额收益（策略收益 - 无风险收益）
        excess_return_strategy = result_df['daily_return_strategy'] - daily_risk_free
        # 夏普比率 = 年化超额收益 / 年化波动率
        sharpe_ratio_strategy = excess_return_strategy.mean() / excess_return_strategy.std() * np.sqrt(252) if excess_return_strategy.std() != 0 else 0
        
        excess_return_benchmark = result_df['daily_return_benchmark'] - daily_risk_free
        sharpe_ratio_benchmark = excess_return_benchmark.mean() / excess_return_benchmark.std() * np.sqrt(252) if excess_return_benchmark.std() != 0 else 0
        
        # 5. 胜率 = 正收益天数 / 总交易天数
        win_rate_strategy = (result_df['daily_return_strategy'] > 0).mean()
        win_rate_benchmark = (result_df['daily_return_benchmark'] > 0).mean()
        
        # 6. 年化波动率 = 日收益率标准差 * sqrt(252)（假设252个交易日）
        annual_volatility_strategy = result_df['daily_return_strategy'].std() * np.sqrt(252)
        annual_volatility_benchmark = result_df['daily_return_benchmark'].std() * np.sqrt(252)
        
        # 7. Alpha和Beta
        # 计算协方差矩阵
        cov_matrix = np.cov(result_df['daily_return_strategy'], result_df['daily_return_benchmark'])
        # Beta = 策略与基准的协方差 / 基准的方差
        beta_strategy = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else 0
        # Alpha = (策略年化收益 - 无风险利率) - Beta * (基准年化收益 - 无风险利率)
        alpha_strategy = (annual_return_strategy - risk_free_rate) - beta_strategy * (annual_return_benchmark - risk_free_rate)
        
        # 8. 索提诺比率（只考虑下行风险）
        def sortino_ratio(returns, risk_free_rate):
            """计算索提诺比率
            
            参数：
            returns: array, 收益率序列
            risk_free_rate: float, 无风险利率
            
            返回：
            float, 索提诺比率
            """
            # 只考虑负收益率（下行风险）
            downside_returns = returns[returns < 0]
            if len(downside_returns) == 0:
                return 0
            # 计算下行偏差（年化）
            downside_deviation = downside_returns.std() * np.sqrt(252)
            if downside_deviation == 0:
                return 0
            # 计算年化收益率
            annual_return = (1 + returns.mean()) ** 252 - 1
            # 索提诺比率 = (年化收益 - 无风险利率) / 下行偏差
            return (annual_return - risk_free_rate) / downside_deviation
        
        sortino_ratio_strategy = sortino_ratio(result_df['daily_return_strategy'], risk_free_rate)
        sortino_ratio_benchmark = sortino_ratio(result_df['daily_return_benchmark'], risk_free_rate)
        
        # 9. 卡玛比率 = 年化收益率 / 最大回撤
        calmar_ratio_strategy = annual_return_strategy / max_dd_strategy if max_dd_strategy != 0 else 0
        calmar_ratio_benchmark = annual_return_benchmark / max_dd_benchmark if max_dd_benchmark != 0 else 0
        
        # 整理所有绩效指标到字典
        metrics = {
            '总收益率_strategy': total_return_strategy,
            '总收益率_benchmark': total_return_benchmark,
            '年化收益率_strategy': annual_return_strategy,
            '年化收益率_benchmark': annual_return_benchmark,
            '最大回撤_strategy': max_dd_strategy,
            '最大回撤_benchmark': max_dd_benchmark,
            '夏普比率_strategy': sharpe_ratio_strategy,
            '夏普比率_benchmark': sharpe_ratio_benchmark,
            '胜率_strategy': win_rate_strategy,
            '胜率_benchmark': win_rate_benchmark,
            '年化波动率_strategy': annual_volatility_strategy,
            '年化波动率_benchmark': annual_volatility_benchmark,
            'Alpha_strategy': alpha_strategy,
            'Beta_strategy': beta_strategy,
            '索提诺比率_strategy': sortino_ratio_strategy,
            '索提诺比率_benchmark': sortino_ratio_benchmark,
            '卡玛比率_strategy': calmar_ratio_strategy,
            '卡玛比率_benchmark': calmar_ratio_benchmark
        }
        
        return metrics
    
    def visualize_backtest(self, result_df, fund_code=None):
        """
        可视化回测结果
        
        同时打印绩效指标和绘制图表，包括：
        1. 总资产价值趋势对比
        2. 每日收益率对比
        3. 绩效指标对比
        
        参数：
        result_df: pandas.DataFrame, 回测结果数据
        fund_code: str, 基金代码（可选，用于单基金回测标识）
        """
        if result_df is None or result_df.empty:
            print("没有数据可以可视化")
            return
        
        # 计算绩效指标
        metrics = self.calculate_performance_metrics(result_df)
        
        # 打印回测结果摘要
        print(f'\n{"="*80}')
        print(f'基金定投策略回测结果' + (f' - {fund_code}' if fund_code else ' - 组合'))
        print(f'时间范围: {self.start_date} 至 {self.end_date}')
        print(f'基准定投金额: {self.base_amount} 元/天')
        print(f'初始现金: {self.initial_cash} 元')
        print(f'总交易天数: {len(result_df)} 天')
        print(f'\n绩效指标：')
        
        if metrics:
            print(f'策略总收益率: {metrics["总收益率_strategy"]:.2%}')
            print(f'基准总收益率: {metrics["总收益率_benchmark"]:.2%}')
            print(f'策略年化收益率: {metrics["年化收益率_strategy"]:.2%}')
            print(f'基准年化收益率: {metrics["年化收益率_benchmark"]:.2%}')
            print(f'策略最大回撤: {metrics["最大回撤_strategy"]:.2%}')
            print(f'基准最大回撤: {metrics["最大回撤_benchmark"]:.2%}')
            print(f'策略夏普比率: {metrics["夏普比率_strategy"]:.2f}')
            print(f'基准夏普比率: {metrics["夏普比率_benchmark"]:.2f}')
            print(f'策略胜率: {metrics["胜率_strategy"]:.2%}')
            print(f'基准胜率: {metrics["胜率_benchmark"]:.2%}')
            
            # 计算超额收益
            excess_return = metrics["总收益率_strategy"] - metrics["总收益率_benchmark"]
            excess_annual_return = metrics["年化收益率_strategy"] - metrics["年化收益率_benchmark"]
            print(f'\n超额收益：')
            print(f'总超额收益率: {excess_return:.2%}')
            print(f'年化超额收益率: {excess_annual_return:.2%}')
        
        # 打印期末总资产对比
        print(f'\n期末总资产对比：')
        print(f'策略期末总资产: {result_df["total_value_strategy"].iloc[-1]:.2f} 元')
        print(f'基准期末总资产: {result_df["total_value_benchmark"].iloc[-1]:.2f} 元')
        print(f'总资产差异: {result_df["total_value_strategy"].iloc[-1] - result_df["total_value_benchmark"].iloc[-1]:.2f} 元')
        
        print(f'{"="*80}\n')
        
        # 绘制可视化图表
        try:
            # 设置中文显示，解决中文乱码问题
            # 设置matplotlib中文字体支持（Windows优先使用微软雅黑）
            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
            
            # 创建三个子图，垂直排列
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 15))
            # 设置图表标题
            fig.suptitle(f'基金定投策略回测结果' + (f' - {fund_code}' if fund_code else ' - 组合'), fontsize=16)
            
            # 第一个子图：总资产价值趋势对比
            ax1.plot(result_df['date'], result_df['total_value_strategy'], label='策略总资产', color='blue')
            ax1.plot(result_df['date'], result_df['total_value_benchmark'], label='基准总资产', color='red')
            ax1.set_xlabel('日期')
            ax1.set_ylabel('总资产价值 (元)')
            ax1.set_title('总资产价值趋势对比')
            ax1.legend()  # 显示图例
            ax1.grid(True)  # 显示网格线
            
            # 第二个子图：每日收益率对比
            ax2.plot(result_df['date'], result_df['daily_return_strategy'] * 100, label='策略日收益率', color='blue', alpha=0.6)
            ax2.plot(result_df['date'], result_df['daily_return_benchmark'] * 100, label='基准日收益率', color='red', alpha=0.6)
            ax2.set_xlabel('日期')
            ax2.set_ylabel('日收益率 (%)')
            ax2.set_title('每日收益率对比')
            ax2.legend()
            ax2.grid(True)
            
            # 第三个子图：绩效指标对比（柱状图）
            if metrics:
                # 准备指标数据
                metrics_names = ['总收益率', '年化收益率', '最大回撤', '夏普比率', '胜率', '年化波动率', 'Alpha', 'Beta', '索提诺比率', '卡玛比率']
                # 策略指标值
                strategy_values = [
                    metrics['总收益率_strategy'], metrics['年化收益率_strategy'], metrics['最大回撤_strategy'],
                    metrics['夏普比率_strategy'], metrics['胜率_strategy'], metrics['年化波动率_strategy'],
                    metrics['Alpha_strategy'], metrics['Beta_strategy'], metrics['索提诺比率_strategy'], metrics['卡玛比率_strategy']
                ]
                # 基准指标值（Alpha基准为0，Beta基准为1）
                benchmark_values = [
                    metrics['总收益率_benchmark'], metrics['年化收益率_benchmark'], metrics['最大回撤_benchmark'],
                    metrics['夏普比率_benchmark'], metrics['胜率_benchmark'], metrics['年化波动率_benchmark'],
                    0, 1, metrics['索提诺比率_benchmark'], metrics['卡玛比率_benchmark']
                ]
                
                # 设置柱状图参数
                bar_width = 0.35
                index = np.arange(len(metrics_names))
                
                # 绘制策略和基准的柱状图
                bars1 = ax3.bar(index - bar_width/2, strategy_values, bar_width, label='策略', color='blue')
                bars2 = ax3.bar(index + bar_width/2, benchmark_values, bar_width, label='基准', color='red')
                
                # 设置图表属性
                ax3.set_xlabel('绩效指标')
                ax3.set_ylabel('指标值')
                ax3.set_title('绩效指标对比')
                ax3.set_xticks(index)  # 设置X轴刻度位置
                ax3.set_xticklabels(metrics_names, rotation=45, ha='right')  # 设置X轴标签，旋转45度
                ax3.legend()
                ax3.grid(True, axis='y')  # 只显示Y轴网格线
                
                # 为柱状图添加数值标签
                def add_labels(bars):
                    """为柱状图添加数值标签"""
                    for bar in bars:
                        height = bar.get_height()
                        # 根据指标类型选择合适的格式（百分比或小数）
                        if '%' in ax3.get_ylabel() or metrics_names[bars.index(bar)] in ['总收益率', '年化收益率', '最大回撤', '胜率']:
                            label = f'{height:.2%}'  # 百分比格式
                        else:
                            label = f'{height:.2f}'  # 小数格式
                        # 添加标签
                        ax3.annotate(label,
                                   xy=(bar.get_x() + bar.get_width()/2, height),
                                   xytext=(0, 3),  # 3点垂直偏移
                                   textcoords="offset points",
                                   ha='center', va='bottom')
                
                # 为两个柱状图添加标签
                add_labels(bars1)
                add_labels(bars2)
            
            # 调整图表布局，避免标签重叠
            plt.tight_layout()
            plt.subplots_adjust(top=0.9, hspace=0.3)  # 调整顶部和子图间距
            
            # 保存图表到文件
            chart_filename = f"backtest_chart_{fund_code if fund_code else 'portfolio'}.png"
            plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
            print(f"图表已保存到文件: {chart_filename}")
            
            # 尝试显示图表（在有图形界面的环境中）
            try:
                plt.show()
            except:
                print("图表已保存但无法显示（可能是因为没有图形界面）")
            
        except Exception as e:
            # 捕获并打印绘图异常
            print(f"绘制图表时出错: {e}")
            print("可能是因为没有可用的图形界面或者中文字体缺失")
            print("将只显示绩效指标数据")
    
    def visualize_portfolio(self, result_df):
        """
        可视化基金组合回测结果
        
        调用visualize_backtest方法，专门用于基金组合的可视化
        
        参数：
        result_df: pandas.DataFrame, 组合回测结果数据
        """
        self.visualize_backtest(result_df)


# 模块级函数，供测试使用
def calculate_cumulative_returns(returns: np.ndarray) -> np.ndarray:
    """
    计算累计收益率
    
    参数:
        returns: 日收益率数组
        
    返回:
        累计收益率数组
    """
    if len(returns) == 0:
        return np.array([])
    
    # 计算累计收益
    cumulative = np.cumprod(1 + returns) - 1
    return cumulative


def calculate_max_drawdown(prices: np.ndarray) -> tuple:
    """
    计算最大回撤
    
    参数:
        prices: 价格序列
        
    返回:
        (最大回撤值, 开始索引, 结束索引)
    """
    if len(prices) == 0:
        return 0.0, 0, 0
    
    # 计算累计最大值
    running_max = np.maximum.accumulate(prices)
    
    # 计算回撤
    drawdown = (prices - running_max) / running_max
    
    # 找到最大回撤
    max_dd_idx = np.argmin(drawdown)
    max_dd = drawdown[max_dd_idx]
    
    # 找到回撤开始点（最高点）
    start_idx = np.argmax(prices[:max_dd_idx + 1]) if max_dd_idx > 0 else 0
    
    return max_dd, start_idx, max_dd_idx


def calculate_sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
    """
    计算夏普比率
    
    参数:
        returns: 收益率数组（日收益率）
        risk_free_rate: 无风险利率（年化）
        
    返回:
        夏普比率
        
    注意:
        此函数已重构为使用 PerformanceCalculator 的实现
        保留此函数以维持向后兼容性
    """
    # 使用 PerformanceCalculator 的实现
    from ..analysis.performance_metrics import PerformanceCalculator
    
    calculator = PerformanceCalculator(risk_free_rate=risk_free_rate)
    return calculator.calculate_sharpe_ratio(returns)


def calculate_volatility(returns: np.ndarray) -> float:
    """
    计算波动率（年化）
    
    参数:
        returns: 收益率数组
        
    返回:
        年化波动率
    """
    if len(returns) == 0:
        return 0.0
    
    return np.std(returns) * np.sqrt(252)


# 示例用法
if __name__ == "__main__":
    """示例：演示FundBacktest类的使用"""
    # 创建回测引擎实例
    backtester = FundBacktest(
        base_amount=100,  # 每天定投100元
        start_date='2020-01-01',  # 回测开始日期
        end_date='2023-12-29'  # 回测结束日期
    )
    
    # 示例1：回测单只基金
    fund_code = '005827'  # 易方达蓝筹精选混合
    print(f"正在回测基金 {fund_code}...")
    result_single = backtester.backtest_single_fund(fund_code)
    if result_single is not None:
        print(f"基金 {fund_code} 回测完成")
        backtester.visualize_backtest(result_single, fund_code)
    
    # 示例2：回测基金组合
    fund_codes = ['005827', '110022', '000001', '001475', '000988']  # 示例基金组合
    weights = [0.2, 0.2, 0.2, 0.2, 0.2]  # 等权重分配
    print(f"正在回测基金组合 {fund_codes}...")
    result_portfolio = backtester.backtest_portfolio(fund_codes, weights)
    if result_portfolio is not None:
        print("基金组合回测完成")
        backtester.visualize_portfolio(result_portfolio)
