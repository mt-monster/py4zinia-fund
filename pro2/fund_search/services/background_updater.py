#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
后台数据更新服务

系统运行期间自动更新数据，确保缓存始终新鲜。

更新策略：
1. 最新净值：每30分钟更新一次
2. 历史净值：每天收盘后更新
3. 绩效指标：净值更新后自动重算
4. 基金列表：每周更新一次

使用示例:
    # 系统启动时启动后台更新
    updater = BackgroundUpdater()
    updater.start()
    
    # 系统关闭时停止
    updater.stop()
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class UpdateInterval(Enum):
    """更新间隔枚举"""
    REALTIME = 60           # 1分钟
    FREQUENT = 5 * 60       # 5分钟
    NORMAL = 30 * 60        # 30分钟
    DAILY = 24 * 60 * 60    # 1天
    WEEKLY = 7 * 24 * 60 * 60  # 1周


class UpdateTask:
    """更新任务"""
    
    def __init__(self, name: str, interval: int, callback: Callable, 
                 immediate: bool = False, enabled: bool = True):
        """
        初始化更新任务
        
        Args:
            name: 任务名称
            interval: 更新间隔（秒）
            callback: 更新回调函数
            immediate: 是否立即执行一次
            enabled: 是否启用
        """
        self.name = name
        self.interval = interval
        self.callback = callback
        self.immediate = immediate
        self.enabled = enabled
        
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count = 0
        self.error_count = 0
        self.last_error: Optional[str] = None
    
    def should_run(self) -> bool:
        """检查是否应该执行"""
        if not self.enabled:
            return False
        
        if self.next_run is None:
            return self.immediate
        
        return datetime.now() >= self.next_run
    
    def run(self):
        """执行任务"""
        if not self.enabled:
            return
        
        try:
            logger.debug(f"执行任务: {self.name}")
            self.callback()
            self.run_count += 1
            self.last_error = None
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"任务 {self.name} 执行失败: {e}")
        finally:
            self.last_run = datetime.now()
            self.next_run = self.last_run + timedelta(seconds=self.interval)
    
    def get_status(self) -> dict:
        """获取任务状态"""
        return {
            'name': self.name,
            'enabled': self.enabled,
            'interval': self.interval,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'run_count': self.run_count,
            'error_count': self.error_count,
            'last_error': self.last_error
        }


class BackgroundUpdater:
    """
    后台数据更新服务
    
    自动定时更新缓存数据，确保数据新鲜度。
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.tasks: List[UpdateTask] = []
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self._lock = threading.Lock()
        
        # 预加载器引用
        self._preloader = None
        
        # 初始化默认任务
        self._init_default_tasks()
        
        self._initialized = True
        logger.info("BackgroundUpdater 初始化完成")
    
    @property
    def preloader(self):
        """获取预加载器"""
        if self._preloader is None:
            from services.fund_data_preloader import get_preloader
            self._preloader = get_preloader()
        return self._preloader
    
    def _init_default_tasks(self):
        """初始化默认更新任务"""
        # 1. 最新净值更新（每30分钟）
        self.add_task(UpdateTask(
            name="latest_nav_update",
            interval=UpdateInterval.NORMAL.value,
            callback=self._update_latest_nav,
            immediate=False
        ))
        
        # 2. 历史净值更新（每天收盘后）
        self.add_task(UpdateTask(
            name="nav_history_update",
            interval=UpdateInterval.DAILY.value,
            callback=self._update_nav_history,
            immediate=False
        ))
        
        # 3. 绩效指标重算（净值更新后）
        self.add_task(UpdateTask(
            name="performance_recalc",
            interval=UpdateInterval.DAILY.value,
            callback=self._recalc_performance,
            immediate=False
        ))
        
        # 4. 缓存健康检查（每5分钟）
        self.add_task(UpdateTask(
            name="cache_health_check",
            interval=UpdateInterval.FREQUENT.value,
            callback=self._check_cache_health,
            immediate=False
        ))
    
    def add_task(self, task: UpdateTask):
        """添加更新任务"""
        with self._lock:
            self.tasks.append(task)
        logger.info(f"添加更新任务: {task.name}, 间隔: {task.interval}秒")
    
    def remove_task(self, task_name: str):
        """移除更新任务"""
        with self._lock:
            self.tasks = [t for t in self.tasks if t.name != task_name]
        logger.info(f"移除更新任务: {task_name}")
    
    def start(self):
        """启动后台更新服务"""
        if self._running:
            logger.warning("后台更新服务已在运行")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._running = True
        
        logger.info("后台更新服务已启动")
    
    def stop(self):
        """停止后台更新服务"""
        if not self._running:
            return
        
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=5)
        
        self._running = False
        logger.info("后台更新服务已停止")
    
    def _run_loop(self):
        """主循环"""
        logger.info("后台更新循环已启动")
        
        while not self._stop_event.is_set():
            try:
                # 检查并执行到期的任务
                with self._lock:
                    tasks_to_run = [t for t in self.tasks if t.should_run()]
                
                for task in tasks_to_run:
                    task.run()
                
                # 睡眠1秒避免CPU空转
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"后台更新循环出错: {e}")
                time.sleep(5)
        
        logger.info("后台更新循环已结束")
    
    # ============ 默认更新回调 ============
    
    def _update_latest_nav(self):
        """更新最新净值"""
        try:
            logger.info("后台任务: 更新最新净值...")
            
            # 获取所有基金代码
            codes = self._get_all_fund_codes()
            if not codes:
                return
            
            # 批量获取最新净值
            from data_retrieval.optimized_fund_data import OptimizedFundData
            fetcher = OptimizedFundData()
            
            results = fetcher.batch_get_latest_nav(codes[:100])  # 限制数量
            
            # 更新缓存
            for code, data in results.items():
                key = f"fund:latest:{code}"
                self.preloader.cache.set(key, data, 30 * 60)  # 30分钟TTL
            
            logger.info(f"最新净值更新完成: {len(results)} 只基金")
            
        except Exception as e:
            logger.error(f"更新最新净值失败: {e}")
    
    def _update_nav_history(self):
        """更新历史净值"""
        try:
            logger.info("后台任务: 更新历史净值...")
            
            # 只在交易日收盘后执行
            if not self._is_after_market_close():
                logger.debug("还未收盘，跳过历史净值更新")
                return
            
            codes = self._get_all_fund_codes()
            if not codes:
                return
            
            # 分批更新
            from data_retrieval.optimized_fund_data import OptimizedFundData
            fetcher = OptimizedFundData()
            
            # 只更新部分基金（避免一次性更新太多）
            batch_size = 50
            for i in range(0, min(len(codes), 200), batch_size):
                batch = codes[i:i + batch_size]
                results = fetcher.batch_get_fund_nav(batch, days=30)  # 最近30天
                
                for code, df in results.items():
                    if not df.empty:
                        key = f"fund:nav:{code}"
                        data = {
                            'records': df.to_dict('records'),
                            'columns': df.columns.tolist(),
                            'last_date': str(df.iloc[-1]['date']) if 'date' in df.columns else None
                        }
                        self.preloader.cache.set(key, data, 24 * 3600)
                
                time.sleep(1)  # 避免频率限制
            
            logger.info("历史净值更新完成")
            
        except Exception as e:
            logger.error(f"更新历史净值失败: {e}")
    
    def _recalc_performance(self):
        """重新计算绩效指标"""
        try:
            logger.info("后台任务: 重新计算绩效指标...")
            
            codes = self._get_all_fund_codes()
            if not codes:
                return
            
            for code in codes[:100]:  # 限制数量
                try:
                    # 获取历史数据
                    hist_key = f"fund:nav:{code}"
                    hist_data = self.preloader.cache.get(hist_key)
                    
                    if hist_data:
                        # 重新计算
                        metrics = self.preloader._calculate_metrics(hist_data['records'])
                        perf_key = f"fund:perf:{code}"
                        self.preloader.cache.set(perf_key, metrics, 24 * 3600)
                        
                except Exception as e:
                    logger.debug(f"计算 {code} 绩效指标失败: {e}")
            
            logger.info("绩效指标重算完成")
            
        except Exception as e:
            logger.error(f"重算绩效指标失败: {e}")
    
    def _check_cache_health(self):
        """检查缓存健康状态"""
        try:
            stats = self.preloader.get_cache_stats()
            
            # 如果缓存命中率过低，可能需要调整
            hit_rate_str = stats.get('hit_rate', '0%')
            hit_rate = float(hit_rate_str.replace('%', ''))
            
            if hit_rate < 50 and stats.get('access_count', 0) > 100:
                logger.warning(f"缓存命中率较低: {hit_rate}%，建议检查缓存策略")
            
            # 如果缓存已满，清理过期数据
            if stats.get('size', 0) >= stats.get('max_size', 10000) * 0.9:
                logger.info("缓存接近上限，执行清理...")
                self.preloader.cache._cleanup_lru(500)
            
        except Exception as e:
            logger.error(f"缓存健康检查失败: {e}")
    
    def _get_all_fund_codes(self) -> List[str]:
        """获取市场上所有真实的场外开放式基金代码"""
        try:
            import akshare as ak
            
            # 优先使用场外基金列表
            try:
                fund_df = ak.fund_open_fund_daily_em()
                if not fund_df.empty and '基金代码' in fund_df.columns:
                    codes = fund_df['基金代码'].unique().tolist()
                    valid_codes = [c for c in codes if isinstance(c, str) and len(c) == 6 and c.isdigit()]
                    return valid_codes
            except Exception:
                pass
            
            # 备用方案
            fund_list = ak.fund_name_em()
            codes = fund_list['基金代码'].unique().tolist()
            valid_codes = [c for c in codes if isinstance(c, str) and len(c) == 6 and c.isdigit()]
            # 过滤场内基金代码
            otc_codes = [c for c in valid_codes if not c.startswith(('51', '15', '16', '50', '18'))]
            return otc_codes
            
        except Exception as e:
            logger.warning(f"获取基金列表失败: {e}")
            return []
    
    def _is_after_market_close(self) -> bool:
        """检查是否已收盘"""
        now = datetime.now()
        # 简单判断：下午3点后认为是收盘后
        return now.hour >= 15
    
    # ============ 公共接口 ============
    
    def force_update(self, task_name: Optional[str] = None):
        """
        强制立即更新
        
        Args:
            task_name: 任务名称，None表示所有任务
        """
        with self._lock:
            tasks = [t for t in self.tasks if task_name is None or t.name == task_name]
        
        for task in tasks:
            logger.info(f"强制执行任务: {task.name}")
            task.run()
    
    def get_status(self) -> dict:
        """获取服务状态"""
        with self._lock:
            return {
                'running': self._running,
                'tasks': [t.get_status() for t in self.tasks]
            }
    
    def is_running(self) -> bool:
        """检查服务是否运行中"""
        return self._running


# 全局实例
_updater_instance: Optional[BackgroundUpdater] = None


def get_background_updater() -> BackgroundUpdater:
    """获取全局后台更新器"""
    global _updater_instance
    if _updater_instance is None:
        _updater_instance = BackgroundUpdater()
    return _updater_instance


def start_background_update():
    """便捷函数：启动后台更新"""
    updater = get_background_updater()
    updater.start()
    return updater


def stop_background_update():
    """便捷函数：停止后台更新"""
    updater = get_background_updater()
    updater.stop()


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("后台更新服务测试")
    print("=" * 60)
    
    updater = BackgroundUpdater()
    
    # 添加测试任务
    def test_task():
        print(f"测试任务执行: {datetime.now()}")
    
    updater.add_task(UpdateTask(
        name="test",
        interval=5,  # 5秒
        callback=test_task,
        immediate=True
    ))
    
    # 启动服务
    print("\n启动后台更新服务...")
    updater.start()
    
    # 运行30秒
    print("运行30秒...")
    time.sleep(30)
    
    # 停止服务
    print("\n停止后台更新服务...")
    updater.stop()
    
    # 显示状态
    print(f"\n服务状态: {updater.get_status()}")
    
    print("\n测试完成")
