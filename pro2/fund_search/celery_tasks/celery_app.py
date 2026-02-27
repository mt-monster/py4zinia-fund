#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery应用配置

使用内存 broker（无需 Redis），支持：
- memory:// broker + cache+memory:// 结果后端
- task_always_eager 同进程同步执行（单机部署）
- 多队列逻辑分组（路由到同一内存 broker）
- Flask 应用上下文绑定
- Beat 定时任务调度
"""

import os
import sys
import logging
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
from celery.schedules import crontab

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# 全局 Celery 应用实例
celery_app: Celery = None

# 内存 broker 基础配置（不依赖任何外部服务）
_MEMORY_CONFIG = {
    'broker_url': 'memory://',
    'result_backend': 'cache+memory://',
    'task_always_eager': True,        # 同进程同步执行，无需单独 Worker 进程
    'task_eager_propagates': True,    # 同步模式下异常正常向上传播
    'task_store_eager_result': True,  # 保存同步结果，支持 AsyncResult 查询
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'Asia/Shanghai',
    'enable_utc': True,
    'task_track_started': True,
    'worker_prefetch_multiplier': 1,
    'worker_max_tasks_per_child': 100,
    # 任务路由（逻辑分组，内存模式下队列名仅作标识）
    'task_routes': {
        'celery_tasks.tasks.update_fund_nav_task':    {'queue': 'data_sync'},
        'celery_tasks.tasks.update_nav_history_task': {'queue': 'data_sync'},
        'celery_tasks.tasks.sync_fund_data_task':     {'queue': 'data_sync'},
        'celery_tasks.tasks.run_backtest_task':       {'queue': 'backtest'},
        'celery_tasks.tasks.recalc_performance_task': {'queue': 'calculation'},
        'celery_tasks.tasks.clear_expired_cache_task':{'queue': 'default'},
        'celery_tasks.tasks.send_notification_task':  {'queue': 'default'},
        'celery_tasks.tasks.batch_update_task':       {'queue': 'data_sync'},
    },
    'task_default_queue': 'default',
}


def create_celery_app(flask_app=None) -> Celery:
    """
    创建并配置 Celery 应用（内存模式，无需 Redis）

    Args:
        flask_app: Flask 应用实例（可选，绑定后任务可访问应用上下文）

    Returns:
        Celery: 配置好的 Celery 应用实例
    """
    global celery_app

    celery = Celery('fund_platform')
    celery.conf.update(_MEMORY_CONFIG)

    # Beat 定时任务调度
    # 注意：task_always_eager=True 时 beat 不实际触发（beat 需要 Worker），
    # 但配置保留，以便将来切换到真实 broker 时直接生效。
    celery.conf.beat_schedule = {
        'update-latest-nav-every-30min': {
            'task': 'celery_tasks.tasks.update_fund_nav_task',
            'schedule': 30 * 60,
            'options': {'queue': 'data_sync'}
        },
        'update-nav-history-daily': {
            'task': 'celery_tasks.tasks.update_nav_history_task',
            'schedule': crontab(hour=16, minute=30),
            'options': {'queue': 'data_sync'}
        },
        'recalc-performance-daily': {
            'task': 'celery_tasks.tasks.recalc_performance_task',
            'schedule': crontab(hour=17, minute=0),
            'options': {'queue': 'calculation'}
        },
        'clear-expired-cache-hourly': {
            'task': 'celery_tasks.tasks.clear_expired_cache_task',
            'schedule': crontab(minute=0),
            'options': {'queue': 'default'}
        },
        'sync-fund-data-nightly': {
            'task': 'celery_tasks.tasks.sync_fund_data_task',
            'schedule': crontab(hour=2, minute=0),
            'options': {'queue': 'data_sync'}
        },
    }

    # 自动发现任务
    celery.autodiscover_tasks(['celery_tasks.tasks'])

    # 绑定 Flask 应用上下文
    if flask_app:
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with flask_app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask
        logger.info("Celery 已绑定到 Flask 应用")

    celery_app = celery
    logger.info("Celery 初始化完成（内存模式，无需 Redis）")
    return celery


def init_celery(flask_app) -> Celery:
    """初始化 Celery 并绑定到 Flask 应用"""
    return create_celery_app(flask_app)


def get_celery_app() -> Celery:
    """获取全局 Celery 应用实例"""
    if celery_app is None:
        raise RuntimeError("Celery 尚未初始化，请先调用 init_celery()")
    return celery_app


# ============ 任务信号处理 ============

@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **extras):
    logger.info(f"任务开始: {task.name}[{task_id}]")


@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **extras):
    logger.info(f"任务完成: {task.name}[{task_id}] 状态: {state}")


@task_failure.connect
def task_failure_handler(task_id, exception, args, kwargs, traceback, einfo, **extras):
    logger.error(f"任务失败: {task_id} 异常: {exception}")
