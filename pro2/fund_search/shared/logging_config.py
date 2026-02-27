#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一日志配置模块
确保日志只被配置一次，避免重复初始化
"""

import logging
import sys
from typing import Optional, List

# 全局标志，确保只配置一次
_configured = False
_default_logger = None


def configure_logging(
    level: int = logging.ERROR,
    log_file: Optional[str] = 'fund_analysis.log',
    format_string: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    enable_console: bool = True,
    enable_file: bool = True
) -> logging.Logger:
    """
    配置日志（线程安全，只允许执行一次）
    
    Args:
        level: 日志级别
        log_file: 日志文件路径，None表示不写入文件
        format_string: 日志格式
        enable_console: 是否输出到控制台
        enable_file: 是否写入文件（需要log_file不为None）
        
    Returns:
        根日志记录器
    """
    global _configured, _default_logger
    
    if _configured:
        return _default_logger or logging.getLogger()
    
    handlers: List[logging.Handler] = []
    
    # 控制台处理器
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(format_string))
        handlers.append(console_handler)
    
    # 文件处理器
    if enable_file and log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(format_string))
            handlers.append(file_handler)
        except Exception as e:
            print(f"警告: 无法创建日志文件 {log_file}: {e}")
    
    # 配置根日志记录器
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=handlers,
        force=False  # 不强制重置现有处理器
    )
    
    _configured = True
    _default_logger = logging.getLogger()
    _default_logger.info("日志系统初始化完成")
    
    return _default_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器
    
    如果日志尚未配置，会自动进行默认配置
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器实例
    """
    global _configured
    
    if not _configured:
        # 自动进行默认配置
        configure_logging()
    
    return logging.getLogger(name)


def is_configured() -> bool:
    """检查日志是否已配置"""
    return _configured


def reset_logging():
    """
    重置日志配置（主要用于测试）
    
    警告: 生产环境慎用
    """
    global _configured
    logging.getLogger().handlers.clear()
    _configured = False
