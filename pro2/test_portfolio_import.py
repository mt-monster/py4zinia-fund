#!/usr/bin/env python
# coding: utf-8

"""
测试持仓导入功能
"""

import sys
import os
sys.path.append('fund_search')

from fund_search.data_retrieval.portfolio_importer import import_portfolio_from_screenshot, PortfolioImporter
from fund_search.data_retrieval.akshare_fund_lookup import AkshareFundLookup

def test_akshare_lookup():
    """测试akshare基金查找功能"""
    print("=== 测试akshare基金查找 ===")
    
    lookup = AkshareFundLookup()
    
    test_names = [
        "天弘标普500发起",
        "景顺长城全球半导体芯片股票",
        "广发北证50成份指数",
    ]
    
    for name in test_names:
        print(f"\n查找基金: {name}")
        try:
            result = lookup.find_best_match(name)
            if result:
                print(f"  找到: {result['fund_code']} - {result['fund_name']}")
                print(f"  相似度: {result['similarity']:.2f}")
                print(f"  基金公司: {result.get('management_company', 'N/A')}")
            else:
                print("  未找到匹配的基金")
        except Exception as e:
            print(f"  查找失败: {e}")

def test_portfolio_extraction():
    """测试持仓信息提取"""
    print("\n=== 测试持仓信息提取 ===")
    
    # 模拟从你的截图中识别到的文本
    ocr_texts = [
        "基金持仓",
        "我的持有",
        "全部(53)",
        "天弘标普500发起(QDII-FOF)A",
        "681.30",
        "+21.11",
        "+3.20%",
        "交易：1笔买入中合计710份",
        "景顺长城全球半导体芯片股票A(...)",
        "664.00",
        "+83.08",
        "+15.08%",
        "交易：3笔买入中合计30.00元",
        "广发北证50成份指数A",
        "568.11",
        "+15.10",
        "+2.83%",
        "交易：1笔买入中合计20.00元",
        "富国全球科技互联网股票(QDII)A",
        "438.25",
        "+28.42",
        "+7.29%",
        "交易：2笔买入中合计20.00元",
        "易方达战略新兴产业股票A",
        "429.02",
        "+21.21",
        "+5.33%",
        "交易：1笔买入中合计10.00元"
    ]
    
    result = import_portfolio_from_screenshot(ocr_texts, user_id="test_user")
    
    print(f"导入结果: {result['success']}")
    print(f"消息: {result['message']}")
    print(f"持仓数量: {result['holdings_count']}")
    
    if result['holdings']:
        print("\n提取的持仓信息:")
        for holding in result['holdings']:
            print(f"  基金: {holding.get('fund_name', 'N/A')}")
            print(f"  代码: {holding.get('fund_code', 'N/A')}")
            print(f"  净值: {holding.get('nav_value', 'N/A')}")
            print(f"  涨跌金额: {holding.get('change_amount', 'N/A')}")
            print(f"  涨跌百分比: {holding.get('change_percent', 'N/A')}%")
            print(f"  估算持仓金额: {holding.get('position_value', 'N/A')}")
            print("  ---")

def test_portfolio_database():
    """测试持仓数据库操作"""
    print("\n=== 测试持仓数据库操作 ===")
    
    importer = PortfolioImporter()
    
    # 获取用户持仓
    portfolio = importer.get_user_portfolio("test_user")
    
    if portfolio:
        print(f"用户持仓数量: {len(portfolio)}")
        print("\n持仓列表:")
        for holding in portfolio:
            print(f"  {holding['fund_code']} - {holding['fund_name']}")
            print(f"    净值: {holding['nav_value']}")
            print(f"    涨跌: {holding['change_amount']} ({holding['change_percent']}%)")
            print(f"    更新时间: {holding['last_updated']}")
            print("    ---")
    else:
        print("用户暂无持仓")

def main():
    """主测试函数"""
    print("基金持仓导入系统测试")
    print("=" * 50)
    
    try:
        # 测试akshare查找（可能需要网络连接）
        test_akshare_lookup()
        
        # 测试持仓提取和导入
        test_portfolio_extraction()
        
        # 测试数据库操作
        test_portfolio_database()
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()