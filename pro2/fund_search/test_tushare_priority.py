#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 Tushare 优先获取数据
"""

import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_realtime_fetcher():
    """测试 RealtimeDataFetcher 优先使用 Tushare"""
    from services.holding_realtime_service import RealtimeDataFetcher
    
    fetcher = RealtimeDataFetcher()
    
    # 测试基金代码
    test_codes = ['016667', '018048', '000001']
    
    print("=" * 60)
    print("测试 RealtimeDataFetcher 数据源优先级")
    print("=" * 60)
    
    for code in test_codes:
        print(f"\n测试基金: {code}")
        result = fetcher.get_fund_realtime(code)
        print(f"  数据源: {result.get('source', 'unknown')}")
        print(f"  当前净值: {result.get('current_nav')}")
        print(f"  日涨跌幅: {result.get('today_return')}%")
        
        if result.get('source') == 'tushare':
            print("  [OK] 成功从 Tushare 获取数据")
        else:
            print(f"  [WARN] 从 {result.get('source')} 获取数据（Tushare 可能失败）")


def test_multi_source_adapter():
    """测试 MultiSourceDataAdapter 优先使用 Tushare"""
    from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
    
    adapter = MultiSourceDataAdapter()
    
    # 测试基金代码
    test_codes = ['016667', '018048']
    
    print("\n" + "=" * 60)
    print("测试 MultiSourceDataAdapter 数据源优先级")
    print("=" * 60)
    
    for code in test_codes:
        print(f"\n测试基金: {code}")
        
        # 测试获取昨日收益率
        return_result = adapter._get_yesterday_return(code)
        yesterday_return = return_result.get('value', 0.0) if isinstance(return_result, dict) else return_result
        print(f"  昨日收益率: {yesterday_return}%")
        
        # 测试获取实时数据
        result = adapter.get_realtime_data(code)
        print(f"  数据源: {result.get('data_source', 'unknown')}")
        print(f"  当前净值: {result.get('current_nav')}")
        print(f"  日涨跌幅: {result.get('today_return')}%")
        print(f"  昨日收益率: {result.get('prev_day_return')}%")


def test_fund_nav_history():
    """测试 get_fund_nav_history 优先使用 Tushare"""
    from data_retrieval.multi_source_fund_data import MultiSourceFundData
    
    # 使用默认 token 初始化
    fetcher = MultiSourceFundData()
    
    test_codes = ['016667', '018048']
    
    print("\n" + "=" * 60)
    print("测试 get_fund_nav_history 数据源优先级")
    print("=" * 60)
    
    for code in test_codes:
        print(f"\n测试基金: {code}")
        try:
            # 使用 start_date 而不是 days
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
            
            df = fetcher.get_fund_nav_history(code, source='auto', start_date=start_date, end_date=end_date)
            if not df.empty:
                print(f"  获取到 {len(df)} 条记录")
                print(f"  最新记录: {df.iloc[0].to_dict()}")
                print("  [OK] 成功获取数据")
            else:
                print("  [FAIL] 未获取到数据")
        except Exception as e:
            print(f"  [FAIL] 获取失败: {e}")


if __name__ == '__main__':
    print("Tushare 数据源优先级测试")
    print("=" * 60)
    
    try:
        test_realtime_fetcher()
    except Exception as e:
        logger.error(f"RealtimeDataFetcher 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        test_multi_source_adapter()
    except Exception as e:
        logger.error(f"MultiSourceDataAdapter 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        test_fund_nav_history()
    except Exception as e:
        logger.error(f"get_fund_nav_history 测试失败: {e}")
        import traceback
        traceback.print_exc()
