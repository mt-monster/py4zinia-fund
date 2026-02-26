#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery 任务模块
包含所有异步后台任务
"""

from .fund_tasks import (
    update_latest_nav,
    update_nav_history,
    recalculate_performance,
    run_backtest,
    sync_fund_data
)

__all__ = [
    'update_latest_nav',
    'update_nav_history',
    'recalculate_performance',
    'run_backtest',
    'sync_fund_data'
]

