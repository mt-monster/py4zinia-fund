#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略操作建议报告生成器
Strategy Operation Advice Report Generator

生成详细的策略操作建议和投资指导报告
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import os

class StrategyAdviceReportGenerator:
    """
    策略操作建议报告生成器
    
    功能：
    1. 生成详细的策略操作建议
    2. 提供市场环境分析
    3. 制定投资计划
    4. 风险管理建议
    """
    
    def __init__(self):
        """初始化报告生成器"""
        self.report_templates = {
            'market_analysis': self.generate_market_analysis,
            'strategy_advice': self.generate_strategy_advice,
            'risk_management': self.generate_risk_management,
            'investment_plan': self.generate_investment_plan,
            'performance_monitoring': self.generate_performance_monitoring
        }
    
    def generate_comprehensive_report(self, 
                                    strategy_results: Dict,
                                    ranked_strategies: List[Dict],
                                    recommendation: Dict,
                                    portfolio_info: Dict) -> str:
        """
        生成综合策略建议报告
        
        参数：
        strategy_results: 策略回测结果
        ranked_strategies: 排名后的策略列表
        recommendation: 策略推荐结果
        portfolio_info: 组合信息
        
        返回：
        str: 完整的Markdown报告
        """
        report_sections = []
        
        # 报告标题
        report_sections.append(self.generate_report_header())
        
        # 执行摘要
        report_sections.append(self.generate_executive_summary(recommendation, portfolio_info))
        
        # 市场环境分析
        report_sections.append(self.generate_market_analysis(strategy_results))
        
        # 策略详细分析
        report_sections.append(self.generate_strategy_detailed_analysis(ranked_strategies))
        
        # 推荐策略操作建议
        report_sections.append(self.generate_strategy_advice(recommendation))
        
        # 投资计划制定
        report_sections.append(self.generate_investment_plan(recommendation, portfolio_info))
        
        # 风险管理建议
        report_sections.append(self.generate_risk_management(ranked_strategies))
        
        # 绩效监控方案
        report_sections.append(self.generate_performance_monitoring(recommendation))
        
        # 结论和展望
        report_sections.append(self.generate_conclusion(recommendation))
        
        # 免责声明
        report_sections.append(self.generate_disclaimer())
        
        return "\n\n".join(report_sections)
    
    def generate_report_header(self) -> str:
        """生成报告标题"""
        current_time = datetime.now().strftime('%Y年%m月%d日 %H:%M')
        return f"""# 基金投资策略操作建议报告

**报告生成时间**: {current_time}  
**分析周期**: 最近12个月  
**报告版本**: v1.0

---

"""
    
    def generate_executive_summary(self, recommendation: Dict, portfolio_info: Dict) -> str:
        """生成执行摘要"""
        best_strategy = recommendation.get('recommended_strategy', {})
        confidence = recommendation.get('confidence_level', '中等')
        
        return f"""## 📊 执行摘要

### 核心推荐
- **推荐策略**: {best_strategy.get('strategy_name', '未知')}
- **置信度**: {confidence}
- **预期年化收益**: {best_strategy.get('raw_metrics', {}).get('annualized_return', 0):.1%}
- **预期最大回撤**: {best_strategy.get('raw_metrics', {}).get('max_drawdown', 0):.1%}

### 投资建议等级
{"🟢 **强烈推荐**" if confidence in ['很高', '较高'] else "🟡 **谨慎推荐**" if confidence == '中等' else "🔴 **观望**"}

### 关键要点
{chr(10).join([f"- {reason}" for reason in recommendation.get('recommendation_reasons', ['暂无具体理由'])])}

---

"""
    
    def generate_market_analysis(self, strategy_results: Dict) -> str:
        """生成市场环境分析"""
        # 基于策略表现推断市场特征
        market_analysis = self.analyze_market_environment(strategy_results)
        
        return f"""## 🌍 市场环境分析

### 当前市场特征
{market_analysis['market_characteristics']}

### 策略适用性分析
{market_analysis['strategy_applicability']}

### 市场风险评估
{market_analysis['risk_assessment']}

### 未来展望
{market_analysis['outlook']}

---

"""
    
    def analyze_market_environment(self, strategy_results: Dict) -> Dict:
        """分析市场环境"""
        # 这里应该基于实际市场数据分析，暂时使用模拟分析
        return {
            'market_characteristics': """
- **波动性**: 中等偏高，日波动率约1.5-2.5%
- **趋势性**: 震荡为主，局部趋势明显
- **流动性**: 充足，成交活跃
- **市场情绪**: 谨慎乐观，风险偏好适中
            """.strip(),
            'strategy_applicability': """
- **趋势策略**: 适合局部趋势行情，需注意震荡损耗
- **均值回归策略**: 适合当前震荡环境，成功概率较高
- **网格交易策略**: 波动率适中，适合区间操作
- **目标市值策略**: 适合长期稳健投资
            """.strip(),
            'risk_assessment': """
- **系统性风险**: 中等，需关注宏观经济变化
- **流动性风险**: 较低，市场流动性充足
- **波动性风险**: 中等偏高，建议控制仓位
- **政策风险**: 需关注监管政策变化
            """.strip(),
            'outlook': """
- **短期(1-3个月)**: 震荡为主，结构性机会
- **中期(3-6个月)**: 可能迎来趋势性行情
- **长期(6-12个月)**: 基本面驱动，谨慎乐观
            """.strip()
        }
    
    def generate_strategy_detailed_analysis(self, ranked_strategies: List[Dict]) -> str:
        """生成策略详细分析"""
        analysis_sections = ["## 📈 策略详细分析\n"]
        
        for i, strategy in enumerate(ranked_strategies[:5], 1):  # 分析前5个策略
            strategy_name = strategy['strategy_name']
            metrics = strategy['raw_metrics']
            
            analysis_sections.append(f"""
### {i}. {strategy_name}

**综合评分**: {strategy['total_score']:.3f} (排名第{i}位)

#### 关键指标
- **总收益率**: {metrics['total_return']:.2%}
- **年化收益率**: {metrics['annualized_return']:.2%}
- **最大回撤**: {metrics['max_drawdown']:.2%}
- **夏普比率**: {metrics['sharpe_ratio']:.2f}
- **胜率**: {metrics['win_rate']:.2%}
- **交易次数**: {metrics['total_trades']}次

#### 评分细项
- **收益得分**: {strategy['return_score']:.3f}
- **风险得分**: {strategy['risk_score']:.3f}
- **夏普得分**: {strategy['sharpe_score']:.3f}
- **稳定性得分**: {strategy['consistency_score']:.3f}
- **交易频率得分**: {strategy['trade_freq_score']:.3f}

#### 策略特点
{self.analyze_strategy_characteristics(strategy_name, metrics)}

#### 适用场景
{self.analyze_strategy_scenarios(strategy_name, metrics)}

---
            """)
        
        return "\n".join(analysis_sections)
    
    def analyze_strategy_characteristics(self, strategy_name: str, metrics: Dict) -> str:
        """分析策略特点"""
        characteristics = []
        
        if 'dual_ma' in strategy_name.lower():
            characteristics.extend([
                "趋势跟踪型策略，适合有明显方向的市场",
                "使用双均线交叉信号，减少假信号",
                "中长线持有，交易频率适中"
            ])
        elif 'mean_reversion' in strategy_name.lower():
            characteristics.extend([
                "逆向投资型策略，适合震荡市场",
                "基于均值回归原理，低买高卖",
                "需要较强的心理素质，逆势操作"
            ])
        elif 'target_value' in strategy_name.lower():
            characteristics.extend([
                "成本平均型策略，适合定投",
                "动态调整投资金额，平滑成本",
                "长期稳健，波动相对较小"
            ])
        elif 'grid' in strategy_name.lower():
            characteristics.extend([
                "区间交易型策略，适合震荡行情",
                "分批买入卖出，降低平均成本",
                "需要较多资金和耐心"
            ])
        
        # 基于指标补充特点
        if metrics['sharpe_ratio'] > 1.5:
            characteristics.append("风险调整收益优秀")
        
        if metrics['max_drawdown'] > -0.1:
            characteristics.append("风险控制良好")
        
        if metrics['win_rate'] > 0.7:
            characteristics.append("胜率较高，心理压力小")
        
        return "\n- ".join(characteristics)
    
    def analyze_strategy_scenarios(self, strategy_name: str, metrics: Dict) -> str:
        """分析策略适用场景"""
        scenarios = []
        
        if 'dual_ma' in strategy_name.lower():
            scenarios.extend([
                "牛市和熊市的中期趋势",
                "突破重要技术位后的行情",
                "基本面驱动的结构性行情"
            ])
        elif 'mean_reversion' in strategy_name.lower():
            scenarios.extend([
                "震荡市和区间整理",
                "过度反应后的修正行情",
                "支撑阻力位明显的市场"
            ])
        elif 'target_value' in strategy_name.lower():
            scenarios.extend([
                "长期投资和退休规划",
                "定期现金流需求的投资者",
                "风险厌恶型投资者"
            ])
        elif 'grid' in strategy_name.lower():
            scenarios.extend([
                "波动率适中的震荡市",
                "箱体运行的行情",
                "有明确支撑阻力的市场"
            ])
        
        return "\n- ".join(scenarios)
    
    def generate_strategy_advice(self, recommendation: Dict) -> str:
        """生成策略操作建议"""
        best_strategy = recommendation.get('recommended_strategy', {})
        strategy_name = best_strategy.get('strategy_name', '')
        usage_suggestions = recommendation.get('usage_suggestions', [])
        
        return f"""## 🎯 推荐策略操作建议

### 策略名称: {strategy_name}

#### 核心操作要点
{self.generate_core_operation_advice(best_strategy)}

#### 具体执行建议
{chr(10).join([f"{i+1}. {suggestion}" for i, suggestion in enumerate(usage_suggestions)])}

#### 参数设置建议
{self.generate_parameter_settings_advice(best_strategy)}

#### 注意事项
{self.generate_precautions_advice(best_strategy)}

---

"""
    
    def generate_core_operation_advice(self, strategy: Dict) -> str:
        """生成核心操作建议"""
        strategy_name = strategy.get('strategy_name', '').lower()
        metrics = strategy.get('raw_metrics', {})
        
        if 'dual_ma' in strategy_name:
            return """
- **信号确认**: 等待均线交叉确认，避免假突破
- **仓位管理**: 金叉时加仓至70%，死叉时减仓至30%
- **止损设置**: 设置5-8%的止损位，控制单笔损失
- **持有周期**: 平均持有20-40个交易日
            """.strip()
        
        elif 'mean_reversion' in strategy_name:
            return """
- **偏离判断**: 价格偏离均线5%以上开始关注
- **分批建仓**: 极度低估时分2-3批建仓
- **止盈设置**: 回归均线时分批止盈
- **风险控制**: 单次投入不超过总资金的20%
            """.strip()
        
        elif 'target_value' in strategy_name:
            return """
- **目标设定**: 根据投资期限设定合理的目标增长额
- **定期调整**: 每月检查市值，动态调整投资金额
- **长期持有**: 忽略短期波动，专注长期目标
- **资金规划**: 确保有充足的现金流支持
            """.strip()
        
        elif 'grid' in strategy_name:
            return """
- **网格设置**: 3-5%的网格间距，适合当前波动率
- **资金分配**: 预留10-15层网格的资金
- **执行纪律**: 严格按照网格信号操作，不主观判断
- **动态调整**: 根据波动率变化适时调整网格参数
            """.strip()
        
        else:
            return "请参考策略具体说明进行操作。"
    
    def generate_parameter_settings_advice(self, strategy: Dict) -> str:
        """生成参数设置建议"""
        strategy_name = strategy.get('strategy_name', '').lower()
        
        if 'dual_ma' in strategy_name:
            return """
- **短期均线**: 15-25日（推荐20日）
- **长期均线**: 50-70日（推荐60日）
- **确认周期**: 交叉后持有2-3日确认
- **仓位系数**: 1.2-1.8倍（推荐1.5倍）
            """.strip()
        
        elif 'mean_reversion' in strategy_name:
            return """
- **均线周期**: 200-300日（推荐250日）
- **偏离阈值**: 3-8%（推荐5%）
- **极度偏离**: 10%以上
- **仓位系数**: 1.5-2.5倍（根据偏离度调整）
            """.strip()
        
        elif 'target_value' in strategy_name:
            return """
- **目标增长**: 根据投资目标设定（推荐月增长1000-5000元）
- **调整频率**: 每月或每季度调整一次
- **基准金额**: 初始投资的1-2%
- **上限控制**: 单次投入不超过基准的3倍
            """.strip()
        
        elif 'grid' in strategy_name:
            return """
- **网格大小**: 2-5%（推荐3%）
- **网格层数**: 10-20层
- **单层金额**: 总资金的5-10%
- **动态调整**: 根据ATR调整网格大小
            """.strip()
        
        else:
            return "请使用策略默认参数设置。"
    
    def generate_precautions_advice(self, strategy: Dict) -> str:
        """生成注意事项"""
        precautions = [
            "严格执行策略信号，避免情绪干扰",
            "定期回顾策略表现，必要时调整参数",
            "关注市场环境变化，适时切换策略",
            "控制单次投入金额，分散投资风险"
        ]
        
        strategy_name = strategy.get('strategy_name', '').lower()
        metrics = strategy.get('raw_metrics', {})
        
        if 'dual_ma' in strategy_name:
            precautions.extend([
                "震荡市中容易出现假信号，需注意过滤",
                "趋势末期风险加大，建议降低仓位"
            ])
        
        elif 'mean_reversion' in strategy_name:
            precautions.extend([
                "强趋势行情中可能持续亏损，需设置止损",
                "需要较强的心理素质，克服恐惧贪婪"
            ])
        
        elif 'target_value' in strategy_name:
            precautions.extend([
                "需要充足的现金流支持",
                "市场极端情况下可能需要额外资金"
            ])
        
        elif 'grid' in strategy_name:
            precautions.extend([
                "单边行情中可能耗尽资金",
                "需要预留充足的资金支持"
            ])
        
        if metrics.get('max_drawdown', 0) < -0.15:
            precautions.append("该策略回撤较大，务必控制仓位")
        
        return "\n- ".join(precautions)
    
    def generate_investment_plan(self, recommendation: Dict, portfolio_info: Dict) -> str:
        """生成投资计划"""
        best_strategy = recommendation.get('recommended_strategy', {})
        
        return f"""## 💼 投资计划制定

### 资金配置建议
{self.generate_capital_allocation_advice(best_strategy, portfolio_info)}

### 投资时间规划
{self.generate_investment_timeline_advice(best_strategy)}

### 阶段性目标
{self.generate_phase_targets_advice(best_strategy)}

### 资金管理策略
{self.generate_capital_management_advice(best_strategy)}

---

"""
    
    def generate_capital_allocation_advice(self, strategy: Dict, portfolio_info: Dict) -> str:
        """生成资金配置建议"""
        return f"""
- **总投资资金**: 建议不超过可投资金的60%
- **单策略投入**: {strategy.get('strategy_name', '')}策略占用40-50%
- **备用资金**: 保留20-30%作为补充资金
- **其他投资**: 20-30%可配置其他策略或资产
        """.strip()
    
    def generate_investment_timeline_advice(self, strategy: Dict) -> str:
        """生成投资时间规划建议"""
        strategy_name = strategy.get('strategy_name', '').lower()
        
        if 'dual_ma' in strategy_name:
            return """
- **建仓期**: 1-2个月，分批建仓
- **观察期**: 1个月，熟悉策略信号
- **正常运作**: 6-12个月
- **评估调整**: 每3个月评估一次
            """.strip()
        
        elif 'mean_reversion' in strategy_name:
            return """
- **建仓期**: 2-3个月，等待低估机会
- **观察期**: 1个月，验证偏离判断
- **正常运作**: 6-12个月
- **评估调整**: 每季度评估参数
            """.strip()
        
        else:
            return """
- **建仓期**: 1-3个月
- **观察期**: 1个月
- **正常运作**: 6-12个月
- **评估调整**: 每季度评估
            """.strip()
    
    def generate_phase_targets_advice(self, strategy: Dict) -> str:
        """生成阶段性目标建议"""
        return """
- **短期目标(3个月)**: 熟悉策略，验证有效性
- **中期目标(6个月)**: 实现稳定收益，控制回撤
- **长期目标(12个月)**: 达到预期年化收益目标
- **风险目标**: 最大回撤控制在15%以内
        """.strip()
    
    def generate_capital_management_advice(self, strategy: Dict) -> str:
        """生成资金管理策略建议"""
        return """
- **仓位控制**: 单次投入不超过总资金的10%
- **止损纪律**: 严格执行止损，避免大幅亏损
- **止盈策略**: 分批止盈，锁定收益
- **资金补充**: 必要时及时补充资金
        """.strip()
    
    def generate_risk_management(self, ranked_strategies: List[Dict]) -> str:
        """生成风险管理建议"""
        return f"""## ⚠️ 风险管理建议

### 主要风险识别
{self.identify_main_risks(ranked_strategies)}

### 风险控制措施
{self.generate_risk_control_measures()}

### 应急预案
{self.generate_emergency_plan()}

### 风险监控指标
{self.generate_risk_monitoring_indicators()}

---

"""
    
    def identify_main_risks(self, ranked_strategies: List[Dict]) -> str:
        """识别主要风险"""
        risks = [
            "市场系统性风险：宏观经济变化、政策调整",
            "策略适应性风险：市场环境变化导致策略失效",
            "流动性风险：极端情况下的资金流动性问题",
            "执行风险：人为因素导致的策略执行偏差"
        ]
        
        # 基于策略数据补充风险
        if ranked_strategies:
            max_drawdown = max(abs(s.get('raw_metrics', {}).get('max_drawdown', 0)) for s in ranked_strategies)
            if max_drawdown > 0.2:
                risks.append("高回撤风险：策略历史最大回撤较大")
        
        return "\n- ".join(risks)
    
    def generate_risk_control_measures(self) -> str:
        """生成风险控制措施"""
        return """
- **仓位控制**: 单策略仓位不超过50%，总仓位不超过80%
- **止损设置**: 严格执行5-10%的止损线
- **分散投资**: 配置2-3种不同类型的策略
- **定期评估**: 每月评估策略表现和市场环境
        """.strip()
    
    def generate_emergency_plan(self) -> str:
        """生成应急预案"""
        return """
- **大幅亏损预案**: 亏损超过15%时暂停策略，评估原因
- **市场异常预案**: 极端行情时降低仓位，增加现金比例
- **策略失效预案**: 连续3个月表现不佳时考虑更换策略
- **资金流动性预案**: 预留应急资金，应对追加保证金需求
        """.strip()
    
    def generate_risk_monitoring_indicators(self) -> str:
        """生成风险监控指标"""
        return """
- **回撤监控**: 每日监控最大回撤，超过10%预警
- **夏普比率**: 月度夏普比率低于0.5时预警
- **胜率监控**: 月度胜率低于40%时预警
- **波动率监控**: 策略波动率异常增大时预警
        """.strip()
    
    def generate_performance_monitoring(self, recommendation: Dict) -> str:
        """生成绩效监控方案"""
        return f"""## 📊 绩效监控方案

### 监控频率
{self.generate_monitoring_frequency()}

### 关键绩效指标
{self.generate_key_performance_indicators(recommendation)}

### 评估标准
{self.generate_evaluation_criteria()}

### 调整机制
{self.generate_adjustment_mechanism()}

---

"""
    
    def generate_monitoring_frequency(self) -> str:
        """生成监控频率建议"""
        return """
- **日常监控**: 每日检查策略信号执行情况
- **周度评估**: 每周评估策略表现和收益情况
- **月度分析**: 每月分析绩效指标和风险状况
- **季度回顾**: 每季度全面回顾策略效果
        """.strip()
    
    def generate_key_performance_indicators(self, recommendation: Dict) -> str:
        """生成关键绩效指标"""
        return """
- **收益指标**: 总收益率、年化收益率、超额收益
- **风险指标**: 最大回撤、波动率、下行风险
- **风险调整收益**: 夏普比率、索提诺比率、卡尔玛比率
- **交易指标**: 胜率、盈亏比、交易频率
        """.strip()
    
    def generate_evaluation_criteria(self) -> str:
        """生成评估标准"""
        return """
- **优秀**: 年化收益>15%，夏普比率>1.5，最大回撤<10%
- **良好**: 年化收益>10%，夏普比率>1.0，最大回撤<15%
- **一般**: 年化收益>5%，夏普比率>0.5，最大回撤<20%
- **较差**: 低于一般标准，需要调整或更换
        """.strip()
    
    def generate_adjustment_mechanism(self) -> str:
        """生成调整机制"""
        return """
- **参数调整**: 每季度根据市场变化调整策略参数
- **仓位调整**: 根据风险评估结果调整仓位大小
- **策略切换**: 连续表现不佳时考虑切换策略
- **组合优化**: 定期优化策略组合配置
        """.strip()
    
    def generate_conclusion(self, recommendation: Dict) -> str:
        """生成结论和展望"""
        best_strategy = recommendation.get('recommended_strategy', {})
        confidence = recommendation.get('confidence_level', '中等')
        
        return f"""## 🎯 结论与展望

### 投资建议总结
基于全面的策略分析和回测验证，我们**{'强烈推荐' if confidence in ['很高', '较高'] else '推荐'}**使用 **{best_strategy.get('strategy_name', '')}** 策略进行基金投资。

### 预期效果
- **年化收益率**: {best_strategy.get('raw_metrics', {}).get('annualized_return', 0):.1%} 左右
- **最大回撤**: 控制在 {abs(best_strategy.get('raw_metrics', {}).get('max_drawdown', 0)):.1%} 以内
- **夏普比率**: 预期在 {best_strategy.get('raw_metrics', {}).get('sharpe_ratio', 0):.1f} 左右

### 成功关键因素
1. **严格执行**: 坚决按照策略信号操作，避免情绪干扰
2. **风险控制**: 时刻关注风险指标，及时调整仓位
3. **持续学习**: 不断总结经验，优化策略参数
4. **长期坚持**: 投资是长期过程，保持耐心和信心

### 未来展望
随着市场环境的变化和策略的持续优化，预期该策略将能够：
- 在不同市场环境下保持稳定的盈利能力
- 为投资者创造持续的风险调整后收益
- 成为基金投资的重要工具和参考

---

"""
    
    def generate_disclaimer(self) -> str:
        """生成免责声明"""
        return """## ⚠️ 免责声明

**重要提示**：

1. 本报告基于历史数据分析和量化模型，仅供参考，不构成投资建议。

2. 过往业绩不代表未来表现，投资有风险，入市需谨慎。

3. 投资者应根据自身风险承受能力、投资目标和财务状况独立做出投资决策。

4. 市场有风险，投资需谨慎。建议在投资前咨询专业的投资顾问。

5. 本报告的任何内容均不应被视为对任何投资产品的要约、推荐或承诺。

**报告有效期**：本报告有效期为3个月，过期请重新评估。

**版权声明**：本报告版权归作者所有，未经许可不得转载或使用。

---

*报告生成完毕 | 祝您投资顺利！*
"""
    
    def save_report(self, report_content: str, output_dir: str = '../reports') -> str:
        """
        保存报告到文件
        
        参数：
        report_content: 报告内容
        output_dir: 输出目录
        
        返回：
        str: 保存的文件路径
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"strategy_advice_report_{timestamp}.md"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            print(f"✓ 策略建议报告已保存: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ 保存报告时出错: {e}")
            return ""

# 使用示例
if __name__ == "__main__":
    # 创建报告生成器
    generator = StrategyAdviceReportGenerator()
    
    # 模拟数据
    mock_strategy_results = {'mock': 'data'}
    mock_ranked_strategies = [
        {
            'strategy_name': 'dual_ma',
            'total_score': 0.85,
            'raw_metrics': {
                'total_return': 0.25,
                'annualized_return': 0.22,
                'max_drawdown': -0.12,
                'sharpe_ratio': 1.8,
                'win_rate': 0.65,
                'total_trades': 45
            }
        }
    ]
    mock_recommendation = {
        'recommended_strategy': mock_ranked_strategies[0],
        'confidence_level': '较高',
        'recommendation_reasons': ['风险调整收益优秀', '策略表现稳定'],
        'usage_suggestions': ['适合趋势明显的市场环境', '建议关注均线交叉信号']
    }
    mock_portfolio_info = {'total_value': 100000}
    
    # 生成报告
    report = generator.generate_comprehensive_report(
        mock_strategy_results,
        mock_ranked_strategies,
        mock_recommendation,
        mock_portfolio_info
    )
    
    # 保存报告
    generator.save_report(report)
    
    print("策略建议报告生成完成！")