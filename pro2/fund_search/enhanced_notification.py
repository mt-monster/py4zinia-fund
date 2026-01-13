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
import base64
import time

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
        self.last_send_time = 0  # 上次发送时间，用于频率控制
        self.min_interval = 5  # 最小发送间隔（秒）
    
    def _send_with_retry(self, url: str, payload: dict, max_retries: int = 3) -> dict:
        """
        发送请求并支持重试机制
        
        参数：
        url: 请求URL
        payload: 请求负载
        max_retries: 最大重试次数
        
        返回：
        dict: 响应结果
        """
        headers = {'Content-Type': 'application/json'}
        
        for attempt in range(max_retries):
            try:
                # 频率控制
                current_time = time.time()
                time_since_last = current_time - self.last_send_time
                if time_since_last < self.min_interval:
                    sleep_time = self.min_interval - time_since_last
                    logger.info(f"频率控制：等待 {sleep_time:.1f} 秒")
                    time.sleep(sleep_time)
                
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                self.last_send_time = time.time()
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 检查是否是频率限制错误
                    if result.get('code') == 999 and ('频率过快' in result.get('msg', '') or '服务端验证错误' in result.get('msg', '')):
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 5  # 递增等待时间
                            logger.warning(f"频率限制或服务端验证错误，等待 {wait_time} 秒后重试 (尝试 {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                            continue
                    
                    return result
                else:
                    logger.error(f"HTTP请求失败: {response.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    return {'code': response.status_code, 'msg': 'HTTP请求失败'}
                    
            except Exception as e:
                logger.error(f"请求异常 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return {'code': 500, 'msg': f'请求异常: {str(e)}'}
        
        return {'code': 500, 'msg': '达到最大重试次数'}
    
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
        生成HTML格式报告（匹配参考图片样式）
        """
        try:
            # 构建HTML表格
            html_table = self._format_fund_data_to_table(fund_data)
            
            # 格式化日期（将2026-01-13转换为2026年01月13日格式）
            try:
                date_obj = datetime.strptime(analysis_date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%Y年%m月%d日')
            except:
                formatted_date = analysis_date
            
            # 添加策略汇总信息（如果有）
            summary_html = ""
            if strategy_summary:
                summary_html = self._format_strategy_summary_to_html(strategy_summary)
            
            # 构建完整的HTML报告
            full_content = f"""
            <div style="font-family: Arial, sans-serif; margin: 20px;">
                <div style="display: flex; align-items: center; margin-bottom: 20px;">
                    <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 15px;">
                        <span style="color: white; font-size: 24px; font-weight: bold;">📊</span>
                    </div>
                    <h2 style="margin: 0; color: #333;">基金分析报告 - {formatted_date}</h2>
                </div>
                
                <h3 style="color: #555; border-bottom: 2px solid #e0e0e0; padding-bottom: 5px;">持仓基金收益率变化分析</h3>
                
                {html_table}
                
                {summary_html}
            </div>
            """
            
            return full_content
            
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
            
            # 发送POST请求 (支持更大的内容长度)
            url = f"https://www.pushplus.plus/send"
            payload = {
                'token': token,
                'title': title,
                'content': content,
                'template': template
            }
            
            result = self._send_with_retry(url, payload)
            
            if result.get('code') == 200:
                logger.info("微信通知发送成功")
                return True
            else:
                logger.error(f"微信通知发送失败: {result.get('msg', '未知错误')}")
                return False
                
        except Exception as e:
            logger.error(f"发送微信通知失败: {str(e)}")
            return False
    
    def send_email_notification(self, title: str, content: str, template: str = 'html') -> bool:
        """
        发送邮件通知
        
        参数：
        title: 邮件标题
        content: 邮件内容
        template: 模板类型，默认为html
        
        返回：
        bool: 发送是否成功
        """
        try:
            if not self.email_config.get('enabled', False):
                logger.info("邮件通知已禁用")
                return True
            
            token = self.email_config.get('token', '')  # 使用邮件配置中的token
            if not token:
                logger.warning("邮件token未配置")
                return False
            
            # 发送POST请求到PushPlus邮件接口（与微信通知使用相同的参数格式）
            url = f"https://www.pushplus.plus/send"
            data = {
                "token": token,
                "title": title,
                "content": content,
                "template": template,
                "channel": "mail"  # 指定为邮件渠道
            }
            
            result = self._send_with_retry(url, data)
            
            if result.get('code') == 200:
                logger.info("邮件通知发送成功")
                return True
            else:
                logger.error(f"邮件通知发送失败: {result.get('msg', '未知错误')}")
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
            
            # 发送邮件通知（使用HTML格式，与基金表格格式一致）
            email_title = f"📊 基金分析报告 - {analysis_date}"
            email_content = report_data.get('html', '报告生成失败')
            
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

    def send_fund_table_notification(self, fund_data: pd.DataFrame, title: str = "基金分析表格", 
                                   strategy_summary: Dict = None) -> bool:
        """
        发送基金数据表格到PushPlus
        
        参数：
        fund_data: 基金数据DataFrame
        title: 消息标题
        strategy_summary: 策略汇总数据（可选）
        
        返回：
        bool: 发送是否成功
        """
        try:
            if fund_data.empty:
                logger.warning("基金数据为空，无法发送表格")
                return True

            # 构建HTML表格
            html_table = self._format_fund_data_to_table(fund_data)
            
            # 添加策略汇总信息（如果有）
            summary_html = ""
            if strategy_summary:
                summary_html = self._format_strategy_summary_to_html(strategy_summary)
            
            # 添加表格标题和时间信息
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            full_content = f"""
            <h3>{title}</h3>
            <p><strong>生成时间:</strong> {current_time}</p>
            <p><strong>数据条数:</strong> {len(fund_data)} 条</p>
            {summary_html}
            {html_table}
            """
            
            # 发送通知
            wechat_success = self.send_wechat_notification(title, full_content, 'html')
            email_success = self.send_email_notification(title, full_content)
            
            return wechat_success or email_success
            
        except Exception as e:
            logger.error(f"发送基金表格通知失败: {str(e)}")
            return False

    def _format_fund_data_to_table(self, fund_data: pd.DataFrame) -> str:
        """
        将基金数据格式化为HTML表格（匹配参考图片样式）
        
        参数：
        fund_data: 基金数据DataFrame
        
        返回：
        str: HTML格式的表格
        """
        if fund_data.empty:
            return "<p>没有基金数据可显示</p>"
        
        # 选择要显示的列（与参考图片一致的顺序）
        display_columns = [
            'fund_code', 'fund_name', 'today_return', 'yesterday_return', 
            'trend_status', 'operation_suggestion', 'execute_amount'
        ]
        
        # 确保所需的列存在
        available_columns = [col for col in display_columns if col in fund_data.columns]
        
        # 创建HTML表格（匹配参考图片样式）
        html_table = """
        <div style="width: 100%; overflow-x: auto;">
        <table border="1" style="border-collapse: collapse; width: 100%; text-align: center; font-size: 12px;">
            <thead>
                <tr style="background-color: #f5f5f5; color: #333; font-weight: bold;">
        """
        
        # 添加表头
        for col in available_columns:
            display_name = self._get_column_display_name(col)
            html_table += f"<th style='padding: 6px; border: 1px solid #ddd;'>{display_name}</th>"
        
        html_table += "</tr></thead><tbody>"
        
        # 添加数据行
        for _, row in fund_data.iterrows():
            html_table += "<tr>"
            for col in available_columns:
                value = row[col] if col in row else "N/A"
                
                # 根据列类型格式化值
                if col in ['today_return', 'yesterday_return']:
                    # 百分比格式
                    if pd.notna(value):
                        formatted_value = f"{value*100:.2f}%"
                        # 根据数值正负设置颜色
                        color = '#FF6B6B' if value < 0 else '#4ECDC4' if value > 0 else 'black'
                        html_table += f"<td style='padding: 6px; border: 1px solid #ddd; color: {color};'>{formatted_value}</td>"
                    else:
                        html_table += "<td style='padding: 6px; border: 1px solid #ddd;'>N/A</td>"
                
                elif col == 'trend_status':
                    # 趋势状态格式化（带有颜色标识）
                    if pd.notna(value):
                        status = str(value)
                        # 根据趋势状态设置不同的颜色标识
                        if '连涨回落' in status or '反转转弱' in status:
                            icon = '<span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background-color: #FF6B6B; margin-right: 4px;"></span>'
                            color = '#FF6B6B'
                        elif '连涨放缓' in status:
                            icon = '<span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background-color: #FFA726; margin-right: 4px;"></span>'
                            color = '#FFA726'
                        elif '连涨加速' in status:
                            icon = '<span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background-color: #FFEE58; margin-right: 4px;"></span>'
                            color = '#FFEE58'
                        elif '大涨' in status:
                            icon = '<span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background-color: #66BB6A; margin-right: 4px;"></span>'
                            color = '#66BB6A'
                        else:
                            icon = '<span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background-color: #9E9E9E; margin-right: 4px;"></span>'
                            color = 'black'
                        html_table += f"<td style='padding: 6px; border: 1px solid #ddd; color: {color};'>{icon}{status}</td>"
                    else:
                        html_table += "<td style='padding: 6px; border: 1px solid #ddd;'>N/A</td>"
                
                elif col == 'operation_suggestion':
                    # 操作建议格式化
                    suggestion = str(value) if pd.notna(value) else "N/A"
                    # 根据建议内容设置颜色
                    if "买入" in suggestion or "持有" in suggestion:
                        color = "#4ECDC4"
                    elif "赎回" in suggestion or "卖出" in suggestion:
                        color = "#FF6B6B"
                    else:
                        color = "black"
                    html_table += f"<td style='padding: 6px; border: 1px solid #ddd; color: {color};'>{suggestion}</td>"
                
                elif col == 'execute_amount':
                    # 执行金额格式化
                    amount = str(value) if pd.notna(value) else "N/A"
                    # 根据金额内容设置颜色
                    if "赎回" in amount:
                        color = "#FF6B6B"
                    else:
                        color = "black"
                    html_table += f"<td style='padding: 6px; border: 1px solid #ddd; color: {color};'>{amount}</td>"
                
                else:
                    # 普通文本格式
                    html_table += f"<td style='padding: 6px; border: 1px solid #ddd;'>{value if pd.notna(value) else 'N/A'}</td>"
            
            html_table += "</tr>"
        
        html_table += "</tbody></table></div>"
        return html_table

    def _format_strategy_summary_to_html(self, strategy_summary: Dict) -> str:
        """
        将策略汇总格式化为HTML
        
        参数：
        strategy_summary: 策略汇总数据
        
        返回：
        str: HTML格式的汇总信息
        """
        if not strategy_summary:
            return ""
        
        html_content = "<div style='margin: 15px 0; padding: 10px; background-color: #f5f5f5; border-radius: 5px;'><h4>📊 策略汇总</h4><ul>"
        
        # 添加操作分布
        if 'action_distribution' in strategy_summary:
            html_content += "<li><strong>操作分布:</strong> "
            for action, count in strategy_summary['action_distribution'].items():
                html_content += f"{action}: {count} 只, "
            html_content = html_content.rstrip(', ') + "</li>"
        
        # 添加平均买入倍数
        if 'avg_buy_multiplier' in strategy_summary:
            html_content += f"<li><strong>平均买入倍数:</strong> {strategy_summary['avg_buy_multiplier']:.2f}</li>"
        
        # 添加总赎回金额
        if 'total_redeem_amount' in strategy_summary:
            html_content += f"<li><strong>总赎回金额:</strong> ¥{strategy_summary['total_redeem_amount']}</li>"
        
        # 添加信号统计
        if 'buy_signals' in strategy_summary:
            html_content += f"<li><strong>买入信号:</strong> {strategy_summary['buy_signals']} 只</li>"
        if 'sell_signals' in strategy_summary:
            html_content += f"<li><strong>卖出信号:</strong> {strategy_summary['sell_signals']} 只</li>"
        if 'hold_signals' in strategy_summary:
            html_content += f"<li><strong>持有信号:</strong> {strategy_summary['hold_signals']} 只</li>"
        
        html_content += "</ul></div>"
        return html_content

    def _get_column_display_name(self, column_name: str) -> str:
        """获取列的显示名称"""
        column_names = {
            'fund_code': '基金代码',
            'fund_name': '基金名称',
            'today_return': '今日收益率',
            'yesterday_return': '昨日收益率',
            'trend_status': '趋势状态',
            'operation_suggestion': '操作建议',
            'execute_amount': '执行金额',
            'annualized_return': '年化收益率',
            'sharpe_ratio': '夏普比率',
            'max_drawdown': '最大回撤',
            'volatility': '波动率',
            'win_rate': '胜率',
            'composite_score': '综合评分'
        }
        return column_names.get(column_name, column_name)


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