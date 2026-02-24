#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重仓股数据获取器
提供基金重仓股票数据获取功能
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 全局 fetcher 实例
_fetcher_instance = None


class HeavyweightStocksFetcher:
    """基金重仓股数据获取器"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        logger.info("HeavyweightStocksFetcher initialized")
    
    def fetch(self, fund_code: str) -> List[Dict]:
        """获取基金重仓股数据"""
        logger.debug(f"Fetching heavyweight stocks for {fund_code}")
        return []
    
    def fetch_batch(self, fund_codes: List[str]) -> Dict[str, List[Dict]]:
        """批量获取重仓股数据"""
        return {code: self.fetch(code) for code in fund_codes}


def init_fetcher(db_manager=None):
    """初始化全局 fetcher"""
    global _fetcher_instance
    _fetcher_instance = HeavyweightStocksFetcher(db_manager)
    logger.info("Heavyweight stocks fetcher initialized")


def get_fetcher() -> HeavyweightStocksFetcher:
    """获取全局 fetcher 实例"""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = HeavyweightStocksFetcher()
    return _fetcher_instance


def fetch_heavyweight_stocks(fund_code: str, **kwargs) -> List[Dict]:
    """获取基金重仓股（便捷函数）"""
    fetcher = get_fetcher()
    return fetcher.fetch(fund_code)


def fetch_heavyweight_stocks_batch(fund_codes: List[str], **kwargs) -> Dict[str, List[Dict]]:
    """批量获取重仓股（便捷函数）"""
    fetcher = get_fetcher()
    return fetcher.fetch_batch(fund_codes)
