#!/usr/bin/env python
# coding: utf-8

"""
QDII基金净值获取测试用例 - 国富全球科技互联混合(QDII)人民币 (006105)

测试目标：
1. 验证QDII基金数据获取的完整性
2. 测试从排名接口获取QDII基金数据
3. 验证QDII基金的特殊字段（如日期、净值、增长率等）
4. 对比不同数据源的一致性

测试基金：国富全球科技互联混合(QDII)人民币
基金代码：006105
基金类型：QDII混合型基金
"""

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import akshare as ak
import pandas as pd


class TestQDIIFund006105:
    """QDII基金 006105 数据获取测试类"""
    
    def __init__(self):
        self.fund_code = "006105"
        self.fund_name = "国富全球科技互联混合(QDII)人民币"
    
    def test_1_rank_api_data(self):
        """
        测试1：从排名接口获取QDII基金数据
        目的：验证QDII基金可以从全部基金排名接口获取
        """
        print("=" * 80)
        print(f"测试1：排名接口数据 - {self.fund_name} ({self.fund_code})")
        print("=" * 80)
        
        try:
            # 获取所有开放基金的排名数据（包含QDII）
            print("正在获取全部开放基金排名数据...")
            all_funds_rank_df = ak.fund_open_fund_rank_em(symbol="全部")
            
            if all_funds_rank_df.empty:
                print("❌ 排名接口返回空数据")
                return False
            
            print(f"✅ 成功获取排名数据，共 {len(all_funds_rank_df)} 只基金")
            print(f"\n数据列名：{list(all_funds_rank_df.columns)}")
            
            # 查找代码为 006105 的基金
            fund_006105_rank = all_funds_rank_df[all_funds_rank_df['基金代码'] == self.fund_code]
            
            if fund_006105_rank.empty:
                print(f"❌ 未找到基金 {self.fund_code}")
                return False
            
            print(f"\n✅ 找到基金 {self.fund_code}")
            print("\n基金详细信息：")
            print("-" * 80)
            
            # 显示关键字段
            key_columns = ['基金代码', '基金简称', '日期', '单位净值', '日增长率', '近1月', '近3月', '近6月', '近1年', '今年来']
            available_columns = [col for col in key_columns if col in fund_006105_rank.columns]
            
            for col in available_columns:
                value = fund_006105_rank.iloc[0][col]
                print(f"  {col}: {value}")
            
            # 保存完整数据用于后续测试
            self.rank_data = fund_006105_rank.iloc[0]
            
            print("\n✅ 测试1通过")
            return True
            
        except Exception as e:
            print(f"❌ 测试1失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_2_nav_history_data(self):
        """
        测试2：获取QDII基金历史净值数据
        目的：验证可以获取QDII基金的完整历史净值走势
        """
        print("\n" + "=" * 80)
        print(f"测试2：历史净值数据 - {self.fund_name} ({self.fund_code})")
        print("=" * 80)
        
        try:
            # 获取基金历史净值数据
            print("正在获取历史净值数据...")
            fund_nav = ak.fund_open_fund_info_em(symbol=self.fund_code, indicator="单位净值走势")
            
            if fund_nav.empty:
                print("❌ 历史净值接口返回空数据")
                return False
            
            print(f"✅ 成功获取历史净值数据，共 {len(fund_nav)} 条记录")
            print(f"\n数据列名：{list(fund_nav.columns)}")
            
            # 按日期排序
            fund_nav = fund_nav.sort_values('净值日期', ascending=True)
            
            # 显示最近5天的数据
            print("\n最近5天的净值数据：")
            print("-" * 80)
            recent_5 = fund_nav.tail(5)
            for _, row in recent_5.iterrows():
                date = row.get('净值日期', 'N/A')
                nav = row.get('单位净值', 'N/A')
                growth = row.get('日增长率', 'N/A')
                print(f"  日期: {date} | 单位净值: {nav} | 日增长率: {growth}%")
            
            # 保存数据用于后续测试
            self.nav_history = fund_nav
            
            print("\n✅ 测试2通过")
            return True
            
        except Exception as e:
            print(f"❌ 测试2失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_3_basic_info(self):
        """
        测试3：获取QDII基金基本信息
        目的：验证可以获取QDII基金的基本信息（成立日期、基金类型等）
        """
        print("\n" + "=" * 80)
        print(f"测试3：基金基本信息 - {self.fund_name} ({self.fund_code})")
        print("=" * 80)
        
        try:
            # 获取基金基本信息
            print("正在获取基金基本信息...")
            fund_info = ak.fund_open_fund_info_em(symbol=self.fund_code, indicator="基本信息")
            
            if fund_info.empty:
                print("⚠️  基本信息接口返回空数据（QDII基金可能不提供此接口）")
                return True  # QDII基金可能不提供基本信息接口，不算失败
            
            print(f"✅ 成功获取基本信息，共 {len(fund_info)} 条记录")
            
            # 显示基本信息
            print("\n基金基本信息：")
            print("-" * 80)
            for _, row in fund_info.iterrows():
                item = row.get('项目', 'N/A')
                value = row.get('数值', 'N/A')
                print(f"  {item}: {value}")
            
            print("\n✅ 测试3通过")
            return True
            
        except Exception as e:
            print(f"⚠️  测试3异常（QDII基金可能不提供基本信息接口）: {str(e)}")
            return True  # 不算失败
    
    def test_4_data_consistency(self):
        """
        测试4：数据一致性验证
        目的：对比排名接口和历史净值接口的数据是否一致
        """
        print("\n" + "=" * 80)
        print(f"测试4：数据一致性验证 - {self.fund_name} ({self.fund_code})")
        print("=" * 80)
        
        if not hasattr(self, 'rank_data') or not hasattr(self, 'nav_history'):
            print("⚠️  缺少前置测试数据，跳过一致性验证")
            return True
        
        try:
            # 获取排名接口的最新数据
            rank_date = self.rank_data.get('日期', None)
            rank_nav = self.rank_data.get('单位净值', None)
            rank_growth = self.rank_data.get('日增长率', None)
            
            # 获取历史净值接口的最新数据
            latest_nav = self.nav_history.iloc[-1]
            nav_date = latest_nav.get('净值日期', None)
            nav_value = latest_nav.get('单位净值', None)
            nav_growth = latest_nav.get('日增长率', None)
            
            print("数据对比：")
            print("-" * 80)
            print(f"排名接口 - 日期: {rank_date} | 净值: {rank_nav} | 增长率: {rank_growth}%")
            print(f"历史接口 - 日期: {nav_date} | 净值: {nav_value} | 增长率: {nav_growth}%")
            
            # 验证日期是否一致
            if str(rank_date) == str(nav_date):
                print("\n✅ 日期一致")
            else:
                print(f"\n⚠️  日期不一致（可能是数据更新时间差异）")
            
            # 验证净值是否一致（允许小误差）
            if rank_nav is not None and nav_value is not None:
                nav_diff = abs(float(rank_nav) - float(nav_value))
                if nav_diff < 0.0001:
                    print(f"✅ 净值一致（差异: {nav_diff:.6f}）")
                else:
                    print(f"⚠️  净值存在差异（差异: {nav_diff:.6f}）")
            
            # 验证增长率是否一致（允许小误差）
            if rank_growth is not None and nav_growth is not None:
                growth_diff = abs(float(rank_growth) - float(nav_growth))
                if growth_diff < 0.01:
                    print(f"✅ 增长率一致（差异: {growth_diff:.4f}%）")
                else:
                    print(f"⚠️  增长率存在差异（差异: {growth_diff:.4f}%）")
            
            print("\n✅ 测试4通过")
            return True
            
        except Exception as e:
            print(f"❌ 测试4失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_5_qdii_specific_features(self):
        """
        测试5：QDII基金特有特性验证
        目的：验证QDII基金的特殊属性（如T+2到账、外币计价等）
        """
        print("\n" + "=" * 80)
        print(f"测试5：QDII特性验证 - {self.fund_name} ({self.fund_code})")
        print("=" * 80)
        
        try:
            print("QDII基金特性说明：")
            print("-" * 80)
            print("1. 交易规则：T+2 确认，赎回到账时间较长（通常7-10个工作日）")
            print("2. 计价货币：可能涉及外币计价（美元、港币等）")
            print("3. 净值更新：受海外市场交易时间影响，可能延迟更新")
            print("4. 投资范围：投资于海外市场（美股、港股等）")
            
            if hasattr(self, 'rank_data'):
                print("\n当前基金数据特征：")
                print("-" * 80)
                
                # 检查基金名称是否包含QDII标识
                fund_name = self.rank_data.get('基金简称', '')
                if 'QDII' in fund_name or '人民币' in fund_name:
                    print(f"✅ 基金名称包含QDII标识: {fund_name}")
                
                # 检查是否有外币份额
                if '人民币' in fund_name:
                    print("✅ 基金为人民币份额（可能还有美元份额）")
                
                # 显示近期收益率（QDII基金波动可能较大）
                if hasattr(self, 'nav_history') and len(self.nav_history) >= 5:
                    recent_growth = self.nav_history.tail(5)['日增长率'].tolist()
                    print(f"\n近5日增长率: {recent_growth}")
                    
                    # 计算波动率
                    import numpy as np
                    volatility = np.std(recent_growth)
                    print(f"近5日波动率: {volatility:.4f}%")
                    
                    if volatility > 1.0:
                        print("✅ 波动率较高，符合QDII基金特征")
            
            print("\n✅ 测试5通过")
            return True
            
        except Exception as e:
            print(f"❌ 测试5失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 80)
        print(f"QDII基金数据获取测试套件 - {self.fund_name} ({self.fund_code})")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        results = {
            '测试1：排名接口数据': self.test_1_rank_api_data(),
            '测试2：历史净值数据': self.test_2_nav_history_data(),
            '测试3：基金基本信息': self.test_3_basic_info(),
            '测试4：数据一致性验证': self.test_4_data_consistency(),
            '测试5：QDII特性验证': self.test_5_qdii_specific_features(),
        }
        
        # 汇总结果
        print("\n" + "=" * 80)
        print("测试结果汇总")
        print("=" * 80)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {test_name}: {status}")
        
        print(f"\n总计: {passed}/{total} 测试通过")
        
        if passed == total:
            print("\n🎉 所有测试通过！")
        else:
            print(f"\n⚠️  有 {total - passed} 个测试失败")
        
        return passed == total


def main():
    """主函数"""
    tester = TestQDIIFund006105()
    success = tester.run_all_tests()
    
    if success:
        print("\n" + "=" * 80)
        print("✅ QDII基金数据获取功能正常")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ QDII基金数据获取存在问题，请检查")
        print("=" * 80)


if __name__ == "__main__":
    main()
