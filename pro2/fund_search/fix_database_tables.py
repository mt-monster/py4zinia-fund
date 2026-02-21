#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库表修复脚本
自动创建缺失的表
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_retrieval.enhanced_database import EnhancedDatabaseManager
from shared.enhanced_config import DATABASE_CONFIG
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_fund_data_cache_table(db_manager):
    """创建 fund_data_cache 表"""
    try:
        sql = """
        CREATE TABLE IF NOT EXISTS fund_data_cache (
            fund_code VARCHAR(20) NOT NULL,
            cache_date DATE NOT NULL,
            current_nav FLOAT,
            previous_nav FLOAT,
            prev_day_return FLOAT,
            nav_date VARCHAR(10),
            data_source VARCHAR(50),
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (fund_code, cache_date),
            INDEX idx_cached_at (cached_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        db_manager.execute_sql(sql)
        logger.info("✅ fund_data_cache 表创建成功")
        return True
    except Exception as e:
        logger.error(f"❌ fund_data_cache 表创建失败: {e}")
        return False


def check_and_create_tables():
    """检查并创建所有缺失的表"""
    logger.info("开始检查和修复数据库表...")
    
    try:
        # 初始化数据库管理器
        db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        logger.info("数据库连接成功")
        
        # 创建 fund_data_cache 表
        create_fund_data_cache_table(db_manager)
        
        logger.info("数据库表检查和修复完成")
        return True
        
    except Exception as e:
        logger.error(f"数据库操作失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = check_and_create_tables()
    sys.exit(0 if success else 1)
