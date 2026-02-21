#!/usr/bin/env python
# coding: utf-8
import sys
sys.path.insert(0, r'd:\coding\trae_project\py4zinia\pro2\fund_search')
from data_retrieval.enhanced_database import EnhancedDatabaseManager
import pandas as pd

db_config = {
    'user': 'root',
    'password': 'root',
    'host': 'localhost',
    'port': 3306,
    'database': 'fund_analysis',
    'charset': 'utf8mb4'
}

db = EnhancedDatabaseManager(db_config)
sql = 'SELECT fund_code, analysis_date, today_return, prev_day_return FROM fund_analysis_results WHERE analysis_date = (SELECT MAX(analysis_date) FROM fund_analysis_results) LIMIT 10'
df = db.execute_query(sql)
print('最新数据:')
print(df.to_string())
print(f'\nprev_day_return 有值的数量: {df["prev_day_return"].notna().sum()} / {len(df)}')
