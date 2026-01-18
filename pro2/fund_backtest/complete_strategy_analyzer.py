#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金策略对比分析完整流程
Complete Fund Strategy Comparison Analysis Process

整合所有模块，提供完整的策略对比分析流程
"""

import argparse
import sys
import os
from datetime import datetime

# 导入所有模块
from strategy_comparison_engine import StrategyComparisonEngine
from strategy_ranking_system import StrategyRankingSystem, RiskProfile
from strategy_advice_report_generator import StrategyAdviceReportGenerator

class CompleteStrategyAnalyzer:
    """
    完整策略分析器
    
    整合策略对比、排名推荐和报告生成功能
    """
    
    def __init__(self, 
                 start_date: str = '2024-01-01',
                 end_date: str = None,
                 base_amount: float = 1000,
                 portfolio_size: int = 8,
                 risk_profile: str = 'moderate'):
        """
        初始化完整分析器
        
        参数：
        start_date: 开始日期
        end_date: 结束日期
        base_amount: 基准金额
        portfolio_size: 组合大小
        risk_profile: 风险偏好
        """
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime('%Y-%m-%d')
        self.base_amount = base_amount
        self.portfolio_size = portfolio_size
        
        # 风险偏好映射
        risk_profile_map = {
            'conservative': RiskProfile.CONSERVATIVE,
            'moderate': RiskProfile.MODERATE,
            'aggressive': RiskProfile.AGGRESSIVE
        }
        self.risk_profile = risk_profile_map.get(risk_profile.lower(), RiskProfile.MODERATE)
        
        # 初始化各个模块
        self.comparison_engine = StrategyComparisonEngine(
            backtest_start_date=start_date,
            backtest_end_date=end_date,
            base_amount=base_amount,
            portfolio_size=portfolio_size
        )
        
        self.ranking_system = StrategyRankingSystem()
        self.report_generator = StrategyAdviceReportGenerator()
        
        # 存储分析结果
        self.analysis_results = {}
    
    def run_complete_analysis(self, 
                             top_n: int = 20,
                             rank_type: str = 'daily',
                             output_dir: str = './strategy_analysis_results',
                             generate_report: bool = True,
                             generate_charts: bool = True) -> dict:
        """
        运行完整的策略分析流程
        
        参数：
        top_n: 获取前N只基金
        rank_type: 排名类型
        output_dir: 输出目录
        generate_report: 是否生成报告
        generate_charts: 是否生成图表
        
        返回：
        dict: 完整的分析结果
        """
        print("=" * 80)
        print("基金策略对比分析完整流程")
        print("=" * 80)
        print(f"分析时间: {self.start_date} 至 {self.end_date}")
        print(f"风险偏好: {self.risk_profile.value}")
        print(f"基准金额: {self.base_amount} 元")
        print(f"组合大小: {self.portfolio_size}")
        print("=" * 80)
        
        try:
            # 步骤1: 运行策略对比回测
            print("\n[步骤1] 运行策略对比回测...")
            comparison_results = self.comparison_engine.run_strategy_comparison(
                top_n=top_n,
                rank_type=rank_type
            )

            # 步骤2: 策略排名和推荐
            print("\n[步骤2] 策略排名和推荐...")
            ranked_strategies = self.ranking_system.rank_strategies(
                comparison_results['strategy_metrics'],
                self.risk_profile
            )

            recommendation = self.ranking_system.recommend_strategy(ranked_strategies)
            portfolio_recommendation = self.ranking_system.create_portfolio_recommendation(
                ranked_strategies,
                portfolio_size=3
            )

            # 步骤3: 生成操作建议报告
            print("\n[步骤3] 生成操作建议报告...")
            if generate_report:
                report_content = self.report_generator.generate_comprehensive_report(
                    comparison_results,
                    ranked_strategies,
                    recommendation,
                    {'portfolio_size': self.portfolio_size, 'base_amount': self.base_amount}
                )

                # 保存报告
                os.makedirs(output_dir, exist_ok=True)
                report_file = self.report_generator.save_report(report_content, output_dir)

                self.analysis_results['report'] = {
                    'content': report_content,
                    'file_path': report_file
                }

                print(f"[成功] 报告已生成: {report_file}")

            # 步骤4: 保存分析结果
            print("\n[步骤4] 保存分析结果...")
            saved_files = self.save_all_results(output_dir)

            # 步骤5: 生成图表
            if generate_charts:
                print("\n[步骤5] 生成分析图表...")
                self.generate_analysis_charts(output_dir)

            # 显示结果摘要
            self.display_analysis_summary()

            print(f"\n[完成] 完整分析流程结束！")
            print(f"[输出] 结果保存在: {output_dir}")

            return self.analysis_results

        except Exception as e:
            print(f"[错误] 分析过程中出错: {e}")
            return {'error': str(e)}

    def save_all_results(self, output_dir: str) -> dict:
        """
        保存所有分析结果

        参数：
        output_dir: 输出目录

        返回：
        dict: 保存的文件列表
        """
        try:
            # 这里可以实现保存逻辑，暂时返回空字典
            print("[保存] 结果保存功能待实现")
            return {}
        except Exception as e:
            print(f"[错误] 保存结果时出错: {e}")
            return {}

    def generate_analysis_charts(self, output_dir: str):
        """
        生成分析图表

        参数：
        output_dir: 输出目录
        """
        try:
            print("[图表] 图表生成功能待实现")
        except Exception as e:
            print(f"[错误] 生成图表时出错: {e}")

    def display_analysis_summary(self):
        """
        显示分析结果摘要
        """
        try:
            print("\n[结果] 策略对比分析结果")
            print("=" * 50)

            if 'comparison' in self.analysis_results:
                comparison = self.analysis_results['comparison']
                print(f"[对比] 策略对比: 共{len(comparison['strategy_results'])}个策略参与对比")

            if 'ranking' in self.analysis_results:
                ranking = self.analysis_results['ranking']
                recommendation = ranking['recommendation']

                print(f"[推荐] 推荐策略: {recommendation.get('recommended_strategy', {}).get('strategy_name', '未知')}")
                print(f"[置信] 置信度: {recommendation.get('confidence_level', '中等')}")

            print("=" * 50)
        except Exception as e:
            print(f"[错误] 显示摘要时出错: {e}")

# 使用示例
if __name__ == "__main__":
    # 创建分析器
    analyzer = CompleteStrategyAnalyzer(
        start_date='2024-01-01',
        end_date='2024-12-31',
        base_amount=1000,
        portfolio_size=6,
        risk_profile='moderate'
    )

    # 运行分析
    results = analyzer.run_complete_analysis(
        top_n=10,
        rank_type='daily',
        output_dir='./test_results',
        generate_report=True,
        generate_charts=False  # 禁用图表以避免matplotlib依赖问题
    )

    if 'error' in results:
        print(f"[失败] 分析失败: {results['error']}")
    else:
        print("[成功] 分析完成！")