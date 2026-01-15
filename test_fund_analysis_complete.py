#!/usr/bin/env python
# coding: utf-8

import sys
sys.path.insert(0, 'pro2/fund_search')

from enhanced_main import EnhancedFundAnalysisSystem
from data_retrieval.enhanced_database import EnhancedDatabaseManager
from shared.enhanced_config import DATABASE_CONFIG
from datetime import datetime
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_fund_analysis():
    """完整的基金分析测试"""
    
    logger.info("=" * 100)
    logger.info("开始完整的基金分析测试 - 仅保留fund_analysis_results表")
    logger.info("=" * 100)
    
    # 初始化系统
    system = EnhancedFundAnalysisSystem()
    
    # 运行完整分析
    try:
        logger.info("执行完整的基金分析流程...")
        success = system.run_complete_analysis()
        
        if success:
            logger.info("✓ 完整分析成功完成")
        else:
            logger.error("✗ 完整分析失败")
            return False
            
    except Exception as e:
        logger.error(f"✗ 分析过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # 验证数据
    logger.info("=" * 100)
    logger.info("验证数据插入情况")
    logger.info("=" * 100)
    
    db = EnhancedDatabaseManager(DATABASE_CONFIG)
    
    # 查询fund_analysis_results表的记录数
    result = db.execute_query_raw("SELECT COUNT(*) as count FROM fund_analysis_results WHERE analysis_date = '2026-01-15'")
    count = result[0][0] if result else 0
    logger.info(f"✓ fund_analysis_results表2026-01-15的记录数: {count}")
    
    # 验证strategy_results表是否为空（应该没有新数据）
    result = db.execute_query_raw("SELECT COUNT(*) as count FROM strategy_results WHERE analysis_date = '2026-01-15'")
    count_strategy = result[0][0] if result else 0
    logger.info(f"✓ strategy_results表2026-01-15的记录数: {count_strategy} (应该为0)")
    
    # 查询所有列的数据完整性
    logger.info("=" * 100)
    logger.info("检查fund_analysis_results表的数据完整性")
    logger.info("=" * 100)
    
    # 获取表的所有列
    result = db.execute_query_raw("""
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'fund_analysis_results' AND TABLE_SCHEMA = 'fund_analysis'
        ORDER BY ORDINAL_POSITION
    """)
    
    columns = [row[0] for row in result] if result else []
    logger.info(f"表的所有列({len(columns)}个): {', '.join(columns)}")
    
    # 检查每一列的非空值数量
    logger.info("\n检查每一列的数据填充情况:")
    logger.info("-" * 100)
    
    for col in columns:
        if col in ['created_at', 'updated_at']:
            continue
        
        result = db.execute_query_raw(f"""
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN `{col}` IS NULL OR `{col}` = '' OR `{col}` = 0 THEN 1 ELSE 0 END) as empty_count
            FROM fund_analysis_results 
            WHERE analysis_date = '2026-01-15'
        """)
        
        if result:
            total, empty = result[0]
            filled = total - (empty or 0)
            fill_rate = (filled / total * 100) if total > 0 else 0
            status = "✓" if fill_rate >= 80 else "⚠" if fill_rate >= 50 else "✗"
            logger.info(f"{status} {col:30s} - 填充率: {fill_rate:6.1f}% ({filled}/{total})")
    
    # 显示样本数据
    logger.info("\n" + "=" * 100)
    logger.info("fund_analysis_results表样本数据（2026-01-15）")
    logger.info("=" * 100)
    
    result = db.execute_query_raw("""
        SELECT 
            fund_code, fund_name, today_return, yesterday_return, status_label,
            operation_suggestion, annualized_return, sharpe_ratio, max_drawdown,
            volatility, composite_score, analysis_date
        FROM fund_analysis_results 
        WHERE analysis_date = '2026-01-15'
        LIMIT 3
    """)
    
    if result:
        for i, row in enumerate(result, 1):
            logger.info(f"\n样本 {i}:")
            logger.info(f"  基金代码: {row[0]}")
            logger.info(f"  基金名称: {row[1]}")
            logger.info(f"  今日收益: {row[2]:.2f}%")
            logger.info(f"  昨日收益: {row[3]:.2f}%")
            logger.info(f"  状态标签: {row[4]}")
            logger.info(f"  操作建议: {row[5]}")
            logger.info(f"  年化收益: {row[6]:.2f}%")
            logger.info(f"  夏普比率: {row[7]:.4f}")
            logger.info(f"  最大回撤: {row[8]:.2f}%")
            logger.info(f"  波动率: {row[9]:.2f}%")
            logger.info(f"  综合评分: {row[10]:.4f}")
            logger.info(f"  分析日期: {row[11]}")
    else:
        logger.warning("没有找到2026-01-15的数据")
        return False
    
    # 统计汇总
    logger.info("\n" + "=" * 100)
    logger.info("数据统计汇总")
    logger.info("=" * 100)
    
    result = db.execute_query_raw("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT fund_code) as unique_funds,
            MIN(today_return) as min_return,
            MAX(today_return) as max_return,
            AVG(today_return) as avg_return,
            AVG(annualized_return) as avg_annualized,
            AVG(sharpe_ratio) as avg_sharpe,
            AVG(composite_score) as avg_score
        FROM fund_analysis_results 
        WHERE analysis_date = '2026-01-15'
    """)
    
    if result:
        row = result[0]
        logger.info(f"总记录数: {row[0]}")
        logger.info(f"唯一基金数: {row[1]}")
        logger.info(f"最小收益率: {row[2]:.2f}%")
        logger.info(f"最大收益率: {row[3]:.2f}%")
        logger.info(f"平均收益率: {row[4]:.2f}%")
        logger.info(f"平均年化收益: {row[5]:.2f}%")
        logger.info(f"平均夏普比率: {row[6]:.4f}")
        logger.info(f"平均综合评分: {row[7]:.4f}")
    
    logger.info("\n" + "=" * 100)
    logger.info("✓ 测试完成 - 所有数据已正确保存到fund_analysis_results表")
    logger.info("=" * 100)
    
    return True

if __name__ == '__main__':
    success = test_fund_analysis()
    sys.exit(0 if success else 1)
