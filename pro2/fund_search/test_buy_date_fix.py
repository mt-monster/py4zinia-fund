#!/usr/bin/env python3
"""
测试buy_date字段修复效果
"""

import requests
import json
import logging

logging.basicConfig(level=logging.INFO)

def test_empty_buy_date():
    """测试空buy_date的更新"""
    url = 'http://localhost:5000/api/holdings/008401'
    
    # 测试数据 - 包含空的buy_date
    data = {
        'user_id': 'default_user',
        'fund_code': '008401',
        'fund_name': '华夏恒生互联网科技业ETF联接(QDII)A',
        'holding_shares': 120.18,
        'cost_price': 1.0,
        'buy_date': '',  # 空字符串 - 这就是导致错误的原因
        'notes': '测试空日期更新'
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.put(url, data=json.dumps(data), headers=headers)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ 修复成功！空buy_date可以正常处理")
            else:
                print(f"❌ 更新失败: {result.get('error')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保Flask应用正在运行")
    except Exception as e:
        print(f"❌ 测试出错: {str(e)}")

def test_null_buy_date():
    """测试None buy_date的更新"""
    url = 'http://localhost:5000/api/holdings/008401'
    
    data = {
        'user_id': 'default_user',
        'fund_code': '008401',
        'fund_name': '华夏恒生互联网科技业ETF联接(QDII)A',
        'holding_shares': 120.18,
        'cost_price': 1.0,
        'buy_date': None,  # None值
        'notes': '测试None日期更新'
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.put(url, data=json.dumps(data), headers=headers)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ None buy_date处理正常")
            else:
                print(f"❌ 更新失败: {result.get('error')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试出错: {str(e)}")

def test_valid_buy_date():
    """测试有效的buy_date"""
    url = 'http://localhost:5000/api/holdings/008401'
    
    data = {
        'user_id': 'default_user',
        'fund_code': '008401',
        'fund_name': '华夏恒生互联网科技业ETF联接(QDII)A',
        'holding_shares': 120.18,
        'cost_price': 1.0,
        'buy_date': '2024-01-15',  # 有效日期
        'notes': '测试有效日期更新'
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.put(url, data=json.dumps(data), headers=headers)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ 有效日期处理正常")
            else:
                print(f"❌ 更新失败: {result.get('error')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试出错: {str(e)}")

if __name__ == '__main__':
    print("=== 测试buy_date字段修复 ===")
    print("\n1. 测试空字符串buy_date:")
    test_empty_buy_date()
    
    print("\n2. 测试None buy_date:")
    test_null_buy_date()
    
    print("\n3. 测试有效buy_date:")
    test_valid_buy_date()
    
    print("\n=== 测试完成 ===")