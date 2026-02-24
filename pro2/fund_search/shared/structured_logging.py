#!/usr/bin/env python
# coding: utf-8

"""
结构化日志配置模块
使用structlog提供结构化日志输出
"""

import logging
import sys
from typing import Any, Dict
from datetime import datetime

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


def add_timestamp(
    logger: logging.Logger,
    method_name: str,
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """添加时间戳"""
    event_dict['timestamp'] = datetime.now().isoformat()
    return event_dict


def add_log_level(
    logger: logging.Logger,
    method_name: str,
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """添加日志级别"""
    event_dict['level'] = method_name.upper()
    return event_dict


def add_caller_info(
    logger: logging.Logger,
    method_name: str,
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """添加调用者信息"""
    import inspect
    frame = inspect.currentframe()
    
    while frame:
        if frame.f_code.co_filename not in [__file__, '<string>']:
            event_dict['caller'] = {
                'file': frame.f_code.co_filename.split('/')[-1],
                'function': frame.f_code.co_name,
                'line': frame.f_lineno
            }
            break
        frame = frame.f_back
    
    return event_dict


def configure_logging(
    log_level: str = "INFO",
    json_format: bool = False,
    include_caller: bool = False
):
    """
    配置结构化日志
    
    Args:
        log_level: 日志级别
        json_format: 是否使用JSON格式输出
        include_caller: 是否包含调用者信息
    """
    if not STRUCTLOG_AVAILABLE:
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging
    
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        add_timestamp,
    ]
    
    if include_caller:
        processors.append(add_caller_info)
    
    processors.extend([
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ])
    
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level),
    )


def get_logger(name: str = None) -> Any:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器实例
    """
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    return logging.getLogger(name)


class RequestContext:
    """请求上下文管理器"""
    
    def __init__(self):
        self._context: Dict[str, Any] = {}
    
    def set(self, key: str, value: Any):
        """设置上下文值"""
        self._context[key] = value
        if STRUCTLOG_AVAILABLE:
            structlog.contextvars.bind_contextvars(**{key: value})
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文值"""
        return self._context.get(key, default)
    
    def clear(self):
        """清除上下文"""
        self._context.clear()
        if STRUCTLOG_AVAILABLE:
            structlog.contextvars.unbind_contextvars(*list(self._context.keys()))
    
    def bind(self, **kwargs):
        """绑定多个上下文值"""
        self._context.update(kwargs)
        if STRUCTLOG_AVAILABLE:
            structlog.contextvars.bind_contextvars(**kwargs)


request_context = RequestContext()


class PerformanceLogger:
    """性能日志记录器"""
    
    def __init__(self, logger_name: str = "performance"):
        self.logger = get_logger(logger_name)
    
    def log_operation(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        **extra
    ):
        """记录操作性能"""
        self.logger.info(
            "operation_completed",
            operation=operation,
            duration_ms=round(duration_ms, 2),
            success=success,
            **extra
        )
    
    def log_database_query(
        self,
        query_type: str,
        table: str,
        duration_ms: float,
        rows_affected: int = 0
    ):
        """记录数据库查询性能"""
        self.logger.info(
            "database_query",
            query_type=query_type,
            table=table,
            duration_ms=round(duration_ms, 2),
            rows_affected=rows_affected
        )
    
    def log_cache_operation(
        self,
        operation: str,
        key: str,
        hit: bool = None,
        duration_ms: float = None
    ):
        """记录缓存操作"""
        data = {
            "cache_operation": operation,
            "cache_key": key
        }
        if hit is not None:
            data["cache_hit"] = hit
        if duration_ms is not None:
            data["duration_ms"] = round(duration_ms, 2)
        
        self.logger.info("cache_operation", **data)
    
    def log_api_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        user_id: str = None
    ):
        """记录API请求"""
        self.logger.info(
            "api_request",
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            user_id=user_id
        )


performance_logger = PerformanceLogger()


def init_logging(app=None, log_level: str = "INFO", json_format: bool = False):
    """
    初始化日志系统
    
    Args:
        app: Flask应用实例（可选）
        log_level: 日志级别
        json_format: 是否使用JSON格式
    """
    configure_logging(log_level=log_level, json_format=json_format)
    
    logger = get_logger(__name__)
    logger.info("logging_initialized", log_level=log_level, json_format=json_format)
    
    if app:
        @app.before_request
        def before_request():
            from flask import request, g
            import time
            g.start_time = time.time()
            request_context.bind(
                request_id=request.headers.get('X-Request-ID', 'unknown'),
                endpoint=request.endpoint,
                method=request.method
            )
        
        @app.after_request
        def after_request(response):
            from flask import request, g
            import time
            
            duration = (time.time() - g.get('start_time', time.time())) * 1000
            
            performance_logger.log_api_request(
                endpoint=request.endpoint,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration
            )
            
            request_context.clear()
            return response
    
    return logger
