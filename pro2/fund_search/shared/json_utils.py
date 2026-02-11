#!/usr/bin/env python
# coding: utf-8
"""
JSON工具模块
提供安全的JSON序列化功能，处理NaN、Infinity等特殊值
"""

import json
import numpy as np
import pandas as pd
from flask import jsonify, Response
from typing import Any, Dict, List, Union
import logging


logger = logging.getLogger(__name__)


def _is_nan_or_inf(val) -> bool:
    """检查值是否为NaN或Infinity"""
    try:
        # 使用numpy的isnan和isinf，它们可以处理更多类型
        if np.isnan(val) or np.isinf(val):
            return True
    except (TypeError, ValueError):
        # np.isnan对非数值类型会抛出TypeError
        pass
    
    try:
        # 对Python float进行检查
        if isinstance(val, float):
            # NaN的特点是 NaN != NaN
            if val != val or val == float('inf') or val == float('-inf'):
                return True
    except:
        pass
    
    try:
        # 使用pandas的isna作为兜底
        if pd.isna(val):
            return True
    except:
        pass
    
    return False


def safe_json_serialize(obj: Any, _seen: set = None) -> Any:
    """
    安全的JSON序列化函数
    处理NaN、Infinity、-Infinity等特殊值，以及循环引用
    
    Args:
        obj: 要序列化的对象
        _seen: 内部使用的已见对象集合（用于检测循环引用）
        
    Returns:
        处理后的可JSON序列化对象
    """
    if _seen is None:
        _seen = set()
    
    # 检测循环引用
    obj_id = id(obj)
    if obj_id in _seen:
        return "[Circular Reference]"
    
    # 对复杂对象类型添加到已见集合
    if isinstance(obj, (dict, list, tuple)):
        _seen.add(obj_id)
    
    try:
        if isinstance(obj, dict):
            return {key: safe_json_serialize(value, _seen) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [safe_json_serialize(item, _seen) for item in obj]
        elif isinstance(obj, tuple):
            return [safe_json_serialize(item, _seen) for item in obj]
        elif isinstance(obj, np.ndarray):
            # 处理numpy数组
            return safe_json_serialize(obj.tolist(), _seen)
        elif isinstance(obj, np.integer):
            # 处理所有numpy整数类型（包括int64, int32等）
            return int(obj)
        elif isinstance(obj, np.floating):
            # 处理所有numpy浮点数类型（包括float64, float32等）
            if _is_nan_or_inf(obj):
                return None
            return float(obj)
        elif isinstance(obj, (int, float)):
            # 处理Python数值类型
            if _is_nan_or_inf(obj):
                return None
            return obj
        elif isinstance(obj, pd.Timestamp):
            # 处理pandas时间戳
            return obj.isoformat()
        elif isinstance(obj, pd.Series):
            # 处理pandas Series
            return safe_json_serialize(obj.to_list(), _seen)
        elif isinstance(obj, pd.DataFrame):
            # 处理pandas DataFrame
            return safe_json_serialize(obj.to_dict(orient='records'), _seen)
        elif obj is None:
            return None
        elif hasattr(obj, '__dict__'):
            # 处理自定义对象，转换为字典
            return safe_json_serialize(obj.__dict__, _seen)
        else:
            # 对其他类型，尝试检查是否为NaN
            if _is_nan_or_inf(obj):
                return None
            # 尝试转换为字符串
            try:
                return str(obj)
            except:
                return "[Unserializable Object]"
    finally:
        # 清理已见集合（可选，用于减少内存占用）
        pass


def _json_default(obj):
    """处理json.dumps的default参数"""
    # 处理numpy整数类型（包括int64, int32等）
    if isinstance(obj, np.integer):
        return int(obj)
    # 处理numpy浮点数类型
    elif isinstance(obj, np.floating):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, pd.Series):
        return obj.to_list()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient='records')
    # 其他类型转字符串
    return str(obj)


def safe_jsonify(data: Dict[str, Any], **kwargs):
    """
    安全的Flask jsonify替代函数
    
    Args:
        data: 要JSON化的数据
        **kwargs: jsonify的额外参数
        
    Returns:
        Flask Response对象
    """
    try:
        # 先处理特殊值和循环引用
        safe_data = safe_json_serialize(data)
        # 使用Python标准json.dumps，使用default处理剩余类型
        json_str = json.dumps(safe_data, ensure_ascii=False, allow_nan=False, default=_json_default)
        # 创建Flask Response
        return Response(json_str, mimetype='application/json', **kwargs)
    except Exception as e:
        logger.error(f"JSON序列化失败: {e}")
        # 返回错误信息
        error_response = json.dumps({
            'success': False,
            'error': '数据序列化失败',
            'message': str(e)
        }, ensure_ascii=False)
        return Response(error_response, mimetype='application/json', status=500)


def create_safe_response(success: bool, data: Any = None, error: str = None, **kwargs) -> Dict[str, Any]:
    """
    创建安全的API响应
    
    Args:
        success: 是否成功
        data: 响应数据
        error: 错误信息
        **kwargs: 其他响应字段
        
    Returns:
        安全的响应字典
    """
    response = {
        'success': success,
        'timestamp': __import__('datetime').datetime.now().isoformat()
    }
    
    if data is not None:
        response['data'] = safe_json_serialize(data)
    
    if error:
        response['error'] = error
    
    # 添加其他字段
    for key, value in kwargs.items():
        response[key] = safe_json_serialize(value)
    
    return response


class SafeJSONEncoder(json.JSONEncoder):
    """安全的JSON编码器"""
    
    def default(self, obj):
        try:
            return safe_json_serialize(obj)
        except Exception:
            return str(obj)


# 为方便使用，提供全局函数
def to_safe_json(obj: Any) -> str:
    """将对象转换为安全的JSON字符串"""
    return json.dumps(safe_json_serialize(obj), cls=SafeJSONEncoder, ensure_ascii=False)


def from_safe_json(json_str: str) -> Any:
    """从安全的JSON字符串解析对象"""
    return json.loads(json_str)