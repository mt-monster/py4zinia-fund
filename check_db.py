import sqlite3

conn = sqlite3.connect(r'd:\codes\py4zinia\pro2\fund_search\web\fund_analysis.db')
cursor = conn.cursor()

# 检查所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("数据库中的表:")
for table in tables:
    print(table[0])

# 检查可能包含净值数据的表
for table_name in ['fund_nav_history', 'fund_performance', 'fund_basic_info']:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"\n表 {table_name}: {count} 条记录")
        
        if count > 0:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"字段结构:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
    except:
        print(f"表 {table_name} 不存在")

conn.close()