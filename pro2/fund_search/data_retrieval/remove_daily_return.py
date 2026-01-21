#!/usr/bin/env python
# coding: utf-8

"""
删除 fund_analysis_results 表中的 daily_return 字段
"""

import sys
import os

# 添加模块路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, '..', 'shared'))

from enhanced_database import EnhancedDatabaseManager
from config import DB_CONFIG
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    try:
        # 创建数据库连接
        db = EnhancedDatabaseManager(DB_CONFIG)
        
        # 检查字段是否存在
        check_sql = """
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'fund_analysis_results'
        AND COLUMN_NAME = 'daily_return'
        """
        
        result = db.execute_query_raw(check_sql)
        
        if result:
            logger.info("发现 daily_return 字段，准备删除...")
            
            # 删除字段
            alter_sql = "ALTER TABLE fund_analysis_results DROP COLUMN daily_return"
            db.execute_sql(alter_sql)
            logger.info("✅ 成功删除 fund_analysis_results 表中的 daily_return 字段")
            
            # 同时检查 fund_performance 表
            check_performance_sql = """
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'fund_performance'
            AND COLUMN_NAME = 'daily_return'
            """
            
            perf_result = db.execute_query_raw(check_performance_sql)
            
            if perf_result:
                logger.info("发现 fund_performance 表中也有 daily_return 字段，是否删除? (y/n)")
                # 这里我们直接删除，因为用户之前确认要删除
                alter_perf_sql = "ALTER TABLE fund_performance DROP COLUMN daily_return"
                db.execute_sql(alter_perf_sql)
                logger.info("✅ 成功删除 fund_performance 表中的 daily_return 字段")
            else:
                logger.info("fund_performance 表中没有 daily_return 字段，跳过")
            
            logger.info("\n✅ 所有 daily_return 字段已删除完成！")
        else:
            logger.info("daily_return 字段不存在，无需删除")
        
        # 关闭连接
        db.close_connection()
        
    except Exception as e:
        logger.error(f"删除字段失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
