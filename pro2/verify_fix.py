#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证修复后的夏普比率计算"""

import sys
sys.path.insert(0, '.')
from fund_search.data_retrieval.multi_source_adapter import MultiSourceDataAdapter

adapter = MultiSourceDataAdapter()

# 测试001270
print("=" * 60)
print("001270 Sharpe Calculation Verification")
print("=" * 60)

metrics = adapter.get_performance_metrics('001270')

print(f"\nAfter Fix:")
print(f"  sharpe_ratio_all: {metrics['sharpe_ratio_all']:.4f}")
print(f"  sharpe_ratio_1y: {metrics['sharpe_ratio_1y']:.4f}")
print(f"  sharpe_ratio_ytd: {metrics['sharpe_ratio_ytd']:.4f}")
print(f"  annualized_return: {metrics['annualized_return']*100:.2f}%")
print(f"  volatility: {metrics['volatility']*100:.2f}%")

print(f"\nExpected (from document):")
print(f"  sharpe_ratio_all: 0.0436")
print(f"  annualized_return: 3.89%")
print(f"  volatility: 20.41%")

# 测试更多基金
test_funds = ['006373', '020422', '025832', '519196']

print("\n" + "=" * 60)
print("More Funds Verification")
print("=" * 60)

for code in test_funds:
    try:
        m = adapter.get_performance_metrics(code)
        print(f"\n{code}:")
        print(f"  sharpe_all: {m['sharpe_ratio_all']:.4f}")
        print(f"  volatility: {m['volatility']*100:.2f}%")
    except Exception as e:
        print(f"\n{code}: Error - {e}")

print("\n" + "=" * 60)
print("Fix verification completed!")
print("=" * 60)
