#!/usr/bin/env python
# coding: utf-8
"""
多数据源基金数据获取器
整合 akshare、tushare 和备用数据源的统一接口
"""

import pandas as pd
import akshare as ak
import tushare as ts
import requests
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from functools import wraps
import json
import re
import os
import sys

# 添加项目路径以便导入配置
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from fund_search.shared.enhanced_config import DATA_SOURCE_CONFIG
except ImportError:
    # 如果无法导入配置，使用默认值
    DATA_SOURCE_CONFIG = {
        'tushare': {
            'token': '5ff19facae0e5b26a407d491d33707a9884a39a714a0d76b6495725b',
            'timeout': 30,
            'max_retries': 3
        },
        'akshare': {
            'timeout': 30,
            'max_retries': 3,
            'delay_between_requests': 1.0
        },
        'fallback': {
            'sina_enabled': True,
            'eastmoney_enabled': True,
            'request_timeout': 10
        }
    }

logger = logging.getLogger(__name__)

class MultiSourceFundDataFetcher:
    """多数据源基金数据获取器"""
    
    def __init__(self, tushare_token: str = None):
        # 优先使用传入的token，否则使用配置文件中的token
        self.tushare_token = tushare_token or DATA_SOURCE_CONFIG['tushare']['token']
        self.pro = None
        self._initialize_tushare()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 配置参数
        self.tushare_config = DATA_SOURCE_CONFIG['tushare']
        self.akshare_config = DATA_SOURCE_CONFIG['akshare']
        self.fallback_config = DATA_SOURCE_CONFIG['fallback']
    
    def _initialize_tushare(self):
        """初始化 Tushare"""
        if self.tushare_token:
            try:
                ts.set_token(self.tushare_token)
                self.pro = ts.pro_api()
                logger.info("Tushare 初始化成功")
            except Exception as e:
                logger.warning(f"Tushare 初始化失败: {e}")
                self.pro = None
    
    def retry_on_failure(max_retries=3, delay=1):
        """重试装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                last_exception = None
                for attempt in range(max_retries):
                    try:
                        return func(self, *args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries - 1:
                            logger.warning(f"尝试 {attempt + 1}/{max_retries} 失败: {e}，{delay}秒后重试...")
                            time.sleep(delay)
                        else:
                            logger.error(f"所有 {max_retries} 次尝试都失败了")
                raise last_exception
            return wrapper
        return decorator
    
    @retry_on_failure(max_retries=3, delay=2)
    def get_fund_basic_info(self, fund_code: str) -> Dict:
        """
        获取基金基本信息
        优先级: akshare > tushare > 备用源
        """
        logger.info(f"获取基金 {fund_code} 基本信息")
        
        # 方法1: 使用 akshare fund_individual_basic_info_xq
        try:
            logger.info("尝试 akshare fund_individual_basic_info_xq")
            fund_info = ak.fund_individual_basic_info_xq(symbol=fund_code)
            
            if not fund_info.empty:
                info_dict = {}
                for _, row in fund_info.iterrows():
                    item = row.get('item', '')
                    value = row.get('value', '')
                    if pd.notna(value):
                        info_dict[item] = str(value).strip()
                    else:
                        info_dict[item] = None
                
                result = {
                    'fund_code': fund_code,
                    'fund_name': info_dict.get('基金名称', f'基金{fund_code}'),
                    'fund_type': info_dict.get('基金类型', '未知'),
                    'establish_date': info_dict.get('成立日期', None),
                    'fund_company': info_dict.get('基金公司', '未知'),
                    'fund_manager': info_dict.get('基金经理', '未知'),
                    'management_fee': info_dict.get('管理费率', '未知'),
                    'custody_fee': info_dict.get('托管费率', '未知'),
                    'data_source': 'akshare_xq',
                    'raw_info': info_dict
                }
                
                logger.info(f"✓ akshare 获取成功: {result['fund_name']}")
                return result
        except Exception as e:
            logger.warning(f"akshare fund_individual_basic_info_xq 失败: {e}")
        
        # 方法2: 使用 akshare fund_open_fund_info_em
        try:
            logger.info("尝试 akshare fund_open_fund_info_em")
            fund_info = ak.fund_open_fund_info_em(symbol=fund_code, indicator="基本信息")
            
            if not fund_info.empty:
                info_dict = {}
                for _, row in fund_info.iterrows():
                    item = row.get('项目', '')
                    value = row.get('数值', '')
                    if pd.notna(value):
                        info_dict[item] = str(value).strip()
                    else:
                        info_dict[item] = None
                
                result = {
                    'fund_code': fund_code,
                    'fund_name': info_dict.get('基金简称', f'基金{fund_code}'),
                    'fund_type': info_dict.get('基金类型', '未知'),
                    'establish_date': info_dict.get('成立日期', None),
                    'fund_company': info_dict.get('基金管理人', '未知'),
                    'fund_manager': info_dict.get('基金经理', '未知'),
                    'management_fee': info_dict.get('管理费率', '未知'),
                    'custody_fee': info_dict.get('托管费率', '未知'),
                    'data_source': 'akshare_em',
                    'raw_info': info_dict
                }
                
                logger.info(f"✓ akshare 获取成功: {result['fund_name']}")
                return result
        except Exception as e:
            logger.warning(f"akshare fund_open_fund_info_em 失败: {e}")
        
        # 方法3: 使用 tushare (如果有权限)
        if self.pro:
            try:
                logger.info("尝试 tushare fund_basic")
                fund_info = self.pro.fund_basic(ts_code=fund_code)
                
                if not fund_info.empty:
                    row = fund_info.iloc[0]
                    result = {
                        'fund_code': fund_code,
                        'fund_name': row.get('name', f'基金{fund_code}'),
                        'fund_type': row.get('type', '未知'),
                        'establish_date': row.get('found_date', None),
                        'fund_company': row.get('company', '未知'),
                        'fund_manager': row.get('manager', '未知'),
                        'management_fee': row.get('m_fee', '未知'),
                        'custody_fee': row.get('c_fee', '未知'),
                        'data_source': 'tushare',
                        'raw_info': row.to_dict()
                    }
                    
                    logger.info(f"✓ tushare 获取成功: {result['fund_name']}")
                    return result
            except Exception as e:
                logger.warning(f"tushare fund_basic 失败: {e}")
        
        # 方法4: 备用方案 - 从基金列表中查找
        try:
            logger.info("尝试备用方案: 从基金列表查找")
            fund_list = ak.fund_name_em()
            
            if not fund_list.empty:
                target_fund = fund_list[fund_list['基金代码'] == fund_code]
                if not target_fund.empty:
                    row = target_fund.iloc[0]
                    result = {
                        'fund_code': fund_code,
                        'fund_name': row.get('基金简称', f'基金{fund_code}'),
                        'fund_type': '未知',
                        'establish_date': None,
                        'fund_company': '未知',
                        'fund_manager': '未知',
                        'management_fee': '未知',
                        'custody_fee': '未知',
                        'data_source': 'akshare_list',
                        'raw_info': row.to_dict()
                    }
                    
                    logger.info(f"✓ 备用方案获取成功: {result['fund_name']}")
                    return result
        except Exception as e:
            logger.warning(f"备用方案失败: {e}")
        
        # 所有方法都失败
        logger.error(f"✗ 所有方法都无法获取基金 {fund_code} 的基本信息")
        return {
            'fund_code': fund_code,
            'fund_name': f'基金{fund_code}',
            'fund_type': '未知',
            'establish_date': None,
            'fund_company': '未知',
            'fund_manager': '未知',
            'management_fee': '未知',
            'custody_fee': '未知',
            'data_source': 'failed',
            'raw_info': {}
        }
    
    @retry_on_failure(max_retries=3, delay=2)
    def get_fund_nav_history(self, fund_code: str, days: int = 365) -> pd.DataFrame:
        """
        获取基金历史净值数据
        优先级: akshare > tushare > 备用源
        """
        logger.info(f"获取基金 {fund_code} 历史净值数据 ({days}天)")
        
        # 方法1: 使用 akshare fund_open_fund_info_em (单位净值走势)
        try:
            logger.info("尝试 akshare fund_open_fund_info_em (单位净值走势)")
            nav_history = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            
            if not nav_history.empty:
                # 处理数据
                nav_history = nav_history.rename(columns={
                    '净值日期': 'date',
                    '单位净值': 'nav',
                    '日增长率': 'daily_return'
                })
                
                # 转换日期格式
                nav_history['date'] = pd.to_datetime(nav_history['date'])
                
                # 按日期排序
                nav_history = nav_history.sort_values('date', ascending=True)
                
                # 过滤日期范围
                if days < 9999:  # 不是"成立以来"
                    start_date = datetime.now() - timedelta(days=days)
                    nav_history = nav_history[nav_history['date'] >= start_date]
                
                # 确保数值类型正确
                nav_history['nav'] = pd.to_numeric(nav_history['nav'], errors='coerce')
                nav_history['daily_return'] = pd.to_numeric(nav_history['daily_return'], errors='coerce')
                
                # 删除空值
                nav_history = nav_history.dropna(subset=['nav'])
                
                logger.info(f"✓ akshare 获取成功: {len(nav_history)} 条数据")
                return nav_history.reset_index(drop=True)
        except Exception as e:
            logger.warning(f"akshare fund_open_fund_info_em 失败: {e}")
        
        # 方法2: 使用 akshare fund_open_fund_info_em (累计净值走势)
        try:
            logger.info("尝试 akshare fund_open_fund_info_em (累计净值走势)")
            nav_history = ak.fund_open_fund_info_em(symbol=fund_code, indicator="累计净值走势")
            
            if not nav_history.empty:
                # 处理数据
                nav_history = nav_history.rename(columns={
                    '净值日期': 'date',
                    '累计净值': 'nav',
                    '日增长率': 'daily_return'
                })
                
                # 转换日期格式
                nav_history['date'] = pd.to_datetime(nav_history['date'])
                
                # 按日期排序
                nav_history = nav_history.sort_values('date', ascending=True)
                
                # 过滤日期范围
                if days < 9999:
                    start_date = datetime.now() - timedelta(days=days)
                    nav_history = nav_history[nav_history['date'] >= start_date]
                
                # 确保数值类型正确
                nav_history['nav'] = pd.to_numeric(nav_history['nav'], errors='coerce')
                nav_history['daily_return'] = pd.to_numeric(nav_history['daily_return'], errors='coerce')
                
                # 删除空值
                nav_history = nav_history.dropna(subset=['nav'])
                
                logger.info(f"✓ akshare 累计净值获取成功: {len(nav_history)} 条数据")
                return nav_history.reset_index(drop=True)
        except Exception as e:
            logger.warning(f"akshare 累计净值走势失败: {e}")
        
        # 方法3: 使用 tushare (如果有权限)
        if self.pro:
            try:
                logger.info("尝试 tushare fund_nav")
                # 计算日期范围
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
                
                nav_history = self.pro.fund_nav(ts_code=fund_code, start_date=start_date, end_date=end_date)
                
                if not nav_history.empty:
                    # 处理数据
                    nav_history = nav_history.rename(columns={
                        'nav_date': 'date',
                        'unit_nav': 'nav',
                        'daily_profit': 'daily_return'
                    })
                    
                    # 转换日期格式
                    nav_history['date'] = pd.to_datetime(nav_history['date'])
                    
                    # 按日期排序
                    nav_history = nav_history.sort_values('date', ascending=True)
                    
                    # 确保数值类型正确
                    nav_history['nav'] = pd.to_numeric(nav_history['nav'], errors='coerce')
                    nav_history['daily_return'] = pd.to_numeric(nav_history['daily_return'], errors='coerce')
                    
                    # 删除空值
                    nav_history = nav_history.dropna(subset=['nav'])
                    
                    logger.info(f"✓ tushare 获取成功: {len(nav_history)} 条数据")
                    return nav_history.reset_index(drop=True)
            except Exception as e:
                logger.warning(f"tushare fund_nav 失败: {e}")
        
        # 所有方法都失败
        logger.error(f"✗ 所有方法都无法获取基金 {fund_code} 的历史净值数据")
        return pd.DataFrame()

    def get_fund_realtime_estimate(self, fund_code: str) -> Dict:
        """
        获取基金实时估算数据
        主要使用新浪财经接口
        """
        logger.info(f"获取基金 {fund_code} 实时估算数据")
        
        try:
            # 使用新浪财经实时数据接口
            url = f"http://hq.sinajs.cn/list=f_{fund_code}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                content = response.text.strip()
                if content and not content.endswith('"";'):
                    # 解析数据
                    data_part = content.split('"')[1]
                    if data_part:
                        data_items = data_part.split(',')
                        if len(data_items) >= 4:
                            result = {
                                'fund_code': fund_code,
                                'fund_name': data_items[0] if len(data_items) > 0 else f'基金{fund_code}',
                                'yesterday_nav': float(data_items[1]) if data_items[1] else 0.0,
                                'current_estimate': float(data_items[2]) if data_items[2] else 0.0,
                                'estimate_return': float(data_items[3]) if data_items[3] else 0.0,
                                'estimate_time': data_items[4] if len(data_items) > 4 else '',
                                'data_source': 'sina_realtime'
                            }
                            
                            logger.info(f"✓ 新浪财经实时数据获取成功")
                            return result
            
            logger.warning("新浪财经实时数据获取失败或无数据")
        except Exception as e:
            logger.warning(f"新浪财经实时数据获取异常: {e}")
        
        # 备用方案：使用历史数据的最后一行作为估算
        try:
            logger.info("使用历史数据作为备用估算")
            history_df = self.get_fund_nav_history(fund_code, days=7)
            
            if not history_df.empty:
                latest_row = history_df.iloc[-1]
                result = {
                    'fund_code': fund_code,
                    'fund_name': f'基金{fund_code}',
                    'yesterday_nav': latest_row['nav'],
                    'current_estimate': latest_row['nav'],
                    'estimate_return': latest_row.get('daily_return', 0.0),
                    'estimate_time': latest_row['date'].strftime('%Y-%m-%d'),
                    'data_source': 'history_backup'
                }
                
                logger.info(f"✓ 历史数据备用方案成功")
                return result
        except Exception as e:
            logger.warning(f"历史数据备用方案失败: {e}")
        
        # 最终失败
        logger.error(f"✗ 无法获取基金 {fund_code} 的实时估算数据")
        return {
            'fund_code': fund_code,
            'fund_name': f'基金{fund_code}',
            'yesterday_nav': 0.0,
            'current_estimate': 0.0,
            'estimate_return': 0.0,
            'estimate_time': '',
            'data_source': 'failed'
        }

# 使用示例和测试
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 创建数据获取器实例
    fetcher = MultiSourceFundDataFetcher(tushare_token="5ff19facae0e5b26a407d491d33707a9884a39a714a0d76b6495725b")
    
    # 测试基金代码
    test_fund_code = "021539"
    
    print("=" * 60)
    print("多数据源基金数据获取器测试")
    print("=" * 60)
    
    # 测试基本信息获取
    print(f"\n1. 测试基金 {test_fund_code} 基本信息获取:")
    basic_info = fetcher.get_fund_basic_info(test_fund_code)
    print(f"   基金名称: {basic_info['fund_name']}")
    print(f"   基金类型: {basic_info['fund_type']}")
    print(f"   成立日期: {basic_info['establish_date']}")
    print(f"   数据来源: {basic_info['data_source']}")
    
    # 测试历史净值获取
    print(f"\n2. 测试基金 {test_fund_code} 历史净值获取 (30天):")
    nav_history = fetcher.get_fund_nav_history(test_fund_code, days=30)
    if not nav_history.empty:
        print(f"   获取到 {len(nav_history)} 条数据")
        print(f"   日期范围: {nav_history['date'].min().strftime('%Y-%m-%d')} ~ {nav_history['date'].max().strftime('%Y-%m-%d')}")
        print(f"   最新净值: {nav_history.iloc[-1]['nav']}")
    else:
        print("   获取失败")
    
    # 测试实时估算获取
    print(f"\n3. 测试基金 {test_fund_code} 实时估算获取:")
    realtime_data = fetcher.get_fund_realtime_estimate(test_fund_code)
    print(f"   昨日净值: {realtime_data['yesterday_nav']}")
    print(f"   实时估算: {realtime_data['current_estimate']}")
    print(f"   估算涨跌幅: {realtime_data['estimate_return']}%")
    print(f"   数据来源: {realtime_data['data_source']}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)