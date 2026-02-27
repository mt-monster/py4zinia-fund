#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery任务定义

定义所有异步执行的Celery任务，用于处理耗时的后台操作。
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def update_fund_data_task(self, fund_code: str, data_type: str = 'basic') -> Dict[str, Any]:
    """
    更新单个基金数据任务
    
    Args:
        fund_code: 基金代码
        data_type: 数据类型 (basic/nav/performance/all)
        
    Returns:
        Dict: 任务执行结果
    """
    try:
        logger.info(f"开始更新基金 {fund_code} 的 {data_type} 数据")
        
        # 导入服务
        from services.fund_data_preloader import get_preloader
        
        preloader = get_preloader()
        result = {}
        
        if data_type in ('basic', 'all'):
            # 更新基础信息
            basic_info = preloader.get_fund_basic_info(fund_code)
            result['basic'] = basic_info is not None
            
        if data_type in ('nav', 'all'):
            # 更新净值数据
            nav_data = preloader.get_fund_nav(fund_code, days=30)
            result['nav'] = nav_data is not None and not nav_data.empty
            
        if data_type in ('performance', 'all'):
            # 更新绩效数据
            performance = preloader.get_fund_performance(fund_code)
            result['performance'] = performance is not None
        
        logger.info(f"基金 {fund_code} 数据更新完成: {result}")
        return {
            'success': True,
            'fund_code': fund_code,
            'data_type': data_type,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"更新基金 {fund_code} 数据失败: {exc}")
        # 重试任务
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30, time_limit=1800)
def run_backtest_task(self, strategy_id: str, user_id: str, 
                      start_date: str, end_date: str,
                      initial_capital: float = 100000.0,
                      rebalance_freq: str = 'monthly') -> Dict[str, Any]:
    """
    执行策略回测任务
    
    Args:
        strategy_id: 策略ID
        user_id: 用户ID
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        initial_capital: 初始资金
        rebalance_freq: 再平衡频率
        
    Returns:
        Dict: 回测结果
    """
    try:
        logger.info(f"开始执行回测任务: strategy_id={strategy_id}, user={user_id}")
        
        from backtesting.core.backtest_api import BacktestAPIHandler
        from data_access.enhanced_database import EnhancedDatabaseManager
        from shared.config_manager import config_manager
        
        # 初始化组件
        db_config = config_manager.get_database_config()
        db_manager = EnhancedDatabaseManager({
            'host': db_config.host,
            'user': db_config.user,
            'password': db_config.password,
            'database': db_config.database,
            'port': db_config.port,
            'charset': db_config.charset
        })
        
        handler = BacktestAPIHandler(db_manager=db_manager)
        
        # 执行任务
        success, result = handler.run_backtest(
            strategy_id=strategy_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            rebalance_freq=rebalance_freq
        )
        
        if success:
            logger.info(f"回测任务完成: task_id={result.get('task_id')}")
            return {
                'success': True,
                'task_id': result.get('task_id'),
                'strategy_id': strategy_id,
                'summary': result.get('summary'),
                'timestamp': datetime.now().isoformat()
            }
        else:
            error_msg = result.get('error', '未知错误')
            logger.error(f"回测任务失败: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as exc:
        logger.error(f"执行回测任务异常: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_fund_data_task(self, sync_type: str = 'incremental') -> Dict[str, Any]:
    """
    同步基金数据任务
    
    Args:
        sync_type: 同步类型 (incremental/full)
        
    Returns:
        Dict: 同步结果
    """
    try:
        logger.info(f"开始执行数据同步任务: type={sync_type}")
        
        from services.fund_data_sync_service import FundDataSyncService
        from services.fund_data_preloader import get_preloader
        from data_access.enhanced_database import EnhancedDatabaseManager
        from shared.config_manager import config_manager
        
        # 初始化组件
        db_config = config_manager.get_database_config()
        db_manager = EnhancedDatabaseManager({
            'host': db_config.host,
            'user': db_config.user,
            'password': db_config.password,
            'database': db_config.database,
            'port': db_config.port,
            'charset': db_config.charset
        })
        
        preloader = get_preloader()
        sync_service = FundDataSyncService(preloader.cache, db_manager)
        
        # 执行同步
        if sync_type == 'full':
            result = sync_service.full_sync()
        else:
            result = sync_service.incremental_sync()
        
        logger.info(f"数据同步任务完成: {result}")
        return {
            'success': True,
            'sync_type': sync_type,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"数据同步任务失败: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def clear_expired_cache_task(self) -> Dict[str, Any]:
    """
    清理过期缓存任务
    
    Returns:
        Dict: 清理结果
    """
    try:
        logger.info("开始清理过期缓存")
        
        from services.fund_data_preloader import get_preloader
        
        preloader = get_preloader()
        stats_before = preloader.get_cache_stats()
        
        # 清理过期缓存
        preloader.cache.cleanup_expired()
        
        stats_after = preloader.get_cache_stats()
        
        logger.info("过期缓存清理完成")
        return {
            'success': True,
            'stats_before': stats_before,
            'stats_after': stats_after,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"清理缓存任务失败: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300, time_limit=3600)
def update_nav_history_task(self, fund_codes: Optional[List[str]] = None,
                            days: int = 30) -> Dict[str, Any]:
    """
    批量更新基金历史净值任务（定时任务，每日收盘后执行）

    Args:
        fund_codes: 基金代码列表，None 表示全量
        days: 获取最近多少天的历史数据

    Returns:
        Dict: 更新结果
    """
    try:
        logger.info(f"开始更新历史净值，days={days}")

        from data_retrieval.fetchers.optimized_fund_data import OptimizedFundData
        from services.fund_data_preloader import get_preloader

        preloader = get_preloader()
        fetcher = OptimizedFundData()

        if fund_codes is None:
            fund_codes = _get_all_fund_codes()

        import time
        updated_count = 0
        failed_count = 0
        batch_size = 50

        for i in range(0, len(fund_codes), batch_size):
            batch = fund_codes[i:i + batch_size]
            try:
                results = fetcher.batch_get_fund_nav(batch, days=days)
                for code, df in results.items():
                    if df is not None and not df.empty:
                        key = f"fund:nav:{code}"
                        data = {
                            'records': df.to_dict('records'),
                            'columns': df.columns.tolist(),
                            'last_date': str(df.iloc[-1].get('date', '')) if len(df) > 0 else None
                        }
                        preloader.cache.set(key, data, 24 * 3600)
                        updated_count += 1
                    else:
                        failed_count += 1
            except Exception as e:
                logger.debug(f"批次更新历史净值失败 {batch[:3]}...: {e}")
                failed_count += len(batch)

            time.sleep(1)  # 避免 API 限频

        logger.info(f"历史净值更新完成: 成功 {updated_count}, 失败 {failed_count}")
        return {
            'success': True,
            'updated_count': updated_count,
            'failed_count': failed_count,
            'total': len(fund_codes),
            'days': days,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as exc:
        logger.error(f"历史净值更新任务失败: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, time_limit=900)
def update_fund_nav_task(self) -> Dict[str, Any]:
    """
    批量更新基金净值任务（定时任务）
    
    Returns:
        Dict: 更新结果
    """
    try:
        logger.info("开始批量更新基金净值")
        
        import akshare as ak
        from services.fund_data_preloader import get_preloader
        
        preloader = get_preloader()
        
        # 获取基金列表
        try:
            fund_df = ak.fund_open_fund_daily_em()
            codes = fund_df['基金代码'].unique().tolist()[:100]  # 限制数量
        except Exception:
            codes = []
        
        updated_count = 0
        failed_count = 0
        
        for code in codes:
            try:
                # 获取最新净值
                from data_retrieval.fetchers.optimized_fund_data import OptimizedFundData
                fetcher = OptimizedFundData()
                data = fetcher.get_latest_nav(code)
                
                if data:
                    key = f"fund:latest:{code}"
                    preloader.cache.set(key, data, 30 * 60)
                    updated_count += 1
            except Exception as e:
                logger.debug(f"更新 {code} 失败: {e}")
                failed_count += 1
        
        logger.info(f"基金净值更新完成: 成功 {updated_count}, 失败 {failed_count}")
        return {
            'success': True,
            'updated_count': updated_count,
            'failed_count': failed_count,
            'total': len(codes),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"批量更新净值任务失败: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60, time_limit=1800)
def recalc_performance_task(self) -> Dict[str, Any]:
    """
    重新计算绩效指标任务（定时任务）
    
    Returns:
        Dict: 计算结果
    """
    try:
        logger.info("开始重新计算绩效指标")
        
        import akshare as ak
        from services.fund_data_preloader import get_preloader
        
        preloader = get_preloader()
        
        # 获取基金列表
        try:
            fund_df = ak.fund_open_fund_daily_em()
            codes = fund_df['基金代码'].unique().tolist()[:100]
        except Exception:
            codes = []
        
        recalc_count = 0
        failed_count = 0
        
        for code in codes:
            try:
                # 获取历史数据
                hist_key = f"fund:nav:{code}"
                hist_data = preloader.cache.get(hist_key)
                
                if hist_data and 'records' in hist_data:
                    # 重新计算绩效指标
                    metrics = preloader._calculate_metrics(hist_data['records'])
                    perf_key = f"fund:perf:{code}"
                    preloader.cache.set(perf_key, metrics, 24 * 3600)
                    recalc_count += 1
            except Exception as e:
                logger.debug(f"计算 {code} 绩效指标失败: {e}")
                failed_count += 1
        
        logger.info(f"绩效指标重算完成: 成功 {recalc_count}, 失败 {failed_count}")
        return {
            'success': True,
            'recalc_count': recalc_count,
            'failed_count': failed_count,
            'total': len(codes),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"绩效指标重算任务失败: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def batch_update_task(self, fund_codes: List[str], data_type: str = 'basic') -> Dict[str, Any]:
    """
    批量更新多个基金数据的任务
    
    Args:
        fund_codes: 基金代码列表
        data_type: 数据类型
        
    Returns:
        Dict: 批量更新结果
    """
    try:
        logger.info(f"开始批量更新 {len(fund_codes)} 只基金的 {data_type} 数据")
        
        results = []
        success_count = 0
        failed_count = 0
        
        for code in fund_codes:
            try:
                # 调用单个更新任务
                result = update_fund_data_task.run(fund_code=code, data_type=data_type)
                results.append(result)
                if result.get('success'):
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"批量更新中处理 {code} 失败: {e}")
                failed_count += 1
        
        logger.info(f"批量更新完成: 成功 {success_count}, 失败 {failed_count}")
        return {
            'success': True,
            'total': len(fund_codes),
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"批量更新任务失败: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=1, default_retry_delay=10)
def send_notification_task(self, user_id: str, notification_type: str, 
                           title: str, message: str, **kwargs) -> Dict[str, Any]:
    """
    发送通知任务
    
    Args:
        user_id: 用户ID
        notification_type: 通知类型 (email/sms/push)
        title: 通知标题
        message: 通知内容
        
    Returns:
        Dict: 发送结果
    """
    try:
        logger.info(f"发送通知给用户 {user_id}: {title}")
        
        # 这里可以实现具体的通知逻辑
        # 例如：发送邮件、短信、推送等
        
        return {
            'success': True,
            'user_id': user_id,
            'notification_type': notification_type,
            'title': title,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"发送通知失败: {exc}")
        raise self.retry(exc=exc)


# ============ 辅助函数 ============

def _get_all_fund_codes() -> List[str]:
    """获取所有场外开放式基金代码（优先从 akshare 获取，失败返回空列表）"""
    try:
        import akshare as ak

        # 方法1：从每日行情获取
        try:
            fund_df = ak.fund_open_fund_daily_em()
            if not fund_df.empty and '基金代码' in fund_df.columns:
                codes = fund_df['基金代码'].unique().tolist()
                return [c for c in codes if isinstance(c, str) and len(c) == 6 and c.isdigit()]
        except Exception:
            pass

        # 方法2：从基金名称列表获取，过滤场内 ETF
        fund_list = ak.fund_name_em()
        codes = fund_list['基金代码'].unique().tolist()
        valid = [c for c in codes if isinstance(c, str) and len(c) == 6 and c.isdigit()]
        # 排除场内基金前缀
        return [c for c in valid if not c.startswith(('51', '15', '16', '50', '18'))]

    except Exception as e:
        logger.warning(f"获取基金代码列表失败: {e}")
        return []
