#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查user_holdings表结构
"""

import sys
sys.path.append('.')

from data_retrieval.enhanced_database import EnhancedDatabaseManager
from shared.enhanced_config import DATABASE_CONFIG


def check_holdings_table():
    """
    检查user_holdings表结构
    """
    try:
        # 初始化数据库管理器
        db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        
        # 查询表结构
        sql = "DESCRIBE user_holdings"
        result = db_manager.execute_query_raw(sql)
        
        print("user_holdings表结构:")
        for row in result:
            print(row)
        
        # 查询表中的数据
        print("\nuser_holdings表数据:")
        data_sql = "SELECT * FROM user_holdings"
        data_result = db_manager.execute_query_raw(data_sql)
        for row in data_result:
            print(row)
        
    except Exception as e:
        print(f"检查表结构失败: {e}")
    finally:
        # 数据库连接会在对象销毁时自动关闭
        pass


if __name__ == "__main__":
    check_holdings_table()
