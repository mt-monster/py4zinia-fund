#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试基金评价 API"""

import requests
import json

url = "http://localhost:5000/api/fund-evaluation/run"

# 测试数据
params = {
    "fund_type": "all",
    "min_score": 0
}

print("发送请求...")
print(f"请求参数: {json.dumps(params, ensure_ascii=False, indent=2)}")

try:
    response = requests.post(url, json=params)
    print(f"\n响应状态码: {response.status_code}")
    print(f"响应内容: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n成功! 共评价 {len(data.get('data', []))} 只基金")
        if data.get('data'):
            print("\n前5只基金:")
            for fund in data['data'][:5]:
                print(f"  {fund['code']} - {fund['name']}: {fund['total_score']}分")
    else:
        print(f"\n失败: {response.json()}")
        
except Exception as e:
    print(f"请求出错: {e}")
