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
                sheet_name = BASE_CONFIG['sheet_name']
            
            # 读取Excel文件
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            logger.info(f"成功读取Excel文件，共 {len(df)} 行数据")
            
            # 过滤有效基金代码（只保留数字代码）
            valid_df = df[df['代码'].astype(str).str.isdigit()].copy()
            logger.info(f"过滤后有效基金数据: {len(valid_df)} 条")
            
            # 格式化基金代码为6位
            valid_df['代码'] = valid_df['代码'].astype(str).str.zfill(6)
            
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
            # 优先使用实时数据中的daily_return（来自AKShare的日增长率字段，已是百分比格式）
            today_return = realtime_data.get('daily_return', 0.0)
            prev_day_return = 0.0
            
            # 从历史数据获取前一日收益率
            if not historical_data.empty and 'daily_growth_rate' in historical_data.columns:
                # 使用AKShare原始的日增长率字段（已是百分比格式）
                recent_growth = historical_data['daily_growth_rate'].dropna().tail(2)
                if len(recent_growth) >= 2:
                    prev_day_return = float(recent_growth.iloc[-2]) if pd.notna(recent_growth.iloc[-2]) else 0.0
                elif len(recent_growth) == 1:
                    prev_day_return = float(recent_growth.iloc[-1]) if pd.notna(recent_growth.iloc[-1]) else 0.0
            elif not historical_data.empty and 'daily_return' in historical_data.columns:
                # 备用方案：使用pct_change计算的收益率（小数格式，需要乘100）
                recent_returns = historical_data['daily_return'].dropna().tail(2)
                if len(recent_returns) >= 2:
                    prev_day_return = recent_returns.iloc[-2] * 100
                elif len(recent_returns) == 1:
                    prev_day_return = recent_returns.iloc[-1] * 100
            
            # 投资策略分析
            strategy_result = self.strategy_engine.analyze_strategy(
                today_return, prev_day_return, performance_metrics
            )
            
            # 合并所有数据
            fund_result = {
                'fund_code': fund_code,
                'fund_name': fund_name,
                'analysis_date': analysis_date,
                **basic_info,
                **realtime_data,
                **performance_metrics,
                **strategy_result,
                'today_return': today_return,
                'prev_day_return': prev_day_return,
                'daily_return': today_return  # 用于收益率分析图表
            }
            
            # 调试日志
            logger.debug(f"基金 {fund_code} 分析结果包含的键: {list(fund_result.keys())}")
            logger.debug(f"daily_return值: {fund_result.get('daily_return')}")
            logger.debug(f"today_return值: {fund_result.get('today_return')}")
            
            logger.info(f"基金 {fund_code} 分析完成，综合评分: {performance_metrics.get('composite_score', 0):.3f}")
            return fund_result
            
        except Exception as e:
            logger.error(f"分析基金 {fund_code} 失败: {str(e)}")
            # 返回默认结果
            return {
                'fund_code': fund_code,
                'fund_name': fund_name,
                'analysis_date': analysis_date,
                'today_return': 0.0,
                'prev_day_return': 0.0,
                'daily_return': 0.0,  # 用于收益率分析图表
                'status_label': "🔴 **分析失败**",
                'operation_suggestion': "数据获取失败，建议人工核查",
                'execution_amount': "持有不动",
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
            
            # 确保所有结果都包含daily_return字段
            for i, result in enumerate(results):
                # 明确添加daily_return字段，覆盖可能存在的任何问题
                logger.info(f"为基金 {result.get('fund_code', '未知')} 添加/更新daily_return字段")
                results[i]['daily_return'] = result.get('today_return', 0.0)  # 确保使用today_return的值
            
            # 再次检查并确认
            for i, result in enumerate(results):
                if 'daily_return' not in result:
                    logger.error(f"基金 {result.get('fund_code', '未知')} 仍然缺少daily_return字段")
                else:
                    logger.debug(f"基金 {result.get('fund_code', '未知')} 的daily_return值: {result['daily_return']}")
            
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
            # 获取基础策略汇总
            base_summary = self.strategy_engine.generate_strategy_summary(results)
            
            if not base_summary:
                return {}
            
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
                'action_distribution': {},
                'avg_buy_multiplier': 0.0,
                'total_redeem_amount': 0,
                'buy_signals': 0,
                'sell_signals': 0,
                'hold_signals': 0,
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
                excel_file_path = BASE_CONFIG['fund_position_file']
            
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
                print(f"平均年化收益率: {results_df['annualized_return'].mean()*100:.2f}%")
                print(f"平均夏普比率: {results_df['sharpe_ratio'].mean():.3f}")
                print(f"平均最大回撤: {results_df['max_drawdown'].mean()*100:.2f}%")
                print(f"平均综合评分: {results_df['composite_score'].mean():.3f}")
            
            print("\n📈 策略信号统计:")
            if strategy_summary:
                for action, count in strategy_summary.get('action_distribution', {}).items():
                    print(f"  {action}: {count} 只基金")
                print(f"  平均买入倍数: {strategy_summary.get('avg_buy_multiplier', 0):.2f}")
                print(f"  总赎回金额: ¥{strategy_summary.get('total_redeem_amount', 0)}")
            
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
                print(f"  年化收益率: {best_fund['annualized_return']*100:.2f}%")
            
            print("\n" + "="*80)
            
        except Exception as e:
            logger.error(f"打印分析摘要失败: {str(e)}")
    
    def _run_test_mode(self):
        """运行测试模式"""
        try:
            logger.info("开始运行测试模式")
            
            # 创建测试数据
            test_fund_data = pd.DataFrame({
                '代码': ['000001', '000002', '000003', '000004', '000005'],
                '名称': ['测试基金1', '测试基金2', '测试基金3', '测试基金4', '测试基金5'],
                '持有金额': [1000, 2000, 1500, 3000, 2500],
                '当日盈亏': [10, 25, -15, 30, -5],
                '当日盈亏率': [0.01, 0.0125, -0.01, 0.01, -0.002],
                '持有盈亏': [50, 100, -50, 150, 75],
                '持有盈亏率': [0.05, 0.05, -0.033, 0.05, 0.03]
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
                print(f"平均年化收益率: {results_df['annualized_return'].mean()*100:.2f}%")
                print(f"平均夏普比率: {results_df['sharpe_ratio'].mean():.3f}")
                print(f"平均综合评分: {results_df['composite_score'].mean():.3f}")
                
                print("\n📈 策略信号统计:")
                if strategy_summary:
                    for action, count in strategy_summary.get('action_distribution', {}).items():
                        print(f"  {action}: {count} 只基金")
                    print(f"  平均买入倍数: {strategy_summary.get('avg_buy_multiplier', 0):.2f}")
                
                # 显示最佳基金
                if not results_df.empty and 'composite_score' in results_df.columns:
                    best_fund = results_df.loc[results_df['composite_score'].idxmax()]
                    print(f"\n🏆 最佳表现基金:")
                    print(f"  基金代码: {best_fund['fund_code']}")
                    print(f"  基金名称: {best_fund['fund_name']}")
                    print(f"  综合评分: {best_fund['composite_score']:.3f}")
                    print(f"  年化收益率: {best_fund['annualized_return']*100:.2f}%")
                
                print("\n✅ 测试模式运行成功")
            else:
                print("\n❌ 测试模式运行失败：没有获取到分析结果")
            
        except Exception as e:
            logger.error(f"测试模式运行失败: {str(e)}")
            print(f"\n❌ 测试模式运行失败: {str(e)}")
    
    def generate_wechat_message(self, result_df: pd.DataFrame) -> str:
        """
        根据基金分析结果生成微信通知的HTML消息
        
        参数：
        result_df: 基金分析结果的DataFrame
        
        返回：
        str: 格式化的HTML消息内容
        """
        try:
            # 创建一个副本用于格式化显示
            df_display = result_df.copy()
            
            # 格式化收益率为百分比
            if 'today_return' in df_display.columns:
                df_display['today_return'] = df_display['today_return'].map('{:.2f}%'.format)
            if 'prev_day_return' in df_display.columns:
                df_display['prev_day_return'] = df_display['prev_day_return'].map('{:.2f}%'.format)
            if 'comparison_value' in df_display.columns:
                df_display['comparison_value'] = df_display['comparison_value'].map('{:.2f}%'.format)
            
            # 按照操作建议和执行金额排序
            if 'operation_suggestion' in df_display.columns and 'execution_amount' in df_display.columns:
                df_display = df_display.sort_values(by=['operation_suggestion', 'execution_amount'])
            
            # 生成HTML消息
            message = f"<h2>📊 基金分析报告 - {datetime.now().strftime('%Y年%m月%d日')}</h2>\n"
            message += f"<h3>持仓基金收益率变化分析</h3>\n"
            message += f"<table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse; width: 100%;'>\n"
            message += f"<thead>\n"
            message += f"<tr style='background-color: #f0f0f0;'>\n"
            message += f"<th>基金代码</th>\n"
            message += f"<th>基金名称</th>\n"
            message += f"<th>今日收益率</th>\n"
            message += f"<th>昨日收益率</th>\n"
            message += f"<th>趋势状态</th>\n"
            message += f"<th>操作建议</th>\n"
            message += f"<th>执行金额</th>\n"
            message += f"</tr>\n"
            message += f"</thead>\n"
            message += f"<tbody>\n"
            
            for _, row in df_display.iterrows():
                message += f"<tr>\n"
                message += f"<td>{row.get('fund_code', '')}</td>\n"
                message += f"<td>{row.get('fund_name', '')}</td>\n"
                message += f"<td>{row.get('today_return', '0.00%')}</td>\n"
                message += f"<td>{row.get('prev_day_return', '0.00%')}</td>\n"
                message += f"<td>{row.get('status_label', '')}</td>\n"
                message += f"<td>{row.get('operation_suggestion', '')}</td>\n"
                message += f"<td>{row.get('execution_amount', '')}</td>\n"
                message += f"</tr>\n"
            
            message += f"</tbody>\n"
            message += f"</table>\n"
            message += f"<p style='margin-top: 15px; color: #666; font-size: 14px;'>"
            message += f"<strong>提示</strong>：以上分析基于实时估值数据，仅供参考。最终投资决策请结合市场情况谨慎考虑。"
            message += f"</p>"
            
            return message
            
        except Exception as e:
            logger.error(f"生成微信消息失败: {str(e)}")
            return f"<h2>基金分析报告</h2><p>数据生成失败: {str(e)}</p>"
    
    def get_investment_strategy(self, today_return: float, prev_day_return: float) -> tuple:
        """
        根据当日收益率和前一日收益率，返回投资策略结果
        
        参数：
        today_return: 当日收益率（%）
        prev_day_return: 前一日收益率（%）
        
        返回：
        tuple: (status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, execution_amount, buy_multiplier)
        """
        return_diff = today_return - prev_day_return
        
        # 1. 今日>0 昨日>0 today-prev>1%
        if today_return > 0 and prev_day_return > 0:
            if return_diff > 1:
                status_label = "🟢 **大涨**"
                is_buy = False
                redeem_amount = 0
                buy_multiplier = 0
                operation_suggestion = "不买入，不赎回"
                execution_amount = "持有不动"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 2. 今日>0 昨日>0 0<today-prev≤1%
            elif 0 < return_diff <= 1:
                status_label = "🟡 **连涨加速**"
                is_buy = False
                redeem_amount = 15
                buy_multiplier = 0
                operation_suggestion = "不买入，赎回15元"
                execution_amount = "赎回¥15"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 3. 今日>0 昨日>0 -1%≤today-prev≤0
            elif -1 <= return_diff <= 0:
                status_label = "🟠 **连涨放缓**"
                is_buy = False
                redeem_amount = 0
                buy_multiplier = 0
                operation_suggestion = "不买入，不赎回"
                execution_amount = "持有不动"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 4. 今日>0 昨日>0 today-prev<-1%
            elif return_diff < -1:
                status_label = "🟠 **连涨回落**"
                is_buy = False
                redeem_amount = 0
                buy_multiplier = 0
                operation_suggestion = "不买入，不赎回"
                execution_amount = "持有不动"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 5. 今日>0 昨日≤0
        elif today_return > 0 and prev_day_return <= 0:
            status_label = "🔵 **反转涨**"
            is_buy = True
            redeem_amount = 0
            buy_multiplier = 1.5
            operation_suggestion = "定投买入，不赎回"
            execution_amount = f"买入{buy_multiplier}×定额"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 6. 今日=0 昨日>0
        elif today_return == 0 and prev_day_return > 0:
            status_label = "🔴 **转势休整**"
            is_buy = False
            redeem_amount = 30
            buy_multiplier = 0
            operation_suggestion = "不买入，赎回30元"
            execution_amount = "赎回¥30"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 7. 今日<0 昨日>0
        elif today_return < 0 and prev_day_return > 0:
            status_label = "🔴 **反转跌**"
            is_buy = False
            redeem_amount = 30
            buy_multiplier = 0
            operation_suggestion = "不买入，赎回30元"
            execution_amount = "赎回¥30"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 8. 今日=0 昨日≤0
        elif today_return == 0 and prev_day_return <= 0:
            status_label = "⚪ **绝对企稳**"
            is_buy = True
            redeem_amount = 0
            buy_multiplier = 3.0
            operation_suggestion = "定投买入，不赎回"
            execution_amount = f"买入{buy_multiplier}×定额"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 9. 今日<0 昨日=0 today≤-2%
        elif today_return < 0 and prev_day_return == 0:
            if today_return <= -2:
                status_label = "🔴 **首次大跌**"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 0.5
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 10. 今日<0 昨日=0 -2%<today≤-0.5%
            elif -2 < today_return <= -0.5:
                status_label = "🟠 **首次下跌**"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 1.5
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 11. 今日<0 昨日=0 today>-0.5%
            elif today_return > -0.5:
                status_label = "🔵 **微跌试探**"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 1.0
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 12. 今日<0 昨日<0 (today-prev)>1% & today≤-2%
        elif today_return < 0 and prev_day_return < 0:
            if return_diff > 1 and today_return <= -2:
                status_label = "🔴 **暴跌加速**"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 0.5
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 13. 今日<0 昨日<0 (today-prev)>1% & today>-2%
            elif return_diff > 1 and today_return > -2:
                status_label = "🟣 **跌速扩大**"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 1.0
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 14. 今日<0 昨日<0 (prev-today)>0 & prev≤-2%
            elif (prev_day_return - today_return) > 0 and prev_day_return <= -2:
                status_label = "🔵 **暴跌回升**"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 1.5
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 15. 今日<0 昨日<0 (prev-today)>0 & prev>-2%
            elif (prev_day_return - today_return) > 0 and prev_day_return > -2:
                status_label = "🟦 **跌速放缓**"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 1.0
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 16. 今日<0 昨日<0 abs差值≤1%
            elif abs(return_diff) <= 1:
                status_label = "🟣 **阴跌筑底**"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 1.0
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 默认情况（不应该发生）
        status_label = "🔴 **未知**"
        is_buy = False
        redeem_amount = 0
        buy_multiplier = 0
        operation_suggestion = "不买入，不赎回"
        execution_amount = "持有不动"
        return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
    
    def plot_annualized_returns(self, comparison_df: pd.DataFrame, today_str: str) -> bool:
        """
        绘制优化的年化收益率对比图表
        
        参数：
        comparison_df: 包含基金绩效对比数据的DataFrame
        today_str: 今天的日期字符串
        
        返回：
        bool: 是否成功生成图表
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            from shared.enhanced_config import BASE_CONFIG
            
            # 过滤掉年化收益率为空的数据
            valid_data = comparison_df.dropna(subset=['annualized_return'])
            if len(valid_data) == 0:
                logger.warning("没有有效的年化收益率数据")
                return False
            
            # 准备数据
            n_funds = len(valid_data)
            indices = np.arange(n_funds)
            returns = valid_data['annualized_return'] * 100
            
            # 使用现代化的配色方案
            colors = ['#08804B' if x >= 5 else '#2E8B57' if x >= 0 else '#CD5C5C' for x in returns]
            
            # 创建专业级图表
            fig, ax = plt.subplots(figsize=(16, 10))
            
            # 绘制改进的柱状图
            bars = ax.bar(indices, returns, alpha=0.85, color=colors, 
                       edgecolor='white', linewidth=1.2)
            
            # 现代化的图表属性
            ax.set_xlabel('基金代码', fontsize=14, fontweight='bold', color='#2C3E50')
            ax.set_ylabel('年化收益率 (%)', fontsize=14, fontweight='bold', color='#2C3E50')
            ax.set_title('📊 基金年化收益率对比分析', fontsize=18, fontweight='bold', color='#2C3E50')
            ax.set_xticks(indices)
            ax.set_xticklabels(valid_data['fund_code'], rotation=45, ha='right', fontsize=12)
            ax.grid(True, alpha=0.4, linestyle='-')
            
            # 添加专业的零基准线
            ax.axhline(y=0, color='#95A5A6', linestyle='-', alpha=0.3)
            
            # 改进的数值标签
            for bar, value in zip(bars, returns):
                height = bar.get_height()
                # 根据收益水平使用不同颜色的标签
                label_color = '#2C3E50' if abs(value) < 1 else '#27AE60' if value >= 0 else '#E74C3C'
                ax.text(bar.get_x() + bar.get_width()/2., 
                        height + (0.2 if value >= 0 else -0.2),
                        f'{value:.2f}%', 
                        ha='center', va='bottom' if value >= 0 else 'top',
                        fontsize=11, fontweight='bold', color=label_color)
            
            # 智能图例系统 - 优化中文显示
            # 根据基金数量自动调整显示策略
            display_strategy = "smart_wrap" if n_funds > 8 else "side_panel"
            
            if display_strategy == "smart_wrap":
                # 智能换行显示基金名称（中文优化）
                rows = (n_funds + 4) // 5  # 每行最多5个
                for i in range(rows):
                    start_idx = i * 5
                    end_idx = min((i + 1) * 5, n_funds)
                    y_position = 0.85 - i * 0.05
                    for j in range(start_idx, end_idx):
                        name = valid_data.iloc[j]['fund_name']
                        code = valid_data.iloc[j]['fund_code']
                        # 智能截断中文名称，优先显示中文部分
                        if len(name) > 12:  # 中文字符截断长度
                            display_name = name[:10] + '...'
                        else:
                            display_name = name
                        ax.text(1.02, y_position, f'{code}: {display_name}',
                        transform=ax.transAxes, ha='left', va='top', fontsize=10, 
                        fontproperties='SimHei')  # 明确指定中文字体
            else:
                # 侧边栏显示（中文优化）
                fund_names = valid_data['fund_name'].tolist()
                if fund_names:
                    ax.text(1.02, 0.95, '基金名称:', transform=ax.transAxes, 
                           fontweight='bold', ha='left', va='top', fontsize=11,
                           fontproperties='SimHei')
                    for i, (name, code) in enumerate(zip(fund_names, valid_data['fund_code'])):
                        # 智能处理中文名称显示
                        if len(name) > 15:
                            display_name = name[:13] + '...'
                        else:
                            display_name = name
                        y_pos = 0.90 - i * 0.04
                        ax.text(1.02, y_pos, f'{code}: {display_name}',
                               transform=ax.transAxes, ha='left', va='top', fontsize=10,
                               fontproperties='SimHei')
            
            # 专业的布局调整
            plt.tight_layout()
            
            # 保存高品质图表到指定目录
            report_dir = BASE_CONFIG.get('report_output_dir', './reports/')
            chart_filename = f'年化收益率对比图_{today_str}.png'
            chart_path = os.path.join(report_dir, chart_filename)
            
            os.makedirs(report_dir, exist_ok=True)
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')  # 提高图像质量
            plt.close()
            
            logger.info(f"年化收益率对比图表已保存为: {chart_path}")
            return True
            
        except Exception as e:
            logger.error(f"生成年化收益率对比图表时出错: {str(e)}")
            return False
    
    def generate_comprehensive_charts(self, comparison_df: pd.DataFrame, today_str: str) -> Dict[str, str]:
        """
        生成综合图表报告
        
        参数：
        comparison_df: 包含基金绩效对比数据的DataFrame
        today_str: 今天的日期字符串
        
        返回：
        dict: 生成的图表文件路径
        """
        try:
            logger.info("开始生成综合图表报告")
            
            report_files = {}
            
            # 1. 年化收益率对比图
            if self.plot_annualized_returns(comparison_df, today_str):
                report_files['annualized_returns'] = f'年化收益率对比图_{today_str}.png'
            
            # 2. 最大回撤对比图
            if self.plot_max_drawdown(comparison_df, today_str):
                report_files['max_drawdown'] = f'最大回撤对比图_{today_str}.png'
            
            # 3. 夏普比率对比图
            if self.plot_sharpe_ratio(comparison_df, today_str):
                report_files['sharpe_ratio'] = f'夏普比率对比图_{today_str}.png'
            
            # 4. 波动率对比图
            if self.plot_volatility(comparison_df, today_str):
                report_files['volatility'] = f'波动率对比图_{today_str}.png'
            
            # 5. 日收益率对比图
            if self.plot_daily_returns_comparison(comparison_df, today_str):
                report_files['daily_returns'] = f'日收益率对比图_{today_str}.png'
            
            logger.info(f"综合图表报告生成完成，共生成 {len(report_files)} 个图表")
            return report_files
            
        except Exception as e:
            logger.error(f"生成综合图表报告失败: {str(e)}")
            return {}
    
    def plot_max_drawdown(self, comparison_df: pd.DataFrame, today_str: str) -> bool:
        """
        绘制最大回撤对比图表
        
        参数：
        comparison_df: 包含基金绩效对比数据的DataFrame
        today_str: 今天的日期字符串
        
        返回：
        bool: 是否成功生成图表
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            from shared.enhanced_config import BASE_CONFIG
            
            # 过滤掉最大回撤为空的数据
            valid_data = comparison_df.dropna(subset=['max_drawdown'])
            if len(valid_data) == 0:
                logger.warning("没有有效的最大回撤数据")
                return False
            
            # 准备数据（转换为百分比）
            n_funds = len(valid_data)
            indices = np.arange(n_funds)
            drawdown_values = valid_data['max_drawdown'] * 100  # 转换为百分比
            
            # 设置颜色：回撤越深（负值越大）用更红的颜色表示，较小回撤用较浅颜色
            colors = ['#CD5C5C' if x < 0 else '#2E8B57' for x in drawdown_values]
            
            # 创建图表
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # 绘制柱状图
            bars = ax.bar(indices, drawdown_values, alpha=0.8, color=colors, edgecolor='black', linewidth=0.5)
            
            # 设置图表属性
            ax.set_xlabel('基金代码', fontsize=12, fontweight='bold')
            ax.set_ylabel('最大回撤 (%)', fontsize=12, fontweight='bold')
            ax.set_title('基金最大回撤对比', fontweight='bold', fontsize=16, pad=20)
            ax.set_xticks(indices)
            ax.set_xticklabels(valid_data['fund_code'], rotation=45, ha='right', fontsize=10)
            ax.grid(True, alpha=0.3, axis='y')
            
            # 添加零基准线
            ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            
            # 在柱子上添加数值标签
            for bar, value in zip(bars, drawdown_values):
                height = bar.get_height()
                # 根据值的正负决定标签位置
                if height >= 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height + max(0.1 * abs(height), 0.2),
                            f'{value:.2f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
                else:
                    ax.text(bar.get_x() + bar.get_width()/2., height - max(0.1 * abs(height), 0.2),
                            f'{value:.2f}%', ha='center', va='top', fontsize=9, fontweight='bold')
            
            # 创建图例（中文优化）
            from matplotlib.patches import Patch
            legend_elements = [Patch(facecolor='#2E8B57', label='较小回撤'),
                              Patch(facecolor='#CD5C5C', label='较大回撤')]
            ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0, 1), 
                     fontsize=10, prop={'family': 'SimHei'})  # 明确指定中文字体
            
            # 在右侧显示基金名称（中文优化）
            fund_names = valid_data['fund_name'].tolist()
            if fund_names:
                # 计算合适的文本位置
                y_positions = np.linspace(ax.get_ylim()[1] * 0.8, ax.get_ylim()[1] * 0.3, len(fund_names))
                for i, (name, code) in enumerate(zip(fund_names, valid_data['fund_code'])):
                    # 智能处理中文名称显示
                    if len(name) > 15:  # 中文字符截断长度
                        display_name = name[:13] + '...'
                    else:
                        display_name = name
                    ax.annotate(f'{code}: {display_name}', 
                               xy=(1, y_positions[i]), 
                               xytext=(5, 0), 
                               xycoords=('axes fraction', 'data'),
                               textcoords='offset points',
                               va='center', ha='left', fontsize=9,
                               fontproperties='SimHei',  # 明确指定中文字体
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgray', alpha=0.7))
            
            # 调整布局
            plt.tight_layout()
            
            # 保存图表到指定目录
            report_dir = BASE_CONFIG.get('report_output_dir', './reports/')
            chart_filename = f'最大回撤对比图_{today_str}.png'
            chart_path = os.path.join(report_dir, chart_filename)
            
            os.makedirs(report_dir, exist_ok=True)
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            logger.info(f"最大回撤对比图表已保存为: {chart_path}")
            return True
            
        except Exception as e:
            logger.error(f"生成最大回撤对比图表时出错: {str(e)}")
            return False
    
    def plot_sharpe_ratio(self, comparison_df: pd.DataFrame, today_str: str) -> bool:
        """
        绘制夏普比率对比图表
        
        参数：
        comparison_df: 包含基金绩效对比数据的DataFrame
        today_str: 今天的日期字符串
        
        返回：
        bool: 是否成功生成图表
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            from shared.enhanced_config import BASE_CONFIG
            
            # 过滤掉夏普比率为空的数据
            valid_data = comparison_df.dropna(subset=['sharpe_ratio'])
            if len(valid_data) == 0:
                logger.warning("没有有效的夏普比率数据")
                return False
            
            # 准备数据
            n_funds = len(valid_data)
            indices = np.arange(n_funds)
            sharpe_values = valid_data['sharpe_ratio']
            
            # 设置颜色：夏普比率越高用越绿的颜色，越低用越红的颜色
            colors = ['#08804B' if x >= 1.0 else '#2E8B57' if x >= 0.5 else '#CD5C5C' for x in sharpe_values]
            
            # 创建图表
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # 绘制柱状图
            bars = ax.bar(indices, sharpe_values, alpha=0.8, color=colors, edgecolor='black', linewidth=0.5)
            
            # 设置图表属性
            ax.set_xlabel('基金代码', fontsize=12, fontweight='bold')
            ax.set_ylabel('夏普比率', fontsize=12, fontweight='bold')
            ax.set_title('基金夏普比率对比', fontweight='bold', fontsize=16, pad=20)
            ax.set_xticks(indices)
            ax.set_xticklabels(valid_data['fund_code'], rotation=45, ha='right', fontsize=10)
            ax.grid(True, alpha=0.3, axis='y')
            
            # 添加零基准线
            ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            
            # 在柱子上添加数值标签
            for bar, value in zip(bars, sharpe_values):
                height = bar.get_height()
                # 根据值的正负决定标签位置
                if height >= 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height + max(0.02 * abs(height), 0.02),
                            f'{value:.2f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
                else:
                    ax.text(bar.get_x() + bar.get_width()/2., height - max(0.02 * abs(height), 0.02),
                            f'{value:.2f}', ha='center', va='top', fontsize=9, fontweight='bold')
            
            # 创建图例（中文优化）
            from matplotlib.patches import Patch
            legend_elements = [Patch(facecolor='#08804B', label='优秀 (≥1.0)'),
                              Patch(facecolor='#2E8B57', label='良好 (0.5-1.0)'),
                              Patch(facecolor='#CD5C5C', label='较差 (<0.5)')]
            ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0, 1), 
                     fontsize=10, prop={'family': 'SimHei'})  # 明确指定中文字体
            
            # 在右侧显示基金名称（中文优化）
            fund_names = valid_data['fund_name'].tolist()
            if fund_names:
                # 计算合适的文本位置
                y_positions = np.linspace(ax.get_ylim()[1] * 0.8, ax.get_ylim()[1] * 0.3, len(fund_names))
                for i, (name, code) in enumerate(zip(fund_names, valid_data['fund_code'])):
                    # 智能处理中文名称显示
                    if len(name) > 15:  # 中文字符截断长度
                        display_name = name[:13] + '...'
                    else:
                        display_name = name
                    ax.annotate(f'{code}: {display_name}', 
                               xy=(1, y_positions[i]), 
                               xytext=(5, 0), 
                               xycoords=('axes fraction', 'data'),
                               textcoords='offset points',
                               va='center', ha='left', fontsize=9,
                               fontproperties='SimHei',  # 明确指定中文字体
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgray', alpha=0.7))
            
            # 调整布局
            plt.tight_layout()
            
            # 保存图表到指定目录
            report_dir = BASE_CONFIG.get('report_output_dir', './reports/')
            chart_filename = f'夏普比率对比图_{today_str}.png'
            chart_path = os.path.join(report_dir, chart_filename)
            
            os.makedirs(report_dir, exist_ok=True)
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            logger.info(f"夏普比率对比图表已保存为: {chart_path}")
            return True
            
        except Exception as e:
            logger.error(f"生成夏普比率对比图表时出错: {str(e)}")
            return False
    
    def plot_volatility(self, comparison_df: pd.DataFrame, today_str: str) -> bool:
        """
        绘制波动率对比图表
        
        参数：
        comparison_df: 包含基金绩效对比数据的DataFrame
        today_str: 今天的日期字符串
        
        返回：
        bool: 是否成功生成图表
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            from shared.enhanced_config import BASE_CONFIG
            
            # 过滤掉波动率为空的数据
            valid_data = comparison_df.dropna(subset=['volatility'])
            if len(valid_data) == 0:
                logger.warning("没有有效的波动率数据")
                return False
            
            # 准备数据（转换为百分比）
            n_funds = len(valid_data)
            indices = np.arange(n_funds)
            volatility_values = valid_data['volatility'] * 100  # 转换为百分比
            
            # 设置颜色：波动率越高用越红的颜色，越低用越绿的颜色
            colors = ['#CD5C5C' if x >= 20 else '#FF8C00' if x >= 15 else '#2E8B57' for x in volatility_values]
            
            # 创建图表
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # 绘制柱状图
            bars = ax.bar(indices, volatility_values, alpha=0.8, color=colors, edgecolor='black', linewidth=0.5)
            
            # 设置图表属性
            ax.set_xlabel('基金代码', fontsize=12, fontweight='bold')
            ax.set_ylabel('波动率 (%)', fontsize=12, fontweight='bold')
            ax.set_title('基金波动率对比', fontweight='bold', fontsize=16, pad=20)
            ax.set_xticks(indices)
            ax.set_xticklabels(valid_data['fund_code'], rotation=45, ha='right', fontsize=10)
            ax.grid(True, alpha=0.3, axis='y')
            
            # 在柱子上添加数值标签
            for bar, value in zip(bars, volatility_values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + max(0.1 * abs(height), 0.2),
                        f'{value:.2f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
            
            # 创建图例（中文优化）
            from matplotlib.patches import Patch
            legend_elements = [Patch(facecolor='#2E8B57', label='低波动 (<15%)'),
                              Patch(facecolor='#FF8C00', label='中等波动 (15-20%)'),
                              Patch(facecolor='#CD5C5C', label='高波动 (≥20%)')]
            ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0, 1), 
                     fontsize=10, prop={'family': 'SimHei'})  # 明确指定中文字体
            
            # 在右侧显示基金名称（中文优化）
            fund_names = valid_data['fund_name'].tolist()
            if fund_names:
                # 计算合适的文本位置
                y_positions = np.linspace(ax.get_ylim()[1] * 0.8, ax.get_ylim()[1] * 0.3, len(fund_names))
                for i, (name, code) in enumerate(zip(fund_names, valid_data['fund_code'])):
                    # 智能处理中文名称显示
                    if len(name) > 15:  # 中文字符截断长度
                        display_name = name[:13] + '...'
                    else:
                        display_name = name
                    ax.annotate(f'{code}: {display_name}', 
                               xy=(1, y_positions[i]), 
                               xytext=(5, 0), 
                               xycoords=('axes fraction', 'data'),
                               textcoords='offset points',
                               va='center', ha='left', fontsize=9,
                               fontproperties='SimHei',  # 明确指定中文字体
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgray', alpha=0.7))
            
            # 调整布局
            plt.tight_layout()
            
            # 保存图表到指定目录
            report_dir = BASE_CONFIG.get('report_output_dir', './reports/')
            chart_filename = f'波动率对比图_{today_str}.png'
            chart_path = os.path.join(report_dir, chart_filename)
            
            os.makedirs(report_dir, exist_ok=True)
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            logger.info(f"波动率对比图表已保存为: {chart_path}")
            return True
            
        except Exception as e:
            logger.error(f"生成波动率对比图表时出错: {str(e)}")
            return False
    
    def plot_daily_returns_comparison(self, comparison_df: pd.DataFrame, today_str: str) -> bool:
        """
        绘制日收益率对比图表
        
        参数：
        comparison_df: 包含基金绩效对比数据的DataFrame
        today_str: 今天的日期字符串
        
        返回：
        bool: 是否成功生成图表
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            from shared.enhanced_config import BASE_CONFIG
            
            # 过滤掉日收益率为空的数据
            valid_data = comparison_df.dropna(subset=['today_return'])
            if len(valid_data) == 0:
                logger.warning("没有有效的日收益率数据")
                return False
            
            # 准备数据（转换为百分比）
            n_funds = len(valid_data)
            indices = np.arange(n_funds)
            daily_returns = valid_data['today_return'] * 100  # 转换为百分比
            
            # 设置颜色：正收益用绿色，负收益用红色，零收益用灰色
            colors = ['#2E8B57' if x > 0 else '#CD5C5C' if x < 0 else '#808080' for x in daily_returns]
            
            # 创建图表
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # 绘制柱状图
            bars = ax.bar(indices, daily_returns, alpha=0.8, color=colors, edgecolor='black', linewidth=0.5)
            
            # 设置图表属性
            ax.set_xlabel('基金代码', fontsize=12, fontweight='bold')
            ax.set_ylabel('日收益率 (%)', fontsize=12, fontweight='bold')
            ax.set_title('基金日收益率对比', fontweight='bold', fontsize=16, pad=20)
            ax.set_xticks(indices)
            ax.set_xticklabels(valid_data['fund_code'], rotation=45, ha='right', fontsize=10)
            ax.grid(True, alpha=0.3, axis='y')
            
            # 添加零基准线
            ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            
            # 在柱子上添加数值标签
            for bar, value in zip(bars, daily_returns):
                height = bar.get_height()
                # 根据值的正负决定标签位置
                if height >= 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height + max(0.1 * abs(height), 0.2),
                            f'{value:.2f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
                else:
                    ax.text(bar.get_x() + bar.get_width()/2., height - max(0.1 * abs(height), 0.2),
                            f'{value:.2f}%', ha='center', va='top', fontsize=9, fontweight='bold')
            
            # 创建图例（中文优化）
            from matplotlib.patches import Patch
            legend_elements = [Patch(facecolor='#2E8B57', label='正收益'),
                              Patch(facecolor='#CD5C5C', label='负收益'),
                              Patch(facecolor='#808080', label='零收益')]
            ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0, 1), 
                     fontsize=10, prop={'family': 'SimHei'})  # 明确指定中文字体
            
            # 在右侧显示基金名称（中文优化）
            fund_names = valid_data['fund_name'].tolist()
            if fund_names:
                # 计算合适的文本位置
                y_positions = np.linspace(ax.get_ylim()[1] * 0.8, ax.get_ylim()[1] * 0.3, len(fund_names))
                for i, (name, code) in enumerate(zip(fund_names, valid_data['fund_code'])):
                    # 智能处理中文名称显示
                    if len(name) > 15:  # 中文字符截断长度
                        display_name = name[:13] + '...'
                    else:
                        display_name = name
                    ax.annotate(f'{code}: {display_name}', 
                               xy=(1, y_positions[i]), 
                               xytext=(5, 0), 
                               xycoords=('axes fraction', 'data'),
                               textcoords='offset points',
                               va='center', ha='left', fontsize=9,
                               fontproperties='SimHei',  # 明确指定中文字体
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgray', alpha=0.7))
            
            # 调整布局
            plt.tight_layout()
            
            # 保存图表到指定目录
            report_dir = BASE_CONFIG.get('report_output_dir', './reports/')
            chart_filename = f'日收益率对比图_{today_str}.png'
            chart_path = os.path.join(report_dir, chart_filename)
            
            os.makedirs(report_dir, exist_ok=True)
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            logger.info(f"日收益率对比图表已保存为: {chart_path}")
            return True
            
        except Exception as e:
            logger.error(f"生成日收益率对比图表时出错: {str(e)}")
            return False
    
    def cleanup(self):
        """清理资源"""
        try:
            # 关闭数据库连接
            self.db_manager.close_connection()
            logger.info("系统资源清理完成")
        except Exception as e:
            logger.error(f"清理资源失败: {str(e)}")
    
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
                excel_file_path = BASE_CONFIG['fund_position_file']
            
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
            report_files = self.generate_comprehensive_charts(results_df, datetime.now().strftime('%Y%m%d'))
            
            # 5. 保存结果到数据库
            db_success = self.save_results_to_database(results, strategy_summary, report_files)
            if not db_success:
                logger.warning("保存到数据库失败，但继续执行")
            
            # 6. 发送通知
            self.send_analysis_notification(results_df, strategy_summary, report_files)
            
            logger.info("基金分析完成")
            return results_df
            
        except Exception as e:
            logger.error(f"分析基金时出错: {str(e)}")
            return pd.DataFrame()
    
    def load_fund_data_from_excel(self, excel_file_path: str) -> pd.DataFrame:
        """从Excel文件加载基金数据"""
        try:
            logger.info(f"正在从Excel文件加载基金数据: {excel_file_path}")
            
            # 读取Excel文件
            df = pd.read_excel(excel_file_path)
            
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
            
            # 清理数据 - 只保留数字基金代码
            df = df[df[fund_code_col].astype(str).str.isdigit()].copy()
            
            # 格式化基金代码为6位
            df[fund_code_col] = df[fund_code_col].astype(str).str.zfill(6)
            
            # 重命名列以便统一处理
            df = df.rename(columns={
                fund_code_col: '基金代码',
                fund_name_col: '基金名称'
            })
            
            logger.info(f"成功加载 {len(df)} 只基金的数据")
            return df
            
        except Exception as e:
            logger.error(f"从Excel文件加载基金数据失败: {str(e)}")
            return pd.DataFrame()
    
    def analyze_all_funds(self, fund_data: pd.DataFrame, analysis_date: str) -> List[Dict]:
        """分析所有基金"""
        results = []
        
        for _, row in fund_data.iterrows():
            fund_code = str(row['基金代码']).zfill(6)
            fund_name = row.get('基金名称', f'基金{fund_code}')
            
            try:
                logger.info(f"正在分析基金: {fund_code} ({fund_name})")
                
                # 获取基金实时数据
                fund_info = self.fund_data_manager.get_realtime_data(fund_code)
                if not fund_info:
                    logger.warning(f"无法获取基金 {fund_code} 的实时数据")
                    continue
                
                # 获取基金绩效指标
                metrics = self.fund_data_manager.get_performance_metrics(fund_code)
                
                # 获取投资策略建议 - 正确获取字段
                # 优先使用实时数据中的daily_return（来自AKShare的日增长率字段，已是百分比格式）
                today_return = float(fund_info.get('daily_return', 0))
                
                # 获取历史数据用于计算前一日收益率
                historical_data = self.fund_data_manager.get_historical_data(fund_code, days=30)
                prev_day_return = 0.0
                
                # 从历史数据获取前一日收益率
                if not historical_data.empty and 'daily_growth_rate' in historical_data.columns:
                    # 使用AKShare原始的日增长率字段（已是百分比格式）
                    recent_growth = historical_data['daily_growth_rate'].dropna().tail(2)
                    if len(recent_growth) >= 2:
                        prev_day_return = float(recent_growth.iloc[-2]) if pd.notna(recent_growth.iloc[-2]) else 0.0
                    elif len(recent_growth) == 1:
                        prev_day_return = float(recent_growth.iloc[-1]) if pd.notna(recent_growth.iloc[-1]) else 0.0
                elif not historical_data.empty and 'daily_return' in historical_data.columns:
                    # 备用方案：使用pct_change计算的收益率（小数格式，需要乘100）
                    recent_returns = historical_data['daily_return'].dropna().tail(2)
                    if len(recent_returns) >= 2:
                        prev_day_return = recent_returns.iloc[-2] * 100
                    elif len(recent_returns) == 1:
                        prev_day_return = recent_returns.iloc[-1] * 100
                
                # 计算交易建议的所有字段（与analyze_single_fund保持一致）
                status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, execution_amount, buy_multiplier = self.get_investment_strategy(today_return, prev_day_return)
                
                strategy = self.strategy_engine.analyze_strategy(today_return, prev_day_return)
                
                # 确保字段名与analyze_single_fund保持一致
                result = {
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'analysis_date': analysis_date,
                    'today_return': today_return,
                    'prev_day_return': prev_day_return,
                    'daily_return': today_return,  # 用于收益率分析图表
                    'total_return': float(metrics.get('total_return', 0)),
                    'current_nav': float(fund_info.get('current_nav', 0)),
                    'previous_nav': float(fund_info.get('previous_nav', 0)),
                    'estimate_nav': float(fund_info.get('estimate_nav', 0)),
                    'strategy_advice': strategy['action'],
                    'strategy_reason': strategy['operation_suggestion'],
                    'risk_level': 'medium',  # 默认风险等级
                    # 添加缺失的字段
                    'status_label': status_label,
                    'is_buy': is_buy,
                    'redeem_amount': redeem_amount,
                    'comparison_value': comparison_value,
                    'operation_suggestion': operation_suggestion,
                    'execution_amount': execution_amount,
                    'buy_multiplier': buy_multiplier,
                    **metrics
                }
                
                results.append(result)
                logger.info(f"基金 {fund_code} 分析完成")
                
            except Exception as e:
                logger.error(f"分析基金 {fund_code} 时出错: {str(e)}")
                continue
        
        return results
    
    def generate_strategy_summary(self, results: List[Dict]) -> Dict:
        """生成策略汇总"""
        if not results:
            return {}
        
        df = pd.DataFrame(results)
        
        summary = {
            'total_funds': len(results),
            'avg_today_return': df['today_return'].mean(),
            'avg_total_return': df['total_return'].mean(),
            'positive_return_funds': len(df[df['today_return'] > 0]),
            'negative_return_funds': len(df[df['today_return'] < 0]),
            'zero_return_funds': len(df[df['today_return'] == 0]),
            'buy_recommendations': len(df[df['strategy_advice'] == '买入']),
            'hold_recommendations': len(df[df['strategy_advice'] == '持有']),
            'sell_recommendations': len(df[df['strategy_advice'] == '卖出']),
            'high_risk_funds': len(df[df['risk_level'] == 'high']),
            'medium_risk_funds': len(df[df['risk_level'] == 'medium']),
            'low_risk_funds': len(df[df['risk_level'] == 'low'])
        }
        
        return summary
    
    def save_results_to_database(self, results: List[Dict], strategy_summary: Dict, report_files: List[str]) -> bool:
        """保存结果到数据库"""
        try:
            logger.info("正在保存分析结果到数据库")
            
            # 保存详细结果
            for result in results:
                self.db_manager.save_fund_analysis(result)
            
            # 保存策略汇总
            self.db_manager.save_strategy_summary(strategy_summary)
            
            # 保存报告文件信息
            for report_file in report_files:
                self.db_manager.save_report_info(report_file, 'comprehensive_analysis')
            
            logger.info("分析结果保存到数据库完成")
            return True
            
        except Exception as e:
            logger.error(f"保存结果到数据库失败: {str(e)}")
            return False
    
    def send_analysis_notification(self, results_df: pd.DataFrame, strategy_summary: Dict, report_files: List[str]):
        """发送分析通知"""
        try:
            logger.info("正在发送分析通知")
            
            # 生成微信消息
            message = self.generate_wechat_message(results_df)
            
            # 发送通知
            token = NOTIFICATION_CONFIG.get('wechat_token', '')
            if token:
                self.send_notification(
                    token=token,
                    message=message,
                    title="基金持仓分析报告",
                    send_wechat=True,
                    send_email=True
                )
            
            logger.info("分析通知发送完成")
            
        except Exception as e:
            logger.error(f"发送分析通知失败: {str(e)}")
    
    def generate_wechat_message(self, result_df: pd.DataFrame) -> str:
        """生成微信消息（兼容HTML格式）"""
        try:
            if result_df.empty:
                return "暂无基金分析数据"
            
            # 计算汇总信息
            total_funds = len(result_df)
            positive_funds = len(result_df[result_df['today_return'] > 0])
            negative_funds = len(result_df[result_df['today_return'] < 0])
            avg_return = result_df['today_return'].mean()
            
            # 生成HTML格式的消息内容
            message = f"""
<div style="font-family: 'Microsoft YaHei', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center;">
        <h2 style="margin: 0; font-size: 24px; font-weight: bold;">📊 基金持仓分析报告</h2>
        <p style="margin: 5px 0 0 0; opacity: 0.9;">{datetime.now().strftime('%Y年%m月%d日')}</p>
    </div>
    
    <div style="padding: 25px;">
        <div style="background: #f8f9fa; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
            <h3 style="color: #2c3e50; margin: 0 0 15px 0; font-size: 18px;">📈 今日概况</h3>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                <div style="background: white; padding: 15px; border-radius: 6px; border-left: 4px solid #3498db;">
                    <div style="color: #7f8c8d; font-size: 14px; margin-bottom: 5px;">总基金数</div>
                    <div style="color: #2c3e50; font-size: 20px; font-weight: bold;">{total_funds}只</div>
                </div>
                <div style="background: white; padding: 15px; border-radius: 6px; border-left: 4px solid #27ae60;">
                    <div style="color: #7f8c8d; font-size: 14px; margin-bottom: 5px;">上涨基金</div>
                    <div style="color: #27ae60; font-size: 20px; font-weight: bold;">{positive_funds}只</div>
                </div>
                <div style="background: white; padding: 15px; border-radius: 6px; border-left: 4px solid #e74c3c;">
                    <div style="color: #7f8c8d; font-size: 14px; margin-bottom: 5px;">下跌基金</div>
                    <div style="color: #e74c3c; font-size: 20px; font-weight: bold;">{negative_funds}只</div>
                </div>
                <div style="background: white; padding: 15px; border-radius: 6px; border-left: 4px solid #f39c12;">
                    <div style="color: #7f8c8d; font-size: 14px; margin-bottom: 5px;">平均收益</div>
                    <div style="color: {'#27ae60' if avg_return >= 0 else '#e74c3c'}; font-size: 20px; font-weight: bold;">{avg_return:+.2f}%</div>
                </div>
            </div>
        </div>
        
        <div style="background: #e8f5e8; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
            <h3 style="color: #27ae60; margin: 0 0 15px 0; font-size: 18px;">🏆 今日表现最佳</h3>
"""
            
            # 添加表现最好的3只基金
            top_funds = result_df.nlargest(3, 'today_return')[['fund_code', 'fund_name', 'today_return']]
            for _, fund in top_funds.iterrows():
                message += f"""
            <div style="background: white; margin-bottom: 10px; padding: 15px; border-radius: 6px; border-left: 4px solid #27ae60; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: bold; color: #2c3e50; margin-bottom: 5px;">{fund['fund_name']}</div>
                        <div style="color: #7f8c8d; font-size: 14px;">{fund['fund_code']}</div>
                    </div>
                    <div style="color: #27ae60; font-size: 18px; font-weight: bold;">+{fund['today_return']:.2f}%</div>
                </div>
            </div>
"""
            
            message += """
        </div>
        
        <div style="background: #ffeaea; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
            <h3 style="color: #e74c3c; margin: 0 0 15px 0; font-size: 18px;">⚠️ 今日表现最差</h3>
"""
            
            # 添加表现最差的3只基金
            bottom_funds = result_df.nsmallest(3, 'today_return')[['fund_code', 'fund_name', 'today_return']]
            for _, fund in bottom_funds.iterrows():
                message += f"""
            <div style="background: white; margin-bottom: 10px; padding: 15px; border-radius: 6px; border-left: 4px solid #e74c3c; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: bold; color: #2c3e50; margin-bottom: 5px;">{fund['fund_name']}</div>
                        <div style="color: #7f8c8d; font-size: 14px;">{fund['fund_code']}</div>
                    </div>
                    <div style="color: #e74c3c; font-size: 18px; font-weight: bold;">{fund['today_return']:.2f}%</div>
                </div>
            </div>
"""
            
            message += """
        </div>
        
        <div style="background: #fff3cd; border-radius: 8px; padding: 20px; text-align: center;">
            <p style="color: #856404; margin: 0; font-size: 14px;">
                <strong>📊 详细报告已生成</strong><br>
                请查看附件图表获取更详细的分析信息
            </p>
        </div>
    </div>
    
    <div style="background: #f8f9fa; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #6c757d;">
        本报告由增强版基金分析系统生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</div>
"""
            
            return message.strip()
            
        except Exception as e:
            logger.error(f"生成微信消息失败: {str(e)}")
            return "基金分析完成，但生成消息失败"
    
    def send_notification(self, token: str, message: str, title: str = "基金分析报告", 
                          send_wechat: bool = True, send_email: bool = True, 
                          email_channel: str = "mail") -> bool:
        """发送通知"""
        try:
            logger.info(f"正在发送通知: {title}")
            
            # 这里可以实现实际的通知发送逻辑
            # 由于这是一个示例，我们只记录日志
            if send_wechat:
                logger.info(f"微信通知已准备发送: {title}")
                logger.info(f"微信消息内容: {message}")
            
            if send_email:
                logger.info(f"邮件通知已准备发送: {title}")
                logger.info(f"邮件消息内容: {message}")
            
            logger.info("通知发送完成")
            return True
            
        except Exception as e:
            logger.error(f"发送通知失败: {str(e)}")
            return False
    
    def compare_fund_performance(self) -> pd.DataFrame:
        """
        对比基金绩效
        
        返回：
        DataFrame: 对比结果
        """
        logger.info("开始对比基金绩效")
        
        try:
            # 获取所有持仓基金
            fund_data = self.load_fund_data_from_excel(BASE_CONFIG['fund_position_file'])
            if fund_data.empty:
                logger.error("没有获取到有效的基金数据")
                return pd.DataFrame()
            
            # 分析所有基金
            results = []
            today_str = datetime.now().strftime('%Y%m%d')
            
            for _, row in fund_data.iterrows():
                fund_code = str(row['基金代码']).zfill(6)
                fund_name = row.get('基金名称', f'基金{fund_code}')
                
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
                        'today_return': float(fund_info.get('today_return', 0)),
                        'total_return': float(fund_info.get('total_return', 0)),
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
            
            # 生成对比图表 - 使用analytics engine的方法
            self.analytics_engine._create_performance_overview(df, './reports/', today_str)
            self.analytics_engine._create_return_analysis(df, './reports/', today_str)
            self.analytics_engine._create_risk_analysis(df, './reports/', today_str)
            self.analytics_engine._create_composite_score_chart(df, './reports/', today_str)
            self.analytics_engine._create_correlation_analysis(df, './reports/', today_str)
            self.analytics_engine._create_investment_summary(df, './reports/', today_str)
            
            return df
            
        except Exception as e:
            logger.error(f"进行基金绩效对比时出错: {str(e)}")
            return pd.DataFrame()


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


    def send_notification(self, token: str, message: str, title: str = "基金分析报告", 
                          send_wechat: bool = True, send_email: bool = True, 
                          email_channel: str = "mail") -> bool:
        """
        通过PushPlus服务发送通知（微信和邮件）
        
        参数：
        token: PushPlus的token
        message: 要发送的消息内容
        title: 消息标题（默认：基金分析报告）
        send_wechat: 是否发送微信通知（默认：True）
        send_email: 是否发送邮件通知（默认：True）
        email_channel: 邮件发送通道（默认：mail）
        
        返回：
        bool: 发送是否成功
        """
        try:
            import requests
            
            logger.info("开始发送通知...")
            
            # 发送微信通知
            if send_wechat:
                logger.info("正在发送微信通知...")
                template = 'html'
                url = f"https://www.pushplus.plus/send?token={token}&title={title}&content={message}&template={template}"
                response = requests.get(url)
                if response.status_code == 200 and response.json().get('code') == 200:
                    logger.info("微信通知发送成功")
                else:
                    logger.error(f"微信通知发送失败: {response.text}")
                    return False
            
            # 发送邮件通知
            if send_email:
                logger.info("正在发送邮件通知...")
                url = f"http://www.pushplus.plus/send/{token}"
                headers = {'Content-Type': 'application/json'}
                data = {
                    "token": token,
                    "title": title,
                    "content": message,
                    "channel": email_channel,
                    "template": "html",  # 使用HTML模板
                    "option": ""
                }
                response = requests.post(url, headers=headers, json=data)
                if response.status_code == 200 and response.json().get('code') == 200:
                    logger.info("邮件通知发送成功")
                else:
                    logger.error(f"邮件通知发送失败: {response.text}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"发送通知时出错: {str(e)}")
            return False
    
    def get_fund_metrics(self, fund_code: str, fund_name: str) -> Dict:
        """
        获取基金的绩效指标
        
        参数：
        fund_code: 基金代码
        fund_name: 基金名称
        
        返回：
        dict: 包含各种绩效指标的字典
        """
        try:
            import akshare as ak
            import numpy as np
            from datetime import datetime, timedelta
            
            logger.info(f"正在获取基金 {fund_code} ({fund_name}) 的绩效指标")
            
            # 获取基金历史净值数据
            fund_hist = ak.fund_open_fund_info_em(symbol=fund_code, indicator='单位净值走势')
            
            if fund_hist.empty:
                # 如果无法获取数据，返回默认值
                logger.warning(f"基金 {fund_code} ({fund_name}) 无法获取历史数据，返回默认值")
                return {
                    'annualized_return': 0.0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'volatility': 0.0,
                    'calmar_ratio': 0.0,
                    'sortino_ratio': 0.0,
                    'var_95': 0.0,
                    'win_rate': 0.0,
                    'profit_loss_ratio': 0.0
                }
            
            # 按日期排序
            fund_hist['净值日期'] = pd.to_datetime(fund_hist['净值日期'])
            fund_hist = fund_hist.sort_values('净值日期', ascending=True)
            
            # 计算日收益率
            fund_hist['daily_return'] = fund_hist['单位净值'].pct_change()
            daily_returns = fund_hist['daily_return'].dropna()
            
            if len(daily_returns) < 2:
                # 数据不足，返回默认值
                logger.warning(f"基金 {fund_code} ({fund_name}) 数据不足，返回默认值")
                return {
                    'annualized_return': 0.0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'volatility': 0.0,
                    'calmar_ratio': 0.0,
                    'sortino_ratio': 0.0,
                    'var_95': 0.0,
                    'win_rate': 0.0,
                    'profit_loss_ratio': 0.0
                }
            
            # 计算年化收益率
            total_return = (fund_hist['单位净值'].iloc[-1] / fund_hist['单位净值'].iloc[0]) - 1
            days = (fund_hist['净值日期'].iloc[-1] - fund_hist['净值日期'].iloc[0]).days
            if days > 0:
                annualized_return = (1 + total_return) ** (365.25 / days) - 1
            else:
                annualized_return = 0.0
            
            # 计算年化波动率
            volatility = daily_returns.std() * np.sqrt(252)
            
            # 计算夏普比率（假设无风险收益率为0.03）
            risk_free_rate = 0.03
            sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility != 0 else 0.0
            
            # 计算最大回撤
            cumulative_returns = (1 + daily_returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min() if not drawdown.empty else 0.0
            
            # 计算卡玛比率
            calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
            
            # 计算索提诺比率
            negative_returns = daily_returns[daily_returns < 0]
            downside_deviation = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else volatility
            sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation if downside_deviation != 0 else 0.0
            
            # 计算VaR (95%)
            var_95 = daily_returns.quantile(0.05) if not daily_returns.empty else 0.0
            
            # 计算胜率
            win_rate = (daily_returns > 0).sum() / len(daily_returns) if len(daily_returns) > 0 else 0.0
            
            # 计算盈亏比
            positive_returns = daily_returns[daily_returns > 0]
            negative_returns = daily_returns[daily_returns < 0]
            avg_positive = positive_returns.mean() if len(positive_returns) > 0 else 0.0
            avg_negative = abs(negative_returns.mean()) if len(negative_returns) > 0 else 0.0
            profit_loss_ratio = avg_positive / avg_negative if avg_negative != 0 else 0.0
            
            metrics = {
                'annualized_return': annualized_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'volatility': volatility,
                'calmar_ratio': calmar_ratio,
                'sortino_ratio': sortino_ratio,
                'var_95': var_95,
                'win_rate': win_rate,
                'profit_loss_ratio': profit_loss_ratio
            }
            
            logger.info(f"基金 {fund_code} ({fund_name}) 绩效指标计算完成")
            return metrics
            
        except Exception as e:
            logger.error(f"计算基金 {fund_code} ({fund_name}) 绩效指标时出错: {str(e)}")
            # 出错时返回默认值
            return {
                'annualized_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'volatility': 0.0,
                'calmar_ratio': 0.0,
                'sortino_ratio': 0.0,
                'var_95': 0.0,
                'win_rate': 0.0,
                'profit_loss_ratio': 0.0
            }
    
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
                excel_file_path = BASE_CONFIG['fund_position_file']
            
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
            report_files = self.generate_comprehensive_charts(results_df, datetime.now().strftime('%Y%m%d'))
            
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
            # 从数据库获取最新的基金数据（每个基金只取最新一条记录）
            query = """
            SELECT DISTINCT t1.fund_code, t1.fund_name, t1.today_return, t1.prev_day_return, t1.status_label, t1.operation_suggestion,
                   t1.annualized_return, t1.sharpe_ratio, t1.max_drawdown, t1.volatility, t1.calmar_ratio, t1.sortino_ratio, t1.var_95, t1.win_rate, t1.profit_loss_ratio,
                   t1.daily_return
            FROM fund_analysis_results t1
            INNER JOIN (
                SELECT fund_code, MAX(analysis_date) as max_date
                FROM fund_analysis_results
                GROUP BY fund_code
            ) t2 ON t1.fund_code = t2.fund_code AND t1.analysis_date = t2.max_date
            ORDER BY t1.fund_code
            """
            
            df = self.db_manager.execute_query(query)
            
            if df.empty:
                logger.warning("未找到足够的数据进行对比")
                return pd.DataFrame()
            
            logger.info(f"共找到 {len(df)} 只基金的最新绩效数据")
            
            # 格式化显示
            logger.info("基金绩效指标对比结果：")
            display_columns = [
                'fund_code', 'fund_name', 'today_return', 'annualized_return', 
                'sharpe_ratio', 'max_drawdown', 'volatility', 'calmar_ratio', 
                'sortino_ratio', 'win_rate', 'status_label', 'operation_suggestion'
            ]
            
            display_df = df.copy()
            # 格式化数值为百分比
            display_df['today_return'] = display_df['today_return'].map('{:.2f}%'.format)
            display_df['annualized_return'] = display_df['annualized_return'].map('{:.2f}%'.format)
            display_df['max_drawdown'] = display_df['max_drawdown'].map('{:.2f}%'.format)
            display_df['volatility'] = display_df['volatility'].map('{:.2f}%'.format)
            display_df['win_rate'] = display_df['win_rate'].map('{:.2f}%'.format)
            # 其他指标保留小数点后三位
            display_df['sharpe_ratio'] = display_df['sharpe_ratio'].round(3)
            display_df['calmar_ratio'] = display_df['calmar_ratio'].round(3)
            display_df['sortino_ratio'] = display_df['sortino_ratio'].round(3)
            display_df['var_95'] = display_df['var_95'].round(4)
            display_df['profit_loss_ratio'] = display_df['profit_loss_ratio'].round(2)
            
            logger.info(f"\n{display_df[display_columns].to_string()}")
            
            # 生成可视化图表
            self.generate_comprehensive_charts(df, datetime.now().strftime('%Y%m%d'))
            
            return df
            
        except Exception as e:
            logger.error(f"进行基金绩效对比时出错: {str(e)}")
            return pd.DataFrame()
    
    def send_notification(self, token: str, message: str, title: str = "基金分析报告", 
                          send_wechat: bool = True, send_email: bool = True, 
                          email_channel: str = "mail") -> bool:
        """
        通过PushPlus服务发送通知（微信和邮件）
        
        参数：
        token: PushPlus的token
        message: 要发送的消息内容
        title: 消息标题（默认：基金分析报告）
        send_wechat: 是否发送微信通知（默认：True）
        send_email: 是否发送邮件通知（默认：True）
        email_channel: 邮件发送通道（默认：mail）
        
        返回：
        bool: 发送是否成功
        """
        try:
            import requests
            
            logger.info("开始发送通知...")
            
            # 发送微信通知
            if send_wechat:
                logger.info("正在发送微信通知...")
                template = 'html'
                url = f"https://www.pushplus.plus/send?token={token}&title={title}&content={message}&template={template}"
                response = requests.get(url)
                if response.status_code == 200 and response.json().get('code') == 200:
                    logger.info("微信通知发送成功")
                else:
                    logger.error(f"微信通知发送失败: {response.text}")
                    return False
            
            # 发送邮件通知
            if send_email:
                logger.info("正在发送邮件通知...")
                url = f"http://www.pushplus.plus/send/{token}"
                headers = {'Content-Type': 'application/json'}
                data = {
                    "token": token,
                    "title": title,
                    "content": message,
                    "channel": email_channel,
                    "option": ""
                }
                response = requests.post(url, headers=headers, json=data)
                if response.status_code == 200 and response.json().get('code') == 200:
                    logger.info("邮件通知发送成功")
                else:
                    logger.error(f"邮件通知发送失败: {response.text}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"发送通知时出错: {str(e)}")
            return False
    
    def get_fund_metrics(self, fund_code: str, fund_name: str) -> Dict:
        """
        获取基金的绩效指标
        
        参数：
        fund_code: 基金代码
        fund_name: 基金名称
        
        返回：
        dict: 包含各种绩效指标的字典
        """
        try:
            import akshare as ak
            import numpy as np
            from datetime import datetime, timedelta
            
            logger.info(f"正在获取基金 {fund_code} ({fund_name}) 的绩效指标")
            
            # 获取基金历史净值数据
            fund_hist = ak.fund_open_fund_info_em(symbol=fund_code, indicator='单位净值走势')
            
            if fund_hist.empty:
                # 如果无法获取数据，返回默认值
                logger.warning(f"基金 {fund_code} ({fund_name}) 无法获取历史数据，返回默认值")
                return {
                    'annualized_return': 0.0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'volatility': 0.0,
                    'calmar_ratio': 0.0,
                    'sortino_ratio': 0.0,
                    'var_95': 0.0,
                    'win_rate': 0.0,
                    'profit_loss_ratio': 0.0
                }
            
            # 按日期排序
            fund_hist['净值日期'] = pd.to_datetime(fund_hist['净值日期'])
            fund_hist = fund_hist.sort_values('净值日期', ascending=True)
            
            # 计算日收益率
            fund_hist['daily_return'] = fund_hist['单位净值'].pct_change()
            daily_returns = fund_hist['daily_return'].dropna()
            
            if len(daily_returns) < 2:
                # 数据不足，返回默认值
                logger.warning(f"基金 {fund_code} ({fund_name}) 数据不足，返回默认值")
                return {
                    'annualized_return': 0.0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'volatility': 0.0,
                    'calmar_ratio': 0.0,
                    'sortino_ratio': 0.0,
                    'var_95': 0.0,
                    'win_rate': 0.0,
                    'profit_loss_ratio': 0.0
                }
            
            # 计算年化收益率
            total_return = (fund_hist['单位净值'].iloc[-1] / fund_hist['单位净值'].iloc[0]) - 1
            days = (fund_hist['净值日期'].iloc[-1] - fund_hist['净值日期'].iloc[0]).days
            if days > 0:
                annualized_return = (1 + total_return) ** (365.25 / days) - 1
            else:
                annualized_return = 0.0
            
            # 计算年化波动率
            volatility = daily_returns.std() * np.sqrt(252)
            
            # 计算夏普比率（假设无风险收益率为0.03）
            risk_free_rate = 0.03
            sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility != 0 else 0.0
            
            # 计算最大回撤
            cumulative_returns = (1 + daily_returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min() if not drawdown.empty else 0.0
            
            # 计算卡玛比率
            calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
            
            # 计算索提诺比率
            negative_returns = daily_returns[daily_returns < 0]
            downside_deviation = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else volatility
            sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation if downside_deviation != 0 else 0.0
            
            # 计算VaR (95%)
            var_95 = daily_returns.quantile(0.05) if not daily_returns.empty else 0.0
            
            # 计算胜率
            win_rate = (daily_returns > 0).sum() / len(daily_returns) if len(daily_returns) > 0 else 0.0
            
            # 计算盈亏比
            positive_returns = daily_returns[daily_returns > 0]
            negative_returns = daily_returns[daily_returns < 0]
            avg_positive = positive_returns.mean() if len(positive_returns) > 0 else 0.0
            avg_negative = abs(negative_returns.mean()) if len(negative_returns) > 0 else 0.0
            profit_loss_ratio = avg_positive / avg_negative if avg_negative != 0 else 0.0
            
            metrics = {
                'annualized_return': annualized_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'volatility': volatility,
                'calmar_ratio': calmar_ratio,
                'sortino_ratio': sortino_ratio,
                'var_95': var_95,
                'win_rate': win_rate,
                'profit_loss_ratio': profit_loss_ratio
            }
            
            logger.info(f"基金 {fund_code} ({fund_name}) 绩效指标计算完成")
            return metrics
            
        except Exception as e:
            logger.error(f"计算基金 {fund_code} ({fund_name}) 绩效指标时出错: {str(e)}")
            # 出错时返回默认值
            return {
                'annualized_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'volatility': 0.0,
                'calmar_ratio': 0.0,
                'sortino_ratio': 0.0,
                'var_95': 0.0,
                'win_rate': 0.0,
                'profit_loss_ratio': 0.0
            }
    
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
                excel_file_path = BASE_CONFIG['fund_position_file']
            
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
            report_files = self.generate_comprehensive_charts(results_df, datetime.now().strftime('%Y%m%d'))
            
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
            # 从数据库获取最新的基金数据（每个基金只取最新一条记录）
            query = """
            SELECT DISTINCT t1.fund_code, t1.fund_name, t1.today_return, t1.prev_day_return, t1.status_label, t1.operation_suggestion,
                   t1.annualized_return, t1.sharpe_ratio, t1.max_drawdown, t1.volatility, t1.calmar_ratio, t1.sortino_ratio, t1.var_95, t1.win_rate, t1.profit_loss_ratio,
                   t1.daily_return
            FROM fund_analysis_results t1
            INNER JOIN (
                SELECT fund_code, MAX(analysis_date) as max_date
                FROM fund_analysis_results
                GROUP BY fund_code
            ) t2 ON t1.fund_code = t2.fund_code AND t1.analysis_date = t2.max_date
            ORDER BY t1.fund_code
            """
            
            df = self.db_manager.execute_query(query)
            
            if df.empty:
                logger.warning("未找到足够的数据进行对比")
                return pd.DataFrame()
            
            logger.info(f"共找到 {len(df)} 只基金的最新绩效数据")
            
            # 格式化显示
            logger.info("基金绩效指标对比结果：")
            display_columns = [
                'fund_code', 'fund_name', 'today_return', 'annualized_return', 
                'sharpe_ratio', 'max_drawdown', 'volatility', 'calmar_ratio', 
                'sortino_ratio', 'win_rate', 'status_label', 'operation_suggestion'
            ]
            
            display_df = df.copy()
            # 格式化数值为百分比
            display_df['today_return'] = display_df['today_return'].map('{:.2f}%'.format)
            display_df['annualized_return'] = display_df['annualized_return'].map('{:.2f}%'.format)
            display_df['max_drawdown'] = display_df['max_drawdown'].map('{:.2f}%'.format)
            display_df['volatility'] = display_df['volatility'].map('{:.2f}%'.format)
            display_df['win_rate'] = display_df['win_rate'].map('{:.2f}%'.format)
            # 其他指标保留小数点后三位
            display_df['sharpe_ratio'] = display_df['sharpe_ratio'].round(3)
            display_df['calmar_ratio'] = display_df['calmar_ratio'].round(3)
            display_df['sortino_ratio'] = display_df['sortino_ratio'].round(3)
            display_df['var_95'] = display_df['var_95'].round(4)
            display_df['profit_loss_ratio'] = display_df['profit_loss_ratio'].round(2)
            
            logger.info(f"\n{display_df[display_columns].to_string()}")
            
            # 生成可视化图表
            self.generate_comprehensive_charts(df, datetime.now().strftime('%Y%m%d'))
            
            return df
            
        except Exception as e:
            logger.error(f"进行基金绩效对比时出错: {str(e)}")
            return pd.DataFrame()


if __name__ == "__main__":
    main()