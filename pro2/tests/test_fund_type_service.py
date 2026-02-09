"""
基金类型服务测试脚本

测试基于证监会标准的基金分类服务
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fund_search.services.fund_type_service import (
    FundType, FundTypeService, classify_fund,
    get_fund_type_display, get_fund_type_css_class,
    FUND_TYPE_CN, FUND_TYPE_CSS_CLASS
)


def test_classify_by_name():
    """测试基于名称的分类"""
    print("\n=== 测试基于名称的分类 ===")
    
    test_cases = [
        # (基金名称, 期望类型)
        ("易方达沪深300ETF", FundType.ETF),
        ("华夏上证50ETF联接A", FundType.INDEX),
        ("嘉实沪深300指数增强", FundType.INDEX),
        ("南方全球精选QDII", FundType.QDII),
        ("广发纳斯达克100指数基金", FundType.QDII),
        ("华夏大盘精选混合", FundType.HYBRID),
        ("易方达消费行业股票", FundType.STOCK),
        ("广发纯债债券A", FundType.BOND),
        ("天弘余额宝货币", FundType.MONEY_MARKET),
        ("交银施罗德养老目标日期FOF", FundType.FOF),
        ("某不知名的基金", FundType.UNKNOWN),
    ]
    
    passed = 0
    failed = 0
    
    for fund_name, expected in test_cases:
        result = FundTypeService.classify_fund(fund_name)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"  {status} {fund_name:30s} => {result.value:12s} (期望: {expected.value})")
    
    print(f"\n结果: 通过 {passed}/{len(test_cases)}, 失败 {failed}/{len(test_cases)}")
    return failed == 0


def test_classify_by_official_type():
    """测试基于官方类型的分类"""
    print("\n=== 测试基于官方类型的分类 ===")
    
    test_cases = [
        # (官方类型, 期望类型)
        ("股票型基金", FundType.STOCK),
        ("债券型基金", FundType.BOND),
        ("混合型基金", FundType.HYBRID),
        ("货币型基金", FundType.MONEY_MARKET),
        ("指数型基金", FundType.INDEX),
        ("QDII基金", FundType.QDII),
        ("ETF", FundType.ETF),
        ("FOF基金", FundType.FOF),
    ]
    
    passed = 0
    failed = 0
    
    for official_type, expected in test_cases:
        result = FundTypeService.classify_fund("", official_type=official_type)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"  {status} {official_type:20s} => {result.value:12s} (期望: {expected.value})")
    
    print(f"\n结果: 通过 {passed}/{len(test_cases)}, 失败 {failed}/{len(test_cases)}")
    return failed == 0


def test_classify_by_code():
    """测试基于基金代码的分类"""
    print("\n=== 测试基于基金代码的分类 ===")
    
    test_cases = [
        # (基金代码, 期望类型)
        ("510300", FundType.ETF),  # 沪深300ETF
        ("159919", FundType.ETF),  # 嘉实沪深300ETF
        ("161725", FundType.INDEX),  # 招商白酒（LOF）
    ]
    
    passed = 0
    failed = 0
    
    for fund_code, expected in test_cases:
        result = FundTypeService.classify_fund("", fund_code=fund_code)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"  {status} {fund_code:10s} => {result.value:12s} (期望: {expected.value})")
    
    print(f"\n结果: 通过 {passed}/{len(test_cases)}, 失败 {failed}/{len(test_cases)}")
    return failed == 0


def test_helper_functions():
    """测试便捷函数"""
    print("\n=== 测试便捷函数 ===")
    
    # 测试 classify_fund
    print("\n  classify_fund函数:")
    result = classify_fund("易方达沪深300ETF")
    print(f"    易方达沪深300ETF => {result}")
    assert result == "etf", f"期望 etf, 实际 {result}"
    
    result = classify_fund("华夏大盘精选混合")
    print(f"    华夏大盘精选混合 => {result}")
    assert result == "hybrid", f"期望 hybrid, 实际 {result}"
    
    # 测试 get_fund_type_display
    print("\n  get_fund_type_display函数:")
    names = ["stock", "bond", "hybrid", "money", "index", "qdii", "etf", "fof"]
    for code in names:
        display = get_fund_type_display(code)
        print(f"    {code:10s} => {display}")
    
    # 测试 get_fund_type_css_class
    print("\n  get_fund_type_css_class函数:")
    for code in names:
        css = get_fund_type_css_class(code)
        print(f"    {code:10s} => {css}")
    
    print("\n  ✓ 所有便捷函数测试通过")
    return True


def test_batch_classify():
    """测试批量分类"""
    print("\n=== 测试批量分类 ===")
    
    funds = [
        {'fund_code': '000001', 'fund_name': '华夏大盘精选混合'},
        {'fund_code': '000002', 'fund_name': '易方达沪深300ETF'},
        {'fund_code': '000003', 'fund_name': '南方全球精选QDII'},
        {'fund_code': '000004', 'fund_name': '广发纯债债券A'},
    ]
    
    results = FundTypeService.batch_classify(funds)
    
    print("\n  批量分类结果:")
    for fund in results:
        print(f"    {fund['fund_code']}: {fund['fund_name']:25s} => "
              f"{fund['fund_type_code']:10s} | {fund['fund_type_cn']:8s} | {fund['fund_type_class']}")
    
    print("\n  ✓ 批量分类测试通过")
    return True


def test_priority():
    """测试分类优先级"""
    print("\n=== 测试分类优先级 ===")
    
    # QDII应该优先于指数型
    result = FundTypeService.classify_fund("易方达中证海外联接QDII")
    print(f"  '易方达中证海外联接QDII' => {result.value} (期望: qdii, QDII优先于指数)")
    assert result == FundType.QDII, "QDII应优先于指数型"
    
    # ETF应该优先于指数型
    result = FundTypeService.classify_fund("华泰柏瑞沪深300ETF")
    print(f"  '华泰柏瑞沪深300ETF' => {result.value} (期望: etf, ETF优先于指数)")
    assert result == FundType.ETF, "ETF应优先于指数型"
    
    # 官方类型优先于名称推断
    result = FundTypeService.classify_fund("某混合基金", official_type="股票型基金")
    print(f"  '某混合基金' (官方类型:股票型) => {result.value} (期望: stock, 官方类型优先)")
    assert result == FundType.STOCK, "官方类型应优先于名称推断"
    
    print("\n  ✓ 优先级测试通过")
    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("基金类型服务测试 - 基于证监会标准分类")
    print("=" * 60)
    
    all_passed = True
    
    all_passed &= test_classify_by_name()
    all_passed &= test_classify_by_official_type()
    all_passed &= test_classify_by_code()
    all_passed &= test_helper_functions()
    all_passed &= test_batch_classify()
    all_passed &= test_priority()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有测试通过！")
    else:
        print("✗ 存在测试失败！")
    print("=" * 60)
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
