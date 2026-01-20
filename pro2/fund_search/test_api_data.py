import requests
import json

# 测试获取基金实时数据
try:
    # 使用一个示例基金代码
    fund_code = '001186'
    response = requests.get(f'http://localhost:5000/api/fund/{fund_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'基金 {fund_code} 数据：')
        if data.get('success'):
            fund_data = data['data']
            for key, value in fund_data.items():
                if key in ['today_return', 'prev_day_return', 'yesterday_return']:
                    print(f'{key}: {value} (类型: {type(value).__name__})')
        else:
            print(f'获取失败: {data.get("error")}')
    else:
        print(f'请求失败，状态码: {response.status_code}')
        print(f'响应内容: {response.text}')
except Exception as e:
    print(f'请求错误: {e}')