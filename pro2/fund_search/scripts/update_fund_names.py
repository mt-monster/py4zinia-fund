#!/usr/bin/env python
# coding: utf-8

"""
批量更新数据库中的基金名称
从akshare获取真正的基金名称，替换"基金{fund_code}"格式的占位符
"""

import sys
import os
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_fund_names():
    """更新数据库中的基金名称"""
    try:
        from data_access.enhanced_database import EnhancedDatabaseManager
        from shared.config_manager import config_manager

        # 获取数据库配置
        db_config = config_manager.get_database_config()
        db_manager = EnhancedDatabaseManager({
            'host': db_config.host,
            'user': db_config.user,
            'password': db_config.password,
            'database': db_config.database,
            'port': db_config.port,
            'charset': db_config.charset
        })

        import akshare as ak

        # 1. 更新 fund_basic_info 表
        logger.info("正在查询 fund_basic_info 表中需要更新的基金...")
        sql = "SELECT fund_code, fund_name FROM fund_basic_info"
        df = db_manager.execute_query(sql)

        if df is not None and not df.empty:
            codes_to_update = []
            for _, row in df.iterrows():
                fund_code = str(row['fund_code'])
                fund_name = str(row['fund_name']) if row['fund_name'] else ''
                # 检查是否是"基金{fund_code}"格式
                if fund_name == f'基金{fund_code}':
                    codes_to_update.append(fund_code)

            logger.info(f"找到 {len(codes_to_update)} 只基金需要更新名称")

            # 批量从akshare获取真正的名称
            for fund_code in codes_to_update:
                try:
                    fund_info = ak.fund_open_fund_info_em(symbol=fund_code, indicator="基本信息")
                    if fund_info is not None and not fund_info.empty:
                        info_dict = {}
                        for _, row in fund_info.iterrows():
                            info_dict[row['项目']] = row['数值']
                        real_name = info_dict.get('基金简称', '')

                        if real_name and real_name != f'基金{fund_code}':
                            # 更新 fund_basic_info 表
                            sql_update = "UPDATE fund_basic_info SET fund_name = :fund_name WHERE fund_code = :fund_code"
                            db_manager.execute_sql(sql_update, {'fund_name': real_name, 'fund_code': fund_code})
                            logger.info(f"更新 fund_basic_info: {fund_code} -> {real_name}")
                        else:
                            logger.warning(f"无法获取基金 {fund_code} 的真正名称")
                except Exception as e:
                    logger.error(f"获取基金 {fund_code} 名称失败: {e}")

        # 2. 更新 user_holdings 表
        logger.info("正在查询 user_holdings 表中需要更新的基金...")
        sql = "SELECT DISTINCT fund_code, fund_name FROM user_holdings"
        df = db_manager.execute_query(sql)

        if df is not None and not df.empty:
            codes_to_update = []
            for _, row in df.iterrows():
                fund_code = str(row['fund_code'])
                fund_name = str(row['fund_name']) if row['fund_name'] else ''
                # 检查是否是"基金{fund_code}"格式
                if fund_name == f'基金{fund_code}':
                    codes_to_update.append(fund_code)

            logger.info(f"找到 {len(codes_to_update)} 只基金需要更新名称")

            # 批量从akshare获取真正的名称
            for fund_code in codes_to_update:
                try:
                    fund_info = ak.fund_open_fund_info_em(symbol=fund_code, indicator="基本信息")
                    if fund_info is not None and not fund_info.empty:
                        info_dict = {}
                        for _, row in fund_info.iterrows():
                            info_dict[row['项目']] = row['数值']
                        real_name = info_dict.get('基金简称', '')

                        if real_name and real_name != f'基金{fund_code}':
                            # 更新 user_holdings 表
                            sql_update = "UPDATE user_holdings SET fund_name = :fund_name WHERE fund_code = :fund_code"
                            db_manager.execute_sql(sql_update, {'fund_name': real_name, 'fund_code': fund_code})
                            logger.info(f"更新 user_holdings: {fund_code} -> {real_name}")
                        else:
                            logger.warning(f"无法获取基金 {fund_code} 的真正名称")
                except Exception as e:
                    logger.error(f"获取基金 {fund_code} 名称失败: {e}")

        # 3. 更新 fund_analysis_results 表
        logger.info("正在查询 fund_analysis_results 表中需要更新的基金...")
        sql = "SELECT DISTINCT fund_code, fund_name FROM fund_analysis_results"
        df = db_manager.execute_query(sql)

        if df is not None and not df.empty:
            codes_to_update = []
            for _, row in df.iterrows():
                fund_code = str(row['fund_code'])
                fund_name = str(row['fund_name']) if row['fund_name'] else ''
                # 检查是否是"基金{fund_code}"格式
                if fund_name == f'基金{fund_code}':
                    codes_to_update.append(fund_code)

            logger.info(f"找到 {len(codes_to_update)} 只基金需要更新名称")

            # 批量从akshare获取真正的名称
            for fund_code in codes_to_update:
                try:
                    fund_info = ak.fund_open_fund_info_em(symbol=fund_code, indicator="基本信息")
                    if fund_info is not None and not fund_info.empty:
                        info_dict = {}
                        for _, row in fund_info.iterrows():
                            info_dict[row['项目']] = row['数值']
                        real_name = info_dict.get('基金简称', '')

                        if real_name and real_name != f'基金{fund_code}':
                            # 更新 fund_analysis_results 表
                            sql_update = "UPDATE fund_analysis_results SET fund_name = :fund_name WHERE fund_code = :fund_code"
                            db_manager.execute_sql(sql_update, {'fund_name': real_name, 'fund_code': fund_code})
                            logger.info(f"更新 fund_analysis_results: {fund_code} -> {real_name}")
                        else:
                            logger.warning(f"无法获取基金 {fund_code} 的真正名称")
                except Exception as e:
                    logger.error(f"获取基金 {fund_code} 名称失败: {e}")

        logger.info("基金名称更新完成!")

    except Exception as e:
        logger.error(f"更新基金名称失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    update_fund_names()
