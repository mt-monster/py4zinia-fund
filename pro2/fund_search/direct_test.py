#!/usr/bin/env python
# coding: utf-8
"""
直接测试QDII基金向前追溯功能
"""

import sys
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_direct_qdii_trace():
    """直接测试QDII基金数据获取"""
    try:
        from data_retrieval.enhanced_fund_data import EnhancedFundData
        
        fund_code = '021539'
        fund_name = '华安法国CAC40ETF发起式联接(QDII)A'
        
        print(f"测试基金: {fund_name} ({fund_code})")
        print("=" * 50)
        
        # 直接调用数据获取方法
        fund_data = EnhancedFundData.get_realtime_data(fund_code, fund_name)
        
        if fund_data:
            print(f"数据来源: {fund_data.get('data_source', 'unknown')}")
            print(f"今日收益率: {fund_data.get('today_return', 'N/A')}%")
            print(f"昨日收益率: {fund_data.get('yesterday_return', 'N/A')}%")
            print(f"前日收益率: {fund_data.get('prev_day_return', 'N/A')}%")
            
            # 检查是否为QDII基金
            is_qdii = EnhancedFundData.is_qdii_fund(fund_code, fund_name)
            print(f"是否为QDII基金: {is_qdii}")
            
            if fund_data.get('yesterday_return') != 0.0:
                print("✅ 成功获取非零昨日收益率")
            else:
                print("⚠️  昨日收益率仍为0")
        else:
            print("❌ 无法获取基金数据")
            
    except Exception as e:
        print(f"测试出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_qdii_trace()