# -*- coding: utf-8 -*-
"""
事件发布器
提供统一的事件发布接口，支持多种发布模式和选项
"""

import logging
import functools
from typing import Any, Dict, Optional, Callable, Union
from datetime import datetime

from .redis_broker import RedisBroker, MessagePriority, DeliveryMode, Message

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    事件发布器
    
    提供统一的事件发布接口：
    - 支持同步/异步发布
    - 支持优先级设置
    - 支持多种投递模式
    - 支持事件追踪
    """
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.broker = RedisBroker()
        self.logger = logging.getLogger(__name__)
        self._default_source = "fund_platform"
        self._initialized = True
        self.logger.info("事件发布器初始化完成")
    
    def publish(
        self,
        event_type: str,
        payload: Dict[str, Any],
        priority: Union[MessagePriority, str] = MessagePriority.NORMAL,
        delivery_mode: Union[DeliveryMode, str] = DeliveryMode.PUB_SUB,
        correlation_id: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发布事件
        
        Args:
            event_type: 事件类型
            payload: 事件负载数据
            priority: 消息优先级（MessagePriority枚举或字符串）
            delivery_mode: 投递模式（DeliveryMode枚举或字符串）
            correlation_id: 关联ID（用于事件追踪）
            source: 事件来源标识
            metadata: 额外元数据
            
        Returns:
            bool: 是否发布成功
            
        Example:
            >>> publisher = EventPublisher()
            >>> publisher.publish(
            ...     "FUND_DATA_UPDATED",
            ...     {"fund_code": "000001", "update_time": "2024-01-01"},
            ...     priority=MessagePriority.HIGH
            ... )
            True
        """
        # 标准化参数
        if isinstance(priority, str):
            priority = MessagePriority[priority.upper()]
        if isinstance(delivery_mode, str):
            delivery_mode = DeliveryMode(delivery_mode)
        
        # 构建完整负载
        full_payload = {
            'data': payload,
            'published_at': datetime.now().isoformat(),
            'version': '1.0'
        }
        
        if metadata:
            full_payload['metadata'] = metadata
        
        # 发布事件
        success = self.broker.publish(
            event_type=event_type,
            payload=full_payload,
            priority=priority,
            delivery_mode=delivery_mode,
            correlation_id=correlation_id,
            source=source or self._default_source
        )
        
        if success:
            self.logger.debug(
                f"事件发布成功: {event_type}, "
                f"correlation_id={correlation_id}, "
                f"priority={priority.name}"
            )
        else:
            self.logger.error(f"事件发布失败: {event_type}")
        
        return success
    
    def publish_high_priority(
        self,
        event_type: str,
        payload: Dict[str, Any],
        **kwargs
    ) -> bool:
        """
        发布高优先级事件（便捷方法）
        
        Args:
            event_type: 事件类型
            payload: 事件负载数据
            **kwargs: 其他参数
            
        Returns:
            bool: 是否发布成功
        """
        return self.publish(
            event_type=event_type,
            payload=payload,
            priority=MessagePriority.HIGH,
            **kwargs
        )
    
    def publish_point_to_point(
        self,
        event_type: str,
        payload: Dict[str, Any],
        **kwargs
    ) -> bool:
        """
        发布点对点事件（便捷方法）
        
        Args:
            event_type: 事件类型
            payload: 事件负载数据
            **kwargs: 其他参数
            
        Returns:
            bool: 是否发布成功
        """
        return self.publish(
            event_type=event_type,
            payload=payload,
            delivery_mode=DeliveryMode.POINT_TO_POINT,
            **kwargs
        )
    
    def emit(self, event_type: str, **payload) -> bool:
        """
        简化的发布接口（使用关键字参数）
        
        Args:
            event_type: 事件类型
            **payload: 事件数据
            
        Returns:
            bool: 是否发布成功
            
        Example:
            >>> publisher.emit("NAV_UPDATED", fund_code="000001", nav=1.5)
            True
        """
        return self.publish(event_type, payload)
    
    def batch_publish(
        self,
        events: list,
        continue_on_error: bool = True
    ) -> Dict[str, Any]:
        """
        批量发布事件
        
        Args:
            events: 事件列表，每个元素为字典包含event_type和payload
            continue_on_error: 遇到错误时是否继续
            
        Returns:
            Dict: 批量发布结果统计
            
        Example:
            >>> events = [
            ...     {"event_type": "FUND_DATA_UPDATED", "payload": {"code": "000001"}},
            ...     {"event_type": "NAV_UPDATED", "payload": {"code": "000002"}}
            ... ]
            >>> publisher.batch_publish(events)
            {"total": 2, "success": 2, "failed": 0}
        """
        results = {
            'total': len(events),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for event in events:
            try:
                success = self.publish(
                    event_type=event['event_type'],
                    payload=event.get('payload', {}),
                    priority=event.get('priority', MessagePriority.NORMAL),
                    delivery_mode=event.get('delivery_mode', DeliveryMode.PUB_SUB)
                )
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Failed to publish: {event['event_type']}")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{event['event_type']}: {str(e)}")
                if not continue_on_error:
                    break
        
        self.logger.info(
            f"批量发布完成: 总数={results['total']}, "
            f"成功={results['success']}, 失败={results['failed']}"
        )
        return results


# 全局发布器实例
_event_publisher = EventPublisher()


def publish_event(
    event_type: str,
    payload: Dict[str, Any],
    **kwargs
) -> bool:
    """
    全局便捷函数 - 发布事件
    
    Args:
        event_type: 事件类型
        payload: 事件负载数据
        **kwargs: 其他参数
        
    Returns:
        bool: 是否发布成功
    """
    return _event_publisher.publish(event_type, payload, **kwargs)


def emit_event(event_type: str, **payload) -> bool:
    """
    全局便捷函数 - 简化发布事件
    
    Args:
        event_type: 事件类型
        **payload: 事件数据
        
    Returns:
        bool: 是否发布成功
    """
    return _event_publisher.emit(event_type, **payload)


def event_trigger(event_type: str, priority: MessagePriority = MessagePriority.NORMAL):
    """
    装饰器 - 在函数执行后触发事件
    
    Args:
        event_type: 事件类型
        priority: 消息优先级
        
    Returns:
        Decorator function
        
    Example:
        >>> @event_trigger("FUND_DATA_UPDATED", priority=MessagePriority.HIGH)
        ... def update_fund_data(fund_code: str):
        ...     # 更新基金数据
        ...     return {"fund_code": fund_code, "status": "updated"}
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 执行原函数
            result = func(*args, **kwargs)
            
            # 构建事件负载
            payload = {
                'function': func.__name__,
                'args': args,
                'kwargs': kwargs,
                'result': result if isinstance(result, dict) else {'value': result}
            }
            
            # 发布事件
            _event_publisher.publish(event_type, payload, priority=priority)
            
            return result
        return wrapper
    return decorator
