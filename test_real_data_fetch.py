#!/usr/bin/env python
# coding: utf-8

"""
测试真实数据获取功能
验证沪深300和基金净值数据的真实性
"""

import sys
import os
sys.path.append('pro2/fund_search')

from web.real_data_fetcher import RealDataFetcher
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

def test_csi300_data():
    """测试沪深300数据获取"""
    print("🧪 测试沪深300真实数据获取...")
    
    try:
        # 获取沪深300历史数据
        csi300_data = RealDataFetcher.get_csi300_history(100)
        
        if csi300_data.empty:
            print("❌ 无法获取沪深300数据")
            return False
        
        print(f"✅ 成功获取沪深300数据 {len(csi300_data)} 条")
        print(f"📊 数据时间范围: {csi300_data['date'].min()} 到 {csi300_data['date'].max()}")
        print(f"📈 价格范围: {csi300_data['price'].min():.2f} - {csi300_data['price'].max():.2f}")
        
        # 计算收益率统计
        prices = csi300_data['price'].values
        returns = [(prices[i]/prices[i-1]-1)*100 for i in range(1, len(prices))]
        
        print(f"📊 日收益率统计:")
        print(f"   平均值: {np.mean(returns):.3f}%")
        print(f"   标准差: {np.std(returns):.3f}%")
        print(f"   最大值: {np.max(returns):.3f}%")
        print(f"   最小值: {np.min(returns):.3f}%")
        
        # 验证数据真实性特征
        std_dev = np.std(returns)
        if 0.5 <= std_dev <= 3.0:  # 沪深300日波动率通常在0.5%-3%之间
            print("✅ 波动率符合沪深300真实特征")
        else:
            print(f"⚠️ 波动率 {std_dev:.3f}% 可能不符合沪深300特征")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试沪深300数据时出错: {str(e)}")
        return False

def test_fund_nav_data():
    """测试基金净值数据获取"""
    print("\n🧪 测试基金净值真实数据获取...")
    
    # 测试几个常见的基金代码
    test_funds = ['000001', '110011', '161725']  # 华夏成长、易方达中小盘、招商中证白酒
    
    results = {}
    
    for fund_code in test_funds:
        try:
            print(f"\n测试基金 {fund_code}...")
            fund_data = RealDataFetcher.get_fund_nav_history(fund_code, 60)
            
            if fund_data.empty:
                print(f"❌ 基金 {fund_code} 无数据")
                results[fund_code] = None
                continue
            
            print(f"✅ 获取到 {len(fund_data)} 条净值数据")
            print(f"📊 净值范围: {fund_data['nav'].min():.4f} - {fund_data['nav'].max():.4f}")
            
            # 计算基金收益率统计
            navs = fund_data['nav'].values
            returns = [(navs[i]/navs[i-1]-1)*100 for i in range(1, len(navs))]
            
            if returns:
                print(f"📊 日收益率统计:")
                print(f"   平均值: {np.mean(returns):.3f}%")
                print(f"   标准差: {np.std(returns):.3f}%")
                print(f"   最大值: {np.max(returns):.3f}%")
                print(f"   最小值: {np.min(returns):.3f}%")
            
            results[fund_code] = fund_data
            
        except Exception as e:
            print(f"❌ 测试基金 {fund_code} 时出错: {str(e)}")
            results[fund_code] = None
    
    successful_funds = [code for code, data in results.items() if data is not None]
    print(f"\n📈 成功获取 {len(successful_funds)} 只基金的数据: {', '.join(successful_funds)}")
    
    return len(successful_funds) > 0

def test_portfolio_calculation():
    """测试投资组合净值计算"""
    print("\n🧪 测试投资组合净值计算...")
    
    try:
        # 使用测试基金进行组合计算
        fund_codes = ['000001', '110011']
        weights = [0.6, 0.4]  # 60%华夏成长，40%易方达中小盘
        
        portfolio_data = RealDataFetcher.calculate_portfolio_nav(
            fund_codes, weights, initial_amount=10000, days=90
        )
        
        if portfolio_data.empty:
            print("❌ 投资组合计算失败")
            return False
        
        print(f"✅ 成功计算投资组合净值 {len(portfolio_data)} 条")
        print(f"📊 组合净值范围: {portfolio_data['portfolio_nav'].min():.2f} - {portfolio_data['portfolio_nav'].max():.2f}")
        print(f"📊 数据时间范围: {portfolio_data['date'].min()} 到 {portfolio_data['date'].max()}")
        
        # 验证组合计算逻辑
        first_value = portfolio_data.iloc[0]['portfolio_nav']
        last_value = portfolio_data.iloc[-1]['portfolio_nav']
        total_return = (last_value/first_value - 1) * 100
        
        print(f"📊 组合总收益率: {total_return:.2f}%")
        
        if abs(first_value - 10000) < 1:  # 起始值应该是10000左右
            print("✅ 起始净值计算正确")
        else:
            print(f"⚠️ 起始净值异常: {first_value}")
        
        return True
        
    except Exception as e:
        print(f"❌ 投资组合计算测试失败: {str(e)}")
        return False

def visualize_real_data():
    """可视化真实数据"""
    print("\n🎨 生成真实数据可视化...")
    
    try:
        # 获取数据
        csi300_data = RealDataFetcher.get_csi300_history(90)
        
        # 获取一只基金数据
        fund_data = RealDataFetcher.get_fund_nav_history('000001', 90)
        
        if csi300_data.empty or fund_data.empty:
            print("❌ 无法获取可视化所需数据")
            return
        
        # 创建图表
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # 沪深300图表
        ax1.plot(csi300_data['date'], csi300_data['price'], 'r-', linewidth=2, label='沪深300指数')
        ax1.set_title('沪深300指数真实历史数据', fontsize=14, fontweight='bold')
        ax1.set_ylabel('指数点位', fontsize=12)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 基金净值图表
        ax2.plot(fund_data['date'], fund_data['nav'], 'b-', linewidth=2, label='华夏成长基金净值')
        ax2.set_title('基金净值真实历史数据', fontsize=14, fontweight='bold')
        ax2.set_xlabel('日期', fontsize=12)
        ax2.set_ylabel('单位净值', fontsize=12)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('real_historical_data.png', dpi=300, bbox_inches='tight')
        print("✅ 真实数据图表已保存为 real_historical_data.png")
        plt.show()
        
    except Exception as e:
        print(f"❌ 生成可视化图表时出错: {str(e)}")

def main():
    print("=" * 60)
    print("真实历史数据获取测试")
    print("=" * 60)
    
    # 测试各项功能
    csi300_success = test_csi300_data()
    fund_success = test_fund_nav_data()
    portfolio_success = test_portfolio_calculation()
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print(f"📊 沪深300数据获取: {'✅ 成功' if csi300_success else '❌ 失败'}")
    print(f"💰 基金净值获取: {'✅ 成功' if fund_success else '❌ 失败'}")
    print(f"📈 组合计算功能: {'✅ 成功' if portfolio_success else '❌ 失败'}")
    
    if csi300_success and fund_success:
        print("\n🎉 核心功能测试通过！系统可以获取真实历史数据")
        visualize_real_data()
    else:
        print("\n❌ 核心功能存在问题，请检查网络连接和AkShare接口")
    
    print("=" * 60)

if __name__ == "__main__":
    main()