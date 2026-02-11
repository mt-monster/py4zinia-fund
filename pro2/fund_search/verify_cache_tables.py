#!/usr/bin/env python
# coding: utf-8

"""
验证缓存表是否存在
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.enhanced_config import DATABASE_CONFIG
from data_retrieval.enhanced_database import EnhancedDatabaseManager

def verify_cache_tables():
    """验证缓存表是否存在"""
    print("验证缓存表...")
    
    try:
        # 初始化数据库管理器
        db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        
        # 检查关键表是否存在
        tables_to_check = ['fund_nav_cache', 'fund_cache_metadata']
        
        for table in tables_to_check:
            try:
                result = db_manager.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                count = result.iloc[0]['count']
                print(f"✓ 表 {table} 存在，记录数: {count}")
            except Exception as e:
                print(f"✗ 表 {table} 不存在或访问失败: {e}")
        
        # 测试插入一条记录
        try:
            test_sql = """
                INSERT INTO fund_nav_cache 
                (fund_code, nav_date, nav_value, daily_return, data_source)
                VALUES ('000001', '2026-02-10', 1.5, 2.5, 'test')
                ON DUPLICATE KEY UPDATE nav_value = VALUES(nav_value)
            """
            db_manager.execute_sql(test_sql)
            print("✓ 插入测试记录成功")
            
            # 删除测试记录
            db_manager.execute_sql("DELETE FROM fund_nav_cache WHERE fund_code = '000001'")
            print("✓ 清理测试记录成功")
            
        except Exception as e:
            print(f"✗ 插入测试失败: {e}")
            
    except Exception as e:
        print(f"验证失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_cache_tables()