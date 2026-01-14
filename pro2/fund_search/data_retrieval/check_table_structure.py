#!/usr/bin/env python
# coding: utf-8

"""
检查数据库表结构
"""

import pymysql
from enhanced_config import DATABASE_CONFIG

# 连接数据库
conn = pymysql.connect(**DATABASE_CONFIG)
cursor = conn.cursor()

# 查询表结构
cursor.execute("DESCRIBE fund_analysis_results")
fields = cursor.fetchall()

print('=== 数据库表结构 (fund_analysis_results) ===')
print('字段名'.ljust(20), '类型'.ljust(20), '备注')
print('-' * 60)

# 打印字段信息
for field in fields:
    field_name = field[0]
    field_type = field[1]
    print(f'{field_name.ljust(20)} {field_type.ljust(20)}')

conn.close()