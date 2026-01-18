import akshare as ak
import sys
sys.path.insert(0, 'D:/coding/trae_project/py4zinia/pro2/fund_search')

from data_retrieval.enhanced_fund_data import EnhancedFundData

fund_code = '110022'
print(f"Testing fund: {fund_code}")

# Test the get_realtime_data function
print("\n=== Testing get_realtime_data ===")
realtime_result = EnhancedFundData.get_realtime_data(fund_code)
print(f"Realtime data result:")
for key, value in result.items():
    print(f"  {key}: {value}")

# Test raw akshare data
print("
=== Testing raw akshare data ===")
try:
    df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
    if not df.empty:
        print("Last 5 rows of nav data:")
        print(df.tail(5).to_string())
        print(f"\n日增长率 column values: {df['日增长率'].tail(5).tolist()}")
    else:
        print("No nav data")
except Exception as e:
    print(f"Error: {e}")
