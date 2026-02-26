# -*- coding: utf-8 -*-
"""
事件订阅器/消费者
提供统一的事件订阅和消费接口，支持多种消费模式
"""

import logging
import threading
import functools
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from .redis_broker import RedisBroker, MessagePriority, DeliveryMode, Message

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """订阅信息"""
    id: str
    event_type: str
    handler: Callable[[Message], None]
    delivery_mode: DeliveryMode
    priority: MessagePriority
    created_at: datetime = field(default_factory=datetime.now)
    active: bool = True


class EventSubscriber:
    """
    事件订阅器
    
    提供事件订阅和消费功能：
    - 支持Pub/Sub模式（实时广播）
    - 支持点对点模式（队列消费）
    - 支持并发消费
    - 支持自动重连和错误恢复
    """
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, max_workers: int = 4):
        if self._initialized:
            return
        
        self.broker = RedisBroker()
        self.logger = logging.getLogger(__name__)
        self._subscriptions: Dict[str, Subscription] = {}
        self._running = False
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="event_worker")
        self._consumer_threads: List[threading.Thread] = []
        self._max_workers = max_workers
        
        self._initialized = True
        self.logger.info(f"事件订阅器初始化完成（工作线程: {max_workers}）")
    
    def subscribe(
        self,
        event_type: str,
        handler: Callable[[Message], None],
        delivery_mode: DeliveryMode = DeliveryMode.PUB_SUB,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Subscription:
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
            delivery_mode: 投递模式
            priority: 优先级（点对点模式有效）
            
        Returns:
            Subscription: 订阅对象
            
        Example:
            >>> def handle_fund_update(message: Message):
            ...     print(f"收到基金更新: {message.payload}")
            >>> sub = subscriber.subscribe("FUND_DATA_UPDATED", handle_fund_update)
        """
        import uuid
        
        subscription_id = str(uuid.uuid4())
        
        subscription = Subscription(
            id=subscription_id,
            event_type=event_type,
            handler=handler,
            delivery_mode=delivery_mode,
            priority=priority
        )
        
        self._subscriptions[subscription_id] = subscription
        
        # 如果是Pub/Sub模式，立即注册到broker
        if delivery_mode == DeliveryMode.PUB_SUB:
            self.broker.subscribe(event_type, handler)
        
        self.logger.info(
            f"已订阅事件: {event_type}, "
            f"模式: {delivery_mode.value}, "
            f"订阅ID: {subscription_id}"
        )
        
        return subscription
    
    def unsubscribe(self, subscription: Union[str, Subscription]) -> bool:
        """
        取消订阅
        
        Args:
            subscription: 订阅ID或订阅对象
            
        Returns:
            bool: 是否成功
        """
        if isinstance(subscription, Subscription):
            subscription_id = subscription.id
        else:
            subscription_id = subscription
        
        if subscription_id in self._subscriptions:
            sub = self._subscriptions[subscription_id]
            sub.active = False
            del self._subscriptions[subscription_id]
            
            # 如果是Pub/Sub模式，从broker取消订阅
            if sub.delivery_mode == DeliveryMode.PUB_SUB:
                self.broker.unsubscribe(subscription_id)
            
            self.logger.info(f"已取消订阅: {subscription_id}")
            return True
        
        return False
    
    def on(
        self,
        event_type: str,
        delivery_mode: DeliveryMode = DeliveryMode.PUB_SUB,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Callable:
        """
        装饰器方式订阅事件
        
        Args:
            event_type: 事件类型
            delivery_mode: 投递模式
            priority: 优先级
            
        Returns:
            Decorator function
            
        Example:
            >>> @subscriber.on("FUND_DATA_UPDATED")
            ... def handle_fund_update(message: Message):
            ...     print(f"收到更新: {message.payload}")
        """
        def decorator(func: Callable) -> Callable:
            self.subscribe(event_type, func, delivery_mode, priority)
            return func
        return decorator
    
    def start_consuming(self, blocking: bool = False) -> None:
        """
        启动消息消费
        
        Args:
            blocking: 是否阻塞当前线程
        """
        if self._running:
            return
        
        self._running = True
        
        # 启动Pub/Sub监听
        self.broker.start_listening()
        
        # 为点对点模式的订阅启动消费线程
        for sub in self._subscriptions.values():
            if sub.delivery_mode == DeliveryMode.POINT_TO_POINT and sub.active:
                thread = threading.Thread(
                    target=self._consume_loop,
                    args=(sub,),
                    daemon=True,
                    name=f"consumer-{sub.event_type}"
                )
                thread.start()
                self._consumer_threads.append(thread)
        
        self.logger.info(f"消息消费已启动，共 {len(self._consumer_threads)} 个消费线程")
        
        if blocking:
            # 阻塞主线程
            try:
                while self._running:
                    threading.Event().wait(1)
            except KeyboardInterrupt:
                self.stop_consuming()
    
    def _consume_loop(self, subscription: Subscription) -> None:
        """
        消费循环
        
        Args:
            subscription: 订阅对象
        """
        self.logger.info(f"消费线程启动: {subscription.event_type}")
        
        while self._running and subscription.active:
            try:
                def handler(message: Message) -> bool:
                    """消息处理包装器"""
                    try:
                        # 在线程池中执行处理函数
                        future = self._executor.submit(subscription.handler, message)
                        future.result(timeout=60)  # 最多等待60秒
                        return True
                    except Exception as e:
                        self.logger.error(f"消息处理异常: {e}, message_id={message.id}")
                        return False
                
                # 消费消息
                message = self.broker.consume(
                    subscription.event_type,
                    handler,
                    timeout=5,
                    priority=subscription.priority
                )
                
                if message is None:
                    # 没有消息，短暂休眠
                    threading.Event().wait(0.1)
                    
            except Exception as e:
                self.logger.error(f"消费循环异常: {e}")
                threading.Event().wait(1)
        
        self.logger.info(f"消费线程停止: {subscription.event_type}")
    
    def stop_consuming(self) -> None:
        """停止消息消费"""
        self._running = False
        self.broker.stop_listening()
        
        # 关闭线程池
        self._executor.shutdown(wait=True)
        
        self.logger.info("消息消费已停止")
    
    def get_subscriptions(self, event_type: Optional[str] = None) -> List[Subscription]:
        """
        获取订阅列表
        
        Args:
            event_type: 事件类型过滤器（None表示所有）
            
        Returns:
            List[Subscription]: 订阅列表
        """
        subscriptions = list(self._subscriptions.values())
        if event_type:
            subscriptions = [s for s in subscriptions if s.event_type == event_type]
        return subscriptions
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取订阅统计信息
        
        Returns:
            Dict: 统计信息
        """
        return {
            'total_subscriptions': len(self._subscriptions),
            'active_subscriptions': sum(1 for s in self._subscriptions.values() if s.active),
            'pub_sub_count': sum(1 for s in self._subscriptions.values() 
                              if s.delivery_mode == DeliveryMode.PUB_SUB),
            'point_to_point_count': sum(1 for s in self._subscriptions.values() 
                                       if s.delivery_mode == DeliveryMode.POINT_TO_POINT),
            'consumer_threads': len(self._consumer_threads),
            'running': self._running
        }


# 全局订阅器实例
_event_subscriber = EventSubscriber()


def subscribe(
    event_type: str,
    handler: Callable[[Message], None],
    delivery_mode: DeliveryMode = DeliveryMode.PUB_SUB,
    priority: MessagePriority = MessagePriority.NORMAL
) -> Subscription:
    """
    全局便捷函数 - 订阅事件
    
    Args:
        event_type: 事件类型
        handler: 处理函数
        delivery_mode: 投递模式
        priority: 优先级
        
    Returns:
        Subscription: 订阅对象
    """
    return _event_subscriber.subscribe(event_type, handler, delivery_mode, priority)


def on_event(event_type: str, **kwargs):
    """
    全局便捷函数 - 装饰器方式订阅事件
    
    Args:
        event_type: 事件类型
        **kwargs: 其他参数
        
    Returns:
        Decorator function
    """
    return _event_subscriber.on(event_type, **kwargs)
