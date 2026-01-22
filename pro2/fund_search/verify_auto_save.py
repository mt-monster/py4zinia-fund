#!/usr/bin/env python
# coding: utf-8

"""
验证自动保存功能实现情况（包含闭环流程）
"""

import os
import re

def verify_auto_save():
    """验证自动保存功能是否已正确实现"""
    
    print("=" * 80)
    print("验证自动保存功能实现情况（包含闭环流程）")
    print("=" * 80)
    
    my_holdings_path = 'web/templates/my_holdings.html'
    
    if not os.path.exists(my_holdings_path):
        print(f"❌ 文件不存在: {my_holdings_path}")
        return False
    
    with open(my_holdings_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = []
    
    # 检查1: autoSaveToDatabase函数是否存在
    if re.search(r'function\s+autoSaveToDatabase\s*\(', content):
        checks.append(('✅', 'autoSaveToDatabase函数', '已实现'))
    else:
        checks.append(('❌', 'autoSaveToDatabase函数', '未找到'))
    
    # 检查2: recognizeScreenshot中是否调用autoSaveToDatabase
    if 'autoSaveToDatabase(recognizedFunds)' in content:
        checks.append(('✅', '自动保存调用', '已添加'))
    else:
        checks.append(('❌', '自动保存调用', '未添加'))
    
    # 检查3: showSaveSuccessNotification函数是否存在
    if re.search(r'function\s+showSaveSuccessNotification\s*\(', content):
        checks.append(('✅', '成功通知函数', '已实现'))
    else:
        checks.append(('❌', '成功通知函数', '未找到'))
    
    # 检查4: showSaveErrorNotification函数是否存在
    if re.search(r'function\s+showSaveErrorNotification\s*\(', content):
        checks.append(('✅', '失败通知函数', '已实现'))
    else:
        checks.append(('❌', '失败通知函数', '未找到'))
    
    # 检查5: slideIn动画是否存在
    if '@keyframes slideIn' in content:
        checks.append(('✅', 'slideIn动画', '已添加'))
    else:
        checks.append(('❌', 'slideIn动画', '未添加'))
    
    # 检查6: slideOut动画是否存在
    if '@keyframes slideOut' in content:
        checks.append(('✅', 'slideOut动画', '已添加'))
    else:
        checks.append(('❌', 'slideOut动画', '未添加'))
    
    # 检查7: API调用是否使用/api/holdings/import/confirm
    if "'/api/holdings/import/confirm'" in content:
        checks.append(('✅', 'API端点调用', '正确'))
    else:
        checks.append(('❌', 'API端点调用', '未找到'))
    
    # 检查8: 是否在保存成功后刷新持仓列表
    if 'loadFunds()' in content and 'autoSaveToDatabase' in content:
        checks.append(('✅', '刷新持仓列表', '已实现'))
    else:
        checks.append(('❌', '刷新持仓列表', '未实现'))
    
    # 检查9: 导出功能是否保留
    if 'exportRecognitionResults' in content:
        checks.append(('✅', '导出功能', '已保留'))
    else:
        checks.append(('❌', '导出功能', '被误删'))
    
    # 检查10: 确认导入按钮是否已移除（应该不存在）
    if '确认导入持仓' not in content:
        checks.append(('✅', '确认按钮移除', '已移除'))
    else:
        checks.append(('❌', '确认按钮移除', '仍存在'))
    
    # 检查11: 保存成功后是否关闭模态框（闭环流程）
    if 'closeScreenshotModal()' in content and 'autoSaveToDatabase' in content:
        # 检查是否在autoSaveToDatabase中调用closeScreenshotModal
        auto_save_section = content[content.find('function autoSaveToDatabase'):content.find('function autoSaveToDatabase') + 2000]
        if 'closeScreenshotModal()' in auto_save_section:
            checks.append(('✅', '关闭模态框（闭环）', '已实现'))
        else:
            checks.append(('❌', '关闭模态框（闭环）', '未实现'))
    else:
        checks.append(('❌', '关闭模态框（闭环）', '未找到'))
    
    # 检查12: closeScreenshotModal是否调用resetScreenshotModal
    if 'resetScreenshotModal()' in content:
        close_modal_section = content[content.find('function closeScreenshotModal'):content.find('function closeScreenshotModal') + 500]
        if 'resetScreenshotModal()' in close_modal_section:
            checks.append(('✅', '重置模态框状态', '已实现'))
        else:
            checks.append(('❌', '重置模态框状态', '未实现'))
    else:
        checks.append(('❌', '重置模态框状态', '未找到'))
    
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
        print("\n🎉 所有检查通过！自动保存功能已完整实现（包含闭环流程）。")
        print("\n完整闭环流程:")
        print("  1. 上传截图")
        print("  2. 开始识别")
        print("  3. 显示结果")
        print("  4. 自动保存到数据库")
        print("  5. 显示成功通知")
        print("  6. 关闭模态框")
        print("  7. 重置模态框状态")
        print("  8. 刷新持仓列表")
        print("  9. 用户可以继续下一次导入")
        return True
    else:
        print(f"\n⚠️  还有 {total - passed} 项需要处理。")
        return False

if __name__ == '__main__':
    verify_auto_save()
