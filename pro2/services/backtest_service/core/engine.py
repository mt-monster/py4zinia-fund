#!/usr/bin/env python
# coding: utf-8

"""
Core Backtest Execution Engine
核心回测执行引擎

该模块实现了独立的回测执行逻辑，兼容原有的回测引擎功能
"""

import uuid
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio

import pandas as pd
import numpy as np

# 配置日志
logger = logging.getLogger(__name__)


class BacktestStatus(str, Enum):
    """回测状态枚举"""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


@dataclass
class BacktestTask:
    """回测任务数据类"""
    task_id: str
    backtest_type: str
    status: BacktestStatus = BacktestStatus.PENDING
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error_message: str = ''
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'backtest_type': self.backtest_type,
            'status': self.status.value,
            'progress': round(self.progress, 2),
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class BacktestTaskManager:
    """回测任务管理器（线程安全）"""
    
    def __init__(self):
        self._tasks: Dict[str, BacktestTask] = {}
        self._lock = threading.RLock()
        self._active_count = 0
        
    def create_task(self, backtest_type: str) -> str:
        """创建新的回测任务"""
        task_id = str(uuid.uuid4())[:12]
        task = BacktestTask(
            task_id=task_id,
            backtest_type=backtest_type
        )
        
        with self._lock:
            self._tasks[task_id] = task
            
        logger.info(f"创建回测任务: {task_id}, 类型: {backtest_type}")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[BacktestTask]:
        """获取任务"""
        with self._lock:
            return self._tasks.get(task_id)
    
    def update_task_status(
        self, 
        task_id: str, 
        status: BacktestStatus,
        progress: float = None,
        error_message: str = None
    ):
        """更新任务状态"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
                
            old_status = task.status
            task.status = status
            
            if progress is not None:
                task.progress = min(100.0, max(0.0, progress))
            
            if error_message is not None:
                task.error_message = error_message
            
            # 更新时间点
            if status == BacktestStatus.RUNNING and old_status != BacktestStatus.RUNNING:
                task.started_at = datetime.now()
                self._active_count += 1
            elif status in [BacktestStatus.COMPLETED, BacktestStatus.FAILED, BacktestStatus.CANCELLED]:
                if old_status == BacktestStatus.RUNNING:
                    self._active_count = max(0, self._active_count - 1)
                task.completed_at = datetime.now()
    
    def set_task_result(self, task_id: str, result: Dict[str, Any]):
        """设置任务结果"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.result = result
                task.status = BacktestStatus.COMPLETED
                task.progress = 100.0
                task.completed_at = datetime.now()
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            if task.status in [BacktestStatus.COMPLETED, BacktestStatus.FAILED, BacktestStatus.CANCELLED]:
                return False
            
            task.cancel_event.set()
            task.status = BacktestStatus.CANCELLED
            task.completed_at = datetime.now()
            
            if task.status == BacktestStatus.RUNNING:
                self._active_count = max(0, self._active_count - 1)
            
            logger.info(f"任务已取消: {task_id}")
            return True
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理过期任务"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        with self._lock:
            expired_tasks = [
                task_id for task_id, task in self._tasks.items()
                if task.created_at < cutoff_time
            ]
            for task_id in expired_tasks:
                task = self._tasks[task_id]
                if task.status == BacktestStatus.RUNNING:
                    self._active_count = max(0, self._active_count - 1)
                del self._tasks[task_id]
            
            if expired_tasks:
                logger.info(f"清理了 {len(expired_tasks)} 个过期任务")
    
    def get_active_count(self) -> int:
        """获取活跃任务数"""
        with self._lock:
            return self._active_count
    
    def get_all_tasks(self) -> List[BacktestTask]:
        """获取所有任务"""
        with self._lock:
            return list(self._tasks.values())


# 全局任务管理器实例
_task_manager = BacktestTaskManager()


def get_task_manager() -> BacktestTaskManager:
    """获取全局任务管理器"""
    return _task_manager


class BacktestExecutor:
    """回测执行器"""
    
    def __init__(self, task_manager: BacktestTaskManager = None):
        self.task_manager = task_manager or get_task_manager()
        
    def _check_cancelled(self, task: BacktestTask) -> bool:
        """检查任务是否被取消"""
        return task.cancel_event.is_set()
    
    def _run_single_fund_backtest(
        self, 
        task: BacktestTask,
        fund_code: str,
        start_date: str,
        end_date: str,
        base_amount: float,
        initial_cash: float,
        use_unified_strategy: bool
    ) -> Dict[str, Any]:
        """执行单基金回测"""
        try:
            # 导入原有回测引擎
            import sys
            import os
            
            # 添加fund_search到路径
            fund_search_path = os.path.join(
                os.path.dirname(__file__), '..', '..', '..', 'fund_search'
            )
            if fund_search_path not in sys.path:
                sys.path.insert(0, fund_search_path)
            
            from backtesting.core.backtest_engine import FundBacktest
            
            self.task_manager.update_task_status(
                task.task_id, BacktestStatus.RUNNING, progress=10.0
            )
            
            if self._check_cancelled(task):
                raise Exception("任务已取消")
            
            # 创建回测引擎
            backtester = FundBacktest(
                base_amount=base_amount,
                start_date=start_date,
                end_date=end_date,
                initial_cash=initial_cash,
                use_unified_strategy=use_unified_strategy
            )
            
            self.task_manager.update_task_status(
                task.task_id, BacktestStatus.RUNNING, progress=30.0
            )
            
            if self._check_cancelled(task):
                raise Exception("任务已取消")
            
            # 执行回测
            result_df = backtester.backtest_single_fund(fund_code)
            
            if result_df is None:
                raise Exception(f"基金 {fund_code} 回测失败，无法获取数据")
            
            self.task_manager.update_task_status(
                task.task_id, BacktestStatus.RUNNING, progress=60.0
            )
            
            if self._check_cancelled(task):
                raise Exception("任务已取消")
            
            # 计算绩效指标
            metrics = backtester.calculate_performance_metrics(result_df)
            
            if metrics is None:
                raise Exception("计算绩效指标失败")
            
            self.task_manager.update_task_status(
                task.task_id, BacktestStatus.RUNNING, progress=80.0
            )
            
            # 转换结果为字典格式
            daily_values = []
            for _, row in result_df.iterrows():
                daily_values.append({
                    'date': row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                    'total_value_strategy': float(row['total_value_strategy']),
                    'total_value_benchmark': float(row['total_value_benchmark']),
                    'daily_return_strategy': float(row.get('daily_return_strategy', 0)),
                    'daily_return_benchmark': float(row.get('daily_return_benchmark', 0)),
                })
            
            # 构建结果
            result = {
                'task_id': task.task_id,
                'fund_code': fund_code,
                'start_date': start_date,
                'end_date': end_date,
                'total_return': float(metrics.get('总收益率_strategy', 0)),
                'annualized_return': float(metrics.get('年化收益率_strategy', 0)),
                'max_drawdown': float(metrics.get('最大回撤_strategy', 0)),
                'sharpe_ratio': float(metrics.get('夏普比率_strategy', 0)),
                'metrics': {
                    'total_return_strategy': float(metrics.get('总收益率_strategy', 0)),
                    'total_return_benchmark': float(metrics.get('总收益率_benchmark', 0)),
                    'annual_return_strategy': float(metrics.get('年化收益率_strategy', 0)),
                    'annual_return_benchmark': float(metrics.get('年化收益率_benchmark', 0)),
                    'max_drawdown_strategy': float(metrics.get('最大回撤_strategy', 0)),
                    'max_drawdown_benchmark': float(metrics.get('最大回撤_benchmark', 0)),
                    'sharpe_ratio_strategy': float(metrics.get('夏普比率_strategy', 0)),
                    'sharpe_ratio_benchmark': float(metrics.get('夏普比率_benchmark', 0)),
                    'win_rate_strategy': float(metrics.get('胜率_strategy', 0)),
                    'win_rate_benchmark': float(metrics.get('胜率_benchmark', 0)),
                    'annual_volatility_strategy': float(metrics.get('年化波动率_strategy', 0)),
                    'annual_volatility_benchmark': float(metrics.get('年化波动率_benchmark', 0)),
                    'alpha_strategy': float(metrics.get('Alpha_strategy', 0)),
                    'beta_strategy': float(metrics.get('Beta_strategy', 0)),
                    'sortino_ratio_strategy': float(metrics.get('索提诺比率_strategy', 0)),
                    'sortino_ratio_benchmark': float(metrics.get('索提诺比率_benchmark', 0)),
                    'calmar_ratio_strategy': float(metrics.get('卡玛比率_strategy', 0)),
                    'calmar_ratio_benchmark': float(metrics.get('卡玛比率_benchmark', 0)),
                },
                'trades': [],  # 单基金回测暂时不生成详细交易记录
                'daily_values': daily_values,
            }
            
            return result
            
        except Exception as e:
            logger.error(f"单基金回测失败: {str(e)}")
            raise
    
    def _run_portfolio_backtest(
        self,
        task: BacktestTask,
        fund_codes: List[str],
        weights: Optional[List[float]],
        start_date: str,
        end_date: str,
        base_amount: float,
        initial_cash: float,
        use_unified_strategy: bool
    ) -> Dict[str, Any]:
        """执行组合回测"""
        try:
            import sys
            import os
            
            fund_search_path = os.path.join(
                os.path.dirname(__file__), '..', '..', '..', 'fund_search'
            )
            if fund_search_path not in sys.path:
                sys.path.insert(0, fund_search_path)
            
            from backtesting.core.backtest_engine import FundBacktest
            
            self.task_manager.update_task_status(
                task.task_id, BacktestStatus.RUNNING, progress=10.0
            )
            
            if self._check_cancelled(task):
                raise Exception("任务已取消")
            
            # 创建回测引擎
            backtester = FundBacktest(
                base_amount=base_amount,
                start_date=start_date,
                end_date=end_date,
                initial_cash=initial_cash,
                use_unified_strategy=use_unified_strategy
            )
            
            self.task_manager.update_task_status(
                task.task_id, BacktestStatus.RUNNING, progress=30.0
            )
            
            if self._check_cancelled(task):
                raise Exception("任务已取消")
            
            # 执行组合回测
            result_df = backtester.backtest_portfolio(fund_codes, weights)
            
            if result_df is None:
                raise Exception("组合回测失败，无法获取数据")
            
            self.task_manager.update_task_status(
                task.task_id, BacktestStatus.RUNNING, progress=60.0
            )
            
            if self._check_cancelled(task):
                raise Exception("任务已取消")
            
            # 计算绩效指标
            metrics = backtester.calculate_performance_metrics(result_df)
            
            if metrics is None:
                raise Exception("计算绩效指标失败")
            
            self.task_manager.update_task_status(
                task.task_id, BacktestStatus.RUNNING, progress=80.0
            )
            
            # 转换结果为字典格式
            daily_values = []
            for _, row in result_df.iterrows():
                daily_values.append({
                    'date': row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                    'total_value_strategy': float(row['total_value_strategy']),
                    'total_value_benchmark': float(row['total_value_benchmark']),
                    'daily_return_strategy': float(row.get('daily_return_strategy', 0)),
                    'daily_return_benchmark': float(row.get('daily_return_benchmark', 0)),
                })
            
            result = {
                'task_id': task.task_id,
                'fund_codes': fund_codes,
                'weights': weights or [1.0/len(fund_codes)] * len(fund_codes),
                'start_date': start_date,
                'end_date': end_date,
                'total_return': float(metrics.get('总收益率_strategy', 0)),
                'annualized_return': float(metrics.get('年化收益率_strategy', 0)),
                'max_drawdown': float(metrics.get('最大回撤_strategy', 0)),
                'sharpe_ratio': float(metrics.get('夏普比率_strategy', 0)),
                'metrics': {
                    'total_return_strategy': float(metrics.get('总收益率_strategy', 0)),
                    'total_return_benchmark': float(metrics.get('总收益率_benchmark', 0)),
                    'annual_return_strategy': float(metrics.get('年化收益率_strategy', 0)),
                    'annual_return_benchmark': float(metrics.get('年化收益率_benchmark', 0)),
                    'max_drawdown_strategy': float(metrics.get('最大回撤_strategy', 0)),
                    'max_drawdown_benchmark': float(metrics.get('最大回撤_benchmark', 0)),
                    'sharpe_ratio_strategy': float(metrics.get('夏普比率_strategy', 0)),
                    'sharpe_ratio_benchmark': float(metrics.get('夏普比率_benchmark', 0)),
                    'win_rate_strategy': float(metrics.get('胜率_strategy', 0)),
                    'win_rate_benchmark': float(metrics.get('胜率_benchmark', 0)),
                    'annual_volatility_strategy': float(metrics.get('年化波动率_strategy', 0)),
                    'annual_volatility_benchmark': float(metrics.get('年化波动率_benchmark', 0)),
                    'alpha_strategy': float(metrics.get('Alpha_strategy', 0)),
                    'beta_strategy': float(metrics.get('Beta_strategy', 0)),
                    'sortino_ratio_strategy': float(metrics.get('索提诺比率_strategy', 0)),
                    'sortino_ratio_benchmark': float(metrics.get('索提诺比率_benchmark', 0)),
                    'calmar_ratio_strategy': float(metrics.get('卡玛比率_strategy', 0)),
                    'calmar_ratio_benchmark': float(metrics.get('卡玛比率_benchmark', 0)),
                },
                'trades': [],
                'daily_values': daily_values,
            }
            
            return result
            
        except Exception as e:
            logger.error(f"组合回测失败: {str(e)}")
            raise
    
    def execute_backtest(
        self,
        task_id: str,
        backtest_type: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行回测（同步方法）"""
        task = self.task_manager.get_task(task_id)
        if not task:
            raise Exception(f"任务不存在: {task_id}")
        
        try:
            # 设置默认日期
            end_date = params.get('end_date') or datetime.now().strftime('%Y-%m-%d')
            start_date = params.get('start_date') or (
                datetime.now() - timedelta(days=365)
            ).strftime('%Y-%m-%d')
            
            base_amount = params.get('base_amount', 100.0)
            initial_cash = params.get('initial_cash') or base_amount
            use_unified_strategy = params.get('use_unified_strategy', True)
            
            if backtest_type == 'single_fund':
                fund_code = params.get('fund_code')
                if not fund_code:
                    raise Exception("基金代码不能为空")
                
                result = self._run_single_fund_backtest(
                    task, fund_code, start_date, end_date,
                    base_amount, initial_cash, use_unified_strategy
                )
                
            elif backtest_type == 'portfolio':
                fund_codes = params.get('fund_codes', [])
                weights = params.get('weights')
                
                if not fund_codes:
                    raise Exception("基金代码列表不能为空")
                
                result = self._run_portfolio_backtest(
                    task, fund_codes, weights, start_date, end_date,
                    base_amount, initial_cash, use_unified_strategy
                )
            else:
                raise Exception(f"不支持的回测类型: {backtest_type}")
            
            # 保存结果
            self.task_manager.set_task_result(task_id, result)
            logger.info(f"回测任务完成: {task_id}")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"回测任务失败: {task_id}, 错误: {error_msg}")
            self.task_manager.update_task_status(
                task_id, BacktestStatus.FAILED, error_message=error_msg
            )
            raise


# 全局执行器实例
_executor = BacktestExecutor()


def get_executor() -> BacktestExecutor:
    """获取全局执行器"""
    return _executor
