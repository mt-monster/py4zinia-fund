
#!/usr/bin/env python3
"""
SQLite数据库适配器 - 用于本地开发环境
"""

import sqlite3
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)

class SQLiteAdapter:
    """SQLite数据库适配器"""
    
    def __init__(self, db_path: str = 'fund_analysis.db'):
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """建立数据库连接"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
            logger.info(f"SQLite连接成功: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"SQLite连接失败: {e}")
            return False
    
    def disconnect(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("SQLite连接已关闭")
    
    def execute_query(self, sql: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """执行查询并返回DataFrame"""
        if not self.conn:
            if not self.connect():
                return pd.DataFrame()
        
        try:
            if params:
                cursor = self.conn.execute(sql, params)
            else:
                cursor = self.conn.execute(sql)
            
            # 获取列名
            columns = [description[0] for description in cursor.description]
            
            # 获取数据
            rows = cursor.fetchall()
            
            # 转换为DataFrame
            if rows:
                df = pd.DataFrame(rows, columns=columns)
                # 转换数据类型
                for col in df.columns:
                    if df[col].dtype == 'object':
                        # 尝试转换数值类型
                        try:
                            df[col] = pd.to_numeric(df[col], errors='ignore')
                        except:
                            pass
                return df
            else:
                return pd.DataFrame(columns=columns)
                
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            logger.error(f"SQL: {sql}")
            if params:
                logger.error(f"参数: {params}")
            return pd.DataFrame()
    
    def execute_sql(self, sql: str, params: Optional[Union[Dict, tuple]] = None) -> bool:
        """执行SQL语句"""
        if not self.conn:
            if not self.connect():
                return False
        
        try:
            if params:
                self.conn.execute(sql, params)
            else:
                self.conn.execute(sql)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"SQL执行失败: {e}")
            logger.error(f"SQL: {sql}")
            if params:
                logger.error(f"参数: {params}")
            return False
    
    def get_table_list(self) -> List[str]:
        """获取表列表"""
        sql = "SELECT name FROM sqlite_master WHERE type='table'"
        df = self.execute_query(sql)
        return df['name'].tolist() if not df.empty else []
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        df = self.execute_query(sql, (table_name,))
        return len(df) > 0

# 创建全局实例
sqlite_adapter = SQLiteAdapter()

# 兼容原有接口的包装函数
def execute_query(sql: str, params: Optional[Dict] = None) -> pd.DataFrame:
    """兼容原有的execute_query接口"""
    return sqlite_adapter.execute_query(sql, params)

def execute_sql(sql: str, params: Optional[Union[Dict, tuple]] = None) -> bool:
    """兼容原有的execute_sql接口"""
    return sqlite_adapter.execute_sql(sql, params)
