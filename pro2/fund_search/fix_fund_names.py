#!/usr/bin/env python
# coding: utf-8

"""修复基金名称显示问题"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_retrieval.enhanced_database import EnhancedDatabaseManager
from shared.enhanced_config import DATABASE_CONFIG
import pandas as pd

def fix_fund_names():
    """修复基金名称显示问题"""
    print("修复基金名称显示问题...")
    
    try:
        db = EnhancedDatabaseManager(DATABASE_CONFIG)
        
        # 检查所有fund_analysis_results表中fund_name为基金代码格式的记录
        sql = """
        SELECT fund_code, fund_name 
        FROM fund_analysis_results 
        WHERE fund_name LIKE '基金%' OR fund_name REGEXP '^[0-9]{6}$'
        """
        df = db.execute_query(sql)
        
        print(f"发现 {len(df)} 条基金名称可能有问题的记录:")
        
        fixed_count = 0
        for _, row in df.iterrows():
            fund_code = row['fund_code']
            current_name = row['fund_name']
            
            print(f"  基金 {fund_code}: 当前名称 = '{current_name}'")
            
            # 尝试从其他表获取正确的基金名称
            correct_name = None
            
            # 1. 从fund_basic_info表获取
            sql_basic = "SELECT fund_name FROM fund_basic_info WHERE fund_code = %s LIMIT 1"
            df_basic = db.execute_query_raw(sql_basic, (fund_code,))
            if df_basic and len(df_basic) > 0 and df_basic[0][0]:
                correct_name = df_basic[0][0]
                print(f"    ✓ 从fund_basic_info获取到名称: {correct_name}")
            
            # 2. 如果fund_basic_info中没有，尝试从akshare获取
            if not correct_name:
                try:
                    import akshare as ak
                    fund_list = ak.fund_name_em()
                    if fund_list is not None and not fund_list.empty:
                        fund_list.columns = ['code', 'pinyin_short', 'name', 'type', 'pinyin_full']
                        fund_row = fund_list[fund_list['code'] == fund_code]
                        if not fund_row.empty:
                            correct_name = fund_row.iloc[0]['name']
                            print(f"    ✓ 从akshare获取到名称: {correct_name}")
                except Exception as e:
                    print(f"    ✗ 从akshare获取失败: {e}")
            
            # 3. 如果都获取不到，使用默认格式但确保不是纯数字
            if not correct_name:
                correct_name = f"基金{fund_code}"
                print(f"    ! 使用默认格式: {correct_name}")
            
            # 更新数据库
            if correct_name and correct_name != current_name:
                update_sql = """
                UPDATE fund_analysis_results 
                SET fund_name = %s 
                WHERE fund_code = %s
                """
                db.execute_sql(update_sql, (correct_name, fund_code))
                print(f"    ✓ 已更新基金名称")
                fixed_count += 1
            else:
                print(f"    - 无需更新")
        
        print(f"\n总共修复了 {fixed_count} 条记录")
        
        # 验证修复结果
        print("\n验证修复结果:")
        verify_sql = "SELECT fund_code, fund_name FROM fund_analysis_results WHERE fund_code = '020422'"
        verify_df = db.execute_query(verify_sql)
        if not verify_df.empty:
            row = verify_df.iloc[0]
            print(f"  基金020422: {row['fund_name']}")
        
    except Exception as e:
        print(f"修复失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_fund_names()