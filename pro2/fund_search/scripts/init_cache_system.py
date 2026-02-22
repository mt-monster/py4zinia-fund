#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金数据缓存系统初始化脚本

使用说明：
    python init_cache_system.py [--full]

参数：
    --full: 执行完整初始化（包括历史数据同步）

功能：
    1. 创建缓存相关数据库表
    2. 初始化缓存元数据
    3. （可选）同步历史数据
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.enhanced_config import DATABASE_CONFIG
from data_access.enhanced_database import EnhancedDatabaseManager
from services import FundNavCacheManager, FundDataSyncService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_tables(db_manager):
    """创建缓存相关表"""
    logger.info("开始创建缓存表...")
    
    tables_sql = [
        # 基金净值缓存表
        """
        CREATE TABLE IF NOT EXISTS fund_nav_cache (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fund_code VARCHAR(10) NOT NULL,
            nav_date DATE NOT NULL,
            nav_value DECIMAL(10,4) NOT NULL,
            accum_nav DECIMAL(10,4),
            daily_return DECIMAL(8,4),
            data_source VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_fund_date (fund_code, nav_date),
            INDEX idx_fund_code (fund_code),
            INDEX idx_nav_date (nav_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='基金净值缓存表'
        """,
        
        # 缓存元数据表
        """
        CREATE TABLE IF NOT EXISTS fund_cache_metadata (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fund_code VARCHAR(10) NOT NULL UNIQUE,
            earliest_date DATE,
            latest_date DATE,
            total_records INT DEFAULT 0,
            last_sync_at TIMESTAMP,
            next_sync_at TIMESTAMP,
            sync_status ENUM('pending', 'syncing', 'completed', 'failed') DEFAULT 'pending',
            sync_fail_count INT DEFAULT 0,
            data_source VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_sync_status (sync_status),
            INDEX idx_next_sync (next_sync_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='基金缓存元数据表'
        """,
        
        # 用户持仓日终数据表
        """
        CREATE TABLE IF NOT EXISTS user_holding_daily (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            fund_code VARCHAR(10) NOT NULL,
            holding_shares DECIMAL(15,4),
            cost_price DECIMAL(10,4),
            holding_amount DECIMAL(15,4),
            yesterday_nav DECIMAL(10,4),
            yesterday_return DECIMAL(8,4),
            yesterday_profit DECIMAL(15,4),
            yesterday_market_value DECIMAL(15,4),
            total_buy_amount DECIMAL(15,4),
            total_sell_amount DECIMAL(15,4),
            record_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_user_fund_date (user_id, fund_code, record_date),
            INDEX idx_user_id (user_id),
            INDEX idx_record_date (record_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户持仓日终数据表'
        """,
        
        # 用户持仓快照表
        """
        CREATE TABLE IF NOT EXISTS user_portfolio_snapshot (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            snapshot_date DATE NOT NULL,
            fund_code VARCHAR(10) NOT NULL,
            holding_shares DECIMAL(15,4),
            nav_value DECIMAL(10,4),
            market_value DECIMAL(15,4),
            daily_return DECIMAL(8,4),
            holding_profit DECIMAL(15,4),
            total_profit DECIMAL(15,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_user_fund_date (user_id, fund_code, snapshot_date),
            INDEX idx_user_date (user_id, snapshot_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户持仓快照表'
        """,
        
        # 后台任务日志表
        """
        CREATE TABLE IF NOT EXISTS fund_sync_job_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            job_name VARCHAR(50) NOT NULL,
            job_type ENUM('daily', 'full', 'realtime'),
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            status ENUM('running', 'success', 'failed'),
            total_count INT DEFAULT 0,
            success_count INT DEFAULT 0,
            fail_count INT DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_job_name (job_name),
            INDEX idx_start_time (start_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据同步任务日志表'
        """
    ]
    
    for i, sql in enumerate(tables_sql, 1):
        try:
            db_manager.execute_sql(sql)
            logger.info(f"表 {i}/{len(tables_sql)} 创建成功")
        except Exception as e:
            logger.error(f"表 {i} 创建失败: {e}")
            raise
    
    logger.info("所有缓存表创建完成")


def init_metadata(db_manager, cache_manager):
    """初始化缓存元数据"""
    logger.info("初始化缓存元数据...")
    
    # 获取所有持仓基金
    sql = "SELECT DISTINCT fund_code FROM user_holdings WHERE holding_shares > 0"
    df = db_manager.execute_query(sql)
    
    if df.empty:
        logger.warning("没有找到持仓基金")
        return
    
    fund_codes = df['fund_code'].tolist()
    logger.info(f"发现 {len(fund_codes)} 只持仓基金")
    
    # 初始化元数据记录
    for fund_code in fund_codes:
        try:
            sql = """
                INSERT INTO fund_cache_metadata 
                (fund_code, sync_status, next_sync_at)
                VALUES (:fund_code, 'pending', NOW())
                ON DUPLICATE KEY UPDATE
                sync_status = 'pending',
                next_sync_at = NOW()
            """
            db_manager.execute_sql(sql, {'fund_code': fund_code})
        except Exception as e:
            logger.warning(f"初始化 {fund_code} 元数据失败: {e}")
    
    logger.info("缓存元数据初始化完成")


def sync_historical_data(cache_manager, sync_service, days=365):
    """同步历史数据"""
    logger.info(f"开始同步历史数据（最近{days}天）...")
    
    # 获取需要同步的基金
    sql = """
        SELECT fund_code 
        FROM fund_cache_metadata
        WHERE sync_status = 'pending'
        ORDER BY fund_code
    """
    df = cache_manager.db.execute_query(sql)
    
    if df.empty:
        logger.info("没有需要同步的基金")
        return
    
    fund_codes = df['fund_code'].tolist()
    logger.info(f"需要同步 {len(fund_codes)} 只基金")
    
    # 逐个同步
    success_count = 0
    for i, fund_code in enumerate(fund_codes, 1):
        try:
            logger.info(f"[{i}/{len(fund_codes)}] 同步 {fund_code}...")
            
            # 获取历史数据
            df_nav = cache_manager.fetch_fund_nav_from_source(fund_code, days)
            
            if not df_nav.empty:
                cache_manager.save_fund_nav_to_db(fund_code, df_nav, 'akshare')
                success_count += 1
                logger.info(f"  ✓ 成功: {len(df_nav)}条记录")
            else:
                logger.warning(f"  ✗ 失败: 无数据")
            
            # 每5只基金暂停一下
            if i % 5 == 0:
                import time
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"  ✗ 异常: {e}")
    
    logger.info(f"历史数据同步完成: 成功{success_count}/{len(fund_codes)}")


def calculate_performance_metrics(cache_manager):
    """计算绩效指标"""
    logger.info("开始计算绩效指标...")
    
    # 获取有净值数据的基金
    sql = "SELECT DISTINCT fund_code FROM fund_nav_cache"
    df = cache_manager.db.execute_query(sql)
    
    if df.empty:
        logger.warning("没有净值数据用于计算绩效")
        return
    
    fund_codes = df['fund_code'].tolist()
    logger.info(f"需要计算 {len(fund_codes)} 只基金的绩效指标")
    
    success_count = 0
    for i, fund_code in enumerate(fund_codes, 1):
        try:
            metrics = cache_manager._calculate_performance_metrics(fund_code, 365)
            if metrics:
                cache_manager.save_performance_to_db(fund_code, metrics)
                success_count += 1
                logger.debug(f"[{i}/{len(fund_codes)}] {fund_code} 绩效计算完成")
            else:
                logger.warning(f"[{i}/{len(fund_codes)}] {fund_code} 绩效计算失败")
        except Exception as e:
            logger.error(f"[{i}/{len(fund_codes)}] {fund_code} 绩效计算异常: {e}")
    
    logger.info(f"绩效指标计算完成: 成功{success_count}/{len(fund_codes)}")


def main():
    parser = argparse.ArgumentParser(description='基金数据缓存系统初始化')
    parser.add_argument('--full', action='store_true', help='执行完整初始化（包括历史数据同步）')
    parser.add_argument('--days', type=int, default=365, help='同步历史数据天数（默认365天）')
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("基金数据缓存系统初始化")
    logger.info("=" * 60)
    
    try:
        # 1. 连接数据库
        logger.info("连接数据库...")
        db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        
        # 2. 创建表
        create_tables(db_manager)
        
        # 3. 初始化缓存管理器
        cache_manager = FundNavCacheManager(db_manager)
        
        # 4. 初始化元数据
        init_metadata(db_manager, cache_manager)
        
        if args.full:
            # 5. 同步历史数据
            sync_historical_data(cache_manager, None, args.days)
            
            # 6. 计算绩效指标
            calculate_performance_metrics(cache_manager)
            
            logger.info("=" * 60)
            logger.info("完整初始化完成！")
            logger.info("=" * 60)
        else:
            logger.info("=" * 60)
            logger.info("基础初始化完成！")
            logger.info("提示：使用 --full 参数可同步历史数据")
            logger.info("提示：系统会自动在晚上22:00执行数据同步")
            logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
