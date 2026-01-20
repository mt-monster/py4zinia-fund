import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_retrieval.enhanced_fund_data import EnhancedFundData

def debug_return_values():
    """调试获取的日收益率值"""
    print("开始调试收益率获取...")
    
    try:
        data_manager = EnhancedFundData()
        
        # 使用一个示例基金代码
        fund_code = '001186'
        print(f"\n获取基金 {fund_code} 的实时数据...")
        
        realtime_data = data_manager.get_realtime_data(fund_code)
        if realtime_data:
            print(f"实时数据: {realtime_data}")
            
            if 'yesterday_return' in realtime_data:
                yesterday_return = realtime_data['yesterday_return']
                print(f"yesterday_return (原始): {yesterday_return} (类型: {type(yesterday_return).__name__})")
                
                try:
                    float_val = float(yesterday_return)
                    print(f"yesterday_return (转换为float): {float_val}")
                    print(f"yesterday_return (除以100): {float_val / 100}")
                    print(f"yesterday_return (格式化显示): {float_val:.2f}%")
                    print(f"如果实际应为-0.09%，则原始值应该是: -0.09")
                    print(f"如果原始值是-9.0，则实际百分比应为: -900.0%")
                except ValueError:
                    print(f"无法将 {yesterday_return} 转换为float")
        else:
            print("无法获取实时数据")
            
        # 检查get_fund_basic_info方法
        print(f"\n获取基金 {fund_code} 的基本信息...")
        basic_info = data_manager.get_fund_basic_info(fund_code)
        if basic_info:
            print(f"基本信息: {basic_info}")
            
        print("\n获取历史数据...")
        historical_data = data_manager.get_fund_historical_data(fund_code)
        if historical_data is not None and not historical_data.empty:
            print(f"历史数据列: {list(historical_data.columns)}")
            
            if 'daily_growth_rate' in historical_data.columns:
                recent_growth = historical_data['daily_growth_rate'].dropna().tail(3)
                print(f"最近3天的daily_growth_rate:")
                for i, val in enumerate(recent_growth):
                    print(f"  第{i+1}天: {val} (类型: {type(val).__name__})")
                    
                    try:
                        float_val = float(val)
                        print(f"    转换为float: {float_val}")
                        print(f"    除以100: {float_val / 100}")
                        print(f"    格式化显示: {float_val:.2f}%")
                    except ValueError:
                        print(f"    无法转换为float")
        else:
            print("无法获取历史数据")
            
    except Exception as e:
        print(f"调试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_return_values()