#!/usr/bin/env python
# coding: utf-8

"""
验证主持仓页面截图导入功能整合
"""

import os
import sys

def verify_integration():
    """验证整合完成度"""
    
    print("=" * 60)
    print("主持仓页面截图导入功能整合验证")
    print("=" * 60)
    print()
    
    # 检查文件是否存在
    files_to_check = {
        'my_holdings.html': 'pro2/fund_search/web/templates/my_holdings.html',
        'app.py': 'pro2/fund_search/web/app.py',
        'smart_fund_parser.py': 'pro2/fund_search/data_retrieval/smart_fund_parser.py'
    }
    
    print("📋 1. 文件存在性检查")
    print("-" * 60)
    all_files_exist = True
    for name, path in files_to_check.items():
        exists = os.path.exists(path)
        status = "✅" if exists else "❌"
        print(f"{status} {name}: {path}")
        if not exists:
            all_files_exist = False
    print()
    
    if not all_files_exist:
        print("❌ 部分文件不存在，请检查文件路径")
        return False
    
    # 检查 my_holdings.html 中的关键函数
    print("📋 2. my_holdings.html 功能检查")
    print("-" * 60)
    
    with open(files_to_check['my_holdings.html'], 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_functions = [
        'showRecognitionResult',
        'recognizeScreenshot',
        'exportRecognitionResults',
        'openConfirmModal',
        'confirmImport'
    ]
    
    required_elements = [
        'portfolio_summary',  # 投资组合汇总
        'best_fund',  # 表现最佳基金
        'worst_fund',  # 表现最差基金
        'holding_amount',  # 持仓金额
        'profit_amount',  # 盈亏金额
        'profit_rate',  # 盈亏率
        'current_value',  # 当前市值
        'confidence',  # 置信度
        'source',  # 识别来源
        'original_text'  # 原始文本
    ]
    
    all_functions_present = True
    for func in required_functions:
        present = f'function {func}' in content or f'const {func}' in content
        status = "✅" if present else "❌"
        print(f"{status} 函数: {func}")
        if not present:
            all_functions_present = False
    
    print()
    print("📋 3. 数据字段检查")
    print("-" * 60)
    
    all_elements_present = True
    for element in required_elements:
        present = element in content
        status = "✅" if present else "❌"
        print(f"{status} 字段: {element}")
        if not present:
            all_elements_present = False
    
    print()
    
    # 检查 app.py 中的 API 端点
    print("📋 4. API 端点检查")
    print("-" * 60)
    
    with open(files_to_check['app.py'], 'r', encoding='utf-8') as f:
        app_content = f.read()
    
    api_endpoints = [
        '/api/holdings/import/screenshot',
        '/api/holdings/import/confirm'
    ]
    
    all_endpoints_present = True
    for endpoint in api_endpoints:
        present = endpoint in app_content
        status = "✅" if present else "❌"
        print(f"{status} API: {endpoint}")
        if not present:
            all_endpoints_present = False
    
    print()
    
    # 检查 API 返回的数据结构
    print("📋 5. API 响应结构检查")
    print("-" * 60)
    
    response_fields = [
        'portfolio_summary',
        'total_funds',
        'total_holding_amount',
        'total_profit_amount',
        'total_current_value',
        'total_profit_rate',
        'best_fund',
        'worst_fund'
    ]
    
    all_response_fields_present = True
    for field in response_fields:
        present = field in app_content
        status = "✅" if present else "❌"
        print(f"{status} 响应字段: {field}")
        if not present:
            all_response_fields_present = False
    
    print()
    
    # 检查 smart_fund_parser.py 中的数据提取
    print("📋 6. 数据解析器检查")
    print("-" * 60)
    
    with open(files_to_check['smart_fund_parser.py'], 'r', encoding='utf-8') as f:
        parser_content = f.read()
    
    parser_fields = [
        'holding_amount',
        'profit_amount',
        'profit_rate',
        'confidence',
        'source',
        'original_text'
    ]
    
    all_parser_fields_present = True
    for field in parser_fields:
        present = field in parser_content
        status = "✅" if present else "❌"
        print(f"{status} 解析字段: {field}")
        if not present:
            all_parser_fields_present = False
    
    print()
    
    # 总结
    print("=" * 60)
    print("📊 整合验证总结")
    print("=" * 60)
    
    checks = {
        '文件存在性': all_files_exist,
        'my_holdings.html 功能': all_functions_present,
        '数据字段': all_elements_present,
        'API 端点': all_endpoints_present,
        'API 响应结构': all_response_fields_present,
        '数据解析器': all_parser_fields_present
    }
    
    all_passed = all(checks.values())
    
    for check_name, passed in checks.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {check_name}")
    
    print()
    
    if all_passed:
        print("✅ 整合验证完成：所有检查项通过")
        print()
        print("🎉 主持仓页面截图导入功能已成功整合！")
        print()
        print("📝 使用说明：")
        print("1. 启动服务: python pro2/fund_search/web/app.py")
        print("2. 访问页面: http://127.0.0.1:5000/my-holdings")
        print("3. 点击工具栏中的 '截图导入' 按钮")
        print("4. 上传基金持仓截图")
        print("5. 查看增强的识别结果（投资组合汇总 + 详细列表）")
        print("6. 确认导入或导出Excel")
        print()
        print("📊 功能特性：")
        print("- 投资组合汇总（5项关键指标）")
        print("- 表现最佳/最差基金对比")
        print("- 9列详细基金列表")
        print("- 导出Excel功能")
        print("- 完整的导入确认流程")
        return True
    else:
        print("❌ 整合验证失败：部分检查项未通过")
        print()
        print("请检查以下内容：")
        for check_name, passed in checks.items():
            if not passed:
                print(f"  - {check_name}")
        return False

if __name__ == '__main__':
    success = verify_integration()
    sys.exit(0 if success else 1)
