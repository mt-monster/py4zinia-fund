#!/usr/bin/env python3
"""
本地开发环境配置脚本 - MySQL环境配置助手
帮助开发者快速配置本地MySQL开发环境
"""

import os
from pathlib import Path

def setup_local_mysql_env():
    """设置本地MySQL开发环境"""
    print("设置本地MySQL开发环境...")
    print("=" * 50)
    
    # 默认本地MySQL配置
    default_config = {
        'DB_HOST': 'localhost',
        'DB_USER': 'root',
        'DB_PASSWORD': '123456',
        'DB_NAME': 'fund_analysis',
        'DB_PORT': '3306',
        'DB_CHARSET': 'utf8mb4'
    }
    
    print("\n当前数据库配置:")
    for key, value in default_config.items():
        env_value = os.environ.get(key, value)
        print(f"  {key}: {env_value}")
    
    print("\n如需修改配置，请设置以下环境变量:")
    print("  set DB_HOST=your_host")
    print("  set DB_USER=your_user")
    print("  set DB_PASSWORD=your_password")
    print("  set DB_NAME=your_database")
    print("  set DB_PORT=3306")
    
    return default_config

def check_mysql_connection():
    """检查MySQL连接"""
    print("\n检查MySQL连接...")
    
    try:
        from data_access.enhanced_database import EnhancedDatabaseManager
        from shared.enhanced_config import DATABASE_CONFIG
        
        db = EnhancedDatabaseManager(DATABASE_CONFIG)
        
        # 测试查询
        result = db.execute_query("SELECT VERSION() as version")
        if not result.empty:
            version = result.iloc[0]['version']
            print(f"✓ MySQL连接成功")
            print(f"  版本: {version}")
            
            # 检查数据库中的表
            tables = db.execute_query("SHOW TABLES")
            if not tables.empty:
                print(f"\n现有数据表 ({len(tables)} 个):")
                for table in tables.iloc[:, 0]:
                    print(f"  - {table}")
            else:
                print("\n数据库中暂无表，将自动创建")
            
            db.close()
            return True
        else:
            print("✗ 无法获取MySQL版本信息")
            db.close()
            return False
            
    except ImportError as e:
        print(f"✗ 导入模块失败: {e}")
        print("  请确保在项目根目录运行此脚本")
        return False
    except Exception as e:
        print(f"✗ MySQL连接失败: {e}")
        print("\n可能的原因:")
        print("  1. MySQL服务未启动")
        print("  2. 连接配置不正确")
        print("  3. 数据库用户权限不足")
        print("\n请检查:")
        print("  1. MySQL服务是否运行: net start mysql")
        print("  2. 配置文件中的连接信息是否正确")
        return False

def create_docker_mysql():
    """提供Docker运行MySQL的命令"""
    print("\n使用Docker快速启动MySQL:")
    print("-" * 50)
    print("docker run -d \\")
    print("  --name fund-mysql \\")
    print("  -e MYSQL_ROOT_PASSWORD=123456 \\")
    print("  -e MYSQL_DATABASE=fund_analysis \\")
    print("  -p 3306:3306 \\")
    print("  --restart unless-stopped \\")
    print("  mysql:8.0 \\")
    print("  --character-set-server=utf8mb4 \\")
    print("  --collation-server=utf8mb4_unicode_ci")
    print("-" * 50)

def show_quick_start_guide():
    """显示快速开始指南"""
    print("\n" + "=" * 50)
    print("快速开始指南")
    print("=" * 50)
    
    print("\n1. 确保MySQL已安装并运行:")
    print("   - Windows: net start mysql")
    print("   - Linux: sudo systemctl start mysql")
    print("   - Mac: brew services start mysql")
    
    print("\n2. 创建数据库（如不存在）:")
    print("   mysql -u root -p")
    print("   CREATE DATABASE fund_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    
    print("\n3. 运行应用:")
    print("   cd pro2/fund_search")
    print("   python -m web.app")
    
    print("\n4. 访问应用:")
    print("   http://localhost:5000")
    
    print("\n5. 首次启动会自动:")
    print("   - 创建所有必需的表")
    print("   - 同步持仓基金的历史净值数据")
    print("   - 预加载数据到内存缓存")

def main():
    """主函数"""
    print("基金分析系统 - 本地开发环境配置")
    print("=" * 50)
    
    # 1. 显示配置
    setup_local_mysql_env()
    
    # 2. 检查连接
    check_mysql_connection()
    
    # 3. 显示Docker命令
    create_docker_mysql()
    
    # 4. 显示指南
    show_quick_start_guide()
    
    print("\n" + "=" * 50)
    print("配置完成!")
    print("=" * 50)

if __name__ == "__main__":
    main()
