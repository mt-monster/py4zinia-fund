#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据获取优化迁移助手

帮助从旧的 MultiSourceFundData 迁移到 OptimizedFundData

使用示例:
    # 1. 测试新的批量获取器
    python migration_helper.py --test-batch
    
    # 2. 对比新旧性能
    python migration_helper.py --benchmark --fund-codes 000001,000002,021539
    
    # 3. 预热缓存
    python migration_helper.py --warmup --fund-codes 000001,000002
"""

import sys
import os
import time
import argparse
import logging
from typing import List

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_batch_fetcher(fund_codes: List[str]):
    """测试批量获取器"""
    print("\n" + "=" * 60)
    print("测试批量数据获取器")
    print("=" * 60)
    
    from data_retrieval.fetchers.batch_fund_data_fetcher import BatchFundDataFetcher
    
    fetcher = BatchFundDataFetcher()
    
    # 测试批量获取最新净值
    print(f"\n测试基金: {fund_codes}")
    
    start = time.time()
    results = fetcher.batch_get_latest_nav(fund_codes)
    elapsed = time.time() - start
    
    print(f"\n获取结果 ({elapsed:.2f}s):")
    for code, data in results.items():
        print(f"  {code}: NAV={data.get('nav')}, Date={data.get('date')}, Source={data.get('source')}")
    
    print(f"\n统计信息:")
    stats = fetcher.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    return results


def test_optimized_fetcher(fund_codes: List[str]):
    """测试优化后的获取器"""
    print("\n" + "=" * 60)
    print("测试优化后的数据获取器")
    print("=" * 60)
    
    from data_retrieval.fetchers.optimized_fund_data import OptimizedFundData
    
    fetcher = OptimizedFundData(
        enable_batch=True,
        enable_rate_limit=True
    )
    
    print(f"\n测试基金: {fund_codes}")
    
    # 测试批量获取
    start = time.time()
    results = fetcher.batch_get_fund_nav(fund_codes)
    elapsed = time.time() - start
    
    print(f"\n批量获取结果 ({elapsed:.2f}s):")
    for code, df in results.items():
        if not df.empty:
            latest = df.iloc[-1]
            print(f"  {code}: {len(df)}条数据, 最新NAV={latest.get('nav')}")
    
    # 显示统计
    print(f"\n优化统计:")
    stats = fetcher.get_optimized_stats()
    print(f"  批量优化: {stats.get('batch_enabled')}")
    print(f"  速率限制: {stats.get('rate_limit_enabled')}")
    
    if 'batch_stats' in stats:
        print(f"  批量统计: {stats['batch_stats']}")
    
    return results


def benchmark_comparison(fund_codes: List[str]):
    """对比测试新旧实现"""
    print("\n" + "=" * 60)
    print("性能对比测试")
    print("=" * 60)
    
    from data_retrieval.fetchers.multi_source_fund_data import MultiSourceFundData
    from data_retrieval.fetchers.optimized_fund_data import OptimizedFundData
    
    print(f"\n测试基金: {fund_codes} (共{len(fund_codes)}只)")
    
    # 测试旧实现
    print("\n--- 旧实现 (MultiSourceFundData) ---")
    old_fetcher = MultiSourceFundData()
    
    old_start = time.time()
    old_results = {}
    for code in fund_codes:
        try:
            df = old_fetcher.get_fund_nav_history(code, source='auto')
            old_results[code] = len(df) if not df.empty else 0
        except Exception as e:
            old_results[code] = f"Error: {e}"
    old_elapsed = time.time() - old_start
    
    print(f"耗时: {old_elapsed:.2f}s")
    print(f"结果: {old_results}")
    
    # 测试新实现
    print("\n--- 新实现 (OptimizedFundData) ---")
    new_fetcher = OptimizedFundData(enable_batch=True, enable_rate_limit=True)
    
    new_start = time.time()
    new_results = new_fetcher.batch_get_fund_nav(fund_codes)
    new_elapsed = time.time() - new_start
    
    print(f"耗时: {new_elapsed:.2f}s")
    print(f"结果: { {code: len(df) for code, df in new_results.items()} }")
    
    # 对比
    print("\n--- 对比结果 ---")
    speedup = old_elapsed / new_elapsed if new_elapsed > 0 else float('inf')
    print(f"速度提升: {speedup:.2f}x")
    print(f"API调用优化: 从 {len(fund_codes)} 次减少到约 1 次")


def warmup_cache(fund_codes: List[str]):
    """预热缓存"""
    print("\n" + "=" * 60)
    print("缓存预热")
    print("=" * 60)
    
    from data_retrieval.fetchers.optimized_fund_data import OptimizedFundData
    
    fetcher = OptimizedFundData(enable_batch=True)
    
    print(f"\n预热基金: {fund_codes}")
    
    start = time.time()
    fetcher.preload_fund_data(fund_codes)
    elapsed = time.time() - start
    
    print(f"预热完成，耗时: {elapsed:.2f}s")
    print(f"缓存统计: {fetcher.get_optimized_stats().get('batch_stats', {})}")


def check_rate_limit_status():
    """检查速率限制状态"""
    print("\n" + "=" * 60)
    print("速率限制状态检查")
    print("=" * 60)
    
    from data_retrieval.utils.rate_limiter import tushare_limiter
    
    stats = tushare_limiter.get_all_stats()
    
    print("\n各接口速率限制状态:")
    for api_name, api_stats in stats.items():
        print(f"\n  {api_name}:")
        print(f"    配置: {api_stats['max_calls']}次/{api_stats['period']}秒")
        print(f"    当前使用: {api_stats['current_usage']}次 ({api_stats['usage_percent']}%)")
        print(f"    总调用: {api_stats['total_calls']}次")
        print(f"    被限制: {api_stats['throttled_calls']}次")


def main():
    parser = argparse.ArgumentParser(description='数据获取优化迁移助手')
    parser.add_argument('--test-batch', action='store_true', help='测试批量获取器')
    parser.add_argument('--test-optimized', action='store_true', help='测试优化后的获取器')
    parser.add_argument('--benchmark', action='store_true', help='对比测试新旧实现')
    parser.add_argument('--warmup', action='store_true', help='预热缓存')
    parser.add_argument('--check-rate-limit', action='store_true', help='检查速率限制状态')
    parser.add_argument('--fund-codes', type=str, default='000001,000002,021539,100055',
                       help='测试基金代码，逗号分隔')
    
    args = parser.parse_args()
    
    # 解析基金代码
    fund_codes = [code.strip() for code in args.fund_codes.split(',')]
    
    # 执行选定的操作
    if args.test_batch:
        test_batch_fetcher(fund_codes)
    
    if args.test_optimized:
        test_optimized_fetcher(fund_codes)
    
    if args.benchmark:
        benchmark_comparison(fund_codes)
    
    if args.warmup:
        warmup_cache(fund_codes)
    
    if args.check_rate_limit:
        check_rate_limit_status()
    
    # 默认执行全部测试
    if not any([args.test_batch, args.test_optimized, args.benchmark, 
                args.warmup, args.check_rate_limit]):
        print("请指定操作，使用 --help 查看帮助")
        print("\n常用命令:")
        print("  python migration_helper.py --test-batch")
        print("  python migration_helper.py --benchmark --fund-codes 000001,000002")
        print("  python migration_helper.py --warmup")


if __name__ == '__main__':
    main()
