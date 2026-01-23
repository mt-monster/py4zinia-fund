#!/usr/bin/env python
# coding: utf-8

"""
基金相关性分析测试脚本（改进版）
根据 README_CORRELATION_ANALYSIS.md 文件中的测试案例进行测试
"""

import logging
import sys
from typing import List, Dict
import json

# 添加项目根目录到Python路径
sys.path.insert(0, 'd:\\codes\\py4zinia\\pro2\\fund_search')

from data_retrieval.fund_analyzer import FundAnalyzer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def format_correlation_matrix(fund_names: List[str], correlation_matrix: List[List[float]]) -> str:
    """
    格式化相关性矩阵为表格形式
    
    参数：
    fund_names: 基金名称列表
    correlation_matrix: 相关性矩阵
    
    返回：
    str: 格式化的表格字符串
    """
    # 计算列宽
    max_name_len = max(len(name) for name in fund_names)
    col_width = max(max_name_len, 8)
    
    # 构建表头
    header = "基金名称".ljust(col_width)
    for name in fund_names:
        header += name[:col_width].ljust(col_width)
    
    # 构建分隔线
    separator = "-" * (col_width * (len(fund_names) + 1))
    
    # 构建数据行
    rows = [header, separator]
    for i, name in enumerate(fund_names):
        row = name[:col_width].ljust(col_width)
        for j, value in enumerate(correlation_matrix[i]):
            row += f"{value:.4f}".ljust(col_width)
        rows.append(row)
    
    return "\n".join(rows)


def interpret_correlation(r: float) -> str:
    """
    解释相关系数的含义
    
    参数：
    r: 相关系数
    
    返回：
    str: 相关性解释
    """
    if r > 0.8:
        return "强正相关 (风险集中)"
    elif r > 0.5:
        return "中等正相关 (风险较集中)"
    elif r > 0.2:
        return "弱正相关 (风险分散一般)"
    elif r > -0.2:
        return "无相关性 (风险分散最佳)"
    elif r > -0.5:
        return "弱负相关 (风险对冲)"
    else:
        return "强负相关 (风险对冲最佳)"


def analyze_correlation_quality(correlation_matrix: List[List[float]]) -> Dict:
    """
    分析相关性矩阵的质量
    
    参数：
    correlation_matrix: 相关性矩阵
    
    返回：
    dict: 质量分析结果
    """
    n = len(correlation_matrix)
    
    # 提取非对角线元素
    off_diagonal = []
    for i in range(n):
        for j in range(i + 1, n):
            off_diagonal.append(correlation_matrix[i][j])
    
    if not off_diagonal:
        return {}
    
    import numpy as np
    off_diagonal = np.array(off_diagonal)
    
    return {
        'avg_correlation': float(np.mean(off_diagonal)),
        'max_correlation': float(np.max(off_diagonal)),
        'min_correlation': float(np.min(off_diagonal)),
        'std_correlation': float(np.std(off_diagonal)),
        'diversification_score': float(1 - np.mean(np.abs(off_diagonal)))  # 分散度评分
    }


def test_correlation_analysis(fund_codes: List[str], test_name: str) -> Dict:
    """
    测试基金相关性分析
    
    参数：
    fund_codes: 基金代码列表
    test_name: 测试名称
    
    返回：
    dict: 相关性分析结果
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"测试: {test_name}")
    logger.info(f"基金代码: {fund_codes}")
    logger.info(f"{'='*80}")
    
    try:
        # 初始化基金分析器
        analyzer = FundAnalyzer(enable_cache=True)
        
        # 执行相关性分析
        result = analyzer.analyze_correlation(fund_codes)
        
        # 打印基本信息
        logger.info(f"\n✓ 测试完成: {test_name}")
        logger.info(f"  - 分析基金数: {len(result['fund_codes'])}")
        logger.info(f"  - 使用数据点: {result['data_points']}")
        logger.info(f"  - 分析时间: {result['analysis_date']}")
        
        if result['failed_codes']:
            logger.warning(f"  - 失败基金数: {len(result['failed_codes'])}")
            for code, reason in result['failed_codes']:
                logger.warning(f"    • {code}: {reason}")
        
        # 打印相关性矩阵
        logger.info(f"\n相关性矩阵:")
        logger.info(format_correlation_matrix(result['fund_names'], result['correlation_matrix']))
        
        # 分析相关性质量
        quality = analyze_correlation_quality(result['correlation_matrix'])
        if quality:
            logger.info(f"\n相关性质量分析:")
            logger.info(f"  - 平均相关性: {quality['avg_correlation']:.4f}")
            logger.info(f"  - 最大相关性: {quality['max_correlation']:.4f}")
            logger.info(f"  - 最小相关性: {quality['min_correlation']:.4f}")
            logger.info(f"  - 标准差: {quality['std_correlation']:.4f}")
            logger.info(f"  - 分散度评分: {quality['diversification_score']:.4f} (0-1, 越高越好)")
        
        # 打印相关性解释
        logger.info(f"\n相关性解释:")
        n = len(result['fund_codes'])
        for i in range(n):
            for j in range(i + 1, n):
                r = result['correlation_matrix'][i][j]
                interpretation = interpret_correlation(r)
                logger.info(f"  - {result['fund_names'][i]} ↔ {result['fund_names'][j]}: "
                          f"{r:.4f} ({interpretation})")
        
        logger.info(f"\n{'='*80}\n")
        
        return result
        
    except Exception as e:
        logger.error(f"✗ 测试失败: {test_name}")
        logger.error(f"  错误信息: {e}")
        logger.info(f"\n{'='*80}\n")
        return None


def main():
    """
    主测试函数
    """
    logger.info("\n" + "="*80)
    logger.info("基金相关性分析测试套件")
    logger.info("="*80)
    
    results = {}
    
    # 测试案例 1：分析三只不同类型基金的相关性
    results['test1'] = test_correlation_analysis(
        fund_codes=["110011", "110050", "159934"],
        test_name="分析三只不同类型基金的相关性"
    )
    
    # 测试案例 2：分析两只同类型基金的相关性
    results['test2'] = test_correlation_analysis(
        fund_codes=["110011", "162605"],
        test_name="分析两只同类型基金的相关性"
    )
    
    # 测试案例 3：分析不同行业基金的相关性
    results['test3'] = test_correlation_analysis(
        fund_codes=["159928", "512010", "512480", "515030"],
        test_name="分析不同行业基金的相关性"
    )
    
    # 测试案例 4：测试重复基金代码处理
    results['test4'] = test_correlation_analysis(
        fund_codes=["110011", "110011", "110050"],
        test_name="测试重复基金代码处理"
    )
    
    # 测试案例 5：测试无效基金代码处理
    results['test5'] = test_correlation_analysis(
        fund_codes=["999999", "110011", "110050"],
        test_name="测试无效基金代码处理"
    )
    
    # 生成测试总结
    logger.info("\n" + "="*80)
    logger.info("测试总结")
    logger.info("="*80)
    
    success_count = sum(1 for r in results.values() if r is not None)
    total_count = len(results)
    
    logger.info(f"\n总体结果: {success_count}/{total_count} 测试通过")
    
    for test_name, result in results.items():
        if result:
            logger.info(f"✓ {test_name}: 成功 ({result['data_points']} 数据点)")
        else:
            logger.info(f"✗ {test_name}: 失败")
    
    logger.info("\n" + "="*80)
    logger.info("测试完成")
    logger.info("="*80 + "\n")


if __name__ == "__main__":
    main()
