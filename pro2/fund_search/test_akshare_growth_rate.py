import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

# 测试AKShare返回的日增长率格式
def test_akshare_growth_rate():
    """测试AKShare返回的日增长率格式"""
    print("开始测试AKShare日增长率格式...")
    
    # 使用一个示例基金代码
    fund_code = '001186'
    print(f"\n获取基金 {fund_code} 的历史数据...")
    
    try:
        # 获取基金历史净值数据
        fund_hist = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
        
        if fund_hist.empty:
            print("AKShare返回空数据")
            return
        
        print(f"数据列: {list(fund_hist.columns)}")
        print(f"总行数: {len(fund_hist)}")
        
        # 查看最近3条数据
        recent_data = fund_hist.tail(3)
        print("\n最近3条数据:")
        print(recent_data)
        
        # 查看日增长率列的类型和实际值
        if '日增长率' in fund_hist.columns:
            growth_rates = recent_data['日增长率']
            print("\n日增长率数据:")
            for i, (idx, val) in enumerate(growth_rates.items()):
                print(f"第{i+1}条: 值={val} (类型: {type(val).__name__})")
                
                # 尝试转换为float
                try:
                    if isinstance(val, str):
                        # 去除百分号并转换
                        val_str = val.replace('%', '')
                        float_val = float(val_str)
                        print(f"   去除%后: {val_str} -> float: {float_val}")
                        print(f"   转换为小数: {float_val / 100}")
                        print(f"   直接显示: {float_val:.2f}%")
                    elif isinstance(val, (int, float)):
                        print(f"   直接转换: {val}%")
                        print(f"   转换为小数: {val / 100}")
                except ValueError as e:
                    print(f"   转换失败: {e}")
    
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_akshare_growth_rate()