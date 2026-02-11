#!/usr/bin/env python
# coding: utf-8

"""检查基金016667的昨日盈亏率为何为0"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_fund_016667():
    """检查基金016667的数据"""
    print("=" * 60)
    print("检查基金 016667 昨日盈亏率")
    print("=" * 60)
    
    try:
        # 初始化适配器
        adapter = MultiSourceDataAdapter(timeout=10)
        
        # 清除缓存确保获取最新数据
        adapter.invalidate_fund_cache('016667')
        
        # 获取基金数据
        print("\n1. 获取基金实时数据...")
        data = adapter.get_realtime_data('016667')
        
        print(f"基金代码: 016667")
        print(f"基金名称: {data.get('fund_name', 'N/A')}")
        print(f"当前净值: {data.get('current_nav', 'N/A')}")
        print(f"昨日净值: {data.get('previous_nav', 'N/A')}")
        print(f"昨日盈亏率: {data.get('prev_day_return', 'N/A')}%")
        print(f"今日涨跌幅: {data.get('today_return', 'N/A')}%")
        print(f"数据来源: {data.get('data_source', 'N/A')}")
        
        # 检查历史数据
        print("\n2. 获取历史数据...")
        hist_data = adapter.get_fund_nav_history('016667', source='auto')
        
        if hist_data is not None and not hist_data.empty:
            print(f"历史数据条数: {len(hist_data)}")
            print("最近几条数据:")
            print(hist_data.head().to_string())
            
            # 检查是否有日增长率数据
            if '日增长率' in hist_data.columns:
                growth_rates = hist_data['日增长率'].head(5)
                print(f"\n最近5日增长率:")
                for i, rate in enumerate(growth_rates):
                    print(f"  第{i+1}天: {rate}")
            elif 'daily_return' in hist_data.columns:
                growth_rates = hist_data['daily_return'].head(5)
                print(f"\n最近5日收益率:")
                for i, rate in enumerate(growth_rates):
                    print(f"  第{i+1}天: {rate}")
            else:
                print("未找到日增长率列")
        else:
            print("未获取到历史数据")
            
        # 检查是否为QDII基金
        print("\n3. 检查基金类型...")
        is_qdii = adapter.is_qdii_fund('016667')
        print(f"是否为QDII基金: {is_qdii}")
        
        # 如果是QDII基金，检查前向追溯逻辑
        if is_qdii and data.get('prev_day_return', 0) == 0:
            print("\n4. QDII基金前向追溯检查...")
            # 获取更多历史数据进行追溯
            extended_hist = adapter.get_fund_nav_history('016667', days=20, source='auto')
            if extended_hist is not None and not extended_hist.empty:
                print(f"扩展历史数据条数: {len(extended_hist)}")
                # 查找非零的日增长率
                if '日增长率' in extended_hist.columns:
                    non_zero_returns = extended_hist[extended_hist['日增长率'] != 0]['日增长率']
                    if len(non_zero_returns) > 0:
                        print(f"找到非零收益率 {len(non_zero_returns)} 条:")
                        print(non_zero_returns.head())
                    else:
                        print("未找到非零收益率")
                elif 'daily_return' in extended_hist.columns:
                    non_zero_returns = extended_hist[extended_hist['daily_return'] != 0]['daily_return']
                    if len(non_zero_returns) > 0:
                        print(f"找到非零收益率 {len(non_zero_returns)} 条:")
                        print(non_zero_returns.head())
                    else:
                        print("未找到非零收益率")
                        
        print("\n" + "=" * 60)
        print("检查完成！")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_fund_016667()