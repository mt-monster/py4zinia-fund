#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery异步任务模块

本模块实现了基于Celery的异步任务处理系统，用于处理耗时的后台任务。
主要功能包括：
- 基金数据更新任务
- 回测计算任务
- 数据同步任务
- 缓存清理任务

使用方法:
    from celery_tasks import init_celery, get_celery_app
    
    # 初始化Celery应用
    celery = init_celery(app)
    
    # 在其他地方使用任务
    from celery_tasks.tasks import update_fund_data_task
    update_fund_data_task.delay(fund_code='000001')

配置要求:
    - Redis作为消息代理和结果后端
    - celery>=5.3.0
    - redis>=5.0.0
"""

from .celery_app import init_celery, get_celery_app, celery_app

# 延迟导入任务，避免在Celery未初始化时出错
def __getattr__(name):
    if name in ('update_fund_data_task', 'run_backtest_task', 'sync_fund_data_task',
                'clear_expired_cache_task', 'update_fund_nav_task', 
                'recalc_performance_task', 'batch_update_task'):
        from . import tasks
        return getattr(tasks, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    'init_celery',
    'get_celery_app',
    'celery_app',
    'update_fund_data_task',
    'run_backtest_task',
    'sync_fund_data_task',
    'clear_expired_cache_task',
    'update_fund_nav_task',
    'recalc_performance_task',
    'batch_update_task'
]
