#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
缓存系统验证和初始化脚本

功能：
1. 检查缓存表是否存在
2. 为现有持仓基金预加载缓存数据
3. 验证缓存是否正常工作
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from shared.enhanced_config import DATABASE_CONFIG
from data_access.enhanced_database import EnhancedDatabaseManager
from services.fund_nav_cache_manager import FundNavCacheManager
from services.holding_realtime_service import HoldingRealtimeService


def check_cache_tables(db_manager):
    """检查缓存表是否存在 - 绩效数据使用 fund_analysis_results"""
    tables = ['fund_nav_cache', 'fund_cache_metadata']
    results = {}
    
    for table in tables:
        try:
            sql = f"SELECT COUNT(*) as count FROM {table}"
            df = db_manager.execute_query(sql)
            count = df.iloc[0]['count'] if not df.empty else 0
            results[table] = {'exists': True, 'count': count}
            logger.info(f"✓ 表 {table} 存在，记录数: {count}")
        except Exception as e:
            results[table] = {'exists': False, 'error': str(e)}
            logger.error(f"✗ 表 {table} 不存在或无法访问: {e}")
    
    return results


def get_user_holdings(db_manager):
    """获取用户持仓基金列表"""
    try:
        sql = """
            SELECT DISTINCT fund_code, fund_name
            FROM user_holdings
            WHERE holding_shares > 0
        """
        df = db_manager.execute_query(sql)
        return df.to_dict('records') if not df.empty else []
    except Exception as e:
        logger.error(f"获取持仓失败: {e}")
        return []


def preload_cache_for_holdings(db_manager, cache_manager, holdings):
    """为持仓基金预加载缓存数据"""
    logger.info(f"开始为 {len(holdings)} 只基金预加载缓存...")
    
    success_count = 0
    failed_funds = []
    
    for holding in holdings:
        fund_code = holding['fund_code']
        fund_name = holding.get('fund_name', '')
        
        try:
            # 检查是否已有缓存
            cached = cache_manager.get_fund_nav_from_db(fund_code, days=30)
            if cached is not None and not cached.empty:
                latest_date = cached['nav_date'].max()
                logger.info(f"  {fund_code} 已有缓存数据，最新日期: {latest_date}")
                success_count += 1
                continue
            
            # 没有缓存，从数据源获取
            logger.info(f"  {fund_code} 缓存缺失，正在从数据源获取...")
            fresh_data = cache_manager.fetch_fund_nav_from_source(fund_code, days=30)
            
            if not fresh_data.empty:
                cache_manager.save_fund_nav_to_db(fund_code, fresh_data, 'akshare')
                logger.info(f"  ✓ {fund_code} 缓存成功 ({len(fresh_data)} 条记录)")
                success_count += 1
            else:
                logger.warning(f"  ✗ {fund_code} 无法获取数据")
                failed_funds.append(fund_code)
                
        except Exception as e:
            logger.error(f"  ✗ {fund_code} 处理失败: {e}")
            failed_funds.append(fund_code)
    
    logger.info(f"\n预加载完成: {success_count}/{len(holdings)} 只基金成功")
    if failed_funds:
        logger.warning(f"失败的基金: {failed_funds}")
    
    return success_count, failed_funds


def test_holding_service_cache(db_manager, cache_manager, holdings):
    """测试 HoldingRealtimeService 的缓存功能"""
    logger.info("\n测试 HoldingRealtimeService 缓存...")
    
    service = HoldingRealtimeService(db_manager, cache_manager)
    
    # 第一次调用（应该会从数据源获取）
    logger.info("第一次调用 get_holdings_data...")
    start = datetime.now()
    result1 = service.get_holdings_data('default_user')
    duration1 = (datetime.now() - start).total_seconds()
    logger.info(f"  耗时: {duration1:.2f}s, 返回 {len(result1)} 条记录")
    
    # 第二次调用（应该从缓存获取）
    logger.info("第二次调用 get_holdings_data（应该更快）...")
    start = datetime.now()
    result2 = service.get_holdings_data('default_user')
    duration2 = (datetime.now() - start).total_seconds()
    logger.info(f"  耗时: {duration2:.2f}s, 返回 {len(result2)} 条记录")
    
    if duration2 < duration1:
        logger.info(f"✓ 缓存生效！第二次比第一次快 {duration1/duration2:.1f}x")
    else:
        logger.warning("✗ 缓存可能未生效，两次调用耗时相近")
    
    # 检查内存缓存
    mem_cache_stats = cache_manager.get_cache_stats()
    logger.info(f"\n内存缓存统计: {mem_cache_stats['memory_cache']}")
    logger.info(f"数据库缓存统计: {mem_cache_stats['database_cache']}")


def main():
    logger.info("=" * 60)
    logger.info("缓存系统验证和初始化")
    logger.info("=" * 60)
    
    # 初始化数据库连接
    try:
        db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        logger.info("✓ 数据库连接成功")
    except Exception as e:
        logger.error(f"✗ 数据库连接失败: {e}")
        return
    
    # 检查缓存表
    logger.info("\n1. 检查缓存表状态")
    logger.info("-" * 40)
    table_status = check_cache_tables(db_manager)
    
    # 如果表不存在，提示创建
    if not all(s['exists'] for s in table_status.values()):
        logger.error("\n部分缓存表不存在，请先运行 init_cache_system.py 创建表")
        return
    
    # 初始化缓存管理器
    cache_manager = FundNavCacheManager(db_manager, default_ttl_minutes=15)
    logger.info("\n✓ 缓存管理器初始化完成")
    
    # 获取用户持仓
    logger.info("\n2. 获取用户持仓")
    logger.info("-" * 40)
    holdings = get_user_holdings(db_manager)
    if not holdings:
        logger.warning("没有找到持仓基金，跳过预加载")
        return
    
    logger.info(f"找到 {len(holdings)} 只持仓基金:")
    for h in holdings:
        logger.info(f"  - {h['fund_code']}: {h['fund_name']}")
    
    # 预加载缓存
    logger.info("\n3. 预加载缓存数据")
    logger.info("-" * 40)
    preload_cache_for_holdings(db_manager, cache_manager, holdings)
    
    # 测试缓存服务
    logger.info("\n4. 测试缓存服务")
    logger.info("-" * 40)
    test_holding_service_cache(db_manager, cache_manager, holdings)
    
    logger.info("\n" + "=" * 60)
    logger.info("缓存系统验证完成")
    logger.info("=" * 60)
    logger.info("\n提示:")
    logger.info("- 实时数据有2分钟内存缓存")
    logger.info("- 昨日数据有15分钟内存缓存")
    logger.info("- 绩效指标有1天数据库缓存")
    logger.info("- 访问 /api/cache/status 可查看缓存状态")


if __name__ == '__main__':
    main()
