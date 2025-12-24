#!/usr/bin/env python
# coding: utf-8

import pandas as pd, openpyxl
from datetime import date
pd.set_option('display.expand_frame_repr', False)  # 核心：不换行，强制一行显示所有列
pd.set_option('display.max_columns', None)         # 显示所有列（默认会限制列数导致截断/换行）
pd.set_option('display.width', 1000)               # 设置控制台显示宽度（值越大，一行能容纳的内容越多）
pd.set_option('display.max_colwidth', 20)          # 可选：设置每列的最大宽度（避免单列内容过长）

# 定义发送微信通知的函数 - 使用pushplus服务
def send_wechat_via_pushplus(message, title="基金分析报告"):
    """
    通过pushplus服务发送微信消息
    
    参数：
    message: 要发送的消息内容
    title: 消息标题
    """
    try:
        # pushplus token - 与itchat_test.py保持一致
        token = 'fb0dfd5592ed4eb19cd886d737b6cc6a'
        
        # 构建请求URL
        url = f"https://www.pushplus.plus/send?token={token}&title={title}&content={message}&template=html"
        
        print("📤 正在发送微信通知...")
        response = requests.get(url=url)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 200:
                print("✅ 微信通知发送成功!")
                return True
            else:
                print(f"❌ 微信通知发送失败: {result.get('msg', '未知错误')}")
                return False
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 发送微信通知时出错: {str(e)}")
        return False

# 读取京东金融Excel文件中的持仓数据表
file_path = "d:/codes/py4zinia/fund_search/京东金融.xlsx"

# 只读取名为'持仓数据'的工作表
持仓数据 = pd.read_excel(file_path, sheet_name='持仓数据')

# 显示持仓数据的基本信息
print("持仓数据表信息：")
print(f"数据形状: {持仓数据.shape[0]} 行 x {持仓数据.shape[1]} 列")
print(f"列名: {list(持仓数据.columns)}")
print("\n前5行数据:")
print(持仓数据.head())

# 尝试使用fund_realtime获取基金净值和收益率数据
try:
    from fund_realtime import FundRealTime

    print("\n使用fund_realtime获取基金数据示例：")

    # 提取基金代码
    fund_codes = 持仓数据['代码'].astype(str).tolist()
    print(f"基金代码列表: {fund_codes[:5]}... (共{len(fund_codes)}个)")

    # 使用fund_realtime批量获取基金实时数据
    print("\n获取基金实时数据:")

    # 批量获取我们持仓中的基金数据
    fund_data_filtered = FundRealTime.get_realtime_batch(fund_codes)

    if not fund_data_filtered.empty:
        print(f"找到 {len(fund_data_filtered)} 只持仓基金的实时数据:")
        # 选择关键列显示
        columns_to_show = ['基金代码', '基金名称', '昨日净值', '实时估值', '涨跌(%)']
        if all(col in fund_data_filtered.columns for col in columns_to_show):
            print(fund_data_filtered[columns_to_show].head(10))
        else:
            print(fund_data_filtered.head(10))
    else:
        print("未找到持仓基金的实时数据")
except ImportError:
    print("\nfund_realtime模块未找到，请确保fund_realtime.py文件在当前目录下")
except Exception as e:
    print(f"\n获取基金数据时出错: {str(e)}") 

# 获取单个基金的实时数据，并比较当日收益率与前一日收益率
sample_fund_code = fund_data_filtered['基金代码'].values[0] if not fund_data_filtered.empty else None
if sample_fund_code:
    print(f"\n获取基金 {sample_fund_code} 的实时数据用于收益率比较:")
    try:
        # 使用fund_realtime获取基金的实时数据
        fund_realtime_data = FundRealTime.get_realtime_nav(sample_fund_code)
        if fund_realtime_data:
            # 从实时数据获取当前信息
            fund_name = fund_realtime_data['name']
            yesterday_nav = float(fund_realtime_data['dwjz'])  # 昨日净值
            current_estimate = float(fund_realtime_data['gsz'])  # 当前估值
            estimate_change_pct = float(fund_realtime_data['gszzl'])  # 估算涨跌百分比

            print(f"基金名称: {fund_name}")
            print(f"昨日净值: {yesterday_nav}")
            print(f"当前估值: {current_estimate}")
            print(f"估算涨跌: {estimate_change_pct}%")

            # 获取历史数据用于比较前一日收益率
            # 由于fund_realtime主要提供实时数据，我们需要用净值计算当日收益率
            if yesterday_nav != 0:
                # 计算当日收益率：(当前估值 - 昨日净值) / 昨日净值 * 100
                today_return = (current_estimate - yesterday_nav) / yesterday_nav * 100

                print(f"当日收益率(基于估值计算): {today_return:.2f}%")
                print(f"前一日收益率(估算): {estimate_change_pct}%")

                # 比较当日收益率是否小于前一日收益率
                if today_return < estimate_change_pct:
                    print(f"✓ 基金 {sample_fund_code} 满足条件：今日收益率({today_return:.2f}%) < 前一日收益率({estimate_change_pct}%)")
                else:
                    print(f"✗ 基金 {sample_fund_code} 不满足条件：今日收益率({today_return:.2f}%) >= 前一日收益率({estimate_change_pct}%)")
            else:
                print("昨日净值为0，无法计算收益率")
        else:
            print("未获取到基金实时数据")
    except Exception as e:
        print(f"获取基金数据时出错: {str(e)}")
        print("尝试使用其他方法获取基金数据...")

# 定义生成微信通知markdown消息的函数
def generate_wechat_message(result_df):
    """
    根据基金分析结果生成微信通知的markdown消息
    
    参数：
    result_df: 基金分析结果的DataFrame
    
    返回：
    str: 格式化的markdown消息内容
    """
    from datetime import date
    
    # 创建一个副本用于格式化显示
    df_display = result_df.copy()
    
    # 格式化收益率为百分比
    df_display['today_return'] = df_display['today_return'].map('{:.2f}%'.format)
    df_display['prev_day_return'] = df_display['prev_day_return'].map('{:.2f}%'.format)
    df_display['comparison_value'] = df_display['comparison_value'].map('{:.2f}%'.format)
    
    # 生成markdown消息
    message = f"### 📊 基金分析报告 - {date.today().strftime('%Y年%m月%d日')}\n\n"
    message += "**持仓基金收益率变化分析**\n\n"
    
    # 添加表格
    message += "| 基金代码 | 基金名称 | 今日收益率 | 昨日收益率 | 趋势状态 | 操作建议 | 执行金额 |\n"
    message += "|---------|---------|----------|----------|---------|---------|---------|\n"
    
    for _, row in df_display.iterrows():
        message += f"| {row['fund_code']} | {row['fund_name']} | {row['today_return']} | {row['prev_day_return']} | {row['status_label']} | {row['operation_suggestion']} | {row['execution_amount']} |\n"
    
    message += "\n**提示**：以上分析基于实时估值数据，仅供参考。最终投资决策请结合市场情况谨慎考虑。"
    
    return message

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

# 分析所有持仓基金，比较当日收益率与前一日收益率
print("\n分析所有持仓基金的收益率变化：")
try:
    from fund_realtime import FundRealTime
    import akshare as ak  # 重新引入akshare用于获取前一日收益率
    import pandas as pd
    import requests  # 添加requests导入

    # 获取持仓数据中的基金代码
    fund_codes = 持仓数据['代码'].astype(str).tolist()

    # 批量获取所有持仓基金的实时数据
    all_fund_data = FundRealTime.get_realtime_batch(fund_codes)

    if not all_fund_data.empty:
        all_funds = []  # 存储所有基金数据，包括满足和不满足条件的

        print(f"正在分析 {len(all_fund_data)} 只持仓基金...")

        for idx, row in all_fund_data.iterrows():
            fund_code = row['基金代码']
            fund_name = row['基金名称']
            yesterday_nav = float(row['昨日净值'])  # 昨日净值
            current_estimate = float(row['实时估值'])  # 当前估值
            estimate_change_pct = float(row['涨跌(%)'])  # 估算涨跌百分比

            if yesterday_nav != 0:
                # 计算当日收益率：(当前估值 - 昨日净值) / 昨日净值 * 100
                today_return = (current_estimate - yesterday_nav) / yesterday_nav * 100

                # 获取前一日实际收益率（使用akshare）
                try:
                    # 使用akshare获取基金历史净值数据
                    fund_hist = ak.fund_open_fund_info_em(symbol=fund_code, indicator='单位净值走势')
                    if not fund_hist.empty:
                        # 按日期排序确保最新数据在前
                        fund_hist = fund_hist.sort_values('净值日期', ascending=False)
                        # 获取前一天的实际收益率
                        prev_day_return = float(fund_hist.iloc[0]['日增长率'])

                        # 比较当日收益率是否小于前一日收益率
                        is_qualified = today_return < prev_day_return
                        
                        if is_qualified:
                            print(f"✓ 基金 {fund_code} ({fund_name}) 满足条件")
                        else:
                            print(f"  基金 {fund_code} ({fund_name}) 不满足条件")
                            
                        print(f"  当日收益率(基于估值计算): {today_return:.2f}%")
                        print(f"  前一日收益率(akshare获取): {prev_day_return}%")
                        
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
                        # 如果无法获取历史数据，使用估算值
                        print(f"  基金 {fund_code} ({fund_name}) 无法获取历史数据，使用估算值")
                        print(f"  当日收益率(基于估值计算): {today_return:.2f}%")
                        print(f"  前一日收益率(估算): {estimate_change_pct}%")

                        # 比较当日收益率是否小于前一日收益率（使用估算值）
                        is_qualified = today_return < estimate_change_pct
                        
                        if is_qualified:
                            print(f"✓ 基金 {fund_code} ({fund_name}) 满足条件")
                        else:
                            print(f"  基金 {fund_code} ({fund_name}) 不满足条件")
                            
                        # 应用投资策略
                        status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, execution_amount, buy_multiplier = get_investment_strategy(today_return, estimate_change_pct)
                        
                        # 将所有基金数据添加到列表，包括投资策略结果
                        all_funds.append({
                            'fund_code': fund_code,
                            'fund_name': fund_name,
                            'yesterday_nav': yesterday_nav,
                            'current_estimate': current_estimate,
                            'today_return': today_return,
                            'prev_day_return': estimate_change_pct,
                            'status_label': status_label,
                            'is_buy': is_buy,
                            'redeem_amount': redeem_amount,
                            'comparison_value': comparison_value,
                            'operation_suggestion': operation_suggestion,
                            'execution_amount': execution_amount,
                            'buy_multiplier': buy_multiplier,
                            'analysis_date': date.today()  # 添加分析日期
                        })
                except Exception as e:
                    # 如果获取历史数据失败，使用估算值
                    print(f"  基金 {fund_code} ({fund_name}) 获取历史数据失败: {str(e)}，使用估算值")
                    print(f"  当日收益率(基于估值计算): {today_return:.2f}%")
                    print(f"  前一日收益率(估算): {estimate_change_pct}%")

                    # 比较当日收益率是否小于前一日收益率（使用估算值）
                    is_qualified = today_return < estimate_change_pct
                    
                    if is_qualified:
                        print(f"✓ 基金 {fund_code} ({fund_name}) 满足条件")
                    else:
                        print(f"  基金 {fund_code} ({fund_name}) 不满足条件")
                        
                    # 应用投资策略
                    status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, execution_amount, buy_multiplier = get_investment_strategy(today_return, estimate_change_pct)
                    
                    # 将所有基金数据添加到列表，包括投资策略结果
                    all_funds.append({
                        'fund_code': fund_code,
                        'fund_name': fund_name,
                        'yesterday_nav': yesterday_nav,
                        'current_estimate': current_estimate,
                        'today_return': today_return,
                        'prev_day_return': estimate_change_pct,
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
            if all_funds:
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
                # 请在下面设置正确的数据库连接信息
                db_config = {
                    'host': 'localhost',      # 数据库主机地址
                    'user': 'root',           # 数据库用户名
                    'password': 'root',  # 数据库密码
                    'database': 'fund_analysis',  # 数据库名
                    'port': 3306,             # 端口号
                    'charset': 'utf8mb4'      # 字符编码
                }

                # 微信通知配置 - 使用pushplus
                wechat_config = {
                    'enabled': True,  # 启用微信通知功能
                    'title': f"📊 基金分析报告 - {date.today().strftime('%m月%d日')}"  # 微信消息标题
                }

                # 检查是否 still using default configuration
                if db_config['password'] == 'root':
                    print("\n注意：当前使用默认密码配置，尝试连接数据库...")
                    # 尝试连接 anyway with current configuration
                # Create database connection regardless of password
                connection_string = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}?charset={db_config['charset']}"
                engine = create_engine(connection_string)

                # 检查并更新数据库表结构，添加新字段
                try:
                    # 连接数据库
                    conn = pymysql.connect(**db_config)
                    cursor = conn.cursor()
                    
                    # 检查字段是否存在，如果不存在则添加
                    fields_to_add = [
                        ('fund_code', 'VARCHAR(20)'),
                        ('fund_name', 'VARCHAR(100)'),
                        ('yesterday_nav', 'FLOAT'),
                        ('current_estimate', 'FLOAT'),
                        ('today_return', 'FLOAT'),
                        ('prev_day_return', 'FLOAT'),
                        ('status_label', 'VARCHAR(50)'),
                        ('is_buy', 'BOOLEAN'),
                        ('redeem_amount', 'DECIMAL(10,2)'),
                        ('comparison_value', 'FLOAT'),
                        ('operation_suggestion', 'VARCHAR(100)'),
                        ('execution_amount', 'VARCHAR(20)'),
                        ('analysis_date', 'DATE'),
                        ('buy_multiplier', 'FLOAT')
                    ]
                    
                    for field_name, field_type in fields_to_add:
                        cursor.execute(f"SHOW COLUMNS FROM fund_analysis_results LIKE '{field_name}'")
                        if cursor.fetchone() is None:
                            cursor.execute(f"ALTER TABLE fund_analysis_results ADD COLUMN {field_name} {field_type}")
                            print(f"已添加字段: {field_name}")
                    
                    # 检查是否有旧的中文字段需要删除
                    old_fields = ['基金代码', '基金名称', '昨日净值', '实时估值', '当日收益率', '前一日收益率', '状态标记', '是否买入', '赎回金额', '比较结果值']
                    for old_field in old_fields:
                        cursor.execute(f"SHOW COLUMNS FROM fund_analysis_results LIKE '{old_field}'")
                        if cursor.fetchone() is not None:
                            cursor.execute(f"ALTER TABLE fund_analysis_results DROP COLUMN {old_field}")
                            print(f"已删除旧字段: {old_field}")
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                except Exception as e:
                    print(f"更新数据库表结构时出错: {str(e)}")
                
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

                # 新增：发送微信通知 - 使用pushplus
                if wechat_config['enabled']:
                    print("\n正在发送微信通知...")
                    try:
                        # 生成微信通知消息
                        wechat_message = generate_wechat_message(result_df_db)
                        # 发送微信通知 - 使用pushplus
                        send_wechat_via_pushplus(wechat_message, wechat_config['title'])
                    except Exception as e:
                        print(f"发送微信通知时出错: {str(e)}")
                else:
                    print("\n微信通知功能未启用")

            except ImportError:
                print("\n缺少必要的数据库依赖包，请安装: pip install PyMySQL sqlalchemy requests")
            except Exception as e:
                print(f"\n保存到数据库时出错: {str(e)}")
                print("请检查数据库连接配置是否正确")
                print("请确保MySQL服务已启动，并且用户名密码正确")
        else:
            print("\n未获取到基金数据")
    else:
        print("未能获取到任何基金的实时数据")

except Exception as e:
    print(f"\n分析基金收益率时出错: {str(e)}")