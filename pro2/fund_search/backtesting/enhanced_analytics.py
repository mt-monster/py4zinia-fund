#!/usr/bin/env python
# coding: utf-8

"""
增强版基金绩效分析和可视化模块
提供专业的基金绩效分析和图表生成功能
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
import warnings
warnings.filterwarnings('ignore')

# 设置日志和中文字体
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class EnhancedFundAnalytics:
    """增强版基金分析类"""
    
    def __init__(self):
        from shared.enhanced_config import CHART_CONFIG
        self.chart_config = CHART_CONFIG
        self.color_palette = CHART_CONFIG['color_palette']
        
        # 设置图表样式
        plt.style.use(self.chart_config['style'])
        sns.set_palette("husl")
    
    def _validate_data_columns(self, fund_data: pd.DataFrame, required_cols: List[str], chart_name: str) -> bool:
        """
        验证数据是否包含必需的列
        
        参数：
        fund_data: 基金数据DataFrame
        required_cols: 必需的列名列表
        chart_name: 图表名称，用于错误日志
        
        返回：
        bool: 是否包含所有必需列
        """
        missing_cols = [col for col in required_cols if col not in fund_data.columns]
        if missing_cols:
            logger.warning(f"{chart_name} 缺少必需列: {missing_cols}")
            return False
        return True
    
    def generate_comprehensive_report(self, fund_data: pd.DataFrame, output_dir: str = "./") -> Dict:
        """
        生成综合基金分析报告
        
        参数：
        fund_data: 基金数据DataFrame
        output_dir: 输出目录
        
        返回：
        dict: 报告生成结果
        """
        try:
            today_str = datetime.now().strftime('%Y%m%d')
            report_files = {}
            
            # 1. 生成绩效概览图表
            report_files['performance_overview'] = self._create_performance_overview(fund_data, output_dir, today_str)
            
            # 2. 生成收益率分析图表
            report_files['return_analysis'] = self._create_return_analysis(fund_data, output_dir, today_str)
            
            # 3. 生成风险分析图表
            report_files['risk_analysis'] = self._create_risk_analysis(fund_data, output_dir, today_str)
            
            # 4. 生成综合评分图表
            report_files['composite_score'] = self._create_composite_score_chart(fund_data, output_dir, today_str)
            
            # 5. 生成相关性分析图表
            report_files['correlation_analysis'] = self._create_correlation_analysis(fund_data, output_dir, today_str)
            
            # 6. 生成投资建议汇总
            report_files['investment_summary'] = self._create_investment_summary(fund_data, output_dir, today_str)
            
            logger.info(f"综合报告生成完成，共生成 {len(report_files)} 个图表")
            return {
                'status': 'success',
                'report_files': report_files,
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"生成综合报告失败: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _create_performance_overview(self, fund_data: pd.DataFrame, output_dir: str, date_str: str) -> str:
        """
        创建绩效概览图表
        """
        try:
            # 验证必需列
            required_cols = ['fund_code', 'fund_name', 'annualized_return', 'sharpe_ratio', 'max_drawdown', 'composite_score']
            if not self._validate_data_columns(fund_data, required_cols, '绩效概览'):
                logger.error("绩效概览图表生成失败：缺少必需数据列")
                return ""
            
            fig, axes = plt.subplots(2, 2, figsize=(20, 16))
            fig.suptitle(f'基金绩效概览 - {date_str}', fontsize=20, fontweight='bold')
            
            # 1. 年化收益率排名
            ax1 = axes[0, 0]
            valid_data = fund_data.dropna(subset=['annualized_return']).sort_values('annualized_return', ascending=True)
            if not valid_data.empty:
                colors = [self._get_return_color(x) for x in valid_data['annualized_return']]
                bars = ax1.barh(range(len(valid_data)), valid_data['annualized_return'] * 100, color=colors)
                ax1.set_yticks(range(len(valid_data)))
                ax1.set_yticklabels([f"{code}\n{name}" for code, name in zip(valid_data['fund_code'], valid_data['fund_name'])], fontsize=8)
                ax1.set_xlabel('年化收益率 (%)')
                ax1.set_title('年化收益率排名', fontsize=14, fontweight='bold')
                ax1.grid(True, alpha=0.3)
                
                # 添加数值标签
                for i, (bar, value) in enumerate(zip(bars, valid_data['annualized_return'] * 100)):
                    ax1.text(value + 0.5, bar.get_y() + bar.get_height()/2, f'{value:.1f}%', 
                            va='center', fontsize=8, fontweight='bold')
            
            # 2. 夏普比率排名
            ax2 = axes[0, 1]
            valid_data = fund_data.dropna(subset=['sharpe_ratio']).sort_values('sharpe_ratio', ascending=True)
            if not valid_data.empty:
                colors = [self._get_sharpe_color(x) for x in valid_data['sharpe_ratio']]
                bars = ax2.barh(range(len(valid_data)), valid_data['sharpe_ratio'], color=colors)
                ax2.set_yticks(range(len(valid_data)))
                ax2.set_yticklabels([f"{code}\n{name}" for code, name in zip(valid_data['fund_code'], valid_data['fund_name'])], fontsize=8)
                ax2.set_xlabel('夏普比率')
                ax2.set_title('夏普比率排名', fontsize=14, fontweight='bold')
                ax2.grid(True, alpha=0.3)
                
                # 添加数值标签
                for i, (bar, value) in enumerate(zip(bars, valid_data['sharpe_ratio'])):
                    ax2.text(value + 0.02, bar.get_y() + bar.get_height()/2, f'{value:.2f}', 
                            va='center', fontsize=8, fontweight='bold')
            
            # 3. 最大回撤排名
            ax3 = axes[1, 0]
            valid_data = fund_data.dropna(subset=['max_drawdown']).sort_values('max_drawdown', ascending=False)
            if not valid_data.empty:
                colors = [self._get_drawdown_color(x) for x in valid_data['max_drawdown']]
                bars = ax3.barh(range(len(valid_data)), valid_data['max_drawdown'] * 100, color=colors)
                ax3.set_yticks(range(len(valid_data)))
                ax3.set_yticklabels([f"{code}\n{name}" for code, name in zip(valid_data['fund_code'], valid_data['fund_name'])], fontsize=8)
                ax3.set_xlabel('最大回撤 (%)')
                ax3.set_title('最大回撤排名（越小越好）', fontsize=14, fontweight='bold')
                ax3.grid(True, alpha=0.3)
                
                # 添加数值标签
                for i, (bar, value) in enumerate(zip(bars, valid_data['max_drawdown'] * 100)):
                    ax3.text(value - 0.5, bar.get_y() + bar.get_height()/2, f'{value:.1f}%', 
                            va='center', ha='right', fontsize=8, fontweight='bold')
            
            # 4. 综合评分排名
            ax4 = axes[1, 1]
            valid_data = fund_data.dropna(subset=['composite_score']).sort_values('composite_score', ascending=True)
            if not valid_data.empty:
                colors = [self._get_score_color(x) for x in valid_data['composite_score']]
                bars = ax4.barh(range(len(valid_data)), valid_data['composite_score'], color=colors)
                ax4.set_yticks(range(len(valid_data)))
                ax4.set_yticklabels([f"{code}\n{name}" for code, name in zip(valid_data['fund_code'], valid_data['fund_name'])], fontsize=8)
                ax4.set_xlabel('综合评分')
                ax4.set_title('综合评分排名', fontsize=14, fontweight='bold')
                ax4.grid(True, alpha=0.3)
                
                # 添加数值标签
                for i, (bar, value) in enumerate(zip(bars, valid_data['composite_score'])):
                    ax4.text(value + 0.01, bar.get_y() + bar.get_height()/2, f'{value:.2f}', 
                            va='center', fontsize=8, fontweight='bold')
            
            plt.tight_layout()
            
            # 保存图表
            chart_path = f"{output_dir}基金绩效概览_{date_str}.png"
            plt.savefig(chart_path, dpi=self.chart_config['dpi'], bbox_inches='tight')
            plt.close()
            
            logger.info(f"绩效概览图表已保存: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.error(f"创建绩效概览图表失败: {str(e)}")
            return ""
    
    def _create_return_analysis(self, fund_data: pd.DataFrame, output_dir: str, date_str: str) -> str:
        """
        创建收益率分析图表
        """
        try:
            fig, axes = plt.subplots(2, 2, figsize=(20, 16))
            fig.suptitle(f'收益率分析 - {date_str}', fontsize=20, fontweight='bold')
            
            # 1. 日收益率分布
            ax1 = axes[0, 0]
            
            # 检查并修复daily_return列
            if 'daily_return' not in fund_data.columns:
                logger.warning("缺少 'daily_return' 列，尝试从today_return列获取")
                if 'today_return' in fund_data.columns:
                    logger.info("从today_return列复制数据到daily_return列")
                    fund_data['daily_return'] = fund_data['today_return']
                elif '日收益率' in fund_data.columns:
                    logger.info("从日收益率列复制数据到daily_return列")
                    fund_data['daily_return'] = fund_data['日收益率']
            
            if 'daily_return' not in fund_data.columns:
                logger.warning("仍然缺少 'daily_return' 列，跳过日收益率分析")
                ax1.text(0.5, 0.5, '缺少日收益率数据', ha='center', va='center', 
                        transform=ax1.transAxes, fontsize=12)
                ax1.set_title('日收益率对比', fontsize=14, fontweight='bold')
            else:
                valid_data = fund_data.dropna(subset=['daily_return'])
                if not valid_data.empty:
                    colors = [self._get_return_color(x/100) for x in valid_data['daily_return']]
                    bars = ax1.bar(range(len(valid_data)), valid_data['daily_return'], color=colors)
                    ax1.set_xticks(range(len(valid_data)))
                    ax1.set_xticklabels(valid_data['fund_code'], rotation=45, fontsize=10)
                    ax1.set_ylabel('日收益率 (%)')
                    ax1.set_title('日收益率对比', fontsize=14, fontweight='bold')
                    ax1.grid(True, alpha=0.3)
                    ax1.axhline(y=0, color='black', linestyle='-', alpha=0.5)
                    
                    # 添加数值标签
                    for bar, value in zip(bars, valid_data['daily_return']):
                        height = bar.get_height()
                        ax1.text(bar.get_x() + bar.get_width()/2., height + (0.01 if height >= 0 else -0.03),
                                f'{value:.2f}%', ha='center', va='bottom' if height >= 0 else 'top',
                                fontsize=9, fontweight='bold')
                else:
                    # 当valid_data为空时
                    ax1.text(0.5, 0.5, '无有效日收益率数据', ha='center', va='center', 
                            transform=ax1.transAxes, fontsize=12)
                    ax1.set_title('日收益率对比', fontsize=14, fontweight='bold')
            
            # 2. 收益率vs波动率散点图
            ax2 = axes[0, 1]
            valid_data = fund_data.dropna(subset=['annualized_return', 'volatility'])
            if not valid_data.empty:
                scatter = ax2.scatter(valid_data['volatility'] * 100, valid_data['annualized_return'] * 100, 
                                    c=valid_data['composite_score'], cmap='RdYlGn', 
                                    s=100, alpha=0.7, edgecolors='black')
                
                # 添加基金代码标签
                for _, row in valid_data.iterrows():
                    ax2.annotate(row['fund_code'], 
                               (row['volatility'] * 100, row['annualized_return'] * 100),
                               xytext=(5, 5), textcoords='offset points', fontsize=8)
                
                ax2.set_xlabel('波动率 (%)')
                ax2.set_ylabel('年化收益率 (%)')
                ax2.set_title('收益率 vs 波动率', fontsize=14, fontweight='bold')
                ax2.grid(True, alpha=0.3)
                
                # 添加颜色条
                cbar = plt.colorbar(scatter, ax=ax2)
                cbar.set_label('综合评分')
            
            # 3. 夏普比率vs最大回撤散点图
            ax3 = axes[1, 0]
            valid_data = fund_data.dropna(subset=['sharpe_ratio', 'max_drawdown'])
            if not valid_data.empty:
                scatter = ax3.scatter(valid_data['max_drawdown'] * 100, valid_data['sharpe_ratio'], 
                                    c=valid_data['composite_score'], cmap='RdYlGn', 
                                    s=100, alpha=0.7, edgecolors='black')
                
                # 添加基金代码标签
                for _, row in valid_data.iterrows():
                    ax3.annotate(row['fund_code'], 
                               (row['max_drawdown'] * 100, row['sharpe_ratio']),
                               xytext=(5, 5), textcoords='offset points', fontsize=8)
                
                ax3.set_xlabel('最大回撤 (%)')
                ax3.set_ylabel('夏普比率')
                ax3.set_title('夏普比率 vs 最大回撤', fontsize=14, fontweight='bold')
                ax3.grid(True, alpha=0.3)
                
                # 添加颜色条
                cbar = plt.colorbar(scatter, ax=ax3)
                cbar.set_label('综合评分')
            
            # 4. 胜率分布
            ax4 = axes[1, 1]
            valid_data = fund_data.dropna(subset=['win_rate'])
            if not valid_data.empty:
                colors = [self._get_win_rate_color(x) for x in valid_data['win_rate']]
                bars = ax4.bar(range(len(valid_data)), valid_data['win_rate'] * 100, color=colors)
                ax4.set_xticks(range(len(valid_data)))
                ax4.set_xticklabels(valid_data['fund_code'], rotation=45, fontsize=10)
                ax4.set_ylabel('胜率 (%)')
                ax4.set_title('胜率分布', fontsize=14, fontweight='bold')
                ax4.grid(True, alpha=0.3)
                ax4.axhline(y=50, color='red', linestyle='--', alpha=0.7, label='50%基准线')
                ax4.legend()
                
                # 添加数值标签
                for bar, value in zip(bars, valid_data['win_rate'] * 100):
                    height = bar.get_height()
                    ax4.text(bar.get_x() + bar.get_width()/2., height + 1,
                            f'{value:.1f}%', ha='center', va='bottom',
                            fontsize=9, fontweight='bold')
            
            plt.tight_layout()
            
            # 保存图表
            chart_path = f"{output_dir}收益率分析_{date_str}.png"
            plt.savefig(chart_path, dpi=self.chart_config['dpi'], bbox_inches='tight')
            plt.close()
            
            logger.info(f"收益率分析图表已保存: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.error(f"创建收益率分析图表失败: {str(e)}")
            return ""
    
    def _create_risk_analysis(self, fund_data: pd.DataFrame, output_dir: str, date_str: str) -> str:
        """
        创建风险分析图表
        """
        try:
            # 验证必需列
            required_cols = ['fund_code', 'fund_name', 'volatility', 'var_95', 'sortino_ratio', 'calmar_ratio']
            if not self._validate_data_columns(fund_data, required_cols, '风险分析'):
                logger.error("风险分析图表生成失败：缺少必需数据列")
                return ""
            fig, axes = plt.subplots(2, 2, figsize=(20, 16))
            fig.suptitle(f'风险分析 - {date_str}', fontsize=20, fontweight='bold')
            
            # 1. 波动率排名
            ax1 = axes[0, 0]
            valid_data = fund_data.dropna(subset=['volatility']).sort_values('volatility', ascending=True)
            if not valid_data.empty:
                colors = [self._get_volatility_color(x) for x in valid_data['volatility']]
                bars = ax1.barh(range(len(valid_data)), valid_data['volatility'] * 100, color=colors)
                ax1.set_yticks(range(len(valid_data)))
                ax1.set_yticklabels([f"{code}\n{name}" for code, name in zip(valid_data['fund_code'], valid_data['fund_name'])], fontsize=8)
                ax1.set_xlabel('波动率 (%)')
                ax1.set_title('波动率排名（越低越好）', fontsize=14, fontweight='bold')
                ax1.grid(True, alpha=0.3)
                
                # 添加数值标签
                for i, (bar, value) in enumerate(zip(bars, valid_data['volatility'] * 100)):
                    ax1.text(value + 0.2, bar.get_y() + bar.get_height()/2, f'{value:.1f}%', 
                            va='center', fontsize=8, fontweight='bold')
            
            # 2. VaR(95%)排名
            ax2 = axes[0, 1]
            valid_data = fund_data.dropna(subset=['var_95']).sort_values('var_95', ascending=False)
            if not valid_data.empty:
                colors = [self._get_var_color(x) for x in valid_data['var_95']]
                bars = ax2.barh(range(len(valid_data)), valid_data['var_95'] * 100, color=colors)
                ax2.set_yticks(range(len(valid_data)))
                ax2.set_yticklabels([f"{code}\n{name}" for code, name in zip(valid_data['fund_code'], valid_data['fund_name'])], fontsize=8)
                ax2.set_xlabel('VaR(95%) (%)')
                ax2.set_title('VaR(95%)排名（负值越小风险越大）', fontsize=14, fontweight='bold')
                ax2.grid(True, alpha=0.3)
                ax2.axvline(x=0, color='red', linestyle='--', alpha=0.7)
                
                # 添加数值标签
                for i, (bar, value) in enumerate(zip(bars, valid_data['var_95'] * 100)):
                    ax2.text(value - 0.1, bar.get_y() + bar.get_height()/2, f'{value:.1f}%', 
                            va='center', ha='right', fontsize=8, fontweight='bold')
            
            # 3. 索提诺比率排名
            ax3 = axes[1, 0]
            valid_data = fund_data.dropna(subset=['sortino_ratio']).sort_values('sortino_ratio', ascending=True)
            if not valid_data.empty:
                colors = [self._get_sortino_color(x) for x in valid_data['sortino_ratio']]
                bars = ax3.barh(range(len(valid_data)), valid_data['sortino_ratio'], color=colors)
                ax3.set_yticks(range(len(valid_data)))
                ax3.set_yticklabels([f"{code}\n{name}" for code, name in zip(valid_data['fund_code'], valid_data['fund_name'])], fontsize=8)
                ax3.set_xlabel('索提诺比率')
                ax3.set_title('索提诺比率排名', fontsize=14, fontweight='bold')
                ax3.grid(True, alpha=0.3)
                
                # 添加数值标签
                for i, (bar, value) in enumerate(zip(bars, valid_data['sortino_ratio'])):
                    ax3.text(value + 0.02, bar.get_y() + bar.get_height()/2, f'{value:.2f}', 
                            va='center', fontsize=8, fontweight='bold')
            
            # 4. 卡玛比率排名
            ax4 = axes[1, 1]
            valid_data = fund_data.dropna(subset=['calmar_ratio']).sort_values('calmar_ratio', ascending=True)
            if not valid_data.empty:
                colors = [self._get_calmar_color(x) for x in valid_data['calmar_ratio']]
                bars = ax4.barh(range(len(valid_data)), valid_data['calmar_ratio'], color=colors)
                ax4.set_yticks(range(len(valid_data)))
                ax4.set_yticklabels([f"{code}\n{name}" for code, name in zip(valid_data['fund_code'], valid_data['fund_name'])], fontsize=8)
                ax4.set_xlabel('卡玛比率')
                ax4.set_title('卡玛比率排名', fontsize=14, fontweight='bold')
                ax4.grid(True, alpha=0.3)
                
                # 添加数值标签
                for i, (bar, value) in enumerate(zip(bars, valid_data['calmar_ratio'])):
                    ax4.text(value + 0.02, bar.get_y() + bar.get_height()/2, f'{value:.2f}', 
                            va='center', fontsize=8, fontweight='bold')
            
            plt.tight_layout()
            
            # 保存图表
            chart_path = f"{output_dir}风险分析_{date_str}.png"
            plt.savefig(chart_path, dpi=self.chart_config['dpi'], bbox_inches='tight')
            plt.close()
            
            logger.info(f"风险分析图表已保存: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.error(f"创建风险分析图表失败: {str(e)}")
            return ""
    
    def _create_composite_score_chart(self, fund_data: pd.DataFrame, output_dir: str, date_str: str) -> str:
        """
        创建综合评分图表
        """
        try:
            # 验证必需列
            required_cols = ['fund_code', 'fund_name', 'annualized_return', 'sharpe_ratio', 'max_drawdown', 'volatility', 'win_rate', 'composite_score']
            if not self._validate_data_columns(fund_data, required_cols, '综合评分'):
                logger.error("综合评分图表生成失败：缺少必需数据列")
                return ""
            
            fig, axes = plt.subplots(2, 2, figsize=(20, 16))
            fig.suptitle(f'综合评分分析 - {date_str}', fontsize=20, fontweight='bold')
            
            # 1. 综合评分雷达图（前5名）
            ax1 = axes[0, 0]
            valid_data = fund_data.dropna(subset=['composite_score']).nlargest(5, 'composite_score')
            if not valid_data.empty and len(valid_data) >= 3:
                self._create_radar_chart(ax1, valid_data, '综合评分雷达图 - 前5名')
            else:
                ax1.text(0.5, 0.5, '数据不足\n无法生成雷达图', ha='center', va='center', 
                        transform=ax1.transAxes, fontsize=14)
                ax1.set_title('综合评分雷达图 - 前5名', fontsize=14, fontweight='bold')
            
            # 2. 综合评分分布
            ax2 = axes[0, 1]
            valid_data = fund_data.dropna(subset=['composite_score'])
            if not valid_data.empty:
                colors = [self._get_score_color(x) for x in valid_data['composite_score']]
                bars = ax2.bar(range(len(valid_data)), valid_data['composite_score'], color=colors)
                ax2.set_xticks(range(len(valid_data)))
                ax2.set_xticklabels(valid_data['fund_code'], rotation=45, fontsize=10)
                ax2.set_ylabel('综合评分')
                ax2.set_title('综合评分分布', fontsize=14, fontweight='bold')
                ax2.grid(True, alpha=0.3)
                
                # 添加数值标签
                for bar, value in zip(bars, valid_data['composite_score']):
                    height = bar.get_height()
                    ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                            f'{value:.2f}', ha='center', va='bottom',
                            fontsize=9, fontweight='bold')
            
            # 3. 评分构成分析
            ax3 = axes[1, 0]
            valid_data = fund_data.dropna(subset=['annualized_return', 'sharpe_ratio', 'max_drawdown', 'volatility', 'win_rate'])
            if not valid_data.empty and len(valid_data) > 0:
                # 选择评分最高的基金进行构成分析
                top_fund = valid_data.loc[valid_data['composite_score'].idxmax()]
                
                metrics = ['年化收益率', '夏普比率', '最大回撤', '波动率', '胜率']
                values = [
                    max(0, min(1, (top_fund['annualized_return'] + 0.5) / 1.0)),
                    max(0, min(1, (top_fund['sharpe_ratio'] + 2) / 4.0)),
                    max(0, min(1, 1 - abs(top_fund['max_drawdown']) / 0.5)),
                    max(0, min(1, 1 - top_fund['volatility'] / 0.5)),
                    top_fund['win_rate']
                ]
                
                colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
                bars = ax3.bar(metrics, values, color=colors, alpha=0.8)
                ax3.set_ylabel('标准化得分')
                ax3.set_title(f'评分构成分析 - {top_fund["fund_code"]}', fontsize=14, fontweight='bold')
                ax3.grid(True, alpha=0.3)
                ax3.set_ylim(0, 1)
                
                # 添加数值标签
                for bar, value in zip(bars, values):
                    height = bar.get_height()
                    ax3.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                            f'{value:.2f}', ha='center', va='bottom',
                            fontsize=10, fontweight='bold')
            
            # 4. 评分等级分布
            ax4 = axes[1, 1]
            valid_data = fund_data.dropna(subset=['composite_score'])
            if not valid_data.empty:
                # 评分等级划分
                excellent = len(valid_data[valid_data['composite_score'] >= 0.8])
                good = len(valid_data[(valid_data['composite_score'] >= 0.6) & (valid_data['composite_score'] < 0.8)])
                average = len(valid_data[(valid_data['composite_score'] >= 0.4) & (valid_data['composite_score'] < 0.6)])
                poor = len(valid_data[valid_data['composite_score'] < 0.4])
                
                categories = ['优秀\n(≥0.8)', '良好\n(0.6-0.8)', '一般\n(0.4-0.6)', '较差\n(<0.4)']
                values = [excellent, good, average, poor]
                colors = ['#2E8B57', '#FFD700', '#FF8C00', '#DC143C']
                
                bars = ax4.bar(categories, values, color=colors, alpha=0.8)
                ax4.set_ylabel('基金数量')
                ax4.set_title('评分等级分布', fontsize=14, fontweight='bold')
                ax4.grid(True, alpha=0.3)
                
                # 添加数值标签
                for bar, value in zip(bars, values):
                    height = bar.get_height()
                    if height > 0:
                        ax4.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                f'{value}', ha='center', va='bottom',
                                fontsize=12, fontweight='bold')
            
            plt.tight_layout()
            
            # 保存图表
            chart_path = f"{output_dir}综合评分分析_{date_str}.png"
            plt.savefig(chart_path, dpi=self.chart_config['dpi'], bbox_inches='tight')
            plt.close()
            
            logger.info(f"综合评分分析图表已保存: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.error(f"创建综合评分分析图表失败: {str(e)}")
            return ""
    
    def _create_correlation_analysis(self, fund_data: pd.DataFrame, output_dir: str, date_str: str) -> str:
        """
        创建相关性分析图表
        """
        try:
            fig, axes = plt.subplots(1, 2, figsize=(20, 8))
            fig.suptitle(f'相关性分析 - {date_str}', fontsize=20, fontweight='bold')
            
            # 1. 绩效指标相关性热力图
            ax1 = axes[0]
            metrics_cols = ['annualized_return', 'sharpe_ratio', 'max_drawdown', 'volatility', 'win_rate', 'composite_score']
            valid_data = fund_data[metrics_cols].dropna()
            
            if not valid_data.empty:
                # 计算相关性矩阵
                corr_matrix = valid_data.corr()
                
                # 创建热力图
                sns.heatmap(corr_matrix, annot=True, cmap='RdBu_r', center=0, 
                           square=True, ax=ax1, cbar_kws={'shrink': 0.8})
                ax1.set_title('绩效指标相关性热力图', fontsize=14, fontweight='bold')
                
                # 旋转标签
                ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45, ha='right')
                ax1.set_yticklabels(ax1.get_yticklabels(), rotation=0)
            
            # 2. 收益率分布直方图
            ax2 = axes[1]
            valid_data = fund_data.dropna(subset=['annualized_return'])
            if not valid_data.empty:
                ax2.hist(valid_data['annualized_return'] * 100, bins=15, alpha=0.7, 
                        color='skyblue', edgecolor='black')
                ax2.set_xlabel('年化收益率 (%)')
                ax2.set_ylabel('基金数量')
                ax2.set_title('年化收益率分布', fontsize=14, fontweight='bold')
                ax2.grid(True, alpha=0.3)
                
                # 添加统计信息
                mean_return = valid_data['annualized_return'].mean() * 100
                std_return = valid_data['annualized_return'].std() * 100
                ax2.axvline(mean_return, color='red', linestyle='--', 
                           label=f'均值: {mean_return:.1f}%')
                ax2.axvline(mean_return + std_return, color='orange', linestyle='--', 
                           label=f'+1σ: {mean_return + std_return:.1f}%')
                ax2.axvline(mean_return - std_return, color='orange', linestyle='--', 
                           label=f'-1σ: {mean_return - std_return:.1f}%')
                ax2.legend()
            
            plt.tight_layout()
            
            # 保存图表
            chart_path = f"{output_dir}相关性分析_{date_str}.png"
            plt.savefig(chart_path, dpi=self.chart_config['dpi'], bbox_inches='tight')
            plt.close()
            
            logger.info(f"相关性分析图表已保存: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.error(f"创建相关性分析图表失败: {str(e)}")
            return ""
    
    def _create_investment_summary(self, fund_data: pd.DataFrame, output_dir: str, date_str: str) -> str:
        """
        创建投资建议汇总
        """
        try:
            fig, ax = plt.subplots(1, 1, figsize=(16, 10))
            fig.suptitle(f'投资建议汇总 - {date_str}', fontsize=20, fontweight='bold')
            
            # 创建投资建议表格
            if not fund_data.empty:
                # 选择重要指标进行展示，处理可能缺失的列
                display_cols = ['fund_code', 'fund_name', 'annualized_return', 
                               'sharpe_ratio', 'max_drawdown', 'composite_score']
                
                # 如果daily_return列存在，则添加到显示列中
                if 'daily_return' in fund_data.columns:
                    display_cols.insert(2, 'daily_return')
                
                # 按综合评分排序
                summary_data = fund_data[display_cols].dropna(subset=['composite_score']).sort_values('composite_score', ascending=False)
                
                if not summary_data.empty:
                    # 格式化数据
                    summary_display = summary_data.copy()
                    if 'daily_return' in summary_display.columns:
                        summary_display['daily_return'] = summary_display['daily_return'].map('{:.2f}%'.format)
                    summary_display['annualized_return'] = summary_display['annualized_return'].map('{:.2f}%'.format)
                    summary_display['sharpe_ratio'] = summary_display['sharpe_ratio'].map('{:.3f}'.format)
                    summary_display['max_drawdown'] = summary_display['max_drawdown'].map('{:.2f}%'.format)
                    summary_display['composite_score'] = summary_display['composite_score'].map('{:.3f}'.format)
                    
                    # 重命名列（动态根据实际列名）
                    column_mapping = {
                        'fund_code': '基金代码',
                        'fund_name': '基金名称',
                        'daily_return': '日收益',
                        'annualized_return': '年化收益',
                        'sharpe_ratio': '夏普比率',
                        'max_drawdown': '最大回撤',
                        'composite_score': '综合评分'
                    }
                    summary_display.columns = [column_mapping.get(col, col) for col in summary_display.columns]
                    
                    # 创建表格
                    ax.axis('tight')
                    ax.axis('off')
                    
                    table = ax.table(cellText=summary_display.values,
                                   colLabels=summary_display.columns,
                                   cellLoc='center',
                                   loc='center',
                                   bbox=[0, 0, 1, 1])
                    
                    # 设置表格样式
                    table.auto_set_font_size(False)
                    table.set_fontsize(10)
                    table.scale(1.2, 2)
                    
                    # 设置表头样式
                    for i in range(len(summary_display.columns)):
                        table[(0, i)].set_facecolor('#4CAF50')
                        table[(0, i)].set_text_props(weight='bold', color='white')
                    
                    # 设置数据行样式
                    for i in range(1, len(summary_display) + 1):
                        for j in range(len(summary_display.columns)):
                            if j == 0:  # 基金代码列
                                table[(i, j)].set_facecolor('#E3F2FD')
                            elif j == len(summary_display.columns) - 1:  # 综合评分列
                                score = float(summary_display.iloc[i-1]['综合评分'])
                                if score >= 0.8:
                                    table[(i, j)].set_facecolor('#C8E6C9')
                                elif score >= 0.6:
                                    table[(i, j)].set_facecolor('#FFF9C4')
                                else:
                                    table[(i, j)].set_facecolor('#FFCDD2')
                    
                    ax.set_title('基金投资建议汇总表', fontsize=16, fontweight='bold', pad=20)
            
            plt.tight_layout()
            
            # 保存图表
            chart_path = f"{output_dir}投资建议汇总_{date_str}.png"
            plt.savefig(chart_path, dpi=self.chart_config['dpi'], bbox_inches='tight')
            plt.close()
            
            logger.info(f"投资建议汇总图表已保存: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.error(f"创建投资建议汇总图表失败: {str(e)}")
            return ""
    
    def _create_radar_chart(self, ax, data: pd.DataFrame, title: str):
        """
        创建雷达图
        """
        try:
            # 选择要展示的指标
            metrics = ['annualized_return', 'sharpe_ratio', 'max_drawdown', 'volatility', 'win_rate']
            labels = ['年化收益率', '夏普比率', '最大回撤', '波动率', '胜率']
            
            # 标准化数据
            values_list = []
            fund_names = []
            
            for _, row in data.iterrows():
                values = [
                    max(0, min(1, (row['annualized_return'] + 0.5) / 1.0)),
                    max(0, min(1, (row['sharpe_ratio'] + 2) / 4.0)),
                    max(0, min(1, 1 - abs(row['max_drawdown']) / 0.5)),
                    max(0, min(1, 1 - row['volatility'] / 0.5)),
                    row['win_rate']
                ]
                values_list.append(values)
                fund_names.append(f"{row['fund_code']}\n({row['composite_score']:.3f})")
            
            # 创建雷达图 - 确保使用极坐标
            if not hasattr(ax, 'set_theta_offset'):
                # 如果ax不是极坐标轴，转换为极坐标
                ax.remove()
                ax = plt.subplot(ax.get_subplotspec(), projection='polar')
            
            angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
            angles += angles[:1]  # 闭合图形
            
            ax.set_theta_offset(np.pi / 2)
            ax.set_theta_direction(-1)
            ax.set_thetagrids(np.degrees(angles[:-1]), labels)
            
            # 绘制每个基金的数据
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
            for i, (values, name) in enumerate(zip(values_list, fund_names)):
                values += values[:1]  # 闭合图形
                ax.plot(angles, values, 'o-', linewidth=2, label=name, color=colors[i % len(colors)])
                ax.fill(angles, values, alpha=0.25, color=colors[i % len(colors)])
            
            ax.set_ylim(0, 1)
            ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
            ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
            ax.grid(True)
            
        except Exception as e:
            logger.error(f"创建雷达图失败: {str(e)}")
            ax.text(0.5, 0.5, '数据不足\n无法生成雷达图', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12)
    
    # 颜色辅助函数
    def _get_return_color(self, value: float) -> str:
        """根据收益率获取颜色"""
        if value >= 0.2:
            return self.color_palette['positive'][0]
        elif value >= 0.1:
            return self.color_palette['positive'][1]
        elif value >= 0.0:
            return self.color_palette['positive'][2]
        elif value >= -0.1:
            return self.color_palette['neutral'][1]
        else:
            return self.color_palette['negative'][0]
    
    def _get_sharpe_color(self, value: float) -> str:
        """根据夏普比率获取颜色"""
        if value >= 2.0:
            return self.color_palette['positive'][0]
        elif value >= 1.0:
            return self.color_palette['positive'][1]
        elif value >= 0.5:
            return self.color_palette['positive'][2]
        elif value >= 0.0:
            return self.color_palette['neutral'][1]
        else:
            return self.color_palette['negative'][0]
    
    def _get_drawdown_color(self, value: float) -> str:
        """根据最大回撤获取颜色"""
        if value >= 0.0:
            return self.color_palette['positive'][2]
        elif value >= -0.1:
            return self.color_palette['neutral'][1]
        elif value >= -0.2:
            return self.color_palette['neutral'][2]
        elif value >= -0.3:
            return self.color_palette['negative'][1]
        else:
            return self.color_palette['negative'][0]
    
    def _get_volatility_color(self, value: float) -> str:
        """根据波动率获取颜色"""
        if value <= 0.1:
            return self.color_palette['positive'][0]
        elif value <= 0.2:
            return self.color_palette['positive'][1]
        elif value <= 0.3:
            return self.color_palette['neutral'][1]
        elif value <= 0.4:
            return self.color_palette['neutral'][2]
        else:
            return self.color_palette['negative'][0]
    
    def _get_score_color(self, value: float) -> str:
        """根据综合评分获取颜色"""
        if value >= 0.8:
            return self.color_palette['positive'][0]
        elif value >= 0.6:
            return self.color_palette['positive'][1]
        elif value >= 0.4:
            return self.color_palette['neutral'][1]
        elif value >= 0.2:
            return self.color_palette['neutral'][2]
        else:
            return self.color_palette['negative'][0]
    
    def _get_win_rate_color(self, value: float) -> str:
        """根据胜率获取颜色"""
        if value >= 0.7:
            return self.color_palette['positive'][0]
        elif value >= 0.6:
            return self.color_palette['positive'][1]
        elif value >= 0.5:
            return self.color_palette['positive'][2]
        elif value >= 0.4:
            return self.color_palette['neutral'][1]
        else:
            return self.color_palette['negative'][0]
    
    def _get_var_color(self, value: float) -> str:
        """根据VaR获取颜色"""
        if value >= -0.01:
            return self.color_palette['positive'][2]
        elif value >= -0.02:
            return self.color_palette['neutral'][1]
        elif value >= -0.03:
            return self.color_palette['neutral'][2]
        elif value >= -0.05:
            return self.color_palette['negative'][1]
        else:
            return self.color_palette['negative'][0]
    
    def _get_sortino_color(self, value: float) -> str:
        """根据索提诺比率获取颜色"""
        if value >= 2.0:
            return self.color_palette['positive'][0]
        elif value >= 1.0:
            return self.color_palette['positive'][1]
        elif value >= 0.5:
            return self.color_palette['positive'][2]
        elif value >= 0.0:
            return self.color_palette['neutral'][1]
        else:
            return self.color_palette['negative'][0]
    
    def _get_calmar_color(self, value: float) -> str:
        """根据卡玛比率获取颜色"""
        if value >= 2.0:
            return self.color_palette['positive'][0]
        elif value >= 1.0:
            return self.color_palette['positive'][1]
        elif value >= 0.5:
            return self.color_palette['positive'][2]
        elif value >= 0.0:
            return self.color_palette['neutral'][1]
        else:
            return self.color_palette['negative'][0]


if __name__ == "__main__":
    # 测试代码
    analytics = EnhancedFundAnalytics()
    
    # 创建测试数据
    test_data = pd.DataFrame({
        'fund_code': ['000001', '000002', '000003', '000004', '000005'],
        'fund_name': ['测试基金1', '测试基金2', '测试基金3', '测试基金4', '测试基金5'],
        'daily_return': [0.5, 1.2, -0.8, 0.3, 2.1],
        'annualized_return': [0.15, 0.25, -0.05, 0.08, 0.35],
        'sharpe_ratio': [1.2, 1.8, -0.2, 0.6, 2.2],
        'max_drawdown': [-0.08, -0.12, -0.25, -0.15, -0.06],
        'volatility': [0.12, 0.14, 0.22, 0.16, 0.10],
        'win_rate': [0.65, 0.72, 0.45, 0.58, 0.78],
        'var_95': [-0.015, -0.018, -0.035, -0.022, -0.012],
        'sortino_ratio': [1.5, 2.1, -0.1, 0.8, 2.8],
        'calmar_ratio': [1.8, 2.1, -0.2, 0.5, 5.8],
        'composite_score': [0.72, 0.85, 0.35, 0.58, 0.92]
    })
    
    # 生成综合报告
    result = analytics.generate_comprehensive_report(test_data, "./test_output/")
    print(f"测试报告生成结果: {result}")
    
    # 测试单个图表生成
    print("\n测试单个图表生成:")
    
    # 绩效概览
    overview_path = analytics._create_performance_overview(test_data, "./test_output/", "20240101")
    print(f"绩效概览图表: {overview_path}")
    
    # 收益率分析
    return_path = analytics._create_return_analysis(test_data, "./test_output/", "20240101")
    print(f"收益率分析图表: {return_path}")
    
    # 风险分析
    risk_path = analytics._create_risk_analysis(test_data, "./test_output/", "20240101")
    print(f"风险分析图表: {risk_path}")
    
    # 综合评分
    score_path = analytics._create_composite_score_chart(test_data, "./test_output/", "20240101")
    print(f"综合评分图表: {score_path}")
    
    # 相关性分析
    corr_path = analytics._create_correlation_analysis(test_data, "./test_output/", "20240101")
    print(f"相关性分析图表: {corr_path}")
    
    # 投资建议
    summary_path = analytics._create_investment_summary(test_data, "./test_output/", "20240101")
    print(f"投资建议汇总图表: {summary_path}")