#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金列表夏普比率计算汇总
"""

import sys
sys.path.insert(0, '.')

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List

from fund_search.data_retrieval.enhanced_database import EnhancedDatabaseManager
from fund_search.data_retrieval.multi_source_adapter import MultiSourceDataAdapter
from fund_search.shared.enhanced_config import DATABASE_CONFIG, PERFORMANCE_CONFIG, INVESTMENT_STRATEGY_CONFIG

# 配置参数
RISK_FREE_RATE = INVESTMENT_STRATEGY_CONFIG['risk_free_rate']  # 0.03
TRADING_DAYS = PERFORMANCE_CONFIG['trading_days_per_year']     # 252


def get_all_funds() -> List[Dict]:
    """获取所有未删除的基金"""
    db = EnhancedDatabaseManager(DATABASE_CONFIG)
    query = """
        SELECT fund_code, fund_name 
        FROM user_holdings 
        ORDER BY fund_code
    """
    df = db.execute_query(query)
    return df.to_dict('records') if not df.empty else []


def calculate_sharpe_summary(fund_code: str, fund_name: str, adapter: MultiSourceDataAdapter) -> Dict:
    """计算夏普比率汇总"""
    result = {
        'fund_code': fund_code,
        'fund_name': fund_name,
        'metrics': {}
    }
    
    try:
        hist_data = adapter.get_historical_data(fund_code, days=3650)
        
        if hist_data.empty:
            return result
        
        # 提取日收益率
        if '日增长率' in hist_data.columns:
            daily_growth_col = '日增长率'
        elif 'daily_return' in hist_data.columns:
            daily_growth_col = 'daily_return'
        else:
            return result
        
        daily_returns = hist_data[daily_growth_col].dropna()
        
        # 转换为小数形式（如果数据是百分比格式，如 0.65 表示 0.65%）
        # 判断标准：如果绝对值均值大于 0.1，认为是百分比格式
        if abs(daily_returns).mean() >= 0.01:
            daily_returns = daily_returns / 100
        
        # 计算全期指标
        nav_col = '累计净值' if '累计净值' in hist_data.columns else 'nav'
        date_col = '日期' if '日期' in hist_data.columns else 'date'
        
        # 确保数据按日期升序排列（最早的在前）
        if date_col in hist_data.columns:
            hist_data = hist_data.sort_values(date_col, ascending=True).reset_index(drop=True)
        
        start_nav = float(hist_data[nav_col].iloc[0])
        end_nav = float(hist_data[nav_col].iloc[-1])
        total_days = len(hist_data)
        
        total_return = (end_nav - start_nav) / start_nav
        annualized_return = (1 + total_return) ** (TRADING_DAYS / total_days) - 1
        volatility = daily_returns.std() * np.sqrt(TRADING_DAYS)
        
        sharpe_all = (annualized_return - RISK_FREE_RATE) / volatility if volatility != 0 else 0.0
        
        result['metrics']['sharpe_ratio_all'] = sharpe_all
        result['metrics']['annualized_return'] = annualized_return
        result['metrics']['volatility'] = volatility
        result['metrics']['total_days'] = total_days
        
        # 计算近一年指标
        now = pd.Timestamp.now()
        one_year_ago = now - pd.DateOffset(years=1)
        hist_data_copy = hist_data.copy()
        hist_data_copy[date_col] = pd.to_datetime(hist_data_copy[date_col])
        
        last_year_data = hist_data_copy[hist_data_copy[date_col] >= one_year_ago]
        
        if len(last_year_data) >= 30:
            last_year_returns = daily_returns[-len(last_year_data):]
            vol_1y = last_year_returns.std() * np.sqrt(TRADING_DAYS)
            
            start_nav_1y = float(last_year_data[nav_col].iloc[0])
            end_nav_1y = float(last_year_data[nav_col].iloc[-1])
            total_return_1y = (end_nav_1y - start_nav_1y) / start_nav_1y
            annualized_return_1y = (1 + total_return_1y) ** (TRADING_DAYS / len(last_year_data)) - 1
            
            sharpe_1y = (annualized_return_1y - RISK_FREE_RATE) / vol_1y if vol_1y != 0 else 0.0
            
            result['metrics']['sharpe_ratio_1y'] = sharpe_1y
        else:
            result['metrics']['sharpe_ratio_1y'] = 0.0
        
        # 计算YTD指标
        ytd_start = pd.Timestamp(year=now.year, month=1, day=1)
        ytd_data = hist_data_copy[hist_data_copy[date_col] >= ytd_start]
        
        if len(ytd_data) >= 10:
            ytd_returns = daily_returns[-len(ytd_data):]
            vol_ytd = ytd_returns.std() * np.sqrt(TRADING_DAYS)
            
            start_nav_ytd = float(ytd_data[nav_col].iloc[0])
            end_nav_ytd = float(ytd_data[nav_col].iloc[-1])
            total_return_ytd = (end_nav_ytd - start_nav_ytd) / start_nav_ytd
            annualized_return_ytd = (1 + total_return_ytd) ** (TRADING_DAYS / len(ytd_data)) - 1
            
            sharpe_ytd = (annualized_return_ytd - RISK_FREE_RATE) / vol_ytd if vol_ytd != 0 else 0.0
            
            result['metrics']['sharpe_ratio_ytd'] = sharpe_ytd
        else:
            result['metrics']['sharpe_ratio_ytd'] = 0.0
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def main():
    """主函数"""
    # 获取所有基金
    funds = get_all_funds()
    
    if not funds:
        print("没有找到基金数据")
        return
    
    # 创建数据适配器
    adapter = MultiSourceDataAdapter()
    
    # 存储所有结果
    all_results = []
    
    # 逐个计算每只基金的夏普比率
    for i, fund in enumerate(funds, 1):
        result = calculate_sharpe_summary(
            fund['fund_code'],
            fund['fund_name'],
            adapter
        )
        all_results.append(result)
    
    # 打印汇总表
    print("=" * 120)
    print("基金列表夏普比率计算汇总表")
    print("=" * 120)
    print(f"配置参数: 无风险利率={RISK_FREE_RATE}({RISK_FREE_RATE*100}%), 年化交易日={TRADING_DAYS}")
    print("=" * 120)
    print(f"{'基金代码':<12} {'基金名称':<30} {'夏普(全期)':<12} {'夏普(1年)':<12} {'夏普(YTD)':<12} {'数据天数':<10}")
    print("-" * 120)
    
    for r in all_results:
        code = r['fund_code']
        name = r['fund_name'][:28]  # 截断长名称
        metrics = r.get('metrics', {})
        
        sharpe_all = metrics.get('sharpe_ratio_all', 0)
        sharpe_1y = metrics.get('sharpe_ratio_1y', 0)
        sharpe_ytd = metrics.get('sharpe_ratio_ytd', 0)
        days = metrics.get('total_days', 0)
        
        print(f"{code:<12} {name:<30} {sharpe_all:<12.4f} {sharpe_1y:<12.4f} {sharpe_ytd:<12.4f} {days:<10}")
    
    print("=" * 120)
    print(f"\n共计算 {len(all_results)} 只基金")
    
    # 保存到CSV
    output_data = []
    for r in all_results:
        metrics = r.get('metrics', {})
        output_data.append({
            'fund_code': r['fund_code'],
            'fund_name': r['fund_name'],
            'sharpe_ratio_all': metrics.get('sharpe_ratio_all', 0),
            'sharpe_ratio_1y': metrics.get('sharpe_ratio_1y', 0),
            'sharpe_ratio_ytd': metrics.get('sharpe_ratio_ytd', 0),
            'annualized_return': metrics.get('annualized_return', 0),
            'volatility': metrics.get('volatility', 0),
            'total_days': metrics.get('total_days', 0)
        })
    
    df = pd.DataFrame(output_data)
    output_file = 'fund_sharpe_summary.csv'
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n详细结果已保存到: {output_file}")


if __name__ == '__main__':
    main()
