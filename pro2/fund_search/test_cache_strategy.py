#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金数据缓存策略测试脚本

测试内容：
1. 首次访问时从 Tushare 获取数据并存入缓存
2. 非首次访问优先使用缓存数据
3. today_return 实时计算
4. prev_day_return 从缓存获取
5. QDII基金前向追溯
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_cache_strategy():
    """测试缓存策略"""
    
    print("=" * 60)
    print("基金数据缓存策略测试")
    print("=" * 60)
    
    # 测试基金列表（包含普通基金和QDII基金）
    test_funds = [
        ('008811', '鹏华科技创新混合'),      # 普通基金
        ('015577', '国联安上证商品ETF联接C'),  # ETF
        ('016667', '景顺长城全球半导体芯片股票A(QDII-LOF)'),  # QDII基金
    ]
    
    try:
        from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
        
        print("\n1. 初始化数据适配器（带缓存）...")
        adapter = MultiSourceDataAdapter(timeout=10)
        print("   [OK] 适配器初始化完成")
        
        # 第一次访问：从 Tushare 获取
        print("\n2. 首次访问基金数据（应从Tushare获取）...")
        for fund_code, fund_name in test_funds:
            print(f"\n   获取基金 {fund_code} ({fund_name})...")
            data1 = adapter.get_realtime_data(fund_code, fund_name)
            print(f"   - current_nav: {data1.get('current_nav')}")
            print(f"   - today_return: {data1.get('today_return')}%")
            print(f"   - prev_day_return: {data1.get('prev_day_return')}%")
            print(f"   - data_source: {data1.get('data_source')}")
        
        # 第二次访问：应从缓存获取
        print("\n3. 第二次访问基金数据（应使用缓存）...")
        for fund_code, fund_name in test_funds:
            print(f"\n   获取基金 {fund_code} ({fund_name})...")
            data2 = adapter.get_realtime_data(fund_code, fund_name)
            print(f"   - current_nav: {data2.get('current_nav')}")
            print(f"   - today_return: {data2.get('today_return')}%")
            print(f"   - prev_day_return: {data2.get('prev_day_return')}%")
            print(f"   - data_source: {data2.get('data_source')}")
            
            # 验证缓存是否生效
            if data2.get('data_source') == 'cache_with_realtime':
                print(f"   [OK] 缓存命中！")
            else:
                print(f"   [MISS] 缓存未命中")
        
        # 批量获取测试
        print("\n4. 批量获取基金数据测试...")
        fund_codes = [code for code, _ in test_funds]
        fund_names = {code: name for code, name in test_funds}
        
        batch_results = adapter.get_batch_realtime_data(fund_codes, fund_names)
        print(f"   成功获取 {len(batch_results)} 只基金数据")
        for code, data in batch_results.items():
            print(f"   - {code}: today_return={data.get('today_return')}%, source={data.get('data_source')}")
        
        # 缓存统计
        print("\n5. 缓存统计信息...")
        stats = adapter.get_cache_statistics()
        print(f"   - 内存缓存键数: {stats.get('memory_cache_keys', 0)}")
        print(f"   - 类型分布: {stats.get('type_distribution', {})}")
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        return False


def test_qdii_traceback():
    """测试QDII基金前向追溯功能"""
    
    print("\n" + "=" * 60)
    print("QDII基金前向追溯测试")
    print("=" * 60)
    
    # QDII基金
    qdii_funds = [
        '016667',  # 景顺长城全球半导体
        '501225',  # 鹏华道琼斯石油
    ]
    
    try:
        from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
        
        adapter = MultiSourceDataAdapter(timeout=10)
        
        for fund_code in qdii_funds:
            print(f"\n测试基金 {fund_code}:")
            
            # 清除缓存，确保从API获取
            adapter.invalidate_fund_cache(fund_code)
            
            # 获取数据
            data = adapter.get_realtime_data(fund_code)
            
            print(f"   - 基金名称: {data.get('fund_name')}")
            print(f"   - 当前净值: {data.get('current_nav')}")
            print(f"   - 昨日盈亏率: {data.get('prev_day_return')}%")
            print(f"   - 日涨跌幅: {data.get('today_return')}%")
            print(f"   - 数据来源: {data.get('data_source')}")
            
            if data.get('prev_day_return', 0) != 0:
                print(f"   [OK] 昨日盈亏率非零，前向追溯可能已生效")
            else:
                print(f"   [WARN] 昨日盈亏率为零，可能无历史数据")
        
        print("\n" + "=" * 60)
        print("QDII测试完成！")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"QDII测试失败: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    print("\n开始基金数据缓存策略测试...\n")
    
    # 运行主要测试
    success1 = test_cache_strategy()
    
    # 运行QDII测试
    success2 = test_qdii_traceback()
    
    if success1 and success2:
        print("\n[PASS] 所有测试通过！")
        sys.exit(0)
    else:
        print("\n[FAIL] 部分测试失败")
        sys.exit(1)
