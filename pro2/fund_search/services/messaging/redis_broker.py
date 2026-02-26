# -*- coding: utf-8 -*-
"""
Redis消息代理
提供基于Redis的消息队列功能，支持发布-订阅和点对点模式
"""

import json
import logging
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager

try:
    import redis
    from redis.exceptions import RedisError, ConnectionError, TimeoutError
except ImportError:
    redis = None
    RedisError = Exception
    ConnectionError = Exception
    TimeoutError = Exception

from ...shared.config import REDIS_CONFIG

logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """消息优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class DeliveryMode(Enum):
    """消息投递模式"""
    PUB_SUB = "pub_sub"  # 发布-订阅模式（广播）
    POINT_TO_POINT = "point_to_point"  # 点对点模式（队列）


@dataclass
class Message:
    """消息数据结构"""
    id: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: float
    priority: int
    retry_count: int = 0
    max_retries: int = 3
    delivery_mode: str = DeliveryMode.PUB_SUB.value
    correlation_id: Optional[str] = None
    source: Optional[str] = None
    
    def to_json(self) -> str:
        """序列化为JSON"""
        return json.dumps(asdict(self), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """从JSON反序列化"""
        data = json.loads(json_str)
        return cls(**data)


class RedisBroker:
    """
    Redis消息代理
    
    提供消息队列的核心功能：
    - 发布-订阅模式（Pub/Sub）
    - 点对点模式（List/Queue）
    - 延迟队列（Sorted Set）
    - 消息持久化和重试机制
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
        
        if redis is None:
            raise ImportError("redis package is required. Install with: pip install redis")
        
        self.config = REDIS_CONFIG
        self._redis_client: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._subscribers: Dict[str, List[Callable]] = {}
        self._running = False
        self.logger = logging.getLogger(__name__)
        
        self._connect()
        self._initialized = True
        self.logger.info("Redis消息代理初始化完成")
    
    def _connect(self) -> None:
        """建立Redis连接"""
        try:
            self._redis_client = redis.Redis(
                host=self.config.get('host', 'localhost'),
                port=self.config.get('port', 6379),
                db=self.config.get('db', 0),
                password=self.config.get('password'),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                health_check_interval=30
            )
            # 测试连接
            self._redis_client.ping()
            self.logger.info(f"Redis连接成功: {self.config.get('host')}:{self.config.get('port')}")
        except Exception as e:
            self.logger.error(f"Redis连接失败: {e}")
            raise ConnectionError(f"无法连接到Redis: {e}")
    
    @contextmanager
    def _connection_context(self):
        """连接上下文管理器，自动处理重连"""
        try:
            if not self._redis_client or not self._redis_client.ping():
                self._connect()
            yield self._redis_client
        except (ConnectionError, TimeoutError) as e:
            self.logger.warning(f"Redis连接异常，尝试重连: {e}")
            self._connect()
            yield self._redis_client
        except Exception as e:
            self.logger.error(f"Redis操作异常: {e}")
            raise
    
    def _get_queue_name(self, event_type: str, priority: MessagePriority = MessagePriority.NORMAL) -> str:
        """获取队列名称"""
        if priority == MessagePriority.HIGH:
            return f"queue:high:{event_type}"
        elif priority == MessagePriority.LOW:
            return f"queue:low:{event_type}"
        return f"queue:{event_type}"
    
    def _get_channel_name(self, event_type: str) -> str:
        """获取发布订阅频道名称"""
        return f"channel:{event_type}"
    
    def _get_dead_letter_queue(self, event_type: str) -> str:
        """获取死信队列名称"""
        return f"dlq:{event_type}"
    
    def publish(
        self,
        event_type: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        delivery_mode: DeliveryMode = DeliveryMode.PUB_SUB,
        correlation_id: Optional[str] = None,
        source: Optional[str] = None
    ) -> bool:
        """
        发布消息
        
        Args:
            event_type: 事件类型
            payload: 消息负载
            priority: 消息优先级
            delivery_mode: 投递模式
            correlation_id: 关联ID（用于追踪）
            source: 消息来源
            
        Returns:
            bool: 是否发送成功
        """
        message = Message(
            id=str(uuid.uuid4()),
            event_type=event_type,
            payload=payload,
            timestamp=time.time(),
            priority=priority.value,
            delivery_mode=delivery_mode.value,
            correlation_id=correlation_id or str(uuid.uuid4()),
            source=source or "unknown"
        )
        
        try:
            with self._connection_context() as client:
                if delivery_mode == DeliveryMode.PUB_SUB:
                    # 发布-订阅模式
                    channel = self._get_channel_name(event_type)
                    client.publish(channel, message.to_json())
                    self.logger.debug(f"消息已发布到频道 {channel}: {message.id}")
                else:
                    # 点对点模式 - 使用优先级队列
                    queue = self._get_queue_name(event_type, priority)
                    # 使用LPUSH RPOP模式实现FIFO队列
                    client.lpush(queue, message.to_json())
                    self.logger.debug(f"消息已入队 {queue}: {message.id}")
                
                return True
        except Exception as e:
            self.logger.error(f"消息发布失败: {e}")
            return False
    
    def subscribe(
        self,
        event_type: str,
        handler: Callable[[Message], None],
        pattern: bool = False
    ) -> str:
        """
        订阅事件（Pub/Sub模式）
        
        Args:
            event_type: 事件类型（或模式）
            handler: 消息处理函数
            pattern: 是否使用模式匹配
            
        Returns:
            str: 订阅ID
        """
        subscription_id = str(uuid.uuid4())
        
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append((subscription_id, handler))
        self.logger.debug(f"已订阅事件 {event_type}, 订阅ID: {subscription_id}")
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        取消订阅
        
        Args:
            subscription_id: 订阅ID
            
        Returns:
            bool: 是否成功
        """
        for event_type, handlers in self._subscribers.items():
            for i, (sid, _) in enumerate(handlers):
                if sid == subscription_id:
                    handlers.pop(i)
                    self.logger.debug(f"已取消订阅 {subscription_id} 从事件 {event_type}")
                    return True
        return False
    
    def consume(
        self,
        event_type: str,
        handler: Callable[[Message], bool],
        timeout: int = 5,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Optional[Message]:
        """
        消费消息（点对点模式）
        
        Args:
            event_type: 事件类型
            handler: 消息处理函数，返回True表示处理成功
            timeout: 阻塞超时时间（秒）
            priority: 队列优先级
            
        Returns:
            Optional[Message]: 消费的消息，如果没有则返回None
        """
        try:
            with self._connection_context() as client:
                queue = self._get_queue_name(event_type, priority)
                
                # 尝试从高优先级到低优先级获取消息
                for prio in [MessagePriority.CRITICAL, MessagePriority.HIGH, 
                           MessagePriority.NORMAL, MessagePriority.LOW]:
                    q = self._get_queue_name(event_type, prio)
                    result = client.rpop(q)
                    if result:
                        break
                else:
                    result = None
                
                if not result:
                    return None
                
                message = Message.from_json(result)
                
                try:
                    success = handler(message)
                    if not success:
                        # 处理失败，重试
                        self._retry_message(message)
                except Exception as e:
                    self.logger.error(f"消息处理失败: {e}, message_id={message.id}")
                    self._retry_message(message)
                
                return message
        except Exception as e:
            self.logger.error(f"消息消费异常: {e}")
            return None
    
    def _retry_message(self, message: Message) -> None:
        """
        重试消息处理
        
        Args:
            message: 需要重试的消息
        """
        message.retry_count += 1
        
        if message.retry_count > message.max_retries:
            # 超过最大重试次数，放入死信队列
            self._move_to_dead_letter(message)
        else:
            # 重新入队，延迟重试（指数退避）
            delay = min(2 ** message.retry_count, 60)  # 最大延迟60秒
            time.sleep(delay)
            
            try:
                with self._connection_context() as client:
                    queue = self._get_queue_name(message.event_type)
                    client.lpush(queue, message.to_json())
                    self.logger.warning(
                        f"消息重新入队: {message.id}, "
                        f"重试次数: {message.retry_count}, 延迟: {delay}s"
                    )
            except Exception as e:
                self.logger.error(f"消息重试失败: {e}")
    
    def _move_to_dead_letter(self, message: Message) -> None:
        """
        将消息移入死信队列
        
        Args:
            message: 消息对象
        """
        try:
            with self._connection_context() as client:
                dlq = self._get_dead_letter_queue(message.event_type)
                message.payload['_dead_reason'] = f"超过最大重试次数({message.max_retries})"
                message.payload['_dead_time'] = time.time()
                client.lpush(dlq, message.to_json())
                self.logger.error(f"消息已移入死信队列: {message.id}")
        except Exception as e:
            self.logger.error(f"移入死信队列失败: {e}")
    
    def start_listening(self) -> None:
        """启动Pub/Sub监听（在独立线程中运行）"""
        import threading
        
        if self._running:
            return
        
        self._running = True
        listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        listener_thread.start()
        self.logger.info("Pub/Sub监听线程已启动")
    
    def _listen_loop(self) -> None:
        """监听循环"""
        try:
            with self._connection_context() as client:
                self._pubsub = client.pubsub()
                
                # 订阅所有已注册的事件
                for event_type in self._subscribers.keys():
                    channel = self._get_channel_name(event_type)
                    self._pubsub.subscribe(channel)
                    self.logger.debug(f"已订阅频道: {channel}")
                
                # 监听消息
                for message_data in self._pubsub.listen():
                    if not self._running:
                        break
                    
                    if message_data['type'] == 'message':
                        try:
                            msg = Message.from_json(message_data['data'])
                            event_type = msg.event_type
                            
                            # 调用所有注册的处理器
                            handlers = self._subscribers.get(event_type, [])
                            for _, handler in handlers:
                                try:
                                    handler(msg)
                                except Exception as e:
                                    self.logger.error(f"处理器执行失败: {e}")
                        except Exception as e:
                            self.logger.error(f"消息解析失败: {e}")
        except Exception as e:
            self.logger.error(f"监听循环异常: {e}")
            self._running = False
    
    def stop_listening(self) -> None:
        """停止监听"""
        self._running = False
        if self._pubsub:
            self._pubsub.close()
        self.logger.info("Pub/Sub监听已停止")
    
    def get_queue_length(self, event_type: str, priority: Optional[MessagePriority] = None) -> int:
        """
        获取队列长度
        
        Args:
            event_type: 事件类型
            priority: 优先级（None表示所有优先级）
            
        Returns:
            int: 队列长度
        """
        try:
            with self._connection_context() as client:
                if priority:
                    queue = self._get_queue_name(event_type, priority)
                    return client.llen(queue)
                else:
                    # 统计所有优先级
                    total = 0
                    for prio in MessagePriority:
                        queue = self._get_queue_name(event_type, prio)
                        total += client.llen(queue)
                    return total
        except Exception as e:
            self.logger.error(f"获取队列长度失败: {e}")
            return 0
    
    def clear_queue(self, event_type: str) -> bool:
        """
        清空队列
        
        Args:
            event_type: 事件类型
            
        Returns:
            bool: 是否成功
        """
        try:
            with self._connection_context() as client:
                for prio in MessagePriority:
                    queue = self._get_queue_name(event_type, prio)
                    client.delete(queue)
                return True
        except Exception as e:
            self.logger.error(f"清空队列失败: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            Dict: 健康状态信息
        """
        status = {
            'connected': False,
            'pubsub_active': self._running,
            'queue_stats': {},
            'subscribers': {}
        }
        
        try:
            with self._connection_context() as client:
                status['connected'] = True
                status['redis_info'] = client.info('server')
                
                # 统计订阅者
                for event_type, handlers in self._subscribers.items():
                    status['subscribers'][event_type] = len(handlers)
        except Exception as e:
            status['error'] = str(e)
        
        return status
