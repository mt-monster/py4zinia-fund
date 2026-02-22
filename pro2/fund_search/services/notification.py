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
import re
import base64
import time
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# 只获取logger，不配置basicConfig（由主程序配置）
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
日收益率: {fund.get('today_return', 0)*100:.2f}%
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
                markdown_content += f"{fund.get('today_return', 0)*100:.2f}% | {fund.get('annualized_return', 0)*100:.2f}% | "
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
    
    def save_html_report(self, title: str, content: str, filename_prefix: str = "report") -> str:
        """
        将报告保存为本地HTML文件
        
        参数：
        title: 报告标题
        content: 报告内容（HTML）
        filename_prefix: 文件名前缀
        
        返回：
        str: 保存的文件路径，失败则返回空字符串
        """
        try:
            # 使用统一的reports目录（项目根目录）
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            reports_dir = os.path.join(project_root, 'reports')
            if not os.path.exists(reports_dir):
                os.makedirs(reports_dir)
                
            # 生成文件名
            current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{filename_prefix}_{current_time}.html"
            file_path = os.path.join(reports_dir, filename)
            
            # 确保内容包含基本的HTML结构（如果尚未包含）
            if "<html" not in content.lower():
                full_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>{title}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                        th {{ background-color: #f2f2f2; }}
                        tr:nth-child(even) {{ background-color: #f9f9f9; }}
                        .container {{ max-width: 1200px; margin: 0 auto; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>{title}</h1>
                        {content}
                    </div>
                </body>
                </html>
                """
            else:
                full_content = content
                
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
                
            logger.info(f"HTML报告已保存至: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"保存HTML报告失败: {str(e)}")
            return ""

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
    
    def _send_via_smtp(self, title: str, content: str, template: str = 'html') -> bool:
        """
        通过SMTP发送邮件
        """
        try:
            smtp_host = self.email_config.get('smtp_host')
            smtp_port = self.email_config.get('smtp_port')
            smtp_user = self.email_config.get('smtp_user')
            smtp_password = self.email_config.get('smtp_password')
            receivers = self.email_config.get('smtp_receivers')
            
            if not all([smtp_host, smtp_port, smtp_user, smtp_password, receivers]):
                logger.warning("SMTP配置不完整，无法发送邮件。请在配置文件中设置 smtp_host, smtp_port, smtp_user, smtp_password, smtp_receivers")
                return False
                
            message = MIMEMultipart()
            message['From'] = Header(f"基金分析助手 <{smtp_user}>", 'utf-8')
            # 如果receivers是列表，将其转换为逗号分隔的字符串用于Header，但sendmail需要列表
            if isinstance(receivers, list):
                receivers_list = receivers
                receivers_str = ",".join(receivers)
            else:
                receivers_list = [receivers]
                receivers_str = receivers
                
            message['To'] = Header(receivers_str, 'utf-8')
            message['Subject'] = Header(title, 'utf-8')
            
            if template == 'html':
                message.attach(MIMEText(content, 'html', 'utf-8'))
            else:
                message.attach(MIMEText(content, 'plain', 'utf-8'))
                
            try:
                if smtp_port == 465:
                    smtp = smtplib.SMTP_SSL(smtp_host, smtp_port)
                else:
                    smtp = smtplib.SMTP(smtp_host, smtp_port)
                    # 尝试启动TLS，如果服务器支持
                    try:
                        smtp.starttls()
                    except:
                        pass
                    
                smtp.login(smtp_user, smtp_password)
                smtp.sendmail(smtp_user, receivers_list, message.as_string())
                smtp.quit()
                logger.info("SMTP邮件发送成功")
                return True
            except Exception as e:
                logger.error(f"SMTP连接或发送失败: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"构建SMTP邮件失败: {str(e)}")
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
            
            # 检查发送渠道
            channel = self.email_config.get('channel', 'mail')
            if channel == 'smtp':
                return self._send_via_smtp(title, content, template)
            
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
            
            # 如果发送失败，或者为了备份，保存本地HTML
            if not email_success:
                logger.warning("邮件发送失败，正在生成本地HTML报告...")
                self.save_html_report(email_title, email_content, "fund_analysis_report")
            
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
            
            # 如果发送失败，保存本地HTML
            if not email_success:
                logger.warning("邮件发送失败，正在生成本地HTML报告...")
                self.save_html_report(title, full_content, "fund_table_report")
            
            return wechat_success or email_success
            
        except Exception as e:
            logger.error(f"发送基金表格通知失败: {str(e)}")
            return False
    
    def send_performance_analysis_email(self, performance_data: pd.DataFrame, title: str = None) -> bool:
        """
        发送基金绩效分析结果邮件
        
        参数：
        performance_data: 基金绩效分析数据DataFrame
        title: 邮件标题（可选）
        
        返回：
        bool: 发送是否成功
        """
        try:
            if performance_data.empty:
                logger.warning("绩效分析数据为空，无法发送邮件")
                return True
            
            # 设置邮件标题（与图片完全一致）
            if not title:
                current_date = datetime.now().strftime('%Y-%m-%d')
                title = f"[测试] 基金绩效分析报告 - {current_date}"
            
            # 构建专业的HTML表格
            html_table = self._format_performance_data_to_table(performance_data)
            
            # 生成策略汇总信息
            strategy_summary = self._generate_performance_summary(performance_data)
            summary_html = self._format_strategy_summary_to_html(strategy_summary)
            
            # 添加报告标题和时间信息
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 构建完整的HTML邮件内容
            full_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto;">
                <h2 style="color: #2c3e50; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                    {title}
                </h2>
                
                <div style="background-color: #f8f9fa; padding: 15px; margin: 20px 0; border-radius: 5px;">
                    <p style="margin: 5px 0;"><strong>生成时间:</strong> {current_time}</p>
                    <p style="margin: 5px 0;"><strong>分析基金数量:</strong> {len(performance_data)} 只</p>
                    <p style="margin: 5px 0;"><strong>报告类型:</strong> 专业绩效分析</p>
                </div>
                
                {summary_html}
                
                <h3 style="color: #2c3e50; margin-top: 30px;">📈 基金绩效分析详情</h3>
                <div style="margin: 20px 0;">{html_table}</div>
                
                <div style="border-top: 1px solid #ecf0f1; padding-top: 15px; margin-top: 30px; font-size: 12px; color: #7f8c8d;">
                    <p>📋 <strong>备注:</strong></p>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>绩效数据基于历史表现计算，不代表未来收益</li>
                        <li>夏普比率、卡尔玛比率等指标用于风险调整收益评估</li>
                        <li>最大回撤率反映基金历史最大跌幅</li>
                        <li>操作建议仅供参考，请结合自身投资策略决策</li>
                    </ul>
                </div>
            </div>
            """
            
            # 发送邮件通知（使用专业的绩效分析模板）
            email_success = self.send_email_notification(title, full_content)
            
            # 如果发送失败，保存本地HTML
            if not email_success:
                logger.warning("邮件发送失败，正在生成本地HTML报告...")
                self.save_html_report(title, full_content, "performance_analysis_report")
            
            return email_success
            
        except Exception as e:
            logger.error(f"发送绩效分析邮件失败: {str(e)}")
            return False
    
    def _generate_performance_summary(self, performance_data: pd.DataFrame) -> Dict:
        """
        从绩效分析数据中生成策略汇总信息
        
        参数：
        performance_data: 基金绩效分析数据DataFrame
        
        返回：
        Dict: 策略汇总信息
        """
        summary = {
            'total_funds': len(performance_data),
            'buy_signals': 0,
            'sell_signals': 0,
            'hold_signals': 0,
            'avg_today_return': 0.0
        }
        
        if performance_data.empty:
            return summary
        
        # 计算买入/卖出/持有信号数量
        if 'operation_suggestion' in performance_data.columns:
            suggestions = performance_data['operation_suggestion'].dropna()
            summary['buy_signals'] = len(suggestions[suggestions.str.contains('买入|加仓')])
            summary['sell_signals'] = len(suggestions[suggestions.str.contains('卖出|赎回')])
            summary['hold_signals'] = len(suggestions[suggestions.str.contains('持有|观望')])
        
        # 计算平均今日收益率
        if 'today_return' in performance_data.columns:
            today_returns = performance_data['today_return'].dropna()
            if not today_returns.empty:
                summary['avg_today_return'] = today_returns.mean()
        
        # 计算平均年化收益率
        if 'annualized_return' in performance_data.columns:
            annualized_returns = performance_data['annualized_return'].dropna()
            if not annualized_returns.empty:
                summary['avg_annualized_return'] = annualized_returns.mean()
        
        # 计算平均夏普比率
        if 'sharpe_ratio' in performance_data.columns:
            sharpe_ratios = performance_data['sharpe_ratio'].dropna()
            if not sharpe_ratios.empty:
                summary['avg_sharpe_ratio'] = sharpe_ratios.mean()
        
        return summary

    def _format_performance_data_to_table(self, fund_data: pd.DataFrame) -> str:
        """
        将基金绩效分析数据格式化为专业的HTML表格
        
        参数：
        fund_data: 基金绩效分析数据DataFrame
        
        返回：
        str: HTML格式的表格
        """
        if fund_data.empty:
            return "<p>没有基金绩效数据可显示</p>"
        
        # 定义与图片完全一致的列顺序
        priority_columns = [
            'fund_code', 'fund_name', 'yesterday_nav', 'current_estimate', 
            'today_return', 'prev_day_return', 'annualized_return',
            'sharpe_ratio', 'max_drawdown', 'volatility',
            'calmar_ratio', 'sortino_ratio', 'var_95',
            'win_rate', 'profit_loss_ratio', 'composite_score',
            'status_label', 'operation_suggestion', 'redeem_amount',
            'execution_amount'
        ]
        
        # 确定实际可用的列，按照优先级排序
        available_columns = []
        for col in priority_columns:
            if col in fund_data.columns:
                available_columns.append(col)
        
        # 如果优先级列中没有可用的，使用数据中的所有列
        if not available_columns:
            available_columns = fund_data.columns.tolist()
        
        # 创建HTML表格（与图片完全一致的样式）
        html_table = """
        <div style="width: 100%; overflow-x: auto;">
        <table border="1" style="border-collapse: collapse; width: 100%; text-align: center; font-size: 12px; font-family: Arial, sans-serif;">
            <thead>
                <tr style="background-color: #f5f5f5; color: #333; font-weight: bold; border-bottom: 2px solid #333;">
        """
        
        # 添加表头
        for col in available_columns:
            display_name = self._get_column_display_name(col)
            html_table += f"<th style='padding: 8px; border: 1px solid #bdc3c7; background-color: #e8f4f8;'>{display_name}</th>"
        
        html_table += "</tr></thead><tbody>"
        
        # 添加数据行
        for _, row in fund_data.iterrows():
            html_table += "<tr>"
            for col in available_columns:
                value = row[col] if col in row else "N/A"
                
                # 根据列类型格式化值
                if col in ['today_return', 'prev_day_return', 
                           'annualized_return', 'total_return',
                           'volatility', 'win_rate']:
                    # 百分比格式的收益率和波动率
                    if pd.notna(value):
                        formatted_value = f"{value*100:.2f}%"
                        # 根据数值正负设置颜色
                        color = '#FF6B6B' if value < 0 else '#27ae60' if value > 0 else '#7f8c8d'
                        html_table += f"<td style='padding: 6px; border: 1px solid #bdc3c7; color: {color};'>{formatted_value}</td>"
                    else:
                        html_table += "<td style='padding: 6px; border: 1px solid #bdc3c7;'>N/A</td>"
                
                elif col in ['max_drawdown']:
                    # 百分比格式的回撤率（通常为负值）
                    if pd.notna(value):
                        formatted_value = f"{value*100:.2f}%"
                        # 回撤率通常显示为红色
                        color = '#FF6B6B'
                        html_table += f"<td style='padding: 6px; border: 1px solid #bdc3c7; color: {color};'>{formatted_value}</td>"
                    else:
                        html_table += "<td style='padding: 6px; border: 1px solid #bdc3c7;'>N/A</td>"
                
                elif col in ['sharpe_ratio', 'calmar_ratio', 'sortino_ratio', 'profit_loss_ratio', 'composite_score']:
                    # 数值格式的绩效指标
                    if pd.notna(value):
                        formatted_value = f"{value:.4f}"
                        # 根据数值好坏设置颜色
                        if col in ['sharpe_ratio', 'calmar_ratio', 'sortino_ratio', 'profit_loss_ratio', 'composite_score']:
                            color = '#27ae60' if value > 0 else '#FF6B6B' if value < 0 else '#7f8c8d'
                        else:
                            color = '#2c3e50'
                        html_table += f"<td style='padding: 6px; border: 1px solid #bdc3c7; color: {color};'>{formatted_value}</td>"
                    else:
                        html_table += "<td style='padding: 6px; border: 1px solid #bdc3c7;'>N/A</td>"
                
                elif col == 'var_95':
                    # 风险价值
                    if pd.notna(value):
                        formatted_value = f"{value:.4f}"
                        # 风险价值通常显示为红色
                        color = '#FF6B6B'
                        html_table += f"<td style='padding: 6px; border: 1px solid #bdc3c7; color: {color};'>{formatted_value}</td>"
                    else:
                        html_table += "<td style='padding: 6px; border: 1px solid #bdc3c7;'>N/A</td>"
                
                elif col in ['yesterday_nav', 'current_estimate']:
                    # 净值和估值
                    if pd.notna(value):
                        try:
                            # 确保值是数值类型
                            num_value = float(value)
                            formatted_value = f"¥{num_value:.4f}"
                            color = '#2c3e50'
                        except (ValueError, TypeError):
                            # 如果是字符串，直接使用
                            formatted_value = str(value)
                            color = '#2c3e50'
                        html_table += f"<td style='padding: 6px; border: 1px solid #bdc3c7; color: {color};'>{formatted_value}</td>"
                    else:
                        html_table += "<td style='padding: 6px; border: 1px solid #bdc3c7;'>N/A</td>"
                
                elif col == 'redeem_amount':
                    # 赎回金额（支持数值和字符串格式）
                    if pd.notna(value):
                        try:
                            # 尝试将值转换为数值
                            num_value = float(value)
                            formatted_value = f"¥{num_value:.2f}"
                            color = '#FF6B6B' if num_value > 0 else '#2c3e50'
                        except (ValueError, TypeError):
                            # 如果是字符串，直接使用
                            formatted_value = str(value)
                            color = '#FF6B6B' if '赎回' in formatted_value else '#2c3e50'
                        html_table += f"<td style='padding: 6px; border: 1px solid #bdc3c7; color: {color};'>{formatted_value}</td>"
                    else:
                        html_table += "<td style='padding: 6px; border: 1px solid #bdc3c7;'>N/A</td>"
                
                elif col == 'operation_suggestion':
                    # 操作建议格式化
                    suggestion = str(value) if pd.notna(value) else "N/A"
                    # 根据建议内容设置颜色
                    if "买入" in suggestion or "持有" in suggestion:
                        color = "#27ae60"
                    elif "赎回" in suggestion or "卖出" in suggestion:
                        color = "#FF6B6B"
                    else:
                        color = "#2c3e50"
                    html_table += f"<td style='padding: 6px; border: 1px solid #bdc3c7; color: {color}; font-weight: bold;'>{suggestion}</td>"
                
                elif col in ['execute_amount', 'execution_amount']:
                    # 执行金额格式化
                    amount = str(value) if pd.notna(value) else "N/A"
                    # 根据金额内容设置颜色
                    color = "#FF6B6B" if "赎回" in amount else "#27ae60" if "买入" in amount else "#2c3e50"
                    html_table += f"<td style='padding: 6px; border: 1px solid #bdc3c7; color: {color};'>{amount}</td>"
                
                elif col == 'status_label':
                    # 状态标签格式化（与图片完全一致的样式）
                    status = str(value) if pd.notna(value) else "N/A"
                    # 根据状态设置不同颜色的圆形标记（与图片完全一致）
                    if "反转转跌" in status:
                        icon = '<span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: #FF6B6B; margin-right: 5px; vertical-align: middle;"></span>'
                        color = "#FF6B6B"
                        status_text = "反转转跌"
                    elif "连涨加速" in status:
                        icon = '<span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: #FFD700; margin-right: 5px; vertical-align: middle;"></span>'
                        color = "#FFD700"
                        status_text = "连涨加速"
                    elif "连涨放缓" in status:
                        icon = '<span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: #FFA500; margin-right: 5px; vertical-align: middle;"></span>'
                        color = "#FFA500"
                        status_text = "连涨放缓"
                    elif "连涨回落" in status:
                        icon = '<span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: #FF6B6B; margin-right: 5px; vertical-align: middle;"></span>'
                        color = "#FF6B6B"
                        status_text = "连涨回落"
                    elif "大涨" in status:
                        icon = '<span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: #00FF00; margin-right: 5px; vertical-align: middle;"></span>'
                        color = "#00FF00"
                        status_text = "大涨"
                    elif "震荡整理" in status:
                        icon = '<span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: #808080; margin-right: 5px; vertical-align: middle;"></span>'
                        color = "#808080"
                        status_text = "震荡整理"
                    else:
                        icon = '<span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: #808080; margin-right: 5px; vertical-align: middle;"></span>'
                        color = "#808080"
                        status_text = status
                    
                    html_table += f"<td style='padding: 6px; border: 1px solid #bdc3c7;'>{icon}<strong style='color: {color};'>{status_text}</strong></td>"
                
                elif col == 'is_buy':
                    # 是否买入字段
                    if pd.notna(value):
                        is_buy = bool(value)
                        formatted_value = "是" if is_buy else "否"
                        color = "#27ae60" if is_buy else "#FF6B6B"
                        html_table += f"<td style='padding: 6px; border: 1px solid #bdc3c7; color: {color};'>{formatted_value}</td>"
                    else:
                        html_table += "<td style='padding: 6px; border: 1px solid #bdc3c7;'>N/A</td>"
                
                else:
                    # 普通文本格式
                    display_value = str(value) if pd.notna(value) else "N/A"
                    html_table += f"<td style='padding: 6px; border: 1px solid #bdc3c7;'>{display_value}</td>"
            
            html_table += "</tr>"
        
        html_table += "</tbody></table></div>"
        return html_table
    
    def _extract_first_number(self, value: object) -> float:
        try:
            if pd.isna(value):
                return 0.0
            text = str(value)
            match = re.search(r"(-?\d+(?:\.\d+)?)", text.replace(",", ""))
            if not match:
                return 0.0
            return float(match.group(1))
        except Exception:
            return 0.0
    
    def _execution_amount_priority(self, text: str) -> int:
        t = str(text or "")
        if "买入" in t:
            return 0
        if "赎回" in t or "卖出" in t:
            return 1
        if "持有" in t or "不动" in t or "不买入" in t:
            return 2
        return 3
    
    def _operation_suggestion_priority(self, text: str) -> int:
        t = str(text or "")
        if "强烈买入" in t or "积极买入" in t or "强势" in t:
            return 0
        if "买入" in t:
            return 1
        if "持有" in t or "观望" in t or "不买入" in t:
            return 2
        if "赎回" in t or "卖出" in t:
            return 3
        return 4
    
    def _sort_fund_data_for_report(self, fund_data: pd.DataFrame) -> pd.DataFrame:
        if fund_data.empty:
            return fund_data
        
        sort_by = self.email_config.get("sort_by") or self.config.get("sort_by") or "execution_amount"
        sort_by = str(sort_by).lower()
        if sort_by in {"execution_amount", "execution", "amount"}:
            mode = "execution_amount"
        elif sort_by in {"operation_suggestion", "suggestion", "operation"}:
            mode = "operation_suggestion"
        else:
            mode = "execution_amount"
        
        df = fund_data.copy()
        
        has_amount = "execution_amount" in df.columns
        has_suggestion = "operation_suggestion" in df.columns
        
        if has_amount:
            df["_sort_exec_priority"] = df["execution_amount"].map(self._execution_amount_priority)
            df["_sort_exec_amount"] = df["execution_amount"].map(self._extract_first_number).abs()
        else:
            df["_sort_exec_priority"] = 999
            df["_sort_exec_amount"] = 0.0
        
        if has_suggestion:
            df["_sort_suggestion_priority"] = df["operation_suggestion"].map(self._operation_suggestion_priority)
        else:
            df["_sort_suggestion_priority"] = 999
        
        if mode == "operation_suggestion":
            sort_cols = ["_sort_suggestion_priority", "_sort_exec_priority", "_sort_exec_amount"]
            ascending = [True, True, False]
        else:
            sort_cols = ["_sort_exec_priority", "_sort_exec_amount", "_sort_suggestion_priority"]
            ascending = [True, False, True]
        
        if "today_return" in df.columns:
            sort_cols.append("today_return")
            ascending.append(False)
        
        df = df.sort_values(by=sort_cols, ascending=ascending, kind="mergesort")
        df = df.drop(columns=["_sort_exec_priority", "_sort_exec_amount", "_sort_suggestion_priority"], errors="ignore")
        return df
    
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
        
        fund_data = self._sort_fund_data_for_report(fund_data)
        
        # 选择要显示的列（与参考图片一致的顺序）
        display_columns = [
            'fund_code', 'fund_name', 'today_return', 'prev_day_return', 
            'status_label', 'operation_suggestion', 'execution_amount',
            'holding_amount', 'cumulative_profit_loss'
        ]
        
        # 确保所需的列存在
        available_columns = [col for col in display_columns if col in fund_data.columns]
        
        # 创建HTML表格（匹配参考图片样式）
        html_table = """
        <div style="width: 100%; overflow-x: auto;">
        <table border="1" style="border-collapse: collapse; width: 100%; text-align: center; font-size: 14px; font-family: 'Arial', sans-serif;">
            <thead>
                <tr style="background-color: #f5f5f5; color: #333; font-weight: bold; height: 40px;">
        """
        
        # 添加表头
        for col in available_columns:
            display_name = self._get_column_display_name(col)
            width_style = ""
            if col == 'fund_name':
                width_style = "min-width: 180px;"
            elif col == 'operation_suggestion':
                width_style = "min-width: 120px;"
            elif col == 'status_label':
                width_style = "min-width: 100px;"
            elif col in ['holding_amount', 'cumulative_profit_loss']:
                width_style = "min-width: 100px;"
                
            html_table += f"<th style='padding: 8px; border: 1px solid #ddd; {width_style}'>{display_name}</th>"
        
        html_table += "</tr></thead><tbody>"
        
        # 添加数据行
        for _, row in fund_data.iterrows():
            html_table += "<tr style='height: 35px;'>"
            for col in available_columns:
                value = row[col] if col in row else "N/A"
                
                # 根据列类型格式化值
                if col in ['today_return', 'prev_day_return']:
                    if pd.notna(value):
                        formatted_value = f"{value:.2f}%"
                        color = '#e74c3c' if value > 0 else '#27ae60' if value < 0 else 'black'
                        html_table += f"<td style='padding: 8px; border: 1px solid #ddd; color: {color}; font-weight: 500;'>{formatted_value}</td>"
                    else:
                        html_table += "<td style='padding: 8px; border: 1px solid #ddd;'>N/A</td>"
                
                elif col in ['trend_status', 'status_label']:
                    if pd.notna(value):
                        status = str(value)
                        clean_status = re.sub(r'<[^>]+>', '', status)
                        
                        # 根据状态标签中的emoji设置颜色
                        if '🟢' in status:
                            icon_color = '#27ae60'  # 绿色 - 上涨相关
                        elif '🟡' in status:
                            icon_color = '#f39c12'  # 黄色 - 连涨加速
                        elif '🟠' in status:
                            icon_color = '#e67e22'  # 橙色 - 上涨放缓
                        elif '🔵' in status:
                            icon_color = '#3498db'  # 蓝色 - 反转相关
                        elif '🔴' in status:
                            icon_color = '#e74c3c'  # 红色 - 下跌或警告
                        elif '🟣' in status:
                            icon_color = '#9b59b6'  # 紫色 - 下跌相关
                        elif '⚪' in status:
                            icon_color = '#bdc3c7'  # 灰色 - 平稳
                        else:
                            # 根据文字内容判断颜色
                            if '上涨' in clean_status or '突破' in clean_status:
                                icon_color = '#27ae60'
                            elif '下跌' in clean_status or '回调' in clean_status:
                                icon_color = '#e74c3c'
                            elif '震荡' in clean_status:
                                icon_color = '#95a5a6'
                            elif '平稳' in clean_status:
                                icon_color = '#bdc3c7'
                            else:
                                icon_color = '#e67e22'  # 默认橙色
                            
                        icon = f'<span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: {icon_color}; margin-right: 6px; vertical-align: middle;"></span>'
                        
                        html_table += f"<td style='padding: 8px; border: 1px solid #ddd; text-align: left; padding-left: 15px;'>{icon}<strong>{clean_status}</strong></td>"
                    else:
                        html_table += "<td style='padding: 8px; border: 1px solid #ddd;'>N/A</td>"
                
                elif col == 'operation_suggestion':
                    suggestion = str(value) if pd.notna(value) else "N/A"
                    html_table += f"<td style='padding: 8px; border: 1px solid #ddd;'>{suggestion}</td>"
                
                elif col in ['execute_amount', 'execution_amount']:
                    amount = str(value) if pd.notna(value) else "N/A"
                    html_table += f"<td style='padding: 8px; border: 1px solid #ddd;'>{amount}</td>"
                
                elif col == 'holding_amount':
                    if pd.notna(value):
                        try:
                            holding_val = float(value)
                            formatted_value = f"¥{holding_val:.2f}"
                            html_table += f"<td style='padding: 8px; border: 1px solid #ddd; text-align: right;'>{formatted_value}</td>"
                        except (ValueError, TypeError):
                            html_table += f"<td style='padding: 8px; border: 1px solid #ddd;'>{value}</td>"
                    else:
                        html_table += "<td style='padding: 8px; border: 1px solid #ddd;'>N/A</td>"
                
                elif col == 'cumulative_profit_loss':
                    if pd.notna(value):
                        try:
                            profit_val = float(value)
                            formatted_value = f"¥{profit_val:.2f}"
                            color = '#e74c3c' if profit_val > 0 else '#27ae60' if profit_val < 0 else 'black'
                            html_table += f"<td style='padding: 8px; border: 1px solid #ddd; text-align: right; color: {color}; font-weight: 500;'>{formatted_value}</td>"
                        except (ValueError, TypeError):
                            html_table += f"<td style='padding: 8px; border: 1px solid #ddd;'>{value}</td>"
                    else:
                        html_table += "<td style='padding: 8px; border: 1px solid #ddd;'>N/A</td>"
                
                elif col == 'fund_name':
                     html_table += f"<td style='padding: 8px; border: 1px solid #ddd; text-align: left;'>{value if pd.notna(value) else 'N/A'}</td>"

                else:
                    html_table += f"<td style='padding: 8px; border: 1px solid #ddd;'>{value if pd.notna(value) else 'N/A'}</td>"
            
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
        
        html_content = "<div style='margin: 15px 0; padding: 15px; background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #3498db;'><h4 style='color: #2c3e50; margin-top: 0;'>📊 绩效分析汇总</h4><ul style='margin: 10px 0; padding-left: 20px; list-style-type: disc;'>"
        
        # 添加分析基金总数
        if 'total_funds' in strategy_summary:
            html_content += f"<li><strong>分析基金总数:</strong> {strategy_summary['total_funds']} 只</li>"
        
        # 添加信号统计
        if 'buy_signals' in strategy_summary or 'sell_signals' in strategy_summary or 'hold_signals' in strategy_summary:
            html_content += "<li><strong>操作建议分布:</strong> "
            if 'buy_signals' in strategy_summary and strategy_summary['buy_signals'] > 0:
                html_content += f"<span style='color: #27ae60;'>买入: {strategy_summary['buy_signals']} 只</span>, "
            if 'hold_signals' in strategy_summary and strategy_summary['hold_signals'] > 0:
                html_content += f"<span style='color: #f39c12;'>持有: {strategy_summary['hold_signals']} 只</span>, "
            if 'sell_signals' in strategy_summary and strategy_summary['sell_signals'] > 0:
                html_content += f"<span style='color: #e74c3c;'>卖出: {strategy_summary['sell_signals']} 只</span>"
            html_content = html_content.rstrip(', ') + "</li>"
        
        # 添加平均收益率信息
        if 'avg_today_return' in strategy_summary:
            avg_today = strategy_summary['avg_today_return']
            color = '#27ae60' if avg_today > 0 else '#e74c3c' if avg_today < 0 else '#7f8c8d'
            html_content += f"<li><strong>平均今日收益率:</strong> <span style='color: {color};'>{avg_today:.2f}%</span></li>"
        
        # 添加年化收益率信息
        if 'avg_annualized_return' in strategy_summary:
            avg_annualized = strategy_summary['avg_annualized_return']
            color = '#27ae60' if avg_annualized > 0 else '#e74c3c' if avg_annualized < 0 else '#7f8c8d'
            html_content += f"<li><strong>平均年化收益率:</strong> <span style='color: {color};'>{avg_annualized:.2f}%</span></li>"
        
        # 添加平均夏普比率
        if 'avg_sharpe_ratio' in strategy_summary:
            avg_sharpe = strategy_summary['avg_sharpe_ratio']
            color = '#27ae60' if avg_sharpe > 1 else '#f39c12' if avg_sharpe > 0 else '#e74c3c'
            html_content += f"<li><strong>平均夏普比率:</strong> <span style='color: {color};'>{avg_sharpe:.4f}</span></li>"
        
        # 添加操作分布
        if 'action_distribution' in strategy_summary:
            html_content += "<li><strong>详细操作分布:</strong> "
            for action, count in strategy_summary['action_distribution'].items():
                html_content += f"{action}: {count} 只, "
            html_content = html_content.rstrip(', ') + "</li>"
        
        # 添加平均买入倍数
        if 'avg_buy_multiplier' in strategy_summary:
            html_content += f"<li><strong>平均买入倍数:</strong> {strategy_summary['avg_buy_multiplier']:.2f}</li>"
        
        # 添加总赎回金额
        if 'total_redeem_amount' in strategy_summary:
            html_content += f"<li><strong>总赎回金额:</strong> ¥{strategy_summary['total_redeem_amount']:.2f}</li>"
        
        html_content += "</ul></div>"
        return html_content

    def _get_column_display_name(self, column_name: str) -> str:
        """获取列的显示名称"""
        column_names = {
            # 基本信息字段
            'fund_code': '基金代码',
            'fund_name': '基金名称',
            'analysis_date': '分析日期',
            
            # 净值相关字段
            'yesterday_nav': '昨日净值',
            'current_estimate': '今日估值',
            'total_return': '总收益率',
            
            # 收益率相关字段
            'today_return': '今日收益率',
            'prev_day_return': '前一日收益率',
            'prev_day_return': '昨日收益率',
            'annualized_return': '年化收益率',
            
            # 绩效分析字段
            'sharpe_ratio': '夏普比率',
            'max_drawdown': '最大回撤率',
            'volatility': '年化波动率',
            'calmar_ratio': '卡尔玛比率',
            'sortino_ratio': '索提诺比率',
            'var_95': '风险价值(VaR)',
            'win_rate': '盈利胜率',
            'profit_loss_ratio': '盈亏比率',
            'composite_score': '综合绩效评分',
            
            # 交易建议字段
            'status_label': '趋势状态',
            'is_buy': '是否买入',
            'redeem_amount': '赎回金额',
            'comparison_value': '比较值',
            'operation_suggestion': '操作建议',
            'execution_amount': '执行金额',
            'execute_amount': '执行金额',
            'buy_multiplier': '买入倍数',
            
            # 趋势分析字段
            'trend_status': '趋势状态',
            
            # 持仓相关字段
            'holding_amount': '持有金额',
            'cumulative_profit_loss': '累计盈亏'
        }
        return column_names.get(column_name, column_name)


if __name__ == "__main__":
    # 测试代码
    import sys
    import os
    
    # 添加项目根目录到路径，以便导入shared模块
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.append(parent_dir)
    
    from shared.enhanced_config import NOTIFICATION_CONFIG
    
    # 创建通知管理器
    notification_manager = EnhancedNotificationManager(NOTIFICATION_CONFIG)
    
    # 创建测试数据
    test_fund_data = pd.DataFrame({
        'fund_code': ['000001', '000002', '000003'],
        'fund_name': ['测试基金1', '测试基金2', '测试基金3'],
        'today_return': [0.5, 1.2, -0.8],
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
