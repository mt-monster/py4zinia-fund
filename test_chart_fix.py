import requests
import json

def test_chart_fix():
    """测试净值曲线图表修复效果"""
    
    print("🔍 测试净值曲线图表修复效果")
    print("=" * 50)
    
    # 1. 测试API数据获取
    print("\n1️⃣ 测试API数据获取...")
    try:
        response = requests.get(
            'http://127.0.0.1:5000/api/dashboard/profit-trend',
            params={
                'days': 30,
                'fund_codes': '000001',
                'weights': '1.0'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ API数据获取成功")
                print(f"   - 数据点数量: {len(data['data']['labels'])}")
                print(f"   - 数据源: {data['data'].get('data_source', 'unknown')}")
                print(f"   - 组合净值范围: ¥{min(data['data']['profit']):.2f} - ¥{max(data['data']['profit']):.2f}")
                print(f"   - 基准净值范围: ¥{min(data['data']['benchmark']):.2f} - ¥{max(data['data']['benchmark']):.2f}")
            else:
                print("❌ API返回失败:", data.get('error', 'Unknown error'))
                return False
        else:
            print("❌ API请求失败:", response.status_code)
            return False
            
    except Exception as e:
        print("❌ API测试异常:", str(e))
        return False
    
    # 2. 测试策略API
    print("\n2️⃣ 测试策略API...")
    try:
        response = requests.get('http://127.0.0.1:5000/api/strategies/metadata', timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('data'):
                print(f"✅ 策略API正常 - 加载 {len(data['data'])} 个策略")
                for strategy in data['data'][:3]:  # 显示前3个
                    print(f"   - {strategy['name']}: {strategy['description']} ({strategy['total_return']}%)")
            else:
                print("❌ 策略API返回失败")
                return False
        else:
            print("❌ 策略API请求失败")
            return False
    except Exception as e:
        print("❌ 策略API测试异常:", str(e))
        return False
    
    # 3. 测试调试页面
    print("\n3️⃣ 测试调试页面...")
    try:
        response = requests.get('http://127.0.0.1:5000/chart_debug', timeout=10)
        if response.status_code == 200:
            print("✅ 图表调试页面可访问")
        else:
            print("❌ 调试页面访问失败")
            return False
    except Exception as e:
        print("❌ 调试页面测试异常:", str(e))
        return False
    
    print("\n" + "=" * 50)
    print("🎉 所有测试通过！净值曲线图表应该可以正常显示了")
    print("\n📝 修复要点:")
    print("1. 修复了异步数据获取问题 - showAnalysis现在等待数据加载完成")
    print("2. 添加了适当的错误处理和用户反馈")
    print("3. 为图表容器添加了正确的CSS样式")
    print("4. 确保Canvas元素正确初始化和渲染")
    print("\n🚀 建议操作:")
    print("1. 访问 http://127.0.0.1:5000/strategy.html")
    print("2. 进行一次基金回测")
    print("3. 点击'查看投资组合深度分析'按钮")
    print("4. 观察净值曲线图表是否正常显示")
    
    return True

if __name__ == "__main__":
    test_chart_fix()