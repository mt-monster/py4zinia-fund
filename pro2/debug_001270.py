#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调试001270基金数据"""

import sys
sys.path.insert(0, '.')

import pandas as pd
from fund_search.data_retrieval.multi_source_adapter import MultiSourceDataAdapter

adapter = MultiSourceDataAdapter()

# 获取历史数据
hist_data = adapter.get_historical_data('001270', days=3650)

print("=" * 80)
print("001270 历史数据列名:", hist_data.columns.tolist())
print("=" * 80)
print("\n前5条数据:")
print(hist_data.head().to_string())
print("\n后5条数据:")
print(hist_data.tail().to_string())

# 检查列名映射
nav_col = '累计净值' if '累计净值' in hist_data.columns else 'nav'
print(f"\n选择的净值列: {nav_col}")

if nav_col in hist_data.columns:
    print(f"\n使用列 '{nav_col}' 的数据:")
    print(f"  第一条: {hist_data[nav_col].iloc[0]}")
    print(f"  最后一条: {hist_data[nav_col].iloc[-1]}")
else:
    print(f"\n[ERR] 列 '{nav_col}' 不存在于数据中!")
    print("可用列:", hist_data.columns.tolist())

# 检查 accum_nav 列
if 'accum_nav' in hist_data.columns:
    print(f"\n列 'accum_nav' 的数据:")
    print(f"  第一条: {hist_data['accum_nav'].iloc[0]}")
    print(f"  最后一条: {hist_data['accum_nav'].iloc[-1]}")

# 检查 nav 列
if 'nav' in hist_data.columns:
    print(f"\n列 'nav' 的数据:")
    print(f"  第一条: {hist_data['nav'].iloc[0]}")
    print(f"  最后一条: {hist_data['nav'].iloc[-1]}")
