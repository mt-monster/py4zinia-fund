#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
services/celery_tasks — 兼容转发层

所有任务已统一到顶层 celery_tasks/ 模块。
此模块保留是为了防止旧代码 import 报错。
"""

# 从主模块统一导入，保持向后兼容
from celery_tasks.tasks import (
    update_fund_data_task,
    update_nav_history_task,
    update_fund_nav_task,
    recalc_performance_task,
    sync_fund_data_task,
    run_backtest_task,
    batch_update_task,
    send_notification_task,
    clear_expired_cache_task,
    _get_all_fund_codes,
)

# 旧名称别名（services/celery_tasks 中曾使用的任务名）
update_latest_nav = update_fund_nav_task
update_nav_history = update_nav_history_task
recalculate_performance = recalc_performance_task
run_backtest = run_backtest_task
sync_fund_data = sync_fund_data_task

__all__ = [
    'update_fund_data_task',
    'update_nav_history_task',
    'update_fund_nav_task',
    'recalc_performance_task',
    'sync_fund_data_task',
    'run_backtest_task',
    'batch_update_task',
    'send_notification_task',
    'clear_expired_cache_task',
    # 旧别名
    'update_latest_nav',
    'update_nav_history',
    'recalculate_performance',
    'run_backtest',
    'sync_fund_data',
]
