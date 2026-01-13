#!/usr/bin/env python
# coding: utf-8

"""
增强版通知和邮件模块
提供专业的基金分析报告生成和发送功能
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import logging
import requests
import json

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnhancedNotificationManager:
    """增强版通知管理类"""
    
    def __init__(self, notification_config: Dict):
        """
        初始化通知管理器
        
        参数：
        notification_config: 通知配置字典
        """
        self.config = notification_config
        self.wechat_config = notification_config.get('wechat', {})
        self.email_config = notification_config.get('email', {})
    
    def generate_comprehensive_report(self, fund_data: pd.DataFrame, strategy_summary: Dict, 
                                    report_files: Dict, analysis_date: str) -> Dict:
        """
        生成综合基金分析报告
        
        参数：
        fund_data: 基金数据DataFrame
        strategy_summary: 策略汇总字典
        report_files: 报告文件字典
        analysis_date: 分析日期
        
        返回：
        dict: 报告内容
        """
        try:
            # 生成HTML报告
            html_report = self._generate_html_report(fund_data, strategy_summary, report_files, analysis_date)
            
            # 生成文本报告
            text_report = self._generate_text_report(fund_data, strategy_summary, analysis_date)
            
            # 生成Markdown报告
            markdown_report = self._generate_markdown_report(fund_data, strategy_summary, report_files, analysis_date)
            
            return {
                'html': html_report,
                'text': text_report,
                'markdown': markdown_report,
                'analysis_date': analysis_date,
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"生成综合报告失败: {str(e)}")
            return {
                'html': '<p>报告生成失败</p>',
                'text': '报告生成失败',
                'markdown': '报告生成失败',
                'analysis_date': analysis_date,
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def _generate_html_report(self, fund_data: pd.DataFrame, strategy_summary: Dict, 
                             report_files: Dict, analysis_date: str) -> str:
        """
        生成HTML格式报告
        """
        try:
            # 获取关键统计数据
            total_funds = len(fund_data)
            avg_annualized_return = fund_data['annualized_return'].mean() if 'annualized_return' in fund_data.columns else 0
            avg_sharpe_ratio = fund_data['sharpe_ratio'].mean() if 'sharpe_ratio' in fund_data.columns else 0
            avg_max_drawdown = fund_data['max_drawdown'].mean() if 'max_drawdown' in fund_data.columns else 0
            avg_composite_score = fund_data['composite_score'].mean() if 'composite_score' in fund_data.columns else 0
            
            # 获取最佳和最差基金
            if not fund_data.empty:
                best_fund = fund_data.loc[fund_data['composite_score'].idxmax()] if 'composite_score' in fund_data.columns else fund_data.iloc[0]
                worst_fund = fund_data.loc[fund_data['composite_score'].idxmin()] if 'composite_score' in fund_data.columns else fund_data.iloc[-1]
            else:
                best_fund = None
                worst_fund = None
            
            # 生成HTML报告
            html_content = f"""
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>基金分析报告 - {analysis_date}</title>
                <style>
                    body {{
                        font-family: 'Microsoft YaHei', Arial, sans-serif;
                        line-height: 1.6;
                        margin: 0;
                        padding: 20px;
                        background-color: #f5f5f5;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                        background-color: white;
                        padding: 30px;
                        border-radius: 10px;
                        box-shadow: 0 0 20px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        text-align: center;
                        border-bottom: 3px solid #4CAF50;
                        padding-bottom: 20px;
                        margin-bottom: 30px;
                    }}
                    .header h1 {{
                        color: #2E7D32;
                        font-size: 2.5em;
                        margin: 0;
                    }}
                    .header .date {{
                        color: #666;
                        font-size: 1.2em;
                        margin-top: 10px;
                    }}
                    .summary-cards {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                        gap: 20px;
                        margin-bottom: 30px;
                    }}
                    .card {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 20px;
                        border-radius: 10px;
                        text-align: center;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    }}
                    .card h3 {{
                        margin: 0 0 10px 0;
                        font-size: 1.1em;
                    }}
                    .card .value {{
                        font-size: 2em;
                        font-weight: bold;
                        margin: 10px 0;
                    }}
                    .section {{
                        margin-bottom: 40px;
                    }}
                    .section h2 {{
                        color: #2E7D32;
                        border-left: 5px solid #4CAF50;
                        padding-left: 15px;
                        font-size: 1.5em;
                    }}
                    .fund-table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 20px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }}
                    .fund-table th {{
                        background-color: #4CAF50;
                        color: white;
                        padding: 12px;
                        text-align: center;
                        font-weight: bold;
                    }}
                    .fund-table td {{
                        padding: 10px;
                        text-align: center;
                        border-bottom: 1px solid #ddd;
                    }}
                    .fund-table tr:nth-child(even) {{
                        background-color: #f9f9f9;
                    }}
                    .fund-table tr:hover {{
                        background-color: #e8f5e8;
                    }}
                    .positive {{ color: #2E7D32; font-weight: bold; }}
                    .negative {{ color: #D32F2F; font-weight: bold; }}
                    .neutral {{ color: #666; }}
                    .strategy-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 15px;
                        margin-top: 20px;
                    }}
                    .strategy-item {{
                        background-color: #f8f9fa;
                        padding: 15px;
                        border-radius: 8px;
                        border-left: 4px solid #4CAF50;
                    }}
                    .chart-container {{
                        text-align: center;
                        margin: 20px 0;
                    }}
                    .chart-container img {{
                        max-width: 100%;
                        height: auto;
                        border-radius: 8px;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    }}
                    .recommendation {{
                        background-color: #e8f5e8;
                        border: 2px solid #4CAF50;
                        border-radius: 10px;
                        padding: 20px;
                        margin: 20px 0;
                    }}
                    .recommendation h3 {{
                        color: #2E7D32;
                        margin-top: 0;
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 40px;
                        padding-top: 20px;
                        border-top: 2px solid #e0e0e0;
                        color: #666;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📊 基金投资分析报告</h1>
                        <div class="date">分析日期: {analysis_date}</div>
                        <div class="date">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                    </div>
                    
                    <div class="summary-cards">
                        <div class="card">
                            <h3>分析基金数量</h3>
                            <div class="value">{total_funds}</div>
                        </div>
                        <div class="card">
                            <h3>平均年化收益率</h3>
                            <div class="value">{avg_annualized_return*100:.2f}%</div>
                        </div>
                        <div class="card">
                            <h3>平均夏普比率</h3>
                            <div class="value">{avg_sharpe_ratio:.3f}</div>
                        </div>
                        <div class="card">
                            <h3>平均最大回撤</h3>
                            <div class="value">{avg_max_drawdown*100:.2f}%</div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>📈 策略信号汇总</h2>
                        <div class="strategy-grid">
            """
            
            # 添加策略信号统计
            if strategy_summary:
                for action, count in strategy_summary.get('action_distribution', {}).items():
                    html_content += f"""
                            <div class="strategy-item">
                                <strong>{action}</strong><br>
                                <span style="font-size: 1.2em; color: #4CAF50;">{count}</span> 只基金
                            </div>
                    """
            
            html_content += f"""
                        </div>
                        <div style="margin-top: 20px;">
                            <strong>平均买入倍数:</strong> {strategy_summary.get('avg_buy_multiplier', 0):.2f}<br>
                            <strong>总赎回金额:</strong> ¥{strategy_summary.get('total_redeem_amount', 0)}
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>🏆 最佳表现基金</h2>
            """
            
            # 添加最佳基金信息
            if best_fund is not None:
                html_content += f"""
                        <div class="recommendation">
                            <h3>🥇 综合评分最高</h3>
                            <p><strong>基金代码:</strong> {best_fund.get('fund_code', 'N/A')}</p>
                            <p><strong>基金名称:</strong> {best_fund.get('fund_name', 'N/A')}</p>
                            <p><strong>年化收益率:</strong> <span class="positive">{best_fund.get('annualized_return', 0)*100:.2f}%</span></p>
                            <p><strong>夏普比率:</strong> {best_fund.get('sharpe_ratio', 0):.3f}</p>
                            <p><strong>综合评分:</strong> <span class="positive">{best_fund.get('composite_score', 0):.3f}</span></p>
                        </div>
                """
            
            # 添加最差基金信息
            if worst_fund is not None:
                html_content += f"""
                        <div style="background-color: #ffebee; border: 2px solid #f44336; border-radius: 10px; padding: 20px; margin: 20px 0;">
                            <h3 style="color: #d32f2f; margin-top: 0;">⚠️ 需要关注基金</h3>
                            <p><strong>基金代码:</strong> {worst_fund.get('fund_code', 'N/A')}</p>
                            <p><strong>基金名称:</strong> {worst_fund.get('fund_name', 'N/A')}</p>
                            <p><strong>年化收益率:</strong> <span class="negative">{worst_fund.get('annualized_return', 0)*100:.2f}%</span></p>
                            <p><strong>夏普比率:</strong> {worst_fund.get('sharpe_ratio', 0):.3f}</p>
                            <p><strong>综合评分:</strong> <span class="negative">{worst_fund.get('composite_score', 0):.3f}</span></p>
                        </div>
                """
            
            # 添加基金详细表格
            html_content += f"""
                    </div>
                    
                    <div class="section">
                        <h2>📋 基金详细分析</h2>
                        <table class="fund-table">
                            <thead>
                                <tr>
                                    <th>基金代码</th>
                                    <th>基金名称</th>
                                    <th>日收益</th>
                                    <th>年化收益</th>
                                    <th>夏普比率</th>
                                    <th>最大回撤</th>
                                    <th>波动率</th>
                                    <th>胜率</th>
                                    <th>综合评分</th>
                                    <th>操作建议</th>
                                </tr>
                            </thead>
                            <tbody>
            """
            
            # 添加基金数据行
            for _, fund in fund_data.iterrows():
                daily_return_class = 'positive' if fund.get('daily_return', 0) > 0 else 'negative' if fund.get('daily_return', 0) < 0 else 'neutral'
                annualized_return_class = 'positive' if fund.get('annualized_return', 0) > 0 else 'negative' if fund.get('annualized_return', 0) < 0 else 'neutral'
                
                html_content += f"""
                                <tr>
                                    <td>{fund.get('fund_code', 'N/A')}</td>
                                    <td>{fund.get('fund_name', 'N/A')}</td>
                                    <td class="{daily_return_class}">{fund.get('daily_return', 0)*100:.2f}%</td>
                                    <td class="{annualized_return_class}">{fund.get('annualized_return', 0)*100:.2f}%</td>
                                    <td>{fund.get('sharpe_ratio', 0):.3f}</td>
                                    <td class="negative">{fund.get('max_drawdown', 0)*100:.2f}%</td>
                                    <td>{fund.get('volatility', 0)*100:.2f}%</td>
                                    <td>{fund.get('win_rate', 0)*100:.1f}%</td>
                                    <td>{fund.get('composite_score', 0):.3f}</td>
                                    <td>{fund.get('operation_suggestion', 'N/A')}</td>
                                </tr>
                """
            
            html_content += f"""
                            </tbody>
                        </table>
                    </div>
                    
                    <div class="section">
                        <h2>📊 分析图表</h2>
                        <div class="chart-container">
                            <p><strong>绩效概览图表:</strong> {report_files.get('performance_overview', '未生成')}</p>
                            <p><strong>收益率分析图表:</strong> {report_files.get('return_analysis', '未生成')}</p>
                            <p><strong>风险分析图表:</strong> {report_files.get('risk_analysis', '未生成')}</p>
                            <p><strong>综合评分图表:</strong> {report_files.get('composite_score', '未生成')}</p>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>💡 投资建议</h2>
                        <div class="recommendation">
                            <h3>基于本次分析的建议:</h3>
                            <ul>
                                <li><strong>买入信号基金:</strong> 关注综合评分高、夏普比率良好的基金</li>
                                <li><strong>卖出信号基金:</strong> 考虑适当减仓或转换投资标的</li>
                                <li><strong>持有观望:</strong> 继续观察基金表现，等待更好的投资时机</li>
                                <li><strong>风险控制:</strong> 注意最大回撤较大的基金，控制投资风险</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p>本报告基于历史数据和技术分析，仅供参考，不构成投资建议</p>
                        <p>投资有风险，入市需谨慎</p>
                        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return html_content
            
        except Exception as e:
            logger.error(f"生成HTML报告失败: {str(e)}")
            return f"<p>报告生成失败: {str(e)}</p>"
    
    def _generate_text_report(self, fund_data: pd.DataFrame, strategy_summary: Dict, analysis_date: str) -> str:
        """
        生成文本格式报告
        """
        try:
            total_funds = len(fund_data)
            avg_annualized_return = fund_data['annualized_return'].mean() if 'annualized_return' in fund_data.columns else 0
            avg_sharpe_ratio = fund_data['sharpe_ratio'].mean() if 'sharpe_ratio' in fund_data.columns else 0
            
            text_content = f"""
基金投资分析报告
================

分析日期: {analysis_date}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 总体概况
--------
分析基金数量: {total_funds}
平均年化收益率: {avg_annualized_return*100:.2f}%
平均夏普比率: {avg_sharpe_ratio:.3f}

📈 策略信号统计
------------
"""
            
            if strategy_summary:
                for action, count in strategy_summary.get('action_distribution', {}).items():
                    text_content += f"{action}: {count} 只基金\n"
                
                text_content += f"平均买入倍数: {strategy_summary.get('avg_buy_multiplier', 0):.2f}\n"
                text_content += f"总赎回金额: ¥{strategy_summary.get('total_redeem_amount', 0)}\n"
            
            # 添加最佳和最差基金
            if not fund_data.empty:
                best_fund = fund_data.loc[fund_data['composite_score'].idxmax()] if 'composite_score' in fund_data.columns else fund_data.iloc[0]
                worst_fund = fund_data.loc[fund_data['composite_score'].idxmin()] if 'composite_score' in fund_data.columns else fund_data.iloc[-1]
                
                text_content += f"""

🏆 最佳表现基金
-------------
基金代码: {best_fund.get('fund_code', 'N/A')}
基金名称: {best_fund.get('fund_name', 'N/A')}
年化收益率: {best_fund.get('annualized_return', 0)*100:.2f}%
夏普比率: {best_fund.get('sharpe_ratio', 0):.3f}
综合评分: {best_fund.get('composite_score', 0):.3f}

⚠️  需要关注基金
---------------
基金代码: {worst_fund.get('fund_code', 'N/A')}
基金名称: {worst_fund.get('fund_name', 'N/A')}
年化收益率: {worst_fund.get('annualized_return', 0)*100:.2f}%
夏普比率: {worst_fund.get('sharpe_ratio', 0):.3f}
综合评分: {worst_fund.get('composite_score', 0):.3f}

📋 基金详细数据
-------------
"""
            
            # 添加基金详细数据
            for _, fund in fund_data.iterrows():
                text_content += f"""
基金代码: {fund.get('fund_code', 'N/A')}
基金名称: {fund.get('fund_name', 'N/A')}
日收益率: {fund.get('daily_return', 0)*100:.2f}%
年化收益率: {fund.get('annualized_return', 0)*100:.2f}%
夏普比率: {fund.get('sharpe_ratio', 0):.3f}
最大回撤: {fund.get('max_drawdown', 0)*100:.2f}%
波动率: {fund.get('volatility', 0)*100:.2f}%
胜率: {fund.get('win_rate', 0)*100:.1f}%
综合评分: {fund.get('composite_score', 0):.3f}
操作建议: {fund.get('operation_suggestion', 'N/A')}
{'-' * 40}
"""
            
            text_content += f"""

💡 投资建议
---------
1. 关注综合评分高、夏普比率良好的基金
2. 注意最大回撤较大的基金，控制投资风险
3. 根据策略信号调整投资组合
4. 定期review投资表现，及时调整策略

⚠️  风险提示
---------
本报告基于历史数据和技术分析，仅供参考
投资有风险，入市需谨慎
请结合自身风险承受能力做出投资决策

报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            return text_content.strip()
            
        except Exception as e:
            logger.error(f"生成文本报告失败: {str(e)}")
            return f"报告生成失败: {str(e)}"
    
    def _generate_markdown_report(self, fund_data: pd.DataFrame, strategy_summary: Dict, 
                                 report_files: Dict, analysis_date: str) -> str:
        """
        生成Markdown格式报告
        """
        try:
            total_funds = len(fund_data)
            avg_annualized_return = fund_data['annualized_return'].mean() if 'annualized_return' in fund_data.columns else 0
            avg_sharpe_ratio = fund_data['sharpe_ratio'].mean() if 'sharpe_ratio' in fund_data.columns else 0
            
            markdown_content = f"""# 📊 基金投资分析报告

**分析日期:** {analysis_date}  
**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📈 总体概况

| 指标 | 数值 |
|------|------|
| 分析基金数量 | {total_funds} |
| 平均年化收益率 | {avg_annualized_return*100:.2f}% |
| 平均夏普比率 | {avg_sharpe_ratio:.3f} |

## 🎯 策略信号统计

"""
            
            # 添加策略信号统计
            if strategy_summary:
                markdown_content += "| 操作类型 | 基金数量 |\n"
                markdown_content += "|----------|----------|\n"
                for action, count in strategy_summary.get('action_distribution', {}).items():
                    markdown_content += f"| {action} | {count} |\n"
                
                markdown_content += f"\n**平均买入倍数:** {strategy_summary.get('avg_buy_multiplier', 0):.2f}  \n"
                markdown_content += f"**总赎回金额:** ¥{strategy_summary.get('total_redeem_amount', 0)}\n\n"
            
            # 添加最佳和最差基金
            if not fund_data.empty:
                best_fund = fund_data.loc[fund_data['composite_score'].idxmax()] if 'composite_score' in fund_data.columns else fund_data.iloc[0]
                worst_fund = fund_data.loc[fund_data['composite_score'].idxmin()] if 'composite_score' in fund_data.columns else fund_data.iloc[-1]
                
                markdown_content += f"""## 🏆 最佳表现基金

| 项目 | 数值 |
|------|------|
| 基金代码 | {best_fund.get('fund_code', 'N/A')} |
| 基金名称 | {best_fund.get('fund_name', 'N/A')} |
| 年化收益率 | {best_fund.get('annualized_return', 0)*100:.2f}% |
| 夏普比率 | {best_fund.get('sharpe_ratio', 0):.3f} |
| 综合评分 | {best_fund.get('composite_score', 0):.3f} |

## ⚠️ 需要关注基金

| 项目 | 数值 |
|------|------|
| 基金代码 | {worst_fund.get('fund_code', 'N/A')} |
| 基金名称 | {worst_fund.get('fund_name', 'N/A')} |
| 年化收益率 | {worst_fund.get('annualized_return', 0)*100:.2f}% |
| 夏普比率 | {worst_fund.get('sharpe_ratio', 0):.3f} |
| 综合评分 | {worst_fund.get('composite_score', 0):.3f} |

## 📊 基金详细分析

| 基金代码 | 基金名称 | 日收益 | 年化收益 | 夏普比率 | 最大回撤 | 波动率 | 胜率 | 综合评分 | 操作建议 |
|----------|----------|--------|----------|----------|----------|--------|------|----------|----------|
"""
            
            # 添加基金详细数据
            for _, fund in fund_data.iterrows():
                markdown_content += f"| {fund.get('fund_code', 'N/A')} | {fund.get('fund_name', 'N/A')} | "
                markdown_content += f"{fund.get('daily_return', 0)*100:.2f}% | {fund.get('annualized_return', 0)*100:.2f}% | "
                markdown_content += f"{fund.get('sharpe_ratio', 0):.3f} | {fund.get('max_drawdown', 0)*100:.2f}% | "
                markdown_content += f"{fund.get('volatility', 0)*100:.2f}% | {fund.get('win_rate', 0)*100:.1f}% | "
                markdown_content += f"{fund.get('composite_score', 0):.3f} | {fund.get('operation_suggestion', 'N/A')} |\n"
            
            # 添加图表链接
            markdown_content += f"""
## 📈 分析图表

- **绩效概览图表:** `{report_files.get('performance_overview', '未生成')}`
- **收益率分析图表:** `{report_files.get('return_analysis', '未生成')}`
- **风险分析图表:** `{report_files.get('risk_analysis', '未生成')}`
- **综合评分图表:** `{report_files.get('composite_score', '未生成')}`

## 💡 投资建议

### ✅ 推荐操作
1. **买入信号基金**: 关注综合评分高、夏普比率良好的基金
2. **持有观望**: 继续观察基金表现，等待更好的投资时机
3. **分散投资**: 不要将所有资金投入单一基金

### ⚠️ 风险提示
1. **最大回撤较大基金**: 注意控制投资风险
2. **高波动率基金**: 谨慎操作，考虑风险承受能力
3. **胜率较低基金**: 减少投资比例或避免投资

### 📊 策略建议
- 根据策略信号调整投资组合
- 定期review投资表现，及时调整策略
- 结合自身风险承受能力做出投资决策

---

**⚠️ 免责声明**

本报告基于历史数据和技术分析，仅供参考，不构成投资建议。投资有风险，入市需谨慎。请结合自身风险承受能力做出投资决策。

**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            return markdown_content.strip()
            
        except Exception as e:
            logger.error(f"生成Markdown报告失败: {str(e)}")
            return f"报告生成失败: {str(e)}"
    
    def send_wechat_notification(self, title: str, content: str, template: str = 'html') -> bool:
        """
        发送微信通知
        
        参数：
        title: 通知标题
        content: 通知内容
        template: 模板类型
        
        返回：
        bool: 发送是否成功
        """
        try:
            if not self.wechat_config.get('enabled', False):
                logger.info("微信通知已禁用")
                return True
            
            token = self.wechat_config.get('token', '')
            if not token:
                logger.warning("微信token未配置")
                return False
            
            # 发送GET请求
            url = f"https://www.pushplus.plus/send"
            params = {
                'token': token,
                'title': title,
                'content': content,
                'template': template
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 200:
                    logger.info("微信通知发送成功")
                    return True
                else:
                    logger.error(f"微信通知发送失败: {result.get('msg', '未知错误')}")
                    return False
            else:
                logger.error(f"微信通知请求失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"发送微信通知失败: {str(e)}")
            return False
    
    def send_email_notification(self, title: str, content: str, channel: str = 'mail') -> bool:
        """
        发送邮件通知
        
        参数：
        title: 邮件标题
        content: 邮件内容
        channel: 发送渠道
        
        返回：
        bool: 发送是否成功
        """
        try:
            if not self.email_config.get('enabled', False):
                logger.info("邮件通知已禁用")
                return True
            
            token = self.wechat_config.get('token', '')  # 使用微信token，因为PushPlus统一使用token
            if not token:
                logger.warning("邮件token未配置")
                return False
            
            # 发送POST请求
            url = f"http://www.pushplus.plus/send/{token}"
            headers = {'Content-Type': 'application/json'}
            data = {
                "token": token,
                "title": title,
                "content": content,
                "channel": channel,
                "option": ""
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 200:
                    logger.info("邮件通知发送成功")
                    return True
                else:
                    logger.error(f"邮件通知发送失败: {result.get('msg', '未知错误')}")
                    return False
            else:
                logger.error(f"邮件通知请求失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"发送邮件通知失败: {str(e)}")
            return False
    
    def send_comprehensive_notification(self, report_data: Dict, report_files: Dict) -> bool:
        """
        发送综合通知
        
        参数：
        report_data: 报告数据
        report_files: 报告文件
        
        返回：
        bool: 发送是否成功
        """
        try:
            analysis_date = report_data.get('analysis_date', datetime.now().strftime('%Y-%m-%d'))
            
            # 发送微信通知（使用HTML格式）
            wechat_title = f"📊 基金分析报告 - {analysis_date}"
            wechat_content = report_data.get('html', '报告生成失败')
            
            wechat_success = self.send_wechat_notification(wechat_title, wechat_content, 'html')
            
            # 发送邮件通知（使用文本格式）
            email_title = f"基金投资分析报告 - {analysis_date}"
            email_content = report_data.get('text', '报告生成失败')
            
            email_success = self.send_email_notification(email_title, email_content)
            
            # 记录发送结果
            if wechat_success and email_success:
                logger.info("综合通知发送成功")
                return True
            elif wechat_success:
                logger.warning("微信通知发送成功，邮件通知发送失败")
                return True
            elif email_success:
                logger.warning("邮件通知发送成功，微信通知发送失败")
                return True
            else:
                logger.error("所有通知发送失败")
                return False
                
        except Exception as e:
            logger.error(f"发送综合通知失败: {str(e)}")
            return False
    
    def send_simple_notification(self, title: str, message: str) -> bool:
        """
        发送简单通知
        
        参数：
        title: 标题
        message: 消息内容
        
        返回：
        bool: 发送是否成功
        """
        try:
            # 同时发送微信和邮件通知
            wechat_success = self.send_wechat_notification(title, message, 'html')
            email_success = self.send_email_notification(title, message)
            
            return wechat_success or email_success
            
        except Exception as e:
            logger.error(f"发送简单通知失败: {str(e)}")
            return False


if __name__ == "__main__":
    # 测试代码
    from enhanced_config import NOTIFICATION_CONFIG
    
    # 创建通知管理器
    notification_manager = EnhancedNotificationManager(NOTIFICATION_CONFIG)
    
    # 创建测试数据
    test_fund_data = pd.DataFrame({
        'fund_code': ['000001', '000002', '000003'],
        'fund_name': ['测试基金1', '测试基金2', '测试基金3'],
        'daily_return': [0.5, 1.2, -0.8],
        'annualized_return': [0.15, 0.25, -0.05],
        'sharpe_ratio': [1.2, 1.8, -0.2],
        'max_drawdown': [-0.08, -0.12, -0.25],
        'volatility': [0.12, 0.14, 0.22],
        'win_rate': [0.65, 0.72, 0.45],
        'composite_score': [0.72, 0.85, 0.35],
        'operation_suggestion': ['适量买入', '积极买入', '谨慎观望']
    })
    
    test_strategy_summary = {
        'action_distribution': {'buy': 2, 'hold': 1},
        'avg_buy_multiplier': 1.5,
        'total_redeem_amount': 0
    }
    
    test_report_files = {
        'performance_overview': 'test_performance.png',
        'return_analysis': 'test_return.png'
    }
    
    # 测试报告生成
    print("测试生成综合报告:")
    report_data = notification_manager.generate_comprehensive_report(
        test_fund_data, test_strategy_summary, test_report_files, '2024-01-01'
    )
    
    print(f"报告生成状态: {report_data['generated_at']}")
    print(f"HTML报告长度: {len(report_data['html'])} 字符")
    print(f"文本报告长度: {len(report_data['text'])} 字符")
    print(f"Markdown报告长度: {len(report_data['markdown'])} 字符")
    
    # 测试简单通知
    print("\n测试发送简单通知:")
    success = notification_manager.send_simple_notification(
        "测试通知", 
        "这是一个测试通知消息"
    )
    print(f"简单通知发送结果: {success}")
    
    # 测试综合通知
    print("\n测试发送综合通知:")
    success = notification_manager.send_comprehensive_notification(report_data, test_report_files)
    print(f"综合通知发送结果: {success}")