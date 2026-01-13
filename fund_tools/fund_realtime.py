#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时基金净值数据获取工具
来源：天天基金网免费接口
"""

import requests
import json
import re
import pandas as pd
from datetime import datetime
import time


class FundRealTime:
    """实时基金数据获取类"""

    @staticmethod
    def get_realtime_nav(fund_code):
        """
        获取单只基金实时估值

        参数:
            fund_code (str): 基金代码，如 '005827'

        返回:
            dict: 基金实时信息字典
                - fundcode: 基金代码
                - name: 基金名称
                - dwjz: 昨日净值
                - gsz: 实时估值
                - gszzl: 涨跌百分比
                - jzrq: 净值日期
                - gztime: 估值时间
        """
        # 确保基金代码为6位数字格式，补前导零
        fund_code = str(fund_code).zfill(6)
        url = f'http://fundgz.1234567.com.cn/js/{fund_code}.js'
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # 检查响应内容是否为空
                if not response.text:
                    print(f"基金 {fund_code} 的响应内容为空")
                    return None
                
                # 尝试匹配 JSON 数据
                match = re.search(r'jsonpgz\((.*?)\);', response.text)
                if match:
                    json_data = match.group(1)
                    # 检查 JSON 数据是否为空
                    if not json_data:
                        print(f"基金 {fund_code} 的 JSON 数据为空")
                        return None
                    
                    try:
                        data = json.loads(json_data)
                        return data
                    except json.JSONDecodeError as e:
                        print(f"基金 {fund_code} 的 JSON 解析错误: {e}")
                        return None
                else:
                    print(f"基金 {fund_code} 的响应数据格式不正确，无法匹配 JSON")
            else:
                print(f"基金 {fund_code} 的响应状态码不是 200: {response.status_code}")
        except requests.RequestException as e:
            print(f"获取基金 {fund_code} 数据时网络错误: {e}")
        except Exception as e:
            print(f"获取基金 {fund_code} 数据失败: {e}")
        return None

    @staticmethod
    def get_realtime_batch(fund_codes):
        """
        批量获取基金实时估值

        参数:
            fund_codes (list): 基金代码列表，如 ['005827', '161725']

        返回:
            DataFrame: 包含所有基金的实时信息
        """
        results = []
        for code in fund_codes:
            data = FundRealTime.get_realtime_nav(code)
            if data:
                results.append(data)
            time.sleep(0.1)  # 避免请求过快

        if results:
            df = pd.DataFrame(results)
            # 选择关键列并重命名
            columns_order = ['fundcode', 'name', 'dwjz', 'gsz', 'gszzl', 'jzrq', 'gztime']
            df = df[columns_order]
            df.columns = ['fund_code', 'fund_name', 'yesterday_nav', 'current_estimate', 'change_percentage', 'nav_date', 'estimate_time']
            # 转换数据类型
            df['change_percentage'] = df['change_percentage'].astype(float)
            df['yesterday_nav'] = df['yesterday_nav'].astype(float)
            df['current_estimate'] = df['current_estimate'].astype(float)
            return df
        return pd.DataFrame()

    @staticmethod
    def monitor_funds(fund_codes, interval=60, duration=3600):
        """
        持续监控基金实时数据

        参数:
            fund_codes (list): 基金代码列表
            interval (int): 刷新间隔（秒），默认60秒
            duration (int): 监控总时长（秒），默认3600秒（1小时）
        """
        start_time = time.time()
        while True:
            current_time = time.time()
            if current_time - start_time > duration:
                print("\n监控结束")
                break

            print(f"\n{'='*80}")
            print(f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}")

            df = FundRealTime.get_realtime_batch(fund_codes)
            if not df.empty:
                print(df.to_string(index=False))
            else:
                print("未能获取到数据")

            print(f"\n{interval}秒后刷新...")
            time.sleep(interval)


# 使用示例
if __name__ == "__main__":
    # 示例基金代码列表
    my_funds = [
        '005827',   # 易方达蓝筹精选混合
        '161725',   # 招商中证白酒指数
        '001102',   # 前海开源国家比较优势混合
        '003096',   # 中欧医疗健康混合
        '110011',   # 易方达优质精选混合
    ]

    print("实时基金净值数据获取工具")
    print("="*80)

    # 1. 获取单只基金数据
    print("\n1. 获取单只基金实时数据示例:")
    fund_data = FundRealTime.get_realtime_nav('005827')
    if fund_data:
        print(f"基金名称: {fund_data['name']}")
        print(f"昨日净值: {fund_data['dwjz']}")
        print(f"实时估值: {fund_data['gsz']}")
        print(f"涨跌: {fund_data['gszzl']}%")

    # 2. 批量获取基金数据
    print("\n2. 批量获取基金实时数据:")
    df = FundRealTime.get_realtime_batch(my_funds)
    if not df.empty:
        print(df.to_string(index=False))

    # 3. 持续监控（取消注释即可使用）
    # print("\n3. 开始持续监控基金数据（按Ctrl+C停止）:")
    # FundRealTime.monitor_funds(my_funds, interval=300, duration=7200)
