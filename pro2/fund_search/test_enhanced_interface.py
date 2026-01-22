#!/usr/bin/env python
# coding: utf-8

"""
测试增强后的Web界面功能
"""

import requests
import json
import base64
from PIL import Image, ImageDraw, ImageFont
import io

def create_mock_fund_screenshot():
    """创建一个模拟的基金持仓截图，包含文本信息"""
    # 创建一个更大的图片
    img = Image.new('RGB', (800, 1200), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        # 尝试使用系统字体
        font = ImageFont.truetype("arial.ttf", 20)
        small_font = ImageFont.truetype("arial.ttf", 16)
    except:
        # 如果没有找到字体，使用默认字体
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # 绘制标题
    draw.text((50, 50), "基金持仓", fill='black', font=font)
    
    # 绘制基金信息
    y_pos = 100
    funds_data = [
        ("天弘标普500发起", "681.30", "+21.11", "+3.20%"),
        ("景顺长城全球半", "664.00", "+83.08", "+15.08%"),
        ("导体芯片股票A", "", "", ""),
        ("广发北证50成份指", "568.11", "+15.10", "+2.83%"),
        ("数A", "", "", ""),
        ("富国全球科技互联", "438.25", "+28.42", "+7.29%"),
        ("网股票(QDII)A", "", "", ""),
        ("易方达战略新兴产", "429.02", "+21.21", "+5.33%"),
        ("业股票A", "", "", "")
    ]
    
    for fund_name, amount, profit, rate in funds_data:
        draw.text((50, y_pos), fund_name, fill='black', font=small_font)
        if amount:
            draw.text((300, y_pos), amount, fill='black', font=small_font)
        if profit:
            color = 'green' if profit.startswith('+') else 'red'
            draw.text((450, y_pos), profit, fill=color, font=small_font)
        if rate:
            color = 'green' if rate.startswith('+') else 'red'
            draw.text((600, y_pos), rate, fill=color, font=small_font)
        y_pos += 40
    
    # 将图片转换为base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_data = buffer.getvalue()
    
    # 转换为base64字符串
    base64_data = base64.b64encode(img_data).decode('utf-8')
    return f"data:image/png;base64,{base64_data}"

def test_enhanced_web_interface():
    """测试增强后的Web界面"""
    print("🧪 测试增强后的Web界面...")
    
    # 创建模拟截图
    test_image = create_mock_fund_screenshot()
    
    # 准备API请求
    url = "http://127.0.0.1:5000/api/holdings/import/screenshot"
    payload = {
        "image": test_image,
        "use_gpu": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        print(f"HTTP状态码: {response.status_code}")
        
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
                    
                    if summary.get('best_fund'):
                        print(f"  表现最佳: {summary['best_fund']['fund_name']} ({summary['best_fund']['profit_rate']:+.2f}%)")
                    if summary.get('worst_fund'):
                        print(f"  表现最差: {summary['worst_fund']['fund_name']} ({summary['worst_fund']['profit_rate']:+.2f}%)")
                
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

def main():
    """主函数"""
    print("🚀 测试增强后的基金持仓识别界面")
    print("=" * 60)
    
    # 测试Web界面
    success = test_enhanced_web_interface()
    
    if success:
        print("\n🎉 测试成功！")
        print("💡 您可以访问以下页面查看增强后的界面:")
        print("   - 主功能页面: http://127.0.0.1:5000/test-holding-recognition")
        print("   - 功能导航页面: http://127.0.0.1:5000/holding-nav")
        print("   - 演示结果页面: http://127.0.0.1:5000/demo-holding-result")
    else:
        print("\n❌ 测试失败")
        print("💡 请确保Web服务器正在运行: python pro2/fund_search/web/app.py")

if __name__ == "__main__":
    main()