#!/usr/bin/env python
# coding: utf-8

"""
基金相关性分析测试脚本
根据 README_CORRELATION_ANALYSIS.md 文件中的测试案例进行测试
"""

import logging
import sys
from typing import List, Dict

# 添加项目根目录到Python路径
sys.path.insert(0, 'd:\\codes\\py4zinia\\pro2\\fund_search')

from data_retrieval.fund_analyzer import FundAnalyzer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_correlation_analysis(fund_codes: List[str], test_name: str) -> Dict:
    """
    测试基金相关性分析
    
    参数：
    fund_codes: 基金代码列表
    test_name: 测试名称
    
    返回：
    dict: 相关性分析结果
    """
    logger.info(f"开始测试: {test_name}")
    logger.info(f"测试基金代码: {fund_codes}")
    
    try:
        # 初始化基金分析器
        analyzer = FundAnalyzer()
        
        # 执行相关性分析
        result = analyzer.analyze_correlation(fund_codes)
        
        # 打印测试结果
        logger.info(f"测试完成: {test_name}")
        logger.info(f"基金名称: {result['fund_names']}")
        logger.info(f"使用数据点: {result['data_points']}")
        logger.info("相关性矩阵:")
        
        # 格式化打印相关性矩阵
        fund_names = result['fund_names']
        correlation_matrix = result['correlation_matrix']
        
        # 打印表头
        header = "\t".join(["" for _ in range(len(fund_names) + 1)])
        logger.info(header)
        
        # 打印每一行数据
        for i, (fund_name, row) in enumerate(zip(fund_names, correlation_matrix)):
            row_str = "\t".join([f"{val:.4f}" for val in row])
            logger.info(f"{fund_name}\t{row_str}")
        
        logger.info("\n" + "="*80 + "\n")
        
        return result
        
    except Exception as e:
        logger.error(f"测试失败: {test_name}")
        logger.error(f"错误信息: {e}")
        logger.info("\n" + "="*80 + "\n")
        return None


def main():
    """
    主测试函数
    """
    logger.info("开始基金相关性分析测试")
    logger.info("="*80)
    
    # 测试案例 1：分析三只不同类型基金的相关性
    test_correlation_analysis(
        fund_codes=["110011", "110050", "159934"],
        test_name="分析三只不同类型基金的相关性"
    )
    
    # 测试案例 2：分析两只同类型基金的相关性
    test_correlation_analysis(
        fund_codes=["110011", "162605"],
        test_name="分析两只同类型基金的相关性"
    )
    
    # 测试案例 3：分析不同行业基金的相关性
    test_correlation_analysis(
        fund_codes=["159928", "512010", "512480", "515030"],
        test_name="分析不同行业基金的相关性"
    )
    
    # 测试案例 4：分析更多基金的相关性
    test_correlation_analysis(
        fund_codes=["513050", "511010", "508000", "511010"],
        test_name="分析四只基金的相关性"
    )
    
    logger.info("基金相关性分析测试完成")
    logger.info("="*80)


if __name__ == "__main__":
    main()
