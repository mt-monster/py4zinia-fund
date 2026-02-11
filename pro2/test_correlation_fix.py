#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试相关性分析修复"""

import sys
sys.path.insert(0, '.')

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from fund_search.data_retrieval.fund_analyzer import FundAnalyzer

# 测试24只基金
test_funds = [
    '001270', '001614', '002179', '002423', '002611', '003017', '004206', 
    '005550', '006105', '006106', '006195', '006373', '006486', '006614',
    '006718', '007153', '007605', '007721', '007844', '008401', '008706',
    '008811', '009891', '010052'
]

print(f"测试 {len(test_funds)} 只基金的相关性分析")
print("=" * 60)

try:
    analyzer = FundAnalyzer()
    result = analyzer.analyze_correlation(test_funds, use_cache=False)
    
    print(f"✅ 分析成功！")
    print(f"   基金数量: {len(result['fund_codes'])}")
    print(f"   数据点数: {result['data_points']}")
    print(f"   失败基金: {result['failed_codes']}")
    
except Exception as e:
    print(f"❌ 分析失败: {e}")
    import traceback
    traceback.print_exc()
