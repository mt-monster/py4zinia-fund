#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目入口文件 - 用于 Gitee CI 测试
"""

import sys
import os

# 添加 pro2 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pro2'))

def main():
    """主函数"""
    print("=" * 60)
    print("基金分析工具 - Gitee CI 测试")
    print("=" * 60)
    
    # 检查 Python 版本
    print(f"Python 版本: {sys.version}")
    
    # 检查关键依赖
    try:
        import numpy
        print(f"NumPy 版本: {numpy.__version__}")
    except ImportError:
        print("警告: NumPy 未安装")
    
    try:
        import pandas
        print(f"Pandas 版本: {pandas.__version__}")
    except ImportError:
        print("警告: Pandas 未安装")
    
    try:
        import flask
        print(f"Flask 版本: {flask.__version__}")
    except ImportError:
        print("警告: Flask 未安装")
    
    try:
        import sqlalchemy
        print(f"SQLAlchemy 版本: {sqlalchemy.__version__}")
    except ImportError:
        print("警告: SQLAlchemy 未安装")
    
    print("=" * 60)
    print("依赖检查完成!")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
