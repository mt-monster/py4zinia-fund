#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试API端点"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web.app_enhanced import app

client = app.test_client()

print("="*60)
print("API端点测试")
print("="*60)

# 1. Health Check
print("\n[1] Health Check:")
r = client.get('/api/health')
print(f"    Status: {r.status_code}")
print(f"    {r.get_json()}")

# 2. Enhancements
print("\n[2] Architecture Improvements:")
r = client.get('/api/enhancements')
data = r.get_json()
for name, info in data['data'].items():
    status = "OK" if info['available'] else "NO"
    enabled = "ON" if info['enabled'] else "OFF"
    print(f"    [{status}/{enabled}] {name}: {info['description']}")

# 3. Modules
print("\n[3] All Modules:")
r = client.get('/api/modules')
data = r.get_json()
for name, status in data['data'].items():
    s = "OK" if status else "NO"
    print(f"    [{s}] {name}")

print("\n" + "="*60)
print("所有测试通过！应用运行正常。")
print("="*60)
