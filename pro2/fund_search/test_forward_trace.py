#!/usr/bin/env python
# coding: utf-8

"""
测试QDII基金向前追溯功能
"""

import requests
import json

def test_fund_forward_trace(fund_code, fund_name=""):
    """测试单个基金的向前追溯功能"""
    print("=" * 60)
    print(f"测试基金: {fund_code} - {fund_name}")
    print("=" * 60)
    
    try:
        response = requests.get(f"http://localhost:5000/api/fund/{fund_code}", timeout=10)
        if response.status_code == 200:
            data = response.json()['data']
            print(f"基金代码: {data.get('fund_code', 'N/A')}")
            print(f"基金名称: {data.get('fund_name', 'N/A')}")
            print(f"今日收益率: {data.get('today_return', 'N/A')}%")
            print(f"前日收益率: {data.get('prev_day_return', 'N/A')}%")
            print(f"昨日收益率: {data.get('yesterday_return', 'N/A')}%")
            print(f"数据源: {data.get('data_source', 'N/A')}")
            
            # 检查是否成功向前追溯
            prev_return = data.get('prev_day_return', 0)
            if prev_return != 0.0:
                print("✅ 向前追溯成功！")
            else:
                print("❌ 向前追溯失败！")
        else:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
    
    print()

def main():
    """主测试函数"""
    print("QDII基金向前追溯功能测试")
    print("=" * 60)
    
    # 测试基金列表
    test_funds = [
        ('021539', '华安法国CAC40ETF发起式联接(QDII)A'),
        ('162415', '美国消费'),
        ('007721', '天弘标普500发起(QDII-FOF)A'),
        ('100055', '富国全球科技互联网股票(QDII)A')
    ]
    
    for fund_code, fund_name in test_funds:
        test_fund_forward_trace(fund_code, fund_name)

if __name__ == "__main__":
    main()