import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import akshare as ak
import datetime
from fund_realtime import FundRealTime

class FundBacktest:
    def __init__(self, base_amount=100, start_date='2020-01-01', end_date=None, initial_cash=None):
        self.base_amount = base_amount
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.datetime.now().strftime('%Y-%m-%d')
        self.initial_cash = initial_cash if initial_cash is not None else base_amount
        
    def get_fund_history(self, fund_code):
        """从akshare获取基金历史数据"""
        try:
            fund_hist = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            if fund_hist.empty:
                print(f"基金 {fund_code} 没有获取到历史数据")
                return None
            
            # 过滤日期范围
            fund_hist['净值日期'] = pd.to_datetime(fund_hist['净值日期'])
            fund_hist = fund_hist[(fund_hist['净值日期'] >= self.start_date) & (fund_hist['净值日期'] <= self.end_date)]
            
            # 转换数据类型
            fund_hist['单位净值'] = pd.to_numeric(fund_hist['单位净值'], errors='coerce')
            fund_hist['日增长率'] = pd.to_numeric(fund_hist['日增长率'].astype(str).str.rstrip('%'), errors='coerce') / 100
            
            # 重置索引
            fund_hist = fund_hist.reset_index(drop=True)
            
            return fund_hist
        except Exception as e:
            print(f"获取基金 {fund_code} 历史数据时出错: {e}")
            return None
    
    def get_investment_strategy(self, today_return, prev_day_return):
        """复制search_01.py中的投资策略逻辑"""
        status_label = ""
        is_buy = False
        redeem_amount = 0
        comparison_value = 0
        operation_suggestion = ""
        execution_amount = 0
        buy_multiplier = 1.0
        
        # 计算今日与昨日的增长率差
        return_diff = today_return - prev_day_return
        
        # 策略逻辑分支
        if today_return > 0 and prev_day_return <= 0:
            status_label = "反转涨"
            is_buy = True
            buy_multiplier = 1.5
            comparison_value = today_return
            operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
            execution_amount = self.base_amount * buy_multiplier
        elif today_return <= 0 and prev_day_return > 0:
            status_label = "反转跌"
            is_buy = False
            redeem_amount = 30
            comparison_value = today_return
            operation_suggestion = f"赎回 {redeem_amount} 元"
            execution_amount = -redeem_amount
        elif today_return > 0 and prev_day_return > 0:
            if return_diff > 0:
                status_label = "持续涨增强"
                is_buy = True
                buy_multiplier = 1.2
                comparison_value = return_diff
                operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
                execution_amount = self.base_amount * buy_multiplier
            else:
                status_label = "持续涨减弱"
                is_buy = True
                buy_multiplier = 1.0
                comparison_value = return_diff
                operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
                execution_amount = self.base_amount * buy_multiplier
        elif today_return < 0 and prev_day_return < 0:
            if return_diff > 0:
                status_label = "持续跌减弱"
                is_buy = True
                buy_multiplier = 1.5
                comparison_value = return_diff
                operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
                execution_amount = self.base_amount * buy_multiplier
            else:
                status_label = "持续跌增强"
                is_buy = True
                buy_multiplier = 2.0
                comparison_value = return_diff
                operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
                execution_amount = self.base_amount * buy_multiplier
        elif today_return == 0 and prev_day_return > 0:
            status_label = "转势持平"
            is_buy = True
            buy_multiplier = 1.0
            comparison_value = today_return
            operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
            execution_amount = self.base_amount * buy_multiplier
        elif today_return == 0 and prev_day_return < 0:
            status_label = "转势休整"
            is_buy = True
            buy_multiplier = 1.2
            comparison_value = today_return
            operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
            execution_amount = self.base_amount * buy_multiplier
        elif today_return > 0 and prev_day_return == 0:
            status_label = "突破上涨"
            is_buy = True
            buy_multiplier = 1.5
            comparison_value = today_return
            operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
            execution_amount = self.base_amount * buy_multiplier
        elif today_return < 0 and prev_day_return == 0:
            status_label = "突破下跌"
            is_buy = True
            buy_multiplier = 1.5
            comparison_value = today_return
            operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
            execution_amount = self.base_amount * buy_multiplier
        else:
            status_label = "震荡持平"
            is_buy = True
            buy_multiplier = 1.0
            comparison_value = today_return
            operation_suggestion = f"定投金额 {self.base_amount * buy_multiplier} 元"
            execution_amount = self.base_amount * buy_multiplier
        
        return status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, execution_amount, buy_multiplier
    
    def backtest_single_fund(self, fund_code):
        """回测单只基金的定投策略"""
        # 获取历史数据
        fund_hist = self.get_fund_history(fund_code)
        if fund_hist is None or len(fund_hist) < 2:
            print(f"基金 {fund_code} 数据不足，无法进行回测")
            return None
        
        # 初始化变量
        cash = self.initial_cash
        shares = 0
        total_asset = []
        benchmark_asset = []
        benchmark_cash = self.initial_cash
        benchmark_shares = 0
        
        # 模拟每日交易
        for i in range(1, len(fund_hist)):
            today = fund_hist.iloc[i]
            yesterday = fund_hist.iloc[i-1]
            
            today_nav = today['单位净值']
            today_return = today['日增长率']
            prev_day_return = yesterday['日增长率']
            
            # 获取投资策略
            status_label, is_buy, redeem_amount, _, _, _, buy_multiplier = self.get_investment_strategy(today_return, prev_day_return)
            
            # 执行买入
            if is_buy:
                buy_amount = self.base_amount * buy_multiplier
                if cash >= buy_amount or i == 1:  # 第一天允许现金不足
                    buy_shares = buy_amount / today_nav
                    shares += buy_shares
                    cash -= buy_amount
            
            # 执行赎回
            if redeem_amount > 0 and shares > 0:
                redeem_shares = redeem_amount / today_nav
                shares = max(0, shares - redeem_shares)
                cash += redeem_amount
            
            # 计算总资产
            current_asset = cash + shares * today_nav
            total_asset.append({
                'date': today['净值日期'],
                'total_value': current_asset,
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
                'total_value': benchmark_current_asset
            })
        
        # 转换为DataFrame
        result_df = pd.DataFrame(total_asset)
        benchmark_df = pd.DataFrame(benchmark_asset)
        
        # 合并结果
        result_df = result_df.merge(benchmark_df, on='date', suffixes=('_strategy', '_benchmark'))
        
        # 计算每日收益率
        result_df['daily_return_strategy'] = result_df['total_value_strategy'].pct_change().fillna(0)
        result_df['daily_return_benchmark'] = result_df['total_value_benchmark'].pct_change().fillna(0)
        
        return result_df
    
    def backtest_portfolio(self, fund_codes, weights=None):
        """回测基金组合的定投策略"""
        if weights is None:
            weights = [1/len(fund_codes)] * len(fund_codes)
        
        if len(fund_codes) != len(weights):
            print("基金代码数量与权重数量不匹配")
            return None
        
        # 确保权重和为1
        weights = np.array(weights) / np.sum(weights)
        
        # 回测每只基金
        fund_results = {}
        for fund_code in fund_codes:
            result = self.backtest_single_fund(fund_code)
            if result is not None:
                fund_results[fund_code] = result
        
        if not fund_results:
            print("没有基金数据可以进行组合回测")
            return None
        
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
        
        return portfolio_result
    
    def calculate_performance_metrics(self, result_df):
        """计算绩效指标"""
        if result_df is None or result_df.empty:
            return None
        
        # 总收益率
        total_return_strategy = (result_df['total_value_strategy'].iloc[-1] / result_df['total_value_strategy'].iloc[0]) - 1
        total_return_benchmark = (result_df['total_value_benchmark'].iloc[-1] / result_df['total_value_benchmark'].iloc[0]) - 1
        
        # 年化收益率
        days = (result_df['date'].iloc[-1] - result_df['date'].iloc[0]).days
        annual_return_strategy = (1 + total_return_strategy) ** (365 / days) - 1
        annual_return_benchmark = (1 + total_return_benchmark) ** (365 / days) - 1
        
        # 最大回撤
        def max_drawdown(asset_values):
            peak = asset_values[0]
            drawdown = 0
            max_dd = 0
            for value in asset_values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                if drawdown > max_dd:
                    max_dd = drawdown
            return max_dd
        
        max_dd_strategy = max_drawdown(result_df['total_value_strategy'].values)
        max_dd_benchmark = max_drawdown(result_df['total_value_benchmark'].values)
        
        # 夏普比率
        risk_free_rate = 0.03  # 假设无风险利率为3%
        daily_risk_free = (1 + risk_free_rate) ** (1/365) - 1
        
        excess_return_strategy = result_df['daily_return_strategy'] - daily_risk_free
        sharpe_ratio_strategy = excess_return_strategy.mean() / excess_return_strategy.std() * np.sqrt(365) if excess_return_strategy.std() != 0 else 0
        
        excess_return_benchmark = result_df['daily_return_benchmark'] - daily_risk_free
        sharpe_ratio_benchmark = excess_return_benchmark.mean() / excess_return_benchmark.std() * np.sqrt(365) if excess_return_benchmark.std() != 0 else 0
        
        # 胜率
        win_rate_strategy = (result_df['daily_return_strategy'] > 0).mean()
        win_rate_benchmark = (result_df['daily_return_benchmark'] > 0).mean()
        
        # 年化波动率
        annual_volatility_strategy = result_df['daily_return_strategy'].std() * np.sqrt(252)  # 假设252个交易日
        annual_volatility_benchmark = result_df['daily_return_benchmark'].std() * np.sqrt(252)
        
        # Alpha和Beta
        cov_matrix = np.cov(result_df['daily_return_strategy'], result_df['daily_return_benchmark'])
        beta_strategy = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else 0
        alpha_strategy = (annual_return_strategy - risk_free_rate) - beta_strategy * (annual_return_benchmark - risk_free_rate)
        
        # 索提诺比率 (只考虑下行风险)
        def sortino_ratio(returns, risk_free_rate):
            downside_returns = returns[returns < 0]
            if len(downside_returns) == 0:
                return 0
            downside_deviation = downside_returns.std() * np.sqrt(252)
            if downside_deviation == 0:
                return 0
            return (annual_return_strategy - risk_free_rate) / downside_deviation
        
        sortino_ratio_strategy = sortino_ratio(result_df['daily_return_strategy'], risk_free_rate)
        sortino_ratio_benchmark = sortino_ratio(result_df['daily_return_benchmark'], risk_free_rate)
        
        # 卡玛比率 (年化收益率/最大回撤)
        calmar_ratio_strategy = annual_return_strategy / max_dd_strategy if max_dd_strategy != 0 else 0
        calmar_ratio_benchmark = annual_return_benchmark / max_dd_benchmark if max_dd_benchmark != 0 else 0
        
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
        """可视化回测结果（同时打印绩效指标和绘制图表）"""
        if result_df is None or result_df.empty:
            print("没有数据可以可视化")
            return
        
        # 计算绩效指标
        metrics = self.calculate_performance_metrics(result_df)
        
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
        
        print(f'\n期末总资产对比：')
        print(f'策略期末总资产: {result_df["total_value_strategy"].iloc[-1]:.2f} 元')
        print(f'基准期末总资产: {result_df["total_value_benchmark"].iloc[-1]:.2f} 元')
        print(f'总资产差异: {result_df["total_value_strategy"].iloc[-1] - result_df["total_value_benchmark"].iloc[-1]:.2f} 元')
        
        print(f'{"="*80}\n')
        
        # 绘制图表
        try:
            # 设置中文显示
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'Microsoft YaHei']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 创建三个子图
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 15))
            fig.suptitle(f'基金定投策略回测结果' + (f' - {fund_code}' if fund_code else ' - 组合'), fontsize=16)
            
            # 第一个子图：总资产价值趋势
            ax1.plot(result_df['date'], result_df['total_value_strategy'], label='策略总资产', color='blue')
            ax1.plot(result_df['date'], result_df['total_value_benchmark'], label='基准总资产', color='red')
            ax1.set_xlabel('日期')
            ax1.set_ylabel('总资产价值 (元)')
            ax1.set_title('总资产价值趋势对比')
            ax1.legend()
            ax1.grid(True)
            
            # 第二个子图：每日收益率对比
            ax2.plot(result_df['date'], result_df['daily_return_strategy'] * 100, label='策略日收益率', color='blue', alpha=0.6)
            ax2.plot(result_df['date'], result_df['daily_return_benchmark'] * 100, label='基准日收益率', color='red', alpha=0.6)
            ax2.set_xlabel('日期')
            ax2.set_ylabel('日收益率 (%)')
            ax2.set_title('每日收益率对比')
            ax2.legend()
            ax2.grid(True)
            
            # 第三个子图：绩效指标对比
            if metrics:
                # 准备指标数据
                metrics_names = ['总收益率', '年化收益率', '最大回撤', '夏普比率', '胜率', '年化波动率', 'Alpha', 'Beta', '索提诺比率', '卡玛比率']
                strategy_values = [
                    metrics['总收益率_strategy'], metrics['年化收益率_strategy'], metrics['最大回撤_strategy'],
                    metrics['夏普比率_strategy'], metrics['胜率_strategy'], metrics['年化波动率_strategy'],
                    metrics['Alpha_strategy'], metrics['Beta_strategy'], metrics['索提诺比率_strategy'], metrics['卡玛比率_strategy']
                ]
                benchmark_values = [
                    metrics['总收益率_benchmark'], metrics['年化收益率_benchmark'], metrics['最大回撤_benchmark'],
                    metrics['夏普比率_benchmark'], metrics['胜率_benchmark'], metrics['年化波动率_benchmark'],
                    0, 1, metrics['索提诺比率_benchmark'], metrics['卡玛比率_benchmark']  # Alpha基准为0，Beta基准为1
                ]
                
                # 设置图表
                bar_width = 0.35
                index = np.arange(len(metrics_names))
                
                bars1 = ax3.bar(index - bar_width/2, strategy_values, bar_width, label='策略', color='blue')
                bars2 = ax3.bar(index + bar_width/2, benchmark_values, bar_width, label='基准', color='red')
                
                ax3.set_xlabel('绩效指标')
                ax3.set_ylabel('指标值')
                ax3.set_title('绩效指标对比')
                ax3.set_xticks(index)
                ax3.set_xticklabels(metrics_names, rotation=45, ha='right')
                ax3.legend()
                ax3.grid(True, axis='y')
                
                # 添加数值标签
                def add_labels(bars):
                    for bar in bars:
                        height = bar.get_height()
                        ax3.annotate(f'{height:.2%}' if '%' in ax3.get_ylabel() or metrics_names[bars.index(bar)] in ['总收益率', '年化收益率', '最大回撤', '胜率'] else f'{height:.2f}',
                                   xy=(bar.get_x() + bar.get_width()/2, height),
                                   xytext=(0, 3),  # 3点垂直偏移
                                   textcoords="offset points",
                                   ha='center', va='bottom')
                
                add_labels(bars1)
                add_labels(bars2)
            
            # 调整布局
            plt.tight_layout()
            plt.subplots_adjust(top=0.9, hspace=0.3)
            
            # 保存图表到文件
            chart_filename = f"backtest_chart_{fund_code if fund_code else 'portfolio'}.png"
            plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
            print(f"图表已保存到文件: {chart_filename}")
            
            # 尝试显示图表
            try:
                plt.show()
            except:
                print("图表已保存但无法显示（可能是因为没有图形界面）")
            
        except Exception as e:
            print(f"绘制图表时出错: {e}")
            print("可能是因为没有可用的图形界面或者中文字体缺失")
            print("将只显示绩效指标数据")
    
    def visualize_portfolio(self, result_df):
        """可视化基金组合回测结果"""
        self.visualize_backtest(result_df)

# 示例用法
if __name__ == "__main__":
    # 创建回测引擎实例
    backtester = FundBacktest(base_amount=100, start_date='2020-01-01', end_date='2023-12-31')
    
    # 回测单只基金
    fund_code = '005827'  # 易方达蓝筹精选混合
    print(f"正在回测基金 {fund_code}...")
    result_single = backtester.backtest_single_fund(fund_code)
    if result_single is not None:
        print(f"基金 {fund_code} 回测完成")
        backtester.visualize_backtest(result_single, fund_code)
    
    # 回测基金组合
    fund_codes = ['005827', '110022', '000001', '001475', '000988']  # 示例基金组合
    weights = [0.2, 0.2, 0.2, 0.2, 0.2]  # 等权重
    print(f"正在回测基金组合 {fund_codes}...")
    result_portfolio = backtester.backtest_portfolio(fund_codes, weights)
    if result_portfolio is not None:
        print("基金组合回测完成")
        backtester.visualize_portfolio(result_portfolio)
