#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
回测引擎服务核心

实现回测引擎的独立服务逻辑，与原系统解耦。
"""

import os
import sys
import json
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


@dataclass
class BacktestTask:
    """回测任务"""
    task_id: str
    strategy_id: str
    user_id: str
    start_date: str
    end_date: str
    initial_capital: float
    rebalance_freq: str
    status: TaskStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: float = 0.0
    result: Optional[Dict] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'task_id': self.task_id,
            'strategy_id': self.strategy_id,
            'user_id': self.user_id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_capital': self.initial_capital,
            'rebalance_freq': self.rebalance_freq,
            'status': self.status.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'progress': self.progress,
            'result': self.result,
            'error': self.error
        }


class BacktestService:
    """
    回测引擎服务
    
    独立的回测服务，支持REST和gRPC接口。
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
        
        self._tasks: Dict[str, BacktestTask] = {}
        self._db_manager = None
        self._strategy_engine = None
        self._evaluator = None
        
        self._initialized = True
        logger.info("回测引擎服务初始化完成")
    
    def init_components(self, db_config: Dict = None):
        """
        初始化组件
        
        Args:
            db_config: 数据库配置
        """
        try:
            from data_access.enhanced_database import EnhancedDatabaseManager
            from backtesting.core.unified_strategy_engine import UnifiedStrategyEngine
            from backtesting.analysis.strategy_evaluator import StrategyEvaluator
            
            if db_config is None:
                from shared.config_manager import config_manager
                config = config_manager.get_database_config()
                db_config = {
                    'host': config.host,
                    'user': config.user,
                    'password': config.password,
                    'database': config.database,
                    'port': config.port,
                    'charset': config.charset
                }
            
            self._db_manager = EnhancedDatabaseManager(db_config)
            self._strategy_engine = UnifiedStrategyEngine()
            self._evaluator = StrategyEvaluator()
            
            logger.info("回测服务组件初始化完成")
            
        except Exception as e:
            logger.error(f"初始化组件失败: {e}")
            raise
    
    def create_task(self, strategy_id: str, user_id: str,
                    start_date: str, end_date: str,
                    initial_capital: float = 100000.0,
                    rebalance_freq: str = 'monthly') -> BacktestTask:
        """
        创建回测任务
        
        Args:
            strategy_id: 策略ID
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
            rebalance_freq: 再平衡频率
            
        Returns:
            BacktestTask: 创建的任务
        """
        task = BacktestTask(
            task_id=str(uuid.uuid4()),
            strategy_id=strategy_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            rebalance_freq=rebalance_freq,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        
        self._tasks[task.task_id] = task
        logger.info(f"创建回测任务: {task.task_id}")
        
        return task
    
    def run_task(self, task_id: str) -> bool:
        """
        执行任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功启动
        """
        task = self._tasks.get(task_id)
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return False
        
        if task.status != TaskStatus.PENDING:
            logger.warning(f"任务状态不允许执行: {task.status}")
            return False
        
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().isoformat()
            
            logger.info(f"开始执行回测任务: {task_id}")
            
            # 执行回测
            result = self._execute_backtest(task)
            
            if result.get('success'):
                task.status = TaskStatus.COMPLETED
                task.result = result.get('data')
                task.progress = 100.0
                
                # 触发完成事件
                self._emit_completed_event(task)
                
            else:
                task.status = TaskStatus.FAILED
                task.error = result.get('error', '未知错误')
                
            task.completed_at = datetime.now().isoformat()
            
            logger.info(f"回测任务完成: {task_id}, 状态: {task.status.value}")
            return True
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now().isoformat()
            logger.error(f"执行回测任务失败: {e}")
            return False
    
    def _execute_backtest(self, task: BacktestTask) -> Dict:
        """
        执行回测逻辑
        
        Args:
            task: 回测任务
            
        Returns:
            Dict: 回测结果
        """
        try:
            from backtesting.core.backtest_api import BacktestAPIHandler
            
            handler = BacktestAPIHandler(
                db_manager=self._db_manager,
                fund_data_manager=None
            )
            
            success, result = handler.run_backtest(
                strategy_id=task.strategy_id,
                user_id=task.user_id,
                start_date=task.start_date,
                end_date=task.end_date,
                initial_capital=task.initial_capital,
                rebalance_freq=task.rebalance_freq
            )
            
            return {'success': success, 'data': result if success else None, 'error': None if success else result.get('error')}
            
        except Exception as e:
            logger.error(f"执行回测失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _emit_completed_event(self, task: BacktestTask):
        """触发回测完成事件"""
        try:
            from messaging.event_bus import EventBus
            event_bus = EventBus()
            event_bus.emit('backtest.completed', {
                'task_id': task.task_id,
                'strategy_id': task.strategy_id,
                'user_id': task.user_id,
                'success': task.status == TaskStatus.COMPLETED,
                'error': task.error
            })
        except Exception as e:
            logger.error(f"触发事件失败: {e}")
    
    def get_task(self, task_id: str) -> Optional[BacktestTask]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        task = self._tasks.get(task_id)
        if not task:
            return None
        return task.to_dict()
    
    def get_task_result(self, task_id: str) -> Optional[Dict]:
        """获取任务结果"""
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        return {
            'task': task.to_dict(),
            'result': task.result,
            'trades': task.result.get('trades', []) if task.result else [],
            'summary': task.result.get('summary', {}) if task.result else {}
        }
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            return False
        
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now().isoformat()
        logger.info(f"任务已取消: {task_id}")
        
        return True
    
    def list_tasks(self, user_id: str = None, status: str = None) -> List[Dict]:
        """
        列出任务
        
        Args:
            user_id: 用户ID过滤
            status: 状态过滤
            
        Returns:
            List[Dict]: 任务列表
        """
        tasks = self._tasks.values()
        
        if user_id:
            tasks = [t for t in tasks if t.user_id == user_id]
        
        if status:
            tasks = [t for t in tasks if t.status.value == status]
        
        # 按创建时间倒序
        tasks = sorted(tasks, key=lambda t: t.created_at, reverse=True)
        
        return [t.to_dict() for t in tasks]
    
    def get_stats(self) -> Dict:
        """获取服务统计信息"""
        total = len(self._tasks)
        pending = sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING)
        running = sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)
        completed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED)
        
        return {
            'total_tasks': total,
            'pending': pending,
            'running': running,
            'completed': completed,
            'failed': failed,
            'initialized': self._initialized
        }


# 全局服务实例
_service_instance: Optional[BacktestService] = None


def get_service() -> BacktestService:
    """获取服务实例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = BacktestService()
    return _service_instance
