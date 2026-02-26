#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery 配置文件

配置Celery使用Redis作为消息代理和结果后端。
支持环境变量配置，便于不同环境部署。

环境变量:
    CELERY_BROKER_URL: Redis broker URL (默认: redis://localhost:6379/0)
    CELERY_RESULT_BACKEND: 结果后端URL (默认: redis://localhost:6379/0)
    CELERY_TASK_ALWAYS_EAGER: 是否同步执行(调试模式) (默认: False)
    CELERY_WORKER_CONCURRENCY: Worker并发数 (默认: 4)
"""

import os
import logging

logger = logging.getLogger(__name__)

# Redis配置
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_DB = int(os.environ.get('REDIS_DB', 0))
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)

# Broker URL
if REDIS_PASSWORD:
    CELERY_BROKER_URL = os.environ.get(
        'CELERY_BROKER_URL',
        f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    )
else:
    CELERY_BROKER_URL = os.environ.get(
        'CELERY_BROKER_URL',
        f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    )

# 结果后端URL
if REDIS_PASSWORD:
    CELERY_RESULT_BACKEND = os.environ.get(
        'CELERY_RESULT_BACKEND',
        f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB + 1}"
    )
else:
    CELERY_RESULT_BACKEND = os.environ.get(
        'CELERY_RESULT_BACKEND',
        f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB + 1}"
    )

# Celery配置
CELERY_CONFIG = {
    # Broker配置
    'broker_url': CELERY_BROKER_URL,
    'broker_connection_retry_on_startup': True,
    'broker_connection_max_retries': 10,
    
    # 结果后端配置
    'result_backend': CELERY_RESULT_BACKEND,
    'result_expires': 3600 * 24,  # 结果保留24小时
    'result_extended': True,  # 存储更多任务信息
    
    # 序列化配置
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    
    # 时区配置
    'timezone': 'Asia/Shanghai',
    'enable_utc': True,
    
    # 任务执行配置
    'task_always_eager': os.environ.get('CELERY_TASK_ALWAYS_EAGER', 'False').lower() == 'true',
    'task_store_eager_result': True,
    'task_track_started': True,  # 跟踪任务开始状态
    
    # Worker配置
    'worker_concurrency': int(os.environ.get('CELERY_WORKER_CONCURRENCY', '4')),
    'worker_prefetch_multiplier': 1,  # 避免任务被预取
    'worker_max_tasks_per_child': 100,  # 每个worker进程处理100个任务后重启
    'worker_cancel_long_running_tasks_on_connection_loss': True,
    
    # 任务路由配置
    'task_routes': {
        'celery_tasks.fund_data_sync': {'queue': 'data_sync'},
        'celery_tasks.nav_update': {'queue': 'data_sync'},
        'celery_tasks.performance_calculation': {'queue': 'calculation'},
        'celery_tasks.backtest_execution': {'queue': 'backtest'},
        'celery_tasks.report_generation': {'queue': 'report'},
    },
    
    # 默认任务配置
    'task_default_queue': 'default',
    'task_default_exchange': 'default',
    'task_default_routing_key': 'default',
    
    # 任务重试配置
    'task_acks_late': True,  # 任务完成后再确认
    'task_reject_on_worker_lost': True,  # Worker丢失时重新投递
    
    # 日志配置
    'worker_redirect_stdouts_level': 'INFO',
    
    # 定时任务调度器(如使用beat)
    'beat_scheduler': 'celery.beat.PersistentScheduler',
    'beat_schedule_filename': os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'celerybeat-schedule.db'
    ),
}

# 任务默认配置
TASK_DEFAULTS = {
    'max_retries': 3,
    'default_retry_delay': 60,  # 1分钟后重试
    'soft_time_limit': 300,     # 5分钟软超时
    'time_limit': 600,          # 10分钟硬超时
    'acks_late': True,
    'reject_on_worker_lost': True,
}

# 队列定义
CELERY_QUEUES = {
    'default': {
        'exchange': 'default',
        'binding_key': 'default',
    },
    'data_sync': {
        'exchange': 'data_sync',
        'binding_key': 'data_sync',
    },
    'calculation': {
        'exchange': 'calculation',
        'binding_key': 'calculation',
    },
    'backtest': {
        'exchange': 'backtest',
        'binding_key': 'backtest',
    },
    'report': {
        'exchange': 'report',
        'binding_key': 'report',
    },
}


def get_celery_config():
    """获取Celery配置"""
    return CELERY_CONFIG


def check_redis_connection():
    """检查Redis连接是否正常"""
    try:
        import redis
        
        # 创建Redis连接
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            socket_connect_timeout=5
        )
        
        # 测试连接
        client.ping()
        logger.info(f"Redis连接成功: {REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
        return True
        
    except ImportError:
        logger.error("redis package not installed, run: pip install redis")
        return False
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return False


def print_config():
    """打印当前配置(隐藏密码)"""
    safe_broker_url = CELERY_BROKER_URL
    if REDIS_PASSWORD and REDIS_PASSWORD in safe_broker_url:
        safe_broker_url = safe_broker_url.replace(REDIS_PASSWORD, '***')
    
    safe_backend_url = CELERY_RESULT_BACKEND
    if REDIS_PASSWORD and REDIS_PASSWORD in safe_backend_url:
        safe_backend_url = safe_backend_url.replace(REDIS_PASSWORD, '***')
    
    config_info = f"""
Celery Configuration:
  Broker URL: {safe_broker_url}
  Result Backend: {safe_backend_url}
  Timezone: {CELERY_CONFIG['timezone']}
  Worker Concurrency: {CELERY_CONFIG['worker_concurrency']}
  Task Always Eager: {CELERY_CONFIG['task_always_eager']}
  
Queues:
  - default: Default queue
  - data_sync: Data synchronization queue
  - calculation: Calculation queue
  - backtest: Backtest queue
  - report: Report queue
    """
    print(config_info)
    return config_info


if __name__ == '__main__':
    # Test configuration
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Celery Configuration Test")
    print("=" * 60)
    
    print_config()
    
    print("\nChecking Redis connection...")
    if check_redis_connection():
        print("Redis connection: OK")
    else:
        print("Redis connection: FAILED")
    
    print("\nConfiguration test completed")
