#!/usr/bin/env python
# coding: utf-8

"""
增强版基金分析系统主程序
整合所有模块，提供完整的基金分析解决方案
"""

import pandas as pd
import numpy as np
import argparse
import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入自定义模块
from shared.enhanced_config import BASE_CONFIG, DATABASE_CONFIG, NOTIFICATION_CONFIG
from data_retrieval.enhanced_fund_data import EnhancedFundData
from backtesting.enhanced_strategy import EnhancedInvestmentStrategy
from backtesting.enhanced_analytics import EnhancedFundAnalytics
from data_retrieval.enhanced_database import EnhancedDatabaseManager
from data_retrieval.enhanced_notification import EnhancedNotificationManager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fund_analysis.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EnhancedFundAnalysisSystem:
    """增强版基金分析系统主类"""
    
    def __init__(self):
        """初始化系统组件"""
        self.fund_data_manager = EnhancedFundData()
        self.strategy_engine = EnhancedInvestmentStrategy()
        self.analytics_engine = EnhancedFundAnalytics()
        self.db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        self.notification_manager = EnhancedNotificationManager(NOTIFICATION_CONFIG)
        
        # 配置中文字体显示
        self.setup_chinese_font()
        
        logger.info("增强版基金分析系统初始化完成")
    
    def setup_chinese_font(self):
        """
        配置Matplotlib中文字体显示
        解决中文乱码问题
        """
        try:
            import matplotlib.pyplot as plt
            import platform
            
            # 获取操作系统类型
            system = platform.system()
            
            # 根据操作系统设置中文字体
            if system == 'Windows':
                # Windows系统字体
                font_names = ['SimHei', 'Microsoft YaHei', 'SimSun', 'KaiTi', 'FangSong']
            elif system == 'Darwin':  # macOS
                font_names = ['Heiti TC', 'STHeiti', 'PingFang SC', 'Hiragino Sans GB']
            else:  # Linux
                font_names = ['WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 'Noto Sans CJK SC']
            
            # 尝试设置字体
            font_set = False
            for font_name in font_names:
                try:
                    plt.rcParams['font.sans-serif'] = [font_name]
                    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
                    font_set = True
                    logger.info(f"成功设置中文字体: {font_name}")
                    break
                except:
                    continue
            
            if not font_set:
                # 如果所有中文字体都失败，使用备用方案
                logger.warning("无法设置中文字体，将使用默认字体，中文可能显示为方框")
                plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
                plt.rcParams['axes.unicode_minus'] = False
        except ImportError:
            logger.warning("matplotlib未安装，跳过字体设置")
    
    def load_fund_data_from_excel(self, file_path: str, sheet_name: str = None) -> pd.DataFrame:
        """
        从Excel文件加载基金数据
        
        参数：
        file_path: Excel文件路径
        sheet_name: 工作表名称
        
        返回：
        DataFrame: 基金基础数据
        """
        try:
            logger.info(f"正在加载Excel文件: {file_path}")
            
            # 使用配置中的工作表名称，如果没有指定
            if not sheet_name:
                sheet_name = BASE_CONFIG.get('sheet_name', 0)
            
            # 读取Excel文件
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            logger.info(f"成功读取Excel文件，共 {len(df)} 行数据")
            
            # 检查列名，使用正确的列名
            if '代码' in df.columns:
                fund_code_col = '代码'
                fund_name_col = '名称'
            elif '基金代码' in df.columns:
                fund_code_col = '基金代码'
                fund_name_col = '基金名称'
            else:
                logger.error("Excel文件中没有找到基金代码列（'代码'或'基金代码'）")
                return pd.DataFrame()
            
            # 过滤有效基金代码（只保留数字代码）
            valid_df = df[df[fund_code_col].astype(str).str.isdigit()].copy()
            logger.info(f"过滤后有效基金数据: {len(valid_df)} 条")
            
            # 格式化基金代码为6位
            valid_df[fund_code_col] = valid_df[fund_code_col].astype(str).str.zfill(6)
            
            # 重命名列以便统一处理
            valid_df = valid_df.rename(columns={
                fund_code_col: '代码',
                fund_name_col: '名称'
            })
            
            return valid_df
            
        except Exception as e:
            logger.error(f"加载Excel文件失败: {str(e)}")
            return pd.DataFrame()
    
    def analyze_single_fund(self, fund_code: str, fund_name: str, analysis_date: str) -> Dict:
        """
        分析单个基金
        
        参数：
        fund_code: 基金代码
        fund_name: 基金名称
        analysis_date: 分析日期
        
        返回：
        dict: 基金分析结果
        """
        try:
            logger.info(f"开始分析基金: {fund_code} - {fund_name}")
            
            # 获取基金基本信息
            basic_info = self.fund_data_manager.get_fund_basic_info(fund_code)
            
            # 获取实时数据
            realtime_data = self.fund_data_manager.get_realtime_data(fund_code)
            
            # 获取绩效指标
            performance_metrics = self.fund_data_manager.get_performance_metrics(fund_code)
            
            # 获取历史数据用于策略分析
            historical_data = self.fund_data_manager.get_historical_data(fund_code, days=30)
            
            # 计算今日和昨日收益率
            today_return = realtime_data.get('daily_return', 0.0)
            yesterday_return = 0.0
            
            # 从历史数据获取昨日收益率
            if not historical_data.empty and 'daily_growth_rate' in historical_data.columns:
                recent_growth = historical_data['daily_growth_rate'].dropna().tail(2)
                if len(recent_growth) >= 2:
                    yesterday_return = float(recent_growth.iloc[-2]) if pd.notna(recent_growth.iloc[-2]) else 0.0
                elif len(recent_growth) == 1:
                    yesterday_return = float(recent_growth.iloc[-1]) if pd.notna(recent_growth.iloc[-1]) else 0.0
            elif not historical_data.empty and 'daily_return' in historical_data.columns:
                # 备用方案：使用pct_change计算的收益率（小数格式，需要乘100）
                recent_returns = historical_data['daily_return'].dropna().tail(2)
                if len(recent_returns) >= 2:
                    yesterday_return = recent_returns.iloc[-2] * 100
                elif len(recent_returns) == 1:
                    yesterday_return = recent_returns.iloc[-1] * 100
            
            # 投资策略分析 - 使用策略引擎
            strategy_result = self.strategy_engine.analyze_strategy(today_return, yesterday_return, performance_metrics)
            
            # 从策略结果中提取字段
            strategy_name = strategy_result.get('strategy_name', 'momentum_strategy')
            action = strategy_result.get('action', 'hold')
            buy_multiplier = strategy_result.get('buy_multiplier', 0.0)
            redeem_amount = strategy_result.get('redeem_amount', 0.0)
            status_label = strategy_result.get('status_label', '🔴 未知状态')
            operation_suggestion = strategy_result.get('operation_suggestion', '持有不动')
            execution_amount = strategy_result.get('execution_amount', '持有不动')
            comparison_value = strategy_result.get('comparison_value', today_return - yesterday_return)
            
            # 兼容性：设置is_buy字段
            is_buy = action in ['buy', 'strong_buy', 'weak_buy']
            
            # 合并所有数据
            fund_result = {
                'fund_code': fund_code,
                'fund_name': fund_name,  # 优先使用传入的基金名称
                'analysis_date': analysis_date,
                'today_return': today_return,
                'yesterday_return': yesterday_return,  # 使用yesterday_return字段
                'prev_day_return': yesterday_return,  # 兼容字段
                'strategy_name': strategy_name,  # 使用策略引擎返回的策略名称
                'status_label': status_label,
                'operation_suggestion': operation_suggestion,
                'execution_amount': execution_amount,
                'is_buy': is_buy,
                'redeem_amount': redeem_amount,
                'buy_multiplier': buy_multiplier,
                'action': action,  # 添加action字段供策略引擎使用
                'daily_return': today_return,  # 用于收益率分析图表
                'comparison_value': comparison_value,  # 添加比较值字段
                **basic_info,
                **realtime_data,
                **performance_metrics
            }
            
            # 确保使用传入的基金名称覆盖API获取的名称
            fund_result['fund_name'] = fund_name
            
            logger.info(f"基金 {fund_code} 分析完成")
            return fund_result
            
        except Exception as e:
            logger.error(f"分析基金 {fund_code} 失败: {str(e)}")
            # 返回默认结果
            return {
                'fund_code': fund_code,
                'fund_name': fund_name,
                'analysis_date': analysis_date,
                'today_return': 0.0,
                'yesterday_return': 0.0,
                'prev_day_return': 0.0,
                'daily_return': 0.0,
                'strategy_name': 'default_strategy',  # 添加默认策略名称
                'status_label': "🔴 分析失败",
                'operation_suggestion': "数据获取失败，建议人工核查",
                'execution_amount': "持有不动",
                'action': 'hold',  # 添加默认action
                'buy_multiplier': 0.0,  # 添加默认买入倍数
                'redeem_amount': 0.0,  # 添加默认赎回金额
                'comparison_value': 0.0,  # 添加默认比较值
                'composite_score': 0.0
            }
    
    def analyze_all_funds(self, fund_data: pd.DataFrame, analysis_date: str) -> List[Dict]:
        """
        分析所有基金
        
        参数：
        fund_data: 基金基础数据DataFrame
        analysis_date: 分析日期
        
        返回：
        list: 所有基金的分析结果
        """
        try:
            logger.info(f"开始分析所有基金，共 {len(fund_data)} 只基金")
            
            results = []
            
            for _, row in fund_data.iterrows():
                fund_code = row['代码']
                fund_name = row['名称']
                
                # 分析单个基金
                result = self.analyze_single_fund(fund_code, fund_name, analysis_date)
                results.append(result)
            
            # 确保所有结果都包含必要字段
            for i, result in enumerate(results):
                # 确保daily_return字段存在
                if 'daily_return' not in result:
                    results[i]['daily_return'] = result.get('today_return', 0.0)
            
            logger.info(f"所有基金分析完成，共分析 {len(results)} 只基金")
            return results
            
        except Exception as e:
            logger.error(f"分析所有基金失败: {str(e)}")
            return []
    
    def generate_strategy_summary(self, results: List[Dict]) -> Dict:
        """
        生成策略汇总
        
        参数：
        results: 基金分析结果列表
        
        返回：
        dict: 策略汇总数据
        """
        try:
            if not results:
                return {}
            
            # 获取基础策略汇总
            base_summary = self.strategy_engine.generate_strategy_summary(results)
            
            if not base_summary:
                # 如果策略引擎返回空，手动计算基础汇总
                df = pd.DataFrame(results)
                
                base_summary = {
                    'total_funds': len(results),
                    'avg_today_return': df['today_return'].mean() if 'today_return' in df.columns else 0,
                    'positive_return_funds': len(df[df['today_return'] > 0]) if 'today_return' in df.columns else 0,
                    'negative_return_funds': len(df[df['today_return'] < 0]) if 'today_return' in df.columns else 0,
                    'zero_return_funds': len(df[df['today_return'] == 0]) if 'today_return' in df.columns else 0,
                }
            
            # 转换为DataFrame以便分析
            results_df = pd.DataFrame(results)
            
            if not results_df.empty and 'composite_score' in results_df.columns:
                # 找出最佳和最差基金
                best_fund = results_df.loc[results_df['composite_score'].idxmax()]
                worst_fund = results_df.loc[results_df['composite_score'].idxmin()]
                
                # 找出夏普比率最高和波动率最低的基金
                if 'sharpe_ratio' in results_df.columns:
                    highest_sharpe_fund = results_df.loc[results_df['sharpe_ratio'].idxmax()]
                else:
                    highest_sharpe_fund = best_fund
                
                if 'volatility' in results_df.columns:
                    lowest_volatility_fund = results_df.loc[results_df['volatility'].idxmin()]
                else:
                    lowest_volatility_fund = best_fund
                
                # 添加数据库需要的字段
                base_summary.update({
                    'best_performing_fund': best_fund.get('fund_code', ''),
                    'worst_performing_fund': worst_fund.get('fund_code', ''),
                    'highest_sharpe_fund': highest_sharpe_fund.get('fund_code', ''),
                    'lowest_volatility_fund': lowest_volatility_fund.get('fund_code', '')
                })
            else:
                # 如果没有足够的数据，使用默认值
                base_summary.update({
                    'best_performing_fund': '',
                    'worst_performing_fund': '',
                    'highest_sharpe_fund': '',
                    'lowest_volatility_fund': ''
                })
            
            return base_summary
            
        except Exception as e:
            logger.error(f"生成策略汇总失败: {str(e)}")
            return {
                'total_funds': len(results),
                'avg_today_return': 0.0,
                'positive_return_funds': 0,
                'negative_return_funds': 0,
                'zero_return_funds': 0,
                'best_performing_fund': '',
                'worst_performing_fund': '',
                'highest_sharpe_fund': '',
                'lowest_volatility_fund': ''
            }
    
    def generate_analytics_reports(self, results_df: pd.DataFrame, output_dir: str = "./reports/") -> Dict:
        """
        生成分析图表报告
        
        参数：
        results_df: 分析结果DataFrame
        output_dir: 输出目录
        
        返回：
        dict: 报告文件路径
        """
        try:
            logger.info("开始生成分析图表报告")
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成综合报告
            report_result = self.analytics_engine.generate_comprehensive_report(results_df, output_dir)
            
            if report_result['status'] == 'success':
                logger.info(f"分析图表报告生成完成，共生成 {len(report_result['report_files'])} 个图表")
                return report_result['report_files']
            else:
                logger.error(f"生成分析图表报告失败: {report_result.get('message', '未知错误')}")
                return {}
                
        except Exception as e:
            logger.error(f"生成分析图表报告失败: {str(e)}")
            return {}
    
    def save_results_to_database(self, results: List[Dict], strategy_summary: Dict, report_files: Dict) -> bool:
        """
        保存结果到数据库
        
        参数：
        results: 基金分析结果列表
        strategy_summary: 策略汇总数据
        report_files: 报告文件路径
        
        返回：
        bool: 保存是否成功
        """
        try:
            logger.info("开始保存分析结果到数据库")
            
            # 批量插入数据
            success = self.db_manager.batch_insert_data(results, results, {
                'analysis_date': datetime.now().date(),
                **strategy_summary,
                'report_files': report_files
            })
            
            if success:
                logger.info("分析结果已成功保存到数据库")
            else:
                logger.error("保存分析结果到数据库失败")
            
            return success
            
        except Exception as e:
            logger.error(f"保存结果到数据库失败: {str(e)}")
            return False
    
    def send_notification_reports(self, results_df: pd.DataFrame, strategy_summary: Dict, report_files: Dict) -> bool:
        """
        发送通知报告
        
        参数：
        results_df: 分析结果DataFrame
        strategy_summary: 策略汇总数据
        report_files: 报告文件路径
        
        返回：
        bool: 发送是否成功
        """
        try:
            logger.info("开始生成和发送通知报告")
            
            analysis_date = datetime.now().strftime('%Y-%m-%d')
            
            # 生成综合报告
            report_data = self.notification_manager.generate_comprehensive_report(
                results_df, strategy_summary, report_files, analysis_date
            )
            
            # 发送通知
            success = self.notification_manager.send_comprehensive_notification(report_data, report_files)
            
            if success:
                logger.info("通知报告发送成功")
            else:
                logger.error("通知报告发送失败")
            
            return success
            
        except Exception as e:
            logger.error(f"发送通知报告失败: {str(e)}")
            return False
    
    def generate_wechat_message(self, result_df: pd.DataFrame) -> str:
        """
        根据基金分析结果生成微信通知的HTML消息（7列表格格式）
        按照图示样式生成标准格式的基金分析报告
        
        参数：
        result_df: 基金分析结果的DataFrame
        
        返回：
        str: 格式化的HTML消息内容
        """
        try:
            # 创建一个副本用于格式化显示
            df_display = result_df.copy()
            
            # 按基金代码排序
            if 'fund_code' in df_display.columns:
                df_display = df_display.sort_values(by='fund_code')
            
            # 生成HTML消息 - 按照图示样式
            message = f"<h3>📊 基金分析报告 - {datetime.now().strftime('%Y年%m月%d日')}</h3>\n"
            message += f"<p style='font-size: 14px; color: #666; margin-bottom: 15px;'>持仓基金收益率变化分析</p>\n"
            
            # 表格样式 - 模仿图示中的简洁风格
            message += f"<table style='border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; font-size: 13px;'>\n"
            message += f"<thead>\n"
            message += f"<tr style='background-color: #f8f9fa; border-bottom: 2px solid #dee2e6;'>\n"
            message += f"<th style='text-align: center; padding: 8px 6px; border-right: 1px solid #dee2e6; width: 8%;'>基金代码</th>\n"
            message += f"<th style='text-align: left; padding: 8px 6px; border-right: 1px solid #dee2e6; width: 25%;'>基金名称</th>\n"
            message += f"<th style='text-align: center; padding: 8px 6px; border-right: 1px solid #dee2e6; width: 10%;'>今日收益率</th>\n"
            message += f"<th style='text-align: center; padding: 8px 6px; border-right: 1px solid #dee2e6; width: 10%;'>昨日收益率</th>\n"
            message += f"<th style='text-align: center; padding: 8px 6px; border-right: 1px solid #dee2e6; width: 12%;'>趋势状态</th>\n"
            message += f"<th style='text-align: left; padding: 8px 6px; border-right: 1px solid #dee2e6; width: 20%;'>操作建议</th>\n"
            message += f"<th style='text-align: center; padding: 8px 6px; width: 15%;'>执行金额</th>\n"
            message += f"</tr>\n"
            message += f"</thead>\n"
            message += f"<tbody>\n"
            
            for _, row in df_display.iterrows():
                # 获取所有需要的字段
                fund_code = row.get('fund_code', '')
                fund_name = row.get('fund_name', '')
                today_return = row.get('today_return', 0)
                yesterday_return = row.get('yesterday_return', 0)
                status_label = row.get('status_label', '')
                operation_suggestion = row.get('operation_suggestion', '')
                execution_amount = row.get('execution_amount', '')
                
                # 格式化收益率显示
                today_return_str = f"{today_return:.2f}%" if isinstance(today_return, (int, float)) else str(today_return)
                yesterday_return_str = f"{yesterday_return:.2f}%" if isinstance(yesterday_return, (int, float)) else str(yesterday_return)
                
                # 根据收益率设置颜色
                today_color = '#28a745' if today_return > 0 else '#dc3545' if today_return < 0 else '#6c757d'
                yesterday_color = '#28a745' if yesterday_return > 0 else '#dc3545' if yesterday_return < 0 else '#6c757d'
                
                # 根据趋势状态生成彩色圆点和文字（模仿图示样式）
                status_display = ""
                status_color = "#6c757d"
                
                if "涨" in status_label:
                    status_display = "● 反转涨" if "反转" in status_label else "● 连续涨"
                    status_color = "#28a745"
                elif "跌" in status_label:
                    status_display = "● 反转跌" if "反转" in status_label else "● 连续跌"
                    status_color = "#dc3545"
                elif "持平" in status_label:
                    status_display = "● 转势持平"
                    status_color = "#ffc107"
                else:
                    # 保持原有的emoji图标格式作为备选
                    status_display = status_label
                    if "🔵" in status_label or "🟢" in status_label:
                        status_color = "#28a745"
                    elif "🔴" in status_label:
                        status_color = "#dc3545"
                    elif "🟡" in status_label or "⚪" in status_label:
                        status_color = "#ffc107"
                
                message += f"<tr style='border-bottom: 1px solid #dee2e6;'>\n"
                message += f"<td style='text-align: center; padding: 6px; border-right: 1px solid #dee2e6; font-family: monospace;'>{fund_code}</td>\n"
                message += f"<td style='text-align: left; padding: 6px; border-right: 1px solid #dee2e6;'>{fund_name}</td>\n"
                message += f"<td style='text-align: center; padding: 6px; border-right: 1px solid #dee2e6; color: {today_color}; font-weight: bold;'>{today_return_str}</td>\n"
                message += f"<td style='text-align: center; padding: 6px; border-right: 1px solid #dee2e6; color: {yesterday_color}; font-weight: bold;'>{yesterday_return_str}</td>\n"
                message += f"<td style='text-align: center; padding: 6px; border-right: 1px solid #dee2e6; color: {status_color}; font-weight: bold;'>{status_display}</td>\n"
                message += f"<td style='text-align: left; padding: 6px; border-right: 1px solid #dee2e6;'>{operation_suggestion}</td>\n"
                message += f"<td style='text-align: center; padding: 6px; font-weight: bold;'>{execution_amount}</td>\n"
                message += f"</tr>\n"
            
            message += f"</tbody>\n"
            message += f"</table>\n"
            message += f"<p style='margin-top: 12px; color: #6c757d; font-size: 12px;'>"
            message += f"<strong>提示</strong>：以上分析基于实时估值数据，仅供参考。最终投资决策请结合市场情况谨慎考虑。"
            message += f"</p>"
            
            return message
            
        except Exception as e:
            logger.error(f"生成微信消息失败: {str(e)}")
            return f"<h3>基金分析报告</h3><p>数据生成失败: {str(e)}</p>"
    
    def get_investment_strategy(self, today_return: float, yesterday_return: float) -> tuple:
        """
        根据当日收益率和昨日收益率，返回投资策略结果
        
        参数：
        today_return: 当日收益率（%）
        yesterday_return: 昨日收益率（%）
        
        返回：
        tuple: (status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, execution_amount, buy_multiplier)
        """
        return_diff = today_return - yesterday_return
        
        # 1. 今日>0 昨日>0 today-prev>1%
        if today_return > 0 and yesterday_return > 0:
            if return_diff > 1:
                status_label = "🟢 大涨"
                is_buy = False
                redeem_amount = 0
                buy_multiplier = 0
                operation_suggestion = "不买入，不赎回"
                execution_amount = "持有不动"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 2. 今日>0 昨日>0 0<today-prev≤1%
            elif 0 < return_diff <= 1:
                status_label = "🟡 连涨"
                is_buy = False
                redeem_amount = 15
                buy_multiplier = 0
                operation_suggestion = "不买入，赎回15元"
                execution_amount = "赎回¥15"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 3. 今日>0 昨日>0 -1%≤today-prev≤0
            elif -1 <= return_diff <= 0:
                status_label = "🟠 连涨放缓"
                is_buy = False
                redeem_amount = 0
                buy_multiplier = 0
                operation_suggestion = "不买入，不赎回"
                execution_amount = "持有不动"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 4. 今日>0 昨日>0 today-prev<-1%
            elif return_diff < -1:
                status_label = "🟠 连涨回落"
                is_buy = False
                redeem_amount = 0
                buy_multiplier = 0
                operation_suggestion = "不买入，不赎回"
                execution_amount = "持有不动"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 5. 今日>0 昨日≤0
        elif today_return > 0 and yesterday_return <= 0:
            status_label = "🔵 反转涨"
            is_buy = True
            redeem_amount = 0
            buy_multiplier = 1.5
            operation_suggestion = "定投买入，不赎回"
            execution_amount = f"买入{buy_multiplier}×定额"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 6. 今日=0 昨日>0
        elif today_return == 0 and yesterday_return > 0:
            status_label = "🔴 转势休整"
            is_buy = False
            redeem_amount = 30
            buy_multiplier = 0
            operation_suggestion = "不买入，赎回30元"
            execution_amount = "赎回¥30"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 7. 今日<0 昨日>0
        elif today_return < 0 and yesterday_return > 0:
            status_label = "🔴 反转跌"
            is_buy = False
            redeem_amount = 30
            buy_multiplier = 0
            operation_suggestion = "不买入，赎回30元"
            execution_amount = "赎回¥30"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 8. 今日=0 昨日≤0
        elif today_return == 0 and yesterday_return <= 0:
            status_label = "⚪ 持平"
            is_buy = True
            redeem_amount = 0
            buy_multiplier = 2.0
            operation_suggestion = "定投买入，不赎回"
            execution_amount = f"买入{buy_multiplier}×定额"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 9. 今日<0 昨日=0 today≤-2%
        elif today_return < 0 and yesterday_return == 0:
            if today_return <= -2:
                status_label = "🔴 首次大跌"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 0.5
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 10. 今日<0 昨日=0 -2%<today≤-0.5%
            elif -2 < today_return <= -0.5:
                status_label = "🟠 首次下跌"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 1.5
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 11. 今日<0 昨日=0 today>-0.5%
            elif today_return > -0.5:
                status_label = "🔵 微跌试探"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 1.0
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 12. 今日<0 昨日<0 (today-prev)>1% & today≤-2%
        elif today_return < 0 and yesterday_return < 0:
            if return_diff > 1 and today_return <= -2:
                status_label = "🔴 暴跌加速"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 0.5
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 13. 今日<0 昨日<0 (today-prev)>1% & today>-2%
            elif return_diff > 1 and today_return > -2:
                status_label = "🟣 跌速扩大"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 1.0
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 14. 今日<0 昨日<0 (prev-today)>0 & prev≤-2%
            elif (yesterday_return - today_return) > 0 and yesterday_return <= -2:
                status_label = "🔵 暴跌回升"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 1.5
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 15. 今日<0 昨日<0 (prev-today)>0 & prev>-2%
            elif (yesterday_return - today_return) > 0 and yesterday_return > -2:
                status_label = "🟦 跌速放缓"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 1.0
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 16. 今日<0 昨日<0 abs差值≤1%
            elif abs(return_diff) <= 1:
                status_label = "🟣 阴跌筑底"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 1.0
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 默认情况
        status_label = "🔴 下跌"
        is_buy = True
        redeem_amount = 0
        buy_multiplier = 1.0
        operation_suggestion = "定投买入，不赎回"
        execution_amount = f"买入{buy_multiplier}×定额"
        return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
    
    def run_complete_analysis(self, excel_file_path: str = None, output_dir: str = "./reports/") -> bool:
        """
        运行完整的基金分析流程
        
        参数：
        excel_file_path: Excel文件路径（可选，使用配置文件中的默认路径）
        output_dir: 输出目录
        
        返回：
        bool: 分析是否成功完成
        """
        try:
            logger.info("开始运行完整的基金分析流程")
            
            # 使用配置文件中的默认路径，如果没有指定
            if not excel_file_path:
                excel_file_path = BASE_CONFIG.get('fund_position_file', '')
            
            # 1. 加载基金数据
            fund_data = self.load_fund_data_from_excel(excel_file_path)
            if fund_data.empty:
                logger.error("没有获取到有效的基金数据")
                return False
            
            analysis_date = datetime.now().strftime('%Y-%m-%d')
            
            # 2. 分析所有基金
            results = self.analyze_all_funds(fund_data, analysis_date)
            if not results:
                logger.error("基金分析失败")
                return False
            
            # 转换为DataFrame便于处理
            results_df = pd.DataFrame(results)
            
            # 3. 生成策略汇总
            strategy_summary = self.generate_strategy_summary(results)
            
            # 4. 生成分析图表报告
            report_files = self.generate_analytics_reports(results_df, output_dir)
            
            # 5. 保存结果到数据库
            db_success = self.save_results_to_database(results, strategy_summary, report_files)
            if not db_success:
                logger.warning("数据库保存失败，但继续执行后续步骤")
            
            # 6. 发送通知报告
            notification_success = self.send_notification_reports(results_df, strategy_summary, report_files)
            if not notification_success:
                logger.warning("通知发送失败，但分析流程已完成")
            
            # 7. 输出分析摘要
            self._print_analysis_summary(results_df, strategy_summary, report_files)
            
            logger.info("完整的基金分析流程执行完成")
            return True
            
        except Exception as e:
            logger.error(f"运行完整分析流程失败: {str(e)}")
            return False
    
    def _print_analysis_summary(self, results_df: pd.DataFrame, strategy_summary: Dict, report_files: Dict):
        """
        打印分析摘要
        """
        try:
            print("\n" + "="*80)
            print("📊 基金分析摘要报告")
            print("="*80)
            print(f"分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"分析基金数量: {len(results_df)}")
            
            if not results_df.empty:
                if 'annualized_return' in results_df.columns:
                    print(f"平均年化收益率: {results_df['annualized_return'].mean()*100:.2f}%")
                if 'sharpe_ratio' in results_df.columns:
                    print(f"平均夏普比率: {results_df['sharpe_ratio'].mean():.3f}")
                if 'max_drawdown' in results_df.columns:
                    print(f"平均最大回撤: {results_df['max_drawdown'].mean()*100:.2f}%")
                if 'composite_score' in results_df.columns:
                    print(f"平均综合评分: {results_df['composite_score'].mean():.3f}")
            
            print("\n📈 策略信号统计:")
            if strategy_summary:
                print(f"  总基金数: {strategy_summary.get('total_funds', 0)}")
                print(f"  上涨基金: {strategy_summary.get('positive_return_funds', 0)}")
                print(f"  下跌基金: {strategy_summary.get('negative_return_funds', 0)}")
                print(f"  持平基金: {strategy_summary.get('zero_return_funds', 0)}")
            
            print("\n📊 生成报告文件:")
            for report_type, file_path in report_files.items():
                print(f"  {report_type}: {file_path}")
            
            # 显示最佳基金
            if not results_df.empty and 'composite_score' in results_df.columns:
                best_fund = results_df.loc[results_df['composite_score'].idxmax()]
                print(f"\n🏆 最佳表现基金:")
                print(f"  基金代码: {best_fund['fund_code']}")
                print(f"  基金名称: {best_fund['fund_name']}")
                print(f"  综合评分: {best_fund['composite_score']:.3f}")
                if 'annualized_return' in best_fund:
                    print(f"  年化收益率: {best_fund['annualized_return']*100:.2f}%")
            
            print("\n" + "="*80)
            
        except Exception as e:
            logger.error(f"打印分析摘要失败: {str(e)}")
    
    def _run_test_mode(self):
        """运行测试模式"""
        try:
            logger.info("开始运行测试模式")
            
            # 创建测试数据 - 使用真实的基金代码
            test_fund_data = pd.DataFrame({
                '代码': ['000001', '110022', '161725', '270002', '519674'],  # 使用真实基金代码
                '名称': ['华夏成长混合', '易方达消费行业股票', '招商中证白酒指数', '广发稳健增长混合', '银河创新成长混合']
            })
            
            # 运行完整分析流程
            analysis_date = datetime.now().strftime('%Y-%m-%d')
            
            # 1. 分析所有基金
            results = self.analyze_all_funds(test_fund_data, analysis_date)
            
            if results:
                # 转换为DataFrame
                results_df = pd.DataFrame(results)
                
                # 2. 生成策略汇总
                strategy_summary = self.generate_strategy_summary(results)
                
                # 3. 生成分析图表（简化版）
                print("\n📊 测试数据分析结果:")
                print(f"分析基金数量: {len(results)}")
                if 'annualized_return' in results_df.columns:
                    print(f"平均年化收益率: {results_df['annualized_return'].mean()*100:.2f}%")
                if 'sharpe_ratio' in results_df.columns:
                    print(f"平均夏普比率: {results_df['sharpe_ratio'].mean():.3f}")
                if 'composite_score' in results_df.columns:
                    print(f"平均综合评分: {results_df['composite_score'].mean():.3f}")
                
                print("\n📈 策略信号统计:")
                if strategy_summary:
                    print(f"  总基金数: {strategy_summary.get('total_funds', 0)}")
                    print(f"  上涨基金: {strategy_summary.get('positive_return_funds', 0)}")
                    print(f"  下跌基金: {strategy_summary.get('negative_return_funds', 0)}")
                
                # 显示最佳基金
                if not results_df.empty and 'composite_score' in results_df.columns:
                    best_fund = results_df.loc[results_df['composite_score'].idxmax()]
                    print(f"\n🏆 最佳表现基金:")
                    print(f"  基金代码: {best_fund['fund_code']}")
                    print(f"  基金名称: {best_fund['fund_name']}")
                    print(f"  综合评分: {best_fund['composite_score']:.3f}")
                    if 'annualized_return' in best_fund:
                        print(f"  年化收益率: {best_fund['annualized_return']*100:.2f}%")
                
                print("\n✅ 测试模式运行成功")
            else:
                print("\n❌ 测试模式运行失败：没有获取到分析结果")
            
        except Exception as e:
            logger.error(f"测试模式运行失败: {str(e)}")
            print(f"\n❌ 测试模式运行失败: {str(e)}")
    
    def analyze_funds(self, excel_file_path: str = None) -> pd.DataFrame:
        """
        分析所有持仓基金的收益率变化，并发送通知
        
        参数：
        excel_file_path: Excel文件路径（可选，使用配置文件中的默认路径）
        
        返回：
        DataFrame: 分析结果
        """
        logger.info("开始分析所有持仓基金的收益率变化")
        
        try:
            # 使用配置文件中的默认路径，如果没有指定
            if not excel_file_path:
                excel_file_path = BASE_CONFIG.get('fund_position_file', '')
            
            # 1. 加载基金数据
            fund_data = self.load_fund_data_from_excel(excel_file_path)
            if fund_data.empty:
                logger.error("没有获取到有效的基金数据")
                return pd.DataFrame()
            
            analysis_date = datetime.now().strftime('%Y-%m-%d')
            
            # 2. 分析所有基金
            results = self.analyze_all_funds(fund_data, analysis_date)
            if not results:
                logger.error("基金分析失败")
                return pd.DataFrame()
            
            # 转换为DataFrame
            results_df = pd.DataFrame(results)
            
            # 3. 生成策略汇总
            strategy_summary = self.generate_strategy_summary(results)
            
            # 4. 生成分析图表报告
            report_files = self.generate_analytics_reports(results_df, "./reports/")
            
            # 5. 保存结果到数据库
            db_success = self.save_results_to_database(results, strategy_summary, report_files)
            if not db_success:
                logger.warning("数据库保存失败，但继续执行后续步骤")
            
            # 6. 发送通知报告
            notification_success = self.send_notification_reports(results_df, strategy_summary, report_files)
            if not notification_success:
                logger.warning("通知发送失败，但分析流程已完成")
            
            logger.info("基金分析完成")
            return results_df
            
        except Exception as e:
            logger.error(f"分析基金收益率时出错: {str(e)}")
            return pd.DataFrame()
    
    def compare_fund_performance(self) -> pd.DataFrame:
        """
        对比基金的综合绩效指标
        
        返回：
        DataFrame: 包含基金代码、名称和各项绩效指标的对比数据
        """
        logger.info("开始基金绩效对比分析...")
        
        try:
            # 获取所有持仓基金
            fund_data = self.load_fund_data_from_excel(BASE_CONFIG.get('fund_position_file', ''))
            if fund_data.empty:
                logger.error("没有获取到有效的基金数据")
                return pd.DataFrame()
            
            # 分析所有基金
            results = []
            today_str = datetime.now().strftime('%Y%m%d')
            
            for _, row in fund_data.iterrows():
                fund_code = str(row['代码']).zfill(6)
                fund_name = row.get('名称', f'基金{fund_code}')
                
                try:
                    logger.info(f"正在分析基金: {fund_code} ({fund_name})")
                    
                    # 获取基金实时数据
                    fund_info = self.fund_data_manager.get_realtime_data(fund_code)
                    if not fund_info:
                        logger.warning(f"无法获取基金 {fund_code} 的实时数据")
                        continue
                    
                    # 获取基金绩效指标
                    metrics = self.fund_data_manager.get_performance_metrics(fund_code)
                    
                    result = {
                        'fund_code': fund_code,
                        'fund_name': fund_name,
                        'today_return': float(fund_info.get('daily_return', 0)),
                        'nav': float(fund_info.get('nav', 0)),
                        **metrics
                    }
                    
                    results.append(result)
                    logger.info(f"基金 {fund_code} 分析完成")
                    
                except Exception as e:
                    logger.error(f"分析基金 {fund_code} 时出错: {str(e)}")
                    continue
            
            # 转换为DataFrame
            df = pd.DataFrame(results)
            
            if df.empty:
                logger.error("没有获取到有效的基金对比数据")
                return pd.DataFrame()
            
            # 生成对比图表
            self.analytics_engine.generate_comprehensive_report(df, './reports/')
            
            return df
            
        except Exception as e:
            logger.error(f"进行基金绩效对比时出错: {str(e)}")
            return pd.DataFrame()
    
    def cleanup(self):
        """清理资源"""
        try:
            # 关闭数据库连接
            self.db_manager.close_connection()
            logger.info("系统资源清理完成")
        except Exception as e:
            logger.error(f"清理资源失败: {str(e)}")


def main():
    """主函数"""
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(
        description='增强版基金分析系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python enhanced_main.py                    # 使用默认配置文件运行完整分析
  python enhanced_main.py --file path/to/excel.xlsx  # 指定Excel文件路径
  python enhanced_main.py --output ./my_reports/     # 指定输出目录
  python enhanced_main.py --test                    # 运行测试模式
  python enhanced_main.py --analyze                 # 分析持仓基金
  python enhanced_main.py --compare                 # 对比基金绩效
  python enhanced_main.py --all                     # 执行完整分析流程
        """
    )
    
    parser.add_argument(
        '--file', '-f',
        type=str,
        help='Excel文件路径（可选，使用配置文件中的默认路径）'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='./reports/',
        help='输出目录（默认: ./reports/）'
    )
    
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='运行测试模式'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细日志'
    )
    
    parser.add_argument(
        '--analyze', '-a',
        action='store_true',
        help='分析持仓基金'
    )
    
    parser.add_argument(
        '--compare', '-c',
        action='store_true',
        help='对比基金绩效'
    )
    
    parser.add_argument(
        '--all', '-A',
        action='store_true',
        help='执行完整分析流程（等同于run_complete_analysis）'
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # 创建基金分析系统
        system = EnhancedFundAnalysisSystem()
        
        if args.test:
            # 运行测试模式
            logger.info("运行测试模式")
            system._run_test_mode()
        elif args.analyze:
            # 分析持仓基金
            logger.info("开始分析持仓基金")
            results_df = system.analyze_funds(args.file)
            if not results_df.empty:
                logger.info("持仓基金分析完成")
                print(f"\n分析完成，共分析 {len(results_df)} 只基金")
                sys.exit(0)
            else:
                logger.error("持仓基金分析失败")
                sys.exit(1)
        elif args.compare:
            # 对比基金绩效
            logger.info("开始对比基金绩效")
            comparison_df = system.compare_fund_performance()
            if not comparison_df.empty:
                logger.info("基金绩效对比完成")
                print(f"\n对比完成，共对比 {len(comparison_df)} 只基金")
                sys.exit(0)
            else:
                logger.error("基金绩效对比失败")
                sys.exit(1)
        elif args.all:
            # 执行完整分析流程
            logger.info("执行完整分析流程")
            success = system.run_complete_analysis(args.file, args.output)
            
            if success:
                logger.info("基金分析任务成功完成")
                sys.exit(0)
            else:
                logger.error("基金分析任务失败")
                sys.exit(1)
        else:
            # 默认运行完整分析
            logger.info("运行完整分析流程（默认）")
            success = system.run_complete_analysis(args.file, args.output)
            
            if success:
                logger.info("基金分析任务成功完成")
                sys.exit(0)
            else:
                logger.error("基金分析任务失败")
                sys.exit(1)
        
        # 清理资源
        system.cleanup()
        
    except KeyboardInterrupt:
        logger.info("用户中断程序执行")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()