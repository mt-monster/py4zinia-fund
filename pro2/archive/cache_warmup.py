#!/usr/bin/env python
# coding: utf-8

"""
缓存预热服务
在应用启动时预先加载热点数据到缓存
"""

import logging
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class WarmupTask:
    """预热任务"""
    name: str
    func: Callable
    priority: int = 0
    timeout: int = 60
    enabled: bool = True


@dataclass
class WarmupResult:
    """预热结果"""
    task_name: str
    success: bool
    duration_ms: float
    items_cached: int
    error: Optional[str] = None


class CacheWarmupService:
    """
    缓存预热服务
    
    功能：
    - 应用启动时预热热点数据
    - 支持优先级排序
    - 支持并行预热
    - 支持失败重试
    """
    
    def __init__(self, max_workers: int = 4):
        """
        初始化缓存预热服务
        
        Args:
            max_workers: 最大并行工作线程数
        """
        self.max_workers = max_workers
        self.tasks: List[WarmupTask] = []
        self.results: List[WarmupResult] = []
        self._is_warmed_up = False
    
    def register_task(
        self,
        name: str,
        func: Callable,
        priority: int = 0,
        timeout: int = 60,
        enabled: bool = True
    ):
        """
        注册预热任务
        
        Args:
            name: 任务名称
            func: 预热函数，应返回缓存的条目数
            priority: 优先级（数值越大越优先）
            timeout: 超时时间（秒）
            enabled: 是否启用
        """
        task = WarmupTask(
            name=name,
            func=func,
            priority=priority,
            timeout=timeout,
            enabled=enabled
        )
        self.tasks.append(task)
        logger.info(f"注册预热任务: {name}, 优先级={priority}")
    
    def _execute_task(self, task: WarmupTask) -> WarmupResult:
        """执行单个预热任务"""
        start_time = time.time()
        
        try:
            items_cached = task.func()
            duration_ms = (time.time() - start_time) * 1000
            
            logger.info(f"预热任务 {task.name} 完成: 缓存 {items_cached} 条, 耗时 {duration_ms:.0f}ms")
            
            return WarmupResult(
                task_name=task.name,
                success=True,
                duration_ms=duration_ms,
                items_cached=items_cached or 0
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"预热任务 {task.name} 失败: {e}")
            
            return WarmupResult(
                task_name=task.name,
                success=False,
                duration_ms=duration_ms,
                items_cached=0,
                error=str(e)
            )
    
    def warmup(self, parallel: bool = True) -> List[WarmupResult]:
        """
        执行缓存预热
        
        Args:
            parallel: 是否并行执行
            
        Returns:
            预热结果列表
        """
        if self._is_warmed_up:
            logger.info("缓存已预热，跳过")
            return self.results
        
        enabled_tasks = [t for t in self.tasks if t.enabled]
        enabled_tasks.sort(key=lambda x: x.priority, reverse=True)
        
        if not enabled_tasks:
            logger.info("没有启用的预热任务")
            return []
        
        logger.info(f"开始缓存预热，共 {len(enabled_tasks)} 个任务")
        start_time = time.time()
        
        if parallel and len(enabled_tasks) > 1:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self._execute_task, task) for task in enabled_tasks]
                self.results = [f.result() for f in futures]
        else:
            self.results = [self._execute_task(task) for task in enabled_tasks]
        
        total_duration = (time.time() - start_time) * 1000
        success_count = sum(1 for r in self.results if r.success)
        total_items = sum(r.items_cached for r in self.results)
        
        logger.info(
            f"缓存预热完成: 成功 {success_count}/{len(enabled_tasks)} 个任务, "
            f"共缓存 {total_items} 条数据, 总耗时 {total_duration:.0f}ms"
        )
        
        self._is_warmed_up = True
        return self.results
    
    def get_status(self) -> Dict[str, Any]:
        """获取预热状态"""
        return {
            'is_warmed_up': self._is_warmed_up,
            'total_tasks': len(self.tasks),
            'enabled_tasks': len([t for t in self.tasks if t.enabled]),
            'results': [
                {
                    'task_name': r.task_name,
                    'success': r.success,
                    'duration_ms': r.duration_ms,
                    'items_cached': r.items_cached,
                    'error': r.error
                }
                for r in self.results
            ]
        }


def create_default_warmup_tasks(
    db_manager,
    cache_manager=None,
    fund_data_manager=None
) -> List[WarmupTask]:
    """
    创建默认的预热任务
    
    Args:
        db_manager: 数据库管理器
        cache_manager: 缓存管理器
        fund_data_manager: 基金数据管理器
        
    Returns:
        预热任务列表
    """
    tasks = []
    
    def warmup_top_funds():
        """预热热门基金数据"""
        sql = """
        SELECT fund_code, fund_name, composite_score, today_return, sharpe_ratio
        FROM fund_analysis_results
        WHERE analysis_date = (SELECT MAX(analysis_date) FROM fund_analysis_results)
        ORDER BY composite_score DESC
        LIMIT 100
        """
        df = db_manager.execute_query(sql)
        if cache_manager:
            for _, row in df.iterrows():
                cache_key = f"fund:{row['fund_code']}"
                cache_manager.set(cache_key, row.to_dict(), ttl=3600)
        return len(df)
    
    def warmup_user_holdings():
        """预热用户持仓数据"""
        sql = """
        SELECT h.fund_code, h.holding_shares, h.cost_price, h.holding_amount,
               f.fund_name, f.current_estimate
        FROM user_holdings h
        LEFT JOIN fund_analysis_results f ON h.fund_code = f.fund_code
            AND f.analysis_date = (SELECT MAX(analysis_date) FROM fund_analysis_results)
        WHERE h.user_id = 'default_user'
        """
        df = db_manager.execute_query(sql)
        if cache_manager:
            cache_manager.set('user_holdings:default_user', df.to_dict('records'), ttl=300)
        return len(df)
    
    def warmup_fund_types():
        """预热基金类型数据"""
        sql = """
        SELECT DISTINCT fund_code, fund_name
        FROM fund_analysis_results
        WHERE analysis_date = (SELECT MAX(analysis_date) FROM fund_analysis_results)
        """
        df = db_manager.execute_query(sql)
        if cache_manager:
            cache_manager.set('fund_list:all', df.to_dict('records'), ttl=86400)
        return len(df)
    
    tasks.append(WarmupTask(
        name='warmup_top_funds',
        func=warmup_top_funds,
        priority=10,
        enabled=True
    ))
    
    tasks.append(WarmupTask(
        name='warmup_user_holdings',
        func=warmup_user_holdings,
        priority=8,
        enabled=True
    ))
    
    tasks.append(WarmupTask(
        name='warmup_fund_types',
        func=warmup_fund_types,
        priority=5,
        enabled=True
    ))
    
    return tasks


warmup_service = CacheWarmupService()
