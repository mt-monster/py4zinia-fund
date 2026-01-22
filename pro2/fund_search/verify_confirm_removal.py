#!/usr/bin/env python
# coding: utf-8

"""
验证确认导入功能移除完成情况
"""

import os
import re

def verify_confirm_removal():
    """验证确认导入功能是否已完全移除"""
    
    print("=" * 80)
    print("验证确认导入功能移除情况")
    print("=" * 80)
    
    my_holdings_path = 'web/templates/my_holdings.html'
    
    if not os.path.exists(my_holdings_path):
        print(f"❌ 文件不存在: {my_holdings_path}")
        return False
    
    with open(my_holdings_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = []
    
    # 检查1: 确认导入按钮是否已移除
    if '确认导入持仓' in content:
        checks.append(('❌', '确认导入按钮', '仍然存在'))
    else:
        checks.append(('✅', '确认导入按钮', '已移除'))
    
    # 检查2: 确认模态框HTML是否已移除
    if 'confirmModalOverlay' in content:
        checks.append(('❌', '确认模态框HTML', '仍然存在'))
    else:
        checks.append(('✅', '确认模态框HTML', '已移除'))
    
    # 检查3: openConfirmModal函数是否已移除
    if re.search(r'function\s+openConfirmModal\s*\(', content):
        checks.append(('❌', 'openConfirmModal函数', '仍然存在'))
    else:
        checks.append(('✅', 'openConfirmModal函数', '已移除'))
    
    # 检查4: closeConfirmModal函数是否已移除
    if re.search(r'function\s+closeConfirmModal\s*\(', content):
        checks.append(('❌', 'closeConfirmModal函数', '仍然存在'))
    else:
        checks.append(('✅', 'closeConfirmModal函数', '已移除'))
    
    # 检查5: showConfirmContent函数是否已移除
    if re.search(r'function\s+showConfirmContent\s*\(', content):
        checks.append(('❌', 'showConfirmContent函数', '仍然存在'))
    else:
        checks.append(('✅', 'showConfirmContent函数', '已移除'))
    
    # 检查6: confirmImport函数是否已移除
    if re.search(r'function\s+confirmImport\s*\(', content):
        checks.append(('❌', 'confirmImport函数', '仍然存在'))
    else:
        checks.append(('✅', 'confirmImport函数', '已移除'))
    
    # 检查7: confirmImportBtn事件监听器是否已移除
    if 'confirmImportBtn' in content:
        checks.append(('❌', 'confirmImportBtn引用', '仍然存在'))
    else:
        checks.append(('✅', 'confirmImportBtn引用', '已移除'))
    
    # 检查8: window.openConfirmModal赋值是否已移除
    if 'window.openConfirmModal' in content:
        checks.append(('❌', 'window.openConfirmModal', '仍然存在'))
    else:
        checks.append(('✅', 'window.openConfirmModal', '已移除'))
    
    # 检查9: window.closeConfirmModal赋值是否已移除
    if 'window.closeConfirmModal' in content:
        checks.append(('❌', 'window.closeConfirmModal', '仍然存在'))
    else:
        checks.append(('✅', 'window.closeConfirmModal', '已移除'))
    
    # 检查10: window.confirmImport赋值是否已移除
    if 'window.confirmImport' in content:
        checks.append(('❌', 'window.confirmImport', '仍然存在'))
    else:
        checks.append(('✅', 'window.confirmImport', '已移除'))
    
    # 检查11: 导出按钮是否保留
    if 'exportRecognitionResults' in content:
        checks.append(('✅', '导出功能', '已保留'))
    else:
        checks.append(('❌', '导出功能', '被误删'))
    
    # 检查12: /api/holdings/import/confirm API调用是否已移除
    if '/api/holdings/import/confirm' in content:
        checks.append(('❌', 'API调用', '仍然存在'))
    else:
        checks.append(('✅', 'API调用', '已移除'))
    
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
        print("\n🎉 所有检查通过！确认导入功能已完全移除。")
        return True
    else:
        print(f"\n⚠️  还有 {total - passed} 项需要处理。")
        return False

if __name__ == '__main__':
    verify_confirm_removal()
