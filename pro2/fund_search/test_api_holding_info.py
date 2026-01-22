#!/usr/bin/env python
# coding: utf-8

"""
测试Web API的持仓信息识别功能
"""

import requests
import json
import base64
from PIL import Image
import io

def create_test_image():
    """创建一个测试图片（模拟基金持仓截图）"""
    # 创建一个简单的测试图片
    img = Image.new('RGB', (400, 600), color='white')
    
    # 将图片转换为base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_data = buffer.getvalue()
    
    # 转换为base64字符串
    base64_data = base64.b64encode(img_data).decode('utf-8')
    return f"data:image/png;base64,{base64_data}"

def test_api_with_mock_data():
    """使用模拟数据测试API"""
    
    # 模拟OCR识别结果（直接调用智能解析器）
    from data_retrieval.smart_fund_parser import parse_fund_info_with_manual_fallback
    
    # 使用之前测试成功的OCR文本
    test_texts = [
        '12:45', '63', '基金持仓', '理财师', '我的持有 吕', '金额排序', 
        '全部(53)', '股票型(8)', '债券型(0)', '基金名称', '持仓收益/率', 
        '天弘标普500发起',  # 基金名称开头
        '681.30',           # 持仓金额
        '+21.11',           # 盈亏金额
        '(QDIIFOF)A',       # 基金名称结尾
        '+3.20%',           # 盈亏率
        '交易: 1笔赎回中合计7.10份', 
        '景顺长城全球半',   # 基金名称开头
        '664.00',           # 持仓金额
        '+83.08',           # 盈亏金额
        '导体芯片股票A(.',  # 基金名称结尾
        '-1.20',            # 另一个数字（可能是净值变化）
        '+15.08%',          # 盈亏率
        '交易:  3笔买入中合计30.00元', 
        '广发北证50成份指', # 基金名称开头
        '568.11',           # 持仓金额
        '+15.10',           # 盈亏金额
        '数A',              # 基金名称结尾
        '-10.34',           # 另一个数字
        '+2.83%',           # 盈亏率
        '交易: 1笔买入中合计20.00元', 
        '富国全球科技互联', # 基金名称开头
        '438.25',           # 持仓金额
        '+28.42',           # 盈亏金额
        ' 网股票(QDII)A',   # 基金名称结尾
        '+7.29%',           # 盈亏率
        '交易:  2笔买入中合计20.00元', 
        '易方达战略新兴产', # 基金名称开头
        '429.02',           # 持仓金额
        '+21.21',           # 盈亏金额
        '业股票A',          # 基金名称结尾
        '-9.68',            # 另一个数字
        '+5.33%',           # 盈亏率
        '交易: 1笔买入中合计10.00元', 
        '基金', '全球投资', '基金圈', '自选', '持仓'
    ]
    
    print("🧪 测试智能解析器...")
    result = parse_fund_info_with_manual_fallback(test_texts)
    
    if result['success']:
        print(f"✅ 解析成功，识别到 {result['funds_count']} 个基金")
        
        # 显示解析结果
        print("\n📊 解析结果:")
        print("=" * 120)
        print(f"{'序号':<4} {'基金代码':<8} {'基金名称':<35} {'持仓金额':<10} {'盈亏金额':<10} {'盈亏率':<10}")
        print("-" * 120)
        
        total_holding = 0
        total_profit = 0
        
        for i, fund in enumerate(result['funds'], 1):
            name_display = fund['fund_name'][:30] + "..." if len(fund['fund_name']) > 30 else fund['fund_name']
            holding_amount = fund.get('holding_amount', 0) or 0
            profit_amount = fund.get('profit_amount', 0) or 0
            profit_rate = fund.get('profit_rate', 0) or 0
            
            total_holding += holding_amount
            total_profit += profit_amount
            
            print(f"{i:<4} {fund['fund_code']:<8} {name_display:<35} {holding_amount:<10.2f} {profit_amount:<10.2f} {profit_rate:<10.2f}%")
        
        total_value = total_holding + total_profit
        total_rate = (total_profit / total_holding * 100) if total_holding > 0 else 0
        
        print("-" * 120)
        print(f"{'汇总':<4} {'总计':<8} {'投资组合':<35} {total_holding:<10.2f} {total_profit:<10.2f} {total_rate:<10.2f}%")
        print(f"当前总市值: {total_value:.2f} 元")
        
        return result
    else:
        print("❌ 解析失败")
        return None

def test_web_api():
    """测试Web API"""
    print("\n🌐 测试Web API...")
    
    # 创建测试图片
    test_image = create_test_image()
    
    # 准备API请求
    url = "http://127.0.0.1:5000/api/holdings/import/screenshot"
    payload = {
        "image": test_image,
        "use_gpu": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ API调用成功")
                print(f"识别到 {len(data.get('data', []))} 个基金")
                
                # 显示投资组合汇总
                if 'portfolio_summary' in data:
                    summary = data['portfolio_summary']
                    print(f"\n📈 投资组合汇总:")
                    print(f"  基金数量: {summary.get('total_funds', 0)}")
                    print(f"  持仓成本: ¥{summary.get('total_holding_amount', 0):,.2f}")
                    print(f"  盈亏金额: ¥{summary.get('total_profit_amount', 0):+,.2f}")
                    print(f"  当前市值: ¥{summary.get('total_current_value', 0):,.2f}")
                    print(f"  总盈亏率: {summary.get('total_profit_rate', 0):+.2f}%")
                
                # 显示基金详情
                print(f"\n🎯 基金详情:")
                for fund in data.get('data', []):
                    print(f"  {fund.get('fund_code')} - {fund.get('fund_name', '')[:30]}...")
                    print(f"    持仓: ¥{fund.get('holding_amount', 0) or 0:.2f}")
                    print(f"    盈亏: ¥{fund.get('profit_amount', 0) or 0:+.2f} ({fund.get('profit_rate', 0) or 0:+.2f}%)")
                    print(f"    市值: ¥{fund.get('current_value', 0) or 0:.2f}")
                
                return True
            else:
                print(f"❌ API返回失败: {data.get('error', '未知错误')}")
                return False
        else:
            print(f"❌ HTTP请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求异常: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始测试基金持仓信息识别功能")
    print("=" * 60)
    
    # 测试智能解析器
    parser_result = test_api_with_mock_data()
    
    # 测试Web API
    if parser_result:
        api_result = test_web_api()
        
        if api_result:
            print("\n🎉 所有测试通过！")
            print("💡 您可以访问 http://127.0.0.1:5000/test-holding-recognition 查看Web界面")
        else:
            print("\n⚠️ Web API测试失败，但解析器工作正常")
    else:
        print("\n❌ 解析器测试失败")