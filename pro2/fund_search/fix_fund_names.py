#!/usr/bin/env python
# coding: utf-8

"""
彻底更新数据库中的基金名称
使用数据库中已有的正确名称更新"基金{fund_code}"格式的记录
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_access.enhanced_database import EnhancedDatabaseManager
from shared.config_manager import config_manager
import logging
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_fund_names():
    """更新数据库中的基金名称"""
    try:
        db_config = config_manager.get_database_config()
        db_manager = EnhancedDatabaseManager({
            'host': db_config.host,
            'user': db_config.user,
            'password': db_config.password,
            'database': db_config.database,
            'port': db_config.port,
            'charset': db_config.charset
        })

        # 1. 获取所有基金的正确名称（非"基金{fund_code}"格式）
        logger.info("正在获取基金的正确名称...")
        sql = "SELECT DISTINCT fund_code, fund_name FROM fund_analysis_results WHERE fund_name NOT LIKE '基金%%'"
        df = db_manager.execute_query(sql)
        
        correct_names = {}
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                fund_code = str(row['fund_code'])
                fund_name = str(row['fund_name'])
                correct_names[fund_code] = fund_name
        
        logger.info(f"找到 {len(correct_names)} 只基金的正确名称: {correct_names}")

        # 2. 更新所有"基金{fund_code}"格式的记录
        logger.info("正在更新错误的基金名称...")
        
        with db_manager.engine.connect() as conn:
            for fund_code, correct_name in correct_names.items():
                # 更新 fund_analysis_results 表
                sql_update = text("UPDATE fund_analysis_results SET fund_name = :name WHERE fund_code = :code AND fund_name LIKE '基金%%'")
                result = conn.execute(sql_update, {'name': correct_name, 'code': fund_code})
                if result.rowcount > 0:
                    conn.commit()
                    logger.info(f"更新 fund_analysis_results: {fund_code} -> {correct_name}, 影响行数: {result.rowcount}")
                
                # 更新 user_holdings 表
                sql_update2 = text("UPDATE user_holdings SET fund_name = :name WHERE fund_code = :code AND fund_name LIKE '基金%%'")
                result2 = conn.execute(sql_update2, {'name': correct_name, 'code': fund_code})
                if result2.rowcount > 0:
                    conn.commit()
                    logger.info(f"更新 user_holdings: {fund_code} -> {correct_name}, 影响行数: {result2.rowcount}")

        logger.info("基金名称更新完成!")
        
        # 验证更新结果
        logger.info("验证更新结果...")
        sql = "SELECT DISTINCT fund_code, fund_name FROM fund_analysis_results"
        df = db_manager.execute_query(sql)
        logger.info(f"更新后的数据:\n{df}")

    except Exception as e:
        logger.error(f"更新基金名称失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    update_fund_names()
