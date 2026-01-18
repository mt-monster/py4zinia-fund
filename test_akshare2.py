import akshare as ak
import traceback

fund_code = '110022'
print(f"Testing fund: {fund_code}")

indicators = [
    "基本信息",
    "基金规模",
    "单位净值走势",
    "分红送转",
    "基金经理",
    "基金信息",
]

for indicator in indicators:
    print(f"\n=== Testing indicator: {indicator} ===")
    try:
        df = ak.fund_open_fund_info_em(symbol=fund_code, indicator=indicator)
        print(f"Shape: {df.shape}")
        if not df.empty:
            print(f"Columns: {df.columns.tolist()}")
            # Show first few rows
            print(df.head(3).to_string())
        else:
            print("Empty DataFrame")
    except Exception as e:
        print(f"Error: {e}")