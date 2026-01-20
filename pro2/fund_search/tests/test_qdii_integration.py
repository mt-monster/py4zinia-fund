#!/usr/bin/env python
# coding: utf-8

"""
QDII基金系统集成测试
验证QDII基金使用AKShare接口而不是新浪接口
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data_retrieval.enhanced_fund_data import EnhancedFundData


def test_qdii_integration():
    """测试QDII基金系统集成"""
    
    print("=" * 80)
    print("QDII基金系统集成测试")
    print("=" * 80)
    
    # 测试QDII基金列表
    qdii_funds = [
        ('006105', '宏利印度股票(QDII)A'),
        ('006373', '国富全球科技互联混合(QDII)人民币A'),
        ('100055', '富国全球科技互联网股票(QDII)A'),
    ]
    
    fund_data_manager = EnhancedFundData()
    
    for fund_code, fund_name in qdii_funds:
        print(f"\n{'='*80}")
        print(f"测试基金: {fund_name} ({fund_code})")
        print(f"{'='*80}")
        
        # 1. 验证是否识别为QDII基金
        is_qdii = fund_data_manager.is_qdii_fund(fund_code)
        print(f"\n1. QDII识别: {'✅ 是QDII基金' if is_qdii else '❌ 不是QDII基金'}")
        
        if not is_qdii:
            print(f"   ⚠️  基金 {fund_code} 未被识别为QDII基金")
            continue
        
        # 2. 获取实时数据
        try:
            print(f"\n2. 获取实时数据...")
            realtime_data = fund_data_manager.get_realtime_data(fund_code)
            
            print(f"   ✅ 数据获取成功")
            print(f"   数据来源: {realtime_data.get('data_source', 'unknown')}")
            print(f"   净值日期: {realtime_data.get('nav_date', 'N/A')}")
            print(f"   当日净值: {realtime_data.get('current_nav', 0):.4f} 元")
            print(f"   昨日净值: {realtime_data.get('previous_nav', 0):.4f} 元")
            print(f"   当日盈亏: {realtime_data.get('daily_return', 0):.2f}%")
            print(f"   昨日盈亏: {realtime_data.get('yesterday_return', 0):.2f}%")
            
            # 验证数据来源
            if realtime_data.get('data_source') == 'akshare_qdii':
                print(f"\n   ✅ 正确使用AKShare接口（不使用新浪接口）")
            else:
                print(f"\n   ❌ 错误：使用了 {realtime_data.get('data_source')} 接口")
            
        except Exception as e:
            print(f"   ❌ 数据获取失败: {str(e)}")
    
    # 测试普通基金（对比）
    print(f"\n{'='*80}")
    print(f"对比测试：普通基金 (001270 - 英大灵活配置A)")
    print(f"{'='*80}")
    
    normal_fund_code = '001270'
    is_qdii = fund_data_manager.is_qdii_fund(normal_fund_code)
    print(f"\n1. QDII识别: {'✅ 是QDII基金' if is_qdii else '✅ 不是QDII基金（正确）'}")
    
    try:
        print(f"\n2. 获取实时数据...")
        realtime_data = fund_data_manager.get_realtime_data(normal_fund_code)
        
        print(f"   ✅ 数据获取成功")
        print(f"   数据来源: {realtime_data.get('data_source', 'unknown')}")
        
        # 验证数据来源
        if realtime_data.get('data_source') == 'sina_realtime':
            print(f"\n   ✅ 正确使用新浪实时接口")
        else:
            print(f"\n   ⚠️  使用了 {realtime_data.get('data_source')} 接口")
    except Exception as e:
        print(f"   ❌ 数据获取失败: {str(e)}")
    
    print(f"\n{'='*80}")
    print("✅ 集成测试完成")
    print(f"{'='*80}")


if __name__ == "__main__":
    test_qdii_integration()
