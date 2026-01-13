#!/usr/bin/env python
# coding: utf-8

"""
为基金分析结果表添加缺失的绩效指标列
"""

import pymysql
from sqlalchemy import create_engine
from datetime import date
import warnings
from sqlalchemy import text
warnings.filterwarnings('ignore', category=pymysql.Warning)

def add_missing_columns():
    """
    为基金分析结果表添加缺失的绩效指标列
    """
    # 数据库连接信息
    db_config = {
        'host': 'localhost',      # 数据库主机地址
        'user': 'root',           # 数据库用户名
        'password': 'root',       # 数据库密码
        'database': 'fund_analysis',  # 数据库名
        'port': 3306,             # 端口号
        'charset': 'utf8mb4'      # 字符编码
    }

    try:
        # 创建数据库连接
        connection_string = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}?charset={db_config['charset']}"
        engine = create_engine(connection_string)
        
        # 需要添加的列及其定义
        columns_to_add = [
            ("annualized_return", "FLOAT"),
            ("sharpe_ratio", "FLOAT"), 
            ("max_drawdown", "FLOAT"),
            ("volatility", "FLOAT"),
            ("calmar_ratio", "FLOAT"),
            ("sortino_ratio", "FLOAT"),
            ("var_95", "FLOAT"),
            ("win_rate", "FLOAT"),
            ("profit_loss_ratio", "FLOAT")
        ]
        
        # 检查并添加缺失的列
        with engine.connect() as conn:
            # 先获取现有列
            result = conn.execute(text("DESCRIBE fund_analysis_results;"))
            existing_columns = [row[0] for row in result.fetchall()]
            
            for col_name, col_type in columns_to_add:
                if col_name not in existing_columns:
                    alter_sql = f"ALTER TABLE fund_analysis_results ADD COLUMN {col_name} {col_type};"
                    conn.execute(text(alter_sql))
                    print(f"已添加列: {col_name} ({col_type})")
                else:
                    print(f"列已存在: {col_name}")
            
            conn.commit()
        
        print("所有缺失的列都已添加完成！")
        
        # 验证所有列都已存在
        with engine.connect() as conn:
            result = conn.execute(text("DESCRIBE fund_analysis_results;"))
            columns = [row[0] for row in result.fetchall()]
            print(f"表中现有列: {columns}")
        
        return True
        
    except Exception as e:
        print(f"添加列时出错: {str(e)}")
        return False

if __name__ == "__main__":
    success = add_missing_columns()
    if success:
        print("列添加成功！")
    else:
        print("列添加失败！")