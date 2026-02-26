#!/usr/bin/env python
# coding: utf-8

"""
Backtest Service Configuration
回测服务配置
"""

import os
from typing import Optional


class ServiceConfig:
    """服务配置类"""
    
    # 服务基本信息
    SERVICE_NAME = "backtest-service"
    SERVICE_VERSION = "1.0.0"
    SERVICE_PORT = int(os.environ.get('BACKTEST_SERVICE_PORT', 5001))
    SERVICE_HOST = os.environ.get('BACKTEST_SERVICE_HOST', '0.0.0.0')
    
    # 调试模式
    DEBUG = os.environ.get('BACKTEST_DEBUG', 'False').lower() == 'true'
    
    # 任务配置
    TASK_CLEANUP_INTERVAL = int(os.environ.get('TASK_CLEANUP_INTERVAL', '3600'))  # 清理间隔(秒)
    TASK_MAX_AGE_HOURS = int(os.environ.get('TASK_MAX_AGE_HOURS', '24'))  # 任务最大保留时间(小时)
    MAX_CONCURRENT_TASKS = int(os.environ.get('MAX_CONCURRENT_TASKS', '5'))  # 最大并发任务数
    
    # 回测配置
    DEFAULT_START_DATE = os.environ.get('DEFAULT_START_DATE', '2020-01-01')
    DEFAULT_BASE_AMOUNT = float(os.environ.get('DEFAULT_BASE_AMOUNT', '100.0'))
    DEFAULT_INITIAL_CAPITAL = float(os.environ.get('DEFAULT_INITIAL_CAPITAL', '100000.0'))
    
    # 数据配置
    DATA_CACHE_ENABLED = os.environ.get('DATA_CACHE_ENABLED', 'True').lower() == 'true'
    DATA_CACHE_TTL = int(os.environ.get('DATA_CACHE_TTL', '300'))  # 数据缓存时间(秒)
    
    # 数据库配置（可选，用于持久化回测结果）
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', '3306'))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'root')
    DB_NAME = os.environ.get('DB_NAME', 'fund_analysis')
    
    # Redis配置（可选，用于分布式任务队列）
    REDIS_ENABLED = os.environ.get('REDIS_ENABLED', 'False').lower() == 'true'
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
    REDIS_DB = int(os.environ.get('REDIS_DB', '0'))
    
    # 日志配置
    LOG_LEVEL = os.environ.get('BACKTEST_LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 服务发现配置
    SERVICE_REGISTRY_ENABLED = os.environ.get('SERVICE_REGISTRY_ENABLED', 'False').lower() == 'true'
    SERVICE_REGISTRY_URL = os.environ.get('SERVICE_REGISTRY_URL', 'http://localhost:8500')
    SERVICE_HEARTBEAT_INTERVAL = int(os.environ.get('SERVICE_HEARTBEAT_INTERVAL', '30'))
    
    # CORS配置
    CORS_ENABLED = os.environ.get('CORS_ENABLED', 'True').lower() == 'true'
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    @classmethod
    def get_database_url(cls) -> Optional[str]:
        """获取数据库连接URL"""
        if not cls.DB_HOST:
            return None
        return f"mysql+pymysql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
    
    @classmethod
    def get_redis_url(cls) -> Optional[str]:
        """获取Redis连接URL"""
        if not cls.REDIS_ENABLED:
            return None
        return f"redis://{cls.REDIS_HOST}:{cls.REDIS_PORT}/{cls.REDIS_DB}"
    
    @classmethod
    def to_dict(cls) -> dict:
        """转换为字典（用于健康检查等）"""
        return {
            'service_name': cls.SERVICE_NAME,
            'service_version': cls.SERVICE_VERSION,
            'service_port': cls.SERVICE_PORT,
            'service_host': cls.SERVICE_HOST,
            'debug': cls.DEBUG,
            'max_concurrent_tasks': cls.MAX_CONCURRENT_TASKS,
            'task_max_age_hours': cls.TASK_MAX_AGE_HOURS,
            'data_cache_enabled': cls.DATA_CACHE_ENABLED,
            'log_level': cls.LOG_LEVEL,
            'cors_enabled': cls.CORS_ENABLED,
        }


# 全局配置实例
config = ServiceConfig()
