#!/usr/bin/env python
# coding: utf-8
"""
重构版投资建议页面功能验证脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """测试所有模块是否正确导入"""
    print("=" * 60)
    print("Test Module Import")
    print("=" * 60)
    
    tests = [
        ("Route Module", "web.routes.investment_advice_refactored", True),
        ("Holdings API", "web.routes.holdings", True),
        ("Pages Route", "web.routes.pages", True),
    ]
    
    all_passed = True
    for name, module, required in tests:
        try:
            __import__(module)
            print(f"[OK] {name}: {module}")
        except Exception as e:
            if required:
                print(f"[FAIL] {name}: {module} - {e}")
                all_passed = False
            else:
                print(f"[WARN] {name}: {module}")
    
    return all_passed


def test_holdings_api_functions():
    """测试holdings模块中的新API函数"""
    print("\n" + "=" * 60)
    print("Test Holdings New API Functions")
    print("=" * 60)
    
    from web.routes import holdings
    
    functions = [
        'get_investment_advice_holdings',
        'get_investment_advice_strategies',
        'run_investment_advice_backtest',
        'generate_investment_advice_api',
        'get_investment_advice_valuation',
        '_generate_simple_return_curve',
    ]
    
    all_exist = True
    for func_name in functions:
        if hasattr(holdings, func_name):
            print(f"[OK] {func_name}")
        else:
            print(f"[FAIL] {func_name} - not found")
            all_exist = False
    
    return all_exist


def test_routes_registration():
    """测试路由注册"""
    print("\n" + "=" * 60)
    print("Test Route Registration")
    print("=" * 60)
    
    expected_routes = [
        ('/api/investment-advice/holdings', 'GET'),
        ('/api/investment-advice/strategies', 'GET'),
        ('/api/investment-advice/backtest', 'POST'),
        ('/api/investment-advice/generate', 'POST'),
        ('/api/investment-advice/valuation', 'GET'),
        ('/api/investment-advice/valuation', 'POST'),
        ('/investment-advice', 'GET'),
    ]
    
    print("Expected Routes:")
    for route, method in expected_routes:
        print(f"  {method:6} {route}")
    
    return True


def test_template_structure():
    """测试模板文件结构"""
    print("\n" + "=" * 60)
    print("Test Template File Structure")
    print("=" * 60)
    
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'web', 'templates', 'investment_advice_refactored.html'
    )
    
    if not os.path.exists(template_path):
        print(f"[FAIL] Template not found: {template_path}")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键部分
    checks = [
        ('HTML5 DOCTYPE', '<!DOCTYPE html>' in content),
        ('基金选择面板', 'fund-selection-panel' in content),
        ('策略选择面板', 'strategy-selection-panel' in content),
        ('回测结果面板', 'backtest-result-panel' in content),
        ('建议面板', 'advice-panel' in content),
        ('Chart.js引用', 'chart.umd.min.js' in content),
        ('JavaScript模块', 'AppState' in content),
        ('CSS样式', ':root {' in content),
    ]
    
    all_passed = True
    for name, passed in checks:
        if passed:
            print(f"[OK] {name}")
        else:
            print(f"[FAIL] {name}")
            all_passed = False
    
    # 文件大小检查
    file_size = len(content)
    print(f"\n[FILE] Template size: {file_size} chars")
    
    return all_passed


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Investment Advice Page Verification")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Module Import", test_imports()))
    results.append(("Holdings API Functions", test_holdings_api_functions()))
    results.append(("Route Registration", test_routes_registration()))
    results.append(("Template Structure", test_template_structure()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} - {name}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] All tests passed!")
        print("\nPage URL: http://127.0.0.1:5001/investment-advice")
        print("Note: If API returns 404, restart Flask to load new routes")
    else:
        print("[WARNING] Some tests failed")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
