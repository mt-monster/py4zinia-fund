#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
应用配置迁移 - 批量更新导入语句

此脚本会实际修改文件，将旧的配置导入更新为新的统一配置导入。
请确保在运行前已备份代码或提交到版本控制。

使用方法:
    python config/apply_migration.py

警告:
    此脚本会直接修改源文件，请确保:
    1. 已备份代码
    2. 或已提交到版本控制
    3. 在修改后运行测试验证
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict


# 文件迁移配置
# 格式: (文件路径, [(旧导入, 新导入, 使用方式映射)])
MIGRATION_PLAN = [
    # enhanced_main.py
    (
        "fund_search/enhanced_main.py",
        [
            (
                "from shared.enhanced_config import BASE_CONFIG, DATABASE_CONFIG, NOTIFICATION_CONFIG",
                "from config import settings",
                {
                    "BASE_CONFIG": "settings.system",
                    "BASE_CONFIG[": "settings.system.",
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                    "NOTIFICATION_CONFIG": "settings.notification",
                    "NOTIFICATION_CONFIG[": "settings.notification.",
                    "NOTIFICATION_CONFIG.": "settings.notification.",
                }
            ),
        ]
    ),
    
    # web/routes/funds.py
    (
        "fund_search/web/routes/funds.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG, NOTIFICATION_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                    "NOTIFICATION_CONFIG": "settings.notification",
                    "NOTIFICATION_CONFIG[": "settings.notification.",
                    "NOTIFICATION_CONFIG.": "settings.notification.",
                }
            ),
        ]
    ),
    
    # web/routes/holdings.py
    (
        "fund_search/web/routes/holdings.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG, NOTIFICATION_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                    "NOTIFICATION_CONFIG": "settings.notification",
                    "NOTIFICATION_CONFIG[": "settings.notification.",
                    "NOTIFICATION_CONFIG.": "settings.notification.",
                }
            ),
            (
                "from shared.enhanced_config import DATABASE_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                }
            ),
        ]
    ),
    
    # web/routes/dashboard.py
    (
        "fund_search/web/routes/dashboard.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG, NOTIFICATION_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                    "NOTIFICATION_CONFIG": "settings.notification",
                    "NOTIFICATION_CONFIG[": "settings.notification.",
                    "NOTIFICATION_CONFIG.": "settings.notification.",
                }
            ),
        ]
    ),
    
    # web/routes/analysis.py
    (
        "fund_search/web/routes/analysis.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG, NOTIFICATION_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                    "NOTIFICATION_CONFIG": "settings.notification",
                    "NOTIFICATION_CONFIG[": "settings.notification.",
                    "NOTIFICATION_CONFIG.": "settings.notification.",
                }
            ),
        ]
    ),
    
    # web/routes/backtest.py
    (
        "fund_search/web/routes/backtest.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG, NOTIFICATION_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                    "NOTIFICATION_CONFIG": "settings.notification",
                    "NOTIFICATION_CONFIG[": "settings.notification.",
                    "NOTIFICATION_CONFIG.": "settings.notification.",
                }
            ),
        ]
    ),
    
    # web/routes/strategies.py
    (
        "fund_search/web/routes/strategies.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG, NOTIFICATION_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                    "NOTIFICATION_CONFIG": "settings.notification",
                    "NOTIFICATION_CONFIG[": "settings.notification.",
                    "NOTIFICATION_CONFIG.": "settings.notification.",
                }
            ),
        ]
    ),
    
    # web/routes/etf.py
    (
        "fund_search/web/routes/etf.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG, NOTIFICATION_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                    "NOTIFICATION_CONFIG": "settings.notification",
                    "NOTIFICATION_CONFIG[": "settings.notification.",
                    "NOTIFICATION_CONFIG.": "settings.notification.",
                }
            ),
        ]
    ),
    
    # services/fund_analyzer.py
    (
        "fund_search/services/fund_analyzer.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                }
            ),
        ]
    ),
    
    # services/notification.py
    (
        "fund_search/services/notification.py",
        [
            (
                "from shared.enhanced_config import NOTIFICATION_CONFIG",
                "from config import settings",
                {
                    "NOTIFICATION_CONFIG": "settings.notification",
                    "NOTIFICATION_CONFIG[": "settings.notification.",
                    "NOTIFICATION_CONFIG.": "settings.notification.",
                }
            ),
        ]
    ),
    
    # scripts/create_cache_tables.py
    (
        "fund_search/scripts/create_cache_tables.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                }
            ),
        ]
    ),
    
    # scripts/init_cache_system.py
    (
        "fund_search/scripts/init_cache_system.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                }
            ),
        ]
    ),
    
    # scripts/diagnose_performance.py
    (
        "fund_search/scripts/diagnose_performance.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                }
            ),
        ]
    ),
    
    # scripts/sync_fund_nav_data.py
    (
        "fund_search/scripts/sync_fund_nav_data.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                }
            ),
        ]
    ),
    
    # scripts/verify_and_init_cache.py
    (
        "fund_search/scripts/verify_and_init_cache.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                }
            ),
        ]
    ),
    
    # scripts/db_schema_optimizer.py
    (
        "fund_search/scripts/db_schema_optimizer.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                }
            ),
        ]
    ),
    
    # setup_local_dev.py
    (
        "fund_search/setup_local_dev.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                }
            ),
        ]
    ),
    
    # data_access/enhanced_database.py
    (
        "fund_search/data_access/enhanced_database.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                }
            ),
        ]
    ),
    
    # services/portfolio_importer.py
    (
        "fund_search/services/portfolio_importer.py",
        [
            (
                "from shared.enhanced_config import DATABASE_CONFIG",
                "from config import settings",
                {
                    "DATABASE_CONFIG": "settings.database",
                    "DATABASE_CONFIG[": "settings.database.",
                    "DATABASE_CONFIG.": "settings.database.",
                }
            ),
        ]
    ),
    
    # web/real_data_fetcher.py
    (
        "fund_search/web/real_data_fetcher.py",
        [
            (
                "from shared.enhanced_config import DATA_SOURCE_CONFIG",
                "from config import settings",
                {
                    "DATA_SOURCE_CONFIG": "settings.datasource",
                    "DATA_SOURCE_CONFIG[": "settings.datasource.",
                    "DATA_SOURCE_CONFIG.": "settings.datasource.",
                }
            ),
        ]
    ),
    
    # services/holding_realtime_service.py
    (
        "fund_search/services/holding_realtime_service.py",
        [
            (
                "from shared.enhanced_config import DATA_SOURCE_CONFIG",
                "from config import settings",
                {
                    "DATA_SOURCE_CONFIG": "settings.datasource",
                    "DATA_SOURCE_CONFIG[": "settings.datasource.",
                    "DATA_SOURCE_CONFIG.": "settings.datasource.",
                }
            ),
        ]
    ),
    
    # data_retrieval/fetchers/heavyweight_stocks_fetcher.py
    (
        "fund_search/data_retrieval/fetchers/heavyweight_stocks_fetcher.py",
        [
            (
                "from shared.enhanced_config import DATA_SOURCE_CONFIG",
                "from config import settings",
                {
                    "DATA_SOURCE_CONFIG": "settings.datasource",
                    "DATA_SOURCE_CONFIG[": "settings.datasource.",
                    "DATA_SOURCE_CONFIG.": "settings.datasource.",
                }
            ),
        ]
    ),
]


def apply_migration(file_path: Path, migrations: List[Tuple]) -> bool:
    """
    应用迁移到单个文件
    
    Args:
        file_path: 文件路径
        migrations: 迁移规则列表 [(旧导入, 新导入, 使用方式映射), ...]
        
    Returns:
        是否成功修改
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  错误: 无法读取文件 {file_path}: {e}")
        return False
    
    original_content = content
    modified = False
    
    for old_import, new_import, usage_map in migrations:
        # 检查是否存在旧导入
        if old_import in content:
            # 替换导入语句
            content = content.replace(old_import, new_import)
            modified = True
            print(f"  替换导入: {old_import[:50]}... -> {new_import}")
            
            # 替换使用方式
            for old_usage, new_usage in usage_map.items():
                if old_usage in content:
                    content = content.replace(old_usage, new_usage)
                    print(f"    替换使用: {old_usage} -> {new_usage}")
    
    if modified:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  [OK] 已更新: {file_path}")
            return True
        except Exception as e:
            print(f"  [FAIL] 保存失败 {file_path}: {e}")
            return False
    else:
        print(f"  [SKIP] 无需修改: {file_path}")
        return False


def main():
    """主函数"""
    print("=" * 70)
    print("配置迁移 - 批量更新导入语句")
    print("=" * 70)
    print()
    print("警告: 此脚本会直接修改源文件!")
    print("请确保已备份代码或提交到版本控制。")
    print()
    
    # 确认执行
    response = input("是否继续? (yes/no): ")
    if response.lower() not in ('yes', 'y'):
        print("已取消")
        return 0
    
    print()
    
    # 确定项目根目录
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent  # config/ -> fund_search/ -> project/
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    # 应用迁移
    for file_rel, migrations in MIGRATION_PLAN:
        file_path = project_root / file_rel
        
        print(f"\n处理: {file_rel}")
        print("-" * 70)
        
        if not file_path.exists():
            print(f"  [SKIP] 文件不存在: {file_path}")
            skip_count += 1
            continue
        
        if apply_migration(file_path, migrations):
            success_count += 1
        else:
            fail_count += 1
    
    # 输出汇总
    print("\n" + "=" * 70)
    print("迁移完成")
    print("=" * 70)
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"跳过: {skip_count}")
    
    if success_count > 0:
        print("\n[重要] 请执行以下操作:")
        print("1. 检查修改后的文件")
        print("2. 运行测试验证功能正常")
        print("3. 如有问题，使用版本控制回滚")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
