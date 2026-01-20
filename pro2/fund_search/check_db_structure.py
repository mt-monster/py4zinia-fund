import sqlite3

conn = sqlite3.connect('data/fund_analysis.db')
cursor = conn.cursor()

print('fund_analysis_results表结构：')
print('字段名称\t数据类型\t是否主键')
print('-' * 35)

cursor.execute('PRAGMA table_info(fund_analysis_results)')
for col in cursor.fetchall():
    is_primary = "是" if col[5] == 1 else "否"
    print(f'{col[1]}\t{col[2]}\t{is_primary}')

conn.close()