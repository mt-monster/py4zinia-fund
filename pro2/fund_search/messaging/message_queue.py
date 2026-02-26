#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Redis消息队列实现

实现基于Redis的可靠消息队列，支持：
- 消息发布和消费
- 消息确认机制
- 死信队列
- 消息延迟投递
- 优先级队列
"""

import json
import logging
import threading
import uuid
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from dataclasses import dataclass, asdict

import redis

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """消息数据类"""
    id: str
    queue: str
    data: Dict[str, Any]
    priority: int = 0
    timestamp: str = None
    attempts: int = 0
    max_attempts: int = 3
    delay: int = 0  # 延迟投递（秒）
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'queue': self.queue,
            'data': self.data,
            'priority': self.priority,
            'timestamp': self.timestamp,
            'attempts': self.attempts,
            'max_attempts': self.max_attempts,
            'delay': self.delay
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Message':
        return cls(
            id=data['id'],
            queue=data['queue'],
            data=data['data'],
            priority=data.get('priority', 0),
            timestamp=data.get('timestamp'),
            attempts=data.get('attempts', 0),
            max_attempts=data.get('max_attempts', 3),
            delay=data.get('delay', 0)
        )


class MessageQueue:
    """
    消息队列
    
    基于Redis List实现的FIFO队列，支持优先级和延迟消息。
    """
    
    def __init__(self, queue_name: str, redis_url: str = None):
        self.queue_name = queue_name
        self.redis_url = redis_url or 'redis://localhost:6379/0'
        self._redis: Optional[redis.Redis] = None
        self._lock = threading.Lock()
        
        # 队列键名
        self.queue_key = f"queue:{queue_name}"
        self.processing_key = f"queue:{queue_name}:processing"
        self.dlq_key = f"queue:{queue_name}:dlq"  # 死信队列
        self.delay_key = f"queue:{queue_name}:delay"
        
        self._connect()
    
    def _connect(self):
        """连接Redis"""
        try:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        except Exception as e:
            logger.error(f"连接Redis失败: {e}")
            self._redis = None
    
    @property
    def is_connected(self) -> bool:
        """检查连接状态"""
        if self._redis is None:
            return False
        try:
            self._redis.ping()
            return True
        except:
            return False
    
    def publish(self, data: Dict[str, Any], priority: int = 0, 
                delay: int = 0, max_attempts: int = 3) -> str:
        """
        发布消息到队列
        
        Args:
            data: 消息数据
            priority: 优先级（数值越大优先级越高）
            delay: 延迟投递秒数
            max_attempts: 最大重试次数
            
        Returns:
            str: 消息ID
        """
        message = Message(
            id=str(uuid.uuid4()),
            queue=self.queue_name,
            data=data,
            priority=priority,
            max_attempts=max_attempts,
            delay=delay
        )
        
        if not self.is_connected:
            logger.warning("Redis未连接，消息无法发布")
            return message.id
        
        message_data = json.dumps(message.to_dict())
        
        with self._lock:
            if delay > 0:
                # 延迟消息放入有序集合
                execute_time = time.time() + delay
                self._redis.zadd(self.delay_key, {message_data: execute_time})
                logger.debug(f"延迟消息已发布: {message.id}, 延迟: {delay}秒")
            else:
                # 使用优先级分数（Redis sorted set）
                score = priority + time.time() / 1e10  # 确保相同优先级下FIFO
                self._redis.zadd(self.queue_key, {message_data: score})
                logger.debug(f"消息已发布: {message.id}, 优先级: {priority}")
        
        return message.id
    
    def consume(self, timeout: int = 30, auto_ack: bool = False) -> Optional[Message]:
        """
        消费消息
        
        Args:
            timeout: 阻塞超时时间（秒）
            auto_ack: 是否自动确认
            
        Returns:
            Message: 消息对象，超时返回None
        """
        if not self.is_connected:
            logger.warning("Redis未连接，无法消费消息")
            return None
        
        # 先处理延迟消息
        self._process_delayed_messages()
        
        # 从队列获取消息（优先级最高的）
        with self._lock:
            # 获取最高优先级的消息
            items = self._redis.zrevrange(self.queue_key, 0, 0, withscores=True)
            
            if not items:
                return None
            
            message_data, score = items[0]
            
            # 从队列移除
            self._redis.zrem(self.queue_key, message_data)
            
            message = Message.from_dict(json.loads(message_data))
            message.attempts += 1
            
            if not auto_ack:
                # 放入处理中集合
                self._redis.hset(self.processing_key, message.id, json.dumps(message.to_dict()))
            
            logger.debug(f"消息已消费: {message.id}, 第 {message.attempts} 次尝试")
            return message
    
    def ack(self, message_id: str):
        """
        确认消息处理完成
        
        Args:
            message_id: 消息ID
        """
        if not self.is_connected:
            return
        
        with self._lock:
            self._redis.hdel(self.processing_key, message_id)
            logger.debug(f"消息已确认: {message_id}")
    
    def nack(self, message_id: str, requeue: bool = True):
        """
        否定确认消息
        
        Args:
            message_id: 消息ID
            requeue: 是否重新入队
        """
        if not self.is_connected:
            return
        
        with self._lock:
            message_data = self._redis.hget(self.processing_key, message_id)
            
            if message_data:
                self._redis.hdel(self.processing_key, message_id)
                message = Message.from_dict(json.loads(message_data))
                
                if requeue and message.attempts < message.max_attempts:
                    # 重新入队，稍微降低优先级
                    score = (message.priority - 1) + time.time() / 1e10
                    self._redis.zadd(self.queue_key, {message_data: score})
                    logger.debug(f"消息已重新入队: {message_id}")
                else:
                    # 放入死信队列
                    self._redis.lpush(self.dlq_key, message_data)
                    logger.warning(f"消息已转入死信队列: {message_id}")
    
    def _process_delayed_messages(self):
        """处理延迟消息"""
        if not self.is_connected:
            return
        
        now = time.time()
        
        with self._lock:
            # 获取到期的延迟消息
            expired = self._redis.zrangebyscore(self.delay_key, 0, now)
            
            for message_data in expired:
                # 从延迟队列移除
                self._redis.zrem(self.delay_key, message_data)
                
                # 放入主队列
                message = Message.from_dict(json.loads(message_data))
                score = message.priority + time.time() / 1e10
                self._redis.zadd(self.queue_key, {message_data: score})
                
                logger.debug(f"延迟消息已转入主队列: {message.id}")
    
    def get_stats(self) -> Dict[str, int]:
        """获取队列统计信息"""
        if not self.is_connected:
            return {'connected': False}
        
        return {
            'connected': True,
            'pending': self._redis.zcard(self.queue_key),
            'processing': self._redis.hlen(self.processing_key),
            'delayed': self._redis.zcard(self.delay_key),
            'dead_letter': self._redis.llen(self.dlq_key)
        }
    
    def peek(self, count: int = 10) -> List[Message]:
        """
        查看队列中的消息（不取出）
        
        Args:
            count: 查看数量
            
        Returns:
            List[Message]: 消息列表
        """
        if not self.is_connected:
            return []
        
        items = self._redis.zrevrange(self.queue_key, 0, count - 1)
        messages = []
        
        for item in items:
            try:
                message = Message.from_dict(json.loads(item))
                messages.append(message)
            except:
                pass
        
        return messages
    
    def clear(self):
        """清空队列"""
        if not self.is_connected:
            return
        
        self._redis.delete(self.queue_key)
        self._redis.delete(self.processing_key)
        self._redis.delete(self.delay_key)
        self._redis.delete(self.dlq_key)
        
        logger.info(f"队列 {self.queue_name} 已清空")


class QueueConsumer:
    """
    队列消费者
    
    持续消费消息并调用处理器。
    """
    
    def __init__(self, queue: MessageQueue, handler: Callable[[Message], bool]):
        self.queue = queue
        self.handler = handler
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """启动消费者"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._thread.start()
        logger.info(f"队列消费者已启动: {self.queue.queue_name}")
    
    def stop(self):
        """停止消费者"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info(f"队列消费者已停止: {self.queue.queue_name}")
    
    def _consume_loop(self):
        """消费循环"""
        while self._running:
            try:
                message = self.queue.consume(timeout=1, auto_ack=False)
                
                if message:
                    try:
                        success = self.handler(message)
                        if success:
                            self.queue.ack(message.id)
                        else:
                            self.queue.nack(message.id, requeue=True)
                    except Exception as e:
                        logger.error(f"处理消息失败: {e}")
                        self.queue.nack(message.id, requeue=True)
                else:
                    # 没有消息，短暂休息
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"消费循环出错: {e}")
                time.sleep(1)
