#!/usr/bin/env python
# coding: utf-8

"""检查基金020422的数据显示问题"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_retrieval.enhanced_database import EnhancedDatabaseManager
from shared.enhanced_config import DATABASE_CONFIG

def check_fund_020422():
    """检查基金020422的数据"""
    print("检查基金020422的数据...")
    
    try:
        db = EnhancedDatabaseManager(DATABASE_CONFIG)
        
        # 检查fund_analysis_results表
        sql = "SELECT fund_code, fund_name FROM fund_analysis_results WHERE fund_code = '020422'"
        df = db.execute_query(sql)
        
        print("fund_analysis_results表中的数据:")
        if df.empty:
            print("  未找到基金020422的数据")
        else:
            for _, row in df.iterrows():
                print(f"  fund_code: {row['fund_code']}")
                print(f"  fund_name: {row['fund_name']}")
                print(f"  fund_name类型: {type(row['fund_name'])}")
        
        # 检查fund_basic_info表
        sql2 = "SELECT fund_code, fund_name FROM fund_basic_info WHERE fund_code = '020422'"
        df2 = db.execute_query(sql2)
        
        print("\nfund_basic_info表中的数据:")
        if df2.empty:
            print("  未找到基金020422的数据")
        else:
            for _, row in df2.iterrows():
                print(f"  fund_code: {row['fund_code']}")
                print(f"  fund_name: {row['fund_name']}")
        
        # 检查所有包含020422的基金
        sql3 = "SELECT fund_code, fund_name FROM fund_analysis_results WHERE fund_code LIKE '%020422%'"
        df3 = db.execute_query(sql3)
        
        print("\n所有包含020422的基金:")
        if df3.empty:
            print("  未找到相关数据")
        else:
            for _, row in df3.iterrows():
                print(f"  fund_code: {row['fund_code']}")
                print(f"  fund_name: {row['fund_name']}")
                
    except Exception as e:
        print(f"检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_fund_020422()