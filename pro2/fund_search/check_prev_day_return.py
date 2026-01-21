from data_retrieval.enhanced_database import EnhancedDatabaseManager

db = EnhancedDatabaseManager()
print('查询用户持仓中prev_day_return的实际值：')
print('-' * 40)
print('fund_code\tprev_day_return')
print('-' * 40)

results = db.execute_query('SELECT fund_code, prev_day_return FROM user_holdings LIMIT 10')
for row in results:
    print(f'{row[0]}\t{row[1]}')

print('-' * 40)