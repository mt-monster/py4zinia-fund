#!/usr/bin/env python
# coding: utf-8

"""
重命名报告文件脚本
去掉文件名中的 "reports" 前缀
"""

import os
import glob

def rename_report_files():
    """重命名报告文件，去掉 reports 前缀"""
    
    # 获取reports目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pro2_dir = os.path.dirname(os.path.dirname(script_dir))
    reports_dir = os.path.join(pro2_dir, 'reports')
    
    print(f"reports目录: {reports_dir}")
    print()
    
    # 查找所有带 "reports" 前缀的文件
    files_to_rename = []
    for file in glob.glob(os.path.join(reports_dir, 'reports*.png')):
        if os.path.isfile(file):
            files_to_rename.append(file)
    
    if not files_to_rename:
        print("✅ 没有发现需要重命名的文件")
        return
    
    print(f"发现 {len(files_to_rename)} 个需要重命名的文件:")
    print()
    
    # 重命名文件
    renamed_count = 0
    for old_file in files_to_rename:
        old_filename = os.path.basename(old_file)
        # 去掉 "reports" 前缀
        new_filename = old_filename.replace('reports', '', 1)
        new_file = os.path.join(reports_dir, new_filename)
        
        try:
            # 如果目标文件已存在，先删除
            if os.path.exists(new_file):
                print(f"⚠️  目标文件已存在，将被覆盖: {new_filename}")
                os.remove(new_file)
            
            # 重命名文件
            os.rename(old_file, new_file)
            print(f"✅ 已重命名:")
            print(f"   从: {old_filename}")
            print(f"   到: {new_filename}")
            print()
            renamed_count += 1
            
        except Exception as e:
            print(f"❌ 重命名失败: {old_filename}")
            print(f"   错误: {str(e)}")
            print()
    
    print(f"完成！共重命名 {renamed_count} 个文件")

if __name__ == "__main__":
    print("=" * 80)
    print("报告文件重命名脚本")
    print("=" * 80)
    print()
    
    rename_report_files()
    
    print()
    print("=" * 80)
    print("重命名完成")
    print("=" * 80)
