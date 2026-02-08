#!/usr/bin/env python
# coding: utf-8
"""
诊断脚本：检查沪深300数据获取是否正常
"""

import sys
sys.path.insert(0, 'D:/coding/traeCN_project/py4zinia/pro2/fund_search/web')

from real_data_fetcher import RealDataFetcher
from datetime import datetime, timedelta

def check_csi300_data():
    print("=" * 60)
    print("沪深300数据获取诊断")
    print("=" * 60)
    
    # 测试1：获取最近400天的数据
    print("\n【测试1】获取最近400天的沪深300数据")
    df = RealDataFetcher.get_csi300_history(400)
    if df.empty:
        print("❌ 失败：无法获取数据")
        return
    
    print(f"✅ 成功获取 {len(df)} 条数据")
    print(f"   日期范围: {df['date'].min()} 至 {df['date'].max()}")
    print(f"   价格范围: {df['price'].min():.2f} - {df['price'].max():.2f}")
    
    # 测试2：检查特定日期的数据
    print("\n【测试2】检查特定日期的数据")
    test_dates = ['2021-09-22', '2022-09-22', '2023-09-22', '2024-09-22']
    
    df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
    
    for date_str in test_dates:
        if date_str in df['date_str'].values:
            price = df[df['date_str'] == date_str]['price'].values[0]
            print(f"   ✅ {date_str}: {price:.2f}")
        else:
            print(f"   ❌ {date_str}: 不在数据中")
    
    # 测试3：检查数据连续性
    print("\n【测试3】检查数据连续性")
    df_sorted = df.sort_values('date')
    gaps = 0
    for i in range(1, len(df_sorted)):
        prev_date = df_sorted.iloc[i-1]['date']
        curr_date = df_sorted.iloc[i]['date']
        diff = (curr_date - prev_date).days
        if diff > 3:  # 超过3天的间隔（考虑周末）
            gaps += 1
            if gaps <= 3:  # 只显示前3个间隔
                print(f"   ⚠️ 发现数据间隔: {prev_date.date()} 至 {curr_date.date()} ({diff}天)")
    
    if gaps == 0:
        print("   ✅ 数据连续，无大间隔")
    else:
        print(f"   ⚠️ 共发现 {gaps} 个数据间隔")
    
    # 测试4：根据回测日期范围获取数据
    print("\n【测试4】模拟回测日期范围数据获取")
    # 模拟3年前的回测
    start_date = datetime.now() - timedelta(days=3*365)
    days_needed = (datetime.now() - start_date).days + 60
    print(f"   回测起始日期: {start_date.date()}")
    print(f"   需要获取天数: {days_needed}")
    
    df_long = RealDataFetcher.get_csi300_history(days_needed)
    if df_long.empty:
        print("❌ 失败：无法获取数据")
        return
    
    print(f"✅ 成功获取 {len(df_long)} 条数据")
    print(f"   日期范围: {df_long['date'].min()} 至 {df_long['date'].max()}")
    
    # 检查回测起始日期是否在数据中
    start_date_str = start_date.strftime('%Y-%m-%d')
    df_long['date_str'] = df_long['date'].dt.strftime('%Y-%m-%d')
    
    if start_date_str in df_long['date_str'].values:
        print(f"   ✅ 回测起始日期 {start_date_str} 在数据中")
    else:
        print(f"   ❌ 回测起始日期 {start_date_str} 不在数据中")
        # 找最近的日期
        df_long['date'] = pd.to_datetime(df_long['date'])
        df_long['diff'] = abs(df_long['date'] - start_date)
        closest = df_long.loc[df_long['diff'].idxmin()]
        print(f"   最近的可用日期: {closest['date_str']} (相差 {closest['diff'].days} 天)")
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == '__main__':
    import pandas as pd  # 确保pandas可用
    check_csi300_data()
