#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
迁移验证脚本

验证 Tushare API 优化迁移是否成功

使用方法:
    python verify_migration.py
    
    # 详细测试
    python verify_migration.py --full-test
    
    # 性能对比
    python verify_migration.py --benchmark
"""

import sys
import os
import time
import logging
from typing import List, Dict

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_imports() -> Dict[str, bool]:
    """检查关键模块导入"""
    logger.info("=" * 60)
    logger.info("步骤 1: 检查模块导入")
    logger.info("=" * 60)
    
    results = {}
    
    # 检查新模块
    modules_to_check = [
        ('data_retrieval.rate_limiter', '速率限制器'),
        ('data_retrieval.batch_fund_data_fetcher', '批量获取器'),
        ('data_retrieval.optimized_fund_data', '优化后的获取器'),
        ('shared.fund_data_config', '统一配置'),
    ]
    
    for module_name, desc in modules_to_check:
        try:
            __import__(module_name)
            logger.info(f"  ✓ {desc}: {module_name}")
            results[module_name] = True
        except Exception as e:
            logger.error(f"  ✗ {desc}: {module_name} - {e}")
            results[module_name] = False
    
    return results


def check_class_inheritance() -> bool:
    """检查类继承关系是否正确"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 2: 检查类继承关系")
    logger.info("=" * 60)
    
    try:
        from data_retrieval.multi_source_fund_data import MultiSourceFundData
        from data_retrieval.optimized_fund_data import OptimizedFundData
        from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
        
        # 检查 OptimizedFundData 继承 MultiSourceFundData
        is_optimized_subclass = issubclass(OptimizedFundData, MultiSourceFundData)
        logger.info(f"  OptimizedFundData 继承 MultiSourceFundData: {'✓' if is_optimized_subclass else '✗'}")
        
        # 检查 MultiSourceDataAdapter 继承 OptimizedFundData
        is_adapter_subclass = issubclass(MultiSourceDataAdapter, OptimizedFundData)
        logger.info(f"  MultiSourceDataAdapter 继承 OptimizedFundData: {'✓' if is_adapter_subclass else '✗'}")
        
        return is_optimized_subclass and is_adapter_subclass
        
    except Exception as e:
        logger.error(f"  检查失败: {e}")
        return False


def check_rate_limiter() -> bool:
    """检查速率限制器功能"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 3: 检查速率限制器")
    logger.info("=" * 60)
    
    try:
        from data_retrieval.rate_limiter import RateLimiter, get_tushare_limiter
        
        # 创建限制器
        limiter = RateLimiter(max_calls=5, period=10, name="test")
        logger.info(f"  ✓ 速率限制器创建成功")
        
        # 测试获取限制器
        tushare_limiter = get_tushare_limiter('fund_nav')
        logger.info(f"  ✓ Tushare限制器获取成功")
        
        # 测试统计
        stats = tushare_limiter.get_stats()
        logger.info(f"  ✓ 统计信息: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"  ✗ 检查失败: {e}")
        return False


def check_batch_fetcher() -> bool:
    """检查批量获取器功能"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 4: 检查批量获取器")
    logger.info("=" * 60)
    
    try:
        from data_retrieval.batch_fund_data_fetcher import BatchFundDataFetcher
        
        # 创建获取器
        fetcher = BatchFundDataFetcher(use_cache=True)
        logger.info(f"  ✓ 批量获取器创建成功")
        
        # 检查统计
        stats = fetcher.get_stats()
        logger.info(f"  ✓ 统计信息: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"  ✗ 检查失败: {e}")
        return False


def check_optimized_fetcher() -> bool:
    """检查优化后的获取器功能"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 5: 检查优化后的获取器")
    logger.info("=" * 60)
    
    try:
        from data_retrieval.optimized_fund_data import OptimizedFundData
        
        # 创建获取器
        fetcher = OptimizedFundData(
            enable_batch=True,
            enable_rate_limit=True
        )
        logger.info(f"  ✓ 优化后的获取器创建成功")
        logger.info(f"  ✓ 批量优化: 启用")
        logger.info(f"  ✓ 速率限制: 启用")
        
        # 检查统计
        stats = fetcher.get_optimized_stats()
        logger.info(f"  ✓ 统计信息获取成功")
        
        return True
        
    except Exception as e:
        logger.error(f"  ✗ 检查失败: {e}")
        return False


def test_single_fund_fetch(fund_code: str = '000001') -> bool:
    """测试单只基金数据获取"""
    logger.info("\n" + "=" * 60)
    logger.info(f"步骤 6: 测试单只基金获取 ({fund_code})")
    logger.info("=" * 60)
    
    try:
        from data_retrieval.optimized_fund_data import OptimizedFundData
        
        fetcher = OptimizedFundData()
        
        start = time.time()
        df = fetcher.get_fund_nav_history(fund_code, use_batch=True)
        elapsed = time.time() - start
        
        if not df.empty:
            logger.info(f"  ✓ 获取成功: {len(df)} 条数据")
            logger.info(f"  ✓ 耗时: {elapsed:.2f}s")
            logger.info(f"  ✓ 最新净值: {df.iloc[-1].get('nav')}")
            return True
        else:
            logger.warning(f"  ⚠ 获取为空")
            return False
            
    except Exception as e:
        logger.error(f"  ✗ 测试失败: {e}")
        return False


def test_batch_fetch(fund_codes: List[str] = None) -> bool:
    """测试批量基金数据获取"""
    if fund_codes is None:
        fund_codes = ['000001', '000002', '000003']
    
    logger.info("\n" + "=" * 60)
    logger.info(f"步骤 7: 测试批量基金获取 ({len(fund_codes)}只)")
    logger.info("=" * 60)
    
    try:
        from data_retrieval.optimized_fund_data import OptimizedFundData
        
        fetcher = OptimizedFundData()
        
        start = time.time()
        results = fetcher.batch_get_fund_nav(fund_codes)
        elapsed = time.time() - start
        
        success_count = len([r for r in results.values() if not r.empty])
        
        logger.info(f"  ✓ 批量获取成功: {success_count}/{len(fund_codes)} 只基金")
        logger.info(f"  ✓ 耗时: {elapsed:.2f}s")
        logger.info(f"  ✓ 平均每只: {elapsed/len(fund_codes):.2f}s")
        
        # 显示统计
        stats = fetcher.get_optimized_stats()
        if 'batch_stats' in stats:
            logger.info(f"  ✓ API调用: {stats['batch_stats'].get('api_calls', 0)} 次")
            logger.info(f"  ✓ 缓存命中: {stats['batch_stats'].get('cache_hits', 0)} 次")
        
        return success_count == len(fund_codes)
        
    except Exception as e:
        logger.error(f"  ✗ 测试失败: {e}")
        return False


def check_backward_compatibility() -> bool:
    """检查向后兼容性"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 8: 检查向后兼容性")
    logger.info("=" * 60)
    
    try:
        # 检查旧导入方式是否仍然有效
        from data_retrieval import MultiSourceFundData
        logger.info("  ✓ MultiSourceFundData 别名导入成功")
        
        # 创建实例
        fetcher = MultiSourceFundData()
        logger.info("  ✓ MultiSourceFundData 实例创建成功")
        
        # 检查是否具有新方法
        has_batch = hasattr(fetcher, 'batch_get_fund_nav')
        logger.info(f"  {'✓' if has_batch else '✗'} 具有批量获取方法")
        
        has_stats = hasattr(fetcher, 'get_optimized_stats')
        logger.info(f"  {'✓' if has_stats else '✗'} 具有优化统计方法")
        
        return True
        
    except Exception as e:
        logger.error(f"  ✗ 兼容性检查失败: {e}")
        return False


def run_benchmark():
    """运行性能对比测试"""
    logger.info("\n" + "=" * 60)
    logger.info("性能对比测试")
    logger.info("=" * 60)
    
    test_codes = ['000001', '000002', '000003', '021539', '100055']
    
    # 测试优化版本
    logger.info("\n优化版本 (OptimizedFundData):")
    from data_retrieval.optimized_fund_data import OptimizedFundData
    
    opt_fetcher = OptimizedFundData(enable_batch=True, enable_rate_limit=True)
    
    start = time.time()
    opt_results = opt_fetcher.batch_get_fund_nav(test_codes)
    opt_elapsed = time.time() - start
    
    opt_success = len([r for r in opt_results.values() if not r.empty])
    opt_stats = opt_fetcher.get_optimized_stats()
    
    logger.info(f"  成功: {opt_success}/{len(test_codes)} 只")
    logger.info(f"  耗时: {opt_elapsed:.2f}s")
    logger.info(f"  API调用: {opt_stats.get('batch_stats', {}).get('api_calls', 0)} 次")
    
    # 输出总结
    logger.info("\n" + "=" * 60)
    logger.info("性能总结")
    logger.info("=" * 60)
    logger.info(f"  批量获取: {opt_success}只基金, {opt_elapsed:.2f}s")
    logger.info(f"  平均每只: {opt_elapsed/len(test_codes):.2f}s")
    logger.info(f"  API效率: 每只基金约 {opt_stats.get('batch_stats', {}).get('api_calls', 0)/max(opt_success, 1):.2f} 次调用")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='迁移验证脚本')
    parser.add_argument('--full-test', action='store_true', help='运行完整测试')
    parser.add_argument('--benchmark', action='store_true', help='运行性能对比')
    parser.add_argument('--fund-codes', type=str, help='测试基金代码，逗号分隔')
    
    args = parser.parse_args()
    
    # 解析基金代码
    test_codes = None
    if args.fund_codes:
        test_codes = [c.strip() for c in args.fund_codes.split(',')]
    
    logger.info("\n" + "=" * 60)
    logger.info("Tushare API 优化迁移验证")
    logger.info("=" * 60)
    
    all_passed = True
    
    # 基础检查
    import_results = check_imports()
    all_passed &= all(import_results.values())
    
    all_passed &= check_class_inheritance()
    all_passed &= check_rate_limiter()
    all_passed &= check_batch_fetcher()
    all_passed &= check_optimized_fetcher()
    
    # 功能测试
    if args.full_test or args.benchmark:
        all_passed &= test_single_fund_fetch(test_codes[0] if test_codes else '000001')
        all_passed &= test_batch_fetch(test_codes or ['000001', '000002', '000003'])
        all_passed &= check_backward_compatibility()
    
    # 性能测试
    if args.benchmark:
        run_benchmark()
    
    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("验证结果")
    logger.info("=" * 60)
    
    if all_passed:
        logger.info("✓ 所有检查通过！迁移成功。")
        return 0
    else:
        logger.error("✗ 部分检查失败，请查看上方日志。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
