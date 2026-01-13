#!/usr/bin/env python
# coding: utf-8

"""
基金回测脚本：集成search_01.py策略的回测实现

该脚本继承自backtest_engine.py中的FundBacktest类，
通过重写get_investment_strategy方法，实现了使用search_01.py中的
投资策略进行基金组合回测的功能。

功能说明：
1. 从Excel文件读取基金持仓数据
2. 过滤无效基金代码
3. 基于search_01.py策略进行基金组合回测
4. 计算并输出绩效指标
5. 生成可视化图表
"""

# 导入必要的库
import pandas as pd  # 用于数据处理
import numpy as np   # 用于数值计算

# 导入回测引擎和策略函数
from backtest_engine import FundBacktest  # 回测引擎基类
from search_01 import get_investment_strategy  # 自定义投资策略

class FundBacktestWithSearch01(FundBacktest):
    """
    集成search_01.py策略的基金回测类
    
    继承自FundBacktest类，通过重写get_investment_strategy方法，
    将search_01.py中的投资策略集成到回测框架中。
    """
    
    def get_investment_strategy(self, today_return, prev_day_return):
        """
        获取投资策略建议
        
        重写父类方法，调用search_01.py中的策略函数生成投资建议
        
        参数：
        today_return: float, 当日收益率（小数形式，如0.01表示1%）
        prev_day_return: float, 前一日收益率（小数形式）
        
        返回：
        status_label: str, 策略状态标签（如"反转涨"、"反转跌"等）
        is_buy: bool, 是否买入标志
        redeem_amount: float, 赎回金额
        comparison_value: float, 比较值（用于策略决策的中间变量）
        operation_suggestion: str, 操作建议文本
        actual_amount: float, 实际执行金额
        buy_multiplier: float, 买入乘数（基于策略调整的定投倍数）
        """
        # 将收益率从小数转换为百分比，以匹配search_01.py的参数要求
        today_return_pct = today_return * 100  
        prev_day_return_pct = prev_day_return * 100  
        
        # 调用search_01.py中的策略函数获取投资建议
        status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, execution_amount, buy_multiplier = \
            get_investment_strategy(today_return_pct, prev_day_return_pct)
        
        # 根据策略建议计算实际执行金额
        if is_buy:  # 如果是买入操作
            # 实际买入金额 = 基准定投金额 * 买入乘数
            actual_amount = self.base_amount * buy_multiplier
        else:  # 如果不是买入操作
            actual_amount = 0  # 执行金额为0
        
        # 返回完整的策略建议
        return status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, actual_amount, buy_multiplier

if __name__ == "__main__":
    """主函数入口：执行基金组合回测流程"""
    
    # 1. 读取Excel文件中的基金持仓数据
    file_path = "d:/codes/py4zinia/京东金融.xlsx"  # Excel文件路径
    position_data = pd.read_excel(file_path, sheet_name='持仓数据')  # 读取持仓数据
    
    # 2. 提取基金代码列表
    fund_codes = position_data['代码'].astype(str).tolist()  # 将代码转换为字符串并转为列表
    
    # 3. 过滤无效基金代码
    # 排除"汇总"行和空字符串，确保只有有效的基金代码参与回测
    fund_codes = [code for code in fund_codes if code != "汇总" and code.strip() != ""]
    
    print(f"共获取到 {len(fund_codes)} 个有效基金代码")
    print(f"前5个基金代码: {fund_codes[:5]}...")
    
    # 4. 初始化回测实例
    backtest = FundBacktestWithSearch01(
        base_amount=100,  # 基准定投金额：100元/次
        start_date='2023-01-01',  # 回测开始日期
        end_date='2025-12-30'  # 回测结束日期
    )
    
    # 5. 运行基金组合回测
    print("\n开始运行基金组合回测...")
    portfolio_result = backtest.backtest_portfolio(fund_codes)
    
    # 6. 处理回测结果
    if portfolio_result is not None:  # 回测成功
        print("回测完成！开始计算绩效指标...")
        
        # 6.1 计算绩效指标
        metrics = backtest.calculate_performance_metrics(portfolio_result)
        
        # 6.2 打印详细绩效指标
        print("\n" + "="*80)
        print("组合回测结果详细指标")
        print("="*80)
        print(f"总收益率_strategy: {metrics['总收益率_strategy']:.4%}  |  总收益率_benchmark: {metrics['总收益率_benchmark']:.4%}")
        print(f"年化收益率_strategy: {metrics['年化收益率_strategy']:.4%}  |  年化收益率_benchmark: {metrics['年化收益率_benchmark']:.4%}")
        print(f"最大回撤_strategy: {metrics['最大回撤_strategy']:.4%}  |  最大回撤_benchmark: {metrics['最大回撤_benchmark']:.4%}")
        print(f"夏普比率_strategy: {metrics['夏普比率_strategy']:.4f}  |  夏普比率_benchmark: {metrics['夏普比率_benchmark']:.4f}")
        print(f"胜率_strategy: {metrics['胜率_strategy']:.4%}  |  胜率_benchmark: {metrics['胜率_benchmark']:.4%}")
        print(f"年化波动率_strategy: {metrics['年化波动率_strategy']:.4%}  |  年化波动率_benchmark: {metrics['年化波动率_benchmark']:.4%}")
        print(f"Alpha_strategy: {metrics['Alpha_strategy']:.4f}  |  Beta_strategy: {metrics['Beta_strategy']:.4f}")
        print(f"索提诺比率_strategy: {metrics['索提诺比率_strategy']:.4f}  |  索提诺比率_benchmark: {metrics['索提诺比率_benchmark']:.4f}")
        print(f"卡玛比率_strategy: {metrics['卡玛比率_strategy']:.4f}  |  卡玛比率_benchmark: {metrics['卡玛比率_benchmark']:.4f}")
        print("="*80)
        
        # 6.3 生成可视化图表
        print("\n生成回测结果可视化图表...")
        backtest.visualize_backtest(portfolio_result)
        print("图表已保存到文件: backtest_chart_portfolio.png")
    else:  # 回测失败
        print("回测失败，没有获得有效的回测结果")
