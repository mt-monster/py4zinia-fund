#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试昨日盈亏率返回值修复
"""

import sys
sys.path.insert(0, 'D:/coding/traeCN_project/py4zinia/pro2/fund_search')

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def test_yesterday_return():
    """测试 _get_yesterday_return 返回格式"""
    from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
    
    adapter = MultiSourceDataAdapter()
    
    # 测试基金
    test_codes = ['016667', '018048']
    
    print("=" * 60)
    print("测试 _get_yesterday_return 返回格式")
    print("=" * 60)
    
    for code in test_codes:
        print(f"\n测试基金: {code}")
        result = adapter._get_yesterday_return(code)
        
        print(f"  返回类型: {type(result)}")
        if isinstance(result, dict):
            print(f"  value: {result.get('value')}")
            print(f"  date: {result.get('date')}")
            print(f"  days_diff: {result.get('days_diff')}")
            print(f"  is_stale: {result.get('is_stale')}")
        else:
            print(f"  返回值: {result}")
            print("  [警告] 返回类型不是字典！")


def test_realtime_data():
    """测试实时数据获取"""
    from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
    
    adapter = MultiSourceDataAdapter()
    
    test_codes = ['016667', '018048']
    
    print("\n" + "=" * 60)
    print("测试实时数据获取（包含昨日盈亏率）")
    print("=" * 60)
    
    for code in test_codes:
        print(f"\n测试基金: {code}")
        result = adapter.get_realtime_data(code)
        
        print(f"  prev_day_return: {result.get('prev_day_return')}")
        print(f"  today_return: {result.get('today_return')}")
        print(f"  data_source: {result.get('data_source')}")


if __name__ == '__main__':
    try:
        test_yesterday_return()
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        test_realtime_data()
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
