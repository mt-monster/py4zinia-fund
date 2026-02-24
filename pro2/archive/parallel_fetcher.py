#!/usr/bin/env python
# coding: utf-8

"""
并行数据获取服务
提供批量并行数据获取能力，大幅提升数据获取性能
"""

import logging
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class BatchFetchResult:
    """批量获取结果"""
    success_count: int
    fail_count: int
    results: Dict[str, Any]
    errors: Dict[str, str]
    duration_ms: float


class ParallelDataFetcher:
    """
    并行数据获取器
    
    特性：
    - 支持并行获取多只基金数据
    - 支持速率限制
    - 支持失败重试
    - 支持进度回调
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        rate_limit_per_second: float = 10.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        初始化并行数据获取器
        
        Args:
            max_workers: 最大并行工作线程数
            rate_limit_per_second: 每秒最大请求数
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.max_workers = max_workers
        self.rate_limit_per_second = rate_limit_per_second
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self._request_timestamps: List[float] = []
        self._lock = Lock()
        
        logger.info(f"并行数据获取器初始化完成: workers={max_workers}, rate_limit={rate_limit_per_second}/s")
    
    def _wait_for_rate_limit(self):
        """等待以满足速率限制"""
        with self._lock:
            now = time.time()
            min_interval = 1.0 / self.rate_limit_per_second
            
            while self._request_timestamps and now - self._request_timestamps[0] > 1.0:
                self._request_timestamps.pop(0)
            
            if len(self._request_timestamps) >= self.rate_limit_per_second:
                sleep_time = 1.0 - (now - self._request_timestamps[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    now = time.time()
            
            self._request_timestamps.append(now)
    
    def fetch_single(
        self,
        fetch_func: Callable,
        fund_code: str,
        **kwargs
    ) -> Optional[Any]:
        """
        获取单个基金数据（带重试）
        
        Args:
            fetch_func: 数据获取函数
            fund_code: 基金代码
            **kwargs: 传递给获取函数的额外参数
            
        Returns:
            获取的数据或None
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                self._wait_for_rate_limit()
                result = fetch_func(fund_code, **kwargs)
                return result
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    logger.warning(f"基金 {fund_code} 获取失败(尝试 {attempt + 1}/{self.max_retries}): {e}")
        
        logger.error(f"基金 {fund_code} 获取失败，已达最大重试次数: {last_error}")
        return None
    
    def fetch_batch(
        self,
        fund_codes: List[str],
        fetch_func: Callable,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        **kwargs
    ) -> BatchFetchResult:
        """
        批量并行获取基金数据
        
        Args:
            fund_codes: 基金代码列表
            fetch_func: 数据获取函数
            progress_callback: 进度回调函数 (completed, total)
            **kwargs: 传递给获取函数的额外参数
            
        Returns:
            BatchFetchResult: 批量获取结果
        """
        start_time = time.time()
        results: Dict[str, Any] = {}
        errors: Dict[str, str] = {}
        completed = 0
        total = len(fund_codes)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_code = {
                executor.submit(self.fetch_single, fetch_func, code, **kwargs): code
                for code in fund_codes
            }
            
            for future in as_completed(future_to_code):
                fund_code = future_to_code[future]
                try:
                    result = future.result()
                    if result is not None:
                        results[fund_code] = result
                    else:
                        errors[fund_code] = "获取结果为空"
                except Exception as e:
                    errors[fund_code] = str(e)
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
        
        duration_ms = (time.time() - start_time) * 1000
        
        logger.info(f"批量获取完成: 成功={len(results)}, 失败={len(errors)}, 耗时={duration_ms:.0f}ms")
        
        return BatchFetchResult(
            success_count=len(results),
            fail_count=len(errors),
            results=results,
            errors=errors,
            duration_ms=duration_ms
        )
    
    def fetch_batch_with_fallback(
        self,
        fund_codes: List[str],
        primary_func: Callable,
        fallback_func: Optional[Callable] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        **kwargs
    ) -> BatchFetchResult:
        """
        批量获取数据，支持降级到备用数据源
        
        Args:
            fund_codes: 基金代码列表
            primary_func: 主数据源获取函数
            fallback_func: 备用数据源获取函数
            progress_callback: 进度回调函数
            **kwargs: 传递给获取函数的额外参数
            
        Returns:
            BatchFetchResult: 批量获取结果
        """
        start_time = time.time()
        results: Dict[str, Any] = {}
        errors: Dict[str, str] = {}
        
        primary_result = self.fetch_batch(fund_codes, primary_func, None, **kwargs)
        results.update(primary_result.results)
        
        if fallback_func and primary_result.fail_count > 0:
            failed_codes = list(primary_result.errors.keys())
            logger.info(f"尝试使用备用数据源获取 {len(failed_codes)} 只失败基金的数据")
            
            fallback_result = self.fetch_batch(failed_codes, fallback_func, None, **kwargs)
            results.update(fallback_result.results)
            
            for code in failed_codes:
                if code not in fallback_result.results:
                    errors[code] = primary_result.errors.get(code, "主备数据源均获取失败")
        
        duration_ms = (time.time() - start_time) * 1000
        
        return BatchFetchResult(
            success_count=len(results),
            fail_count=len(errors),
            results=results,
            errors=errors,
            duration_ms=duration_ms
        )


class AsyncParallelFetcher:
    """
    异步并行数据获取器
    
    使用asyncio实现更高性能的并发获取
    """
    
    def __init__(
        self,
        max_concurrent: int = 10,
        rate_limit_per_second: float = 20.0
    ):
        """
        初始化异步并行获取器
        
        Args:
            max_concurrent: 最大并发数
            rate_limit_per_second: 每秒最大请求数
        """
        self.max_concurrent = max_concurrent
        self.rate_limit_per_second = rate_limit_per_second
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()
    
    async def _rate_limit(self):
        """异步速率限制"""
        async with self._lock:
            now = time.time()
            min_interval = 1.0 / self.rate_limit_per_second
            elapsed = now - self._last_request_time
            
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            
            self._last_request_time = time.time()
    
    async def fetch_single(
        self,
        fetch_func: Callable,
        fund_code: str,
        **kwargs
    ) -> Optional[Any]:
        """异步获取单个基金数据"""
        async with self._semaphore:
            await self._rate_limit()
            try:
                if asyncio.iscoroutinefunction(fetch_func):
                    return await fetch_func(fund_code, **kwargs)
                else:
                    return fetch_func(fund_code, **kwargs)
            except Exception as e:
                logger.error(f"异步获取基金 {fund_code} 失败: {e}")
                return None
    
    async def fetch_batch(
        self,
        fund_codes: List[str],
        fetch_func: Callable,
        **kwargs
    ) -> Dict[str, Any]:
        """异步批量获取基金数据"""
        tasks = [
            self.fetch_single(fetch_func, code, **kwargs)
            for code in fund_codes
        ]
        
        results = await asyncio.gather(*tasks)
        
        return {
            code: result
            for code, result in zip(fund_codes, results)
            if result is not None
        }


parallel_fetcher = ParallelDataFetcher()
async_fetcher = AsyncParallelFetcher()
