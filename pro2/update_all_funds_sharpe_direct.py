#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""直接更新所有基金的夏普比率到数据库"""

import sys
sys.path.insert(0, '.')

import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import pandas as pd
from fund_search.data_retrieval.enhanced_database import EnhancedDatabaseManager
from fund_search.data_retrieval.multi_source_adapter import MultiSourceDataAdapter
from fund_search.shared.enhanced_config import DATABASE_CONFIG


def get_all_funds():
    """获取所有基金"""
    db = EnhancedDatabaseManager(DATABASE_CONFIG)
    query = """
        SELECT DISTINCT fund_code, fund_name 
        FROM user_holdings 
        ORDER BY fund_code
    """
    df = db.execute_query(query)
    return df.to_dict('records') if not df.empty else []


def update_fund_in_db(fund_code, metrics):
    """更新基金数据到数据库"""
    try:
        db = EnhancedDatabaseManager(DATABASE_CONFIG)
        
        # 检查记录是否存在
        check_query = "SELECT id FROM fund_analysis_results WHERE fund_code = %s"
        check_df = db.execute_query(check_query, (fund_code,))
        
        if check_df.empty:
            # 插入新记录
            insert_query = """
                INSERT INTO fund_analysis_results 
                (fund_code, analysis_date, sharpe_ratio, sharpe_ratio_ytd, 
                 sharpe_ratio_1y, sharpe_ratio_all, annualized_return, volatility)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            db.execute_sql(insert_query, (
                fund_code,
                datetime.now(),
                metrics.get('sharpe_ratio'),
                metrics.get('sharpe_ratio_ytd'),
                metrics.get('sharpe_ratio_1y'),
                metrics.get('sharpe_ratio_all'),
                metrics.get('annualized_return'),
                metrics.get('volatility')
            ))
        else:
            # 更新现有记录
            update_query = """
                UPDATE fund_analysis_results 
                SET analysis_date = %s,
                    sharpe_ratio = %s,
                    sharpe_ratio_ytd = %s,
                    sharpe_ratio_1y = %s,
                    sharpe_ratio_all = %s,
                    annualized_return = %s,
                    volatility = %s
                WHERE fund_code = %s
            """
            db.execute_sql(update_query, (
                datetime.now(),
                metrics.get('sharpe_ratio'),
                metrics.get('sharpe_ratio_ytd'),
                metrics.get('sharpe_ratio_1y'),
                metrics.get('sharpe_ratio_all'),
                metrics.get('annualized_return'),
                metrics.get('volatility'),
                fund_code
            ))
        return True
    except Exception as e:
        logger.error(f"DB update error for {fund_code}: {e}")
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("Starting to update all funds Sharpe ratios (Direct)")
    logger.info("=" * 60)
    
    # 获取所有基金
    funds = get_all_funds()
    logger.info(f"Found {len(funds)} funds to update")
    
    adapter = MultiSourceDataAdapter()
    
    success_count = 0
    fail_count = 0
    
    for i, fund in enumerate(funds, 1):
        code = fund['fund_code']
        name = fund['fund_name']
        
        logger.info(f"[{i}/{len(funds)}] Processing {code}...")
        
        try:
            # 获取修复后的指标
            metrics = adapter.get_performance_metrics(code)
            
            # 更新到数据库
            if update_fund_in_db(code, metrics):
                success_count += 1
                logger.info(f"  Success: sharpe_all={metrics.get('sharpe_ratio_all', 0):.4f}, "
                          f"volatility={metrics.get('volatility', 0)*100:.2f}%")
            else:
                fail_count += 1
                
        except Exception as e:
            fail_count += 1
            logger.error(f"  Failed: {e}")
    
    logger.info("=" * 60)
    logger.info(f"Update completed: {success_count} success, {fail_count} failed")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
