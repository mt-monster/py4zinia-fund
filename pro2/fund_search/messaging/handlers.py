#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
事件处理器

定义系统核心事件的业务处理器。
"""

import logging
from typing import Dict, Any

from .event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class FundDataUpdatedHandler:
    """基金数据更新事件处理器"""
    
    @staticmethod
    def handle(event: Event):
        """处理基金数据更新事件"""
        fund_code = event.data.get('fund_code')
        data_type = event.data.get('data_type', 'all')
        
        logger.info(f"处理基金数据更新事件: {fund_code}, 类型: {data_type}")
        
        try:
            # 触发相关缓存更新
            from services.fund_data_preloader import get_preloader
            preloader = get_preloader()
            
            # 更新相关缓存
            if data_type in ('nav', 'all'):
                cache_key = f"fund:analysis:{fund_code}"
                preloader.cache.delete(cache_key)
                logger.debug(f"已清除分析缓存: {cache_key}")
            
            # 发布衍生事件
            event_bus = EventBus()
            event_bus.emit('cache.invalidated', {
                'fund_code': fund_code,
                'cache_keys': [f"fund:analysis:{fund_code}"]
            })
            
        except Exception as e:
            logger.error(f"处理基金数据更新事件失败: {e}")


class BacktestCompletedHandler:
    """回测完成事件处理器"""
    
    @staticmethod
    def handle(event: Event):
        """处理回测完成事件"""
        task_id = event.data.get('task_id')
        strategy_id = event.data.get('strategy_id')
        user_id = event.data.get('user_id')
        success = event.data.get('success', False)
        
        logger.info(f"处理回测完成事件: task={task_id}, success={success}")
        
        try:
            if success:
                # 发送成功通知
                from celery_tasks.tasks import send_notification_task
                send_notification_task.delay(
                    user_id=user_id,
                    notification_type='push',
                    title='回测完成',
                    message=f'策略 {strategy_id} 的回测任务已完成，任务ID: {task_id}'
                )
                
                # 触发报告生成
                event_bus = EventBus()
                event_bus.emit('report.generate', {
                    'task_id': task_id,
                    'report_type': 'backtest'
                })
            else:
                # 发送失败通知
                error = event.data.get('error', '未知错误')
                from celery_tasks.tasks import send_notification_task
                send_notification_task.delay(
                    user_id=user_id,
                    notification_type='push',
                    title='回测失败',
                    message=f'策略 {strategy_id} 的回测任务失败: {error}'
                )
                
        except Exception as e:
            logger.error(f"处理回测完成事件失败: {e}")


class CacheInvalidatedHandler:
    """缓存失效事件处理器"""
    
    @staticmethod
    def handle(event: Event):
        """处理缓存失效事件"""
        fund_code = event.data.get('fund_code')
        cache_keys = event.data.get('cache_keys', [])
        
        logger.info(f"处理缓存失效事件: {fund_code}, keys={cache_keys}")
        
        try:
            from services.fund_data_preloader import get_preloader
            preloader = get_preloader()
            
            # 清除指定缓存
            for key in cache_keys:
                preloader.cache.delete(key)
            
            # 清除关联缓存
            if fund_code:
                preloader.invalidate_cache(fund_code)
                
        except Exception as e:
            logger.error(f"处理缓存失效事件失败: {e}")


class UserActionHandler:
    """用户操作事件处理器"""
    
    @staticmethod
    def handle(event: Event):
        """处理用户操作事件"""
        action = event.data.get('action')
        user_id = event.data.get('user_id')
        
        logger.info(f"处理用户操作事件: user={user_id}, action={action}")
        
        try:
            # 记录用户行为日志
            # 可以发送到数据分析服务
            pass
            
        except Exception as e:
            logger.error(f"处理用户操作事件失败: {e}")


def register_event_handlers(event_bus: EventBus = None):
    """
    注册所有事件处理器
    
    Args:
        event_bus: 事件总线实例，None则使用全局实例
    """
    from .event_bus import get_event_bus
    
    if event_bus is None:
        event_bus = get_event_bus()
    
    # 注册基金数据更新处理器
    event_bus.subscribe('fund.data_updated', FundDataUpdatedHandler.handle)
    
    # 注册回测完成处理器
    event_bus.subscribe('backtest.completed', BacktestCompletedHandler.handle)
    
    # 注册缓存失效处理器
    event_bus.subscribe('cache.invalidated', CacheInvalidatedHandler.handle)
    
    # 注册用户操作处理器（使用模式匹配）
    event_bus.subscribe_pattern('user.*', UserActionHandler.handle)
    
    logger.info("所有事件处理器已注册")
