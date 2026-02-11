#!/usr/bin/env python
# coding: utf-8

"""添加测试基金数据用于验证排序功能"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_retrieval.enhanced_database import EnhancedDatabaseManager
from shared.enhanced_config import DATABASE_CONFIG
import datetime

def add_test_funds():
    """添加测试基金数据"""
    print("添加测试基金数据...")
    
    try:
        db = EnhancedDatabaseManager(DATABASE_CONFIG)
        today = datetime.date.today()
        
        test_funds = [
            ('000001', '招商白酒指数A', 1.5, 1.5, today),
            ('000002', '易方达蓝筹精选混合', 2.1, 2.1, today),
            ('000003', '华夏大盘精选混合', -0.5, -0.5, today),
            ('000004', '广发稳健增长混合A', 0.8, 0.8, today),
            ('000005', '南方中证500ETF联接A', 1.2, 1.2, today),
        ]
        
        for fund_code, fund_name, today_return, prev_day_return, analysis_date in test_funds:
            sql = """
            INSERT IGNORE INTO fund_analysis_results 
            (fund_code, fund_name, today_return, prev_day_return, analysis_date) 
            VALUES (:fund_code, :fund_name, :today_return, :prev_day_return, :analysis_date)
            """
            params = {
                'fund_code': fund_code,
                'fund_name': fund_name,
                'today_return': today_return,
                'prev_day_return': prev_day_return,
                'analysis_date': analysis_date
            }
            db.execute_sql(sql, params)
            print(f"已添加: {fund_name}")
        
        print("测试数据添加完成!")
        
        # 验证数据
        df = db.execute_query("SELECT fund_code, fund_name FROM fund_analysis_results ORDER BY fund_name")
        print("\n当前基金名称排序:")
        for _, row in df.iterrows():
            print(f"  {row['fund_name']}")
            
    except Exception as e:
        print(f"添加测试数据失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_test_funds()