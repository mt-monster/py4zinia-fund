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
    
    # 低频指标（绩效缓存）
    annualized_return: Optional[float] = None
    max_drawdown: Optional[float] = None
    sharpe_ratio: Optional[float] = None
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
            
            # 低频
            'annualized_return': self.annualized_return,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
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
        
        优先级：
        1. 内存缓存（2分钟有效）
        2. 天天基金估值接口（最实时，有估算涨跌幅）
        3. 新浪实时接口
        4. AKShare接口（降级）
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
        
        # 3. 降级到AKShare
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
            
            # 填充绩效指标
            perf = performance_data.get(fund_code, {})
            dto.annualized_return = perf.get('annualized_return')
            dto.max_drawdown = perf.get('max_drawdown')
            dto.sharpe_ratio = perf.get('sharpe_ratio')
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
        """
        results = {}
        missing_codes = []
        
        # 先查内存缓存
        for code in fund_codes:
            cached = self.cache.get_from_memory(f'yesterday:{code}')
            if cached:
                results[code] = cached
            else:
                missing_codes.append(code)
        
        if not missing_codes:
            return results
        
        # 查询数据库
        if self.db:
            try:
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                
                # 批量查询 - 使用命名参数
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
                            'yesterday_return': float(row['yesterday_return']) if pd.notna(row['yesterday_return']) else 0.0
                        }
                        results[code] = data
                        # 回填内存缓存
                        self.cache.set_to_memory(f'yesterday:{code}', data, ttl_minutes=15)
                
                # 补充缺失的 - 尝试从 fund_analysis_results 获取昨日收益率（QDII基金）
                still_missing = [code for code in missing_codes if code not in results]
                if still_missing:
                    try:
                        placeholders2 = ','.join([f':code{i}' for i in range(len(still_missing))])
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
                        params2 = {f'code{i}': code for i, code in enumerate(still_missing)}
                        df2 = self.db.execute_query(sql2, params2)
                        
                        if not df2.empty:
                            for _, row in df2.iterrows():
                                code = row['fund_code']
                                prev_return = float(row['prev_day_return']) if pd.notna(row['prev_day_return']) else 0.0
                                if prev_return != 0:  # 只使用非零值
                                    results[code] = {
                                        'yesterday_nav': None,
                                        'yesterday_return': prev_return
                                    }
                                    # 回填内存缓存
                                    self.cache.set_to_memory(f'yesterday:{code}', results[code], ttl_minutes=15)
                                    logger.info(f"从 fund_analysis_results 获取 {code} 昨日收益率: {prev_return}%")
                    except Exception as e2:
                        logger.debug(f"从 fund_analysis_results 获取昨日数据失败: {e2}")
                
                # 最终补充仍为缺失的
                for code in missing_codes:
                    if code not in results:
                        results[code] = {'yesterday_nav': None, 'yesterday_return': 0.0}
                        
            except Exception as e:
                logger.error(f"获取昨日数据批量失败: {e}")
                for code in missing_codes:
                    results[code] = {'yesterday_nav': None, 'yesterday_return': 0.0}
        
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
                            data = {
                                'annualized_return': float(row['annualized_return']) if pd.notna(row['annualized_return']) else None,
                                'max_drawdown': float(row['max_drawdown']) if pd.notna(row['max_drawdown']) else None,
                                'volatility': float(row['volatility']) if pd.notna(row['volatility']) else None,
                                'sharpe_ratio': float(row['sharpe_ratio']) if pd.notna(row['sharpe_ratio']) else None,
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
                        metrics = self.cache._calculate_performance_metrics(code, 365)
                        if metrics:
                            results[code] = {
                                'annualized_return': metrics.get('annualized_return'),
                                'max_drawdown': metrics.get('max_drawdown'),
                                'volatility': metrics.get('volatility'),
                                'sharpe_ratio': metrics.get('sharpe_ratio'),
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
