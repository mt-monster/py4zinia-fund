#!/usr/bin/env python
# coding: utf-8

"""检查数据库中基金016667的数据"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_retrieval.enhanced_database import EnhancedDatabaseManager
import pandas as pd

def check_database_data():
    """检查数据库中的基金数据"""
    print("=" * 60)
    print("检查数据库中基金016667的数据")
    print("=" * 60)
    
    try:
        # 初始化数据库管理器
        db = EnhancedDatabaseManager()
        
        # 查询基金016667的最新数据
        sql = """
        SELECT fund_code, fund_name, prev_day_return, today_return, 
               analysis_date, data_source
        FROM fund_analysis_results 
        WHERE fund_code = '016667' 
        ORDER BY analysis_date DESC 
        LIMIT 5
        """
        
        df = db.execute_query(sql)
        
        if df.empty:
            print("数据库中没有找到基金016667的数据")
            return
            
        print("数据库中的基金016667数据:")
        print(df.to_string())
        
        # 检查最新的数据
        latest_data = df.iloc[0]
        print(f"\n最新数据分析日期: {latest_data['analysis_date']}")
        print(f"昨日盈亏率(prev_day_return): {latest_data['prev_day_return']}")
        print(f"今日涨跌幅(today_return): {latest_data['today_return']}")
        print(f"数据来源: {latest_data['data_source']}")
        
        # 检查是否存在NULL或0值
        if pd.isna(latest_data['prev_day_return']) or latest_data['prev_day_return'] == 0:
            print("⚠️  昨日盈亏率为NULL或0，这可能解释了前端显示为0的原因")
        else:
            print("✅ 昨日盈亏率在数据库中有有效值")
            
        print("\n" + "=" * 60)
        print("数据库检查完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database_data()