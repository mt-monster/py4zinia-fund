#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Web 层装饰器
提供统一的路由响应格式和错误处理
"""

import time
import functools
from typing import Callable, Any, Tuple
from flask import jsonify, request
from datetime import datetime
import logging

from shared.exceptions import handle_exception, create_error_response
from shared.json_utils import SafeJSONEncoder

logger = logging.getLogger(__name__)


def api_response(handler: Callable) -> Callable:
    """
    API 响应统一格式装饰器
    
    自动处理异常，统一响应格式为：
    {
        "success": true/false,
        "data": {...},           // 成功时
        "error": {...},          // 失败时
        "timestamp": "..."
    }
    
    Usage:
        @app.route('/api/fund/<code>')
        @api_response
        def get_fund(code):
            return fund_data  # 直接返回数据即可
    """
    @functools.wraps(handler)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            # 执行处理器
            result = handler(*args, **kwargs)
            
            # 如果已经是 Response 对象，直接返回
            if hasattr(result, 'status_code'):
                return result
            
            # 构造统一成功响应
            response = {
                'success': True,
                'data': result,
                'timestamp': datetime.now().isoformat()
            }
            
            # 记录性能
            elapsed = time.time() - start_time
            if elapsed > 1.0:  # 慢查询警告
                logger.warning(f"慢查询: {request.path} 耗时 {elapsed:.2f}s")
            
            return jsonify(response)
            
        except Exception as e:
            # 记录错误
            elapsed = time.time() - start_time
            logger.error(
                f"API错误: {request.path} 耗时 {elapsed:.2f}s, 错误: {str(e)}",
                exc_info=True
            )
            
            # 转换为标准异常
            standardized_error = handle_exception(e)
            
            # 构造错误响应
            response = {
                'success': False,
                'error': {
                    'code': standardized_error.error_code.value,
                    'name': standardized_error.error_code.name,
                    'message': standardized_error.message,
                    'details': standardized_error.details
                },
                'timestamp': datetime.now().isoformat()
            }
            
            return jsonify(response), standardized_error.http_status
    
    return wrapper


def log_request(handler: Callable) -> Callable:
    """
    请求日志装饰器
    
    记录请求信息和性能
    
    Usage:
        @app.route('/api/fund/<code>')
        @log_request
        def get_fund(code):
            ...
    """
    @functools.wraps(handler)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        logger.info(
            f"请求开始: {request.method} {request.path} "
            f"参数: {dict(request.args)}"
        )
        
        try:
            result = handler(*args, **kwargs)
            
            elapsed = time.time() - start_time
            logger.info(f"请求完成: {request.path} 耗时 {elapsed:.3f}s")
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"请求失败: {request.path} 耗时 {elapsed:.3f}s, 错误: {e}")
            raise
    
    return wrapper


def require_auth(handler: Callable) -> Callable:
    """
    认证要求装饰器（预留）
    
    后续可以添加 JWT 或其他认证机制
    
    Usage:
        @app.route('/api/admin/config')
        @require_auth
        def update_config():
            ...
    """
    @functools.wraps(handler)
    def wrapper(*args, **kwargs):
        # TODO: 实现认证逻辑
        # token = request.headers.get('Authorization')
        # if not token:
        #     return jsonify({'success': False, 'error': '未授权'}), 401
        
        return handler(*args, **kwargs)
    
    return wrapper


def cache_response(timeout: int = 300):
    """
    响应缓存装饰器（基于内存，简单实现）
    
    Args:
        timeout: 缓存时间（秒），默认5分钟
        
    Usage:
        @app.route('/api/fund/list')
        @cache_response(timeout=600)
        def get_fund_list():
            ...
    """
    cache = {}
    
    def decorator(handler: Callable) -> Callable:
        @functools.wraps(handler)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{request.path}:{hash(str(request.args))}"
            
            # 检查缓存
            now = time.time()
            if cache_key in cache:
                cached_result, expire_time = cache[cache_key]
                if now < expire_time:
                    logger.debug(f"缓存命中: {cache_key}")
                    return cached_result
            
            # 执行并缓存
            result = handler(*args, **kwargs)
            cache[cache_key] = (result, now + timeout)
            
            # 清理过期缓存（简单策略：每100次请求清理一次）
            if len(cache) > 1000:
                expired_keys = [
                    k for k, (_, exp) in cache.items() 
                    if now > exp
                ]
                for k in expired_keys:
                    del cache[k]
            
            return result
        
        return wrapper
    
    return decorator


def validate_params(**validators):
    """
    参数验证装饰器
    
    Args:
        **validators: 参数名和验证函数的映射
        
    Usage:
        @app.route('/api/fund/<code>')
        @validate_params(
            days=lambda x: 1 <= int(x) <= 365,
            code=lambda x: len(x) == 6
        )
        def get_fund(code):
            days = request.args.get('days', 30)
            ...
    """
    def decorator(handler: Callable) -> Callable:
        @functools.wraps(handler)
        def wrapper(*args, **kwargs):
            errors = []
            
            for param_name, validator in validators.items():
                value = request.args.get(param_name)
                
                if value is not None:
                    try:
                        if not validator(value):
                            errors.append(f"参数 {param_name} 验证失败")
                    except Exception as e:
                        errors.append(f"参数 {param_name} 格式错误: {e}")
            
            if errors:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 400,
                        'message': '参数验证失败',
                        'details': errors
                    }
                }), 400
            
            return handler(*args, **kwargs)
        
        return wrapper
    
    return decorator


# 组合装饰器（常用组合）
def api_endpoint(**kwargs):
    """
    API端点装饰器（组合了 api_response 和 log_request）
    
    Usage:
        @app.route('/api/fund/<code>')
        @api_endpoint
        def get_fund(code):
            ...
    """
    def decorator(handler: Callable) -> Callable:
        # 从内到外包装：api_response(log_request(handler))
        handler = log_request(handler)
        handler = api_response(handler)
        
        # 添加缓存（如果指定）
        cache_timeout = kwargs.get('cache')
        if cache_timeout:
            handler = cache_response(timeout=cache_timeout)(handler)
        
        return handler
    
    return decorator
