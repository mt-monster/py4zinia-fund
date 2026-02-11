#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成所有基金夏普比率完整计算说明文档
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


def calculate_fund_detail(fund_code: str, fund_name: str, adapter: MultiSourceDataAdapter) -> Dict:
    """
    计算单个基金的详细指标
    """
    result = {
        'fund_code': fund_code,
        'fund_name': fund_name,
        'steps': [],
        'metrics': {}
    }
    
    try:
        # 获取历史数据
        hist_data = adapter.get_historical_data(fund_code, days=3650)
        
        if hist_data.empty:
            result['steps'].append("[ERR] 未获取到历史数据")
            return result
        
        # 确定列名
        if '日增长率' in hist_data.columns:
            daily_growth_col = '日增长率'
        elif 'daily_return' in hist_data.columns:
            daily_growth_col = 'daily_return'
        else:
            result['steps'].append("[ERR] 未找到日增长率字段")
            return result
        
        nav_col = '累计净值' if '累计净值' in hist_data.columns else 'nav'
        date_col = '日期' if '日期' in hist_data.columns else 'date'
        
        # 确保数据按日期升序排列
        if date_col in hist_data.columns:
            hist_data = hist_data.sort_values(date_col, ascending=True).reset_index(drop=True)
        
        # 提取日收益率
        daily_returns = hist_data[daily_growth_col].dropna()
        
        # 判断并转换为小数形式
        mean_abs_before = abs(daily_returns).mean()
        if mean_abs_before >= 0.01:
            daily_returns = daily_returns / 100
            is_percentage = True
        else:
            is_percentage = False
        
        mean_abs_after = abs(daily_returns).mean()
        
        # 基础数据信息
        total_days = len(hist_data)
        start_date = hist_data[date_col].iloc[0]
        end_date = hist_data[date_col].iloc[-1]
        start_nav = float(hist_data[nav_col].iloc[0])
        end_nav = float(hist_data[nav_col].iloc[-1])
        
        # 日收益率统计
        daily_std = daily_returns.std()
        daily_mean = daily_returns.mean()
        
        # 计算全期指标
        total_return = (end_nav - start_nav) / start_nav
        annualized_return = (1 + total_return) ** (TRADING_DAYS / total_days) - 1
        volatility = daily_std * np.sqrt(TRADING_DAYS)
        sharpe_all = (annualized_return - RISK_FREE_RATE) / volatility if volatility != 0 else 0.0
        
        # 记录步骤
        result['steps'].append(f"数据天数: {total_days} 天")
        result['steps'].append(f"数据范围: {start_date} 至 {end_date}")
        result['steps'].append(f"日收益率格式: {'百分比' if is_percentage else '小数'} (转换前均值: {mean_abs_before:.6f})")
        result['steps'].append(f"日收益率统计: 均值={daily_mean:.6f}, 标准差={daily_std:.6f}")
        result['steps'].append(f"起始净值: {start_nav:.4f}")
        result['steps'].append(f"最新净值: {end_nav:.4f}")
        result['steps'].append(f"总收益率: {total_return:.4f} ({total_return*100:.2f}%)")
        result['steps'].append(f"年化收益率: {annualized_return:.4f} ({annualized_return*100:.2f}%)")
        result['steps'].append(f"年化波动率: {volatility:.4f} ({volatility*100:.2f}%)")
        result['steps'].append(f"夏普比率(全期) = ({annualized_return:.4f} - {RISK_FREE_RATE}) / {volatility:.4f} = {sharpe_all:.4f}")
        
        result['metrics']['sharpe_all'] = sharpe_all
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
            
            result['steps'].append(f"近一年数据: {len(last_year_data)} 个交易日")
            result['steps'].append(f"近一年年化收益率: {annualized_return_1y:.4f} ({annualized_return_1y*100:.2f}%)")
            result['steps'].append(f"近一年年化波动率: {vol_1y:.4f} ({vol_1y*100:.2f}%)")
            result['steps'].append(f"夏普比率(1年) = ({annualized_return_1y:.4f} - {RISK_FREE_RATE}) / {vol_1y:.4f} = {sharpe_1y:.4f}")
            result['metrics']['sharpe_1y'] = sharpe_1y
        else:
            result['steps'].append(f"近一年数据不足 ({len(last_year_data)} 天 < 30 天)")
            result['metrics']['sharpe_1y'] = 0.0
        
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
            
            result['steps'].append(f"YTD数据: {len(ytd_data)} 个交易日")
            result['steps'].append(f"YTD年化收益率: {annualized_return_ytd:.4f} ({annualized_return_ytd*100:.2f}%)")
            result['steps'].append(f"YTD年化波动率: {vol_ytd:.4f} ({vol_ytd*100:.2f}%)")
            result['steps'].append(f"夏普比率(YTD) = ({annualized_return_ytd:.4f} - {RISK_FREE_RATE}) / {vol_ytd:.4f} = {sharpe_ytd:.4f}")
            result['metrics']['sharpe_ytd'] = sharpe_ytd
        else:
            result['steps'].append(f"YTD数据不足 ({len(ytd_data)} 天 < 10 天)")
            result['metrics']['sharpe_ytd'] = 0.0
        
    except Exception as e:
        result['steps'].append(f"[ERR] 计算出错: {str(e)}")
    
    return result


def generate_document():
    """生成完整计算说明文档"""
    
    # 获取所有基金
    funds = get_all_funds()
    if not funds:
        print("没有找到基金数据")
        return
    
    # 创建数据适配器
    adapter = MultiSourceDataAdapter()
    
    # 存储所有结果
    all_results = []
    
    # 逐个计算每只基金
    for i, fund in enumerate(funds, 1):
        print(f"正在计算第 {i}/{len(funds)} 只基金: {fund['fund_code']}")
        result = calculate_fund_detail(fund['fund_code'], fund['fund_name'], adapter)
        all_results.append(result)
    
    # 生成文档
    doc_lines = []
    
    # 标题
    doc_lines.append("# 基金列表所有基金夏普比率详细计算说明")
    doc_lines.append("")
    doc_lines.append("**生成时间**: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    doc_lines.append("")
    
    # 配置参数
    doc_lines.append("## 一、计算配置参数")
    doc_lines.append("")
    doc_lines.append("| 参数名 | 值 | 说明 |")
    doc_lines.append("|--------|-----|------|")
    doc_lines.append(f"| 无风险利率 (Risk Free Rate) | {RISK_FREE_RATE} ({RISK_FREE_RATE*100}%) | 年化无风险收益率 |")
    doc_lines.append(f"| 年化交易日 (Trading Days) | {TRADING_DAYS} | 每年交易日数 |")
    doc_lines.append("")
    
    # 计算公式
    doc_lines.append("## 二、计算公式")
    doc_lines.append("")
    doc_lines.append("### 2.1 夏普比率公式")
    doc_lines.append("```")
    doc_lines.append("夏普比率 = (年化收益率 - 无风险利率) / 年化波动率")
    doc_lines.append("Sharpe Ratio = (Annualized Return - Risk Free Rate) / Annualized Volatility")
    doc_lines.append("```")
    doc_lines.append("")
    doc_lines.append("### 2.2 年化收益率计算")
    doc_lines.append("```")
    doc_lines.append("总收益率 = (最新净值 - 起始净值) / 起始净值")
    doc_lines.append("年化收益率 = (1 + 总收益率)^(交易天数/持有天数) - 1")
    doc_lines.append("```")
    doc_lines.append("")
    doc_lines.append("### 2.3 年化波动率计算")
    doc_lines.append("```")
    doc_lines.append("年化波动率 = 日收益率标准差 × √252")
    doc_lines.append("```")
    doc_lines.append("")
    doc_lines.append("### 2.4 日收益率格式说明")
    doc_lines.append("- 数据源返回的日增长率可能是**百分比格式**（如0.65表示0.65%）")
    doc_lines.append("- 计算前需转换为**小数格式**（如0.0065表示0.65%）")
    doc_lines.append("- 转换方式：如果日收益率绝对值均值 >= 0.01，则除以100")
    doc_lines.append("")
    
    # 所有基金详细计算
    doc_lines.append("## 三、所有基金详细计算过程")
    doc_lines.append("")
    
    for result in all_results:
        doc_lines.append(f"### 3.{all_results.index(result)+1} {result['fund_code']} {result['fund_name']}")
        doc_lines.append("")
        for step in result['steps']:
            doc_lines.append(f"- {step}")
        doc_lines.append("")
        
        # 汇总
        metrics = result.get('metrics', {})
        if metrics:
            doc_lines.append("**计算结果汇总**:")
            doc_lines.append(f"- 夏普比率(全期): {metrics.get('sharpe_all', 0):.4f}")
            doc_lines.append(f"- 夏普比率(1年): {metrics.get('sharpe_1y', 0):.4f}")
            doc_lines.append(f"- 夏普比率(YTD): {metrics.get('sharpe_ytd', 0):.4f}")
            doc_lines.append(f"- 年化收益率: {metrics.get('annualized_return', 0)*100:.2f}%")
            doc_lines.append(f"- 年化波动率: {metrics.get('volatility', 0)*100:.2f}%")
            doc_lines.append("")
    
    # 汇总表
    doc_lines.append("## 四、所有基金计算结果汇总表")
    doc_lines.append("")
    doc_lines.append("| 基金代码 | 基金名称 | 夏普(全期) | 夏普(1年) | 夏普(YTD) | 年化收益 | 年化波动 | 数据天数 |")
    doc_lines.append("|----------|----------|------------|-----------|-----------|----------|----------|----------|")
    
    for result in all_results:
        code = result['fund_code']
        name = result['fund_name'][:20]
        metrics = result.get('metrics', {})
        sharpe_all = metrics.get('sharpe_all', 0)
        sharpe_1y = metrics.get('sharpe_1y', 0)
        sharpe_ytd = metrics.get('sharpe_ytd', 0)
        ann_ret = metrics.get('annualized_return', 0) * 100
        vol = metrics.get('volatility', 0) * 100
        days = metrics.get('total_days', 0)
        doc_lines.append(f"| {code} | {name} | {sharpe_all:.4f} | {sharpe_1y:.4f} | {sharpe_ytd:.4f} | {ann_ret:.2f}% | {vol:.2f}% | {days} |")
    
    doc_lines.append("")
    
    # 统计分析
    doc_lines.append("## 五、统计分析")
    doc_lines.append("")
    
    sharpe_all_list = [r['metrics'].get('sharpe_all', 0) for r in all_results if 'metrics' in r and 'sharpe_all' in r['metrics']]
    sharpe_1y_list = [r['metrics'].get('sharpe_1y', 0) for r in all_results if 'metrics' in r and 'sharpe_1y' in r['metrics']]
    sharpe_ytd_list = [r['metrics'].get('sharpe_ytd', 0) for r in all_results if 'metrics' in r and 'sharpe_ytd' in r['metrics']]
    
    if sharpe_all_list:
        doc_lines.append("### 5.1 夏普比率分布")
        doc_lines.append("")
        doc_lines.append("| 统计项 | 夏普(全期) | 夏普(1年) | 夏普(YTD) |")
        doc_lines.append("|--------|------------|-----------|-----------|")
        doc_lines.append(f"| 平均值 | {np.mean(sharpe_all_list):.4f} | {np.mean(sharpe_1y_list):.4f} | {np.mean(sharpe_ytd_list):.4f} |")
        doc_lines.append(f"| 最大值 | {np.max(sharpe_all_list):.4f} | {np.max(sharpe_1y_list):.4f} | {np.max(sharpe_ytd_list):.4f} |")
        doc_lines.append(f"| 最小值 | {np.min(sharpe_all_list):.4f} | {np.min(sharpe_1y_list):.4f} | {np.min(sharpe_ytd_list):.4f} |")
        doc_lines.append(f"| 正数数量 | {sum(1 for x in sharpe_all_list if x > 0)} | {sum(1 for x in sharpe_1y_list if x > 0)} | {sum(1 for x in sharpe_ytd_list if x > 0)} |")
        doc_lines.append("")
    
    # 保存文档
    doc_content = "\n".join(doc_lines)
    output_file = "所有基金夏普比率计算详细说明.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(doc_content)
    
    print(f"\n文档已生成: {output_file}")
    print(f"共计算 {len(all_results)} 只基金")


if __name__ == '__main__':
    generate_document()
