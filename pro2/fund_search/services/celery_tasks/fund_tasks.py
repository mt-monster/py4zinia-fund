#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金相关的 Celery 异步任务
"""

import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from services.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='fund.update_latest_nav', max_retries=3)
def update_latest_nav(self, fund_codes: Optional[List[str]] = None, batch_size: int = 100):
    """
    更新最新净值
    
    Args:
        fund_codes: 基金代码列表，None表示所有基金
        batch_size: 批量处理大小
    """
    try:
        logger.info(f"开始更新最新净值，基金数量: {len(fund_codes) if fund_codes else '全部'}")
        
        from data_retrieval.fetchers.optimized_fund_data import OptimizedFundData
        fetcher = OptimizedFundData()
        
        if fund_codes is None:
            fund_codes = _get_all_fund_codes()
        
        results = {}
        for i in range(0, len(fund_codes), batch_size):
            batch = fund_codes[i:i + batch_size]
            batch_results = fetcher.batch_get_latest_nav(batch)
            results.update(batch_results)
            time.sleep(1)
        
        logger.info(f"最新净值更新完成，共处理 {len(results)} 只基金")
        return {
            'status': 'success',
            'count': len(results),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"更新最新净值失败: {e}")
        self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, name='fund.update_nav_history', max_retries=3)
def update_nav_history(self, fund_codes: Optional[List[str]] = None, days: int = 30):
    """
    更新历史净值
    
    Args:
        fund_codes: 基金代码列表
        days: 获取最近多少天的数据
    """
    try:
        logger.info(f"开始更新历史净值，天数: {days}")
        
        from data_retrieval.fetchers.optimized_fund_data import OptimizedFundData
        fetcher = OptimizedFundData()
        
        if fund_codes is None:
            fund_codes = _get_all_fund_codes()
        
        results = {}
        for i in range(0, len(fund_codes), 50):
            batch = fund_codes[i:i + 50]
            batch_results = fetcher.batch_get_fund_nav(batch, days=days)
            results.update(batch_results)
            time.sleep(1)
        
        logger.info(f"历史净值更新完成，共处理 {len(results)} 只基金")
        return {
            'status': 'success',
            'count': len(results),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"更新历史净值失败: {e}")
        self.retry(exc=e, countdown=300)


@celery_app.task(bind=True, name='fund.recalculate_performance', max_retries=3)
def recalculate_performance(self, fund_codes: Optional[List[str]] = None):
    """
    重新计算绩效指标
    
    Args:
        fund_codes: 基金代码列表
    """
    try:
        logger.info("开始重新计算绩效指标")
        
        if fund_codes is None:
            fund_codes = _get_all_fund_codes()
        
        from services.fund_analyzer import FundAnalyzer
        analyzer = FundAnalyzer()
        
        success_count = 0
        for code in fund_codes[:100]:
            try:
                analyzer.analyze_fund(code)
                success_count += 1
            except Exception as e:
                logger.warning(f"计算 {code} 绩效指标失败: {e}")
        
        logger.info(f"绩效指标重算完成，成功 {success_count} 只")
        return {
            'status': 'success',
            'count': success_count,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"重算绩效指标失败: {e}")
        self.retry(exc=e, countdown=300)


@celery_app.task(bind=True, name='fund.run_backtest', max_retries=3)
def run_backtest(self, strategy_config: Dict[str, Any], fund_codes: List[str], 
                start_date: str, end_date: str, initial_capital: float = 10000.0):
    """
    运行策略回测
    
    Args:
        strategy_config: 策略配置
        fund_codes: 基金代码列表
        start_date: 开始日期
        end_date: 结束日期
        initial_capital: 初始资金
    """
    try:
        logger.info(f"开始运行策略回测: {strategy_config.get('name', 'unknown')}")
        
        from backtesting.core.unified_strategy_engine import UnifiedStrategyEngine
        from backtesting.analysis.strategy_evaluator import StrategyEvaluator
        
        engine = UnifiedStrategyEngine()
        evaluator = StrategyEvaluator()
        
        results = {
            'strategy_name': strategy_config.get('name', 'unknown'),
            'fund_codes': fund_codes,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': initial_capital,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"策略回测完成")
        return {
            'status': 'success',
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"运行策略回测失败: {e}")
        self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, name='fund.sync_fund_data', max_retries=3)
def sync_fund_data(self, sync_type: str = 'all'):
    """
    同步基金数据
    
    Args:
        sync_type: 同步类型 ('all', 'basic', 'nav', 'performance')
    """
    try:
        logger.info(f"开始同步基金数据，类型: {sync_type}")
        
        if sync_type in ['all', 'basic']:
            update_latest_nav.delay()
        
        if sync_type in ['all', 'nav']:
            update_nav_history.delay()
        
        if sync_type in ['all', 'performance']:
            recalculate_performance.delay()
        
        return {
            'status': 'success',
            'sync_type': sync_type,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"同步基金数据失败: {e}")
        self.retry(exc=e, countdown=300)


def _get_all_fund_codes() -> List[str]:
    """获取所有基金代码"""
    try:
        import akshare as ak
        fund_df = ak.fund_open_fund_daily_em()
        if not fund_df.empty and '基金代码' in fund_df.columns:
            codes = fund_df['基金代码'].unique().tolist()
            valid_codes = [c for c in codes if isinstance(c, str) and len(c) == 6 and c.isdigit()]
            return valid_codes
    except Exception as e:
        logger.warning(f"获取基金列表失败: {e}")
    return []

