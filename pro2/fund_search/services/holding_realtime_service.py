#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
持仓实时数据服务

数据分级策略：
1. 实时数据（日涨跌幅、当前市值）：每次请求实时获取，不缓存
2. 准实时数据（昨日数据）：内存缓存15分钟
3. 低频指标（年化收益、夏普等）：数据库缓存1天
4. 静态数据（持仓份额、成本价）：直接从数据库读取
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import requests
import json
import threading

logger = logging.getLogger(__name__)


@dataclass
class HoldingDataDTO:
    """持仓数据传输对象"""
    # 基础信息
    fund_code: str = ''
    fund_name: str = ''
    fund_type: str = ''
    
    # 静态数据（持仓表）
    holding_shares: float = 0.0
    cost_price: float = 0.0
    holding_amount: float = 0.0
    
    # 实时数据（外部API）
    current_nav: Optional[float] = None
    estimate_nav: Optional[float] = None
    today_return: Optional[float] = None
    
    # 准实时数据（昨日）
    yesterday_nav: Optional[float] = None
    yesterday_return: Optional[float] = None
    yesterday_profit: Optional[float] = None
    yesterday_return_date: Optional[str] = None  # 昨日收益率使用的净值日期
    yesterday_return_days_diff: Optional[int] = None  # 日期差（T-1=1, T-2=2）
    yesterday_return_is_stale: bool = False  # 是否为延迟数据
    
    # 低频指标（绩效缓存）
    annualized_return: Optional[float] = None
    max_drawdown: Optional[float] = None
    sharpe_ratio: Optional[float] = None  # 默认夏普比率（成立以来）
    sharpe_ratio_ytd: Optional[float] = None  # 今年以来
    sharpe_ratio_1y: Optional[float] = None  # 近一年
    sharpe_ratio_all: Optional[float] = None  # 成立以来
    composite_score: Optional[float] = None
    
    # 计算字段
    current_market_value: Optional[float] = field(default=None, init=False)
    holding_profit: Optional[float] = field(default=None, init=False)
    holding_profit_rate: Optional[float] = field(default=None, init=False)
    today_profit: Optional[float] = field(default=None, init=False)
    
    def calculate(self):
        """计算衍生指标"""
        # 当前市值
        if self.holding_shares and self.current_nav:
            self.current_market_value = round(self.holding_shares * self.current_nav, 2)
        
        # 持仓盈亏
        if self.current_market_value is not None and self.holding_amount:
            self.holding_profit = round(self.current_market_value - self.holding_amount, 2)
            self.holding_profit_rate = round(
                self.holding_profit / self.holding_amount * 100, 2
            ) if self.holding_amount > 0 else 0.0
        
        # 今日盈亏
        if self.holding_shares and self.yesterday_nav and self.current_nav:
            yesterday_value = self.holding_shares * self.yesterday_nav
            self.today_profit = round(
                self.current_market_value - yesterday_value, 2
            ) if self.current_market_value else None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            # 基础
            'fund_code': self.fund_code,
            'fund_name': self.fund_name,
            'fund_type': self.fund_type,
            
            # 静态
            'holding_shares': self.holding_shares,
            'cost_price': self.cost_price,
            'holding_amount': self.holding_amount,
            
            # 实时
            'today_return': self.today_return,
            'current_nav': self.current_nav,
            'estimate_nav': self.estimate_nav,
            
            # 准实时
            'yesterday_return': self.yesterday_return,
            'yesterday_profit': self.yesterday_profit,
            'yesterday_return_date': self.yesterday_return_date,
            'yesterday_return_days_diff': self.yesterday_return_days_diff,
            'yesterday_return_is_stale': self.yesterday_return_is_stale,
            
            # 低频
            'annualized_return': self.annualized_return,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'sharpe_ratio_ytd': self.sharpe_ratio_ytd,
            'sharpe_ratio_1y': self.sharpe_ratio_1y,
            'sharpe_ratio_all': self.sharpe_ratio_all,
            'composite_score': self.composite_score,
            
            # 计算
            'current_market_value': self.current_market_value,
            'holding_profit': self.holding_profit,
            'holding_profit_rate': self.holding_profit_rate,
            'today_profit': self.today_profit
        }


class RealtimeDataFetcher:
    """
    实时数据获取器
    
    专门用于获取日涨跌幅等实时数据，带短期内存缓存（2分钟）
    
    数据源优先级（实时数据计算）：
    1. 天天基金（最实时，有估算涨跌幅）
    2. 新浪（实时性好）
    3. 东方财富（备用）
    4. Tushare（稳定性高）
    5. AKShare（降级）
    """
    
    def __init__(self, cache_ttl_seconds: int = 120):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # 短期内存缓存，避免短时间内重复请求
        self._cache = {}
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._cache_lock = threading.RLock()
    
    def _get_cache_key(self, fund_code: str) -> str:
        """生成缓存键（按分钟级时间戳，2分钟有效期）"""
        now = datetime.now()
        # 按2分钟窗口取整，同一窗口内的请求共享缓存
        time_bucket = now.replace(second=0, microsecond=0)
        time_bucket = time_bucket.replace(minute=(time_bucket.minute // 2) * 2)
        return f"{fund_code}:{time_bucket.strftime('%Y%m%d%H%M')}"
    
    def _get_from_cache(self, fund_code: str) -> Optional[Dict]:
        """从缓存获取数据"""
        with self._cache_lock:
            cache_key = self._get_cache_key(fund_code)
            cached = self._cache.get(cache_key)
            if cached:
                data, timestamp = cached
                if datetime.now() - timestamp < self._cache_ttl:
                    logger.debug(f"实时数据缓存命中: {fund_code}")
                    return data
                else:
                    # 过期，删除
                    del self._cache[cache_key]
            return None
    
    def _save_to_cache(self, fund_code: str, data: Dict):
        """保存数据到缓存"""
        with self._cache_lock:
            cache_key = self._get_cache_key(fund_code)
            self._cache[cache_key] = (data, datetime.now())
            # 清理过期缓存（简单LRU：保留最近100条）
            if len(self._cache) > 100:
                oldest_keys = sorted(
                    self._cache.keys(),
                    key=lambda k: self._cache[k][1]
                )[:20]  # 删除最旧的20条
                for key in oldest_keys:
                    del self._cache[key]
    
    def get_fund_realtime(self, fund_code: str) -> Dict:
        """
        获取基金实时数据（日涨跌幅等）
        
        优先级（实时数据计算）：
        1. 内存缓存（2分钟有效）
        2. 天天基金估值接口（最实时，有估算涨跌幅）
        3. 新浪实时接口（实时性好）
        4. 东方财富接口（备用）
        5. Tushare接口（稳定性高）
        6. AKShare接口（降级）
        """
        # 0. 先检查缓存
        cached_data = self._get_from_cache(fund_code)
        if cached_data:
            return cached_data
        
        result = None
        
        # 1. 尝试天天基金
        try:
            result = self._from_tiantian(fund_code)
            if result:
                self._save_to_cache(fund_code, result)
                return result
        except Exception as e:
            logger.debug(f"天天基金获取失败 {fund_code}: {e}")
        
        # 2. 尝试新浪
        try:
            result = self._from_sina(fund_code)
            if result:
                self._save_to_cache(fund_code, result)
                return result
        except Exception as e:
            logger.debug(f"新浪获取失败 {fund_code}: {e}")
        
        # 3. 尝试东方财富
        try:
            result = self._from_eastmoney(fund_code)
            if result:
                self._save_to_cache(fund_code, result)
                return result
        except Exception as e:
            logger.debug(f"东方财富获取失败 {fund_code}: {e}")
        
        # 4. 尝试 Tushare
        try:
            result = self._from_tushare(fund_code)
            if result:
                self._save_to_cache(fund_code, result)
                return result
        except Exception as e:
            logger.debug(f"Tushare获取失败 {fund_code}: {e}")
        
        # 5. 降级到AKShare
        try:
            result = self._from_akshare(fund_code)
            if result:
                self._save_to_cache(fund_code, result)
                return result
        except Exception as e:
            logger.debug(f"AKShare获取失败 {fund_code}: {e}")
        
        logger.warning(f"所有实时数据源都失败: {fund_code}")
        result = {
            'current_nav': None,
            'estimate_nav': None,
            'today_return': 0.0,
            'source': 'failed'
        }
        self._save_to_cache(fund_code, result)
        return result
    
    def _from_tiantian(self, fund_code: str) -> Optional[Dict]:
        """天天基金实时估值接口"""
        url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
        response = self.session.get(url, timeout=5)
        
        if response.status_code == 200 and 'jsonpgz' in response.text:
            json_str = response.text.replace('jsonpgz(', '').replace(');', '')
            data = json.loads(json_str)
            
            gztime = data.get('gztime', '')
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 验证是今天数据
            if today in gztime:
                return {
                    'current_nav': float(data.get('dwjz', 0)) if data.get('dwjz') else None,
                    'estimate_nav': float(data.get('gsz', 0)) if data.get('gsz') else None,
                    'today_return': float(data.get('gszzl', 0)) if data.get('gszzl') else 0.0,
                    'source': 'tiantian'
                }
        return None
    
    def _from_sina(self, fund_code: str) -> Optional[Dict]:
        """新浪实时接口"""
        url = f"https://hq.sinajs.cn/list=f_{fund_code}"
        headers = {'Referer': 'https://finance.sina.com.cn'}
        response = self.session.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.text
            key = f'f_{fund_code}="'
            if key in data:
                parts = data.split('"')[1].split(',')
                if len(parts) >= 6:
                    return {
                        'current_nav': float(parts[1]) if parts[1] else None,
                        'estimate_nav': float(parts[1]) if parts[1] else None,
                        'today_return': float(parts[5]) if parts[5] else 0.0,
                        'source': 'sina'
                    }
        return None
    
    def _from_eastmoney(self, fund_code: str) -> Optional[Dict]:
        """东方财富实时接口"""
        try:
            import akshare as ak
            
            # 使用东方财富接口获取实时估值
            df = ak.fund_em_valuation(fund_code)
            
            if df is not None and not df.empty:
                latest = df.iloc[0]
                
                current_nav = float(latest.get('单位净值', 0)) if pd.notna(latest.get('单位净值')) else None
                estimate_nav = float(latest.get('估算净值', 0)) if pd.notna(latest.get('估算净值')) else None
                today_return = float(latest.get('估算涨跌', 0)) if pd.notna(latest.get('估算涨跌')) else 0.0
                
                return {
                    'current_nav': current_nav,
                    'estimate_nav': estimate_nav,
                    'today_return': today_return,
                    'source': 'eastmoney'
                }
        except Exception as e:
            logger.debug(f"东方财富获取 {fund_code} 失败: {e}")
        
        return None
    
    def _from_tushare(self, fund_code: str) -> Optional[Dict]:
        """Tushare 实时数据接口"""
        try:
            import tushare as ts
            
            # 从配置获取 token
            token = None
            try:
                from shared.enhanced_config import DATA_SOURCE_CONFIG
                token = DATA_SOURCE_CONFIG.get('tushare', {}).get('token')
            except ImportError:
                token = '5ff19facae0e5b26a407d491d33707a9884a39a714a0d76b6495725b'
            
            ts_pro = ts.pro_api(token)
            
            # Tushare 需要 .OF 后缀
            ts_code = fund_code if fund_code.endswith('.OF') else f"{fund_code}.OF"
            
            # 获取最新净值
            df = ts_pro.fund_nav(ts_code=ts_code)
            
            if df is not None and not df.empty:
                latest = df.iloc[0]
                
                # 获取单位净值
                nav = float(latest.get('unit_nav', 0)) if pd.notna(latest.get('unit_nav')) else None
                
                # 计算日涨跌幅（如果 API 没有直接返回）
                today_return = 0.0
                if len(df) >= 2:
                    prev_nav = float(df.iloc[1].get('unit_nav', 0)) if pd.notna(df.iloc[1].get('unit_nav')) else None
                    if nav and prev_nav and prev_nav > 0:
                        today_return = round((nav - prev_nav) / prev_nav * 100, 2)
                
                return {
                    'current_nav': nav,
                    'estimate_nav': nav,  # Tushare 不提供估算净值，使用实际净值
                    'today_return': today_return,
                    'source': 'tushare'
                }
        except Exception as e:
            logger.debug(f"Tushare 获取 {fund_code} 失败: {e}")
        
        return None
    
    def _from_akshare(self, fund_code: str) -> Optional[Dict]:
        """AKShare实时接口"""
        import akshare as ak
        
        df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
        if df is not None and not df.empty and len(df) >= 2:
            latest = df.iloc[0]
            prev = df.iloc[1]
            
            current_nav = float(latest.get('单位净值', 0)) if pd.notna(latest.get('单位净值')) else None
            prev_nav = float(prev.get('单位净值', 0)) if pd.notna(prev.get('单位净值')) else None
            
            today_return = 0.0
            if current_nav and prev_nav and prev_nav > 0:
                today_return = round((current_nav - prev_nav) / prev_nav * 100, 2)
            
            return {
                'current_nav': current_nav,
                'estimate_nav': current_nav,
                'today_return': today_return,
                'source': 'akshare'
            }
        return None
    
    def get_batch_realtime(self, fund_codes: List[str], max_workers: int = 5) -> Dict[str, Dict]:
        """
        批量获取实时数据（并行请求）
        
        Args:
            fund_codes: 基金代码列表
            max_workers: 最大并发数
        
        Returns:
            Dict[code, data]
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_code = {
                executor.submit(self.get_fund_realtime, code): code 
                for code in fund_codes
            }
            
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    results[code] = future.result()
                except Exception as e:
                    logger.error(f"获取 {code} 实时数据失败: {e}")
                    results[code] = {
                        'current_nav': None,
                        'estimate_nav': None,
                        'today_return': 0.0,
                        'source': 'error'
                    }
        
        return results


class HoldingRealtimeService:
    """
    持仓实时数据服务
    
    核心设计：
    1. 实时指标（日涨跌幅、当前市值）：每次请求实时获取，不缓存
    2. 准实时指标（昨日盈亏）：内存缓存15分钟
    3. 低频指标（年化收益、夏普等）：数据库缓存1天
    4. 静态数据：直接从数据库读取
    """
    
    def __init__(self, db_manager, cache_manager):
        self.db = db_manager
        self.cache = cache_manager
        self.realtime_fetcher = RealtimeDataFetcher()
    
    def get_holdings_data(self, user_id: str = 'default_user') -> List[Dict]:
        """
        获取用户持仓完整数据
        
        数据流：
        1. 静态数据（持仓表）
        2. 实时数据（并行请求：日涨跌幅）
        3. 准实时数据（昨日数据，内存缓存）
        4. 低频指标（绩效数据，数据库缓存1天）
        """
        # 1. 获取静态持仓数据
        holdings = self._get_static_holdings(user_id)
        if not holdings:
            return []
        
        fund_codes = [h['fund_code'] for h in holdings]
        
        # 2. 并行获取实时数据（日涨跌幅 - 不缓存）
        logger.info(f"获取{len(fund_codes)}只基金的实时数据...")
        realtime_data = self.realtime_fetcher.get_batch_realtime(fund_codes)
        
        # 3. 获取昨日数据（准实时，内存缓存）
        yesterday_data = self._get_yesterday_data_batch(fund_codes)
        
        # 4. 获取绩效指标（低频，数据库缓存1天）
        performance_data = self._get_performance_batch(fund_codes)
        
        # 5. 组装结果
        results = []
        for holding in holdings:
            fund_code = holding['fund_code']
            
            dto = HoldingDataDTO(
                fund_code=fund_code,
                fund_name=holding.get('fund_name', ''),
                fund_type=holding.get('fund_type', ''),
                holding_shares=holding.get('holding_shares', 0),
                cost_price=holding.get('cost_price', 0),
                holding_amount=holding.get('holding_amount', 0)
            )
            
            # 填充实时数据
            rt = realtime_data.get(fund_code, {})
            dto.current_nav = rt.get('current_nav')
            dto.estimate_nav = rt.get('estimate_nav')
            dto.today_return = rt.get('today_return')
            
            # 填充昨日数据
            yd = yesterday_data.get(fund_code, {})
            dto.yesterday_nav = yd.get('yesterday_nav')
            dto.yesterday_return = yd.get('yesterday_return')
            dto.yesterday_return_date = yd.get('yesterday_return_date')
            dto.yesterday_return_days_diff = yd.get('yesterday_return_days_diff')
            dto.yesterday_return_is_stale = yd.get('yesterday_return_is_stale', False)
            
            # 填充绩效指标
            perf = performance_data.get(fund_code, {})
            dto.annualized_return = perf.get('annualized_return')
            dto.max_drawdown = perf.get('max_drawdown')
            dto.sharpe_ratio = perf.get('sharpe_ratio')  # 默认夏普比率
            dto.sharpe_ratio_ytd = perf.get('sharpe_ratio_ytd')  # 今年以来
            dto.sharpe_ratio_1y = perf.get('sharpe_ratio_1y')  # 近一年
            dto.sharpe_ratio_all = perf.get('sharpe_ratio_all')  # 成立以来
            dto.composite_score = perf.get('composite_score')
            
            # 计算衍生字段
            dto.calculate()
            
            results.append(dto.to_dict())
        
        return results
    
    def _get_static_holdings(self, user_id: str) -> List[Dict]:
        """获取静态持仓数据"""
        try:
            sql = """
                SELECT 
                    h.fund_code, 
                    h.fund_name, 
                    h.holding_shares, 
                    h.cost_price, 
                    h.holding_amount,
                    COALESCE(bi.fund_type, '未知') as fund_type
                FROM user_holdings h
                LEFT JOIN fund_basic_info bi ON h.fund_code = bi.fund_code
                WHERE h.user_id = :user_id
                  AND h.holding_shares > 0
            """
            df = self.db.execute_query(sql, {'user_id': user_id})
            return df.to_dict('records') if not df.empty else []
        except Exception as e:
            logger.error(f"获取静态持仓失败: {e}")
            return []
    
    def _get_yesterday_data_batch(self, fund_codes: List[str]) -> Dict[str, Dict]:
        """
        批量获取昨日数据（准实时，内存缓存15分钟）
        
        优先从 fund_nav_cache 获取，如果表不存在则直接使用 fund_analysis_results
        """
        results = {}
        missing_codes = []
        
        # 先查内存缓存（holding_realtime_service 自己的缓存）
        for code in fund_codes:
            cached = self.cache.get_from_memory(f'yesterday:{code}')
            if cached:
                results[code] = cached
            else:
                missing_codes.append(code)
        
        if not missing_codes:
            return results
        
        # 从预加载的基金数据缓存获取（FundDataPreloader）
        try:
            from services.fund_data_preloader import get_preloader
            preloader = get_preloader()
            
            still_missing = []
            for code in missing_codes:
                # 尝试从预加载缓存获取最新净值（包含 daily_return）
                latest_nav = preloader.get_fund_latest_nav(code)
                if latest_nav and latest_nav.get('daily_return', 0) != 0:
                    results[code] = {
                        'yesterday_nav': latest_nav.get('nav'),
                        'yesterday_return': latest_nav.get('daily_return', 0),
                        'yesterday_return_date': latest_nav.get('date'),
                        'yesterday_return_days_diff': 1,
                        'yesterday_return_is_stale': False
                    }
                    # 回填到 holding_service 的缓存
                    self.cache.set_to_memory(f'yesterday:{code}', results[code], ttl_minutes=15)
                    logger.debug(f"从预加载缓存获取 {code} 昨日收益率: {latest_nav.get('daily_return')}%")
                else:
                    still_missing.append(code)
            
            missing_codes = still_missing
            
        except Exception as e:
            logger.debug(f"从预加载缓存获取昨日数据失败: {e}")
        
        if not missing_codes:
            return results
        
        # 查询数据库
        if self.db:
            try:
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                
                # 尝试从 fund_nav_cache 获取（如果表存在）
                try:
                    placeholders = ','.join([f':code{i}' for i in range(len(missing_codes))])
                    sql = f"""
                        SELECT 
                            fund_code,
                            nav_value as yesterday_nav,
                            daily_return as yesterday_return
                        FROM fund_nav_cache
                        WHERE fund_code IN ({placeholders})
                          AND nav_date = :yesterday
                    """
                    
                    params = {f'code{i}': code for i, code in enumerate(missing_codes)}
                    params['yesterday'] = yesterday
                    df = self.db.execute_query(sql, params)
                    
                    if not df.empty:
                        for _, row in df.iterrows():
                            code = row['fund_code']
                            data = {
                                'yesterday_nav': float(row['yesterday_nav']) if pd.notna(row['yesterday_nav']) else None,
                                'yesterday_return': float(row['yesterday_return']) if pd.notna(row['yesterday_return']) else 0.0,
                                'yesterday_return_date': yesterday,
                                'yesterday_return_days_diff': 1,
                                'yesterday_return_is_stale': False
                            }
                            results[code] = data
                            # 回填内存缓存
                            self.cache.set_to_memory(f'yesterday:{code}', data, ttl_minutes=15)
                        
                        # 更新缺失列表
                        missing_codes = [code for code in missing_codes if code not in results]
                except Exception as e:
                    # fund_nav_cache 表可能不存在，记录日志继续
                    logger.debug(f"从 fund_nav_cache 获取数据失败（表可能不存在）: {e}")
                
                # 从 fund_analysis_results 获取（作为 fallback 或补充）
                still_missing = [code for code in missing_codes if code not in results]
                
                # 对于 QDII 基金，需要从 Adapter 获取以获取正确的延迟标记
                # 所以这里只处理非 QDII 基金
                from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
                qdii_codes = [code for code in still_missing if MultiSourceDataAdapter.is_qdii_fund(code)]
                non_qdii_codes = [code for code in still_missing if not MultiSourceDataAdapter.is_qdii_fund(code)]
                
                if non_qdii_codes:
                    try:
                        placeholders2 = ','.join([f':code{i}' for i in range(len(non_qdii_codes))])
                        sql2 = f"""
                            SELECT 
                                fund_code,
                                prev_day_return
                            FROM fund_analysis_results
                            WHERE (fund_code, analysis_date) IN (
                                SELECT fund_code, MAX(analysis_date) as max_date
                                FROM fund_analysis_results
                                WHERE fund_code IN ({placeholders2})
                                GROUP BY fund_code
                            )
                        """
                        params2 = {f'code{i}': code for i, code in enumerate(non_qdii_codes)}
                        df2 = self.db.execute_query(sql2, params2)
                        
                        if not df2.empty:
                            for _, row in df2.iterrows():
                                code = row['fund_code']
                                prev_return = float(row['prev_day_return']) if pd.notna(row['prev_day_return']) else 0.0
                                # 使用获取到的值（包括0值，因为0是有效的收益率）
                                # fund_analysis_results 数据默认为 T-1（非延迟）
                                results[code] = {
                                    'yesterday_nav': None,
                                    'yesterday_return': prev_return,
                                    'yesterday_return_date': datetime.now().strftime('%Y-%m-%d'),
                                    'yesterday_return_days_diff': 1,
                                    'yesterday_return_is_stale': False
                                }
                                # 回填内存缓存
                                self.cache.set_to_memory(f'yesterday:{code}', results[code], ttl_minutes=15)
                                logger.info(f"从 fund_analysis_results 获取 {code} 昨日收益率: {prev_return}%")
                    except Exception as e2:
                        logger.debug(f"从 fund_analysis_results 获取昨日数据失败: {e2}")
                
                # QDII 基金需要继续到 Adapter 获取，以获取正确的延迟标记
                if qdii_codes:
                    logger.info(f"QDII 基金 {len(qdii_codes)} 只将从 Adapter 获取以获取延迟标记")
                
                # 对于数据库中仍缺失的基金，从 MultiSourceDataAdapter 实时获取
                still_missing_after_db = [code for code in missing_codes if code not in results]
                if still_missing_after_db:
                    logger.info(f"尝试从 MultiSourceDataAdapter 批量获取 {len(still_missing_after_db)} 只基金的昨日收益率")
                    try:
                        from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
                        adapter = MultiSourceDataAdapter()
                        
                        # 【优化】使用批量获取替代逐个获取
                        # 1. 首先尝试批量获取所有基金的历史数据
                        batch_results = {}
                        try:
                            # 使用批量接口获取多只基金的历史数据
                            batch_nav_data = adapter.batch_get_fund_nav(still_missing_after_db)
                            for code, df in batch_nav_data.items():
                                if not df.empty and len(df) >= 2:
                                    # 计算昨日收益率
                                    latest_nav = float(df.iloc[-1]['nav'])
                                    yesterday_nav = float(df.iloc[-2]['nav'])
                                    yesterday_date = str(df.iloc[-2].get('date', ''))
                                    
                                    if yesterday_nav > 0:
                                        yesterday_return = (latest_nav - yesterday_nav) / yesterday_nav * 100
                                        yesterday_return = round(yesterday_return, 2)
                                        
                                        batch_results[code] = {
                                            'yesterday_nav': yesterday_nav,
                                            'yesterday_return': yesterday_return,
                                            'yesterday_return_date': yesterday_date,
                                            'yesterday_return_days_diff': 1,
                                            'yesterday_return_is_stale': False
                                        }
                        except Exception as batch_error:
                            logger.warning(f"批量获取昨日数据失败，降级到逐个获取: {batch_error}")
                        
                        # 2. 处理批量获取失败的基金，逐个获取
                        remaining_codes = [c for c in still_missing_after_db if c not in batch_results]
                        for code in remaining_codes:
                            try:
                                # 获取基金历史数据来计算昨日收益率
                                return_result = adapter._get_yesterday_return(code)
                                
                                batch_results[code] = {
                                    'yesterday_nav': None,
                                    'yesterday_return': return_result.get('value'),
                                    'yesterday_return_date': return_result.get('date'),
                                    'yesterday_return_days_diff': return_result.get('days_diff'),
                                    'yesterday_return_is_stale': return_result.get('is_stale', False)
                                }
                            except Exception as e:
                                logger.warning(f"从 Adapter 获取基金 {code} 昨日收益率失败: {e}")
                                batch_results[code] = {
                                    'yesterday_nav': None, 
                                    'yesterday_return': None,
                                    'yesterday_return_date': None,
                                    'yesterday_return_days_diff': None,
                                    'yesterday_return_is_stale': False
                                }
                        
                        # 3. 合并结果并回填缓存
                        for code, data in batch_results.items():
                            results[code] = data
                            # 回填内存缓存
                            self.cache.set_to_memory(f'yesterday:{code}', data, ttl_minutes=15)
                            logger.info(f"从 Adapter 获取 {code} 昨日收益率: {data.get('yesterday_return')}% (T-{data.get('yesterday_return_days_diff')})")
                        
                    except Exception as e:
                        logger.error(f"初始化 MultiSourceDataAdapter 失败: {e}")
                        # 所有缺失基金标记为 None
                        for code in still_missing_after_db:
                            results[code] = {
                                'yesterday_nav': None, 
                                'yesterday_return': None,
                                'yesterday_return_date': None,
                                'yesterday_return_days_diff': None,
                                'yesterday_return_is_stale': False
                            }
                        
            except Exception as e:
                logger.error(f"获取昨日数据批量失败: {e}")
                for code in missing_codes:
                    if code not in results:
                        results[code] = {'yesterday_nav': None, 'yesterday_return': None}
        
        return results
    
    def _get_performance_batch(self, fund_codes: List[str]) -> Dict[str, Dict]:
        """
        批量获取绩效指标（低频，数据库缓存1天）
        """
        results = {}
        missing_codes = []
        
        # 先查内存缓存
        for code in fund_codes:
            cached = self.cache.get_from_memory(f'perf:{code}')
            if cached:
                results[code] = cached
            else:
                missing_codes.append(code)
        
        if not missing_codes:
            return results
        
        # 查询数据库（1天内有效）- 使用 fund_analysis_results
        if self.db:
            try:
                placeholders = ','.join([f':code{i}' for i in range(len(missing_codes))])
                sql = f"""
                    SELECT 
                        fund_code,
                        annualized_return,
                        max_drawdown,
                        volatility,
                        sharpe_ratio,
                        sharpe_ratio_ytd,
                        sharpe_ratio_1y,
                        sharpe_ratio_all,
                        composite_score
                    FROM fund_analysis_results
                    WHERE fund_code IN ({placeholders})
                      AND analysis_date >= DATE_SUB(CURDATE(), INTERVAL 1 DAY)
                    ORDER BY analysis_date DESC, updated_at DESC
                """
                
                params = {f'code{i}': code for i, code in enumerate(missing_codes)}
                df = self.db.execute_query(sql, params)
                
                if not df.empty:
                    # 取每个基金的最新记录
                    for code in missing_codes:
                        fund_df = df[df['fund_code'] == code]
                        if not fund_df.empty:
                            row = fund_df.iloc[0]
                            # 获取默认夏普比率（成立以来）
                            # 各个周期的夏普比率独立处理，不使用fallback
                            sharpe_ratio = float(row['sharpe_ratio']) if pd.notna(row['sharpe_ratio']) else None
                            sharpe_ytd = float(row['sharpe_ratio_ytd']) if pd.notna(row['sharpe_ratio_ytd']) else None
                            sharpe_1y = float(row['sharpe_ratio_1y']) if pd.notna(row['sharpe_ratio_1y']) else None
                            sharpe_all = float(row['sharpe_ratio_all']) if pd.notna(row['sharpe_ratio_all']) else None
                            
                            # 如果 sharpe_ratio 为空，优先使用 sharpe_1y（近一年）作为默认值
                            if sharpe_ratio is None:
                                sharpe_ratio = sharpe_1y if sharpe_1y is not None else sharpe_all
                            
                            data = {
                                'annualized_return': float(row['annualized_return']) if pd.notna(row['annualized_return']) else None,
                                'max_drawdown': float(row['max_drawdown']) if pd.notna(row['max_drawdown']) else None,
                                'volatility': float(row['volatility']) if pd.notna(row['volatility']) else None,
                                'sharpe_ratio': sharpe_ratio,  # 默认夏普比率（优先近一年）
                                'sharpe_ratio_ytd': sharpe_ytd,  # 今年以来（独立值，不fallback）
                                'sharpe_ratio_1y': sharpe_1y,    # 近一年（独立值，不fallback）
                                'sharpe_ratio_all': sharpe_all,  # 成立以来（独立值，不fallback）
                                'composite_score': float(row['composite_score']) if pd.notna(row['composite_score']) else None
                            }
                            results[code] = data
                            # 回填内存缓存
                            self.cache.set_to_memory(f'perf:{code}', data, ttl_minutes=30)
                
                # 补充缺失的（触发异步计算）
                still_missing = [c for c in missing_codes if c not in results]
                if still_missing:
                    logger.info(f"绩效指标缺失，使用实时计算: {still_missing}")
                    for code in still_missing:
                        # 实时计算（不缓存到数据库，只放内存）
                        metrics = self.cache._calculate_performance_metrics(code, 3650)  # 使用10年数据
                        if metrics:
                            sharpe_ratio = metrics.get('sharpe_ratio')
                            sharpe_ytd = metrics.get('sharpe_ratio_ytd')
                            sharpe_1y = metrics.get('sharpe_ratio_1y')
                            sharpe_all = metrics.get('sharpe_ratio_all')
                            
                            # 如果 sharpe_ratio 为空，优先使用 sharpe_1y 作为默认值
                            if sharpe_ratio is None:
                                sharpe_ratio = sharpe_1y if sharpe_1y is not None else sharpe_all
                            
                            results[code] = {
                                'annualized_return': metrics.get('annualized_return'),
                                'max_drawdown': metrics.get('max_drawdown'),
                                'volatility': metrics.get('volatility'),
                                'sharpe_ratio': sharpe_ratio,      # 默认夏普比率（优先近一年）
                                'sharpe_ratio_ytd': sharpe_ytd,    # 今年以来（独立值）
                                'sharpe_ratio_1y': sharpe_1y,      # 近一年（独立值）
                                'sharpe_ratio_all': sharpe_all,    # 成立以来（独立值）
                                'composite_score': metrics.get('composite_score')
                            }
                            self.cache.set_to_memory(f'perf:{code}', results[code], ttl_minutes=30)
                        else:
                            results[code] = self._empty_performance()
                            
            except Exception as e:
                logger.error(f"获取绩效指标批量失败: {e}")
                for code in missing_codes:
                    results[code] = self._empty_performance()
        
        return results
    
    def _empty_performance(self) -> Dict:
        """空绩效数据"""
        return {
            'annualized_return': None,
            'max_drawdown': None,
            'volatility': None,
            'sharpe_ratio': None,
            'sharpe_ratio_ytd': None,
            'sharpe_ratio_1y': None,
            'sharpe_ratio_all': None,
            'composite_score': None
        }
    
    def refresh_realtime_only(self, user_id: str, fund_codes: List[str]) -> List[Dict]:
        """
        仅刷新实时数据（用于定时刷新）
        
        只返回实时字段，减少数据传输
        """
        if not fund_codes:
            return []
        
        # 只获取实时数据
        realtime_data = self.realtime_fetcher.get_batch_realtime(fund_codes)
        
        # 获取静态数据（份额、成本）
        placeholders = ','.join(['%s'] * len(fund_codes))
        sql = f"""
            SELECT 
                fund_code,
                holding_shares,
                cost_price,
                holding_amount
            FROM user_holdings
            WHERE user_id = %s
              AND fund_code IN ({placeholders})
        """
        
        df = self.db.execute_query(sql, [user_id] + fund_codes)
        static_map = {}
        if not df.empty:
            for _, row in df.iterrows():
                static_map[row['fund_code']] = {
                    'holding_shares': row['holding_shares'],
                    'holding_amount': row['holding_amount']
                }
        
        # 组装结果
        results = []
        for code in fund_codes:
            rt = realtime_data.get(code, {})
            static = static_map.get(code, {})
            
            shares = static.get('holding_shares', 0)
            current_nav = rt.get('current_nav')
            
            result = {
                'fund_code': code,
                'today_return': rt.get('today_return'),
                'current_nav': current_nav,
                'current_market_value': round(shares * current_nav, 2) if shares and current_nav else None,
                'today_profit': None  # 需要昨日数据计算
            }
            results.append(result)
        
        return results
