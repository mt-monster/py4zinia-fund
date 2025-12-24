#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时基金数据获取 - 使用示例
"""

from fund_realtime import FundRealTime
import pandas as pd

# 示例1: 获取单只基金实时数据
print("="*80)
print("示例1: 获取单只基金实时数据")
print("="*80)

fund_code = '005551'  # 易方达蓝筹精选混合
data = FundRealTime.get_realtime_nav(fund_code)

if data:
    print(f"\n基金代码: {data['fundcode']}")
    print(f"基金名称: {data['name']}")
    print(f"昨日净值: {data['dwjz']}")
    print(f"实时估值: {data['gsz']}")
    print(f"涨跌幅度: {data['gszzl']}%")
    print(f"净值日期: {data['jzrq']}")
    print(f"估值时间: {data['gztime']}")


# 示例2: 批量获取多只基金数据
print("\n" + "="*80)
print("示例2: 批量获取多只基金数据")
print("="*80)

my_fund_list = [
    '005827',   # 易方达蓝筹精选混合
    '161725',   # 招商中证白酒指数
    '001102',   # 前海开源国家比较优势混合
    '003096',   # 中欧医疗健康混合
    '110011',   # 易方达优质精选混合
    '007300',   # 国寿安保货币A（货币基金）
    '000172',   # 华泰柏瑞量化增强混合
]

df = FundRealTime.get_realtime_batch(my_fund_list)
if not df.empty:
    print("\n您的基金组合实时数据：")
    print(df.to_string(index=False))
    
    # 计算整体情况
    print("\n组合统计：")
    print(f"持有基金数量: {len(df)}")
    print(f"上涨基金数量: {len(df[df['涨跌(%)'] > 0])}")
    print(f"下跌基金数量: {len(df[df['涨跌(%)'] < 0])}")
    print(f"平均涨跌幅: {df['涨跌(%)'].mean():.2f}%")
    print(f"最大涨幅: {df['涨跌(%)'].max():.2f}%")
    print(f"最大跌幅: {df['涨跌(%)'].min():.2f}%")


# 示例3: 实时监控（简化版，监控5次，每次间隔10秒）
print("\n" + "="*80)
print("示例3: 实时监控演示（监控5次，间隔10秒）")
print("="*80)

monitor_funds = ['005827', '161725']
for i in range(5):
    print(f"\n第 {i+1} 次查询（{pd.Timestamp.now().strftime('%H:%M:%S')}）：")
    df = FundRealTime.get_realtime_batch(monitor_funds)
    if not df.empty:
        for _, row in df.iterrows():
            print(f"  {row['基金名称']}: {row['实时估值']} ({row['涨跌(%)']:+.2f}%)")
    if i < 4:
        print("  等待10秒...")
        import time
        time.sleep(10)

print("\n监控演示结束")


# 示例4: 保存数据到CSV
print("\n" + "="*80)
print("示例4: 保存数据到CSV文件")
print("="*80)

df = FundRealTime.get_realtime_batch(my_fund_list)
if not df.empty:
    filename = f"fund_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\n数据已保存到: {filename}")
    print(f"文件包含 {len(df)} 只基金的数据")


# 示例5: 筛选关注的数据
print("\n" + "="*80)
print("示例5: 数据筛选与分析")
print("="*80)

df = FundRealTime.get_realtime_batch(my_fund_list)
if not df.empty:
    print("\n今日表现最好和最差的基金：")
    print("\n涨幅前三：")
    top3 = df.nlargest(3, '涨跌(%)')
    for _, row in top3.iterrows():
        print(f"  {row['基金名称']}: {row['涨跌(%)']:+.2f}%")
    
    print("\n跌幅前三：")
    bottom3 = df.nsmallest(3, '涨跌(%)')
    for _, row in bottom3.iterrows():
        print(f"  {row['基金名称']}: {row['涨跌(%)']:+.2f}%")
    
    # 筛选涨跌幅度大于1%的基金
    print("\n波动较大的基金（涨跌幅度>1%）：")
    volatile = df[abs(df['涨跌(%)']) > 1.0]
    if not volatile.empty:
        for _, row in volatile.iterrows():
            direction = "上涨" if row['涨跌(%)'] > 0 else "下跌"
            print(f"  {row['基金名称']}: {direction} {abs(row['涨跌(%)']):.2f}%")
    else:
        print("  今日没有波动超过1%的基金")

print("\n" + "="*80)
print("所有示例运行完成！")
print("="*80)
