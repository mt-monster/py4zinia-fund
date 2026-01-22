#!/usr/bin/env python
# coding: utf-8

"""
测试持仓信息识别功能
"""

import logging
from data_retrieval.smart_fund_parser import parse_fund_info_with_manual_fallback

# 设置日志级别为DEBUG以查看详细信息
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_holding_info_recognition():
    """测试持仓信息识别功能"""
    
    # 模拟用户提供的OCR识别文本（包含持仓金额信息）
    test_texts = [
        '12:45', '63', '基金持仓', '理财师', '我的持有 吕', '金额排序', 
        '全部(53)', '股票型(8)', '债券型(0)', '基金名称', '持仓收益/率', 
        '天弘标普500发起',  # 基金名称开头
        '681.30',           # 持仓金额
        '+21.11',           # 盈亏金额
        '(QDIIFOF)A',       # 基金名称结尾
        '+3.20%',           # 盈亏率
        '交易: 1笔赎回中合计7.10份', 
        '景顺长城全球半',   # 基金名称开头
        '664.00',           # 持仓金额
        '+83.08',           # 盈亏金额
        '导体芯片股票A(.',  # 基金名称结尾
        '-1.20',            # 另一个数字（可能是净值变化）
        '+15.08%',          # 盈亏率
        '交易:  3笔买入中合计30.00元', 
        '广发北证50成份指', # 基金名称开头
        '568.11',           # 持仓金额
        '+15.10',           # 盈亏金额
        '数A',              # 基金名称结尾
        '-10.34',           # 另一个数字
        '+2.83%',           # 盈亏率
        '交易: 1笔买入中合计20.00元', 
        '富国全球科技互联', # 基金名称开头
        '438.25',           # 持仓金额
        '+28.42',           # 盈亏金额
        ' 网股票(QDII)A',   # 基金名称结尾
        '+7.29%',           # 盈亏率
        '交易:  2笔买入中合计20.00元', 
        '易方达战略新兴产', # 基金名称开头
        '429.02',           # 持仓金额
        '+21.21',           # 盈亏金额
        '业股票A',          # 基金名称结尾
        '-9.68',            # 另一个数字
        '+5.33%',           # 盈亏率
        '交易: 1笔买入中合计10.00元', 
        '基金', '全球投资', '基金圈', '自选', '持仓'
    ]
    
    print(f"测试OCR文本 ({len(test_texts)} 项):")
    for i, text in enumerate(test_texts, 1):
        print(f"  {i:2d}. {text}")
    
    print("\n开始解析...")
    
    # 使用智能解析器解析
    result = parse_fund_info_with_manual_fallback(test_texts)
    
    print(f"\n解析结果:")
    print(f"成功识别: {result['success']}")
    print(f"识别基金数量: {result['funds_count']}")
    
    print(f"\n识别到的基金及持仓信息:")
    print("=" * 120)
    print(f"{'序号':<4} {'基金代码':<8} {'基金名称':<35} {'持仓金额':<10} {'盈亏金额':<10} {'盈亏率':<10} {'净值':<8} {'来源':<12}")
    print("-" * 120)
    
    for i, fund in enumerate(result['funds'], 1):
        name_display = fund['fund_name'][:30] + "..." if len(fund['fund_name']) > 30 else fund['fund_name']
        holding_amount = f"{fund.get('holding_amount', 'N/A')}"
        profit_amount = f"{fund.get('profit_amount', 'N/A')}"
        profit_rate = f"{fund.get('profit_rate', 'N/A')}%" if fund.get('profit_rate') is not None else "N/A"
        nav_value = f"{fund.get('nav_value', 'N/A')}"
        source = fund.get('source', 'N/A')
        
        print(f"{i:<4} {fund['fund_code']:<8} {name_display:<35} {holding_amount:<10} {profit_amount:<10} {profit_rate:<10} {nav_value:<8} {source:<12}")
    
    # 显示详细的持仓信息
    print(f"\n详细持仓信息:")
    print("=" * 120)
    
    for i, fund in enumerate(result['funds'], 1):
        print(f"\n{i}. {fund['fund_code']} - {fund['fund_name']}")
        print(f"   识别来源: {fund.get('source', 'N/A')}")
        print(f"   置信度: {fund.get('confidence', 0):.1%}")
        print(f"   原始文本: {fund.get('original_text', 'N/A')}")
        
        # 持仓相关信息
        if fund.get('holding_amount') is not None:
            print(f"   💰 持仓金额: {fund['holding_amount']:.2f} 元")
        else:
            print(f"   💰 持仓金额: 未识别")
            
        if fund.get('profit_amount') is not None:
            profit_sign = "📈" if fund['profit_amount'] >= 0 else "📉"
            print(f"   {profit_sign} 盈亏金额: {fund['profit_amount']:+.2f} 元")
        else:
            print(f"   📊 盈亏金额: 未识别")
            
        if fund.get('profit_rate') is not None:
            rate_sign = "🟢" if fund['profit_rate'] >= 0 else "🔴"
            print(f"   {rate_sign} 盈亏率: {fund['profit_rate']:+.2f}%")
        else:
            print(f"   📊 盈亏率: 未识别")
            
        if fund.get('nav_value') is not None:
            print(f"   📊 净值: {fund['nav_value']:.4f}")
        else:
            print(f"   📊 净值: 未识别")
        
        # 计算市值（如果有持仓金额和盈亏金额）
        if fund.get('holding_amount') is not None and fund.get('profit_amount') is not None:
            current_value = fund['holding_amount'] + fund['profit_amount']
            print(f"   💎 当前市值: {current_value:.2f} 元")
        
        print(f"   " + "-" * 60)
    
    # 统计持仓信息识别情况
    total_funds = len(result['funds'])
    funds_with_holding = sum(1 for f in result['funds'] if f.get('holding_amount') is not None)
    funds_with_profit = sum(1 for f in result['funds'] if f.get('profit_amount') is not None)
    funds_with_rate = sum(1 for f in result['funds'] if f.get('profit_rate') is not None)
    
    # 计算总持仓价值
    total_holding_amount = sum(f.get('holding_amount', 0) for f in result['funds'] if f.get('holding_amount') is not None)
    total_profit_amount = sum(f.get('profit_amount', 0) for f in result['funds'] if f.get('profit_amount') is not None)
    total_current_value = total_holding_amount + total_profit_amount
    total_profit_rate = (total_profit_amount / total_holding_amount * 100) if total_holding_amount > 0 else 0
    
    print(f"\n持仓信息识别统计:")
    print("=" * 60)
    print(f"总基金数量: {total_funds}")
    print(f"识别到持仓金额: {funds_with_holding}/{total_funds} ({funds_with_holding/total_funds*100:.1f}%)")
    print(f"识别到盈亏金额: {funds_with_profit}/{total_funds} ({funds_with_profit/total_funds*100:.1f}%)")
    print(f"识别到盈亏率: {funds_with_rate}/{total_funds} ({funds_with_rate/total_funds*100:.1f}%)")
    
    print(f"\n📊 投资组合汇总:")
    print("=" * 60)
    print(f"💰 总持仓成本: {total_holding_amount:,.2f} 元")
    print(f"📈 总盈亏金额: {total_profit_amount:+,.2f} 元")
    print(f"💎 总当前市值: {total_current_value:,.2f} 元")
    print(f"📊 总盈亏率: {total_profit_rate:+.2f}%")
    
    # 显示收益最好和最差的基金
    if result['funds']:
        best_fund = max(result['funds'], key=lambda x: x.get('profit_rate', -999))
        worst_fund = min(result['funds'], key=lambda x: x.get('profit_rate', 999))
        
        print(f"\n🏆 表现最佳: {best_fund['fund_name'][:25]}... ({best_fund.get('profit_rate', 0):+.2f}%)")
        print(f"📉 表现最差: {worst_fund['fund_name'][:25]}... ({worst_fund.get('profit_rate', 0):+.2f}%)")
    
    return result

if __name__ == "__main__":
    test_holding_info_recognition()