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

# 导入策略对比分析系统
STRATEGY_ANALYZER_AVAILABLE = False
try:
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fund_backtest'))
    from complete_strategy_analyzer import CompleteStrategyAnalyzer
    STRATEGY_ANALYZER_AVAILABLE = True
except ImportError as e:
    pass  # 静默处理，避免logger未定义错误

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
        
        # 检查策略对比分析系统是否可用
        if STRATEGY_ANALYZER_AVAILABLE:
            logger.info("策略对比分析系统已加载")
        else:
            logger.warning("策略对比分析系统不可用，将跳过相关功能")

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
    
    def check_current_strategy_optimality(self, output_dir: str = '../reports/') -> None:
        """
        检查当前使用的策略是否为最优策略，并生成分析报告
        """
        try:
            logger.info("开始检查策略最优性...")
            
            # 尝试导入策略对比引擎
            try:
                sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fund_backtest'))
                from strategy_comparison_engine import StrategyComparisonEngine
            except ImportError:
                logger.warning("无法导入 StrategyComparisonEngine，跳过策略最优性检查")
                return

            # 运行策略对比
            engine = StrategyComparisonEngine(
                backtest_start_date='2024-01-01',
                backtest_end_date=datetime.now().strftime('%Y-%m-%d'),
                base_amount=1000,
                portfolio_size=6
            )
            
            # 使用所有基金进行对比
            results = engine.run_strategy_comparison(top_n=0, rank_type='daily')
            
            if not results or 'comparison_report' not in results:
                logger.warning("策略对比未返回有效结果")
                return
                
            best_backtest_strategy = results['comparison_report'].get('best_strategy', {})
            best_strategy_name = best_backtest_strategy.get('name', 'Unknown')
            
            # 当前策略信息
            current_strategy_name = "Enhanced Rule-Based Strategy"
            
            # 生成报告内容
            report_lines = []
            report_lines.append("# 基金定投策略最优性分析报告")
            report_lines.append(f"分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append(f"\n## 1. 策略对比结果 (基于{len(results.get('strategy_metrics', []))}种策略)")
            report_lines.append(f"本次回测对比了多种策略在当前市场环境下的表现，包括系统当前使用的策略：")
            
            # 动态列出所有参与对比的策略
            strategy_descriptions = {
                'dual_ma': '双均线趋势跟踪',
                'mean_reversion': '均值回归',
                'target_value': '目标市值',
                'grid': '网格交易',
                'enhanced_rule_based': '增强规则基准策略 (当前系统使用)'
            }
            
            for strategy_key in results.get('strategy_metrics', {}).keys():
                desc = strategy_descriptions.get(strategy_key, strategy_key)
                report_lines.append(f"- **{strategy_key}**: {desc}")
            
            if results.get('strategy_metrics'):
                report_lines.append("\n### 绩效指标对比")
                report_lines.append("| 策略名称 | 年化收益率 | 最大回撤 | 夏普比率 | 综合评分 |")
                report_lines.append("|---|---|---|---|---|")
                
                # 计算简单的综合评分用于展示 (如果metrics里没有)
                # 其实 results['comparison_report']['best_strategy'] 里有 score
                # 这里我们重新遍历
                for name, metrics in results['strategy_metrics'].items():
                    # 尝试从metrics获取score，如果没有则简单计算
                    score = metrics.get('composite_score', 0)
                    if score == 0 and metrics.get('volatility', 0) > 0:
                         # 简单的近似计算，与StrategyComparisonEngine保持一致
                         sharpe_score = min(metrics['sharpe_ratio'] / 2.0, 1.0) * 0.4
                         return_score = min(max(metrics['total_return'], 0) / 0.5, 1.0) * 0.3
                         drawdown_score = (1 - min(abs(metrics['max_drawdown']), 0.5) / 0.5) * 0.2
                         winrate_score = metrics['win_rate'] * 0.1
                         score = sharpe_score + return_score + drawdown_score + winrate_score
                         
                    report_lines.append(f"| {name} | {metrics['annualized_return']:.2%} | {metrics['max_drawdown']:.2%} | {metrics['sharpe_ratio']:.2f} | {score:.3f} |")
            
            report_lines.append(f"\n### 最优策略: {best_strategy_name}")
            report_lines.append(f"**综合评分**: {best_backtest_strategy.get('score', 0):.3f}")
            report_lines.append(f"**表现描述**: {best_backtest_strategy.get('description', '')}")

            report_lines.append("\n## 2. 当前系统使用的策略")
            report_lines.append(f"**策略名称**: {current_strategy_name}")
            report_lines.append("**策略描述**: 基于短期价格行为（当日/昨日涨跌幅）和基金绩效指标的复合规则型策略。")
            
            # 获取当前策略的回测表现
            current_metrics = results.get('strategy_metrics', {}).get('enhanced_rule_based', {})
            if current_metrics:
                report_lines.append(f"**回测表现**: 年化收益 {current_metrics.get('annualized_return', 0):.2%}, 最大回撤 {current_metrics.get('max_drawdown', 0):.2%}")

            report_lines.append("\n## 3. 结论与建议")
            
            # 判断最优策略是否是当前策略 (enhanced_rule_based)
            is_optimal = (best_strategy_name == 'enhanced_rule_based')
            
            if is_optimal:
                report_lines.append("✅ **结论**: 当前流程使用的策略 (`enhanced_rule_based`) 在回测中表现最优，建议继续保持。")
            else:
                report_lines.append(f"⚠️ **结论**: 当前流程使用的策略与回测最优策略 **不一致**。")
                report_lines.append(f"\n- **回测显示**: `{best_strategy_name}` 表现最佳 (综合评分 {best_backtest_strategy.get('score', 0):.3f})。")
                report_lines.append(f"- **系统现状**: 当前策略 (`enhanced_rule_based`) 表现次之或欠佳。")
                
                report_lines.append("\n### 改进建议")
                if best_strategy_name == 'target_value':
                    report_lines.append("- **推荐方案**: 建议在定期定投中引入**目标市值法**。设定资产增长目标，若资产超过目标则减少投入或赎回，若低于目标则增加投入。")
                    report_lines.append("- **操作提示**: 可以在现有定投基础上，每月检查一次总持仓市值，动态调整下期定投金额。")
                elif best_strategy_name == 'mean_reversion':
                    report_lines.append("- **推荐方案**: 建议关注**均值回归**机会。当市场出现极端偏离（如连续大跌或大涨）时，敢于逆向操作。")
                elif best_strategy_name == 'grid':
                    report_lines.append("- **推荐方案**: 建议对波动较大的基金采用**网格交易**。")
                elif best_strategy_name == 'dual_ma':
                    report_lines.append("- **推荐方案**: 建议关注**趋势信号**。在均线金叉时加大投入，死叉时暂停定投。")

            # 保存报告
            os.makedirs(output_dir, exist_ok=True)
            report_path = os.path.join(output_dir, 'strategy_optimality_analysis.md')
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            
            logger.info(f"策略最优性分析报告已生成: {report_path}")
            print(f"\n[策略检查] 最优策略分析报告已生成: {report_path}")
            print(f"[策略检查] 回测最优策略: {best_strategy_name} | 当前策略: {current_strategy_name}")
            
        except Exception as e:
            logger.error(f"检查策略最优性时出错: {str(e)}")

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
            logger.debug(f"基金 {fund_code} 基本信息: {basic_info}")
            
            # 获取实时数据
            realtime_data = self.fund_data_manager.get_realtime_data(fund_code)
            logger.info(f"基金 {fund_code} 实时数据: current_nav={realtime_data.get('current_nav')}, "
                       f"previous_nav={realtime_data.get('previous_nav')}, "
                       f"daily_return={realtime_data.get('daily_return')}, "
                       f"yesterday_return={realtime_data.get('yesterday_return')}, "
                       f"data_source={realtime_data.get('data_source')}")
            
            # 获取绩效指标
            performance_metrics = self.fund_data_manager.get_performance_metrics(fund_code)
            logger.debug(f"基金 {fund_code} 绩效指标: sharpe_ratio={performance_metrics.get('sharpe_ratio')}, "
                        f"composite_score={performance_metrics.get('composite_score')}")
            
            # 获取历史数据用于策略分析
            historical_data = self.fund_data_manager.get_historical_data(fund_code, days=30)
            
            # 计算今日和昨日收益率
            # 从实时数据获取今日收益率，并添加验证
            today_return = realtime_data.get('today_return', 0.0)
            try:
                today_return = float(today_return)
                # 检查今日收益率是否异常（超过±100%）
                if abs(today_return) > 100:
                    logger.warning(f"基金 {fund_code} 今日收益率异常: {today_return}%，使用默认值0.0%")
                    today_return = 0.0
            except (ValueError, TypeError):
                logger.warning(f"基金 {fund_code} 今日收益率解析失败，使用默认值0.0%")
                today_return = 0.0
            
            yesterday_return = 0.0
            
            # 首先尝试从实时数据获取昨日收益率（更可靠）
            if 'yesterday_return' in realtime_data:
                yesterday_return = realtime_data['yesterday_return']
                try:
                    yesterday_return = float(yesterday_return)
                    # 检查昨日收益率是否异常（超过±100%）
                    if abs(yesterday_return) > 100:
                        logger.warning(f"基金 {fund_code} 实时数据中的昨日收益率异常: {yesterday_return}%，从历史数据获取")
                        yesterday_return = 0.0
                    else:
                        # 如果实时数据中的昨日收益率正常，直接使用
                        logger.debug(f"基金 {fund_code} 从实时数据获取昨日收益率: {yesterday_return}%")
                except (ValueError, TypeError):
                    logger.warning(f"基金 {fund_code} 实时数据中的昨日收益率解析失败，从历史数据获取")
                    yesterday_return = 0.0
            
            # 如果实时数据中的昨日收益率不可用或异常，从历史数据获取
            if yesterday_return == 0.0 and not historical_data.empty:
                if 'daily_growth_rate' in historical_data.columns:
                    recent_growth = historical_data['daily_growth_rate'].dropna().tail(1)
                    if len(recent_growth) >= 1:
                        try:
                            # 昨日盈亏率直接从最新一条数据的日增长率获取
                            raw_value = float(recent_growth.iloc[-1]) if pd.notna(recent_growth.iloc[-1]) else 0.0
                            
                            # 如果值的绝对值小于1，说明是小数格式（如0.0475），需要乘100
                            # 如果值的绝对值大于等于1，说明已经是百分比格式（如4.75）
                            if abs(raw_value) < 1:
                                yesterday_return = raw_value * 100
                            else:
                                yesterday_return = raw_value
                            
                            # 检查昨日收益率是否异常（超过±100%）
                            if abs(yesterday_return) > 100:
                                logger.warning(f"基金 {fund_code} 历史数据中的昨日收益率异常: {yesterday_return}%，使用默认值")
                                yesterday_return = 0.0
                            else:
                                logger.debug(f"基金 {fund_code} 从历史数据daily_growth_rate获取昨日收益率: {yesterday_return}%")
                        except (ValueError, TypeError):
                            logger.warning(f"基金 {fund_code} 历史数据daily_growth_rate解析失败，使用默认值")
                            yesterday_return = 0.0
            
            # 确保收益率格式正确，保留两位小数
            today_return = round(today_return, 2)
            prev_day_return = round(yesterday_return, 2)
            
            # 记录最终计算的收益率
            logger.info(f"基金 {fund_code} 收益率计算完成: today_return={today_return}%, prev_day_return={prev_day_return}%")
            
            # 投资策略分析 - 使用策略引擎
            strategy_result = self.strategy_engine.analyze_strategy(today_return, prev_day_return, performance_metrics)
            
            # 从策略结果中提取字段
            strategy_name = strategy_result.get('strategy_name', 'momentum_strategy')
            action = strategy_result.get('action', 'hold')
            buy_multiplier = strategy_result.get('buy_multiplier', 0.0)
            redeem_amount = strategy_result.get('redeem_amount', 0.0)
            status_label = strategy_result.get('status_label', '🔴 未知状态')
            operation_suggestion = strategy_result.get('operation_suggestion', '持有不动')
            execution_amount = strategy_result.get('execution_amount', '持有不动')
            comparison_value = strategy_result.get('comparison_value', today_return - prev_day_return)
            
            # 兼容性：设置is_buy字段
            is_buy = action in ['buy', 'strong_buy', 'weak_buy']
            
            # 合并所有数据
            fund_result = {
                'fund_code': fund_code,
                'fund_name': fund_name,  # 优先使用传入的基金名称
                'analysis_date': analysis_date,
                'strategy_name': strategy_name,  # 使用策略引擎返回的策略名称
                'status_label': status_label,
                'operation_suggestion': operation_suggestion,
                'execution_amount': execution_amount,
                'is_buy': is_buy,
                'redeem_amount': redeem_amount,
                'buy_multiplier': buy_multiplier,
                'action': action,  # 添加action字段供策略引擎使用
                'comparison_value': comparison_value,  # 添加比较值字段
                **basic_info,
                **realtime_data,
                **performance_metrics,
                # 最后设置收益率相关字段，确保不会被覆盖
                'today_return': today_return,
                'prev_day_return': prev_day_return,
            }
            
            # 确保使用传入的基金名称覆盖API获取的名称
            fund_result['fund_name'] = fund_name
            
            logger.info(f"基金 {fund_code} 分析完成: status={status_label}, action={action}, "
                       f"buy_multiplier={buy_multiplier}, redeem_amount={redeem_amount}")
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
    
    def generate_analytics_reports(self, results_df: pd.DataFrame, output_dir: str = "../reports/") -> Dict:
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
            success = self.db_manager.batch_insert_data(results, {
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
                prev_day_return = row.get('prev_day_return', 0)
                status_label = row.get('status_label', '')
                operation_suggestion = row.get('operation_suggestion', '')
                execution_amount = row.get('execution_amount', '')
                
                # 格式化收益率显示
                today_return_str = f"{today_return:.2f}%" if isinstance(today_return, (int, float)) else str(today_return)
                prev_day_return_str = f"{prev_day_return:.2f}%" if isinstance(prev_day_return, (int, float)) else str(prev_day_return)
                
                # 根据收益率设置颜色
                today_color = '#28a745' if today_return > 0 else '#dc3545' if today_return < 0 else '#6c757d'
                prev_day_color = '#28a745' if prev_day_return > 0 else '#dc3545' if prev_day_return < 0 else '#6c757d'
                
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
                message += f"<td style='text-align: center; padding: 6px; border-right: 1px solid #dee2e6; color: {prev_day_color}; font-weight: bold;'>{prev_day_return_str}</td>\n"
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
    
    def get_investment_strategy(self, today_return: float, prev_day_return: float) -> tuple:
        """
        根据当日收益率和昨日收益率，返回投资策略结果
        
        参数：
        today_return: 当日收益率（%）
        prev_day_return: 昨日收益率（%）
        
        返回：
        tuple: (status_label, is_buy, redeem_amount, comparison_value, operation_suggestion, execution_amount, buy_multiplier)
        """
        return_diff = today_return - prev_day_return
        
        # 1. 今日>0 昨日>0 today-prev>1%
        if today_return > 0 and prev_day_return > 0:
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
        elif today_return > 0 and prev_day_return <= 0:
            status_label = "🔵 反转涨"
            is_buy = True
            redeem_amount = 0
            buy_multiplier = 1.5
            operation_suggestion = "定投买入，不赎回"
            execution_amount = f"买入{buy_multiplier}×定额"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 6. 今日=0 昨日>0
        elif today_return == 0 and prev_day_return > 0:
            status_label = "🔴 转势休整"
            is_buy = False
            redeem_amount = 30
            buy_multiplier = 0
            operation_suggestion = "不买入，赎回30元"
            execution_amount = "赎回¥30"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 7. 今日<0 昨日>0
        elif today_return < 0 and prev_day_return > 0:
            status_label = "🔴 反转跌"
            is_buy = False
            redeem_amount = 30
            buy_multiplier = 0
            operation_suggestion = "不买入，赎回30元"
            execution_amount = "赎回¥30"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 8. 今日=0 昨日≤0
        elif today_return == 0 and prev_day_return <= 0:
            status_label = "⚪ 持平"
            is_buy = True
            redeem_amount = 0
            buy_multiplier = 2.0
            operation_suggestion = "定投买入，不赎回"
            execution_amount = f"买入{buy_multiplier}×定额"
            return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
        
        # 9. 今日<0 昨日=0 today≤-2%
        elif today_return < 0 and prev_day_return == 0:
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
        elif today_return < 0 and prev_day_return < 0:
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
            elif (prev_day_return - today_return) > 0 and prev_day_return <= -2:
                status_label = "🔵 暴跌回升"
                is_buy = True
                redeem_amount = 0
                buy_multiplier = 1.5
                operation_suggestion = "定投买入，不赎回"
                execution_amount = f"买入{buy_multiplier}×定额"
                return status_label, is_buy, redeem_amount, return_diff, operation_suggestion, execution_amount, buy_multiplier
            # 15. 今日<0 昨日<0 (prev-today)>0 & prev>-2%
            elif (prev_day_return - today_return) > 0 and prev_day_return > -2:
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
    
    def run_complete_analysis(self, excel_file_path: str = None, output_dir: str = "../reports/") -> bool:
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
            report_files = self.generate_analytics_reports(results_df, "../reports/")
            
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
                        'today_return': float(fund_info.get('today_return', 0)),
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
            self.analytics_engine.generate_comprehensive_report(df, '../reports/')
            
            return df
            
        except Exception as e:
            logger.error(f"进行基金绩效对比时出错: {str(e)}")
            return pd.DataFrame()
    
    def run_strategy_comparison_analysis(self,
                                        start_date: str = '2024-01-01',
                                        end_date: str = None,
                                        base_amount: float = 1000,
                                        portfolio_size: int = 8,
                                        risk_profile: str = 'moderate',
                                        top_n: int = 20,
                                        rank_type: str = 'daily',
                                        output_dir: str = './strategy_analysis_results',
                                        generate_report: bool = True,
                                        generate_charts: bool = True) -> bool:
        """
        运行策略对比分析

        参数：
        start_date: 回测开始日期
        end_date: 回测结束日期
        base_amount: 基准定投金额
        portfolio_size: 基金组合大小
        risk_profile: 风险偏好 ('conservative', 'moderate', 'aggressive')
        top_n: 获取前N只基金
        rank_type: 排名类型 ('daily', 'weekly', 'monthly')
        output_dir: 输出目录

        返回：
        bool: 分析是否成功
        """
        try:
            if not STRATEGY_ANALYZER_AVAILABLE:
                logger.error("策略对比分析系统不可用，请检查模块导入")
                return False

            logger.info("开始运行策略对比分析")
            logger.info(f"分析参数: 日期 {start_date} 至 {end_date or '当前'}, 基准金额 {base_amount}, 组合大小 {portfolio_size}")

            # 创建策略分析器
            analyzer = CompleteStrategyAnalyzer(
                start_date=start_date,
                end_date=end_date,
                base_amount=base_amount,
                portfolio_size=portfolio_size,
                risk_profile=risk_profile
            )

            # 运行完整分析
            results = analyzer.run_complete_analysis(
                top_n=top_n,
                rank_type=rank_type,
                output_dir=output_dir,
                generate_report=generate_report,
                generate_charts=generate_charts
            )

            if 'error' in results:
                logger.error(f"策略对比分析失败: {results['error']}")
                return False
            else:
                logger.info("策略对比分析完成")
                print("\n" + "="*80)
                print("🎯 策略对比分析结果")
                print("="*80)

                if 'ranking' in results and 'recommendation' in results['ranking']:
                    rec = results['ranking']['recommendation']
                    print(f"🏆 推荐策略: {rec.get('recommended_strategy', {}).get('strategy_name', '未知')}")
                    print(f"🔍 置信度: {rec.get('confidence_level', '中等')}")
                    print(f"📊 总收益率: {rec.get('recommended_strategy', {}).get('raw_metrics', {}).get('total_return', 0):.2%}")

                if 'comparison' in results and 'strategy_results' in results['comparison']:
                    print(f"📈 对比策略数量: {len(results['comparison']['strategy_results'])}")

                print(f"📁 结果保存路径: {output_dir}")
                print("="*80)

                return True

        except Exception as e:
            logger.error(f"运行策略对比分析失败: {str(e)}")
            return False

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
    # 计算默认输出目录 (相对于脚本位置: ../reports/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_output_dir = os.path.join(script_dir, '..', 'reports')
    
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(
        description='增强版基金分析系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
 示例用法:
   python enhanced_main.py                         # 使用默认配置文件运行完整分析
   python enhanced_main.py --file path/to/excel.xlsx   # 指定Excel文件路径
   python enhanced_main.py --output ./my_reports/      # 指定输出目录
   python enhanced_main.py --test                     # 运行测试模式
   python enhanced_main.py --analyze                  # 分析持仓基金
   python enhanced_main.py --compare                  # 对比基金绩效
   python enhanced_main.py --all                      # 执行完整分析流程

 策略对比分析示例:
   python enhanced_main.py --strategy-analysis                              # 运行策略对比分析
   python enhanced_main.py -S --strategy-risk-profile aggressive         # 激进风险偏好
   python enhanced_main.py -S --strategy-base-amount 2000 --strategy-portfolio-size 10  # 自定义参数
   python enhanced_main.py -S --strategy-start-date 2023-01-01 --strategy-output-dir ./strategy_results  # 指定日期和输出
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
        default=default_output_dir,
        help=f'输出目录（默认: {default_output_dir}）'
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

    parser.add_argument(
        '--strategy-analysis', '-S',
        action='store_true',
        help='运行策略对比分析（测试高级策略）'
    )

    parser.add_argument(
        '--strategy-start-date',
        type=str,
        default='2024-01-01',
        help='策略分析开始日期（默认: 2024-01-01）'
    )

    parser.add_argument(
        '--strategy-end-date',
        type=str,
        default=None,
        help='策略分析结束日期（默认: 当前日期）'
    )

    parser.add_argument(
        '--strategy-base-amount',
        type=float,
        default=1000,
        help='策略分析基准定投金额（默认: 1000）'
    )

    parser.add_argument(
        '--strategy-portfolio-size',
        type=int,
        default=8,
        help='策略分析基金组合大小（默认: 8）'
    )

    parser.add_argument(
        '--strategy-risk-profile',
        type=str,
        default='moderate',
        choices=['conservative', 'moderate', 'aggressive'],
        help='策略分析风险偏好（默认: moderate）'
    )

    parser.add_argument(
        '--strategy-top-n',
        type=int,
        default=20,
        help='策略分析获取前N只基金（默认: 20）'
    )

    parser.add_argument(
        '--strategy-output-dir',
        type=str,
        default='./strategy_analysis_results',
        help='策略分析输出目录（默认: ./strategy_analysis_results）'
    )

    parser.add_argument(
        '--strategy-no-charts',
        action='store_true',
        help='策略分析不生成图表'
    )

    parser.add_argument(
        '--strategy-no-report',
        action='store_true',
        help='策略分析不生成详细报告'
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # 创建基金分析系统
        system = EnhancedFundAnalysisSystem()
        
        # 检查策略最优性
        if args.all or args.strategy_analysis:
            logger.info("检查当前策略最优性...")
            system.check_current_strategy_optimality(output_dir=args.output)
        
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
        elif args.strategy_analysis:
            # 运行策略对比分析
            logger.info("运行策略对比分析")
            success = system.run_strategy_comparison_analysis(
                start_date=args.strategy_start_date,
                end_date=args.strategy_end_date,
                base_amount=args.strategy_base_amount,
                portfolio_size=args.strategy_portfolio_size,
                risk_profile=args.strategy_risk_profile,
                top_n=args.strategy_top_n,
                rank_type='daily',  # 使用默认的daily排名
                output_dir=args.strategy_output_dir,
                generate_report=not args.strategy_no_report,
                generate_charts=not args.strategy_no_charts
            )

            if success:
                logger.info("策略对比分析任务成功完成")
                sys.exit(0)
            else:
                logger.error("策略对比分析任务失败")
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