#!/usr/bin/env python3
"""
本地开发环境配置脚本 - 使用SQLite替代MySQL
"""

import os
import sys
import sqlite3
from pathlib import Path

def setup_local_sqlite_env():
    """设置本地SQLite开发环境"""
    print("设置本地SQLite开发环境...")
    
    # 设置环境变量，强制使用SQLite
    os.environ['USE_SQLITE'] = 'true'
    os.environ['DB_TYPE'] = 'sqlite'
    os.environ['DB_PATH'] = 'fund_analysis.db'
    
    # 创建SQLite数据库文件
    db_path = Path('fund_analysis.db')
    if not db_path.exists():
        print(f"创建SQLite数据库文件: {db_path}")
        conn = sqlite3.connect(str(db_path))
        conn.close()
        print("✓ SQLite数据库文件创建成功")
    else:
        print(f"✓ SQLite数据库文件已存在: {db_path}")
    
    return db_path

def create_sqlite_database_schema():
    """创建SQLite数据库表结构"""
    print("创建SQLite数据库表结构...")
    
    db_path = 'fund_analysis.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建user_holdings表
    create_user_holdings = """
    CREATE TABLE IF NOT EXISTS user_holdings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        fund_code TEXT NOT NULL,
        fund_name TEXT NOT NULL,
        holding_shares REAL DEFAULT 0,
        cost_price REAL DEFAULT 0,
        holding_amount REAL DEFAULT 0,
        buy_date TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # 创建fund_analysis_results表
    create_analysis_results = """
    CREATE TABLE IF NOT EXISTS fund_analysis_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_code TEXT NOT NULL,
        fund_name TEXT NOT NULL,
        analysis_date DATE NOT NULL,
        yesterday_nav REAL DEFAULT 0,
        current_estimate REAL DEFAULT 0,
        today_return REAL DEFAULT 0,
        prev_day_return REAL DEFAULT 0,
        status_label TEXT,
        operation_suggestion TEXT,
        execution_amount TEXT,
        is_buy INTEGER DEFAULT 0,
        buy_multiplier REAL DEFAULT 0,
        redeem_amount REAL DEFAULT 0,
        comparison_value REAL DEFAULT 0,
        annualized_return REAL DEFAULT 0,
        sharpe_ratio REAL DEFAULT 0,
        sharpe_ratio_ytd REAL DEFAULT 0,
        sharpe_ratio_1y REAL DEFAULT 0,
        sharpe_ratio_all REAL DEFAULT 0,
        max_drawdown REAL DEFAULT 0,
        volatility REAL DEFAULT 0,
        calmar_ratio REAL DEFAULT 0,
        sortino_ratio REAL DEFAULT 0,
        var_95 REAL DEFAULT 0,
        win_rate REAL DEFAULT 0,
        profit_loss_ratio REAL DEFAULT 0,
        total_return REAL DEFAULT 0,
        composite_score REAL DEFAULT 0,
        UNIQUE(fund_code, analysis_date)
    )
    """
    
    try:
        cursor.execute(create_user_holdings)
        cursor.execute(create_analysis_results)
        conn.commit()
        print("✓ 数据库表结构创建成功")
    except Exception as e:
        print(f"✗ 创建表结构失败: {e}")
    finally:
        conn.close()

def insert_test_data():
    """插入测试数据"""
    print("插入测试数据...")
    
    db_path = 'fund_analysis.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 插入测试持仓数据
    test_holdings = [
        ('default_user', '100055', '测试基金1', 1000.0, 1.5, 1500.0, '2024-01-01', '测试备注1'),
        ('default_user', '110011', '测试基金2', 2000.0, 2.0, 4000.0, '2024-01-15', '测试备注2'),
        ('default_user', '000001', '测试基金3', 1500.0, 1.8, 2700.0, '2024-02-01', '测试备注3')
    ]
    
    insert_sql = """
    INSERT OR REPLACE INTO user_holdings 
    (user_id, fund_code, fund_name, holding_shares, cost_price, holding_amount, buy_date, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    try:
        cursor.executemany(insert_sql, test_holdings)
        conn.commit()
        print(f"✓ 插入 {len(test_holdings)} 条测试数据")
    except Exception as e:
        print(f"✗ 插入测试数据失败: {e}")
    finally:
        conn.close()

def patch_database_manager():
    """修补数据库管理器以支持SQLite"""
    print("创建SQLite适配器...")
    
    adapter_code = '''
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
'''
    
    # 保存适配器代码
    adapter_path = Path('web/sqlite_adapter.py')
    adapter_path.parent.mkdir(exist_ok=True)
    
    with open(adapter_path, 'w', encoding='utf-8') as f:
        f.write(adapter_code)
    
    print(f"✓ SQLite适配器已创建: {adapter_path}")

def update_app_py():
    """更新app.py以支持SQLite"""
    print("更新app.py以支持SQLite...")
    
    app_path = Path('web/app.py')
    if not app_path.exists():
        print("✗ 找不到app.py文件")
        return False
    
    # 备份原文件
    backup_path = app_path.with_suffix('.py.backup')
    if not backup_path.exists():
        import shutil
        shutil.copy2(app_path, backup_path)
        print(f"✓ 已备份原文件到: {backup_path}")
    
    # 读取原文件
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 添加SQLite支持的导入和配置
    sqlite_import_patch = '''import os
import logging

# SQLite支持
USE_SQLITE = os.environ.get('USE_SQLITE', 'false').lower() == 'true'

if USE_SQLITE:
    from .sqlite_adapter import sqlite_adapter, execute_query, execute_sql
    db_manager = sqlite_adapter
else:
    from data_retrieval.enhanced_database import EnhancedDatabaseManager
    from shared.config import DB_CONFIG
    db_manager = EnhancedDatabaseManager(DB_CONFIG)

# 确保db_manager有execute_query和execute_sql方法
if hasattr(db_manager, 'execute_query'):
    execute_query = db_manager.execute_query
else:
    def execute_query(sql, params=None):
        return db_manager.execute_query(sql, params or {})

if hasattr(db_manager, 'execute_sql'):
    execute_sql = db_manager.execute_sql
else:
    def execute_sql(sql, params=None):
        return db_manager.execute_sql(sql, params or {})
'''

    # 在合适的位置插入补丁
    if '# 数据库管理器' in content:
        # 找到数据库管理器初始化的位置
        lines = content.split('\n')
        patched_lines = []
        patched = False
        
        for line in lines:
            patched_lines.append(line)
            if not patched and '数据库管理器' in line and '#' in line:
                # 在注释后插入补丁
                patched_lines.extend(sqlite_import_patch.split('\n'))
                patched = True
        
        content = '\n'.join(patched_lines)
    else:
        # 如果没找到特定位置，在文件开头附近插入
        content = sqlite_import_patch + '\n' + content
    
    # 保存修改后的文件
    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ app.py已更新以支持SQLite")
    return True

def main():
    """主函数"""
    print("本地SQLite开发环境设置")
    print("=" * 40)
    
    try:
        # 1. 设置环境
        setup_local_sqlite_env()
        
        # 2. 创建数据库结构
        create_sqlite_database_schema()
        
        # 3. 插入测试数据
        insert_test_data()
        
        # 4. 创建适配器
        patch_database_manager()
        
        # 5. 更新应用配置
        # update_app_py()  # 暂时不自动更新，让用户手动决定
        
        print("\n" + "=" * 40)
        print("✓ 本地SQLite环境设置完成!")
        print("\n下一步操作:")
        print("1. 设置环境变量: set USE_SQLITE=true")
        print("2. 运行应用: python web/app.py")
        print("3. 访问: http://localhost:5000")
        
    except Exception as e:
        print(f"\n✗ 设置过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()