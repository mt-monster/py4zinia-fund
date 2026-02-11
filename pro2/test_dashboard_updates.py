#!/usr/bin/env python3
"""
测试仪表盘基金涨跌数据更新功能
"""

import requests
import json
import time
from datetime import datetime

def test_dashboard_updates():
    """测试仪表盘实时更新功能"""
    base_url = "http://localhost:5001"
    
    print("🚀 开始测试仪表盘基金涨跌数据更新功能...")
    print("=" * 50)
    
    # 1. 测试获取持仓基金列表
    print("\n1️⃣ 测试获取持仓基金列表...")
    try:
        holdings_response = requests.get(f"{base_url}/api/holdings/list?user_id=default_user")
        holdings_data = holdings_response.json()
        
        if holdings_data.get('success') and holdings_data.get('data'):
            fund_list = holdings_data['data']
            print(f"✅ 成功获取到 {len(fund_list)} 只持仓基金:")
            for fund in fund_list[:5]:  # 只显示前5只
                print(f"   - {fund['fund_code']}: {fund['fund_name']}")
            if len(fund_list) > 5:
                print(f"   ... 还有 {len(fund_list) - 5} 只基金")
        else:
            print("❌ 未获取到持仓基金数据")
            return
    except Exception as e:
        print(f"❌ 获取持仓基金列表失败: {e}")
        return
    
    # 2. 测试获取单个基金的实时数据
    print("\n2️⃣ 测试获取基金实时涨跌数据...")
    if fund_list:
        test_fund = fund_list[0]
        fund_code = test_fund['fund_code']
        try:
            fund_response = requests.get(f"{base_url}/api/fund/{fund_code}")
            fund_data = fund_response.json()
            
            if fund_data.get('success') and fund_data.get('data'):
                today_return = fund_data['data'].get('today_return', 0)
                current_nav = fund_data['data'].get('current_nav', 0)
                print(f"✅ 基金 {fund_code} 实时数据:")
                print(f"   当日涨跌: {today_return}%")
                print(f"   最新净值: {current_nav}")
            else:
                print(f"❌ 获取基金 {fund_code} 数据失败")
        except Exception as e:
            print(f"❌ 获取基金实时数据失败: {e}")
    
    # 3. 测试批量获取基金数据
    print("\n3️⃣ 测试批量获取基金涨跌数据...")
    fund_codes = [fund['fund_code'] for fund in fund_list[:3]]  # 测试前3只基金
    try:
        fund_data_list = []
        for code in fund_codes:
            response = requests.get(f"{base_url}/api/fund/{code}")
            data = response.json()
            if data.get('success') and data.get('data'):
                fund_data_list.append({
                    'code': code,
                    'name': next((f['fund_name'] for f in fund_list if f['fund_code'] == code), ''),
                    'today_return': data['data'].get('today_return', 0)
                })
        
        if fund_data_list:
            print(f"✅ 成功获取 {len(fund_data_list)} 只基金的涨跌数据:")
            total_change = 0
            positive_count = 0
            negative_count = 0
            
            for fund in fund_data_list:
                change = float(fund['today_return'])
                total_change += change
                if change > 0:
                    positive_count += 1
                    status = "📈 上涨"
                elif change < 0:
                    negative_count += 1
                    status = "📉 下跌"
                else:
                    status = "📊 持平"
                
                print(f"   {fund['code']} {fund['name']}: {change:.2f}% {status}")
            
            avg_change = total_change / len(fund_data_list) if fund_data_list else 0
            print(f"\n📊 统计结果:")
            print(f"   平均涨跌: {avg_change:.2f}%")
            print(f"   上涨基金: {positive_count} 只")
            print(f"   下跌基金: {negative_count} 只")
            print(f"   持平基金: {len(fund_data_list) - positive_count - negative_count} 只")
        else:
            print("❌ 未能获取任何基金的实时数据")
            
    except Exception as e:
        print(f"❌ 批量获取基金数据失败: {e}")
    
    # 4. 测试仪表盘统计数据接口
    print("\n4️⃣ 测试仪表盘统计数据接口...")
    try:
        dashboard_response = requests.get(f"{base_url}/api/dashboard/stats")
        dashboard_data = dashboard_response.json()
        
        if dashboard_response.status_code == 200 and dashboard_data.get('success'):
            stats = dashboard_data.get('data', {})
            print("✅ 仪表盘统计数据:")
            print(f"   持仓金额: {stats.get('totalAssets', '--')}")
            print(f"   今日收益: {stats.get('todayProfit', '--')}")
            print(f"   持仓基金数: {stats.get('holdingCount', '--')}")
            print(f"   夏普比率: {stats.get('sharpeRatio', '--')}")
        else:
            print("❌ 仪表盘统计数据接口异常")
            
    except Exception as e:
        print(f"❌ 测试仪表盘接口失败: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 测试完成！请在浏览器中访问 http://localhost:5001/dashboard 查看实时更新效果")
    print("💡 建议操作：")
    print("   1. 打开仪表盘页面")
    print("   2. 观察'今日收益'卡片中的涨跌数据显示")
    print("   3. 等待15-30秒查看自动更新效果")
    print("   4. 检查控制台是否有'[实时更新]'相关的日志输出")

if __name__ == "__main__":
    test_dashboard_updates()