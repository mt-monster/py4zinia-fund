#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Redis消息队列和事件驱动架构模块

本模块实现了基于Redis的发布/订阅消息队列系统，用于构建事件驱动的架构。
主要功能包括：
- 事件发布/订阅机制
- 消息队列处理
- 事件处理器注册
- 分布式事件广播

使用方法:
    from messaging import EventBus, MessageQueue
    
    # 使用事件总线
    event_bus = EventBus()
    
    @event_bus.on('fund_data_updated')
    def handle_fund_update(event):
        print(f"基金数据已更新: {event.data}")
    
    event_bus.emit('fund_data_updated', {'fund_code': '000001'})
    
    # 使用消息队列
    queue = MessageQueue('backtest_queue')
    queue.publish({'task': 'run_backtest', 'strategy_id': '123'})
    message = queue.consume()

配置要求:
    - Redis服务器
    - redis-py>=5.0.0
"""

from .event_bus import EventBus, Event, EventPriority
from .message_queue import MessageQueue, QueueConsumer
from .handlers import (
    register_event_handlers,
    FundDataUpdatedHandler,
    BacktestCompletedHandler,
    CacheInvalidatedHandler
)

__all__ = [
    'EventBus',
    'Event',
    'EventPriority',
    'MessageQueue',
    'QueueConsumer',
    'register_event_handlers',
    'FundDataUpdatedHandler',
    'BacktestCompletedHandler',
    'CacheInvalidatedHandler'
]
