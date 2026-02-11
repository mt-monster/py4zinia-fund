#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
展示基金列表中所有基金的夏普比率计算过程
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


def calculate_sharpe_step_by_step(fund_code: str, fund_name: str, adapter: MultiSourceDataAdapter) -> Dict:
    """
    逐步计算夏普比率，展示详细过程
    """
    result = {
        'fund_code': fund_code,
        'fund_name': fund_name,
        'calculation_steps': [],
        'metrics': {}
    }
    
    try:
        # 步骤1: 获取历史数据
        result['calculation_steps'].append("=" * 80)
        result['calculation_steps'].append(f"【基金】{fund_code} - {fund_name}")
        result['calculation_steps'].append("=" * 80)
        result['calculation_steps'].append("\n【步骤1】获取历史净值数据...")
        
        hist_data = adapter.get_historical_data(fund_code, days=3650)
        
        if hist_data.empty:
            result['calculation_steps'].append("  [ERR] 未获取到历史数据")
            return result
        
        result['calculation_steps'].append(f"  [OK] 获取到 {len(hist_data)} 条历史记录")
        result['calculation_steps'].append(f"  数据范围: {hist_data['date'].min()} 至 {hist_data['date'].max()}")
        
        # 步骤2: 提取日收益率
        result['calculation_steps'].append("\n【步骤2】提取日收益率...")
        
        if '日增长率' in hist_data.columns:
            daily_growth_col = '日增长率'
        elif 'daily_return' in hist_data.columns:
            daily_growth_col = 'daily_return'
        else:
            result['calculation_steps'].append("  [ERR] 未找到日增长率字段")
            return result
        
        daily_returns = hist_data[daily_growth_col].dropna()
        
        # 转换为小数形式
        if abs(daily_returns).mean() < 1:
            daily_returns = daily_returns  # 已经是小数
            result['calculation_steps'].append(f"  [OK] 日收益率已经是小数格式")
        else:
            daily_returns = daily_returns / 100  # 从百分比转换
            result['calculation_steps'].append(f"  [OK] 日收益率从百分比转换为小数")
        
        result['calculation_steps'].append(f"  有效日收益率数据: {len(daily_returns)} 条")
        result['calculation_steps'].append(f"  日收益率均值: {daily_returns.mean():.6f}")
        result['calculation_steps'].append(f"  日收益率标准差: {daily_returns.std():.6f}")
        
        # 步骤3: 计算全期指标
        result['calculation_steps'].append("\n【步骤3】计算全期夏普比率...")
        
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
        
        result['calculation_steps'].append(f"  起始净值: {start_nav:.4f}")
        result['calculation_steps'].append(f"  最新净值: {end_nav:.4f}")
        result['calculation_steps'].append(f"  持有天数: {total_days}")
        result['calculation_steps'].append(f"  总收益率: {total_return:.4f} ({total_return*100:.2f}%)")
        result['calculation_steps'].append(f"  年化收益率: {annualized_return:.4f} ({annualized_return*100:.2f}%)")
        result['calculation_steps'].append(f"  年化波动率: {volatility:.4f} ({volatility*100:.2f}%)")
        
        sharpe_all = (annualized_return - RISK_FREE_RATE) / volatility if volatility != 0 else 0.0
        result['calculation_steps'].append(f"\n  夏普比率计算公式:")
        result['calculation_steps'].append(f"    Sharpe = (年化收益 - 无风险利率) / 年化波动率")
        result['calculation_steps'].append(f"    Sharpe = ({annualized_return:.4f} - {RISK_FREE_RATE}) / {volatility:.4f}")
        result['calculation_steps'].append(f"    Sharpe = {sharpe_all:.4f}")
        
        result['metrics']['sharpe_ratio_all'] = sharpe_all
        result['metrics']['annualized_return'] = annualized_return
        result['metrics']['volatility'] = volatility
        result['metrics']['total_days'] = total_days
        
        # 步骤4: 计算近一年指标
        result['calculation_steps'].append("\n【步骤4】计算近一年夏普比率...")
        
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
            
            result['calculation_steps'].append(f"  近一年数据: {len(last_year_data)} 个交易日")
            result['calculation_steps'].append(f"  起始净值: {start_nav_1y:.4f}, 最新净值: {end_nav_1y:.4f}")
            result['calculation_steps'].append(f"  年化收益率: {annualized_return_1y:.4f} ({annualized_return_1y*100:.2f}%)")
            result['calculation_steps'].append(f"  年化波动率: {vol_1y:.4f} ({vol_1y*100:.2f}%)")
            result['calculation_steps'].append(f"  夏普比率(1年): {sharpe_1y:.4f}")
            
            result['metrics']['sharpe_ratio_1y'] = sharpe_1y
            result['metrics']['annualized_return_1y'] = annualized_return_1y
            result['metrics']['volatility_1y'] = vol_1y
        else:
            result['calculation_steps'].append(f"  [ERR] 近一年数据不足 ({len(last_year_data)} 天 < 30 天)")
            result['metrics']['sharpe_ratio_1y'] = 0.0
        
        # 步骤5: 计算YTD指标
        result['calculation_steps'].append("\n【步骤5】计算今年以来夏普比率...")
        
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
            
            result['calculation_steps'].append(f"  YTD数据: {len(ytd_data)} 个交易日")
            result['calculation_steps'].append(f"  起始净值: {start_nav_ytd:.4f}, 最新净值: {end_nav_ytd:.4f}")
            result['calculation_steps'].append(f"  年化收益率: {annualized_return_ytd:.4f} ({annualized_return_ytd*100:.2f}%)")
            result['calculation_steps'].append(f"  年化波动率: {vol_ytd:.4f} ({vol_ytd*100:.2f}%)")
            result['calculation_steps'].append(f"  夏普比率(YTD): {sharpe_ytd:.4f}")
            
            result['metrics']['sharpe_ratio_ytd'] = sharpe_ytd
            result['metrics']['annualized_return_ytd'] = annualized_return_ytd
            result['metrics']['volatility_ytd'] = vol_ytd
        else:
            result['calculation_steps'].append(f"  [ERR] YTD数据不足 ({len(ytd_data)} 天 < 10 天)")
            result['metrics']['sharpe_ratio_ytd'] = 0.0
        
        # 最终结果
        result['calculation_steps'].append("\n" + "=" * 80)
        result['calculation_steps'].append("【计算结果汇总】")
        result['calculation_steps'].append(f"  夏普比率(全期): {result['metrics'].get('sharpe_ratio_all', 0):.4f}")
        result['calculation_steps'].append(f"  夏普比率(1年):  {result['metrics'].get('sharpe_ratio_1y', 0):.4f}")
        result['calculation_steps'].append(f"  夏普比率(YTD):  {result['metrics'].get('sharpe_ratio_ytd', 0):.4f}")
        result['calculation_steps'].append("=" * 80)
        
    except Exception as e:
        result['calculation_steps'].append(f"\n  [ERR] 计算出错: {str(e)}")
        import traceback
        result['calculation_steps'].append(traceback.format_exc())
    
    return result


def print_summary_table(all_results: List[Dict]):
    """打印汇总表格"""
    print("\n\n")
    print("=" * 100)
    print("【基金列表夏普比率汇总表】")
    print("=" * 100)
    print(f"{'基金代码':<12} {'基金名称':<20} {'夏普(全期)':<12} {'夏普(1年)':<12} {'夏普(YTD)':<12} {'数据天数':<10}")
    print("-" * 100)
    
    for r in all_results:
        code = r['fund_code']
        name = r['fund_name'][:18]  # 截断长名称
        metrics = r.get('metrics', {})
        
        sharpe_all = metrics.get('sharpe_ratio_all', 0)
        sharpe_1y = metrics.get('sharpe_ratio_1y', 0)
        sharpe_ytd = metrics.get('sharpe_ratio_ytd', 0)
        days = metrics.get('total_days', 0)
        
        print(f"{code:<12} {name:<20} {sharpe_all:<12.4f} {sharpe_1y:<12.4f} {sharpe_ytd:<12.4f} {days:<10}")
    
    print("=" * 100)


def main():
    """主函数"""
    print("=" * 100)
    print("基金列表夏普比率计算过程展示")
    print("=" * 100)
    print(f"\n【系统配置参数】")
    print(f"  无风险利率: {RISK_FREE_RATE} ({RISK_FREE_RATE*100}%)")
    print(f"  年化交易日: {TRADING_DAYS}")
    print()
    
    # 获取所有基金
    funds = get_all_funds()
    print(f"【基金数量】共 {len(funds)} 只基金\n")
    
    if not funds:
        print("没有找到基金数据")
        return
    
    # 创建数据适配器
    adapter = MultiSourceDataAdapter()
    
    # 存储所有结果
    all_results = []
    
    # 逐个计算每只基金的夏普比率
    for i, fund in enumerate(funds, 1):
        print(f"\n\n正在计算第 {i}/{len(funds)} 只基金...")
        
        result = calculate_sharpe_step_by_step(
            fund['fund_code'],
            fund['fund_name'],
            adapter
        )
        
        # 输出计算过程
        for line in result['calculation_steps']:
            print(line)
        
        all_results.append(result)
    
    # 打印汇总表
    print_summary_table(all_results)
    
    print("\n\n计算完成！")


if __name__ == '__main__':
    main()
