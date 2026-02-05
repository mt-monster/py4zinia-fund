#!/usr/bin/env python
# coding: utf-8

"""
测试相关性图表生成功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backtesting.enhanced_correlation import EnhancedCorrelationAnalyzer

def create_sample_data():
    """创建示例基金数据"""
    # 生成日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # 生成示例收益率数据（模拟两只相关基金）
    np.random.seed(42)
    
    # 基金1：基础收益率 + 随机波动
    base_returns = np.random.normal(0.0005, 0.02, len(dates))
    
    # 基金2：与基金1有一定相关性 + 随机波动
    fund2_returns = 0.7 * base_returns + np.random.normal(0, 0.015, len(dates))
    
    # 创建DataFrame
    fund1_data = pd.DataFrame({
        'date': dates,
        'daily_return': base_returns * 100  # 转换为百分比
    })
    
    fund2_data = pd.DataFrame({
        'date': dates,
        'daily_return': fund2_returns * 100  # 转换为百分比
    })
    
    return {
        '002179': fund1_data,
        '013277': fund2_data
    }, {
        '002179': '华安事件驱动量化混合A',
        '013277': '富国创业板ETF联接C'
    }

def test_chart_generation():
    """测试图表生成功能"""
    print("开始测试相关性图表生成功能...")
    
    # 创建示例数据
    fund_data_dict, fund_names = create_sample_data()
    print(f"创建了 {len(fund_data_dict)} 只基金的示例数据")
    
    # 初始化分析器
    analyzer = EnhancedCorrelationAnalyzer()
    print("初始化EnhancedCorrelationAnalyzer...")
    
    # 生成图表
    try:
        chart_data = analyzer.generate_correlation_charts(fund_data_dict, fund_names)
        print("图表生成完成!")
        
        if chart_data and 'correlation_chart' in chart_data:
            print(f"图表数据长度: {len(chart_data['correlation_chart'])} 字符")
            print(f"基金1: {chart_data['fund1_name']}")
            print(f"基金2: {chart_data['fund2_name']}")
            
            # 保存图表到文件进行验证
            import base64
            with open('test_correlation_chart.png', 'wb') as f:
                f.write(base64.b64decode(chart_data['correlation_chart']))
            print("图表已保存为 test_correlation_chart.png")
            
            return True
        else:
            print("图表数据为空")
            return False
            
    except Exception as e:
        print(f"图表生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chart_generation()
    if success:
        print("\n✅ 测试成功！相关性图表生成功能正常工作。")
    else:
        print("\n❌ 测试失败！请检查错误信息。")