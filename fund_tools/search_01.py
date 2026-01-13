#!/usr/bin/env python
# coding: utf-8

import pandas as pd, openpyxl
import schedule
import time
from datetime import date
pd.set_option('display.expand_frame_repr', False)  # 核心：不换行，强制一行显示所有列
pd.set_option('display.max_columns', None)         # 显示所有列（默认会限制列数导致截断/换行）
pd.set_option('display.width', 1000)               # 设置控制台显示宽度（值越大，一行能容纳的内容越多）
pd.set_option('display.max_colwidth', 20)          # 可选：设置每列的最大宽度（避免单列内容过长）

# 定义生成微信通知HTML消息的函数
def generate_wechat_message(result_df):
    """
    根据基金分析结果生成微信通知的HTML消息
    
    参数：
    result_df: 基金分析结果的DataFrame
    
    返回：
    str: 格式化的HTML消息内容
    """
    from datetime import date
    
    # 创建一个副本用于格式化显示
    df_display = result_df.copy()
    
    # 生成HTML消息
    message = f"<h2>📊 基金分析报告 - {date.today().strftime('%Y年%m月%d日')}</h2>\n"
    
    # 检查是否包含绩效分析的指标
    if 'annualized_return' in df_display.columns and 'max_drawdown' in df_display.columns and 'sharpe_ratio' in df_display.columns:
        # 这是绩效分析结果
        message += f"<h3>基金绩效对比分析</h3>\n"
        
        # 格式化收益率为百分比
        df_display['yesterday_return'] = df_display['yesterday_return'].map('{:.2f}%'.format)
        df_display['today_return'] = df_display['today_return'].map('{:.2f}%'.format)
        df_display['return_change'] = df_display['return_change'].map('{:.2f}%'.format)
        df_display['annualized_return'] = (df_display['annualized_return'] * 100).map('{:.2f}%'.format)
        df_display['max_drawdown'] = (df_display['max_drawdown'] * 100).map('{:.2f}%'.format)
        df_display['sharpe_ratio'] = df_display['sharpe_ratio'].map('{:.2f}'.format)
        
        # 生成绩效分析表格
        message += f"<table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse; width: 100%;'>\n"
        message += f"<thead>\n"
        message += f"<tr style='background-color: #f0f0f0;'>\n"
        message += f"<th>基金代码</th>\n"
        message += f"<th>基金名称</th>\n"
        message += f"<th>昨日收益率</th>\n"
        message += f"<th>今日收益率</th>\n"
        message += f"<th>收益率变化</th>\n"
        message += f"<th>年化收益率</th>\n"
        message += f"<th>最大回撤</th>\n"
        message += f"<th>Sharpe比率</th>\n"
        message += f"</tr>\n"
        message += f"</thead>\n"
        message += f"<tbody>\n"
        
        for _, row in df_display.iterrows():
            message += f"<tr>\n"
            message += f"<td>{row['fund_code']}</td>\n"
            message += f"<td>{row['fund_name']}</td>\n"
            message += f"<td>{row['yesterday_return']}</td>\n"
            message += f"<td>{row['today_return']}</td>\n"
            message += f"<td>{row['return_change']}</td>\n"
            message += f"<td>{row['annualized_return']}</td>\n"
            message += f"<td>{row['max_drawdown']}</td>\n"
            message += f"<td>{row['sharpe_ratio']}</td>\n"
            message += f"</tr>\n"
        
        message += f"</tbody>\n"
        message += f"</table>\n"
    else:
        # 这是常规的基金分析结果
        message += f"<h3>持仓基金收益率变化分析</h3>\n"
        
        # 格式化收益率为百分比
        df_display['today_return'] = df_display['today_return'].map('{:.2f}%'.format)
        df_display['prev_day_return'] = df_display['prev_day_return'].map('{:.2f}%'.format)
        df_display['comparison_value'] = df_display['comparison_value'].map('{:.2f}%'.format)
        
        # 按照操作建议和执行金额排序
        df_display = df_display.sort_values(by=['operation_suggestion', 'execution_amount'])
        
        # 生成常规分析表格
        message += f"<table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse; width: 100%;'>\n"
        message += f"<thead>\n"
        message += f"<tr style='background-color: #f0f0f0;'>\n"
        message += f"<th>基金代码</th>\n"
        message += f"<th>基金名称</th>\n"
        message += f"<th>今日收益率</th>\n"
        message += f"<th>昨日收益率</th>\n"
        message += f"<th>趋势状态</th>\n"
        message += f"<th>操作建议</th>\n"
        message += f"<th>执行金额</th>\n"
        message += f"</tr>\n"
        message += f"</thead>\n"
        message += f"<tbody>\n"
        
        for _, row in df_display.iterrows():
            message += f"<tr>\n"
            message += f"<td>{row['fund_code']}</td>\n"
            message += f"<td>{row['fund_name']}</td>\n"
            message += f"<td>{row['today_return']}</td>\n"
            message += f"<td>{row['prev_day_return']}</td>\n"
            message += f"<td>{row['status_label']}</td>\n"
            message += f"<td>{row['operation_suggestion']}</td>\n"
            message += f"<td>{row['execution_amount']}</td>\n"
            message += f"</tr>\n"
        
        message += f"</tbody>\n"
        message += f"</table>\n"
    
    message += f"<p style='margin-top: 15px; color: #666; font-size: 14px;'>"
    message += f"<strong>提示</strong>：以上分析基于实时估值数据，仅供参考。最终投资决策请结合市场情况谨慎考虑。"
    message += f"</p>"
    
    return message

# 定义生成组合报告的函数
def generate_combined_report(regular_df, performance_df):
    """
    将持仓基金收益率变化分析和基金绩效对比分析结合到一个HTML邮件中
    
    参数：
    regular_df: 常规基金分析结果的DataFrame
    performance_df: 基金绩效分析结果的DataFrame
    
    返回：
    str: 格式化的HTML邮件内容
    """
    from datetime import date
    
    # 创建副本用于格式化显示
    regular_display = regular_df.copy()
    performance_display = performance_df.copy()
    
    # 生成HTML消息
    message = f"<h2>📊 基金综合分析报告 - {date.today().strftime('%Y年%m月%d日')}</h2>\n"
    
    # =================== 第一部分：持仓基金收益率变化分析 ===================
    message += f"<h3>一、持仓基金收益率变化分析</h3>\n"
    
    # 格式化收益率为百分比
    regular_display['today_return'] = regular_display['today_return'].map('{:.2f}%'.format)
    regular_display['prev_day_return'] = regular_display['prev_day_return'].map('{:.2f}%'.format)
    regular_display['comparison_value'] = regular_display['comparison_value'].map('{:.2f}%'.format)
    
    # 按照操作建议和执行金额排序
    regular_display = regular_display.sort_values(by=['operation_suggestion', 'execution_amount'])
    
    # 生成常规分析表格
    message += f"<table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse; width: 100%; margin-bottom: 30px;'>\n"
    message += f"<thead>\n"
    message += f"<tr style='background-color: #f0f0f0;'>\n"
    message += f"<th>基金代码</th>\n"
    message += f"<th>基金名称</th>\n"
    message += f"<th>今日收益率</th>\n"
    message += f"<th>昨日收益率</th>\n"
    message += f"<th>趋势状态</th>\n"
    message += f"<th>操作建议</th>\n"
    message += f"<th>执行金额</th>\n"
    message += f"</tr>\n"
    message += f"</thead>\n"
    message += f"<tbody>\n"
    
    for _, row in regular_display.iterrows():
        message += f"<tr>\n"
        message += f"<td>{row['fund_code']}</td>\n"
        message += f"<td>{row['fund_name']}</td>\n"
        message += f"<td>{row['today_return']}</td>\n"
        message += f"<td>{row['prev_day_return']}</td>\n"
        message += f"<td>{row['status_label']}</td>\n"
        message += f"<td>{row['operation_suggestion']}</td>\n"
        message += f"<td>{row['execution_amount']}</td>\n"
        message += f"</tr>\n"
    
    message += f"</tbody>\n"
    message += f"</table>\n"
    
    # =================== 第二部分：基金绩效对比分析 ===================
    message += f"<h3>二、基金绩效对比分析</h3>\n"
    
    # 格式化收益率为百分比
    performance_display['yesterday_return'] = performance_display['yesterday_return'].map('{:.2f}%'.format)
    performance_display['today_return'] = performance_display['today_return'].map('{:.2f}%'.format)
    performance_display['return_change'] = performance_display['return_change'].map('{:.2f}%'.format)
    performance_display['annualized_return'] = (performance_display['annualized_return'] * 100).map('{:.2f}%'.format)
    performance_display['max_drawdown'] = (performance_display['max_drawdown'] * 100).map('{:.2f}%'.format)
    performance_display['sharpe_ratio'] = performance_display['sharpe_ratio'].map('{:.2f}'.format)
    
    # 生成绩效分析表格
    message += f"<table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse; width: 100%;'>\n"
    message += f"<thead>\n"
    message += f"<tr style='background-color: #f0f0f0;'>\n"
    message += f"<th>基金代码</th>\n"
    message += f"<th>基金名称</th>\n"
    message += f"<th>昨日收益率</th>\n"
    message += f"<th>今日收益率</th>\n"
    message += f"<th>收益率变化</th>\n"
    message += f"<th>年化收益率</th>\n"
    message += f"<th>最大回撤</th>\n"
    message += f"<th>Sharpe比率</th>\n"
    message += f"</tr>\n"
    message += f"</thead>\n"
    message += f"<tbody>\n"
    
    for _, row in performance_display.iterrows():
        message += f"<tr>\n"
        message += f"<td>{row['fund_code']}</td>\n"
        message += f"<td>{row['fund_name']}</td>\n"
        message += f"<td>{row['yesterday_return']}</td>\n"
        message += f"<td>{row['today_return']}</td>\n"
        message += f"<td>{row['return_change']}</td>\n"
        message += f"<td>{row['annualized_return']}</td>\n"
        message += f"<td>{row['max_drawdown']}</td>\n"
        message += f"<td>{row['sharpe_ratio']}</td>\n"
        message += f"</tr>\n"
    
    message += f"</tbody>\n"
    message += f"</table>\n"
    
    # 共同的提示信息
    message += f"<p style='margin-top: 20px; color: #666; font-size: 14px;'>"
    message += f"<strong>提示</strong>：以上分析基于实时估值数据，仅供参考。最终投资决策请结合市场情况谨慎考虑。"
    message += f"</p>"
    
    return message

# 定义发送通知的函数
def send_notification(token, message, title="基金分析报告", send_wechat=True, send_email=True, email_channel="mail"):
    """
    通过PushPlus服务发送通知（微信和邮件）
    
    参数：
    token: PushPlus的token
    message: 要发送的消息内容
    title: 消息标题（默认：基金分析报告）
    send_wechat: 是否发送微信通知（默认：True）
    send_email: 是否发送邮件通知（默认：True）
    email_channel: 邮件发送通道（默认：mail）
    """
    try:
        import requests
        
        # 发送微信通知
        if send_wechat:
            print("正在发送微信通知...")
            template = 'html'
            url = f"https://www.pushplus.plus/send?token={token}&title={title}&content={message}&template={template}"
            response = requests.get(url)
            if response.status_code == 200 and response.json().get('code') == 200:
                print("微信通知发送成功")
            else:
                print(f"微信通知发送失败: {response.text}")
        
        # 发送邮件通知
        if send_email:
            print("正在发送邮件通知...")
            url = f"http://www.pushplus.plus/send/{token}"
            headers = {'Content-Type': 'application/json'}
            data = {
                "token": token,
                "title": title,
                "content": message,
                "channel": email_channel,
                "option": ""
            }
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200 and response.json().get('code') == 200:
                print("邮件通知发送成功")
            else:
                print(f"邮件通知发送失败: {response.text}")
    except Exception as e:
        print(f"发送通知时出错: {str(e)}")

# 定义基金投资策略函数
def get_investment_strategy(today_return, prev_day_return):
    """
    根据当日收益率和前一日收益率，返回投资策略结果
    
    参数：
    today_return: 当日收益率（%）
    prev_day_return: 前一日收益率（%）
    
    返回：
    tuple: (status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, execution_amount, buy_multiplier)
    """
    return_diff = today_return - prev_day_return
    
    # 1. 今日>0 昨日>0 today-prev>1%
    if today_return > 0 and prev_day_return > 0:
        if return_diff > 1:
            status_label = "🟢 **大涨**"
            is_buy = False
            redeem_amount = 0
            buy_multiplier = 0
            operation_suggestion = "不买入，不赎回"
            execution_amount = "持有不动"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        # 2. 今日>0 昨日>0 0<today-prev≤1%
        elif 0 < return_diff <= 1:
            status_label = "🟡 **连涨加速**"
            is_buy = False
            redeem_amount = 15
            buy_multiplier = 0
            operation_suggestion = "不买入，赎回15元"
            execution_amount = "赎回¥15"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        # 3. 今日>0 昨日>0 -1%≤today-prev≤0
        elif -1 <= return_diff <= 0:
            status_label = "🟠 **连涨放缓**"
            is_buy = False
            redeem_amount = 0
            buy_multiplier = 0
            operation_suggestion = "不买入，不赎回"
            execution_amount = "持有不动"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        # 4. 今日>0 昨日>0 today-prev<-1%
        elif return_diff < -1:
            status_label = "🟠 **连涨回落**"
            is_buy = False
            redeem_amount = 0
            buy_multiplier = 0
            operation_suggestion = "不买入，不赎回"
            execution_amount = "持有不动"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
    
    # 5. 今日>0 昨日≤0
    elif today_return > 0 and prev_day_return <= 0:
        status_label = "🔵 **反转涨**"
        is_buy = True
        redeem_amount = 0
        buy_multiplier = 1.5
        operation_suggestion = "定投买入，不赎回"
        execution_amount = f"买入{buy_multiplier}×定额"
        return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
    
    # 6. 今日=0 昨日>0
    elif today_return == 0 and prev_day_return > 0:
        status_label = "🔴 **转势休整**"
        is_buy = False
        redeem_amount = 30
        buy_multiplier = 0
        operation_suggestion = "不买入，赎回30元"
        execution_amount = "赎回¥30"
        return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
    
    # 7. 今日<0 昨日>0
    elif today_return < 0 and prev_day_return > 0:
        status_label = "🔴 **反转跌**"
        is_buy = False
        redeem_amount = 30
        buy_multiplier = 0
        operation_suggestion = "不买入，赎回30元"
        execution_amount = "赎回¥30"
        return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
    
    # 8. 今日=0 昨日≤0
    elif today_return == 0 and prev_day_return <= 0:
        status_label = "⚪ **绝对企稳**"
        is_buy = True
        redeem_amount = 0
        buy_multiplier = 3.0
        operation_suggestion = "定投买入，不赎回"
        execution_amount = f"买入{buy_multiplier}×定额"
        return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
    
    # 9. 今日<0 昨日=0 today≤-2%
    elif today_return < 0 and prev_day_return == 0:
        if today_return <= -2:
            status_label = "🔴 **首次大跌**"
            is_buy = True
            redeem_amount = 0
            buy_multiplier = 2.0
            operation_suggestion = "定投买入，不赎回"
            execution_amount = f"买入{buy_multiplier}×定额"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        # 10. 今日<0 昨日=0 -2%<today≤-0.5%
        elif -2 < today_return <= -0.5:
            status_label = "🟠 **首次下跌**"
            is_buy = True
            redeem_amount = 0
            buy_multiplier = 1.5
            operation_suggestion = "定投买入，不赎回"
            execution_amount = f"买入{buy_multiplier}×定额"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        # 11. 今日<0 昨日=0 today>-0.5%
        elif today_return > -0.5:
            status_label = "🔵 **微跌试探**"
            is_buy = True
            redeem_amount = 0
            buy_multiplier = 1.0
            operation_suggestion = "定投买入，不赎回"
            execution_amount = f"买入{buy_multiplier}×定额"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
    
    # 12. 今日<0 昨日<0 (today-prev)>1% & today≤-2%
    elif today_return < 0 and prev_day_return < 0:
        if return_diff > 1 and today_return <= -2:
            status_label = "🔴 **暴跌加速**"
            is_buy = True
            redeem_amount = 0
            buy_multiplier = 0.5
            operation_suggestion = "定投买入，不赎回"
            execution_amount = f"买入{buy_multiplier}×定额"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        # 13. 今日<0 昨日<0 (today-prev)>1% & today>-2%
        elif return_diff > 1 and today_return > -2:
            status_label = "🟣 **跌速扩大**"
            is_buy = True
            redeem_amount = 0
            buy_multiplier = 1.0
            operation_suggestion = "定投买入，不赎回"
            execution_amount = f"买入{buy_multiplier}×定额"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        # 14. 今日<0 昨日<0 (prev-today)>0 & prev≤-2%
        elif (prev_day_return - today_return) > 0 and prev_day_return <= -2:
            status_label = "🔵 **暴跌回升**"
            is_buy = True
            redeem_amount = 0
            buy_multiplier = 1.5
            operation_suggestion = "定投买入，不赎回"
            execution_amount = f"买入{buy_multiplier}×定额"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        # 15. 今日<0 昨日<0 (prev-today)>0 & prev>-2%
        elif (prev_day_return - today_return) > 0 and prev_day_return > -2:
            status_label = "🟦 **跌速放缓**"
            is_buy = True
            redeem_amount = 0
            buy_multiplier = 1.0
            operation_suggestion = "定投买入，不赎回"
            execution_amount = f"买入{buy_multiplier}×定额"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        # 16. 今日<0 昨日<0 abs差值≤1%
        elif abs(return_diff) <= 1:
            status_label = "🟣 **阴跌筑底**"
            is_buy = True
            redeem_amount = 0
            buy_multiplier = 1.0
            operation_suggestion = "定投买入，不赎回"
            execution_amount = f"买入{buy_multiplier}×定额"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
    
    # 默认情况（不应该发生）
    status_label = "🔴 **未知**"
    is_buy = False
    redeem_amount = 0
    buy_multiplier = 0
    operation_suggestion = "不买入，不赎回"
    execution_amount = "持有不动"
    return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier

# 定义基金分析函数
def analyze_funds():
    """
    分析所有持仓基金的收益率变化，并发送通知
    """
    print("\n分析所有持仓基金的收益率变化：")
    
    from fund_realtime import FundRealTime
    import akshare as ak  # 重新引入akshare用于获取前一日收益率
    import pandas as pd
    
    try:
        # 读取京东金融Excel文件中的持仓数据表
        file_path = "d:/codes/py4zinia/京东金融.xlsx"
        # 只读取名为'持仓数据'的工作表
        position_data = pd.read_excel(file_path, sheet_name='持仓数据')

        # 获取持仓数据中的基金代码，并确保为6位数字格式
        fund_codes = position_data['代码'].apply(lambda x: str(int(x)).zfill(6) if pd.notna(x) else '').tolist()
        # 过滤空字符串
        fund_codes = [code for code in fund_codes if code]

        # 批量获取所有持仓基金的实时数据
        all_fund_data = FundRealTime.get_realtime_batch(fund_codes)

        if all_fund_data.empty:
            print("Failed to get real-time data for any funds")
            return
            
        all_funds = []  # Store all fund data, including those that meet and don't meet the conditions

        print(f"Analyzing {len(all_fund_data)} held funds...")

        for idx, row in all_fund_data.iterrows():
            # Get fund data from FundRealTime
            fund_code = row['fund_code']
            fund_name = row['fund_name']
            yesterday_nav = float(row['yesterday_nav'])  # Yesterday NAV
            current_estimate = float(row['current_estimate'])  # Current estimate
            estimate_change_pct = float(row['change_percentage'])  # Estimated change percentage

            if yesterday_nav != 0:
                # Calculate today's return rate: (Current estimate - Yesterday NAV) / Yesterday NAV * 100
                today_return = (current_estimate - yesterday_nav) / yesterday_nav * 100

                # Get previous day's actual return rate (using akshare)
                try:
                    # Use akshare to get fund historical NAV data
                    fund_hist = ak.fund_open_fund_info_em(symbol=fund_code, indicator='单位净值走势')
                    if not fund_hist.empty:
                        # Sort by date to ensure latest data is first
                        fund_hist = fund_hist.sort_values('净值日期', ascending=False)
                        # Get previous day's actual return rate
                        prev_day_return = float(fund_hist.iloc[0]['日增长率'])
                    else:
                        # 如果无法获取历史数据，尝试使用其他数据源
                        print(f"  基金 {fund_code} ({fund_name}) 无法从fund_open_fund_info_em获取历史数据，尝试使用其他数据源")
                        
                        # 尝试使用fund_etf_spot_em获取ETF数据
                        try:
                            etf_data = ak.fund_etf_spot_em()
                            etf_fund = etf_data[etf_data['代码'] == fund_code]
                            if not etf_fund.empty:
                                print(f"  基金 {fund_code} ({fund_name}) 是ETF，从fund_etf_spot_em获取数据")
                                # ETF数据可能没有历史增长率，使用估算值
                                prev_day_return = estimate_change_pct
                            else:
                                # 尝试使用fund_info_em获取基金基本信息
                                try:
                                    fund_info = ak.fund_info_em(fund_code)
                                    print(f"  基金 {fund_code} ({fund_name}) 从fund_info_em获取到基本信息")
                                    # 基本信息可能没有增长率，使用估算值
                                    prev_day_return = estimate_change_pct
                                except Exception as e:
                                    print(f"  基金 {fund_code} ({fund_name}) 从fund_info_em获取数据失败: {str(e)}")
                                    prev_day_return = estimate_change_pct
                        except Exception as e:
                            print(f"  基金 {fund_code} ({fund_name}) 尝试其他数据源失败: {str(e)}")
                            prev_day_return = estimate_change_pct
                except Exception as e:
                    # 如果获取历史数据失败，使用估算值
                    print(f"  基金 {fund_code} ({fund_name}) 获取历史数据失败: {str(e)}，使用估算值")
                    prev_day_return = estimate_change_pct
                
                # 应用投资策略
                status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, execution_amount, buy_multiplier = get_investment_strategy(today_return, prev_day_return)
                
                # 将所有基金数据添加到列表，包括投资策略结果
                all_funds.append({
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'yesterday_nav': yesterday_nav,
                    'current_estimate': current_estimate,
                    'today_return': today_return,
                    'prev_day_return': prev_day_return,
                    'status_label': status_label,
                    'is_buy': is_buy,
                    'redeem_amount': redeem_amount,
                    'comparison_value': comparison_value,
                    'operation_suggestion': operation_suggestion,
                    'execution_amount': execution_amount,
                    'buy_multiplier': buy_multiplier,
                    'analysis_date': date.today()  # 添加分析日期
                })
            else:
                print(f"  基金 {fund_code} ({fund_name}) 昨日净值为0，无法计算")

        # 显示所有基金数据
        if not all_funds:
            print("\n未获取到基金数据")
            return
            
        print(f"\n共分析 {len(all_funds)} 只基金:")
        result_df = pd.DataFrame(all_funds)
        # 保存原始浮点数格式的副本用于数据库保存
        result_df_db = result_df.copy()
        # 显示与表格模板一致的列
        display_columns = ['fund_code', 'fund_name', 'today_return', 'prev_day_return', 'status_label', 'operation_suggestion', 'execution_amount']
        # 格式化收益率为百分比用于显示
        result_df['today_return'] = result_df['today_return'].map('{:.2f}%'.format)
        result_df['prev_day_return'] = result_df['prev_day_return'].map('{:.2f}%'.format)
        print(result_df[display_columns])

        # 新增：将结果保存到MySQL数据库
        try:
            import pymysql
            from sqlalchemy import create_engine
            import warnings
            warnings.filterwarnings('ignore', category=pymysql.Warning)

            # 数据库连接信息（用户需要根据自己的MySQL配置修改）
            db_config = {
                'host': 'localhost',      # 数据库主机地址
                'user': 'root',           # 数据库用户名
                'password': 'root',  # 数据库密码
                'database': 'fund_analysis',  # 数据库名
                'port': 3306,             # 端口号
                'charset': 'utf8mb4'      # 字符编码
            }

            # 微信通知配置（用户需要根据自己的PushPlus配置修改）
            # 请在下面设置正确的PushPlus token
            wechat_config = {
                'enabled': True,  # 是否启用微信通知功能
                'token': 'fb0dfd5592ed4eb19cd886d737b6cc6a'  # PushPlus的token
            }

            # 检查是否 still using default configuration
            if db_config['password'] == 'root':
                print("\n注意：当前使用默认密码配置，尝试连接数据库...")
                
            # Create database connection regardless of password
            connection_string = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}?charset={db_config['charset']}"
            engine = create_engine(connection_string)

            
            # 将结果保存到数据库表中 - 使用upsert操作避免重复记录
            from sqlalchemy.types import String, Float, Boolean, DECIMAL, Date
            
            # 定义所有列的数据类型，包括新添加的analysis_date和buy_multiplier
            dtype = {
                'fund_code': String(20),
                'fund_name': String(100),
                'yesterday_nav': Float,
                'current_estimate': Float,
                'today_return': Float,
                'prev_day_return': Float,
                'status_label': String(50),
                'is_buy': Boolean,
                'redeem_amount': DECIMAL(10, 2),
                'comparison_value': Float,
                'operation_suggestion': String(100),
                'execution_amount': String(20),
                'analysis_date': Date,
                'buy_multiplier': Float
            }
            
            # 使用临时表方式实现upsert
            temp_table = 'fund_analysis_temp'
            
            # 1. 创建临时表并插入数据
            result_df_db.to_sql(
                name=temp_table,
                con=engine,
                if_exists='replace',
                index=False,
                dtype=dtype
            )
            
            # 2. 使用INSERT ... ON DUPLICATE KEY UPDATE实现upsert
            try:
                # 连接数据库执行SQL
                conn = pymysql.connect(**db_config)
                cursor = conn.cursor()
                
                # 构建upsert SQL语句
                upsert_sql = """
                INSERT INTO fund_analysis_results (
                    fund_code, fund_name, yesterday_nav, current_estimate, today_return, prev_day_return, 
                    status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, execution_amount, analysis_date, buy_multiplier
                ) SELECT 
                    fund_code, fund_name, yesterday_nav, current_estimate, today_return, prev_day_return, 
                    status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, execution_amount, analysis_date, buy_multiplier
                FROM %s
                ON DUPLICATE KEY UPDATE
                    fund_name = VALUES(fund_name),
                    yesterday_nav = VALUES(yesterday_nav),
                    current_estimate = VALUES(current_estimate),
                    today_return = VALUES(today_return),
                    prev_day_return = VALUES(prev_day_return),
                    status_label = VALUES(status_label),
                    is_buy = VALUES(is_buy),
                    redeem_amount = VALUES(redeem_amount),
                    comparison_value = VALUES(comparison_value),
                    operation_suggestion = VALUES(operation_suggestion),
                    execution_amount = VALUES(execution_amount),
                    buy_multiplier = VALUES(buy_multiplier)
                """ % temp_table
                
                cursor.execute(upsert_sql)
                conn.commit()
                
                # 3. 删除临时表
                cursor.execute(f"DROP TABLE IF EXISTS {temp_table}")
                conn.commit()
                
                cursor.close()
                conn.close()
                
            except Exception as e:
                print(f"执行upsert操作时出错: {str(e)}")
                # 如果upsert失败，尝试使用原始的append方式（虽然可能产生重复）
                result_df_db.to_sql(
                    name='fund_analysis_results',
                    con=engine,
                    if_exists='append',
                    index=False,
                    dtype=dtype
                )

            print("\n结果已成功保存到MySQL数据库")

            # 新增：发送通知（微信和邮件）
            if wechat_config['enabled']:
                print("\n正在发送通知...")
                try:
                    # 生成通知消息
                    notification_message = generate_wechat_message(result_df_db)
                    # 发送通知（微信和邮件）
                    send_notification(wechat_config['token'], notification_message)
                except Exception as e:
                    print(f"发送通知时出错: {str(e)}")
            else:
                print("\n通知功能未启用，请在配置中设置enabled为True")

            return result_df_db

        except ImportError:
            print("\n缺少必要的数据库依赖包，请安装: pip install PyMySQL sqlalchemy requests")
            return None
        except Exception as e:
            print(f"\n保存到数据库时出错: {str(e)}")
            print("请检查数据库连接配置是否正确")
            print("请确保MySQL服务已启动，并且用户名密码正确")
            return None
            
    except Exception as e:
        print(f"\n分析基金收益率时出错: {str(e)}")
        return None

# 定义基金绩效对比函数
def compare_fund_performance():
    """
    对比前一天和今天的基金绩效变化
    
    返回：
    DataFrame: 包含基金代码、名称、昨日收益率、今日收益率、变化值的对比数据
    """
    print("\n开始基金绩效对比分析...")
    
    try:
        import pandas as pd
        import pymysql
        from sqlalchemy import create_engine
        from datetime import date, timedelta
        import warnings
        warnings.filterwarnings('ignore', category=pymysql.Warning)
        
        # 数据库连接信息（与analyze_funds函数保持一致）
        db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': 'root',
            'database': 'fund_analysis',
            'port': 3306,
            'charset': 'utf8mb4'
        }
        
        # 创建数据库连接
        connection_string = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}?charset={db_config['charset']}"
        engine = create_engine(connection_string)
        
        # 获取今日和昨日日期
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        print(f"对比日期：昨天({yesterday}) vs 今天({today})")
        
        # 从Excel文件中获取基金代码列表
        try:
            file_path = "d:/codes/py4zinia/京东金融.xlsx"
            position_data = pd.read_excel(file_path, sheet_name='持仓数据')
            excel_fund_codes = position_data['代码'].apply(lambda x: str(int(x)).zfill(6) if pd.notna(x) else '').tolist()
            excel_fund_codes = [code for code in excel_fund_codes if code]
            print(f"从京东金融.xlsx中获取到 {len(excel_fund_codes)} 只基金用于绩效对比分析")
        except Exception as e:
            print(f"读取Excel文件失败: {str(e)}")
            excel_fund_codes = []
        
        # 查询今日和昨日的基金数据，只查询Excel文件中存在的基金
        if excel_fund_codes:
            fund_codes_str = "','"
            fund_codes_clause = f"AND fund_code IN ('{fund_codes_str.join(excel_fund_codes)}')"
        else:
            fund_codes_clause = ""
        
        query = f"""
        SELECT * FROM fund_analysis_results 
        WHERE analysis_date IN ('{yesterday}', '{today}')
        {fund_codes_clause}
        ORDER BY fund_code, analysis_date
        """
        
        df = pd.read_sql(query, engine)
        
        if df.empty:
            print("未找到足够的数据进行对比")
            return None
        
        # 按基金代码分组
        fund_groups = df.groupby('fund_code')
        
        comparison_results = []
        
        for fund_code, group in fund_groups:
            if len(group) < 2:
                print(f"基金 {fund_code} 缺少完整的历史数据，尝试从其他数据源获取")
                
                # 尝试从FundRealTime获取实时数据
                try:
                    from fund_realtime import FundRealTime
                    fund_data = FundRealTime.get_realtime_nav(fund_code)
                    if fund_data:
                        print(f"  基金 {fund_code} ({fund_data['name']}) 从FundRealTime获取到实时数据")
                        # 由于我们需要昨天和今天的数据，而这里只能获取实时数据，所以仍然无法进行对比
                        # 但至少我们知道了基金的名称
                        continue
                    else:
                        print(f"  基金 {fund_code} 无法从FundRealTime获取数据")
                except Exception as e:
                    print(f"  基金 {fund_code} 尝试从FundRealTime获取数据失败: {str(e)}")
                
                # 尝试从akshare获取基金基本信息
                try:
                    import akshare as ak
                    fund_info = ak.fund_info_em(fund_code)
                    print(f"  基金 {fund_code} 从fund_info_em获取到基本信息")
                except Exception as e:
                    print(f"  基金 {fund_code} 尝试从fund_info_em获取数据失败: {str(e)}")
                
                continue
                
            # 按日期排序
            sorted_group = group.sort_values('analysis_date')
            
            # 获取昨日和今日数据
            yesterday_data = sorted_group.iloc[0]
            today_data = sorted_group.iloc[1]
            
            # 计算变化值
            return_change = today_data['today_return'] - yesterday_data['today_return']
            
            comparison_results.append({
                'fund_code': fund_code,
                'fund_name': today_data['fund_name'],
                'yesterday_return': yesterday_data['today_return'],
                'today_return': today_data['today_return'],
                'return_change': return_change,
                'yesterday_status': yesterday_data['status_label'],
                'today_status': today_data['status_label'],
                'yesterday_operation': yesterday_data['operation_suggestion'],
                'today_operation': today_data['operation_suggestion']
            })
        
        if not comparison_results:
            print("没有足够的基金数据进行完整对比")
            return None
        
        comparison_df = pd.DataFrame(comparison_results)
        
        # 格式化显示
        print("\n基金绩效对比结果：")
        display_columns = ['fund_code', 'fund_name', 'yesterday_return', 'today_return', 'return_change', 'yesterday_status', 'today_status']
        display_df = comparison_df.copy()
        display_df['yesterday_return'] = display_df['yesterday_return'].map('{:.2f}%'.format)
        display_df['today_return'] = display_df['today_return'].map('{:.2f}%'.format)
        display_df['return_change'] = display_df['return_change'].map('{:.2f}%'.format)
        print(display_df[display_columns])
        
        # 生成可视化图表
        plot_performance_comparison(comparison_df)
        
        return comparison_df
        
    except ImportError:
        print("缺少必要的依赖包，请安装: pip install PyMySQL sqlalchemy pandas")
        return None
    except Exception as e:
        print(f"进行基金绩效对比时出错: {str(e)}")
        return None

# 定义可视化函数
def plot_performance_comparison(comparison_df):
    """
    使用matplotlib创建基金绩效对比图表 - 按指标维度生成多个图表
    
    参数：
    comparison_df: 包含基金绩效对比数据的DataFrame
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        from datetime import date
        import os
        
        # 配置matplotlib为非交互式模式
        plt.switch_backend('Agg')
        
        # 设置中文显示
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 获取今天的日期
        today = date.today()
        today_str = today.strftime('%Y%m%d')
        
        # 检查数据中是否包含绩效指标
        has_performance_metrics = all(col in comparison_df.columns for col in ['annualized_return', 'max_drawdown', 'sharpe_ratio'])
        
        if has_performance_metrics:
            # 生成多个按指标分类的图表
            plot_daily_returns_comparison(comparison_df, today_str)
            plot_annualized_returns(comparison_df, today_str)
            plot_max_drawdown(comparison_df, today_str)
            plot_sharpe_ratio(comparison_df, today_str)
            plot_volatility(comparison_df, today_str)
        else:
            # 如果没有绩效指标，只生成日收益率对比图
            plot_daily_returns_comparison(comparison_df, today_str)
        
        print(f"已生成所有相关图表")
        
    except ImportError:
        print("缺少matplotlib依赖包，请安装: pip install matplotlib")
    except Exception as e:
        print(f"生成可视化图表时出错: {str(e)}")


def plot_daily_returns_comparison(comparison_df, today_str):
    """
    绘制日收益率对比图表
    
    参数：
    comparison_df: 包含基金绩效对比数据的DataFrame
    today_str: 今天的日期字符串
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        from datetime import date, timedelta
        
        # 设置中文显示
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 检查必要的列是否存在
        required_cols = ['yesterday_return', 'today_return', 'return_change']
        has_required_cols = all(col in comparison_df.columns for col in required_cols)
        
        if has_required_cols:
            # 获取今日和昨日日期
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            # 创建图表
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [2, 1]})
            fig.suptitle(f'基金日收益率对比分析\n昨天({yesterday}) vs 今天({today})', fontsize=16, fontweight='bold')
            
            # 1. 柱状图对比昨日和今日收益率
            n_funds = len(comparison_df)
            indices = np.arange(n_funds)
            width = 0.35
            
            ax1.bar(indices - width/2, comparison_df['yesterday_return'], width, label=f'昨日({yesterday})', alpha=0.8, color='#1f77b4')
            ax1.bar(indices + width/2, comparison_df['today_return'], width, label=f'今日({today})', alpha=0.8, color='#ff7f0e')
            
            # 设置柱状图标签
            ax1.set_ylabel('收益率 (%)')
            ax1.set_title('基金每日收益率对比', fontweight='bold')
            ax1.set_xticks(indices)
            ax1.set_xticklabels(comparison_df['fund_code'], rotation=45, ha='right')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 在柱子上添加数值标签
            for i, (yesterday_val, today_val) in enumerate(zip(comparison_df['yesterday_return'], comparison_df['today_return'])):
                ax1.text(i - width/2, yesterday_val + 0.05 * abs(yesterday_val), f'{yesterday_val:.2f}%', ha='center', va='bottom', fontsize=9)
                ax1.text(i + width/2, today_val + 0.05 * abs(today_val), f'{today_val:.2f}%', ha='center', va='bottom', fontsize=9)
            
            # 2. 折线图显示收益率变化值
            ax2.plot(indices, comparison_df['return_change'], marker='o', linewidth=2, markersize=8, color='#2ca02c')
            
            # 添加零基准线
            ax2.axhline(y=0, color='black', linestyle='--', alpha=0.3)
            
            # 设置折线图标签
            ax2.set_ylabel('收益率变化 (%)')
            ax2.set_title('基金收益率变化趋势', fontweight='bold')
            ax2.set_xticks(indices)
            ax2.set_xticklabels(comparison_df['fund_code'], rotation=45, ha='right')
            ax2.grid(True, alpha=0.3)
            
            # 在点上添加数值标签
            for i, val in enumerate(comparison_df['return_change']):
                ax2.text(i, val + 0.05 * abs(val), f'{val:.2f}%', ha='center', va='bottom', fontsize=9)
            
            # 3. 添加基金名称注释
            fund_names = comparison_df['fund_name'].tolist()
            fund_codes = comparison_df['fund_code'].tolist()
            
            # 计算图例位置，使其更整齐
            legend_start_y = 0.9
            for i, (code, name) in enumerate(zip(fund_codes, fund_names)):
                ax1.text(1.02, legend_start_y - i*0.06, f'{code}: {name}', 
                         transform=ax1.transAxes, ha='left', va='top', fontsize=9)
            
            # 添加图例标题
            ax1.text(1.02, legend_start_y + 0.03, '基金名称:', transform=ax1.transAxes, 
                     fontweight='bold', ha='left', va='bottom')
            
            # 调整布局
            plt.tight_layout(rect=[0, 0, 0.85, 1])
            
            # 保存图表为文件
            chart_path = f"基金日收益率对比_{today_str}.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"日收益率对比图表已保存为: {chart_path}")
        else:
            # 如果缺少特定列，则绘制简单的日收益率图
            # 检查是否有'daily_return'列
            if 'daily_return' in comparison_df.columns:
                fig, ax = plt.subplots(figsize=(12, 8))
                
                # 准备数据
                n_funds = len(comparison_df)
                indices = np.arange(n_funds)
                
                # 绘制柱状图
                bars = ax.bar(indices, comparison_df['daily_return'] * 100, alpha=0.8, color='#1f77b4')
                
                # 设置图表属性
                ax.set_xlabel('基金代码')
                ax.set_ylabel('日收益率 (%)')
                ax.set_title('基金日收益率对比', fontweight='bold', fontsize=14)
                ax.set_xticks(indices)
                ax.set_xticklabels(comparison_df['fund_code'], rotation=45, ha='right')
                ax.grid(True, alpha=0.3, axis='y')
                
                # 在柱子上添加数值标签
                for bar, value in zip(bars, comparison_df['daily_return'] * 100):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.05 * abs(height),
                            f'{value:.2f}%', ha='center', va='bottom', fontsize=9)
                
                # 添加基金名称注释
                fund_names = comparison_df['fund_name'].tolist()
                fund_codes = comparison_df['fund_code'].tolist()
                
                # 计算图例位置，使其更整齐
                legend_start_y = 0.9
                for i, (code, name) in enumerate(zip(fund_codes, fund_names)):
                    ax.text(1.02, legend_start_y - i*0.06, f'{code}: {name}', 
                            transform=ax.transAxes, ha='left', va='top', fontsize=9)
                
                # 添加图例标题
                ax.text(1.02, legend_start_y + 0.03, '基金名称:', transform=ax.transAxes, 
                        fontweight='bold', ha='left', va='bottom')
                
                # 调整布局
                plt.tight_layout(rect=[0, 0, 0.85, 1])
                
                # 保存图表
                chart_path = f"基金日收益率对比_{today_str}.png"
                plt.savefig(chart_path, dpi=300, bbox_inches='tight')
                plt.close()
                print(f"日收益率对比图表已保存为: {chart_path}")
            else:
                print("数据中没有找到收益率相关的列，无法生成日收益率对比图表")
        
    except Exception as e:
        print(f"生成日收益率对比图表时出错: {str(e)}")


def plot_annualized_returns(comparison_df, today_str):
    """
    绘制年化收益率对比图表
    
    参数：
    comparison_df: 包含基金绩效对比数据的DataFrame
    today_str: 今天的日期字符串
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        
        # 设置中文显示
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 过滤掉年化收益率为空的数据
        valid_data = comparison_df.dropna(subset=['annualized_return'])
        if len(valid_data) == 0:
            print("没有有效的年化收益率数据")
            return
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 准备数据
        n_funds = len(valid_data)
        indices = np.arange(n_funds)
        
        # 绘制柱状图
        bars = ax.bar(indices, valid_data['annualized_return'] * 100, alpha=0.8, color='#2E8B57')
        
        # 设置图表属性
        ax.set_xlabel('基金代码')
        ax.set_ylabel('年化收益率 (%)')
        ax.set_title('基金年化收益率对比', fontweight='bold', fontsize=14)
        ax.set_xticks(indices)
        ax.set_xticklabels(valid_data['fund_code'], rotation=45, ha='right')
        ax.grid(True, alpha=0.3, axis='y')
        
        # 在柱子上添加数值标签
        for bar, value in zip(bars, valid_data['annualized_return'] * 100):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.05 * abs(height),
                    f'{value:.2f}%', ha='center', va='bottom', fontsize=9)
        
        # 添加基金名称注释
        fund_names = valid_data['fund_name'].tolist()
        fund_codes = valid_data['fund_code'].tolist()
        
        # 计算图例位置，使其更整齐
        legend_start_y = 0.9
        for i, (code, name) in enumerate(zip(fund_codes, fund_names)):
            ax.text(1.02, legend_start_y - i*0.06, f'{code}: {name}', 
                    transform=ax.transAxes, ha='left', va='top', fontsize=9)
        
        # 添加图例标题
        ax.text(1.02, legend_start_y + 0.03, '基金名称:', transform=ax.transAxes, 
                fontweight='bold', ha='left', va='bottom')
        
        # 调整布局
        plt.tight_layout(rect=[0, 0, 0.85, 1])
        
        # 保存图表
        chart_path = f"基金年化收益率对比_{today_str}.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"年化收益率对比图表已保存为: {chart_path}")
        
    except Exception as e:
        print(f"生成年化收益率对比图表时出错: {str(e)}")


def plot_max_drawdown(comparison_df, today_str):
    """
    绘制最大回撤对比图表
    
    参数：
    comparison_df: 包含基金绩效对比数据的DataFrame
    today_str: 今天的日期字符串
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        
        # 设置中文显示
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 过滤掉最大回撤为空的数据
        valid_data = comparison_df.dropna(subset=['max_drawdown'])
        if len(valid_data) == 0:
            print("没有有效的最大回撤数据")
            return
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 准备数据（转换为百分比，并取正值用于绘图，负值会在标签中体现）
        n_funds = len(valid_data)
        indices = np.arange(n_funds)
        drawdown_values = valid_data['max_drawdown'] * 100  # 转换为百分比
        
        # 绘制柱状图（使用正值，但保留原始值用于标签）
        colors = ['#FF6B6B' if x < 0 else '#4ECDC4' for x in drawdown_values]  # 红色表示负回撤，绿色表示正数（理论上不应该有正数）
        bars = ax.bar(indices, drawdown_values, alpha=0.8, color=colors)
        
        # 设置图表属性
        ax.set_xlabel('基金代码')
        ax.set_ylabel('最大回撤 (%)')
        ax.set_title('基金最大回撤对比', fontweight='bold', fontsize=14)
        ax.set_xticks(indices)
        ax.set_xticklabels(valid_data['fund_code'], rotation=45, ha='right')
        ax.grid(True, alpha=0.3, axis='y')
        
        # 添加零基准线
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # 在柱子上添加数值标签
        for bar, value in zip(bars, drawdown_values):
            height = bar.get_height()
            # 如果是负值，标签放在柱子上方；如果是正值，标签放在柱子下方
            if height < 0:
                ax.text(bar.get_x() + bar.get_width()/2., height - 0.05 * abs(height),
                        f'{value:.2f}%', ha='center', va='top', fontsize=9)
            else:
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.05 * abs(height),
                        f'{value:.2f}%', ha='center', va='bottom', fontsize=9)
        
        # 添加基金名称注释
        fund_names = valid_data['fund_name'].tolist()
        ax.text(1.02, 0.5, '基金名称:', transform=ax.transAxes, fontweight='bold', ha='left', va='center')
        for i, name in enumerate(fund_names):
            ax.text(1.02, 0.45 - i*0.05, f'{valid_data.iloc[i]["fund_code"]}: {name}', 
                    transform=ax.transAxes, ha='left', va='top')
        
        # 调整布局
        plt.tight_layout(rect=[0, 0, 0.85, 1])
        
        # 保存图表
        chart_path = f"基金最大回撤对比_{today_str}.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"最大回撤对比图表已保存为: {chart_path}")
        
    except Exception as e:
        print(f"生成最大回撤对比图表时出错: {str(e)}")


def plot_sharpe_ratio(comparison_df, today_str):
    """
    绘制夏普比率对比图表
    
    参数：
    comparison_df: 包含基金绩效对比数据的DataFrame
    today_str: 今天的日期字符串
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        
        # 设置中文显示
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 过滤掉夏普比率为空的数据
        valid_data = comparison_df.dropna(subset=['sharpe_ratio'])
        if len(valid_data) == 0:
            print("没有有效的夏普比率数据")
            return
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 准备数据
        n_funds = len(valid_data)
        indices = np.arange(n_funds)
        
        # 绘制柱状图
        ratios = valid_data['sharpe_ratio']
        colors = ['#98FB98' if x >= 0 else '#FFB6C1' for x in ratios]  # 绿色表示正比率，粉色表示负比率
        bars = ax.bar(indices, ratios, alpha=0.8, color=colors)
        
        # 设置图表属性
        ax.set_xlabel('基金代码')
        ax.set_ylabel('夏普比率')
        ax.set_title('基金夏普比率对比', fontweight='bold', fontsize=14)
        ax.set_xticks(indices)
        ax.set_xticklabels(valid_data['fund_code'], rotation=45, ha='right')
        ax.grid(True, alpha=0.3, axis='y')
        
        # 添加零基准线
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # 在柱子上添加数值标签
        for bar, value in zip(bars, ratios):
            height = bar.get_height()
            # 如果是负值，标签放在柱子上方；如果是正值，标签放在柱子下方
            if height < 0:
                ax.text(bar.get_x() + bar.get_width()/2., height - 0.05 * abs(height),
                        f'{value:.2f}', ha='center', va='top', fontsize=9)
            else:
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.05 * abs(height),
                        f'{value:.2f}', ha='center', va='bottom', fontsize=9)
        
        # 添加基金名称注释
        fund_names = valid_data['fund_name'].tolist()
        ax.text(1.02, 0.5, '基金名称:', transform=ax.transAxes, fontweight='bold', ha='left', va='center')
        for i, name in enumerate(fund_names):
            ax.text(1.02, 0.45 - i*0.05, f'{valid_data.iloc[i]["fund_code"]}: {name}', 
                    transform=ax.transAxes, ha='left', va='top')
        
        # 调整布局
        plt.tight_layout(rect=[0, 0, 0.85, 1])
        
        # 保存图表
        chart_path = f"基金夏普比率对比_{today_str}.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"夏普比率对比图表已保存为: {chart_path}")
        
    except Exception as e:
        print(f"生成夏普比率对比图表时出错: {str(e)}")


def plot_volatility(comparison_df, today_str):
    """
    绘制波动率对比图表
    
    参数：
    comparison_df: 包含基金绩效对比数据的DataFrame
    today_str: 今天的日期字符串
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        
        # 设置中文显示
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 过滤掉波动率为空的数据
        valid_data = comparison_df.dropna(subset=['volatility'])
        if len(valid_data) == 0:
            print("没有有效的波动率数据")
            return
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 准备数据
        n_funds = len(valid_data)
        indices = np.arange(n_funds)
        vol_values = valid_data['volatility'] * 100  # 转换为百分比
        
        # 绘制柱状图
        bars = ax.bar(indices, vol_values, alpha=0.8, color='#87CEEB')
        
        # 设置图表属性
        ax.set_xlabel('基金代码')
        ax.set_ylabel('波动率 (%)')
        ax.set_title('基金波动率对比', fontweight='bold', fontsize=14)
        ax.set_xticks(indices)
        ax.set_xticklabels(valid_data['fund_code'], rotation=45, ha='right')
        ax.grid(True, alpha=0.3, axis='y')
        
        # 在柱子上添加数值标签
        for bar, value in zip(bars, vol_values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.05 * abs(height),
                    f'{value:.2f}%', ha='center', va='bottom', fontsize=9)
        
        # 添加基金名称注释
        fund_names = valid_data['fund_name'].tolist()
        ax.text(1.02, 0.5, '基金名称:', transform=ax.transAxes, fontweight='bold', ha='left', va='center')
        for i, name in enumerate(fund_names):
            ax.text(1.02, 0.45 - i*0.05, f'{valid_data.iloc[i]["fund_code"]}: {name}', 
                    transform=ax.transAxes, ha='left', va='top')
        
        # 调整布局
        plt.tight_layout(rect=[0, 0, 0.85, 1])
        
        # 保存图表
        chart_path = f"基金波动率对比_{today_str}.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"波动率对比图表已保存为: {chart_path}")
        
    except Exception as e:
        print(f"生成波动率对比图表时出错: {str(e)}")

import math

# 定义获取基金历史数据并计算指标的函数
def get_fund_metrics(fund_code, fund_name):
    """
    获取基金历史数据并计算各种指标
    
    参数：
    fund_code: 基金代码
    fund_name: 基金名称
    
    返回：
    dict: 包含各种指标的字典
    """
    try:
        import akshare as ak
        import pandas as pd
        import math
        
        # 获取基金历史净值数据
        print(f"正在获取基金 {fund_code} ({fund_name}) 的历史数据...")
        
        # 使用正确的参数调用函数
        fund_data = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
        
        if fund_data.empty:
            print(f"基金 {fund_code} ({fund_name}) 无历史数据")
            return None
        
        # 处理数据
        fund_data['净值日期'] = pd.to_datetime(fund_data['净值日期'])
        fund_data = fund_data.sort_values('净值日期')
        
        # 检查是否有足够的数据点进行计算
        if len(fund_data) < 2:
            print(f"基金 {fund_code} ({fund_name}) 历史数据不足，无法计算指标")
            return None
        
        # 计算收益率
        fund_data['单位净值'] = pd.to_numeric(fund_data['单位净值'], errors='coerce')
        fund_data = fund_data.dropna(subset=['单位净值'])
        
        if len(fund_data) < 2:
            print(f"基金 {fund_code} ({fund_name}) 净值数据不足，无法计算指标")
            return None
        
        fund_data['returns'] = fund_data['单位净值'].pct_change()
        fund_data = fund_data.dropna(subset=['returns'])
        
        if len(fund_data) < 2:
            print(f"基金 {fund_code} ({fund_name}) 收益率数据不足，无法计算指标")
            return None
        
        # 计算年化收益（假设一年252个交易日）
        total_return = (fund_data['单位净值'].iloc[-1] / fund_data['单位净值'].iloc[0]) - 1
        days = (fund_data['净值日期'].iloc[-1] - fund_data['净值日期'].iloc[0]).days
        if days > 0:
            annualized_return = (1 + total_return) ** (365 / days) - 1
        else:
            annualized_return = 0
        
        # 计算最大回撤
        fund_data['cumulative_return'] = (1 + fund_data['returns']).cumprod()
        fund_data['cumulative_max'] = fund_data['cumulative_return'].cummax()
        fund_data['drawdown'] = (fund_data['cumulative_return'] / fund_data['cumulative_max']) - 1
        max_drawdown = fund_data['drawdown'].min()
        
        # 计算Sharpe比率（假设无风险利率为3%）
        risk_free_rate = 0.03
        daily_returns = fund_data['returns'].dropna()
        if len(daily_returns) > 0:
            mean_return = daily_returns.mean() * 252  # 年化平均收益率
            std_return = daily_returns.std() * math.sqrt(252)  # 年化标准差
            if std_return > 0:
                sharpe_ratio = (mean_return - risk_free_rate) / std_return
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        # 计算波动率
        volatility = daily_returns.std() * math.sqrt(252) if len(daily_returns) > 0 else 0
        
        # 计算信息比率（简化处理，实际应该有基准数据）
        info_ratio = 0
        
        metrics = {
            'fund_code': fund_code,
            'fund_name': fund_name,
            'annualized_return': annualized_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'volatility': volatility,
            'info_ratio': info_ratio,
            'total_return': total_return,
            'days': days,
            'data_points': len(fund_data)
        }
        
        print(f"基金 {fund_code} ({fund_name}) 指标计算完成")
        return metrics
        
    except Exception as e:
        print(f"获取基金 {fund_code} ({fund_name}) 指标失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def enhanced_compare_fund_performance():
    """
    增强版基金绩效对比函数，包含Sharpe比率、年化收益、最大回撤等指标
    """
    print("\n开始增强版基金绩效对比分析...")
    
    try:
        import pandas as pd
        import pymysql
        from sqlalchemy import create_engine
        from datetime import date, timedelta
        import warnings
        import time
        warnings.filterwarnings('ignore', category=pymysql.Warning)
        
        # 数据库连接信息（与analyze_funds函数保持一致）
        db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': 'root',
            'database': 'fund_analysis',
            'port': 3306,
            'charset': 'utf8mb4'
        }
        
        # 创建数据库连接
        connection_string = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}?charset={db_config['charset']}"
        engine = create_engine(connection_string)
        
        # 获取今日和昨日日期
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        print(f"对比日期：昨天({yesterday}) vs 今天({today})")
        
        # 从Excel文件中获取基金代码列表
        try:
            file_path = "d:/codes/py4zinia/京东金融.xlsx"
            position_data = pd.read_excel(file_path, sheet_name='持仓数据')
            excel_fund_codes = position_data['代码'].apply(lambda x: str(int(x)).zfill(6) if pd.notna(x) else '').tolist()
            excel_fund_codes = [code for code in excel_fund_codes if code]
            print(f"从京东金融.xlsx中获取到 {len(excel_fund_codes)} 只基金用于绩效对比分析")
        except Exception as e:
            print(f"读取Excel文件失败: {str(e)}")
            excel_fund_codes = []
        
        # 查询今日和昨日的基金数据，只查询Excel文件中存在的基金
        if excel_fund_codes:
            fund_codes_str = "','".join(excel_fund_codes)
            fund_codes_clause = f"AND fund_code IN ('{fund_codes_str}')"
        else:
            fund_codes_clause = ""
        
        query = f"""
        SELECT * FROM fund_analysis_results 
        WHERE analysis_date IN ('{yesterday}', '{today}')
        {fund_codes_clause}
        ORDER BY fund_code, analysis_date
        """
        
        df = pd.read_sql(query, engine)
        
        if df.empty:
            print("未找到足够的数据进行对比")
            return None
        
        # 按基金代码分组
        fund_groups = df.groupby('fund_code')
        
        comparison_results = []
        
        for fund_code, group in fund_groups:
            if len(group) < 2:
                print(f"基金 {fund_code} 缺少完整的历史数据，尝试从其他数据源获取")
                
                # 尝试从FundRealTime获取实时数据
                try:
                    from fund_realtime import FundRealTime
                    fund_data = FundRealTime.get_realtime_nav(fund_code)
                    if fund_data:
                        print(f"  基金 {fund_code} ({fund_data['name']}) 从FundRealTime获取到实时数据")
                        # 由于我们需要昨天和今天的数据，而这里只能获取实时数据，所以仍然无法进行对比
                        # 但至少我们知道了基金的名称
                        continue
                    else:
                        print(f"  基金 {fund_code} 无法从FundRealTime获取数据")
                except Exception as e:
                    print(f"  基金 {fund_code} 尝试从FundRealTime获取数据失败: {str(e)}")
                
                # 尝试从akshare获取基金基本信息
                try:
                    import akshare as ak
                    fund_info = ak.fund_info_em(fund_code)
                    print(f"  基金 {fund_code} 从fund_info_em获取到基本信息")
                except Exception as e:
                    print(f"  基金 {fund_code} 尝试从fund_info_em获取数据失败: {str(e)}")
                
                continue
                
            # 按日期排序
            sorted_group = group.sort_values('analysis_date')
            
            # 获取昨日和今日数据
            yesterday_data = sorted_group.iloc[0]
            today_data = sorted_group.iloc[1]
            
            # 计算变化值
            return_change = today_data['today_return'] - yesterday_data['today_return']
            
            comparison_results.append({
                'fund_code': fund_code,
                'fund_name': today_data['fund_name'],
                'yesterday_return': yesterday_data['today_return'],
                'today_return': today_data['today_return'],
                'return_change': return_change,
                'yesterday_status': yesterday_data['status_label'],
                'today_status': today_data['status_label'],
                'yesterday_operation': yesterday_data['operation_suggestion'],
                'today_operation': today_data['operation_suggestion']
            })
        
        if not comparison_results:
            print("没有足够的基金数据进行完整对比")
            return None
        
        comparison_df = pd.DataFrame(comparison_results)
        
        # 获取基金的详细指标分析
        print("\n正在获取基金详细指标分析...")
        fund_metrics = []
        
        for index, row in comparison_df.iterrows():
            fund_code = row['fund_code']
            fund_name = row['fund_name']
            metrics = get_fund_metrics(fund_code, fund_name)
            if metrics:
                fund_metrics.append(metrics)
            # 添加延迟，避免API调用过于频繁
            time.sleep(0.5)
        
        # 显示详细指标分析
        if fund_metrics:
            metrics_df = pd.DataFrame(fund_metrics)
            print("\n基金详细指标分析：")
            display_metrics_df = metrics_df.copy()
            display_metrics_df['annualized_return'] = (display_metrics_df['annualized_return'] * 100).map('{:.2f}%'.format)
            display_metrics_df['max_drawdown'] = (display_metrics_df['max_drawdown'] * 100).map('{:.2f}%'.format)
            display_metrics_df['sharpe_ratio'] = display_metrics_df['sharpe_ratio'].map('{:.2f}'.format)
            display_metrics_df['volatility'] = (display_metrics_df['volatility'] * 100).map('{:.2f}%'.format)
            display_metrics_df['total_return'] = (display_metrics_df['total_return'] * 100).map('{:.2f}%'.format)
            print(display_metrics_df[['fund_code', 'fund_name', 'annualized_return', 'max_drawdown', 'sharpe_ratio', 'volatility', 'total_return']])
            
            # 合并指标到对比结果中
            comparison_df = comparison_df.merge(metrics_df, on=['fund_code', 'fund_name'], how='left')
        else:
            print("未能获取任何基金的详细指标")
        
        # 格式化显示
        print("\n基金绩效对比结果：")
        display_columns = ['fund_code', 'fund_name', 'yesterday_return', 'today_return', 'return_change', 'annualized_return', 'max_drawdown', 'sharpe_ratio']
        display_df = comparison_df.copy()
        display_df['yesterday_return'] = display_df['yesterday_return'].map('{:.2f}%'.format)
        display_df['today_return'] = display_df['today_return'].map('{:.2f}%'.format)
        display_df['return_change'] = display_df['return_change'].map('{:.2f}%'.format)
        if 'annualized_return' in display_df.columns:
            display_df['annualized_return'] = (display_df['annualized_return'] * 100).map('{:.2f}%'.format)
        if 'max_drawdown' in display_df.columns:
            display_df['max_drawdown'] = (display_df['max_drawdown'] * 100).map('{:.2f}%'.format)
        if 'sharpe_ratio' in display_df.columns:
            display_df['sharpe_ratio'] = display_df['sharpe_ratio'].map('{:.2f}'.format)
        print(display_df[display_columns])
        
        # 生成可视化图表
        plot_performance_comparison(comparison_df)
        
        return comparison_df
        
    except ImportError:
        print("缺少必要的依赖包，请安装: pip install PyMySQL sqlalchemy pandas")
        return None
    except Exception as e:
        print(f"进行基金绩效对比时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# 主程序入口
if __name__ == "__main__":
    import sys
    
    try:
        # 立即执行一次基金分析
        print("执行基金分析...")
        regular_df = analyze_funds()
        
        # 执行增强版绩效对比分析
        print("\n执行增强版基金绩效对比分析...")
        performance_df = enhanced_compare_fund_performance()
        
        # 如果两者都成功获取，生成组合报告并发送邮件
        if regular_df is not None and performance_df is not None:
            print("\n生成组合报告并发送邮件...")
            
            # 生成组合报告
            combined_message = generate_combined_report(regular_df, performance_df)
            
            # 获取微信配置
            wechat_config = {
                'enabled': True,
                'token': 'fb0dfd5592ed4eb19cd886d737b6cc6a'
            }
            
            # 发送组合报告邮件
            send_notification(wechat_config['token'], combined_message, title="基金综合分析报告")
        
        print("\n程序执行完成")
    except ImportError as e:
        print(f"缺少必要库: {e}")
        print("请安装所需依赖: pip install pandas schedule pymysql sqlalchemy requests matplotlib akshare")
    except KeyboardInterrupt:
        print("\n程序已被用户终止")
        sys.exit(0)
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)