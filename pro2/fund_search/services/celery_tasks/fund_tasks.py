#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
services/celery_tasks/fund_tasks.py — 兼容转发层

任务实现已迁移到 celery_tasks/tasks.py。
此文件保留以防旧代码 import 报错。
"""

from celery_tasks.tasks import (
    update_fund_nav_task as update_latest_nav,
    update_nav_history_task as update_nav_history,
    recalc_performance_task as recalculate_performance,
    run_backtest_task as run_backtest,
    sync_fund_data_task as sync_fund_data,
    _get_all_fund_codes,
)

__all__ = [
    'update_latest_nav',
    'update_nav_history',
    'recalculate_performance',
    'run_backtest',
    'sync_fund_data',
]
