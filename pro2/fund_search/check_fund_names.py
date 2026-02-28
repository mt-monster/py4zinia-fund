#!/usr/bin/env python
# coding: utf-8

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_access.enhanced_database import EnhancedDatabaseManager
from shared.config_manager import config_manager

db_config = config_manager.get_database_config()
db_manager = EnhancedDatabaseManager({
    'host': db_config.host,
    'user': db_config.user,
    'password': db_config.password,
    'database': db_config.database,
    'port': db_config.port,
    'charset': db_config.charset
})

# 检查 fund_basic_info 表
print('=== fund_basic_info 表 ===')
sql = 'SELECT fund_code, fund_name FROM fund_basic_info LIMIT 20'
df = db_manager.execute_query(sql)
print(df)

# 检查 user_holdings 表
print('\n=== user_holdings 表 ===')
sql = 'SELECT fund_code, fund_name FROM user_holdings LIMIT 20'
df = db_manager.execute_query(sql)
print(df)

# 检查 fund_analysis_results 表
print('\n=== fund_analysis_results 表 ===')
sql = 'SELECT DISTINCT fund_code, fund_name FROM fund_analysis_results LIMIT 20'
df = db_manager.execute_query(sql)
print(df)
