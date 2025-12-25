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
        file_path = "d:/codes/py4zinia/fund_search/京东金融.xlsx"
        # 只读取名为'持仓数据'的工作表
        持仓数据 = pd.read_excel(file_path, sheet_name='持仓数据')

        # 获取持仓数据中的基金代码
        fund_codes = 持仓数据['代码'].astype(str).tolist()

        # 批量获取所有持仓基金的实时数据
        all_fund_data = FundRealTime.get_realtime_batch(fund_codes)

        if all_fund_data.empty:
            print("未能获取到任何基金的实时数据")
            return
            
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
                    else:
                        # 如果无法获取历史数据，使用估算值
                        print(f"  基金 {fund_code} ({fund_name}) 无法获取历史数据，使用估算值")
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
        
        # 查询今日和昨日的基金数据
        query = f"""
        SELECT * FROM fund_analysis_results 
        WHERE analysis_date IN ('{yesterday}', '{today}')
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
                print(f"基金 {fund_code} 缺少完整的历史数据")
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
    使用matplotlib创建基金绩效对比图表
    
    参数：
    comparison_df: 包含基金绩效对比数据的DataFrame
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        from datetime import date, timedelta
        
        # 设置中文显示
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 获取今日和昨日日期
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # 创建图表
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [2, 1]})
        fig.suptitle(f'基金绩效对比分析\n昨天({yesterday}) vs 今天({today})', fontsize=16, fontweight='bold')
        
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
        
        # 显示图表
        plt.show()
        
    except ImportError:
        print("缺少matplotlib依赖包，请安装: pip install matplotlib")
    except Exception as e:
        print(f"生成可视化图表时出错: {str(e)}")

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