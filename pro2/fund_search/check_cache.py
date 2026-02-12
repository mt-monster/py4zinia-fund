#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查预加载缓存状态
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("检查预加载缓存状态")
print("=" * 60)

from services.fund_data_preloader import get_preloader

preloader = get_preloader()

# 检查预加载状态
status = preloader.get_preload_status()
print("\n预加载状态:")
print(f"  started: {status.get('started')}")
print(f"  completed: {status.get('completed')}")
print(f"  progress: {status.get('progress')}")

# 检查缓存统计
cache_stats = preloader.get_cache_stats()
print("\n缓存统计:")
print(f"  size: {cache_stats.get('size')}")
print(f"  max_size: {cache_stats.get('max_size')}")
print(f"  hit_rate: {cache_stats.get('hit_rate')}")

# 检查具体基金
print("\n检查具体基金缓存:")
test_codes = ['000001', '007721', '020422', '022741']

for code in test_codes:
    latest = preloader.get_fund_latest_nav(code)
    if latest:
        print(f"  {code}: ✓")
        print(f"    nav: {latest.get('nav')}")
        print(f"    daily_return: {latest.get('daily_return')}")
        print(f"    date: {latest.get('date')}")
    else:
        print(f"  {code}: ✗ 缓存中无数据")

print("\n" + "=" * 60)
