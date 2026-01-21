import requests
import json

# 测试获取持仓数据
try:
    response = requests.get('http://localhost:5000/api/holdings')
    if response.status_code == 200:
        data = response.json()
        print('持仓数据获取成功：')
        print(f'总数量: {data.get("total", 0)}')
        
        if data.get("data"):
            print('\n第一条持仓数据：')
            first_holding = data["data"][0]
            for key, value in first_holding.items():
                if key in ['today_return', 'prev_day_return', 'yesterday_return']:
                    print(f'{key}: {value} (类型: {type(value).__name__})')
        else:
            print('没有持仓数据')
    else:
        print(f'请求失败，状态码: {response.status_code}')
        print(f'响应内容: {response.text}')
except Exception as e:
    print(f'请求错误: {e}')