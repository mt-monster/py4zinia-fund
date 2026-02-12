#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金数据预加载服务

系统启动前预加载用户持仓基金数据到内存缓存，确保用户打开系统后几秒内看到所有持仓数据。

预加载策略：
1. 只预加载用户持仓的基金（个性化）
2. 静态数据（基金基本信息）：启动时加载，缓存7天
3. 准静态数据（历史净值）：启动时加载最近2年数据，缓存1天
4. 动态数据（最新净值）：启动时加载，每30分钟更新
5. 实时数据（今日收益率）：用户访问时实时计算

使用示例:
    # 系统启动时
    preloader = FundDataPreloader()
    preloader.preload_all()  # 预加载用户持仓基金数据
    
    # 用户请求时（几毫秒内返回）
    data = preloader.get_fund_data('000001')  # 从内存缓存获取
"""

import os
import pandas as pd
import numpy as np
import logging
import threading
import time
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class PreloadConfig:
    """预加载配置"""
    # 预加载的基金代码列表
    # None 表示自动获取（优先从用户持仓获取，如无持仓则不预加载）
    fund_codes: Optional[List[str]] = None
    
    # 历史数据天数
    history_days: int = 730  # 2年
    
    # 并行线程数
    max_workers: int = 3
    
    # 是否启用全量预加载（True=加载市场全部基金，False=只加载fund_codes指定的）
    enable_full_preload: bool = True
    
    # 最大预加载基金数量（0表示无限制，默认2000只作为保护）
    max_funds: int = 2000
    
    # 内存缓存最大条目数
    max_cache_size: int = 50000  # 支持更多基金
    
    # 预加载超时时间（秒）
    preload_timeout: int = 600  # 10分钟


class MemoryCacheManager:
    """
    内存缓存管理器 - 兼容层
    
    已重构：使用 services.cache.memory_cache 作为后端实现
    保留此类以维持向后兼容性
    
    高性能内存缓存，支持TTL和LRU淘汰
    """
    
    def __init__(self, max_size: int = 10000):
        # 使用标准缓存作为后端
        from services.cache.memory_cache import MemoryCache
        self._backend = MemoryCache(max_size=max_size)
        self._max_size = max_size
        
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        return self._backend.get(key)
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """设置缓存数据"""
        self._backend.set(key, value, ttl=ttl_seconds)
    
    def mget(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取"""
        results = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                results[key] = value
        return results
    
    def mset(self, data_dict: Dict[str, Any], ttl_seconds: int = 3600):
        """批量设置"""
        for key, value in data_dict.items():
            self.set(key, value, ttl_seconds)
    
    def clear(self):
        """清空缓存"""
        self._backend.clear()
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = self._backend.get_stats()
        return {
            'size': stats.get('size', 0),
            'max_size': self._max_size,
            'access_count': stats.get('hits', 0) + stats.get('misses', 0),
            'hit_count': stats.get('hits', 0),
            'hit_rate': f"{stats.get('hit_rate', 0) * 100:.1f}%"
        }


class FundDataPreloader:
    """
    基金数据预加载服务
    
    负责系统启动前预加载所有必要数据到内存缓存
    """
    
    # 缓存键前缀
    KEY_PREFIX = {
        'basic_info': 'fund:basic',      # 基金基本信息
        'nav_history': 'fund:nav',       # 历史净值
        'latest_nav': 'fund:latest',     # 最新净值
        'performance': 'fund:perf',      # 绩效指标
        'qdii_flag': 'fund:qdii',        # QDII标识
        'profit_trend': 'fund:profit',   # 收益趋势数据
    }
    
    # 缓存TTL配置（秒）
    CACHE_TTL = {
        'basic_info': 7 * 24 * 3600,     # 7天
        'nav_history': 24 * 3600,        # 1天
        'latest_nav': 30 * 60,           # 30分钟
        'performance': 24 * 3600,        # 1天
        'qdii_flag': 7 * 24 * 3600,      # 7天
        'profit_trend': 60 * 60,         # 1小时（收益趋势变化较快）
    }
    
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
        
        self.config = PreloadConfig()
        self.cache = MemoryCacheManager(max_size=self.config.max_cache_size)
        
        # 数据获取器（延迟初始化）
        self._fetcher = None
        self._db_manager = None
        
        # 预加载状态
        self._preload_status = {
            'started': False,
            'completed': False,
            'progress': 0.0,
            'last_preload': None,
            'error': None
        }
        
        self._lock = threading.RLock()
        self._initialized = True
        
        logger.info("FundDataPreloader 初始化完成")
    
    @property
    def fetcher(self):
        """延迟初始化数据获取器"""
        if self._fetcher is None:
            from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
            # MultiSourceDataAdapter 会自动从配置读取 Tushare token
            self._fetcher = MultiSourceDataAdapter()
        return self._fetcher
    
    def preload_all(self, fund_codes: Optional[List[str]] = None, 
                   async_mode: bool = False) -> bool:
        """
        预加载所有数据
        
        Args:
            fund_codes: 要预加载的基金代码列表，None表示自动获取全部
            async_mode: 是否异步执行（后台线程）
            
        Returns:
            bool: 是否成功启动预加载
        """
        if async_mode:
            thread = threading.Thread(
                target=self._preload_all_sync,
                args=(fund_codes,),
                daemon=True
            )
            thread.start()
            logger.info("预加载任务已在后台启动")
            return True
        else:
            return self._preload_all_sync(fund_codes)
    
    def _preload_all_sync(self, fund_codes: Optional[List[str]] = None) -> bool:
        """同步预加载所有数据"""
        with self._lock:
            self._preload_status['started'] = True
            self._preload_status['completed'] = False
            self._preload_status['progress'] = 0.0
            self._preload_status['error'] = None
        
        try:
            start_time = time.time()
            logger.info("=" * 60)
            logger.info("开始预加载基金数据")
            logger.info("=" * 60)
            
            # 1. 获取基金代码列表
            if fund_codes is None:
                fund_codes = self._get_all_fund_codes()
            
            # 根据配置限制数量
            if self.config.max_funds > 0 and len(fund_codes) > self.config.max_funds:
                logger.info(f"基金数量 {len(fund_codes)} 超过限制 {self.config.max_funds}，将只加载前 {self.config.max_funds} 只")
                fund_codes = fund_codes[:self.config.max_funds]
            
            total = len(fund_codes)
            logger.info(f"需要预加载 {total} 只基金的数据")
            
            # 2. 预加载基金基本信息（静态数据）
            self._update_progress(0.1, "加载基金基本信息...")
            self._preload_basic_info(fund_codes)
            
            # 3. 预加载QDII标识
            self._update_progress(0.2, "加载QDII标识...")
            self._preload_qdii_flags(fund_codes)
            
            # 4. 预加载最新净值（批量）
            self._update_progress(0.3, "加载最新净值...")
            self._preload_latest_nav(fund_codes)
            
            # 5. 预加载历史净值（分批）
            self._update_progress(0.5, "加载历史净值...")
            self._preload_nav_history(fund_codes)
            
            # 6. 预计算绩效指标
            self._update_progress(0.85, "计算绩效指标...")
            self._preload_performance(fund_codes)
            
            # 7. 预计算收益趋势数据
            self._update_progress(0.95, "计算收益趋势...")
            self._preload_profit_trend()
            
            # 完成
            elapsed = time.time() - start_time
            self._update_progress(1.0, "预加载完成")
            
            with self._lock:
                self._preload_status['completed'] = True
                self._preload_status['last_preload'] = datetime.now()
            
            logger.info("=" * 60)
            logger.info(f"预加载完成！共 {total} 只基金，耗时 {elapsed:.1f} 秒")
            logger.info(f"内存缓存: {self.cache.get_stats()}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"预加载失败: {e}", exc_info=True)
            with self._lock:
                self._preload_status['error'] = str(e)
            return False
    
    def _get_user_holdings_fund_codes(self) -> List[str]:
        """
        获取用户持仓中的基金代码
        
        从数据库读取用户的持仓基金列表，优先预加载这些基金
        
        Returns:
            List[str]: 用户持仓的基金代码列表
        """
        # 尝试从数据库获取用户持仓
        try:
            from data_retrieval.enhanced_database import EnhancedDatabaseManager
            
            # 尝试连接数据库
            db_config = self._get_db_config()
            if db_config:
                db = EnhancedDatabaseManager(db_config)
                
                try:
                    # 查询 user_holdings 表
                    sql = """
                    SELECT DISTINCT fund_code 
                    FROM user_holdings 
                    WHERE user_id = 'default_user' OR user_id IS NULL
                    ORDER BY fund_code
                    """
                    
                    try:
                        result = db.execute_query(sql)
                        if not result.empty and 'fund_code' in result.columns:
                            codes = result['fund_code'].tolist()
                            # 过滤有效的基金代码
                            valid_codes = [c for c in codes if isinstance(c, str) and len(c) == 6 and c.isdigit()]
                            if valid_codes:
                                logger.info(f"从数据库获取到 {len(valid_codes)} 只用户持仓基金")
                                return valid_codes
                    except Exception as e:
                        logger.debug(f"查询 user_holdings 表失败: {e}")
                    
                    # 尝试 user_holdings 表
                    sql2 = """
                    SELECT DISTINCT fund_code 
                    FROM user_holdings 
                    WHERE user_id = 'default_user' OR user_id IS NULL
                    ORDER BY fund_code
                    """
                    
                    try:
                        result = db.execute_query(sql2)
                        if not result.empty and 'fund_code' in result.columns:
                            codes = result['fund_code'].tolist()
                            valid_codes = [c for c in codes if isinstance(c, str) and len(c) == 6 and c.isdigit()]
                            if valid_codes:
                                logger.info(f"从数据库获取到 {len(valid_codes)} 只用户持仓基金")
                                return valid_codes
                    except Exception as e:
                        logger.debug(f"查询 user_holdings 表失败: {e}")
                    
                finally:
                    # 确保关闭数据库连接
                    try:
                        db.close()
                    except Exception:
                        pass
                    
        except Exception as e:
            logger.debug(f"数据库查询失败: {e}")
        
        # 尝试从本地存储读取（如JSON文件）
        try:
            import json
            holdings_file = 'user_holdings.json'
            if os.path.exists(holdings_file):
                with open(holdings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        codes = [h.get('fund_code') for h in data if h.get('fund_code')]
                        valid_codes = [c for c in codes if isinstance(c, str) and len(c) == 6 and c.isdigit()]
                        if valid_codes:
                            logger.info(f"从本地文件获取到 {len(valid_codes)} 只用户持仓基金")
                            return valid_codes
        except Exception as e:
            logger.debug(f"读取本地持仓文件失败: {e}")
        
        logger.info("未发现用户持仓基金")
        return []
    def _get_db_config(self) -> Optional[Dict]:
        """获取数据库配置"""
        try:
            from shared.config_manager import config_manager
            db_config = config_manager.get_database_config()
            return {
                'host': db_config.host,
                'user': db_config.user,
                'password': db_config.password,
                'database': db_config.database,
                'port': db_config.port,
                'charset': db_config.charset
            }
        except Exception as e:
            logger.debug(f"获取数据库配置失败: {e}")
            return None
    
    def _get_all_fund_codes(self) -> List[str]:
        """
        获取基金代码列表
        
        优先级：
        1. 用户持仓基金（优先）
        2. 如果无持仓，返回空列表（不预加载其他基金）
        """
        # 首先尝试获取用户持仓基金
        user_holdings = self._get_user_holdings_fund_codes()
        if user_holdings:
            logger.info(f"将预加载用户持仓的 {len(user_holdings)} 只基金")
            return user_holdings
        
        # 如果没有持仓，返回空列表（不预加载）
        logger.info("用户暂无持仓基金，跳过预加载")
        return []
    
    def _preload_basic_info(self, fund_codes: List[str]):
        """预加载基金基本信息"""
        logger.info(f"预加载 {len(fund_codes)} 只基金的基本信息...")
        
        loaded_count = 0
        
        # 逐个获取基金基本信息
        for code in fund_codes:
            try:
                info = self.fetcher.get_fund_basic_info(code)
                if info and info.get('fund_name'):
                    key = f"{self.KEY_PREFIX['basic_info']}:{code}"
                    self.cache.set(key, info, self.CACHE_TTL['basic_info'])
                    loaded_count += 1
                else:
                    # 如果获取失败，使用基金代码作为名称
                    key = f"{self.KEY_PREFIX['basic_info']}:{code}"
                    self.cache.set(key, {
                        'fund_code': code,
                        'fund_name': f'基金{code}',
                        'fund_type': '未知',
                        'fund_company': '未知'
                    }, self.CACHE_TTL['basic_info'])
            except Exception as e:
                logger.debug(f"获取基金 {code} 基本信息失败: {e}")
                # 使用默认值
                key = f"{self.KEY_PREFIX['basic_info']}:{code}"
                self.cache.set(key, {
                    'fund_code': code,
                    'fund_name': f'基金{code}',
                    'fund_type': '未知',
                    'fund_company': '未知'
                }, self.CACHE_TTL['basic_info'])
        
        logger.info(f"基金基本信息预加载完成: {loaded_count}/{len(fund_codes)} 只基金")
    
    def _preload_qdii_flags(self, fund_codes: List[str]):
        """预加载QDII标识"""
        logger.info(f"预加载 {len(fund_codes)} 只基金的QDII标识...")
        
        try:
            from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
            
            for code in fund_codes:
                is_qdii = MultiSourceDataAdapter.is_qdii_fund(code)
                key = f"{self.KEY_PREFIX['qdii_flag']}:{code}"
                self.cache.set(key, is_qdii, self.CACHE_TTL['qdii_flag'])
            
            logger.info("QDII标识预加载完成")
            
        except Exception as e:
            logger.error(f"预加载QDII标识失败: {e}")
    
    def _preload_latest_nav(self, fund_codes: List[str]):
        """预加载最新净值"""
        logger.info(f"预加载 {len(fund_codes)} 只基金的最新净值...")
        
        try:
            # 使用批量接口
            results = self.fetcher.batch_get_latest_nav(fund_codes)
            
            for code, data in results.items():
                key = f"{self.KEY_PREFIX['latest_nav']}:{code}"
                self.cache.set(key, data, self.CACHE_TTL['latest_nav'])
            
            logger.info(f"最新净值预加载完成: {len(results)} 只基金")
            
        except Exception as e:
            logger.error(f"预加载最新净值失败: {e}")
    
    def _preload_nav_history(self, fund_codes: List[str]):
        """预加载历史净值"""
        logger.info(f"预加载 {len(fund_codes)} 只基金的历史净值（最近{self.config.history_days}天）...")
        
        batch_size = 50  # 每批处理50只
        total_batches = (len(fund_codes) + batch_size - 1) // batch_size
        
        for i in range(0, len(fund_codes), batch_size):
            batch = fund_codes[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            try:
                # 批量获取
                results = self.fetcher.batch_get_fund_nav(batch)
                
                for code, df in results.items():
                    if not df.empty:
                        key = f"{self.KEY_PREFIX['nav_history']}:{code}"
                        # 将DataFrame转换为更紧凑的格式存储
                        data = {
                            'records': df.to_dict('records'),
                            'columns': df.columns.tolist(),
                            'last_date': str(df.iloc[-1]['date']) if 'date' in df.columns else None
                        }
                        self.cache.set(key, data, self.CACHE_TTL['nav_history'])
                
                # 更新进度
                progress = 0.5 + (batch_num / total_batches) * 0.3
                self._update_progress(progress, f"加载历史净值 ({batch_num}/{total_batches})...")
                
            except Exception as e:
                logger.warning(f"批量 {batch_num} 加载失败: {e}")
        
        logger.info("历史净值预加载完成")
    
    def _preload_performance(self, fund_codes: List[str]):
        """预计算绩效指标"""
        logger.info(f"预计算 {len(fund_codes)} 只基金的绩效指标...")
        
        for code in fund_codes:
            try:
                # 从历史数据计算绩效指标
                hist_key = f"{self.KEY_PREFIX['nav_history']}:{code}"
                hist_data = self.cache.get(hist_key)
                
                if hist_data:
                    # 计算绩效指标
                    metrics = self._calculate_metrics(hist_data['records'])
                    key = f"{self.KEY_PREFIX['performance']}:{code}"
                    self.cache.set(key, metrics, self.CACHE_TTL['performance'])
                    
            except Exception as e:
                logger.debug(f"计算 {code} 绩效指标失败: {e}")
        
        logger.info("绩效指标预计算完成")
    
    def _calculate_metrics(self, records: List[Dict]) -> Dict:
        """计算绩效指标"""
        try:
            if len(records) < 2:
                return {}
            
            # 提取净值序列
            navs = [r.get('nav', r.get('单位净值', 0)) for r in records if r.get('nav') or r.get('单位净值')]
            
            if len(navs) < 2:
                return {}
            
            navs = pd.Series(navs)
            
            # 计算收益率
            returns = navs.pct_change().dropna()
            
            # 计算指标
            total_return = (navs.iloc[-1] - navs.iloc[0]) / navs.iloc[0] if navs.iloc[0] > 0 else 0
            
            # 年化收益率（假设250个交易日）
            years = len(navs) / 250
            annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
            
            # 波动率
            volatility = returns.std() * np.sqrt(250)
            
            # 夏普比率（假设无风险利率2%）
            risk_free_rate = 0.02
            sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
            
            # 最大回撤
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min()
            
            return {
                'total_return': round(total_return * 100, 2),
                'annualized_return': round(annualized_return * 100, 2),
                'volatility': round(volatility * 100, 2),
                'sharpe_ratio': round(sharpe_ratio, 2),
                'max_drawdown': round(max_drawdown * 100, 2),
                'data_days': len(navs)
            }
            
        except Exception as e:
            logger.debug(f"计算指标失败: {e}")
            return {}
    
    def _update_progress(self, progress: float, message: str):
        """更新进度"""
        with self._lock:
            self._preload_status['progress'] = progress
        logger.info(f"[{progress*100:.0f}%] {message}")
    
    def _preload_profit_trend(self):
        """预计算收益趋势数据"""
        logger.info("预计算收益趋势数据...")
        
        try:
            from web.real_data_fetcher import data_fetcher
            
            # 获取用户持仓
            try:
                from data_retrieval.enhanced_database import get_database_manager
                db_manager = get_database_manager()
                
                holdings_sql = """
                SELECT fund_code, holding_shares, cost_price
                FROM user_holdings 
                WHERE user_id = 'default_user' AND holding_shares > 0
                """
                holdings_df = db_manager.execute_query(holdings_sql)
                
                if holdings_df.empty:
                    logger.info("用户无持仓，跳过收益趋势预计算")
                    return
                
                fund_code_list = holdings_df['fund_code'].tolist()
                
                # 计算权重
                total_amount = 0
                amounts = []
                for _, row in holdings_df.iterrows():
                    amount = float(row['holding_shares'] or 0) * float(row['cost_price'] or 0)
                    amounts.append(amount)
                    total_amount += amount
                
                if total_amount > 0:
                    weight_list = [amount/total_amount for amount in amounts]
                else:
                    weight_list = [1.0/len(fund_code_list)] * len(fund_code_list)
                
            except Exception as e:
                logger.warning(f"获取用户持仓失败，跳过收益趋势预计算: {e}")
                return
            
            # 计算多个时间段的收益趋势
            days_list = [30, 90, 180]  # 1个月、3个月、6个月
            
            for days in days_list:
                try:
                    # 获取沪深300历史数据
                    csi300_data = data_fetcher.get_csi300_history(days)
                    
                    # 获取基金组合历史净值
                    portfolio_data = data_fetcher.calculate_portfolio_nav(
                        fund_code_list, weight_list, initial_amount=10000, days=days
                    )
                    
                    if csi300_data.empty or portfolio_data.empty:
                        logger.warning(f"收益趋势数据获取失败（{days}天）")
                        continue
                    
                    # 准备返回数据
                    labels = []
                    profit_data = []
                    benchmark_data = []
                    
                    # 找到共同日期
                    portfolio_dates = set(portfolio_data['date'].dt.date)
                    csi300_dates = set(csi300_data['date'].dt.date)
                    common_dates = sorted(list(portfolio_dates.intersection(csi300_dates)))[:days]
                    
                    if common_dates:
                        base_portfolio_value = None
                        base_benchmark_value = None
                        
                        for date in common_dates:
                            labels.append(date.strftime('%m-%d'))
                            
                            # 沪深300数据
                            csi300_row = csi300_data[csi300_data['date'].dt.date == date]
                            if not csi300_row.empty:
                                current_benchmark = csi300_row.iloc[0]['price']
                                if base_benchmark_value is None:
                                    base_benchmark_value = current_benchmark
                                    benchmark_data.append(10000)
                                else:
                                    benchmark_return = (current_benchmark / base_benchmark_value - 1) * 100
                                    benchmark_data.append(round(10000 * (1 + benchmark_return/100), 2))
                            else:
                                benchmark_data.append(benchmark_data[-1] if benchmark_data else 10000)
                            
                            # 基金组合数据
                            portfolio_row = portfolio_data[portfolio_data['date'].dt.date == date]
                            if not portfolio_row.empty:
                                current_portfolio = portfolio_row.iloc[0]['portfolio_nav']
                                if base_portfolio_value is None:
                                    base_portfolio_value = current_portfolio
                                    profit_data.append(10000)
                                else:
                                    portfolio_return = (current_portfolio / base_portfolio_value - 1) * 100
                                    profit_data.append(round(10000 * (1 + portfolio_return/100), 2))
                            else:
                                profit_data.append(profit_data[-1] if profit_data else 10000)
                    
                    # 缓存收益趋势数据
                    cache_data = {
                        'labels': labels,
                        'profit': profit_data,
                        'benchmark': benchmark_data,
                        'fund_codes': fund_code_list,
                        'weights': weight_list,
                        'days': days,
                        'data_source': 'real_historical_data',
                        'benchmark_name': '沪深300',
                        'calculated_at': datetime.now().isoformat()
                    }
                    
                    key = f"{self.KEY_PREFIX['profit_trend']}:{days}"
                    self.cache.set(key, cache_data, self.CACHE_TTL['profit_trend'])
                    
                    logger.info(f"收益趋势预计算完成（{days}天）: {len(labels)} 个数据点")
                    
                except Exception as e:
                    logger.warning(f"预计算收益趋势失败（{days}天）: {e}")
            
            logger.info("收益趋势预计算完成")
            
        except Exception as e:
            logger.error(f"预计算收益趋势失败: {e}")
    
    # ============ 用户查询接口 ============
    
    def get_fund_basic_info(self, fund_code: str) -> Optional[Dict]:
        """获取基金基本信息（从缓存）"""
        key = f"{self.KEY_PREFIX['basic_info']}:{fund_code}"
        return self.cache.get(key)
    
    def get_fund_nav_history(self, fund_code: str) -> Optional[pd.DataFrame]:
        """获取基金历史净值（从缓存）"""
        key = f"{self.KEY_PREFIX['nav_history']}:{fund_code}"
        data = self.cache.get(key)
        
        if data:
            return pd.DataFrame(data['records'], columns=data['columns'])
        return None
    
    def get_fund_latest_nav(self, fund_code: str) -> Optional[Dict]:
        """获取基金最新净值（从缓存）"""
        key = f"{self.KEY_PREFIX['latest_nav']}:{fund_code}"
        return self.cache.get(key)
    
    def get_fund_performance(self, fund_code: str) -> Optional[Dict]:
        """获取基金绩效指标（从缓存）"""
        key = f"{self.KEY_PREFIX['performance']}:{fund_code}"
        return self.cache.get(key)
    
    def is_qdii_fund(self, fund_code: str) -> bool:
        """判断是否为QDII基金（从缓存）"""
        key = f"{self.KEY_PREFIX['qdii_flag']}:{fund_code}"
        result = self.cache.get(key)
        return result if result is not None else False
    
    def get_profit_trend(self, days: int = 90) -> Optional[Dict]:
        """获取预计算的收益趋势数据（从缓存）"""
        key = f"{self.KEY_PREFIX['profit_trend']}:{days}"
        return self.cache.get(key)
    
    def get_preload_status(self) -> Dict:
        """获取预加载状态"""
        with self._lock:
            return self._preload_status.copy()
    
    def is_ready(self) -> bool:
        """检查是否预加载完成"""
        return self._preload_status['completed']
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        return self.cache.get_stats()
    
    def get_all_fund_codes(self) -> List[str]:
        """获取所有已缓存的基金代码"""
        # 从缓存中提取所有基金代码
        codes = set()
        prefix = f"{self.KEY_PREFIX['basic_info']}:"
        
        # 这里简化处理，实际应该从缓存管理器获取所有key
        return list(codes)


# 全局预加载器实例
_preloader_instance: Optional[FundDataPreloader] = None


def get_preloader() -> FundDataPreloader:
    """获取全局预加载器实例"""
    global _preloader_instance
    if _preloader_instance is None:
        _preloader_instance = FundDataPreloader()
    return _preloader_instance


def preload_fund_data(fund_codes: Optional[List[str]] = None, 
                     async_mode: bool = False) -> bool:
    """
    便捷函数：预加载基金数据
    
    Args:
        fund_codes: 基金代码列表
        async_mode: 是否异步
        
    Returns:
        bool: 是否成功
    """
    preloader = get_preloader()
    return preloader.preload_all(fund_codes, async_mode)


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("基金数据预加载服务测试")
    print("=" * 60)
    
    # 创建预加载器
    preloader = FundDataPreloader()
    
    # 预加载测试数据
    test_codes = ['000001', '000002', '021539', '100055']
    
    print(f"\n预加载 {len(test_codes)} 只基金...")
    success = preloader.preload_all(test_codes)
    
    if success:
        print("\n预加载完成！")
        
        # 测试查询
        print("\n查询测试:")
        for code in test_codes:
            basic = preloader.get_fund_basic_info(code)
            latest = preloader.get_fund_latest_nav(code)
            perf = preloader.get_fund_performance(code)
            
            print(f"\n  {code}:")
            if basic:
                print(f"    名称: {basic.get('fund_name')}")
            if latest:
                print(f"    最新净值: {latest.get('nav')} ({latest.get('date')})")
            if perf:
                print(f"    夏普比率: {perf.get('sharpe_ratio')}")
        
        print(f"\n缓存统计: {preloader.get_cache_stats()}")
