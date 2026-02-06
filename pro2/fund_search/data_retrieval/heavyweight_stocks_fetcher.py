#!/usr/bin/env python
# coding: utf-8

"""
重仓股数据获取模块
通过akshare API获取基金重仓股数据，支持错误处理和备用数据源
支持数据库存储，当接口获取太慢时从数据库读取
"""

import akshare as ak
import pandas as pd
import logging
import time
import requests
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import json
from functools import wraps

logger = logging.getLogger(__name__)


class DataSourceError(Exception):
    """数据源错误基类"""
    pass


class AkshareAPIError(DataSourceError):
    """akshare API错误"""
    pass


class NetworkError(DataSourceError):
    """网络错误"""
    pass


class DataValidationError(DataSourceError):
    """数据验证错误"""
    pass


def retry_on_error(max_retries=3, delay=1):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (requests.RequestException, AkshareAPIError) as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"尝试 {attempt + 1}/{max_retries} 失败: {e}，{delay}秒后重试...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator


class HeavyweightStocksFetcher:
    """重仓股数据获取器
    
    支持多级缓存策略：
    1. 内存缓存（最快，5分钟）
    2. 数据库缓存（较快，7天有效期）
    3. API接口获取（最慢，但最新）
    """
    
    def __init__(self, db_manager=None, cache_duration=300):  # 默认缓存5分钟
        self._cache = {}
        self._cache_duration = cache_duration
        self._cache_timestamps = {}
        self._db_manager = db_manager  # 数据库管理器
        
        # 备用数据源配置
        self._fallback_sources = [
            self._fetch_from_akshare,
            self._fetch_from_eastmoney,
            self._fetch_from_sina
        ]
        
        # 数据库缓存有效期（天）
        self._db_cache_max_age = 7
    
    def _get_cache_key(self, fund_code: str, date: Optional[str] = None) -> str:
        """生成缓存键"""
        return f"{fund_code}_{date or 'latest'}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._cache or cache_key not in self._cache_timestamps:
            return False
        
        elapsed = time.time() - self._cache_timestamps[cache_key]
        return elapsed < self._cache_duration
    
    def _get_cached_data(self, cache_key: str) -> Optional[List[Dict]]:
        """获取缓存数据"""
        if self._is_cache_valid(cache_key):
            logger.info(f"使用缓存数据: {cache_key}")
            return self._cache[cache_key]
        return None
    
    def _set_cached_data(self, cache_key: str, data: List[Dict]):
        """设置缓存数据"""
        self._cache[cache_key] = data
        self._cache_timestamps[cache_key] = time.time()
        logger.info(f"数据已缓存: {cache_key}")
    
    @retry_on_error(max_retries=3, delay=1)
    def _fetch_from_akshare(self, fund_code: str, date: Optional[str] = None) -> List[Dict]:
        """
        从akshare获取重仓股数据
        
        Args:
            fund_code: 基金代码
            date: 报告期日期（可选）
            
        Returns:
            List[Dict]: 重仓股数据列表
        """
        try:
            logger.info(f"从akshare获取基金 {fund_code} 的重仓股数据...")
            
            # 使用akshare获取基金持仓数据
            df = ak.fund_portfolio_hold_em(symbol=fund_code, date=date)
            
            if df is None or df.empty:
                raise AkshareAPIError(f"akshare返回空数据: {fund_code}")
            
            # 验证数据
            required_columns = ['股票名称', '股票代码', '占净值比例', '持仓市值']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise DataValidationError(f"数据缺少必要字段: {missing_columns}")
            
            # 转换为标准格式
            stocks = []
            for _, row in df.head(10).iterrows():  # 只取前10
                stock = {
                    'name': str(row['股票名称']).strip(),
                    'code': str(row['股票代码']).strip(),
                    'holding_ratio': self._parse_percentage(row['占净值比例']),
                    'market_value': self._parse_market_value(row['持仓市值']),
                    'change_percent': self._parse_change_percent(row.get('涨跌幅', '--'))
                }
                stocks.append(stock)
            
            logger.info(f"成功从akshare获取 {len(stocks)} 条重仓股数据")
            return stocks
            
        except Exception as e:
            logger.error(f"从akshare获取数据失败: {e}")
            raise AkshareAPIError(f"akshare数据获取失败: {e}")
    
    @retry_on_error(max_retries=2, delay=2)
    def _fetch_from_eastmoney(self, fund_code: str, date: Optional[str] = None) -> List[Dict]:
        """
        从东方财富备用接口获取数据
        
        Args:
            fund_code: 基金代码
            date: 报告期日期（可选）
            
        Returns:
            List[Dict]: 重仓股数据列表
        """
        try:
            logger.info(f"从东方财富备用接口获取基金 {fund_code} 的重仓股数据...")
            
            # 东方财富API接口
            url = f"http://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 解析JavaScript数据
            content = response.text
            
            # 提取持仓数据（简化处理，实际需要更复杂的解析）
            # 这里作为备用方案，如果akshare失败才使用
            
            logger.warning("东方财富备用接口暂未实现完整解析逻辑")
            raise DataSourceError("东方财富备用接口数据解析未完成")
            
        except Exception as e:
            logger.error(f"从东方财富获取数据失败: {e}")
            raise DataSourceError(f"东方财富数据获取失败: {e}")
    
    @retry_on_error(max_retries=2, delay=2)
    def _fetch_from_sina(self, fund_code: str, date: Optional[str] = None) -> List[Dict]:
        """
        从新浪财经备用接口获取数据
        
        Args:
            fund_code: 基金代码
            date: 报告期日期（可选）
            
        Returns:
            List[Dict]: 重仓股数据列表
        """
        try:
            logger.info(f"从新浪财经备用接口获取基金 {fund_code} 的重仓股数据...")
            
            # 新浪财经API
            url = f"http://stock.finance.sina.com.cn/fundInfo/view/FundInfo_ZC.php?symbol={fund_code}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            logger.warning("新浪财经备用接口暂未实现完整解析逻辑")
            raise DataSourceError("新浪财经备用接口数据解析未完成")
            
        except Exception as e:
            logger.error(f"从新浪财经获取数据失败: {e}")
            raise DataSourceError(f"新浪财经数据获取失败: {e}")
    
    def _parse_percentage(self, value: Any) -> str:
        """解析百分比值"""
        try:
            if pd.isna(value) or value == '--':
                return '--'
            if isinstance(value, str):
                value = value.replace('%', '').strip()
            pct = float(value)
            return f"{pct:.1f}%"
        except:
            return '--'
    
    def _parse_market_value(self, value: Any) -> str:
        """解析市值值"""
        try:
            if pd.isna(value) or value == '--':
                return '--'
            if isinstance(value, str):
                value = value.replace(',', '').replace('万', '').strip()
            mv = float(value)
            return f"{int(mv):,}"
        except:
            return '--'
    
    def _parse_change_percent(self, value: Any) -> str:
        """解析涨跌幅"""
        try:
            if pd.isna(value) or value == '--':
                return '--'
            if isinstance(value, str):
                value = value.replace('%', '').strip()
            change = float(value)
            return f"{change:+.2f}%"
        except:
            return '--'
    
    def fetch_heavyweight_stocks(self, fund_code: str, date: Optional[str] = None, 
                                  use_cache: bool = True) -> Dict[str, Any]:
        """
        获取重仓股数据（主入口）
        
        缓存优先级：内存缓存 > 数据库缓存 > API接口
        
        Args:
            fund_code: 基金代码
            date: 报告期日期（可选，格式：YYYYMMDD）
            use_cache: 是否使用缓存
            
        Returns:
            Dict: 包含以下字段：
                - success: bool, 是否成功
                - data: List[Dict], 重仓股数据
                - source: str, 数据来源
                - error: str, 错误信息（如果失败）
                - timestamp: str, 数据时间戳
        """
        cache_key = self._get_cache_key(fund_code, date)
        
        # 1. 检查内存缓存
        if use_cache:
            cached_data = self._get_cached_data(cache_key)
            if cached_data is not None:
                return {
                    'success': True,
                    'data': cached_data,
                    'source': 'cache',
                    'timestamp': datetime.now().isoformat()
                }
        
        # 2. 检查数据库缓存
        if use_cache and self._db_manager:
            try:
                db_data = self._db_manager.get_heavyweight_stocks(
                    fund_code, 
                    max_age_days=self._db_cache_max_age
                )
                if db_data:
                    # 存入内存缓存
                    self._set_cached_data(cache_key, db_data)
                    return {
                        'success': True,
                        'data': db_data,
                        'source': 'database',
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                logger.warning(f"从数据库获取缓存失败: {e}")
        
        # 3. 从API获取数据
        last_error = None
        for source_func in self._fallback_sources:
            try:
                data = source_func(fund_code, date)
                
                # 验证数据
                if not data or len(data) == 0:
                    raise DataValidationError("获取的数据为空")
                
                # 存入内存缓存
                if use_cache:
                    self._set_cached_data(cache_key, data)
                
                # 存入数据库缓存
                if self._db_manager:
                    try:
                        self._db_manager.save_heavyweight_stocks(fund_code, data)
                    except Exception as db_e:
                        logger.warning(f"保存到数据库失败: {db_e}")
                
                return {
                    'success': True,
                    'data': data,
                    'source': source_func.__name__.replace('_fetch_from_', ''),
                    'timestamp': datetime.now().isoformat()
                }
                
            except Exception as e:
                last_error = e
                logger.warning(f"数据源 {source_func.__name__} 失败: {e}")
                continue
        
        # 所有数据源都失败
        error_msg = f"所有数据源均失败: {last_error}"
        logger.error(error_msg)
        
        return {
            'success': False,
            'data': [],
            'source': 'none',
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        }
    
    def fetch_heavyweight_stocks_batch(self, fund_codes: List[str], 
                                       date: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        批量获取多个基金的重仓股数据
        
        优先从数据库获取，缺失的数据再从API获取
        
        Args:
            fund_codes: 基金代码列表
            date: 报告期日期（可选）
            
        Returns:
            Dict: 以基金代码为key的结果字典
        """
        results = {}
        
        if not fund_codes:
            return results
        
        # 1. 尝试从数据库批量获取
        db_data = {}
        missing_funds = fund_codes
        
        if self._db_manager:
            try:
                db_data, missing_funds = self._db_manager.get_all_heavyweight_stocks_for_funds(
                    fund_codes, 
                    max_age_days=self._db_cache_max_age
                )
                
                # 数据库中获取到的数据直接放入结果
                for fund_code, stocks in db_data.items():
                    results[fund_code] = {
                        'success': True,
                        'data': stocks,
                        'source': 'database',
                        'timestamp': datetime.now().isoformat()
                    }
                    # 同时更新内存缓存
                    cache_key = self._get_cache_key(fund_code, date)
                    self._set_cached_data(cache_key, stocks)
                
                logger.info(f"批量获取：从数据库获取 {len(db_data)} 只基金，{len(missing_funds)} 只需要从API获取")
            except Exception as e:
                logger.warning(f"从数据库批量获取失败: {e}")
                missing_funds = fund_codes
        
        # 2. 从API获取缺失的数据
        for fund_code in missing_funds:
            result = self.fetch_heavyweight_stocks(fund_code, date, use_cache=True)
            results[fund_code] = result
        
        return results
    
    def clear_cache(self, fund_code: Optional[str] = None):
        """清除缓存"""
        if fund_code:
            # 清除特定基金的缓存
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(fund_code)]
            for key in keys_to_remove:
                self._cache.pop(key, None)
                self._cache_timestamps.pop(key, None)
            logger.info(f"已清除基金 {fund_code} 的内存缓存")
        else:
            # 清除所有缓存
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.info("已清除所有内存缓存")
    
    def clear_database_cache(self, fund_code: Optional[str] = None) -> bool:
        """
        清除数据库中的缓存数据
        
        Args:
            fund_code: 基金代码，为None则清除所有
            
        Returns:
            bool: 是否成功
        """
        if not self._db_manager:
            logger.warning("数据库管理器未初始化，无法清除数据库缓存")
            return False
        
        try:
            if fund_code:
                sql = "DELETE FROM fund_heavyweight_stocks WHERE fund_code = :fund_code"
                self._db_manager.execute_sql(sql, {'fund_code': fund_code})
                logger.info(f"已清除基金 {fund_code} 的数据库缓存")
            else:
                sql = "TRUNCATE TABLE fund_heavyweight_stocks"
                self._db_manager.execute_sql(sql)
                logger.info("已清除所有数据库缓存")
            return True
        except Exception as e:
            logger.error(f"清除数据库缓存失败: {e}")
            return False


# 全局实例
_fetcher_instance = None

def get_fetcher(db_manager=None) -> HeavyweightStocksFetcher:
    """
    获取全局数据获取器实例
    
    Args:
        db_manager: 数据库管理器实例，用于持久化缓存
        
    Returns:
        HeavyweightStocksFetcher: 数据获取器实例
    """
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = HeavyweightStocksFetcher(db_manager=db_manager)
    elif db_manager is not None and _fetcher_instance._db_manager is None:
        # 如果之前创建的实例没有db_manager，现在有传入，则更新
        _fetcher_instance._db_manager = db_manager
    return _fetcher_instance


def init_fetcher(db_manager):
    """
    初始化数据获取器的数据库连接
    
    Args:
        db_manager: 数据库管理器实例
    """
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = HeavyweightStocksFetcher(db_manager=db_manager)
    else:
        _fetcher_instance._db_manager = db_manager
    logger.info("重仓股数据获取器已初始化数据库连接")


def fetch_heavyweight_stocks(fund_code: str, date: Optional[str] = None, 
                              use_cache: bool = True) -> Dict[str, Any]:
    """
    便捷函数：获取重仓股数据
    
    Args:
        fund_code: 基金代码
        date: 报告期日期（可选）
        use_cache: 是否使用缓存
        
    Returns:
        Dict: 重仓股数据结果
    """
    fetcher = get_fetcher()
    return fetcher.fetch_heavyweight_stocks(fund_code, date, use_cache)


def fetch_heavyweight_stocks_batch(fund_codes: List[str], 
                                   date: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    便捷函数：批量获取重仓股数据
    
    Args:
        fund_codes: 基金代码列表
        date: 报告期日期（可选）
        
    Returns:
        Dict: 以基金代码为key的结果字典
    """
    fetcher = get_fetcher()
    return fetcher.fetch_heavyweight_stocks_batch(fund_codes, date)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 测试获取数据
    result = fetch_heavyweight_stocks("000001", use_cache=False)
    print(json.dumps(result, ensure_ascii=False, indent=2))
