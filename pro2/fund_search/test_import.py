#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试 fund_analyzer 导入"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print("测试导入 FundAnalyzer...")
try:
    from services.fund_analyzer import FundAnalyzer
    print("✅ FundAnalyzer 导入成功!")
    
    print("\n测试导入 MultiSourceDataAdapter...")
    from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
    print("✅ MultiSourceDataAdapter 导入成功!")
    
    print("\n测试导入 EnhancedDatabaseManager...")
    from data_access.enhanced_database import EnhancedDatabaseManager
    print("✅ EnhancedDatabaseManager 导入成功!")
    
    print("\n🎉 所有导入测试通过!")
    
except Exception as e:
    print(f"❌ 导入失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
