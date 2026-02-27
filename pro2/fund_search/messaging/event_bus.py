#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
事件总线（纯内存实现）

不依赖 Redis，基于线程安全的内存字典实现：
- 事件发布和订阅
- 异步事件处理（后台线程队列）
- 事件优先级
- 通配符模式订阅
- 事件历史存储（内存，限制条数）
"""

import fnmatch
import logging
import queue
import threading
import uuid
from collections import defaultdict, deque
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Callable, Optional, Any

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """事件优先级"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


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
        return {
            'event_id': self.event_id,
            'name': self.name,
            'data': self.data,
            'priority': self.priority.value,
            'timestamp': self.timestamp,
            'source': self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Event':
        return cls(
            name=data['name'],
            data=data['data'],
            priority=EventPriority(data.get('priority', 2)),
            timestamp=data.get('timestamp'),
            event_id=data.get('event_id'),
            source=data.get('source'),
        )


class EventBus:
    """
    内存事件总线（单例）

    emit() 将事件放入优先级队列，后台线程异步分发给订阅者。
    同一进程内所有模块共享同一个实例。
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # (priority, handler) 列表，按 event_name 索引
        self._handlers: Dict[str, List] = defaultdict(list)
        # pattern -> [handler, ...]
        self._pattern_handlers: Dict[str, List[Callable]] = defaultdict(list)

        # 优先级队列：(priority_value, Event)
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

        self._initialized = True
        logger.info("内存事件总线初始化完成")

    # -------- 连接状态（兼容旧代码） --------

    @property
    def is_connected(self) -> bool:
        """内存模式始终返回 True"""
        return True

    # -------- 订阅 --------

    def on(self, event_name: str, priority: EventPriority = EventPriority.NORMAL):
        """事件订阅装饰器"""
        def decorator(handler: Callable):
            self.subscribe(event_name, handler, priority)
            return handler
        return decorator

    def subscribe(self, event_name: str, handler: Callable,
                  priority: EventPriority = EventPriority.NORMAL):
        """订阅事件"""
        self._handlers[event_name].append((priority.value, handler))
        self._handlers[event_name].sort(key=lambda x: x[0])
        logger.debug(f"已订阅: {event_name}，处理器数: {len(self._handlers[event_name])}")

    def unsubscribe(self, event_name: str, handler: Optional[Callable] = None):
        """取消订阅"""
        if event_name not in self._handlers:
            return
        if handler is None:
            del self._handlers[event_name]
        else:
            self._handlers[event_name] = [
                (p, h) for p, h in self._handlers[event_name] if h != handler
            ]

    def subscribe_pattern(self, pattern: str, handler: Callable):
        """通配符模式订阅（如 'fund.*'）"""
        self._pattern_handlers[pattern].append(handler)

    # -------- 发布 --------

    def emit(self, event_name: str, data: Dict[str, Any] = None,
             priority: EventPriority = EventPriority.NORMAL,
             source: str = None):
        """发布事件（放入异步队列）"""
        event = Event(name=event_name, data=data or {}, priority=priority, source=source)
        self._queue.put((priority.value, event))
        logger.debug(f"事件已入队: {event_name}")

    def emit_sync(self, event_name: str, data: Dict[str, Any] = None,
                  priority: EventPriority = EventPriority.NORMAL,
                  source: str = None):
        """同步发布事件（直接在当前线程处理，不经过队列）"""
        event = Event(name=event_name, data=data or {}, priority=priority, source=source)
        self._dispatch(event)

    # -------- 内部分发 --------

    def _dispatch(self, event: Event):
        """将事件分发给匹配的处理器"""
        for _priority, handler in self._handlers.get(event.name, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"处理事件 {event.name} 失败: {e}")

        for pattern, handlers in self._pattern_handlers.items():
            if fnmatch.fnmatch(event.name, pattern):
                for handler in handlers:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"处理模式事件 {pattern} 失败: {e}")

    def _worker_loop(self):
        """后台工作线程，从队列取事件分发"""
        logger.info("事件总线后台线程已启动")
        while self._running:
            try:
                _priority, event = self._queue.get(timeout=1.0)
                self._dispatch(event)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"事件总线工作线程异常: {e}")
        logger.info("事件总线后台线程已停止")

    # -------- 生命周期 --------

    def start_listener(self):
        """启动后台分发线程（兼容旧接口）"""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True, name="EventBusWorker"
        )
        self._worker_thread.start()
        logger.info("事件总线后台线程已启动")

    def stop_listener(self):
        """停止后台分发线程"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        logger.info("事件总线后台线程已停止")

    def get_stats(self) -> Dict:
        """统计信息"""
        return {
            'connected': True,
            'mode': 'memory',
            'handlers_count': sum(len(h) for h in self._handlers.values()),
            'events_count': len(self._handlers),
            'patterns_count': len(self._pattern_handlers),
            'queue_size': self._queue.qsize(),
            'running': self._running,
        }


class EventStore:
    """
    事件存储（内存实现）

    按事件名保存最近 N 条历史记录，用于调试和审计。
    """

    def __init__(self, max_per_event: int = 500):
        self._store: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_per_event))
        self._lock = threading.Lock()

    def store(self, event: Event, ttl: int = None):
        """存储事件（ttl 参数保留兼容性，内存模式不使用）"""
        with self._lock:
            self._store[event.name].appendleft(event.to_dict())

    def get_events(self, event_name: str, count: int = 100) -> List[Event]:
        """获取事件历史"""
        with self._lock:
            records = list(self._store.get(event_name, []))[:count]
        events = []
        for r in records:
            try:
                events.append(Event.from_dict(r))
            except Exception:
                pass
        return events


# 全局事件总线实例
event_bus = EventBus()


def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    return event_bus
