#!/usr/bin/env python
# coding: utf-8

"""
创建缓存表脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.enhanced_config import DATABASE_CONFIG
from data_retrieval.enhanced_database import EnhancedDatabaseManager

def create_cache_tables():
    """创建缓存相关表"""
    print("开始创建缓存表...")
    
    try:
        # 初始化数据库管理器
        db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        
        # 读取SQL文件
        sql_file = "sql/001_create_cache_tables.sql"
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割成单个语句并执行
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        for stmt in statements:
            if stmt.upper().startswith('CREATE TABLE'):
                print(f"执行: {stmt[:50]}...")
                db_manager.execute_sql(stmt)
        
        print("缓存表创建完成!")
        
    except Exception as e:
        print(f"创建缓存表失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_cache_tables()