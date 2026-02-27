#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery 配置文件（内存模式）

不依赖 Redis，使用 memory:// broker + cache+memory:// 结果后端。
task_always_eager=True：任务在调用方进程内同步执行，无需单独启动 Worker。
"""

import os
import logging

logger = logging.getLogger(__name__)

# Celery 配置（内存模式）
CELERY_CONFIG = {
    # Broker / 结果后端（纯内存，无需外部服务）
    'broker_url': 'memory://',
    'result_backend': 'cache+memory://',

    # 同进程同步执行
    'task_always_eager': True,
    'task_eager_propagates': True,
    'task_store_eager_result': True,

    # 序列化
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',

    # 时区
    'timezone': 'Asia/Shanghai',
    'enable_utc': True,

    # Worker 行为
    'task_track_started': True,
    'worker_prefetch_multiplier': 1,
    'worker_max_tasks_per_child': 100,
    'worker_concurrency': int(os.environ.get('CELERY_WORKER_CONCURRENCY', '4')),

    # 任务路由（逻辑分组，内存模式下仅作标识）
    'task_routes': {
        'celery_tasks.tasks.update_fund_nav_task':     {'queue': 'data_sync'},
        'celery_tasks.tasks.update_nav_history_task':  {'queue': 'data_sync'},
        'celery_tasks.tasks.sync_fund_data_task':      {'queue': 'data_sync'},
        'celery_tasks.tasks.batch_update_task':        {'queue': 'data_sync'},
        'celery_tasks.tasks.run_backtest_task':        {'queue': 'backtest'},
        'celery_tasks.tasks.recalc_performance_task':  {'queue': 'calculation'},
        'celery_tasks.tasks.clear_expired_cache_task': {'queue': 'default'},
        'celery_tasks.tasks.send_notification_task':   {'queue': 'default'},
    },
    'task_default_queue': 'default',

    # Beat 调度存储（文件存储，不依赖 Redis）
    'beat_scheduler': 'celery.beat.PersistentScheduler',
    'beat_schedule_filename': os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'celerybeat-schedule.db'
    ),
}

# 任务默认配置
TASK_DEFAULTS = {
    'max_retries': 3,
    'default_retry_delay': 60,
    'soft_time_limit': 300,
    'time_limit': 600,
    'acks_late': False,       # 内存模式不支持 acks_late
    'reject_on_worker_lost': False,
}

# 队列定义（逻辑分组）
CELERY_QUEUES = {
    'default':     {'exchange': 'default',     'binding_key': 'default'},
    'data_sync':   {'exchange': 'data_sync',   'binding_key': 'data_sync'},
    'calculation': {'exchange': 'calculation', 'binding_key': 'calculation'},
    'backtest':    {'exchange': 'backtest',     'binding_key': 'backtest'},
    'report':      {'exchange': 'report',       'binding_key': 'report'},
}


def get_celery_config():
    """获取 Celery 配置"""
    return CELERY_CONFIG


def check_broker_connection() -> bool:
    """内存模式始终可用"""
    logger.info("Celery broker: memory://（内存模式，始终可用）")
    return True


# 保留旧名称兼容性
check_redis_connection = check_broker_connection


def print_config():
    """打印当前配置"""
    info = f"""
Celery Configuration (内存模式):
  Broker URL:        memory://
  Result Backend:    cache+memory://
  Task Always Eager: True（同进程同步执行）
  Timezone:          {CELERY_CONFIG['timezone']}
  Worker Concurrency:{CELERY_CONFIG['worker_concurrency']}

Queues: default / data_sync / calculation / backtest / report
    """
    print(info)
    return info


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print_config()
    print("Broker 可用:", check_broker_connection())
