#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
事件总线实现

基于Redis的发布/订阅模式实现的事件总线，支持：
- 事件发布和订阅
- 异步事件处理
- 事件优先级
- 事件过滤和路由
- 分布式事件广播
"""

import json
import logging
import threading
import uuid
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict

import redis

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """事件优先级"""
    CRITICAL = 0    # 关键事件，立即处理
    HIGH = 1        # 高优先级
    NORMAL = 2      # 普通优先级
    LOW = 3         # 低优先级
    BACKGROUND = 4  # 后台任务


@dataclass
class Event:
    """事件数据类"""
    name: str
    data: Dict[str, Any]
    priority: EventPriority = EventPriority.NORMAL
    timestamp: str = None
    event_id: str = None
    source: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'event_id': self.event_id,
            'name': self.name,
            'data': self.data,
            'priority': self.priority.value,
            'timestamp': self.timestamp,
            'source': self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Event':
        """从字典创建事件"""
        return cls(
            name=data['name'],
            data=data['data'],
            priority=EventPriority(data.get('priority', 2)),
            timestamp=data.get('timestamp'),
            event_id=data.get('event_id'),
            source=data.get('source')
        )


class EventBus:
    """
    事件总线
    
    基于Redis的发布/订阅实现，支持本地和分布式事件传递。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, redis_url: str = None):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, redis_url: str = None):
        if self._initialized:
            return
            
        self.redis_url = redis_url or 'redis://localhost:6379/0'
        self._redis_client: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._handlers: Dict[str, List[Callable]] = {}
        self._pattern_handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._listener_thread: Optional[threading.Thread] = None
        
        self._connect()
        self._initialized = True
        logger.info("事件总线初始化完成")
    
    def _connect(self):
        """连接Redis"""
        try:
            self._redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self._pubsub = self._redis_client.pubsub()
            logger.info(f"已连接到Redis: {self.redis_url}")
        except Exception as e:
            logger.error(f"连接Redis失败: {e}")
            # 降级为本地模式
            self._redis_client = None
            self._pubsub = None
    
    @property
    def is_connected(self) -> bool:
        """检查是否连接到Redis"""
        if self._redis_client is None:
            return False
        try:
            self._redis_client.ping()
            return True
        except:
            return False
    
    def on(self, event_name: str, priority: EventPriority = EventPriority.NORMAL):
        """
        事件订阅装饰器
        
        Args:
            event_name: 事件名称
            priority: 处理器优先级（仅用于排序）
            
        Returns:
            Callable: 装饰器函数
        """
        def decorator(handler: Callable):
            self.subscribe(event_name, handler, priority)
            return handler
        return decorator
    
    def subscribe(self, event_name: str, handler: Callable, 
                  priority: EventPriority = EventPriority.NORMAL):
        """
        订阅事件
        
        Args:
            event_name: 事件名称
            handler: 事件处理器
            priority: 处理器优先级
        """
        if event_name not in self._handlers:
            self._handlers[event_name] = []
            
            # 订阅Redis频道
            if self.is_connected and self._pubsub:
                self._pubsub.subscribe(event_name)
                logger.debug(f"已订阅Redis频道: {event_name}")
        
        # 按优先级排序添加处理器
        self._handlers[event_name].append((priority.value, handler))
        self._handlers[event_name].sort(key=lambda x: x[0])
        logger.debug(f"已添加处理器: {event_name}, 处理器数量: {len(self._handlers[event_name])}")
    
    def unsubscribe(self, event_name: str, handler: Optional[Callable] = None):
        """
        取消订阅事件
        
        Args:
            event_name: 事件名称
            handler: 要移除的处理器，None则移除所有
        """
        if event_name not in self._handlers:
            return
        
        if handler is None:
            del self._handlers[event_name]
            if self.is_connected and self._pubsub:
                self._pubsub.unsubscribe(event_name)
        else:
            self._handlers[event_name] = [
                (p, h) for p, h in self._handlers[event_name] if h != handler
            ]
            if not self._handlers[event_name]:
                del self._handlers[event_name]
    
    def subscribe_pattern(self, pattern: str, handler: Callable):
        """
        使用模式订阅事件（通配符）
        
        Args:
            pattern: 事件名称模式，如 "fund.*"
            handler: 事件处理器
        """
        if pattern not in self._pattern_handlers:
            self._pattern_handlers[pattern] = []
            
            # 订阅Redis模式
            if self.is_connected and self._pubsub:
                self._pubsub.psubscribe(pattern)
        
        self._pattern_handlers[pattern].append(handler)
    
    def emit(self, event_name: str, data: Dict[str, Any] = None,
             priority: EventPriority = EventPriority.NORMAL,
             source: str = None):
        """
        发布事件
        
        Args:
            event_name: 事件名称
            data: 事件数据
            priority: 事件优先级
            source: 事件源
        """
        event = Event(
            name=event_name,
            data=data or {},
            priority=priority,
            source=source
        )
        
        # 本地处理
        self._handle_local(event)
        
        # 广播到Redis
        if self.is_connected:
            try:
                message = json.dumps(event.to_dict())
                self._redis_client.publish(event_name, message)
                logger.debug(f"事件已广播: {event_name}")
            except Exception as e:
                logger.error(f"广播事件失败: {e}")
    
    def _handle_local(self, event: Event):
        """本地处理事件"""
        handlers = self._handlers.get(event.name, [])
        
        for priority, handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"处理事件 {event.name} 失败: {e}")
        
        # 检查模式匹配
        for pattern, handlers in self._pattern_handlers.items():
            import fnmatch
            if fnmatch.fnmatch(event.name, pattern):
                for handler in handlers:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"处理模式事件 {pattern} 失败: {e}")
    
    def start_listener(self):
        """启动Redis消息监听线程"""
        if not self.is_connected or self._running:
            return
        
        self._running = True
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()
        logger.info("事件监听线程已启动")
    
    def stop_listener(self):
        """停止Redis消息监听线程"""
        self._running = False
        if self._listener_thread:
            self._listener_thread.join(timeout=5)
        logger.info("事件监听线程已停止")
    
    def _listen_loop(self):
        """监听Redis消息循环"""
        if not self._pubsub:
            return
        
        logger.info("开始监听Redis消息")
        
        for message in self._pubsub.listen():
            if not self._running:
                break
            
            if message['type'] in ('message', 'pmessage'):
                try:
                    data = json.loads(message['data'])
                    event = Event.from_dict(data)
                    self._handle_local(event)
                except Exception as e:
                    logger.error(f"处理Redis消息失败: {e}")
    
    def get_stats(self) -> Dict:
        """获取事件总线统计信息"""
        return {
            'connected': self.is_connected,
            'handlers_count': sum(len(h) for h in self._handlers.values()),
            'events_count': len(self._handlers),
            'patterns_count': len(self._pattern_handlers),
            'running': self._running
        }


class EventStore:
    """
    事件存储
    
    用于持久化存储事件历史，便于审计和重放。
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or 'redis://localhost:6379/1'
        try:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        except Exception as e:
            logger.error(f"连接Redis失败: {e}")
            self._redis = None
    
    def store(self, event: Event, ttl: int = 86400 * 7):
        """
        存储事件
        
        Args:
            event: 事件对象
            ttl: 过期时间（秒），默认7天
        """
        if not self._redis:
            return
        
        key = f"event:{event.event_id}"
        self._redis.setex(key, ttl, json.dumps(event.to_dict()))
        
        # 添加到事件流
        stream_key = f"events:{event.name}"
        self._redis.xadd(stream_key, {'data': json.dumps(event.to_dict())}, maxlen=10000)
    
    def get_events(self, event_name: str, count: int = 100) -> List[Event]:
        """
        获取事件历史
        
        Args:
            event_name: 事件名称
            count: 返回数量
            
        Returns:
            List[Event]: 事件列表
        """
        if not self._redis:
            return []
        
        stream_key = f"events:{event_name}"
        entries = self._redis.xrevrange(stream_key, count=count)
        
        events = []
        for entry_id, fields in entries:
            try:
                data = json.loads(fields.get('data', '{}'))
                events.append(Event.from_dict(data))
            except:
                pass
        
        return events


# 全局事件总线实例
event_bus = EventBus()


def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    return event_bus
