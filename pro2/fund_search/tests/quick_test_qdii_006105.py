#!/usr/bin/env python
# coding: utf-8

"""
QDII基金快速测试脚本 - 国富全球科技互联混合(QDII)人民币 (006105)

快速验证QDII基金数据获取的核心功能
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import akshare as ak
import pandas as pd


def quick_test_qdii_fund():
    """快速测试QDII基金数据获取"""
    
    fund_code = "006105"
    fund_name = "国富全球科技互联混合(QDII)人民币"
    
    print("=" * 80)
    print(f"快速测试：{fund_name} ({fund_code})")
    print("=" * 80)
    
    # 步骤1：从排名接口获取数据
    print("\n【步骤1：排名接口获取数据】")
    try:
        all_funds_rank_df = ak.fund_open_fund_rank_em(symbol="全部")
        fund_006105_rank = all_funds_rank_df[all_funds_rank_df['基金代码'] == fund_code]
        
        if not fund_006105_rank.empty:
            print("✓ 成功从排名接口获取数据")
            print(f"\n关键数据：")
            print(f"  基金代码: {fund_006105_rank.iloc[0]['基金代码']}")
            print(f"  基金简称: {fund_006105_rank.iloc[0]['基金简称']}")
            print(f"  日期: {fund_006105_rank.iloc[0]['日期']}")
            print(f"  单位净值: {fund_006105_rank.iloc[0]['单位净值']} 元")
            print(f"  日增长率: {fund_006105_rank.iloc[0]['日增长率']}%")
            print(f"  近1月: {fund_006105_rank.iloc[0]['近1月']}%")
            print(f"  近3月: {fund_006105_rank.iloc[0]['近3月']}%")
            print(f"  近6月: {fund_006105_rank.iloc[0]['近6月']}%")
            print(f"  近1年: {fund_006105_rank.iloc[0]['近1年']}%")
            print(f"  今年来: {fund_006105_rank.iloc[0]['今年来']}%")
            
            rank_data = fund_006105_rank.iloc[0]
        else:
            print("✗ 未找到基金数据")
            return False
    except Exception as e:
        print(f"✗ 获取排名数据失败: {e}")
        return False
    
    # 步骤2：从历史净值接口获取数据
    print("\n" + "-" * 80)
    print("【步骤2：历史净值接口获取数据】")
    try:
        fund_nav = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
        
        if not fund_nav.empty:
            fund_nav = fund_nav.sort_values('净值日期', ascending=True)
            latest_nav = fund_nav.iloc[-1]
            
            print(f"✓ 成功获取历史净值数据（共 {len(fund_nav)} 条记录）")
            print(f"\n最新净值数据：")
            print(f"  日期: {latest_nav['净值日期']}")
            print(f"  单位净值: {latest_nav['单位净值']} 元")
            print(f"  日增长率: {latest_nav['日增长率']}%")
            
            # 显示最近5天走势
            print(f"\n最近5天走势：")
            recent_5 = fund_nav.tail(5)
            for _, row in recent_5.iterrows():
                print(f"  {row['净值日期']}: {row['单位净值']}元 ({row['日增长率']:+.2f}%)")
        else:
            print("✗ 未获取到历史净值数据")
            return False
    except Exception as e:
        print(f"✗ 获取历史净值失败: {e}")
        return False
    
    # 步骤3：数据一致性验证
    print("\n" + "-" * 80)
    print("【步骤3：数据一致性验证】")
    
    rank_date = str(rank_data['日期'])
    rank_nav = float(rank_data['单位净值'])
    rank_growth = float(rank_data['日增长率'])
    
    nav_date = str(latest_nav['净值日期'])
    nav_value = float(latest_nav['单位净值'])
    nav_growth = float(latest_nav['日增长率'])
    
    print(f"排名接口: {rank_date} | {rank_nav}元 | {rank_growth:+.2f}%")
    print(f"历史接口: {nav_date} | {nav_value}元 | {nav_growth:+.2f}%")
    
    # 验证一致性
    date_match = rank_date == nav_date
    nav_match = abs(rank_nav - nav_value) < 0.0001
    growth_match = abs(rank_growth - nav_growth) < 0.01
    
    if date_match and nav_match and growth_match:
        print("\n✓ 数据一致性验证通过")
    else:
        print("\n⚠️  数据存在差异：")
        if not date_match:
            print(f"  日期不一致: {rank_date} vs {nav_date}")
        if not nav_match:
            print(f"  净值不一致: {rank_nav} vs {nav_value}")
        if not growth_match:
            print(f"  增长率不一致: {rank_growth}% vs {nav_growth}%")
    
    # 步骤4：QDII特性说明
    print("\n" + "-" * 80)
    print("【步骤4：QDII基金特性】")
    print("✓ QDII基金特点：")
    print("  • 投资海外市场（美股、港股等）")
    print("  • T+2确认，赎回到账时间较长（7-10个工作日）")
    print("  • 净值更新可能受海外市场时差影响")
    print("  • 可能有多个币种份额（人民币、美元等）")
    
    # 计算波动率
    if len(fund_nav) >= 20:
        recent_20_growth = fund_nav.tail(20)['日增长率'].tolist()
        import numpy as np
        volatility = np.std(recent_20_growth)
        print(f"\n✓ 近20日波动率: {volatility:.4f}%")
        if volatility > 1.0:
            print("  （波动率较高，符合QDII基金特征）")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    success = quick_test_qdii_fund()
    
    if not success:
        print("\n❌ 测试失败")
        sys.exit(1)
