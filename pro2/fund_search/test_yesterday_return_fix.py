#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试昨日收益率前向追溯功能修复
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
import pandas as pd
import logging

# 设置日志级别
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_yesterday_return_tracing():
    """测试昨日收益率前向追溯功能"""
    print("=== 测试昨日收益率前向追溯功能 ===")
    
    # 初始化数据管理器
    fund_data_manager = MultiSourceDataAdapter()
    
    # 测试基金列表（包括QDII和普通基金）
    test_funds = [
        "000001",  # 普通基金 - 华夏成长
        "096001",  # QDII基金 - 大成标普500等权重指数(QDII)A
        "100055",  # QDII基金 - 富国全球科技互联网股票(QDII)A
        "510050",  # ETF基金 - 上证50ETF
    ]
    
    for fund_code in test_funds:
        print(f"\n--- 测试基金 {fund_code} ---")
        
        try:
            # 1. 测试直接计算方法
            direct_return = fund_data_manager._get_yesterday_return(fund_code)
            print(f"直接计算昨日收益率: {direct_return}%")
            
            # 2. 测试是否为QDII基金
            is_qdii = fund_data_manager.is_qdii_fund(fund_code)
            print(f"是否为QDII基金: {is_qdii}")
            
            # 3. 获取历史数据用于分析
            hist_data = fund_data_manager.get_historical_data(fund_code, days=15)
            if hist_data is not None and not hist_data.empty:
                print(f"获取到 {len(hist_data)} 条历史数据")
                
                # 显示最近几天的收益率数据
                print("最近5天的收益率数据:")
                return_cols = [col for col in ['daily_return', '日增长率'] if col in hist_data.columns]
                if return_cols:
                    return_col = return_cols[0]
                    recent_data = hist_data.head(5)[['date', return_col]].copy()
                    recent_data[return_col] = pd.to_numeric(recent_data[return_col], errors='coerce')
                    print(recent_data.to_string(index=False))
                
                # 检查是否有零值
                if return_cols:
                    zero_count = (recent_data[return_col] == 0).sum()
                    print(f"其中零值数量: {zero_count}")
            else:
                print("未能获取历史数据")
                
        except Exception as e:
            logger.error(f"测试基金 {fund_code} 时出错: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n=== 测试完成 ===")

def test_specific_qdii_fund():
    """专门测试QDII基金的前向追溯功能"""
    print("\n=== 专门测试QDII基金前向追溯 ===")
    
    fund_data_manager = MultiSourceDataAdapter()
    qdii_fund = "096001"  # 大成标普500等权重指数(QDII)A
    
    try:
        print(f"测试QDII基金: {qdii_fund}")
        
        # 获取较多历史数据以便测试追溯功能
        hist_data = fund_data_manager.get_historical_data(qdii_fund, days=30)
        if hist_data is not None and not hist_data.empty:
            print(f"获取到 {len(hist_data)} 条历史数据")
            
            # 查找收益率列
            return_cols = [col for col in ['daily_return', '日增长率'] if col in hist_data.columns]
            if return_cols:
                return_col = return_cols[0]
                hist_data[return_col] = pd.to_numeric(hist_data[return_col], errors='coerce')
                
                # 统计零值情况
                total_count = len(hist_data)
                zero_count = (hist_data[return_col] == 0).sum()
                nonzero_count = total_count - zero_count
                
                print(f"总数据条数: {total_count}")
                print(f"零值条数: {zero_count}")
                print(f"非零值条数: {nonzero_count}")
                print(f"零值比例: {zero_count/total_count*100:.1f}%")
                
                if nonzero_count > 0:
                    nonzero_values = hist_data[hist_data[return_col] != 0][return_col]
                    print(f"非零收益率范围: {nonzero_values.min():.2f}% ~ {nonzero_values.max():.2f}%")
                    print(f"非零收益率平均值: {nonzero_values.mean():.2f}%")
                
                # 测试前向追溯方法
                traced_return = fund_data_manager._get_previous_nonzero_return(hist_data, qdii_fund)
                print(f"前向追溯获取的收益率: {traced_return}%")
                
                # 对比直接计算和追溯结果
                direct_return = fund_data_manager._get_yesterday_return(qdii_fund)
                print(f"直接计算的昨日收益率: {direct_return}%")
                
        else:
            print("未能获取历史数据")
            
    except Exception as e:
        logger.error(f"测试QDII基金 {qdii_fund} 时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 运行测试
    test_yesterday_return_tracing()
    test_specific_qdii_fund()
    
    print("\n🎉 测试脚本执行完毕！")