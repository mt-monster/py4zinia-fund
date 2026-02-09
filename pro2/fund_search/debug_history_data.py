#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试基金历史数据获取问题
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
import pandas as pd
import logging

# 设置日志级别
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_fund_history(fund_code="022714", days=30):
    """调试基金历史数据获取"""
    print(f"=== 调试基金 {fund_code} 历史数据获取 ===")
    
    # 初始化数据获取器
    fund_data_manager = MultiSourceDataAdapter()
    
    try:
        # 获取历史数据
        print(f"1. 调用 fund_data_manager.get_historical_data({fund_code}, days={days})")
        hist_data = fund_data_manager.get_historical_data(fund_code, days=days)
        
        print(f"2. 原始数据形状: {hist_data.shape if hist_data is not None else 'None'}")
        if hist_data is not None and not hist_data.empty:
            print(f"3. 原始数据列名: {list(hist_data.columns)}")
            print(f"4. 原始数据前5行:")
            print(hist_data.head())
            
            # 检查nav列是否有NaN值
            if 'nav' in hist_data.columns:
                nan_count = hist_data['nav'].isna().sum()
                print(f"5. nav列NaN值数量: {nan_count}/{len(hist_data)}")
                
                # 显示有NaN值的行
                if nan_count > 0:
                    print("6. 包含NaN值的行:")
                    nan_rows = hist_data[hist_data['nav'].isna()]
                    print(nan_rows)
            
            # 检查日期列
            if 'date' in hist_data.columns:
                print(f"7. 日期范围: {hist_data['date'].min()} ~ {hist_data['date'].max()}")
                print(f"8. 日期类型: {type(hist_data['date'].iloc[0])}")
            
            # 应用相同的清理逻辑
            print("\n=== 应用清理逻辑后的结果 ===")
            cleaned_data = hist_data.dropna(subset=['nav'])
            print(f"清理后数据形状: {cleaned_data.shape}")
            
            if not cleaned_data.empty:
                # 转换日期格式
                cleaned_data['date'] = cleaned_data['date'].dt.strftime('%Y-%m-%d')
                # 确保nav是数值类型
                cleaned_data['nav'] = cleaned_data['nav'].astype(float)
                result_data = cleaned_data[['date', 'nav']].tail(days).to_dict('records')
                print(f"最终结果数据条数: {len(result_data)}")
                print("前3条数据:")
                for i, item in enumerate(result_data[:3]):
                    print(f"  {i+1}: {item}")
            else:
                print("清理后数据为空!")
                
        else:
            print("获取到的数据为空!")
            
    except Exception as e:
        print(f"获取数据时发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_fund_history()