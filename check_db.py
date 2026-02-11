import sqlite3

conn = sqlite3.connect(r'd:\codes\py4zinia\pro2\fund_analysis.db')
cursor = conn.cursor()

# 查看所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print('数据库中的表:')
for table in tables:
    print(table[0])

# 检查是否有fund_analysis_results表
cursor.execute("PRAGMA table_info(fund_analysis_results);")
columns = cursor.fetchall()
if columns:
    print('\nfund_analysis_results表结构:')
    for col in columns:
        print(f"列名: {col[1]}, 类型: {col[2]}")
else:
    print('\nfund_analysis_results表不存在')

conn.close()