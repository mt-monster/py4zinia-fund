#!/usr/bin/env python
# coding: utf-8

"""
修复报告文件路径脚本
将错误位置的报告文件移动到正确的 reports 目录
"""

import os
import shutil
import glob

def fix_report_paths():
    """修复报告文件路径"""
    
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # pro2/fund_search/scripts -> pro2
    pro2_dir = os.path.dirname(os.path.dirname(script_dir))
    reports_dir = os.path.join(pro2_dir, 'reports')
    
    print(f"脚本目录: {script_dir}")
    print(f"pro2目录: {pro2_dir}")
    print(f"reports目录: {reports_dir}")
    print()
    
    # 确保reports目录存在
    os.makedirs(reports_dir, exist_ok=True)
    
    # 查找所有错误位置的报告文件（在pro2目录下，但不在reports子目录中）
    error_files = []
    
    # 查找所有.png文件
    for file in glob.glob(os.path.join(pro2_dir, 'reports*.png')):
        if os.path.isfile(file):
            error_files.append(file)
    
    # 查找所有.md报告文件
    for file in glob.glob(os.path.join(pro2_dir, '*分析*.md')):
        if os.path.isfile(file):
            error_files.append(file)
    
    if not error_files:
        print("✅ 没有发现错误位置的报告文件")
        return
    
    print(f"发现 {len(error_files)} 个错误位置的报告文件:")
    print()
    
    # 移动文件
    moved_count = 0
    for error_file in error_files:
        filename = os.path.basename(error_file)
        target_file = os.path.join(reports_dir, filename)
        
        try:
            # 如果目标文件已存在，先删除
            if os.path.exists(target_file):
                print(f"⚠️  目标文件已存在，将被覆盖: {filename}")
                os.remove(target_file)
            
            # 移动文件
            shutil.move(error_file, target_file)
            print(f"✅ 已移动: {filename}")
            print(f"   从: {error_file}")
            print(f"   到: {target_file}")
            print()
            moved_count += 1
            
        except Exception as e:
            print(f"❌ 移动失败: {filename}")
            print(f"   错误: {str(e)}")
            print()
    
    print(f"完成！共移动 {moved_count} 个文件")

if __name__ == "__main__":
    print("=" * 80)
    print("报告文件路径修复脚本")
    print("=" * 80)
    print()
    
    fix_report_paths()
    
    print()
    print("=" * 80)
    print("修复完成")
    print("=" * 80)
