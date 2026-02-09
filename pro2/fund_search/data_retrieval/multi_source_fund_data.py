#!/usr/bin/env python
# coding: utf-8
"""
多数据源基金数据获取模块
整合 akshare 和 tushare，提供高可用的基金数据获取能力

主要功能:
1. 多数据源自动切换(akshare为主，tushare为备用)
2. QDII基金特殊处理
3. 数据质量验证
4. 错误处理和降级策略

使用示例:
    fetcher = MultiSourceFundData(tushare_token="your_token")
    data = fetcher.get_fund_nav_history("021539")
"""

import pandas as pd
import akshare as ak
import tushare as ts
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from functools import wraps

# 设置日志
logger = logging.getLogger(__name__)


# 数据源健康状态
class DataSourceHealth:
    """数据源健康监控"""
    def __init__(self):
        self.akshare = {'success': 0, 'fail': 0, 'last_error': None, 'avg_time': 0}
        self.tushare = {'success': 0, 'fail': 0, 'last_error': None, 'avg_time': 0}
    
    def record_success(self, source: str, response_time: float):
        """记录成功请求"""
        if source == 'akshare':
            self.akshare['success'] += 1
            self._update_avg_time('akshare', response_time)
        elif source == 'tushare':
            self.tushare['success'] += 1
            self._update_avg_time('tushare', response_time)
    
    def record_fail(self, source: str, error: str):
        """记录失败请求"""
        if source == 'akshare':
            self.akshare['fail'] += 1
            self.akshare['last_error'] = error
        elif source == 'tushare':
            self.tushare['fail'] += 1
            self.tushare['last_error'] = error
    
    def _update_avg_time(self, source: str, response_time: float):
        """更新平均响应时间"""
        if source == 'akshare':
            total = self.akshare['success'] + self.akshare['fail']
            if total > 0:
                old_avg = self.akshare['avg_time']
                self.akshare['avg_time'] = (old_avg * (total - 1) + response_time) / total
        elif source == 'tushare':
            total = self.tushare['success'] + self.tushare['fail']
            if total > 0:
                old_avg = self.tushare['avg_time']
                self.tushare['avg_time'] = (old_avg * (total - 1) + response_time) / total
    
    def get_success_rate(self, source: str) -> float:
        """获取数据源成功率"""
        if source == 'akshare':
            total = self.akshare['success'] + self.akshare['fail']
            return self.akshare['success'] / total if total > 0 else 1.0
        elif source == 'tushare':
            total = self.tushare['success'] + self.tushare['fail']
            return self.tushare['success'] / total if total > 0 else 1.0
        return 0.0
    
    def get_recommend_source(self) -> str:
        """
        获取推荐的数据源
        
        数据源优先级:
        1. PRIMARY: Tushare (推荐默认数据源)
        2. BACKUP_1: Akshare (当Tushare成功率低时降级)
        
        降级条件:
        - Tushare成功率 < 0.7
        - Akshare成功率 > Tushare成功率 + 0.2
        """
        ak_rate = self.get_success_rate('akshare')
        ts_rate = self.get_success_rate('tushare')
        
        # 降级条件: Tushare成功率低 或 Akshare明显更好
        if ts_rate < 0.7 or (ak_rate - ts_rate) > 0.2:
            logger.warning(f"Tushare成功率({ts_rate:.2%})低，降级到Akshare({ak_rate:.2%})")
            return 'akshare'
        
        return 'tushare'


def retry_on_failure(max_retries=3, delay=1):
    """失败重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i == max_retries - 1:
                        raise
                    logger.warning(f"{func.__name__} 第{i+1}次失败，{delay}秒后重试: {e}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator


class MultiSourceFundData:
    """
    多数据源基金数据获取器
    
    特点:
    1. 自动数据源切换
    2. 健康状态监控
    3. QDII基金特殊处理
    4. 数据质量验证
    """
    
    # QDII基金代码列表
    QDII_FUND_CODES = {
        '021539',  # 华安法国CAC40ETF发起式联接(QDII)A
        '021540',  # 华安法国CAC40ETF发起式联接(QDII)C
        '096001',  # 大成标普500等权重指数(QDII)A
        '100055',  # 富国全球科技互联网股票(QDII)A
        # 可以添加更多...
    }
    
    def __init__(self, tushare_token: Optional[str] = None, timeout: int = 10):
        """
        初始化多数据源获取器
        
        Args:
            tushare_token: Tushare API token
            timeout: 请求超时时间(秒)
        """
        self.timeout = timeout
        self.health = DataSourceHealth()
        
        # 初始化Tushare
        self.tushare_pro = None
        if tushare_token:
            try:
                ts.set_token(tushare_token)
                self.tushare_pro = ts.pro_api()
                logger.info("Tushare 初始化成功")
            except Exception as e:
                logger.warning(f"Tushare 初始化失败: {e}")
        
        logger.info("MultiSourceFundData 初始化完成")
    
    def is_qdii_fund(self, fund_code: str, fund_name: Optional[str] = None) -> bool:
        """
        判断是否为QDII基金
        
        Args:
            fund_code: 基金代码
            fund_name: 基金名称(可选)
        
        Returns:
            bool: 是否为QDII基金
        """
        # 代码匹配
        if fund_code in self.QDII_FUND_CODES:
            return True
        
        # 名称匹配
        if fund_name and 'QDII' in fund_name.upper():
            return True
        
        return False
    
    @retry_on_failure(max_retries=3, delay=1)
    def get_fund_nav_history(
        self, 
        fund_code: str, 
        source: str = 'auto',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取基金历史净值
        
        数据源优先级 (当 source='auto'):
        1. PRIMARY: Tushare (稳定性高)
        2. BACKUP_1: Akshare (数据全面)
        3. 抛出异常 (如果都失败)
        
        Args:
            fund_code: 基金代码
            source: 数据源 ('akshare', 'tushare', 'auto')
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            DataFrame: 包含以下列的标准化数据
                - date: 日期
                - nav: 单位净值
                - accum_nav: 累计净值
                - daily_return: 日增长率(%)
                - source: 数据来源
        """
        errors = []
        
        if source == 'auto':
            # 新的数据源优先级: Tushare > Akshare
            # 尝试 Tushare (PRIMARY)
            if self.tushare_pro:
                try:
                    tushare_code = self._convert_to_tushare_format(fund_code)
                    df = self._get_nav_from_tushare(tushare_code)
                    logger.info(f"使用 PRIMARY 数据源 Tushare 获取 {fund_code}")
                    
                    # 日期过滤
                    if start_date:
                        df = df[df['date'] >= start_date]
                    if end_date:
                        df = df[df['date'] <= end_date]
                    return df
                except Exception as e:
                    error_msg = f"Tushare获取 {fund_code} 失败: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
            
            # 尝试 Akshare (BACKUP_1)
            try:
                df = self._get_nav_from_akshare(fund_code)
                logger.info(f"使用 BACKUP_1 数据源 Akshare 获取 {fund_code}")
                
                # 日期过滤
                if start_date:
                    df = df[df['date'] >= start_date]
                if end_date:
                    df = df[df['date'] <= end_date]
                return df
            except Exception as e:
                error_msg = f"Akshare获取 {fund_code} 失败: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)
            
            # 都失败了
            raise ValueError(f"所有数据源获取 {fund_code} 失败: {'; '.join(errors)}")
        
        # 指定数据源
        if source == 'akshare':
            df = self._get_nav_from_akshare(fund_code)
        elif source == 'tushare':
            tushare_code = self._convert_to_tushare_format(fund_code)
            df = self._get_nav_from_tushare(tushare_code)
        else:
            raise ValueError(f"未知数据源: {source}")
        
        # 日期过滤
        if start_date:
            df = df[df['date'] >= start_date]
        if end_date:
            df = df[df['date'] <= end_date]
        
        return df
    
    def _get_nav_from_akshare(self, fund_code: str) -> pd.DataFrame:
        """从akshare获取净值历史"""
        start_time = time.time()
        
        try:
            df = ak.fund_open_fund_daily_em(symbol=fund_code)
            
            # 标准化列名
            column_mapping = {
                '净值日期': 'date',
                '单位净值': 'nav',
                '累计净值': 'accum_nav',
                '日增长率': 'daily_return',
                '申购状态': 'purchase_status',
                '赎回状态': 'redeem_status'
            }
            df = df.rename(columns=column_mapping)
            df['source'] = 'akshare'
            
            # 数据类型转换
            df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
            df['accum_nav'] = pd.to_numeric(df['accum_nav'], errors='coerce')
            df['daily_return'] = pd.to_numeric(df['daily_return'], errors='coerce')
            
            # 记录成功
            elapsed = time.time() - start_time
            self.health.record_success('akshare', elapsed)
            
            logger.debug(f"从akshare获取 {fund_code} 历史净值 {len(df)} 条，耗时 {elapsed:.3f}s")
            return df
            
        except Exception as e:
            elapsed = time.time() - start_time
            self.health.record_fail('akshare', str(e))
            logger.error(f"从akshare获取 {fund_code} 失败: {e}")
            raise
    
    def _get_nav_from_tushare(self, fund_code: str) -> pd.DataFrame:
        """从tushare获取净值历史"""
        if not self.tushare_pro:
            raise ValueError("Tushare未初始化")
        
        start_time = time.time()
        
        try:
            df = self.tushare_pro.fund_nav(ts_code=fund_code)
            
            # 标准化列名
            column_mapping = {
                'nav_date': 'date',
                'unit_nav': 'nav',
                'accum_nav': 'accum_nav',
                'nv_daily_growth': 'daily_return'
            }
            df = df.rename(columns=column_mapping)
            df['source'] = 'tushare'
            
            # 数据类型转换
            df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
            df['accum_nav'] = pd.to_numeric(df['accum_nav'], errors='coerce')
            df['daily_return'] = pd.to_numeric(df['daily_return'], errors='coerce')
            
            # 记录成功
            elapsed = time.time() - start_time
            self.health.record_success('tushare', elapsed)
            
            logger.debug(f"从tushare获取 {fund_code} 历史净值 {len(df)} 条，耗时 {elapsed:.3f}s")
            return df
            
        except Exception as e:
            elapsed = time.time() - start_time
            self.health.record_fail('tushare', str(e))
            logger.error(f"从tushare获取 {fund_code} 失败: {e}")
            raise
    
    def get_fund_latest_nav(self, fund_code: str) -> Optional[Dict]:
        """
        获取基金最新净值（带自动降级）
        
        数据源优先级:
        1. PRIMARY: Tushare (稳定性高, 支持 .OF 格式)
        2. BACKUP_1: Akshare (数据全面, 格式兼容性好)
        3. BACKUP_2: Sina/Eastmoney (实时性好, 但不支持所有基金)
        
        Args:
            fund_code: 基金代码
        
        Returns:
            dict: 最新净值数据，失败返回None
        """
        # 记录所有失败的错误信息
        errors = []
        
        # 尝试 PRIMARY 数据源: Tushare
        if self.tushare_pro:
            try:
                # Tushare需要 .OF 后缀格式
                tushare_code = self._convert_to_tushare_format(fund_code)
                df = self._get_nav_from_tushare(tushare_code)
                if not df.empty:
                    latest = df.iloc[-1]
                    result = self._standardize_nav_data(latest, 'tushare')
                    # 转换回原始code格式
                    result['fund_code'] = fund_code
                    logger.info(f"从 Tushare 成功获取 {fund_code} 最新净值")
                    return result
            except Exception as e:
                error_msg = f"Tushare获取 {fund_code} 失败: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)
        else:
            logger.warning("Tushare 未初始化，跳过 PRIMARY 数据源")
        
        # 尝试 BACKUP_1 数据源: Akshare
        try:
            df = self._get_nav_from_akshare(fund_code)
            if not df.empty:
                latest = df.iloc[-1]
                result = self._standardize_nav_data(latest, 'akshare')
                result['fund_code'] = fund_code
                logger.info(f"从 Akshare 成功获取 {fund_code} 最新净值 (BACKUP_1)")
                return result
        except Exception as e:
            error_msg = f"Akshare获取 {fund_code} 失败: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
        
        # 尝试 BACKUP_2 数据源: Sina/Eastmoney
        result = self._get_nav_from_fallback(fund_code)
        if result:
            logger.info(f"从 Fallback 成功获取 {fund_code} 最新净值 (BACKUP_2)")
            return result
        
        # 所有数据源都失败
        logger.error(f"所有数据源获取 {fund_code} 失败: {'; '.join(errors)}")
        return None
    
    def _convert_to_tushare_format(self, fund_code: str) -> str:
        """
        将基金代码转换为 Tushare 格式 (.OF 后缀)
        
        Args:
            fund_code: 原始基金代码, 如 '021539'
        
        Returns:
            str: Tushare格式代码, 如 '021539.OF'
        """
        if not fund_code.endswith('.OF'):
            return f"{fund_code}.OF"
        return fund_code
    
    def _get_nav_from_fallback(self, fund_code: str) -> Optional[Dict]:
        """
        从备用数据源获取净值 (Sina/Eastmoney)
        
        Args:
            fund_code: 基金代码
        
        Returns:
            dict: 标准化净值数据，失败返回None
        """
        # 尝试 Sina
        try:
            import requests
            # Sina API
            url = f"https://hq.sinajs.cn/list=f_{fund_code}"
            headers = {'Referer': 'https://finance.sina.com.cn'}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.text
                if f"f_{fund_code}=\"" in data:
                    parts = data.split('"')[1].split(',')
                    if len(parts) >= 5:
                        return {
                            'fund_code': fund_code,
                            'date': parts[0] if len(parts) > 0 else '',
                            'nav': float(parts[1]) if len(parts) > 1 else 0.0,
                            'accum_nav': float(parts[2]) if len(parts) > 2 else 0.0,
                            'daily_return': float(parts[3]) if len(parts) > 3 else 0.0,
                            'source': 'sina'
                        }
        except Exception as e:
            logger.warning(f"Sina获取 {fund_code} 失败: {e}")
        
        # 尝试 Eastmoney
        try:
            import akshare as ak
            df = ak.fund_open_fund_daily_em(symbol=fund_code)
            if not df.empty:
                latest = df.iloc[0]  # EM数据通常是最新在前
                return {
                    'fund_code': fund_code,
                    'date': latest.get('净值日期', ''),
                    'nav': float(latest.get('单位净值', 0)),
                    'accum_nav': float(latest.get('累计净值', 0)),
                    'daily_return': float(latest.get('日增长率', 0)),
                    'source': 'eastmoney'
                }
        except Exception as e:
            logger.warning(f"Eastmoney获取 {fund_code} 失败: {e}")
        
        return None
    
    def _standardize_nav_data(self, row: pd.Series, source: str) -> Dict:
        """标准化净值数据"""
        return {
            'fund_code': row.get('ts_code', ''),
            'date': row.get('date', ''),
            'nav': float(row.get('nav', 0)),
            'accum_nav': float(row.get('accum_nav', 0)),
            'daily_return': float(row.get('daily_return', 0)),
            'source': source
        }
    
    def get_qdii_fund_data(self, fund_code: str) -> Optional[Dict]:
        """
        获取QDII基金数据（特殊处理）
        
        QDII基金特点:
        1. 净值T+2更新（普通基金T+1）
        2. 受汇率影响
        3. 无实时估算
        
        Args:
            fund_code: 基金代码
        
        Returns:
            dict: QDII基金数据
        """
        logger.info(f"获取QDII基金 {fund_code} 数据")
        
        try:
            # QDII基金使用新的数据源优先级获取历史数据
            # 尝试顺序: Tushare > Akshare > Fallback
            nav_history = None
            source_used = None
            
            # 尝试 Tushare (PRIMARY)
            if self.tushare_pro:
                try:
                    tushare_code = self._convert_to_tushare_format(fund_code)
                    nav_history = self._get_nav_from_tushare(tushare_code)
                    source_used = 'tushare'
                    logger.info(f"QDII基金 {fund_code} 使用 Tushare 数据")
                except Exception as e:
                    logger.warning(f"QDII基金 {fund_code} Tushare获取失败: {e}")
            
            # 尝试 Akshare (BACKUP_1)
            if nav_history is None or nav_history.empty:
                try:
                    nav_history = self._get_nav_from_akshare(fund_code)
                    source_used = 'akshare'
                    logger.info(f"QDII基金 {fund_code} 使用 Akshare 数据 (BACKUP_1)")
                except Exception as e:
                    logger.warning(f"QDII基金 {fund_code} Akshare获取失败: {e}")
            
            if nav_history is None or nav_history.empty:
                logger.warning(f"QDII基金 {fund_code} 无历史数据")
                return None
            
            # 获取最新数据(T+2)
            latest = nav_history.iloc[-1]
            
            # 获取前一日数据
            previous = nav_history.iloc[-2] if len(nav_history) > 1 else latest
            
            # 计算更多统计指标
            returns = {
                'latest': float(latest.get('daily_return', 0)),
                'week': self._calc_period_return(nav_history, 5),
                'month': self._calc_period_return(nav_history, 20),
                'quarter': self._calc_period_return(nav_history, 60),
                'year': self._calc_period_return(nav_history, 250)
            }
            
            return {
                'fund_code': fund_code,
                'fund_type': 'QDII',
                'current_nav': float(latest.get('nav', 0)),
                'previous_nav': float(previous.get('nav', 0)),
                'daily_return': returns['latest'],
                'nav_date': latest.get('date', ''),
                'returns': returns,
                'data_source': source_used or latest.get('source', 'unknown'),
                'is_qdii': True,
                'update_delay': 'T+2',
                'note': 'QDII基金净值T+2更新，受汇率影响'
            }
            
        except Exception as e:
            logger.error(f"获取QDII基金 {fund_code} 数据失败: {e}")
            return None
    
    def _calc_period_return(self, df: pd.DataFrame, days: int) -> float:
        """计算指定周期的收益率"""
        if len(df) < days + 1:
            return 0.0
        
        start_nav = df.iloc[-days-1]['nav']
        end_nav = df.iloc[-1]['nav']
        
        if start_nav > 0:
            return round((end_nav - start_nav) / start_nav * 100, 2)
        return 0.0
    
    def get_fund_basic_info(self, fund_code: str, source: str = 'auto') -> Optional[Dict]:
        """
        获取基金基本信息
        
        Args:
            fund_code: 基金代码
            source: 数据源
        
        Returns:
            dict: 基金基本信息
        """
        if source == 'auto':
            source = self.health.get_recommend_source()
        
        if source == 'akshare':
            return self._get_basic_info_from_akshare(fund_code)
        elif source == 'tushare':
            return self._get_basic_info_from_tushare(fund_code)
        
        return None
    
    def _get_basic_info_from_akshare(self, fund_code: str) -> Optional[Dict]:
        """从akshare获取基本信息"""
        try:
            fund_info = ak.fund_open_fund_info_em(symbol=fund_code, indicator="基本信息")
            
            if fund_info.empty:
                return None
            
            info_dict = {}
            for _, row in fund_info.iterrows():
                info_dict[row['项目']] = row['数值']
            
            return {
                'fund_code': fund_code,
                'fund_name': info_dict.get('基金简称', ''),
                'fund_type': info_dict.get('基金类型', ''),
                'establish_date': info_dict.get('成立日期', ''),
                'fund_company': info_dict.get('基金管理人', ''),
                'fund_manager': info_dict.get('基金经理', ''),
                'management_fee': float(info_dict.get('管理费率', 0)),
                'custody_fee': float(info_dict.get('托管费率', 0)),
                'source': 'akshare'
            }
            
        except Exception as e:
            logger.error(f"从akshare获取 {fund_code} 基本信息失败: {e}")
            return None
    
    def _get_basic_info_from_tushare(self, fund_code: str) -> Optional[Dict]:
        """从tushare获取基本信息"""
        if not self.tushare_pro:
            return None
        
        try:
            fund_info = self.tushare_pro.fund_basic(ts_code=fund_code)
            
            if fund_info.empty:
                return None
            
            row = fund_info.iloc[0]
            return {
                'fund_code': fund_code,
                'fund_name': row.get('name', ''),
                'fund_type': row.get('invest_type', ''),
                'establish_date': row.get('setup_date', ''),
                'fund_company': row.get('management', ''),
                'fund_manager': row.get('manager', ''),
                'source': 'tushare'
            }
            
        except Exception as e:
            logger.error(f"从tushare获取 {fund_code} 基本信息失败: {e}")
            return None
    
    def get_health_status(self) -> Dict:
        """获取数据源健康状态"""
        return {
            'akshare': {
                'success_rate': f"{self.health.get_success_rate('akshare')*100:.1f}%",
                'avg_response_time': f"{self.health.akshare['avg_time']:.3f}s",
                'total_requests': self.health.akshare['success'] + self.health.akshare['fail'],
                'last_error': self.health.akshare['last_error']
            },
            'tushare': {
                'success_rate': f"{self.health.get_success_rate('tushare')*100:.1f}%",
                'avg_response_time': f"{self.health.tushare['avg_time']:.3f}s",
                'total_requests': self.health.tushare['success'] + self.health.tushare['fail'],
                'last_error': self.health.tushare['last_error']
            },
            'recommend_source': self.health.get_recommend_source()
        }


# 便捷函数 - 与现有接口兼容
def get_fund_data_with_fallback(fund_code: str, tushare_token: Optional[str] = None) -> Dict:
    """
    获取基金数据（带自动降级）
    与现有接口兼容的便捷函数
    
    Args:
        fund_code: 基金代码
        tushare_token: Tushare token(可选)
    
    Returns:
        dict: 基金数据
    """
    fetcher = MultiSourceFundData(tushare_token=tushare_token)
    
    # 判断是否为QDII
    if fetcher.is_qdii_fund(fund_code):
        return fetcher.get_qdii_fund_data(fund_code)
    
    return fetcher.get_fund_latest_nav(fund_code)


# 测试代码
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # 测试基金
    test_fund = "021539"  # 华安法国CAC40ETF发起式联接(QDII)A
    
    # 创建获取器
    fetcher = MultiSourceFundData()
    
    # 测试QDII数据获取
    print("=" * 60)
    print("测试 QDII 基金数据获取")
    print("=" * 60)
    
    qdii_data = fetcher.get_qdii_fund_data(test_fund)
    print(f"QDII数据: {qdii_data}")
    
    # 测试健康状态
    print("\n" + "=" * 60)
    print("数据源健康状态")
    print("=" * 60)
    print(fetcher.get_health_status())
