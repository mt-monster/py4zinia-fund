#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调试波动率计算"""

import sys
sys.path.insert(0, '.')
import numpy as np
import pandas as pd
from fund_search.data_retrieval.multi_source_adapter import MultiSourceDataAdapter

adapter = MultiSourceDataAdapter()

# 获取001270的历史数据
hist_data = adapter.get_historical_data('001270', days=3650)

print("=" * 80)
print("001270 波动率计算调试")
print("=" * 80)

print("\n数据列名:", hist_data.columns.tolist())
print("\n前5条数据:")
print(hist_data[['date', 'nav', 'daily_return']].head().to_string())

# 检查日收益率数据
daily_returns = hist_data['daily_return'].dropna()
print(f"\n日收益率统计:")
print(f"  样本数: {len(daily_returns)}")
print(f"  均值: {daily_returns.mean():.6f}")
print(f"  标准差: {daily_returns.std():.6f}")
print(f"  最小值: {daily_returns.min():.6f}")
print(f"  最大值: {daily_returns.max():.6f}")

# 判断数据格式
mean_abs = abs(daily_returns).mean()
print(f"\n绝对值均值: {mean_abs:.6f}")

if mean_abs < 0.1:
    print("判断: 日收益率已经是小数格式 (如 0.01 表示 1%)")
    daily_returns_decimal = daily_returns
else:
    print("判断: 日收益率是百分比格式 (如 1 表示 1%)")
    daily_returns_decimal = daily_returns / 100

print(f"\n转换后的日收益率统计:")
print(f"  均值: {daily_returns_decimal.mean():.6f}")
print(f"  标准差: {daily_returns_decimal.std():.6f}")

# 计算年化波动率
volatility_annual = daily_returns_decimal.std() * np.sqrt(252)
print(f"\n年化波动率计算:")
print(f"  日收益率标准差: {daily_returns_decimal.std():.6f}")
print(f"  sqrt(252): {np.sqrt(252):.4f}")
print(f"  年化波动率: {volatility_annual:.6f} ({volatility_annual*100:.2f}%)")
