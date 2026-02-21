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

# 检查用户持仓
sql1 = 'SELECT * FROM user_holdings LIMIT 5'
df1 = db.execute_query(sql1)
print('用户持仓:')
print(df1.to_string())
print()

# 检查持仓与基金分析结果的关联
sql2 = """
SELECT h.fund_code, h.fund_name,
       far.today_return, far.prev_day_return as yesterday_return,
       far.current_estimate as current_nav
FROM user_holdings h
LEFT JOIN (
    SELECT * FROM fund_analysis_results
    WHERE (fund_code, analysis_date) IN (
        SELECT fund_code, MAX(analysis_date) as max_date
        FROM fund_analysis_results
        GROUP BY fund_code
    )
) far ON h.fund_code = far.fund_code
"""
df2 = db.execute_query(sql2)
print('持仓与分析结果关联:')
print(df2.to_string())
print()
print(f'yesterday_return 有值的数量: {df2["yesterday_return"].notna().sum()} / {len(df2)}')
