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
    
    # 格式化收益率为百分比
    df_display['today_return'] = df_display['today_return'].map('{:.2f}%'.format)
    df_display['prev_day_return'] = df_display['prev_day_return'].map('{:.2f}%'.format)
    df_display['comparison_value'] = df_display['comparison_value'].map('{:.2f}%'.format)
    
    # 按照操作建议和执行金额排序
    df_display = df_display.sort_values(by=['operation_suggestion', 'execution_amount'])
    
    # 生成HTML消息
    message = f"<h2>📊 基金分析报告 - {date.today().strftime('%Y年%m月%d日')}</h2>\n"
    message += f"<h3>持仓基金收益率变化分析</h3>\n"
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
                        # 如果无法获取历史数据，使用估算值
                        print(f"  基金 {fund_code} ({fund_name}) 无法获取历史数据，使用估算值")
                        prev_day_return = estimate_change_pct
                except Exception as e:
                    # 如果获取历史数据失败，使用估算值
                    print(f"  基金 {fund_code} ({fund_name}) 获取历史数据失败: {str(e)}，使用估算值")
                    prev_day_return = estimate_change_pct
                
                # 获取基金绩效指标
                metrics = get_fund_metrics(fund_code, fund_name)
                
                # 应用投资策略
                status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, execution_amount, buy_multiplier = get_investment_strategy(today_return, prev_day_return)
                
                # 将所有基金数据添加到列表，包括投资策略结果和绩效指标
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
                    'annualized_return': metrics['annualized_return'],
                    'sharpe_ratio': metrics['sharpe_ratio'],
                    'max_drawdown': metrics['max_drawdown'],
                    'volatility': metrics['volatility'],
                    'calmar_ratio': metrics['calmar_ratio'],
                    'sortino_ratio': metrics['sortino_ratio'],
                    'var_95': metrics['var_95'],
                    'win_rate': metrics['win_rate'],
                    'profit_loss_ratio': metrics['profit_loss_ratio'],
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
            
            # 定义所有列的数据类型，包括新添加的analysis_date、buy_multiplier和绩效指标
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
                'buy_multiplier': Float,
                'annualized_return': Float,
                'sharpe_ratio': Float,
                'max_drawdown': Float,
                'volatility': Float,
                'calmar_ratio': Float,
                'sortino_ratio': Float,
                'var_95': Float,
                'win_rate': Float,
                'profit_loss_ratio': Float
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
                    status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, execution_amount, analysis_date, buy_multiplier,
                    annualized_return, sharpe_ratio, max_drawdown, volatility, calmar_ratio, sortino_ratio, var_95, win_rate, profit_loss_ratio
                ) SELECT 
                    fund_code, fund_name, yesterday_nav, current_estimate, today_return, prev_day_return, 
                    status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, execution_amount, analysis_date, buy_multiplier,
                    annualized_return, sharpe_ratio, max_drawdown, volatility, calmar_ratio, sortino_ratio, var_95, win_rate, profit_loss_ratio
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
                    buy_multiplier = VALUES(buy_multiplier),
                    annualized_return = VALUES(annualized_return),
                    sharpe_ratio = VALUES(sharpe_ratio),
                    max_drawdown = VALUES(max_drawdown),
                    volatility = VALUES(volatility),
                    calmar_ratio = VALUES(calmar_ratio),
                    sortino_ratio = VALUES(sortino_ratio),
                    var_95 = VALUES(var_95),
                    win_rate = VALUES(win_rate),
                    profit_loss_ratio = VALUES(profit_loss_ratio)
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

        except ImportError:
            print("\n缺少必要的数据库依赖包，请安装: pip install PyMySQL sqlalchemy requests")
        except Exception as e:
            print(f"\n保存到数据库时出错: {str(e)}")
            print("请检查数据库连接配置是否正确")
            print("请确保MySQL服务已启动，并且用户名密码正确")
            
    except Exception as e:
        print(f"\n分析基金收益率时出错: {str(e)}")

# 定义基金绩效对比函数
def compare_fund_performance():
    """
    对比基金的综合绩效指标
    
    返回：
    DataFrame: 包含基金代码、名称和各项绩效指标的对比数据
    """
    print("\n开始基金绩效对比分析...")
    
    try:
        import pandas as pd
        import pymysql
        from sqlalchemy import create_engine
        from datetime import date
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
        
        # 获取最新的基金数据（每个基金只取最新一条记录）
        query = """
        SELECT DISTINCT t1.fund_code, t1.fund_name, t1.today_return, t1.prev_day_return, t1.status_label, t1.operation_suggestion,
               t1.annualized_return, t1.sharpe_ratio, t1.max_drawdown, t1.volatility, t1.calmar_ratio, t1.sortino_ratio, t1.var_95, t1.win_rate, t1.profit_loss_ratio
        FROM fund_analysis_results t1
        INNER JOIN (
            SELECT fund_code, MAX(analysis_date) as max_date
            FROM fund_analysis_results
            GROUP BY fund_code
        ) t2 ON t1.fund_code = t2.fund_code AND t1.analysis_date = t2.max_date
        ORDER BY t1.fund_code
        """
        
        df = pd.read_sql(query, engine)
        
        if df.empty:
            print("未找到足够的数据进行对比")
            return None
        
        print(f"\n共找到 {len(df)} 只基金的最新绩效数据")
        
        # 格式化显示
        print("\n基金绩效指标对比结果：")
        display_columns = [
            'fund_code', 'fund_name', 'today_return', 'annualized_return', 
            'sharpe_ratio', 'max_drawdown', 'volatility', 'calmar_ratio', 
            'sortino_ratio', 'win_rate', 'status_label', 'operation_suggestion'
        ]
        
        display_df = df.copy()
        # 格式化数值为百分比
        display_df['today_return'] = display_df['today_return'].map('{:.2f}%'.format)
        display_df['annualized_return'] = display_df['annualized_return'].map('{:.2f}%'.format)
        display_df['max_drawdown'] = display_df['max_drawdown'].map('{:.2f}%'.format)
        display_df['volatility'] = display_df['volatility'].map('{:.2f}%'.format)
        display_df['win_rate'] = display_df['win_rate'].map('{:.2f}%'.format)
        # 其他指标保留小数点后三位
        display_df['sharpe_ratio'] = display_df['sharpe_ratio'].round(3)
        display_df['calmar_ratio'] = display_df['calmar_ratio'].round(3)
        display_df['sortino_ratio'] = display_df['sortino_ratio'].round(3)
        display_df['var_95'] = display_df['var_95'].round(4)
        display_df['profit_loss_ratio'] = display_df['profit_loss_ratio'].round(2)
        
        print(display_df[display_columns])
        
        # 生成可视化图表
        plot_performance_comparison(df)
        
        return df
        
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
            ax1.text(1.02, 0.5, '基金名称:', transform=ax1.transAxes, fontweight='bold', ha='left', va='center')
            for i, name in enumerate(fund_names):
                ax1.text(1.02, 0.45 - i*0.05, f'{comparison_df.iloc[i, 0]}: {name}', transform=ax1.transAxes, ha='left', va='top')
            
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
                ax.text(1.02, 0.5, '基金名称:', transform=ax.transAxes, fontweight='bold', ha='left', va='center')
                for i, name in enumerate(fund_names):
                    ax.text(1.02, 0.45 - i*0.05, f'{comparison_df.iloc[i]["fund_code"]}: {name}', 
                            transform=ax.transAxes, ha='left', va='top')
                
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
        
        # 准备数据
        n_funds = len(valid_data)
        indices = np.arange(n_funds)
        returns = valid_data['annualized_return'] * 100
        
        # 设置颜色：正收益为绿色，负收益为红色
        colors = ['#2E8B57' if x >= 0 else '#CD5C5C' for x in returns]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 绘制柱状图
        bars = ax.bar(indices, returns, alpha=0.8, color=colors, edgecolor='black', linewidth=0.5)
        
        # 设置图表属性
        ax.set_xlabel('基金代码', fontsize=12, fontweight='bold')
        ax.set_ylabel('年化收益率 (%)', fontsize=12, fontweight='bold')
        ax.set_title('基金年化收益率对比', fontweight='bold', fontsize=16, pad=20)
        ax.set_xticks(indices)
        ax.set_xticklabels(valid_data['fund_code'], rotation=45, ha='right', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        # 添加零基准线
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # 在柱子上添加数值标签
        for bar, value in zip(bars, returns):
            height = bar.get_height()
            # 根据值的正负决定标签位置
            if height >= 0:
                ax.text(bar.get_x() + bar.get_width()/2., height + max(0.1 * abs(height), 0.2),
                        f'{value:.2f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
            else:
                ax.text(bar.get_x() + bar.get_width()/2., height - max(0.1 * abs(height), 0.2),
                        f'{value:.2f}%', ha='center', va='top', fontsize=9, fontweight='bold')
        
        # 创建图例
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor='#2E8B57', label='正收益'),
                          Patch(facecolor='#CD5C5C', label='负收益')]
        ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0, 1), fontsize=10)
        
        # 在右侧显示基金名称
        fund_names = valid_data['fund_name'].tolist()
        if fund_names:
            # 计算合适的文本位置
            y_positions = np.linspace(ax.get_ylim()[1] * 0.8, ax.get_ylim()[1] * 0.3, len(fund_names))
            for i, (name, code) in enumerate(zip(fund_names, valid_data['fund_code'])):
                # Truncate long names
                display_name = name[:20] + '...' if len(name) > 20 else name
                ax.annotate(f'{code}: {display_name}', 
                           xy=(1, y_positions[i]), 
                           xytext=(5, 0), 
                           xycoords=('axes fraction', 'data'),
                           textcoords='offset points',
                           va='center', ha='left', fontsize=9,
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgray', alpha=0.7))
        
        # 调整布局
        plt.tight_layout()
        
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
        
        # 准备数据（转换为百分比）
        n_funds = len(valid_data)
        indices = np.arange(n_funds)
        drawdown_values = valid_data['max_drawdown'] * 100  # 转换为百分比
        
        # 设置颜色：回撤越深（负值越大）用更红的颜色表示，较小回撤用较浅颜色
        colors = ['#CD5C5C' if x < 0 else '#2E8B57' for x in drawdown_values]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 绘制柱状图
        bars = ax.bar(indices, drawdown_values, alpha=0.8, color=colors, edgecolor='black', linewidth=0.5)
        
        # 设置图表属性
        ax.set_xlabel('基金代码', fontsize=12, fontweight='bold')
        ax.set_ylabel('最大回撤 (%)', fontsize=12, fontweight='bold')
        ax.set_title('基金最大回撤对比', fontweight='bold', fontsize=16, pad=20)
        ax.set_xticks(indices)
        ax.set_xticklabels(valid_data['fund_code'], rotation=45, ha='right', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        # 添加零基准线
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # 在柱子上添加数值标签
        for bar, value in zip(bars, drawdown_values):
            height = bar.get_height()
            # 根据值的正负决定标签位置
            if height >= 0:
                ax.text(bar.get_x() + bar.get_width()/2., height + max(0.1 * abs(height), 0.2),
                        f'{value:.2f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
            else:
                ax.text(bar.get_x() + bar.get_width()/2., height - max(0.1 * abs(height), 0.2),
                        f'{value:.2f}%', ha='center', va='top', fontsize=9, fontweight='bold')
        
        # 创建图例
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor='#2E8B57', label='较小回撤'),
                          Patch(facecolor='#CD5C5C', label='较大回撤')]
        ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0, 1), fontsize=10)
        
        # 在右侧显示基金名称
        fund_names = valid_data['fund_name'].tolist()
        if fund_names:
            # 计算合适的文本位置
            y_positions = np.linspace(ax.get_ylim()[1] * 0.8, ax.get_ylim()[1] * 0.3, len(fund_names))
            for i, (name, code) in enumerate(zip(fund_names, valid_data['fund_code'])):
                # Truncate long names
                display_name = name[:20] + '...' if len(name) > 20 else name
                ax.annotate(f'{code}: {display_name}', 
                           xy=(1, y_positions[i]), 
                           xytext=(5, 0), 
                           xycoords=('axes fraction', 'data'),
                           textcoords='offset points',
                           va='center', ha='left', fontsize=9,
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgray', alpha=0.7))
        
        # 调整布局
        plt.tight_layout()
        
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
        
        # 准备数据
        n_funds = len(valid_data)
        indices = np.arange(n_funds)
        ratios = valid_data['sharpe_ratio']
        
        # 设置颜色：正比率为绿色，负比率为红色
        colors = ['#2E8B57' if x >= 0 else '#CD5C5C' for x in ratios]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 绘制柱状图
        bars = ax.bar(indices, ratios, alpha=0.8, color=colors, edgecolor='black', linewidth=0.5)
        
        # 设置图表属性
        ax.set_xlabel('基金代码', fontsize=12, fontweight='bold')
        ax.set_ylabel('夏普比率', fontsize=12, fontweight='bold')
        ax.set_title('基金夏普比率对比', fontweight='bold', fontsize=16, pad=20)
        ax.set_xticks(indices)
        ax.set_xticklabels(valid_data['fund_code'], rotation=45, ha='right', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        # 添加零基准线
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # 在柱子上添加数值标签
        for bar, value in zip(bars, ratios):
            height = bar.get_height()
            # 根据值的正负决定标签位置
            if height >= 0:
                ax.text(bar.get_x() + bar.get_width()/2., height + max(0.1 * abs(height), 0.05),
                        f'{value:.2f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
            else:
                ax.text(bar.get_x() + bar.get_width()/2., height - max(0.1 * abs(height), 0.05),
                        f'{value:.2f}', ha='center', va='top', fontsize=9, fontweight='bold')
        
        # 创建图例
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor='#2E8B57', label='正比率'),
                          Patch(facecolor='#CD5C5C', label='负比率')]
        ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0, 1), fontsize=10)
        
        # 在右侧显示基金名称
        fund_names = valid_data['fund_name'].tolist()
        if fund_names:
            # 计算合适的文本位置
            y_positions = np.linspace(ax.get_ylim()[1] * 0.8, ax.get_ylim()[1] * 0.3, len(fund_names))
            for i, (name, code) in enumerate(zip(fund_names, valid_data['fund_code'])):
                # Truncate long names
                display_name = name[:20] + '...' if len(name) > 20 else name
                ax.annotate(f'{code}: {display_name}', 
                           xy=(1, y_positions[i]), 
                           xytext=(5, 0), 
                           xycoords=('axes fraction', 'data'),
                           textcoords='offset points',
                           va='center', ha='left', fontsize=9,
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgray', alpha=0.7))
        
        # 调整布局
        plt.tight_layout()
        
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
        
        # 准备数据
        n_funds = len(valid_data)
        indices = np.arange(n_funds)
        vol_values = valid_data['volatility'] * 100  # 转换为百分比
        
        # 设置颜色: 波动率较低为绿色，较高为红色（可根据实际情况调整阈值）
        median_vol = np.median(vol_values) if len(vol_values) > 0 else 0
        colors = ['#2E8B57' if x <= median_vol else '#CD5C5C' for x in vol_values]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 绘制柱状图
        bars = ax.bar(indices, vol_values, alpha=0.8, color=colors, edgecolor='black', linewidth=0.5)
        
        # 设置图表属性
        ax.set_xlabel('基金代码', fontsize=12, fontweight='bold')
        ax.set_ylabel('波动率 (%)', fontsize=12, fontweight='bold')
        ax.set_title('基金波动率对比', fontweight='bold', fontsize=16, pad=20)
        ax.set_xticks(indices)
        ax.set_xticklabels(valid_data['fund_code'], rotation=45, ha='right', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        # 在柱子上添加数值标签
        for bar, value in zip(bars, vol_values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + max(0.1 * abs(height), 0.2),
                    f'{value:.2f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        # 创建图例
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor='#2E8B57', label='低波动率'),
                          Patch(facecolor='#CD5C5C', label='高波动率')]
        ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0, 1), fontsize=10)
        
        # 在右侧显示基金名称
        fund_names = valid_data['fund_name'].tolist()
        if fund_names:
            # 计算合适的文本位置
            y_positions = np.linspace(ax.get_ylim()[1] * 0.8, ax.get_ylim()[1] * 0.3, len(fund_names))
            for i, (name, code) in enumerate(zip(fund_names, valid_data['fund_code'])):
                # Truncate long names
                display_name = name[:20] + '...' if len(name) > 20 else name
                ax.annotate(f'{code}: {display_name}', 
                           xy=(1, y_positions[i]), 
                           xytext=(5, 0), 
                           xycoords=('axes fraction', 'data'),
                           textcoords='offset points',
                           va='center', ha='left', fontsize=9,
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgray', alpha=0.7))
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图表
        chart_path = f"基金波动率对比_{today_str}.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"波动率对比图表已保存为: {chart_path}")
        
    except Exception as e:
        print(f"生成波动率对比图表时出错: {str(e)}")


def get_fund_metrics(fund_code, fund_name):
    """
    获取基金的绩效指标
    
    参数：
    fund_code: 基金代码
    fund_name: 基金名称
    
    返回：
    dict: 包含各种绩效指标的字典
    """
    try:
        import akshare as ak
        import pandas as pd
        import numpy as np
        from datetime import datetime
        
        print(f"正在获取基金 {fund_code} ({fund_name}) 的历史数据...")
        
        # 获取基金历史净值数据
        fund_data = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
        
        if fund_data.empty:
            print(f"基金 {fund_code} ({fund_name}) 无历史数据")
            return {
                'annualized_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'volatility': 0,
                'calmar_ratio': 0,
                'alpha': 0,
                'beta': 0,
                'sortino_ratio': 0,
                'var_95': 0,
                'win_rate': 0,
                'profit_loss_ratio': 0,
                'tracking_error': 0,
                'information_ratio': 0
            }
        
        # 数据预处理
        fund_data['净值日期'] = pd.to_datetime(fund_data['净值日期'])
        fund_data = fund_data.sort_values('净值日期').reset_index(drop=True)
        
        # 计算每日收益率
        fund_data['daily_return'] = fund_data['单位净值'].pct_change()
        daily_returns = fund_data['daily_return'].dropna()
        
        if len(daily_returns) < 2:
            print(f"基金 {fund_code} ({fund_name}) 历史数据不足，无法计算指标")
            return {
                'annualized_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'volatility': 0,
                'calmar_ratio': 0,
                'alpha': 0,
                'beta': 0,
                'sortino_ratio': 0,
                'var_95': 0,
                'win_rate': 0,
                'profit_loss_ratio': 0,
                'tracking_error': 0,
                'information_ratio': 0
            }
        
        # 计算年化收益率
        total_return = fund_data['单位净值'].iloc[-1] / fund_data['单位净值'].iloc[0] - 1
        days = (fund_data['净值日期'].iloc[-1] - fund_data['净值日期'].iloc[0]).days
        if days > 0:
            annualized_return = (1 + total_return) ** (365.25 / days) - 1
        else:
            annualized_return = 0
        
        # 计算年化波动率
        volatility = daily_returns.std() * np.sqrt(252) if len(daily_returns) > 1 else 0
        
        # 计算夏普比率 (假设无风险利率为3%)
        risk_free_rate = 0.03
        sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility != 0 else 0
        
        # 计算最大回撤
        cumulative_returns = (1 + daily_returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min() if not drawdown.empty else 0
        
        # 计算卡玛比率 (年化收益率 / 最大回撤绝对值)
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # 计算索提诺比率 (下行风险调整)
        negative_returns = daily_returns[daily_returns < 0]
        downside_deviation = np.sqrt((negative_returns ** 2).mean()) * np.sqrt(252) if len(negative_returns) > 0 else 0
        sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation if downside_deviation != 0 else 0
        
        # 计算胜率 (正收益天数占比)
        win_count = (daily_returns > 0).sum()
        total_count = len(daily_returns)
        win_rate = win_count / total_count if total_count > 0 else 0
        
        # 计算盈亏比 (平均盈利 / 平均亏损)
        positive_returns = daily_returns[daily_returns > 0]
        negative_returns = daily_returns[daily_returns < 0]
        avg_positive = positive_returns.mean() if len(positive_returns) > 0 else 0
        avg_negative = abs(negative_returns.mean()) if len(negative_returns) > 0 else 0
        profit_loss_ratio = avg_positive / avg_negative if avg_negative != 0 else 0
        
        # 计算VaR (95%置信度)
        var_95 = daily_returns.quantile(0.05) if len(daily_returns) > 0 else 0
        
        # 返回所有指标
        return {
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'calmar_ratio': calmar_ratio,
            'alpha': 0,  # 需要基准数据才能计算
            'beta': 0,   # 需要基准数据才能计算
            'sortino_ratio': sortino_ratio,
            'var_95': var_95,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'tracking_error': 0,  # 需要基准数据才能计算
            'information_ratio': 0  # 需要基准数据才能计算
        }
        
    except Exception as e:
        print(f"基金 {fund_code} ({fund_name}) 收益率数据不足，无法计算指标: {str(e)}")
        return {
            'annualized_return': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'volatility': 0,
            'calmar_ratio': 0,
            'alpha': 0,
            'beta': 0,
            'sortino_ratio': 0,
            'var_95': 0,
            'win_rate': 0,
            'profit_loss_ratio': 0,
            'tracking_error': 0,
            'information_ratio': 0
        }


# 主程序入口
if __name__ == "__main__":
    import sys
    
    try:
        # 立即执行一次基金分析
        print("执行基金分析...")
        analyze_funds()
        
        # 执行绩效对比
        print("\n\n执行基金绩效对比分析...")
        compare_fund_performance()
        
        print("\n程序执行完成")
    except ImportError as e:
        print(f"缺少必要库: {e}")
        print("请安装所需依赖: pip install pandas schedule pymysql sqlalchemy requests matplotlib akshare")
    except KeyboardInterrupt:
        print("\n程序已被用户终止")
        sys.exit(0)
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        sys.exit(1)