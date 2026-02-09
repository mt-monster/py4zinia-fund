#!/usr/bin/env python
# coding: utf-8

"""
测试持仓页面的向前追溯功能
"""

import requests
import json

def test_holdings_forward_trace():
    """测试持仓页面API的向前追溯功能"""
    print("测试持仓页面向前追溯功能")
    print("=" * 60)
    
    try:
        # 获取持仓数据
        response = requests.get("http://localhost:5000/api/holdings?user_id=default_user", timeout=10)
        if response.status_code == 200:
            data = response.json()
            holdings = data.get('data', [])
            
            print(f"持仓基金总数: {len(holdings)}")
            print("-" * 40)
            
            # 查找QDII基金
            qdii_funds = []
            for fund in holdings:
                fund_code = fund.get('fund_code', '')
                fund_name = fund.get('fund_name', '')
                yesterday_return = fund.get('yesterday_return')
                
                # 检查是否为QDII基金
                is_qdii = 'QDII' in fund_name.upper() or fund_code in ['021539', '162415', '007721', '100055']
                
                if is_qdii:
                    qdii_funds.append({
                        'fund_code': fund_code,
                        'fund_name': fund_name,
                        'yesterday_return': yesterday_return
                    })
            
            print(f"发现 {len(qdii_funds)} 只QDII基金:")
            for fund in qdii_funds:
                fund_code = fund['fund_code']
                fund_name = fund['fund_name']
                yesterday_return = fund['yesterday_return']
                
                print(f"  基金代码: {fund_code}")
                print(f"  基金名称: {fund_name}")
                print(f"  昨日收益率: {yesterday_return}%")
                
                # 检查是否成功向前追溯
                if yesterday_return is not None and yesterday_return != 0.0:
                    print("  ✅ 向前追溯成功！")
                else:
                    print("  ❌ 向前追溯失败！")
                print()
            
            # 特别检查华安基金
            huaan_fund = None
            for fund in qdii_funds:
                if fund['fund_code'] == '021539':
                    huaan_fund = fund
                    break
            
            if huaan_fund:
                print("=" * 60)
                print("华安基金(021539)详细信息:")
                print(f"基金代码: {huaan_fund['fund_code']}")
                print(f"基金名称: {huaan_fund['fund_name']}")
                print(f"昨日收益率: {huaan_fund['yesterday_return']}%")
                
                if huaan_fund['yesterday_return'] != 0.0:
                    print("✅ 华安基金向前追溯成功！")
                else:
                    print("❌ 华安基金向前追溯失败！")
            else:
                print("⚠️  持仓中未找到华安基金(021539)")
                
        else:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

def test_single_fund_api():
    """测试单个基金API接口"""
    print("\n" + "=" * 60)
    print("测试单个基金API接口")
    print("=" * 60)
    
    fund_code = '021539'
    fund_name = '华安法国CAC40ETF发起式联接(QDII)A'
    
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
                print("✅ 单个基金API向前追溯成功！")
            else:
                print("❌ 单个基金API向前追溯失败！")
        else:
            print(f"❌ 单个基金API请求失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 单个基金API测试失败: {str(e)}")

if __name__ == "__main__":
    test_holdings_forward_trace()
    test_single_fund_api()