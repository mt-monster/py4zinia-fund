#!/usr/bin/env python
# coding: utf-8
"""
统一异常处理框架
提供标准化的异常类层次结构和错误处理机制
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass


logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """标准错误码枚举"""
    # 通用错误 (1000-1999)
    SUCCESS = 0
    UNKNOWN_ERROR = 1000
    INVALID_PARAMETER = 1001
    MISSING_REQUIRED_FIELD = 1002
    DATA_VALIDATION_FAILED = 1003
    
    # 数据库错误 (2000-2999)
    DATABASE_CONNECTION_FAILED = 2000
    DATABASE_QUERY_ERROR = 2001
    DATABASE_RECORD_NOT_FOUND = 2002
    DATABASE_DUPLICATE_KEY = 2003
    
    # 业务逻辑错误 (3000-3999)
    FUND_NOT_FOUND = 3000
    STRATEGY_EXECUTION_FAILED = 3001
    INSUFFICIENT_FUNDS = 3002
    RISK_LIMIT_EXCEEDED = 3003
    
    # 外部服务错误 (4000-4999)
    API_CALL_FAILED = 4000
    NETWORK_TIMEOUT = 4001
    EXTERNAL_SERVICE_UNAVAILABLE = 4002
    AUTHENTICATION_FAILED = 4003
    
    # 权限错误 (5000-5999)
    PERMISSION_DENIED = 5000
    ACCESS_TOKEN_EXPIRED = 5001
    USER_NOT_AUTHENTICATED = 5002


@dataclass
class ErrorInfo:
    """错误信息数据类"""
    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    http_status: int = 500


class BaseApplicationError(Exception):
    """应用程序基础异常类"""
    
    def __init__(
        self, 
        message: str, 
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        http_status: int = 500,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.http_status = http_status
        self.cause = cause
        
        # 记录错误日志
        self._log_error()
    
    def _log_error(self):
        """记录错误日志"""
        log_data = {
            'error_code': self.error_code.name,
            'error_msg': self.message,
            'details': self.details,
            'http_status': self.http_status
        }
        
        if self.cause:
            log_data['cause'] = str(self.cause)
            logger.error(f"Application Error: {self.message}", extra=log_data, exc_info=self.cause)
        else:
            logger.error(f"Application Error: {self.message}", extra=log_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'success': False,
            'error_code': self.error_code.value,
            'error_name': self.error_code.name,
            'message': self.message,
            'details': self.details,
            'http_status': self.http_status
        }


class ValidationError(BaseApplicationError):
    """数据验证异常"""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        details = {}
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = value
            
        super().__init__(
            message=message,
            error_code=ErrorCode.DATA_VALIDATION_FAILED,
            details=details,
            http_status=400
        )


class DatabaseError(BaseApplicationError):
    """数据库相关异常"""
    
    def __init__(
        self, 
        message: str, 
        query: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.DATABASE_QUERY_ERROR
    ):
        details = {}
        if query:
            details['query'] = query
            
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            http_status=500
        )


class BusinessLogicError(BaseApplicationError):
    """业务逻辑异常"""
    
    def __init__(self, message: str, business_code: ErrorCode):
        super().__init__(
            message=message,
            error_code=business_code,
            http_status=400 if business_code.value < 4000 else 500
        )


class ExternalServiceError(BaseApplicationError):
    """外部服务异常"""
    
    def __init__(
        self, 
        message: str, 
        service_name: str,
        endpoint: Optional[str] = None,
        response_status: Optional[int] = None
    ):
        details = {'service': service_name}
        if endpoint:
            details['endpoint'] = endpoint
        if response_status:
            details['response_status'] = response_status
            
        super().__init__(
            message=message,
            error_code=ErrorCode.API_CALL_FAILED,
            details=details,
            http_status=502
        )


class AuthorizationError(BaseApplicationError):
    """授权异常"""
    
    def __init__(self, message: str, permission_required: Optional[str] = None):
        details = {}
        if permission_required:
            details['permission_required'] = permission_required
            
        super().__init__(
            message=message,
            error_code=ErrorCode.PERMISSION_DENIED,
            details=details,
            http_status=403
        )


def handle_exception(exc: Exception) -> BaseApplicationError:
    """
    统一异常处理器
    将各种异常转换为标准化的应用异常
    
    Args:
        exc: 原始异常
        
    Returns:
        BaseApplicationError: 标准化异常
    """
    # 如果已经是标准异常，直接返回
    if isinstance(exc, BaseApplicationError):
        return exc
    
    # 数据库异常处理
    if 'database' in str(type(exc)).lower() or 'mysql' in str(type(exc)).lower():
        return DatabaseError(
            message=f"数据库操作失败: {str(exc)}",
            error_code=ErrorCode.DATABASE_CONNECTION_FAILED
        )
    
    # 参数验证异常
    if 'validation' in str(type(exc)).lower() or 'invalid' in str(exc).lower():
        return ValidationError(message=str(exc))
    
    # 网络相关异常
    if 'timeout' in str(exc).lower() or 'connection' in str(exc).lower():
        return ExternalServiceError(
            message=f"网络连接失败: {str(exc)}",
            service_name="unknown"
        )
    
    # 默认处理
    return BaseApplicationError(
        message=f"未知错误: {str(exc)}",
        cause=exc
    )


def create_error_response(error: BaseApplicationError) -> Dict[str, Any]:
    """
    创建标准错误响应
    
    Args:
        error: 应用异常对象
        
    Returns:
        Dict: 标准错误响应格式
    """
    return {
        'success': False,
        'error': {
            'code': error.error_code.value,
            'name': error.error_code.name,
            'message': error.message,
            'details': error.details,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
    }


def with_error_handling(func):
    """
    异常处理装饰器
    自动捕获和处理函数中的异常
    
    Usage:
        @with_error_handling
        def my_function():
            # 业务逻辑
            pass
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            standardized_error = handle_exception(e)
            # 根据运行环境决定如何处理
            if __import__('os').environ.get('FLASK_ENV') == 'development':
                # 开发环境直接抛出异常以便调试
                raise standardized_error
            else:
                # 生产环境返回错误响应
                return create_error_response(standardized_error), standardized_error.http_status
    
    return wrapper