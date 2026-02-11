#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""更新所有基金的夏普比率到数据库"""

import sys
sys.path.insert(0, '.')

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from fund_search.data_retrieval.enhanced_database import EnhancedDatabaseManager
from fund_search.data_retrieval.multi_source_adapter import MultiSourceDataAdapter
from fund_search.backtesting.enhanced_strategy import EnhancedInvestmentStrategy
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


def update_fund_sharpe(fund_code, fund_name):
    """更新单个基金的夏普比率"""
    try:
        from fund_search.web.routes.holdings import update_fund_analysis_results
        result = update_fund_analysis_results(fund_code, fund_name)
        return True, result
    except Exception as e:
        return False, str(e)


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("Starting to update all funds Sharpe ratios")
    logger.info("=" * 60)
    
    # 获取所有基金
    funds = get_all_funds()
    logger.info(f"Found {len(funds)} funds to update")
    
    success_count = 0
    fail_count = 0
    
    for i, fund in enumerate(funds, 1):
        code = fund['fund_code']
        name = fund['fund_name']
        
        logger.info(f"[{i}/{len(funds)}] Updating {code} - {name}...")
        
        success, result = update_fund_sharpe(code, name)
        
        if success:
            success_count += 1
            logger.info(f"  Success: sharpe_all={result.get('sharpe_ratio_all', 'N/A'):.4f}")
        else:
            fail_count += 1
            logger.error(f"  Failed: {result}")
    
    logger.info("=" * 60)
    logger.info(f"Update completed: {success_count} success, {fail_count} failed")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
