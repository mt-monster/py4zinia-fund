import requests
import json

# 获取持仓数据
response = requests.get("http://localhost:5001/api/holdings")
data = response.json()

# 检查每个基金的sharpe_ratio_all值
print("Checking sharpe_ratio_all values:")
nan_count = 0
for fund in data['data']:
    sr_all = fund.get('sharpe_ratio_all')
    fund_code = fund.get('fund_code')
    if sr_all is not None:
        print(f"Fund {fund_code}: {sr_all} (type: {type(sr_all)})")
        if str(sr_all).upper() == 'NAN':
            nan_count += 1
            print(f"  *** FOUND NaN VALUE ***")
    else:
        print(f"Fund {fund_code}: None")

print(f"\nTotal NaN values found: {nan_count}")