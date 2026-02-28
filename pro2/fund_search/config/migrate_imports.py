#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动迁移脚本：更新旧配置导入语句

此脚本会自动扫描项目中的 Python 文件，将旧的配置导入更新为新的统一配置导入。

使用方法:
    python config/migrate_imports.py [--dry-run] [--fix]

选项:
    --dry-run   仅显示需要修改的文件，不实际修改
    --fix       执行实际的导入语句更新

示例:
    # 查看需要修改的文件
    python config/migrate_imports.py --dry-run
    
    # 执行修改
    python config/migrate_imports.py --fix
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Dict

# 迁移规则定义
MIGRATION_RULES = [
    # (旧导入模式, 新导入语句, 使用方式说明)
    (
        r"from shared\.config import\s+([^\n]+)",
        "from config import settings",
        "settings.database (替代 DB_CONFIG)"
    ),
    (
        r"from shared\.enhanced_config import\s+([^\n]+)",
        "from config import settings",
        "settings.database (替代 DATABASE_CONFIG), settings.notification (替代 NOTIFICATION_CONFIG)"
    ),
    (
        r"from shared\.config_manager import\s+config_manager",
        "from config import settings",
        "settings.database (替代 config_manager.get_database_config())"
    ),
    (
        r"from shared\.config_manager import\s+ConfigManager",
        "from config import Settings",
        "Settings() (替代 ConfigManager)"
    ),
    (
        r"from shared\.fund_data_config import\s+([^\n]+)",
        "from config import settings",
        "settings.datasource (替代 DATA_SOURCE_CONFIG), settings.cache (替代 CacheConfig)"
    ),
    (
        r"from backtesting\.core\.strategy_config import\s+([^\n]+)",
        "from config import settings",
        "settings.strategy (替代 get_strategy_config())"
    ),
    (
        r"from data_retrieval\.utils\.ocr_config import\s+([^\n]+)",
        "from config import settings",
        "settings.ocr (替代 OCR_CONFIG)"
    ),
    (
        r"from services\.celery_config import\s+([^\n]+)",
        "from config import settings",
        "settings.celery (替代 CELERY_CONFIG)"
    ),
]

# 配置使用映射
CONFIG_USAGE_MAP = {
    'DB_CONFIG': 'settings.database',
    'DATABASE_CONFIG': 'settings.database',
    'CACHE_CONFIG': 'settings.cache',
    'NOTIFICATION_CONFIG': 'settings.notification',
    'WECHAT_CONFIG': 'settings.notification.wechat',
    'EMAIL_CONFIG': 'settings.notification.email',
    'DATA_SOURCE_CONFIG': 'settings.datasource',
    'TUSHARE_CONFIG': 'settings.datasource.tushare',
    'AKSHARE_CONFIG': 'settings.datasource.akshare',
    'INVESTMENT_STRATEGY_CONFIG': 'settings.strategy',
    'STRATEGY_CONFIG': 'settings.strategy',
    'PERFORMANCE_CONFIG': 'settings.strategy',  # 注意：可能需要调整
    'CHART_CONFIG': {
        'dpi': 'settings.system.chart_dpi',
        'style': 'settings.system.chart_style',
    },
    'LOGGING_CONFIG': 'settings.logging',
    'BASE_CONFIG': 'settings.system',
    'APP_CONFIG': 'settings.web',
    'SYSTEM_CONFIG': 'settings.system',
    'CELERY_CONFIG': 'settings.celery',
    'OCR_CONFIG': 'settings.ocr',
}


class ImportMigrator:
    """导入迁移器"""
    
    def __init__(self, project_root: Path, dry_run: bool = True):
        self.project_root = project_root
        self.dry_run = dry_run
        self.changes: List[Tuple[Path, str, str, str]] = []  # (文件, 旧代码, 新代码, 说明)
    
    def scan_files(self) -> List[Path]:
        """扫描所有 Python 文件"""
        python_files = []
        
        # 扫描 fund_search 目录
        fund_search_dir = self.project_root / 'fund_search'
        if fund_search_dir.exists():
            for py_file in fund_search_dir.rglob("*.py"):
                # 跳过迁移脚本本身
                if py_file.name == 'migrate_imports.py':
                    continue
                # 跳过 __pycache__
                if '__pycache__' in str(py_file):
                    continue
                python_files.append(py_file)
        
        return python_files
    
    def analyze_file(self, file_path: Path) -> List[Tuple[str, str, str]]:
        """
        分析文件中的旧配置导入
        
        Returns:
            [(旧导入, 新导入, 使用说明), ...]
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"  无法读取文件 {file_path}: {e}")
            return []
        
        matches = []
        
        for pattern, new_import, usage in MIGRATION_RULES:
            for match in re.finditer(pattern, content):
                old_import = match.group(0)
                matches.append((old_import, new_import, usage))
        
        return matches
    
    def generate_usage_guide(self, imported_names: List[str]) -> str:
        """生成使用指南"""
        guides = []
        
        for name in imported_names:
            name = name.strip()
            if name in CONFIG_USAGE_MAP:
                mapping = CONFIG_USAGE_MAP[name]
                if isinstance(mapping, dict):
                    guides.append(f"  {name}: 需要分别访问")
                    for key, new_path in mapping.items():
                        guides.append(f"    {name}['{key}'] -> {new_path}")
                else:
                    guides.append(f"  {name} -> {mapping}")
        
        return "\n".join(guides) if guides else "  无需修改使用方式"
    
    def migrate_file(self, file_path: Path) -> bool:
        """迁移单个文件"""
        matches = self.analyze_file(file_path)
        
        if not matches:
            return False
        
        relative_path = file_path.relative_to(self.project_root)
        print(f"\n{'='*60}")
        print(f"文件: {relative_path}")
        print('='*60)
        
        for old_import, new_import, usage in matches:
            print(f"\n发现旧导入:")
            print(f"  旧: {old_import}")
            print(f"  新: {new_import}")
            
            # 提取导入的配置名称
            imported_names = []
            if 'import' in old_import:
                # 处理 from x import a, b, c
                match = re.search(r'import\s+(.+)$', old_import)
                if match:
                    imported_names = [n.strip() for n in match.group(1).split(',')]
            
            if imported_names:
                guide = self.generate_usage_guide(imported_names)
                print(f"\n使用方式变更:")
                print(guide)
            
            self.changes.append((relative_path, old_import, new_import, usage))
        
        return True
    
    def generate_migration_report(self) -> str:
        """生成迁移报告"""
        lines = []
        lines.append("# 配置迁移报告")
        lines.append("")
        lines.append(f"总计发现 {len(self.changes)} 处需要迁移的导入")
        lines.append("")
        
        # 按文件分组
        by_file: Dict[str, List[Tuple]] = {}
        for file_path, old_import, new_import, usage in self.changes:
            file_str = str(file_path)
            if file_str not in by_file:
                by_file[file_str] = []
            by_file[file_str].append((old_import, new_import, usage))
        
        for file_path, changes in sorted(by_file.items()):
            lines.append(f"## {file_path}")
            lines.append("")
            for old_import, new_import, usage in changes:
                lines.append(f"- **旧导入**: `{old_import}`")
                lines.append(f"- **新导入**: `{new_import}`")
                lines.append(f"- **使用方式**: {usage}")
                lines.append("")
        
        return "\n".join(lines)
    
    def run(self):
        """运行迁移分析"""
        print("="*60)
        print("配置导入迁移分析")
        print("="*60)
        print(f"项目根目录: {self.project_root}")
        print(f"模式: {'预览' if self.dry_run else '实际修改'}")
        print("")
        
        # 扫描文件
        python_files = self.scan_files()
        print(f"扫描到 {len(python_files)} 个 Python 文件")
        
        # 分析每个文件
        affected_files = 0
        for py_file in python_files:
            if self.migrate_file(py_file):
                affected_files += 1
        
        # 输出汇总
        print(f"\n{'='*60}")
        print("迁移分析汇总")
        print('='*60)
        print(f"受影响文件数: {affected_files}")
        print(f"需要迁移的导入: {len(self.changes)}")
        
        # 生成报告
        if self.changes:
            report = self.generate_migration_report()
            report_file = self.project_root / 'config' / 'MIGRATION_REPORT.md'
            
            if not self.dry_run:
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"\n迁移报告已保存: {report_file}")
            else:
                print("\n" + report)
        
        return len(self.changes)


def apply_manual_migration_fixes(project_root: Path):
    """
    应用手动迁移修复
    
    由于配置使用方式复杂，部分文件需要手动调整
    """
    manual_fixes = [
        # (文件路径, 旧代码, 新代码)
        (
            "fund_search/enhanced_main.py",
            "from shared.enhanced_config import BASE_CONFIG, DATABASE_CONFIG, NOTIFICATION_CONFIG",
            "from config import settings\n# 使用方式: settings.system (替代 BASE_CONFIG), settings.database (替代 DATABASE_CONFIG), settings.notification (替代 NOTIFICATION_CONFIG)"
        ),
        # 添加更多需要手动修复的文件...
    ]
    
    print("\n" + "="*60)
    print("手动迁移修复")
    print("="*60)
    
    for file_rel, old_code, new_code in manual_fixes:
        file_path = project_root / file_rel
        if file_path.exists():
            print(f"\n文件: {file_rel}")
            print(f"建议修改:")
            print(f"  旧: {old_code}")
            print(f"  新: {new_code}")


def main():
    parser = argparse.ArgumentParser(description='迁移旧配置导入到新配置系统')
    parser.add_argument('--dry-run', action='store_true', 
                       help='仅显示需要修改的文件，不实际修改')
    parser.add_argument('--fix', action='store_true',
                       help='执行实际的导入语句更新')
    
    args = parser.parse_args()
    
    # 确定项目根目录
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent  # config/ -> fund_search/ -> project/
    
    if not (project_root / 'fund_search').exists():
        print(f"错误: 找不到项目根目录: {project_root}")
        sys.exit(1)
    
    # 默认使用 dry-run 模式
    dry_run = not args.fix
    
    # 运行迁移分析
    migrator = ImportMigrator(project_root, dry_run=dry_run)
    count = migrator.run()
    
    # 显示手动修复建议
    apply_manual_migration_fixes(project_root)
    
    if count > 0:
        print(f"\n{'='*60}")
        if dry_run:
            print("提示: 使用 --fix 参数执行实际修改")
            print("注意: 由于配置使用方式复杂，建议手动检查每个文件")
        else:
            print("迁移完成！请检查修改后的文件")
    
    return 0 if dry_run else 0


if __name__ == '__main__':
    sys.exit(main())
