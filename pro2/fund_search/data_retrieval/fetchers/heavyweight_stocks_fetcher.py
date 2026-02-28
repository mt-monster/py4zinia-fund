#!/usr/bin/env python
# coding: utf-8

"""
重仓股数据获取模块
通过 Tushare API 获取基金重仓股数据，支持错误处理和备用数据源
支持数据库存储，当接口获取太慢时从数据库读取
"""

import pandas as pd
import logging
import time
import requests
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import json
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        
        # 备用数据源配置（akshare 优先，因对QDII基金覆盖更好）
        self._fallback_sources = [
            self._fetch_from_akshare,
            self._fetch_from_eastmoney_js,  # 东方财富JS接口（免费、覆盖QDII）
            self._fetch_from_tushare,        # Tushare对QDII覆盖不足，作为备用
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
    def _fetch_from_tushare(self, fund_code: str, date: Optional[str] = None) -> List[Dict]:
        """
        从 Tushare 获取重仓股数据（主要数据源）

        Tushare fund_portfolio 接口字段：
        - symbol: 股票代码 (如 000333.SZ)
        - mkv: 持仓市值
        - amount: 持股数
        - stk_mkv_ratio: 占净值比例

        Args:
            fund_code: 基金代码
            date: 报告期日期（可选）

        Returns:
            List[Dict]: 重仓股数据列表
        """
        try:
            import tushare as ts

            logger.info(f"从 Tushare 获取基金 {fund_code} 的重仓股数据...")

            # 获取 token
            token = None
            try:
                from shared.enhanced_config import DATA_SOURCE_CONFIG
                token = DATA_SOURCE_CONFIG.get('tushare', {}).get('token')
            except ImportError:
                token = '5ff19facae0e5b26a407d491d33707a9884a39a714a0d76b6495725b'

            ts_pro = ts.pro_api(token)

            # Tushare 需要 .OF 后缀
            ts_code = fund_code if fund_code.endswith('.OF') else f"{fund_code}.OF"

            # 获取基金持仓数据
            df = ts_pro.fund_portfolio(ts_code=ts_code)

            if df is None or df.empty:
                raise DataSourceError(f"Tushare 返回空数据: {fund_code}")

            # 批量获取股票名称（可选）
            stock_names = {}
            try:
                symbols = df['symbol'].tolist()
                # 简化：从 symbol 提取代码，名称后续通过其他接口补全或显示代码
            except Exception:
                pass

            # 转换为标准格式
            stocks = []
            for _, row in df.head(10).iterrows():
                symbol = str(row.get('symbol', ''))
                # 从 symbol 提取纯代码（去掉 .SZ/.SH 后缀）
                code = symbol.split('.')[0] if '.' in symbol else symbol

                stock = {
                    'name': '',  # Tushare 不返回股票名称，由前端通过代码查询或显示代码
                    'code': code,
                    'holding_ratio': self._parse_percentage(row.get('stk_mkv_ratio', '--')),
                    'market_value': self._parse_market_value(row.get('mkv', '--')),
                    'change_percent': '--'
                }
                stocks.append(stock)

            logger.info(f"成功从 Tushare 获取 {len(stocks)} 条重仓股数据")
            return stocks

        except Exception as e:
            logger.error(f"从 Tushare 获取数据失败: {e}")
            raise DataSourceError(f"Tushare 数据获取失败: {e}")

    @retry_on_error(max_retries=3, delay=1)
    def _fetch_from_akshare(self, fund_code: str, date: Optional[str] = None) -> List[Dict]:
        """
        从 akshare 获取重仓股数据（备用数据源）

        Args:
            fund_code: 基金代码
            date: 报告期日期（可选）

        Returns:
            List[Dict]: 重仓股数据列表
        """
        try:
            import akshare as ak

            logger.info(f"从 akshare 获取基金 {fund_code} 的重仓股数据...")

            # 使用 akshare 获取基金持仓数据
            df = ak.fund_portfolio_hold_em(symbol=fund_code, date=date)

            if df is None or df.empty:
                raise DataSourceError(f"akshare 返回空数据: {fund_code}")

            # 列名映射（兼容新旧版本）
            col_map = {
                '股票名称': ['股票名称', '名称', 'stk_name'],
                '股票代码': ['股票代码', '代码', 'stk_code'],
                '占净值比例': ['占净值比例', '持仓比例', 'proportion', '占比'],
                '持仓市值': ['持仓市值', '市值', 'amount', '持仓金额']
            }

            def find_col(df, keys):
                for k in keys:
                    if k in df.columns:
                        return k
                return None

            name_col = find_col(df, col_map['股票名称'])
            code_col = find_col(df, col_map['股票代码'])
            ratio_col = find_col(df, col_map['占净值比例'])
            value_col = find_col(df, col_map['持仓市值'])

            if not all([name_col, code_col, ratio_col]):
                raise DataSourceError(f"akshare 数据缺少必要字段，现有列: {list(df.columns)}")

            # 转换为标准格式
            stocks = []
            for _, row in df.head(10).iterrows():
                stock = {
                    'name': str(row[name_col]).strip(),
                    'code': str(row[code_col]).strip(),
                    'holding_ratio': self._parse_percentage(row[ratio_col]),
                    'market_value': self._parse_market_value(row[value_col]) if value_col else '--',
                    'change_percent': '--'
                }
                stocks.append(stock)

            logger.info(f"成功从 akshare 获取 {len(stocks)} 条重仓股数据")
            return stocks

        except Exception as e:
            logger.error(f"从 akshare 获取数据失败: {e}")
            raise DataSourceError(f"akshare 数据获取失败: {e}")
    
    @retry_on_error(max_retries=2, delay=2)
    def _fetch_from_eastmoney_js(self, fund_code: str, date: Optional[str] = None) -> List[Dict]:
        """
        从东方财富JS接口获取重仓股数据（免费、覆盖QDII基金）
        
        接口返回的JS变量：
        - stockCodes: 持仓股票代码列表
        - stockNames: 持仓股票名称列表
        - stockNewRatio: 持仓占比列表
        
        Args:
            fund_code: 基金代码
            date: 报告期日期（可选，此接口不支持指定日期）
            
        Returns:
            List[Dict]: 重仓股数据列表
        """
        import re
        
        try:
            logger.info(f"从东方财富JS接口获取基金 {fund_code} 的重仓股数据...")
            
            url = f"http://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            content = response.text
            
            # 检查是否返回有效数据
            if len(content) < 1000 or 'fS_code' not in content:
                raise DataSourceError(f"东方财富JS接口返回数据异常: {fund_code}")
            
            # 解析JS变量
            def extract_array(text: str, var_name: str) -> List[str]:
                """提取JS数组变量"""
                # 匹配 var name = [...] 或 var name=[...]
                pattern = rf'var\s+{var_name}\s*=\s*(\[[^\]]*\])'
                match = re.search(pattern, text)
                if match:
                    try:
                        # 安全解析JS数组
                        array_str = match.group(1)
                        # 处理JS数组字符串
                        items = re.findall(r'"([^"]*)"', array_str)
                        return items
                    except Exception:
                        pass
                return []
            
            def extract_float_array(text: str, var_name: str) -> List[float]:
                """提取JS浮点数组变量"""
                pattern = rf'var\s+{var_name}\s*=\s*(\[[^\]]*\])'
                match = re.search(pattern, text)
                if match:
                    try:
                        array_str = match.group(1)
                        # 提取数字
                        numbers = re.findall(r'[-\d.]+', array_str)
                        return [float(n) for n in numbers]
                    except Exception:
                        pass
                return []
            
            # 提取持仓数据
            stock_codes = extract_array(content, 'stockCodes')
            stock_names = extract_array(content, 'stockNames')
            stock_ratios = extract_float_array(content, 'stockNewRatio')
            
            if not stock_codes:
                # 可能是FOF基金，无股票持仓
                logger.info(f"基金 {fund_code} 无股票持仓数据（可能是FOF或债券基金）")
                raise DataSourceError(f"基金 {fund_code} 无股票持仓数据")
            
            # 组合数据
            stocks = []
            count = min(len(stock_codes), 10)  # 最多取前10只
            
            for i in range(count):
                code = stock_codes[i] if i < len(stock_codes) else ''
                name = stock_names[i] if i < len(stock_names) else ''
                ratio = stock_ratios[i] if i < len(stock_ratios) else 0
                
                # 清理股票代码（去掉市场后缀如105、116等）
                # GOOGL105 -> GOOGL, 02259116 -> 02259
                clean_code = re.sub(r'\d+$', '', code) if code else ''
                if not clean_code:
                    clean_code = code
                
                stock = {
                    'name': name,
                    'code': clean_code,
                    'holding_ratio': f"{ratio:.2f}%" if ratio else '--',
                    'market_value': '--',  # JS接口不提供市值
                    'change_percent': '--'
                }
                stocks.append(stock)
            
            if not stocks:
                raise DataSourceError(f"东方财富JS接口解析失败: {fund_code}")
            
            logger.info(f"成功从东方财富JS接口获取 {len(stocks)} 条重仓股数据")
            return stocks
            
        except DataSourceError:
            raise
        except Exception as e:
            logger.error(f"从东方财富JS接口获取数据失败: {e}")
            raise DataSourceError(f"东方财富JS数据获取失败: {e}")
    
    def _fetch_from_eastmoney(self, fund_code: str, date: Optional[str] = None) -> List[Dict]:
        """
        从东方财富备用接口获取数据（已弃用，使用_fetch_from_eastmoney_js代替）
        """
        # 保留此方法以兼容，实际调用新的JS接口
        return self._fetch_from_eastmoney_js(fund_code, date)
    
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
                                       date: Optional[str] = None,
                                       max_workers: int = 5) -> Dict[str, Dict[str, Any]]:
        """
        批量获取多个基金的重仓股数据（并发优化版）
        
        优先从数据库获取，缺失的数据使用线程池并发从API获取
        
        Args:
            fund_codes: 基金代码列表
            date: 报告期日期（可选）
            max_workers: 最大并发线程数，默认5
            
        Returns:
            Dict: 以基金代码为key的结果字典
        """
        results = {}
        
        if not fund_codes:
            return results
        
        # 1. 尝试从数据库批量获取（优化为单次查询）
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
        
        # 2. 使用线程池并发获取缺失的数据
        if missing_funds:
            logger.info(f"开始并发获取 {len(missing_funds)} 只基金的重仓股数据，最大并发数: {max_workers}")
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_fund = {
                    executor.submit(self._fetch_single_fund_with_timeout, fund_code, date, 15): fund_code 
                    for fund_code in missing_funds
                }
                
                # 收集结果
                for future in as_completed(future_to_fund):
                    fund_code = future_to_fund[future]
                    try:
                        result = future.result(timeout=20)  # 20秒超时（内部已设置15秒）
                        results[fund_code] = result
                        
                        # 更新缓存
                        if result.get('success') and result.get('data'):
                            cache_key = self._get_cache_key(fund_code, date)
                            self._set_cached_data(cache_key, result['data'])
                    except Exception as e:
                        logger.error(f"获取基金 {fund_code} 重仓股时发生错误: {e}")
                        results[fund_code] = {
                            'success': False,
                            'data': [],
                            'source': 'none',
                            'error': str(e),
                            'timestamp': datetime.now().isoformat()
                        }
            
            elapsed = time.time() - start_time
            logger.info(f"并发获取完成，耗时: {elapsed:.2f}秒")
        
        return results
    
    def _fetch_single_fund_with_timeout(self, fund_code: str, date: Optional[str] = None, timeout: int = 15) -> Dict[str, Any]:
        """
        带超时的单只基金重仓股获取
        
        Args:
            fund_code: 基金代码
            date: 报告期日期（可选）
            timeout: 超时时间（秒），默认15秒
            
        Returns:
            Dict: 重仓股数据结果
        """
        import threading
        
        result_container = {'result': None, 'error': None}
        
        def fetch_task():
            try:
                result = self.fetch_heavyweight_stocks(fund_code, date, use_cache=True)
                result_container['result'] = result
            except Exception as e:
                result_container['error'] = e
        
        thread = threading.Thread(target=fetch_task)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            logger.warning(f"获取基金 {fund_code} 重仓股超时（{timeout}秒）")
            return {
                'success': False,
                'data': [],
                'source': 'none',
                'error': f'请求超时（{timeout}秒）',
                'timestamp': datetime.now().isoformat()
            }
        
        if result_container['error']:
            logger.error(f"获取基金 {fund_code} 重仓股失败: {result_container['error']}")
            return {
                'success': False,
                'data': [],
                'source': 'none',
                'error': str(result_container['error']),
                'timestamp': datetime.now().isoformat()
            }
        
        return result_container['result']
    
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
                                   date: Optional[str] = None,
                                   max_workers: int = 5) -> Dict[str, Dict[str, Any]]:
    """
    便捷函数：批量获取重仓股数据（并发优化版）
    
    Args:
        fund_codes: 基金代码列表
        date: 报告期日期（可选）
        max_workers: 最大并发线程数，默认5
        
    Returns:
        Dict: 以基金代码为key的结果字典
    """
    fetcher = get_fetcher()
    return fetcher.fetch_heavyweight_stocks_batch(fund_codes, date, max_workers)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 测试获取数据
    result = fetch_heavyweight_stocks("000001", use_cache=False)
    print(json.dumps(result, ensure_ascii=False, indent=2))
