#!/usr/bin/env python
# coding: utf-8

"""
测试真实数据API功能
验证净值曲线对比图表使用真实历史数据
"""

import requests
import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import time

def test_real_data_api():
    """测试真实数据API"""
    print("🧪 测试真实数据API...")
    
    # 测试参数
    test_params = {
        'days': 90,
        'fund_codes': '000001,110011',  # 华夏成长 + 易方达中小盘
        'weights': '0.6,0.4'
    }
    
    url = "http://127.0.0.1:5000/api/dashboard/profit-trend"
    
    try:
        print(f"📡 请求参数: {test_params}")
        response = requests.get(url, params=test_params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print("✅ API调用成功")
                
                # 分析返回的数据
                labels = data['data']['labels']
                profit_data = data['data']['profit']
                benchmark_data = data['data']['benchmark']
                fund_codes = data['data']['fund_codes']
                weights = data['data']['weights']
                data_source = data['data']['data_source']
                
                print(f"📊 数据点数量: {len(labels)}")
                print(f"💰 基金代码: {', '.join(fund_codes)}")
                print(f"⚖️  权重分配: {', '.join([f'{w:.2f}' for w in weights])}")
                print(f"📈 数据来源: {data_source}")
                print(f"📈 策略净值范围: ¥{min(profit_data):.2f} - ¥{max(profit_data):.2f}")
                print(f"📊 基准净值范围: ¥{min(benchmark_data):.2f} - ¥{max(benchmark_data):.2f}")
                
                # 计算收益率
                strategy_return = ((profit_data[-1]/profit_data[0]) - 1) * 100
                benchmark_return = ((benchmark_data[-1]/benchmark_data[0]) - 1) * 100
                
                print(f"📈 策略总收益率: {strategy_return:.2f}%")
                print(f"📊 基准总收益率: {benchmark_return:.2f}%")
                
                # 验证数据真实性
                if data_source == 'real_historical_data':
                    print("✅ 确认使用真实历史数据")
                    
                    # 检查数据波动性
                    strategy_returns = [(profit_data[i]/profit_data[i-1]-1)*100 
                                      for i in range(1, len(profit_data))]
                    benchmark_returns = [(benchmark_data[i]/benchmark_data[i-1]-1)*100 
                                       for i in range(1, len(benchmark_data))]
                    
                    strategy_volatility = np.std(strategy_returns)
                    benchmark_volatility = np.std(benchmark_returns)
                    
                    print(f"📈 策略日波动率: {strategy_volatility:.3f}%")
                    print(f"📊 基准日波动率: {benchmark_volatility:.3f}%")
                    
                    # 生成可视化图表
                    visualize_real_data_comparison(labels, profit_data, benchmark_data, 
                                                 strategy_return, benchmark_return)
                    
                    return True
                else:
                    print("❌ 未使用真实历史数据")
                    return False
            else:
                print(f"❌ API返回错误: {data.get('error', '未知错误')}")
                return False
        else:
            print(f"❌ HTTP请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        return False

def visualize_real_data_comparison(labels, profit_data, benchmark_data, 
                                 strategy_return, benchmark_return):
    """可视化真实数据对比"""
    print("\n🎨 生成真实数据对比图表...")
    
    plt.figure(figsize=(12, 8))
    
    # 绘制策略净值曲线
    plt.plot(range(len(profit_data)), profit_data, 'b-', linewidth=2.5, 
             label=f'基金组合净值 (收益: {strategy_return:.2f}%)', 
             marker='o', markersize=4)
    
    # 绘制基准净值曲线
    plt.plot(range(len(benchmark_data)), benchmark_data, 'r-', linewidth=2.5, 
             label=f'沪深300基准 (收益: {benchmark_return:.2f}%)', 
             marker='s', markersize=4)
    
    plt.xlabel('交易日', fontsize=12)
    plt.ylabel('净值 (元)', fontsize=12)
    plt.title('基金组合 vs 沪深300基准 - 真实历史数据对比', 
              fontsize=14, fontweight='bold')
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)
    
    # 设置x轴标签
    if len(labels) > 10:
        step = len(labels) // 10
        plt.xticks(range(0, len(labels), step), 
                  [labels[i] for i in range(0, len(labels), step)], 
                  rotation=45)
    else:
        plt.xticks(range(len(labels)), labels, rotation=45)
    
    # 添加统计信息框
    stats_text = f'''数据统计:
策略净值范围: ¥{min(profit_data):.2f} - ¥{max(profit_data):.2f}
基准净值范围: ¥{min(benchmark_data):.2f} - ¥{max(benchmark_data):.2f}
数据点数: {len(labels)}个交易日'''

    plt.text(0.02, 0.98, stats_text,
             transform=plt.gca().transAxes, 
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
             fontsize=10)
    
    plt.tight_layout()
    plt.savefig('real_data_performance_comparison.png', dpi=300, bbox_inches='tight')
    print("✅ 真实数据对比图表已保存为 real_data_performance_comparison.png")
    plt.show()

def test_multiple_scenarios():
    """测试多种场景"""
    print("\n🧪 测试多种数据场景...")
    
    scenarios = [
        {
            'name': '单只基金场景',
            'params': {'days': 60, 'fund_codes': '000001', 'weights': '1.0'}
        },
        {
            'name': '多只基金等权场景', 
            'params': {'days': 90, 'fund_codes': '000001,110011,161725', 'weights': '1.0,1.0,1.0'}
        },
        {
            'name': '自定义权重场景',
            'params': {'days': 120, 'fund_codes': '000001,110011', 'weights': '0.7,0.3'}
        }
    ]
    
    results = []
    
    for scenario in scenarios:
        print(f"\n--- 测试场景: {scenario['name']} ---")
        try:
            response = requests.get("http://127.0.0.1:5000/api/dashboard/profit-trend", 
                                  params=scenario['params'], timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data['data']['data_source'] == 'real_historical_data':
                    print("✅ 场景测试成功")
                    results.append({
                        'scenario': scenario['name'],
                        'success': True,
                        'data_points': len(data['data']['labels']),
                        'funds': len(data['data']['fund_codes'])
                    })
                else:
                    print("❌ 场景测试失败")
                    results.append({
                        'scenario': scenario['name'],
                        'success': False,
                        'reason': data.get('error', '未知原因')
                    })
            else:
                print(f"❌ HTTP请求失败: {response.status_code}")
                results.append({
                    'scenario': scenario['name'],
                    'success': False,
                    'reason': f'HTTP {response.status_code}'
                })
                
            time.sleep(1)  # 避免请求过于频繁
            
        except Exception as e:
            print(f"❌ 场景测试出错: {str(e)}")
            results.append({
                'scenario': scenario['name'],
                'success': False,
                'reason': str(e)
            })
    
    # 输出测试结果汇总
    print("\n" + "="*50)
    print("场景测试结果汇总:")
    print("="*50)
    
    successful_scenarios = [r for r in results if r['success']]
    failed_scenarios = [r for r in results if not r['success']]
    
    print(f"✅ 成功场景: {len(successful_scenarios)} 个")
    for result in successful_scenarios:
        print(f"   • {result['scenario']}: {result['data_points']}个数据点, {result['funds']}只基金")
    
    if failed_scenarios:
        print(f"❌ 失败场景: {len(failed_scenarios)} 个")
        for result in failed_scenarios:
            print(f"   • {result['scenario']}: {result['reason']}")

def main():
    print("=" * 60)
    print("真实历史数据API测试")
    print("=" * 60)
    
    # 测试主功能
    main_test_success = test_real_data_api()
    
    # 测试多种场景
    test_multiple_scenarios()
    
    print("\n" + "=" * 60)
    if main_test_success:
        print("🎉 核心功能测试通过！净值曲线现在使用真实历史数据")
        print("📊 沪深300基准线和基金组合净值均基于真实市场数据")
    else:
        print("❌ 核心功能测试失败，请检查系统配置")
    print("=" * 60)

if __name__ == "__main__":
    main()