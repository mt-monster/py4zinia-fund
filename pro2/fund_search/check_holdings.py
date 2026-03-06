#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查用户持仓数据"""

import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.config_manager import config_manager
from data_access.enhanced_database import EnhancedDatabaseManager

# 获取数据库配置
db_config = config_manager.get_database_config()

# 创建数据库管理器
db_manager = EnhancedDatabaseManager({
    'host': db_config.host,
    'user': db_config.user,
    'password': db_config.password,
    'database': db_config.database,
    'port': db_config.port,
    'charset': db_config.charset
})

if not db_manager:
    print("数据库连接失败")
    sys.exit(1)

print("数据库连接成功\n")

# 检查 user_holdings 表
try:
    query = """
    SELECT * FROM user_holdings 
    WHERE user_id = 'default_user' AND holding_shares > 0
    """
    result = db_manager.execute_query(query)
    
    print(f"user_holdings 表查询结果: {len(result)} 条记录\n")
    
    if not result.empty:
        print("持仓数据:")
        print(result.to_string())
    else:
        print("表中没有数据")
        
    # 检查表结构
    print("\n\n表结构:")
    schema_query = "DESCRIBE user_holdings"
    schema = db_manager.execute_query(schema_query)
    print(schema.to_string())
    
except Exception as e:
    print(f"查询出错: {e}")
    import traceback
    traceback.print_exc()

# 检查数据库中是否有任何持仓数据
try:
    print("\n\n所有持仓数据 (不限制 user_id):")
    all_query = "SELECT * FROM user_holdings LIMIT 10"
    all_result = db_manager.execute_query(all_query)
    print(f"共 {len(all_result)} 条记录")
    if not all_result.empty:
        print(all_result.to_string())
except Exception as e:
    print(f"查询所有持仓出错: {e}")
