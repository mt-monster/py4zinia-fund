"""
共享配置模块

该模块包含系统的共享配置和常量：
- 基础配置
- 数据库配置
- 通知配置
- 图表配置
"""

from .enhanced_config import (
    BASE_CONFIG,
    DATABASE_CONFIG, 
    NOTIFICATION_CONFIG,
    CHART_CONFIG
)

__all__ = [
    'BASE_CONFIG',
    'DATABASE_CONFIG',
    'NOTIFICATION_CONFIG', 
    'CHART_CONFIG'
]