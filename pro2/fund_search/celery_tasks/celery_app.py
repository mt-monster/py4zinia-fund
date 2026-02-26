#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery应用配置

配置Celery应用实例，使用Redis作为消息代理和结果存储。
"""

import os
import logging
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
from celery.schedules import crontab

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CELERY_CONFIG = {
    'broker_url': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    'result_backend': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'Asia/Shanghai',
    'enable_utc': True,
    'task_track_started': True,
    'task_time_limit': 3600,  # 1小时超时
    'task_soft_time_limit': 3000,  # 50分钟软超时
    'worker_prefetch_multiplier': 1,  # 每个worker一次只取一个任务
    'worker_max_tasks_per_child': 50,  # 每个worker子进程处理50个任务后重启
}

# 全局Celery应用实例
celery_app: Celery = None


def create_celery_app(flask_app=None) -> Celery:
    """
    创建并配置Celery应用
    
    Args:
        flask_app: Flask应用实例（可选）
        
    Returns:
        Celery: 配置好的Celery应用实例
    """
    global celery_app
    
    # 创建Celery应用
    celery = Celery('fund_platform')
    
    # 加载配置
    celery.conf.update(DEFAULT_CELERY_CONFIG)
    
    # 从环境变量加载额外配置
    if os.environ.get('CELERY_RESULT_BACKEND'):
        celery.conf.result_backend = os.environ.get('CELERY_RESULT_BACKEND')
    
    # 配置定时任务
    celery.conf.beat_schedule = {
        'update-latest-nav-every-30min': {
            'task': 'celery_tasks.tasks.update_fund_nav_task',
            'schedule': 30 * 60,  # 每30分钟
            'options': {'queue': 'default'}
        },
        'recalc-performance-daily': {
            'task': 'celery_tasks.tasks.recalc_performance_task',
            'schedule': crontab(hour=16, minute=0),  # 每天下午4点
            'options': {'queue': 'default'}
        },
        'clear-expired-cache-hourly': {
            'task': 'celery_tasks.tasks.clear_expired_cache_task',
            'schedule': crontab(minute=0),  # 每小时
            'options': {'queue': 'low_priority'}
        },
        'sync-fund-data-nightly': {
            'task': 'celery_tasks.tasks.sync_fund_data_task',
            'schedule': crontab(hour=2, minute=0),  # 每天凌晨2点
            'options': {'queue': 'default'}
        },
    }
    
    # 自动发现任务
    celery.autodiscover_tasks([
        'celery_tasks.tasks',
    ])
    
    # 如果提供了Flask应用，配置上下文
    if flask_app:
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with flask_app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
        logger.info("Celery已绑定到Flask应用")
    
    celery_app = celery
    logger.info("Celery应用初始化完成")
    return celery


def init_celery(flask_app) -> Celery:
    """
    初始化Celery并绑定到Flask应用
    
    Args:
        flask_app: Flask应用实例
        
    Returns:
        Celery: 配置好的Celery应用
    """
    celery = create_celery_app(flask_app)
    return celery


def get_celery_app() -> Celery:
    """
    获取全局Celery应用实例
    
    Returns:
        Celery: Celery应用实例
        
    Raises:
        RuntimeError: 如果Celery尚未初始化
    """
    if celery_app is None:
        raise RuntimeError("Celery应用尚未初始化，请先调用init_celery()")
    return celery_app


# ============ 任务信号处理 ============

@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **extras):
    """任务开始前的处理"""
    logger.info(f"任务开始: {task.name}[{task_id}]")


@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **extras):
    """任务完成后的处理"""
    logger.info(f"任务完成: {task.name}[{task_id}] 状态: {state}")


@task_failure.connect
def task_failure_handler(task_id, exception, args, kwargs, traceback, einfo, **extras):
    """任务失败时的处理"""
    logger.error(f"任务失败: {task_id} 异常: {exception}")
