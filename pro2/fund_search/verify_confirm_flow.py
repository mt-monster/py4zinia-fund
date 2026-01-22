#!/usr/bin/env python
# coding: utf-8

"""
验证用户确认流程实现情况
"""

import os
import re

def verify_confirm_flow():
    """验证用户确认流程是否已正确实现"""
    
    print("=" * 80)
    print("验证用户确认流程实现情况")
    print("=" * 80)
    
    my_holdings_path = 'web/templates/my_holdings.html'
    
    if not os.path.exists(my_holdings_path):
        print(f"❌ 文件不存在: {my_holdings_path}")
        return False
    
    with open(my_holdings_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = []
    
    # 检查1: recognizeScreenshot中是否移除了自动保存调用
    recognize_section = content[content.find('function recognizeScreenshot'):content.find('function recognizeScreenshot') + 1500]
    if 'autoSaveToDatabase(recognizedFunds)' not in recognize_section:
        checks.append(('✅', '移除自动保存', '已移除'))
    else:
        checks.append(('❌', '移除自动保存', '仍存在'))
    
    # 检查2: confirmAndSave函数是否存在
    if re.search(r'function\s+confirmAndSave\s*\(', content):
        checks.append(('✅', 'confirmAndSave函数', '已实现'))
    else:
        checks.append(('❌', 'confirmAndSave函数', '未找到'))
    
    # 检查3: 确认导入按钮是否存在
    if '确认导入' in content and 'onclick="confirmAndSave()"' in content:
        checks.append(('✅', '确认导入按钮', '已添加'))
    else:
        checks.append(('❌', '确认导入按钮', '未添加'))
    
    # 检查4: 导出按钮是否保留
    if '导出Excel' in content and 'exportRecognitionResults' in content:
        checks.append(('✅', '导出按钮', '已保留'))
    else:
        checks.append(('❌', '导出按钮', '被误删'))
    
    # 检查5: window.confirmAndSave赋值是否存在
    if 'window.confirmAndSave' in content:
        checks.append(('✅', 'window.confirmAndSave', '已添加'))
    else:
        checks.append(('❌', 'window.confirmAndSave', '未添加'))
    
    # 检查6: autoSaveToDatabase函数是否仍然存在
    if re.search(r'function\s+autoSaveToDatabase\s*\(', content):
        checks.append(('✅', 'autoSaveToDatabase函数', '已保留'))
    else:
        checks.append(('❌', 'autoSaveToDatabase函数', '被误删'))
    
    # 检查7: confirmAndSave是否调用autoSaveToDatabase
    if 'confirmAndSave' in content:
        confirm_section = content[content.find('function confirmAndSave'):content.find('function confirmAndSave') + 300]
        if 'autoSaveToDatabase' in confirm_section:
            checks.append(('✅', 'confirmAndSave调用保存', '已实现'))
        else:
            checks.append(('❌', 'confirmAndSave调用保存', '未实现'))
    else:
        checks.append(('❌', 'confirmAndSave调用保存', '函数不存在'))
    
    # 检查8: 保存成功后是否关闭模态框
    if 'closeScreenshotModal()' in content:
        auto_save_section = content[content.find('function autoSaveToDatabase'):content.find('function autoSaveToDatabase') + 2500]
        if 'closeScreenshotModal()' in auto_save_section:
            checks.append(('✅', '保存后关闭模态框', '已实现'))
        else:
            checks.append(('❌', '保存后关闭模态框', '未实现'))
    else:
        checks.append(('❌', '保存后关闭模态框', '未找到'))
    
    # 检查9: 保存成功后是否刷新列表
    if 'loadFunds()' in content:
        auto_save_section = content[content.find('function autoSaveToDatabase'):content.find('function autoSaveToDatabase') + 4000]
        if 'loadFunds()' in auto_save_section:
            checks.append(('✅', '保存后刷新列表', '已实现'))
        else:
            checks.append(('❌', '保存后刷新列表', '未实现'))
    else:
        checks.append(('❌', '保存后刷新列表', '未找到'))
    
    # 打印检查结果
    print("\n检查项目:")
    print("-" * 80)
    for status, item, result in checks:
        print(f"{status} {item:30s} - {result}")
    
    # 统计结果
    passed = sum(1 for check in checks if check[0] == '✅')
    total = len(checks)
    
    print("-" * 80)
    print(f"\n总计: {passed}/{total} 项检查通过")
    
    if passed == total:
        print("\n🎉 所有检查通过！用户确认流程已完整实现。")
        print("\n完整流程:")
        print("  1. 上传截图")
        print("  2. 点击'开始识别'")
        print("  3. 显示识别结果")
        print("  4. 用户查看结果")
        print("  5. 点击'确认导入'按钮 ⭐")
        print("  6. 保存到数据库")
        print("  7. 显示成功通知")
        print("  8. 关闭模态框")
        print("  9. 刷新持仓列表")
        return True
    else:
        print(f"\n⚠️  还有 {total - passed} 项需要处理。")
        return False

if __name__ == '__main__':
    verify_confirm_flow()
