import sys
import os
sys.path.append('pro2/fund_search')

from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
import logging

# 设置日志级别
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_qdii_funds():
    adapter = MultiSourceDataAdapter()
    
    # 测试几个显示为0的QDII基金
    test_funds = ['006105', '012060', '006373', '007721']
    
    for fund_code in test_funds:
        try:
            print(f"\n=== 检查基金 {fund_code} ===")
            data = adapter.get_qdii_fund_data(fund_code)
            
            if data:
                print(f"昨日收益率: {data.get('prev_day_return', 'N/A')}")
                print(f"当日收益率: {data.get('today_return', 'N/A')}")
                print(f"数据源: {data.get('data_source', 'N/A')}")
                print(f"基金名称: {data.get('fund_name', 'N/A')}")
                
                # 检查是否为QDII基金
                is_qdii = adapter.is_qdii_fund(fund_code, data.get('fund_name', ''))
                print(f"是否为QDII基金: {is_qdii}")
                
                # 如果昨日收益率为0，查看历史数据
                if data.get('prev_day_return', 0) == 0:
                    print("昨日收益率为0，尝试获取历史数据...")
                    try:
                        from data_retrieval.enhanced_fund_data import EnhancedFundData
                        hist_data = EnhancedFundData.get_fund_nav_history(fund_code, days=10)
                        if hist_data is not None and not hist_data.empty:
                            print(f"获取到 {len(hist_data)} 条历史数据")
                            if '日增长率' in hist_data.columns:
                                returns = hist_data['日增长率'].tail(5)
                                print("最近5天的日增长率:")
                                for i, ret in enumerate(returns):
                                    print(f"  第{i+1}天: {ret}")
                        else:
                            print("无法获取历史数据")
                    except Exception as hist_e:
                        print(f"获取历史数据失败: {hist_e}")
            else:
                print("无法获取基金数据")
                
        except Exception as e:
            print(f"检查基金 {fund_code} 时出错: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    check_qdii_funds()