#!/usr/bin/env python
# coding: utf-8

"""
增强版基金数据获取模块
提供从akshare获取基金实时和历史数据的功能
"""

import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import requests
import re
import ast

# 设置日志
# 只获取logger，不配置basicConfig（由主程序配置）
logger = logging.getLogger(__name__)


class EnhancedFundData:
    """增强版基金数据类"""
    
    # QDII基金代码列表（从京东金融表格中识别）
    QDII_FUND_CODES = {
        '096001',  # 大成标普500等权重指数(QDII)A人民币
        '100055',  # 富国全球科技互联网股票(QDII)A
        '012061',  # 富国全球消费精选混合(QDII)美元现汇
        '006680',  # 广发道琼斯石油指数(QDII-LOF)C美元现汇
        '006373',  # 国富全球科技互联混合(QDII)人民币A
        '006105',  # 宏利印度股票(QDII)A
        '021540',  # 华安法国CAC40ETF发起式联接(QDII)C
        '015016',  # 华安国际龙头(DAX)ETF联接C
        '040047',  # 华安纳斯达克100ETF联接(QDII)A(美元现钞)
        '007844',  # 华宝油气C
        '008708',  # 建信富时100指数(QDII)C美元现汇
        '501225',  # 景顺长城全球半导体芯片股票A(QDII-LOF)(人民币)
        '162415',  # 美国消费
        '007721',  # 天弘标普500发起(QDII-FOF)A
    }
    
    @staticmethod
    def is_qdii_fund(fund_code: str, fund_name: str = None) -> bool:
        """
        判断是否为QDII基金
        
        参数：
        fund_code: 基金代码
        fund_name: 基金名称（可选）
        
        返回：
        bool: 是否为QDII基金
        """
        # 检查基金代码是否在预定义列表中
        if fund_code in EnhancedFundData.QDII_FUND_CODES:
            return True
        
        # 检查基金名称是否包含QDII关键词
        if fund_name and 'QDII' in fund_name:
            return True
        
        return False
    
    @staticmethod
    def get_sina_realtime_estimation(fund_code: str) -> Optional[Dict]:
        """
        从新浪财经获取基金实时估算数据（分钟级）
        
        参数：
        fund_code: 基金代码（6位数字）
        
        返回：
        dict: 包含昨日净值和实时估算的字典，失败返回None
        """
        header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # 实时数据接口
        today_url = f"https://app.xincai.com/fund/api/jsonp.json/var%20t1fu_{fund_code}=/XinCaiFundService.getFundYuCeNav?symbol={fund_code}&___qn=3"
        
        try:
            today_response = requests.get(today_url, headers=header, timeout=10)
            
            # 解析JSONP响应
            parts = re.split("[()]", today_response.text)
            if len(parts) < 2:
                logger.debug(f"基金 {fund_code} 新浪接口返回格式异常: {today_response.text[:200]}")
                return None
            
            today_str = parts[1]
            
            # 检查是否为null值
            if today_str.strip() == 'null':
                logger.debug(f"基金 {fund_code} 新浪接口返回null值")
                return None
            
            today_dict_one = ast.literal_eval(today_str)
            
            # 解析分钟级数据
            if 'detail' not in today_dict_one:
                logger.debug(f"基金 {fund_code} 新浪接口返回数据缺少detail字段")
                return None
                
            minute_list_strs = today_dict_one['detail'].split(',')
            minute_data = {}
            for i in range(0, len(minute_list_strs), 2):
                if i+1 < len(minute_list_strs):
                    try:
                        minute_data[minute_list_strs[i]] = float(minute_list_strs[i+1])
                    except (ValueError, IndexError):
                        continue  # 跳过无效数据
            
            # 获取最新估算值
            latest_estimate = list(minute_data.values())[-1] if minute_data else None
            latest_time = list(minute_data.keys())[-1] if minute_data else None
            
            result = {
                "previous_nav": float(today_dict_one["yes"]),  # 昨日净值
                "estimate_nav": latest_estimate,  # 最新估算
                "estimate_time": latest_time,  # 估算时间
                "minute_data": minute_data,  # 分钟级数据
                "source": "sina_realtime"
            }
            
            logger.debug(f"基金 {fund_code} 从新浪获取实时估算成功: {latest_estimate}")
            return result
            
        except Exception as e:
            logger.debug(f"从新浪财经获取基金 {fund_code} 实时数据失败: {e}")
            return None
    
    @staticmethod
    def get_fund_basic_info(fund_code: str) -> Dict:
        """
        获取基金基本信息

        参数：
        fund_code: 基金代码（6位数字）

        返回：
        dict: 基金基本信息
        """
        try:
            # 获取基金基本信息
            fund_info = ak.fund_open_fund_info_em(symbol=fund_code, indicator="基本信息")

            if fund_info.empty:
                # API返回空数据，尝试从净值历史获取成立日期作为备选
                logger.debug(f"基金 {fund_code} 基本信息API返回空，尝试从净值历史获取")
                establish_date = EnhancedFundData._get_establish_date_from_nav(fund_code)
                return {
                    'fund_code': fund_code,
                    'fund_name': f'基金{fund_code}',
                    'fund_type': '未知',
                    'establish_date': establish_date,
                    'fund_company': '未知',
                    'fund_manager': '未知',
                    'management_fee': 0.0,
                    'custody_fee': 0.0
                }

            # 提取基本信息
            info_dict = {}
            for _, row in fund_info.iterrows():
                info_dict[row['项目']] = row['数值']

            return {
                'fund_code': fund_code,
                'fund_name': info_dict.get('基金简称', f'基金{fund_code}'),
                'fund_type': info_dict.get('基金类型', '未知'),
                'establish_date': info_dict.get('成立日期', None),  # 返回None而不是空字符串
                'fund_company': info_dict.get('基金管理人', '未知'),
                'fund_manager': info_dict.get('基金经理', '未知'),
                'management_fee': float(info_dict.get('管理费率', 0.0)),
                'custody_fee': float(info_dict.get('托管费率', 0.0))
            }
        except Exception as e:
            error_msg = str(e)
            if "SyntaxError" in error_msg and "<!doctype html>" in error_msg:
                logger.debug(f"基金 {fund_code} API返回错误页面，使用默认值")
            else:
                logger.debug(f"获取基金 {fund_code} 基本信息失败: {error_msg}，使用默认值")
            # 尝试从净值历史获取成立日期
            establish_date = EnhancedFundData._get_establish_date_from_nav(fund_code)
            return {
                'fund_code': fund_code,
                'fund_name': f'基金{fund_code}',
                'fund_type': '未知',
                'establish_date': establish_date,
                'fund_company': '未知',
                'fund_manager': '未知',
                'management_fee': 0.0,
                'custody_fee': 0.0
            }

    @staticmethod
    def _get_establish_date_from_nav(fund_code: str) -> Optional[str]:
        """
        从净值历史数据获取基金成立日期（第一个净值日期作为成立日期的近似值）

        参数：
        fund_code: 基金代码

        返回：
        str: 成立日期字符串，格式为YYYY-MM-DD，失败返回None
        """
        try:
            fund_nav = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            if fund_nav.empty:
                return None

            # 获取第一行的净值日期
            first_date = fund_nav.iloc[0].get('净值日期', None)
            if first_date:
                return str(first_date)
            return None
        except Exception as e:
            logger.debug(f"获取基金 {fund_code} 净值历史失败: {e}")
            return None
    
    @staticmethod
    def get_realtime_data(fund_code: str, fund_name: str = None) -> Dict:
        """
        获取基金实时数据
        
        参数：
        fund_code: 基金代码（6位数字）
        fund_name: 基金名称（可选）
        
        返回：
        dict: 基金实时数据
        
        数据获取策略：
        - 普通基金：使用新浪财经实时估算（分钟级更新）
        - QDII基金：仅使用AKShare历史净值接口（不使用新浪接口）
          如果当日数据没有，顺推使用前一天的数据
        """
        # 判断是否为QDII基金
        is_qdii = EnhancedFundData.is_qdii_fund(fund_code, fund_name)
        
        if is_qdii:
            # QDII基金：仅使用AKShare接口
            logger.info(f"基金 {fund_code} 是QDII基金，使用AKShare接口获取数据")
            return EnhancedFundData._get_qdii_realtime_data(fund_code)
        else:
            # 普通基金：使用新浪接口
            return EnhancedFundData._get_normal_fund_realtime_data(fund_code)
    
    @staticmethod
    def _get_qdii_realtime_data(fund_code: str) -> Dict:
        """
        获取QDII基金实时数据
        
        参数：
        fund_code: 基金代码
        
        返回：
        dict: 基金实时数据
        
        逻辑：
        - 优先使用AKShare接口获取数据
        - 如果AKShare失败，尝试从数据库获取历史数据
        - 如果当日盈亏算不到，就用昨日的
        - 昨日盈亏用前天的，这样顺推一天的数据来计算
        - 当所有数据源失败时，返回合理的默认值
        """
        try:
            # 从AKShare获取历史净值数据
            fund_nav = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            
            if fund_nav.empty:
                logger.warning(f"AKShare接口未返回基金 {fund_code} 的净值数据，尝试从数据库获取")
                # 尝试从数据库获取历史数据
                db_data = EnhancedFundData._get_historical_data_from_db(fund_code)
                if db_data:
                    return db_data
                # 如果数据库也没有数据，返回默认值
                return {
                    'fund_code': fund_code,
                    'current_nav': 0.0,
                    'previous_nav': 0.0,
                    'daily_return': 0.0,
                    'today_return': 0.0,
                    'prev_day_return': 0.0,
                    'nav_date': datetime.now().strftime('%Y-%m-%d'),
                    'estimate_nav': 0.0,
                    'estimate_return': 0.0,
                    'data_source': 'akshare_qdii_error',
                    'estimate_time': ''
                }
            
            # 按日期排序
            fund_nav = fund_nav.sort_values('净值日期', ascending=True)
            
            # 获取最新数据（当日或最近一日）
            latest_data = fund_nav.iloc[-1]
            nav_date = str(latest_data.get('净值日期', datetime.now().strftime('%Y-%m-%d')))
            current_nav = float(latest_data.get('单位净值', 0))
            
            # 获取昨日净值（前一日的单位净值）
            if len(fund_nav) > 1:
                previous_data = fund_nav.iloc[-2]
                previous_nav = float(previous_data.get('单位净值', current_nav))
            else:
                previous_nav = current_nav
            
            # 获取当日盈亏率（从最新一条数据的日增长率获取）
            # 注意：akshare返回的日增长率已经是百分数格式（如-0.41），不需要再乘以100
            daily_return_raw = latest_data.get('日增长率', None)
            if pd.notna(daily_return_raw):
                daily_return = float(daily_return_raw)
                # 判断格式：如果绝对值 < 0.1，说明是小数格式，需要乘100
                if abs(daily_return) < 0.1:
                    daily_return = daily_return * 100
                daily_return = round(daily_return, 2)
            else:
                # 如果日增长率字段不存在或为NaN，通过计算当前净值和前一日净值的差值来得到日涨跌幅数据
                if previous_nav != 0:
                    daily_return = (current_nav - previous_nav) / previous_nav * 100
                else:
                    daily_return = 0.0
                daily_return = round(daily_return, 2)
                logger.info(f"QDII基金 {fund_code} 通过净值计算日涨跌幅: {daily_return}%")

            # 获取昨日盈亏率（从前一条数据的日增长率获取）
            # 注意：akshare返回的日增长率已经是百分数格式（如-0.41），不需要再乘以100
            if len(fund_nav) > 1:
                prev_day_return_raw = previous_data.get('日增长率', 0)
                if pd.notna(prev_day_return_raw):
                    prev_day_return = float(prev_day_return_raw)
                    # 判断格式
                    if abs(prev_day_return) < 0.1:
                        prev_day_return = prev_day_return * 100
                    prev_day_return = round(prev_day_return, 2)
                else:
                    prev_day_return = 0.0
            else:
                prev_day_return = 0.0
            
            logger.info(f"QDII基金 {fund_code} 使用AKShare数据: 当日净值={current_nav}, 当日盈亏={daily_return}%, 昨日盈亏={prev_day_return}% (AKShare日增长率直接使用，不进行格式转换)")
            
            return {
                'fund_code': fund_code,
                'current_nav': current_nav,
                'previous_nav': previous_nav,
                'daily_return': daily_return,
                'today_return': daily_return,  # 添加别名，与 enhanced_main.py 保持一致
                'prev_day_return': prev_day_return,
                'nav_date': nav_date,
                'estimate_nav': current_nav,  # QDII基金没有实时估算，使用当日净值
                'estimate_return': daily_return,
                'data_source': 'akshare_qdii',
                'estimate_time': ''
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"获取QDII基金 {fund_code} 数据失败: {error_msg}")
            
            # 检查是否是AKShare返回错误页面
            if "SyntaxError" in error_msg and "<!doctype html>" in error_msg:
                logger.warning(f"AKShare返回错误页面，基金 {fund_code} 尝试从数据库获取")
            
            # 尝试从数据库获取历史数据
            try:
                db_data = EnhancedFundData._get_historical_data_from_db(fund_code)
                if db_data:
                    return db_data
            except Exception as db_e:
                logger.error(f"从数据库获取QDII基金 {fund_code} 历史数据失败: {str(db_e)}")
                
            # 如果所有数据源都失败，返回合理的默认值
            return {
                'fund_code': fund_code,
                'current_nav': 0.0,
                'previous_nav': 0.0,
                'daily_return': 0.0,
                'today_return': 0.0,
                'prev_day_return': 0.0,
                'nav_date': datetime.now().strftime('%Y-%m-%d'),
                'estimate_nav': 0.0,
                'estimate_return': 0.0,
                'data_source': 'akshare_qdii_error',
                'estimate_time': ''
            }
    
    @staticmethod
    def _get_historical_data_from_db(fund_code: str) -> Dict:
        """
        从数据库获取历史基金数据作为备用
        
        参数：
        fund_code: 基金代码
        
        返回：
        dict: 基金历史数据，如果没有数据返回None
        """
        try:
            # 尝试导入数据库模块
            try:
                from .enhanced_database import EnhancedDatabaseManager
            except ImportError:
                from data_access.enhanced_database import EnhancedDatabaseManager
            
            # 数据库配置
            db_config = {
                'user': 'root',
                'password': 'root',
                'host': 'localhost',
                'port': 3306,
                'database': 'fund_analysis',
                'charset': 'utf8mb4'
            }
            
            db_manager = EnhancedDatabaseManager(db_config)
            
            # 查询最新的基金分析结果
            sql = """
            SELECT current_estimate as current_nav, 
                   yesterday_nav as previous_nav, 
                   today_return, 
                   prev_day_return,
                   analysis_date as nav_date
            FROM fund_analysis_results
            WHERE fund_code = :fund_code
            ORDER BY analysis_date DESC
            LIMIT 1
            """
            
            df = db_manager.execute_query(sql, {'fund_code': fund_code})
            
            if not df.empty:
                row = df.iloc[0]
                current_nav = float(row.get('current_nav', 0))
                previous_nav = float(row.get('previous_nav', 0))
                today_return = float(row.get('today_return', 0))
                prev_day_return = float(row.get('prev_day_return', 0))
                nav_date = str(row.get('nav_date', datetime.now().strftime('%Y-%m-%d')))
                
                logger.info(f"从数据库获取QDII基金 {fund_code} 历史数据: 当日净值={current_nav}, 当日盈亏={today_return}%, 昨日盈亏={prev_day_return}%")
                
                return {
                    'fund_code': fund_code,
                    'current_nav': current_nav,
                    'previous_nav': previous_nav,
                    'daily_return': today_return,
                    'today_return': today_return,
                    'prev_day_return': prev_day_return,
                    'nav_date': nav_date,
                    'estimate_nav': current_nav,
                    'estimate_return': today_return,
                    'data_source': 'database_backup',
                    'estimate_time': ''
                }
            
            logger.warning(f"数据库中未找到基金 {fund_code} 的历史数据")
            return None
            
        except Exception as e:
            logger.error(f"从数据库获取QDII基金 {fund_code} 历史数据失败: {str(e)}")
            return None
    
    @staticmethod
    def _get_normal_fund_realtime_data(fund_code: str) -> Dict:
        """
        获取普通基金实时数据（优先使用新浪财经实时估算，失败时使用AKShare历史数据作为备选）
        
        参数：
        fund_code: 基金代码
        
        返回：
        dict: 基金实时数据
        """
        try:
            # 从新浪财经获取实时估算
            sina_data = EnhancedFundData.get_sina_realtime_estimation(fund_code)
            
            if sina_data and sina_data['estimate_nav'] is not None:
                # 成功从新浪获取实时数据
                sina_previous_nav = sina_data['previous_nav']
                estimate_nav = sina_data['estimate_nav']
                
                # 计算实时日涨跌幅
                if sina_previous_nav != 0:
                    daily_return = (estimate_nav - sina_previous_nav) / sina_previous_nav * 100
                else:
                    daily_return = 0.0
                
                logger.info(f"基金 {fund_code} 使用新浪实时数据: {estimate_nav}, 涨跌幅: {daily_return:.2f}%")
                
                # 从AKShare获取昨日盈亏率和其他补充数据
                try:
                    fund_nav = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
                    if not fund_nav.empty:
                        fund_nav = fund_nav.sort_values('净值日期', ascending=True)
                        latest_data = fund_nav.iloc[-1]
                        nav_date = str(latest_data.get('净值日期', datetime.now().strftime('%Y-%m-%d')))
                        current_nav = float(latest_data.get('单位净值', sina_previous_nav))
                        
                        # 获取昨日净值（前一日的单位净值）
                        if len(fund_nav) > 1:
                            previous_data = fund_nav.iloc[-2]
                            previous_nav = float(previous_data.get('单位净值', sina_previous_nav))
                        else:
                            previous_nav = sina_previous_nav
                        
                        # 获取昨日盈亏率（直接从最新一条数据的日增长率获取）
                        # 注意：akshare返回的日增长率已经是百分数格式（如-0.94），不需要再乘以100
                        prev_day_return_raw = latest_data.get('日增长率', 0)
                        if pd.notna(prev_day_return_raw):
                            prev_day_return = float(prev_day_return_raw)
                            # 判断格式：如果绝对值 < 0.1，说明是小数格式（如0.0475），需要乘100
                            if abs(prev_day_return) < 0.1:
                                prev_day_return = prev_day_return * 100
                            prev_day_return = round(prev_day_return, 2)
                        else:
                            prev_day_return = 0.0
                    else:
                        # AKShare数据为空，使用新浪数据作为默认值
                        nav_date = datetime.now().strftime('%Y-%m-%d')
                        current_nav = sina_previous_nav
                        previous_nav = sina_previous_nav
                        prev_day_return = 0.0
                except Exception as e:
                    logger.warning(f"获取基金 {fund_code} AKShare补充数据失败: {e}，使用新浪数据")
                    nav_date = datetime.now().strftime('%Y-%m-%d')
                    current_nav = sina_previous_nav
                    previous_nav = sina_previous_nav
                    prev_day_return = 0.0
                
                return {
                    'fund_code': fund_code,
                    'current_nav': current_nav,
                    'previous_nav': previous_nav,
                    'daily_return': round(daily_return, 2),
                    'today_return': round(daily_return, 2),  # 添加别名，与 enhanced_main.py 保持一致
                    'prev_day_return': prev_day_return,
                    'nav_date': nav_date,
                    'estimate_nav': estimate_nav,
                    'estimate_return': round(daily_return, 2),
                    'data_source': 'sina_realtime',
                    'estimate_time': sina_data.get('estimate_time', '')
                }
            else:
                logger.warning(f"新浪财经接口未返回基金 {fund_code} 的实时估算数据，尝试使用AKShare历史数据")
                
                # 从AKShare获取历史净值数据作为备选方案
                fund_nav = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
                
                try:
                    if fund_nav.empty:
                        logger.warning(f"AKShare接口未返回基金 {fund_code} 的净值数据，尝试从数据库获取")
                        # 尝试从数据库获取历史数据
                        db_data = EnhancedFundData._get_historical_data_from_db(fund_code)
                        if db_data:
                            logger.info(f"基金 {fund_code} 使用数据库历史数据")
                            return db_data
                        # 如果数据库也没有数据，返回默认值
                        return {
                            'fund_code': fund_code,
                            'current_nav': 0.0,
                            'previous_nav': 0.0,
                            'daily_return': 0.0,
                            'today_return': 0.0,
                            'prev_day_return': 0.0,
                            'nav_date': datetime.now().strftime('%Y-%m-%d'),
                            'estimate_nav': 0.0,
                            'estimate_return': 0.0,
                            'data_source': 'akshare_normal_error',
                            'estimate_time': ''
                        }
                    
                    # 对AKShare返回的数据进行处理
                    fund_nav = fund_nav.sort_values('净值日期', ascending=True)
                    
                    # 获取最新的净值数据
                    latest_data = fund_nav.iloc[-1]
                    current_nav = float(latest_data.get('单位净值', 0))
                    nav_date = str(latest_data.get('净值日期', datetime.now().strftime('%Y-%m-%d')))
                    
                    # 获取前一日净值（如果有多个记录的话）
                    if len(fund_nav) > 1:
                        previous_data = fund_nav.iloc[-2]
                        previous_nav = float(previous_data.get('单位净值', current_nav))
                    else:
                        previous_nav = current_nav
                    
                    # 获取日增长率
                    daily_return_raw = latest_data.get('日增长率', 0)
                    if pd.notna(daily_return_raw):
                        daily_return = float(daily_return_raw)
                        # 判断格式：如果绝对值 < 0.1，说明是小数格式（如0.0475），需要乘100
                        if abs(daily_return) < 0.1:
                            daily_return = daily_return * 100
                        daily_return = round(daily_return, 2)
                    else:
                        # 如果日增长率为空，通过计算当前净值和前一日净值的差值得到
                        if previous_nav != 0 and previous_nav != current_nav:
                            daily_return = (current_nav - previous_nav) / previous_nav * 100
                            daily_return = round(daily_return, 2)
                        else:
                            daily_return = 0.0
                    
                    # 获取昨日盈亏率（倒数第二个记录的日增长率，如果存在）
                    prev_day_return = 0.0
                    if len(fund_nav) > 1:
                        second_latest_data = fund_nav.iloc[-2]
                        prev_day_return_raw = second_latest_data.get('日增长率', 0)
                        if pd.notna(prev_day_return_raw):
                            prev_day_return = float(prev_day_return_raw)
                            # 判断格式：如果绝对值 < 0.1，说明是小数格式（如0.0475），需要乘100
                            if abs(prev_day_return) < 0.1:
                                prev_day_return = prev_day_return * 100
                            prev_day_return = round(prev_day_return, 2)
                except Exception as akshare_e:
                    logger.warning(f"AKShare接口异常，基金 {fund_code} 尝试从数据库获取: {akshare_e}")
                    # 尝试从数据库获取历史数据
                    db_data = EnhancedFundData._get_historical_data_from_db(fund_code)
                    if db_data:
                        logger.info(f"基金 {fund_code} 使用数据库历史数据")
                        return db_data
                    # 如果数据库也没有数据，返回默认值
                    return {
                        'fund_code': fund_code,
                        'current_nav': 0.0,
                        'previous_nav': 0.0,
                        'daily_return': 0.0,
                        'today_return': 0.0,
                        'prev_day_return': 0.0,
                        'nav_date': datetime.now().strftime('%Y-%m-%d'),
                        'estimate_nav': 0.0,
                        'estimate_return': 0.0,
                        'data_source': 'akshare_exception',
                        'estimate_time': ''
                    }
                
                logger.info(f"基金 {fund_code} 使用AKShare历史数据: 当前净值={current_nav}, 涨跌幅={daily_return:.2f}%")
                
                return {
                    'fund_code': fund_code,
                    'current_nav': current_nav,
                    'previous_nav': previous_nav,
                    'daily_return': daily_return,
                    'today_return': daily_return,  # 添加别名，与 enhanced_main.py 保持一致
                    'prev_day_return': prev_day_return,
                    'nav_date': nav_date,
                    'estimate_nav': current_nav,  # 使用当前净值作为估算净值
                    'estimate_return': daily_return,  # 使用当前日涨跌幅作为估算收益率
                    'data_source': 'akshare_history',
                    'estimate_time': ''
                }
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"获取基金 {fund_code} 实时数据失败: {error_msg}")
            
            # 再次尝试从数据库获取历史数据
            try:
                db_data = EnhancedFundData._get_historical_data_from_db(fund_code)
                if db_data:
                    logger.info(f"基金 {fund_code} 使用数据库历史数据作为最终备选")
                    return db_data
            except Exception as db_e:
                logger.error(f"从数据库获取基金 {fund_code} 历史数据也失败: {db_e}")
            
            # 如果所有方法都失败，返回基本的错误数据结构而不是抛出异常
            # 这样前端可以处理无数据的情况而不至于崩溃
            return {
                'fund_code': fund_code,
                'current_nav': 0.0,
                'previous_nav': 0.0,
                'daily_return': 0.0,
                'today_return': 0.0,
                'prev_day_return': 0.0,
                'nav_date': datetime.now().strftime('%Y-%m-%d'),
                'estimate_nav': 0.0,
                'estimate_return': 0.0,
                'data_source': 'all_sources_failed',
                'estimate_time': ''
            }
    
    @staticmethod
    def get_historical_data(fund_code: str, days: int = 365) -> pd.DataFrame:
        """
        获取基金历史数据
        
        参数：
        fund_code: 基金代码（6位数字）
        days: 历史数据天数（默认365天）
        
        返回：
        DataFrame: 基金历史数据
        """
        try:
            # 获取基金历史净值数据
            fund_hist = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            
            if fund_hist.empty:
                logger.debug(f"基金 {fund_code} 历史数据API返回空，使用空DataFrame")
                return pd.DataFrame()
            
            # 转换日期格式
            fund_hist['净值日期'] = pd.to_datetime(fund_hist['净值日期'])
            
            # 按日期排序
            fund_hist = fund_hist.sort_values('净值日期', ascending=True)
            
            # 过滤最近的数据
            start_date = datetime.now() - timedelta(days=days)
            fund_hist = fund_hist[fund_hist['净值日期'] >= start_date]
            
            if fund_hist.empty:
                return pd.DataFrame()
            
            # 计算日收益率
            fund_hist['daily_return'] = fund_hist['单位净值'].pct_change()
            
            # 重命名列
            fund_hist = fund_hist.rename(columns={
                '净值日期': 'date',
                '单位净值': 'nav',
                '累计净值': 'accumulated_nav',
                '日增长率': 'daily_growth_rate'
            })
            
            return fund_hist
        except Exception as e:
            error_msg = str(e)
            if "SyntaxError" in error_msg and "<!doctype html>" in error_msg:
                logger.debug(f"基金 {fund_code} API返回错误页面，使用空DataFrame")
            else:
                logger.debug(f"获取基金 {fund_code} 历史数据失败: {error_msg}，使用空DataFrame")
            return pd.DataFrame()
    
    @staticmethod
    def get_performance_metrics(fund_code: str, days: int = 3650) -> Dict:
        """
        获取基金绩效指标

        参数：
        fund_code: 基金代码（6位数字）
        days: 历史数据天数（默认3650天，约10年，确保能获取完整历史数据）
        
        返回：
        dict: 基金绩效指标
        """
        try:
            # 获取历史数据
            hist_data = EnhancedFundData.get_historical_data(fund_code, days)
            
            if hist_data.empty or len(hist_data) < 2:
                return EnhancedFundData._get_default_metrics()
            
            # 提取日收益率
            daily_returns = hist_data['daily_return'].dropna()
            
            if len(daily_returns) < 2:
                return EnhancedFundData._get_default_metrics()
            
            # 计算各种绩效指标
            return EnhancedFundData._calculate_metrics(daily_returns, hist_data)
        except Exception as e:
            logger.error(f"计算基金 {fund_code} 绩效指标失败: {str(e)}")
            return EnhancedFundData._get_default_metrics()
    
    @staticmethod
    def _calculate_metrics(daily_returns: pd.Series, hist_data: pd.DataFrame) -> Dict:
        """
        计算绩效指标
        
        参数：
        daily_returns: 日收益率序列
        hist_data: 历史数据DataFrame
        
        返回：
        dict: 绩效指标
        """
        from shared.enhanced_config import PERFORMANCE_CONFIG, INVESTMENT_STRATEGY_CONFIG
        
        # 获取配置参数
        risk_free_rate = INVESTMENT_STRATEGY_CONFIG['risk_free_rate']
        trading_days = PERFORMANCE_CONFIG['trading_days_per_year']
        var_confidence = PERFORMANCE_CONFIG['var_confidence']
        
        # 计算总收益率
        start_nav = hist_data['nav'].iloc[0]
        end_nav = hist_data['nav'].iloc[-1]
        total_return = (end_nav - start_nav) / start_nav if start_nav != 0 else 0.0
        
        # 计算年化收益率
        days = len(hist_data)
        if days > 0:
            annualized_return = (1 + total_return) ** (trading_days / days) - 1
        else:
            annualized_return = 0.0
        
        # 计算年化波动率
        volatility = daily_returns.std() * np.sqrt(trading_days)
        
        # 计算夏普比率（默认使用全部数据）
        sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility != 0 else 0.0
        
        # 计算今年以来的夏普比率（YTD - Year to Date）
        current_date = hist_data['date'].iloc[-1]
        year_start_date = pd.Timestamp(year=current_date.year, month=1, day=1)
        ytd_data = hist_data[hist_data['date'] >= year_start_date]
        if len(ytd_data) >= 2:
            ytd_returns = ytd_data['daily_return'].dropna()
            ytd_volatility = ytd_returns.std() * np.sqrt(trading_days)
            ytd_start_nav = ytd_data['nav'].iloc[0]
            ytd_end_nav = ytd_data['nav'].iloc[-1]
            ytd_total_return = (ytd_end_nav - ytd_start_nav) / ytd_start_nav if ytd_start_nav != 0 else 0.0
            ytd_annualized_return = (1 + ytd_total_return) ** (trading_days / len(ytd_data)) - 1
            sharpe_ratio_ytd = (ytd_annualized_return - risk_free_rate) / ytd_volatility if ytd_volatility != 0 else 0.0
        else:
            sharpe_ratio_ytd = 0.0
        
        # 计算近一年的夏普比率（1Y - 1 Year）
        one_year_ago = current_date - pd.Timedelta(days=365)
        one_year_data = hist_data[hist_data['date'] >= one_year_ago]
        if len(one_year_data) >= 2:
            one_year_returns = one_year_data['daily_return'].dropna()
            one_year_volatility = one_year_returns.std() * np.sqrt(trading_days)
            one_year_start_nav = one_year_data['nav'].iloc[0]
            one_year_end_nav = one_year_data['nav'].iloc[-1]
            one_year_total_return = (one_year_end_nav - one_year_start_nav) / one_year_start_nav if one_year_start_nav != 0 else 0.0
            one_year_annualized_return = (1 + one_year_total_return) ** (trading_days / len(one_year_data)) - 1
            sharpe_ratio_1y = (one_year_annualized_return - risk_free_rate) / one_year_volatility if one_year_volatility != 0 else 0.0
        else:
            sharpe_ratio_1y = 0.0
        
        # 计算成立以来的夏普比率（All - All Time）
        if len(hist_data) >= 2:
            all_returns = daily_returns
            all_volatility = volatility
            all_annualized_return = annualized_return
            sharpe_ratio_all = (all_annualized_return - risk_free_rate) / all_volatility if all_volatility != 0 else 0.0
        else:
            sharpe_ratio_all = 0.0
        
        # 计算最大回撤
        cumulative_returns = (1 + daily_returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min() if not drawdown.empty else 0.0
        
        # 计算卡玛比率
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
        
        # 计算索提诺比率
        negative_returns = daily_returns[daily_returns < 0]
        downside_deviation = negative_returns.std() * np.sqrt(trading_days) if len(negative_returns) > 0 else volatility
        sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation if downside_deviation != 0 else 0.0
        
        # 计算VaR (95%)
        var_95 = daily_returns.quantile(var_confidence) if not daily_returns.empty else 0.0
        
        # 计算胜率
        win_rate = (daily_returns > 0).sum() / len(daily_returns) if len(daily_returns) > 0 else 0.0
        
        # 计算盈亏比
        positive_returns = daily_returns[daily_returns > 0]
        negative_returns = daily_returns[daily_returns < 0]
        avg_positive = positive_returns.mean() if len(positive_returns) > 0 else 0.0
        avg_negative = abs(negative_returns.mean()) if len(negative_returns) > 0 else 0.0
        profit_loss_ratio = avg_positive / avg_negative if avg_negative != 0 else 0.0
        
        # 计算综合评分
        weights = PERFORMANCE_CONFIG['weights']
        composite_score = (
            weights['annualized_return'] * max(0, min(1, (annualized_return + 0.5) / 1.0)) +
            weights['sharpe_ratio'] * max(0, min(1, (sharpe_ratio + 2) / 4.0)) +
            weights['max_drawdown'] * max(0, min(1, 1 - abs(max_drawdown) / 0.5)) +
            weights['volatility'] * max(0, min(1, 1 - volatility / 0.5)) +
            weights['win_rate'] * win_rate
        )
        
        return {
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio,
            'sharpe_ratio_ytd': sharpe_ratio_ytd,
            'sharpe_ratio_1y': sharpe_ratio_1y,
            'sharpe_ratio_all': sharpe_ratio_all,
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'calmar_ratio': calmar_ratio,
            'sortino_ratio': sortino_ratio,
            'var_95': var_95,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'composite_score': composite_score,
            'total_return': total_return,
            'data_days': days
        }
    
    @staticmethod
    def _get_default_metrics() -> Dict:
        """
        获取默认绩效指标
        
        返回：
        dict: 默认绩效指标
        """
        return {
            'annualized_return': 0.0,
            'sharpe_ratio': 0.0,
            'sharpe_ratio_ytd': 0.0,
            'sharpe_ratio_1y': 0.0,
            'sharpe_ratio_all': 0.0,
            'max_drawdown': 0.0,
            'volatility': 0.0,
            'calmar_ratio': 0.0,
            'sortino_ratio': 0.0,
            'var_95': 0.0,
            'win_rate': 0.0,
            'profit_loss_ratio': 0.0,
            'composite_score': 0.0,
            'total_return': 0.0,
            'data_days': 0
        }
    
    @staticmethod
    def get_batch_fund_data(fund_codes: List[str]) -> pd.DataFrame:
        """
        批量获取基金数据
        
        参数：
        fund_codes: 基金代码列表
        
        返回：
        DataFrame: 批量基金数据
        """
        results = []
        
        for fund_code in fund_codes:
            try:
                # 获取基本信息
                basic_info = EnhancedFundData.get_fund_basic_info(fund_code)
                
                # 获取实时数据
                realtime_data = EnhancedFundData.get_realtime_data(fund_code, basic_info['fund_name'])
                
                # 获取绩效指标
                performance_metrics = EnhancedFundData.get_performance_metrics(fund_code)
                
                # 合并数据
                fund_data = {
                    'fund_code': fund_code,
                    'fund_name': basic_info['fund_name'],
                    'fund_type': basic_info['fund_type'],
                    'fund_company': basic_info['fund_company'],
                    'fund_manager': basic_info['fund_manager'],
                    'current_nav': realtime_data['current_nav'],
                    'previous_nav': realtime_data['previous_nav'],
                    'daily_return': realtime_data['daily_return'],
                    'nav_date': realtime_data['nav_date'],
                    **performance_metrics
                }
                
                results.append(fund_data)
                logger.info(f"成功获取基金 {fund_code} 的数据")
                
            except Exception as e:
                logger.error(f"获取基金 {fund_code} 数据失败: {str(e)}")
                continue
        
        return pd.DataFrame(results)


    @staticmethod
    def get_etf_list() -> pd.DataFrame:
        """
        获取全市场ETF列表（实时行情）
        
        返回：
        DataFrame: ETF列表数据
        """
        try:
            # 使用akshare获取ETF实时行情
            etf_df = ak.fund_etf_spot_em()
            
            if etf_df is None or etf_df.empty:
                logger.warning("ETF列表API返回空数据")
                return pd.DataFrame()
            
            # 重命名列以统一格式
            column_mapping = {
                '代码': 'etf_code',
                '名称': 'etf_name',
                '最新价': 'current_price',
                '涨跌幅': 'change_percent',
                '涨跌额': 'change_amount',
                '成交量': 'volume',
                '成交额': 'turnover',
                '开盘价': 'open_price',
                '最高价': 'high_price',
                '最低价': 'low_price',
                '昨收': 'prev_close',
                '换手率': 'turnover_rate',
                '量比': 'volume_ratio',
                '振幅': 'amplitude'
            }
            
            # 只保留存在的列
            existing_columns = {k: v for k, v in column_mapping.items() if k in etf_df.columns}
            etf_df = etf_df.rename(columns=existing_columns)
            
            # 确保数值类型正确
            numeric_columns = ['current_price', 'change_percent', 'change_amount', 'volume', 
                             'turnover', 'open_price', 'high_price', 'low_price', 'prev_close',
                             'turnover_rate', 'volume_ratio', 'amplitude']
            for col in numeric_columns:
                if col in etf_df.columns:
                    etf_df[col] = pd.to_numeric(etf_df[col], errors='coerce')
            
            logger.info(f"成功获取 {len(etf_df)} 只ETF数据")
            return etf_df
            
        except Exception as e:
            logger.error(f"获取ETF列表失败: {str(e)}")
            return pd.DataFrame()
    
    @staticmethod
    def get_etf_history(etf_code: str, days: int = 365) -> pd.DataFrame:
        """
        获取ETF历史行情数据
        
        参数：
        etf_code: ETF代码
        days: 历史数据天数
        
        返回：
        DataFrame: ETF历史数据
        """
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            
            # 使用akshare获取ETF历史数据
            etf_hist = ak.fund_etf_hist_em(
                symbol=etf_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )
            
            if etf_hist is None or etf_hist.empty:
                logger.warning(f"ETF {etf_code} 历史数据API返回空")
                return pd.DataFrame()
            
            # 重命名列
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'turnover',
                '振幅': 'amplitude',
                '涨跌幅': 'change_percent',
                '涨跌额': 'change_amount',
                '换手率': 'turnover_rate'
            }
            
            existing_columns = {k: v for k, v in column_mapping.items() if k in etf_hist.columns}
            etf_hist = etf_hist.rename(columns=existing_columns)
            
            # 转换日期格式
            if 'date' in etf_hist.columns:
                etf_hist['date'] = pd.to_datetime(etf_hist['date'])
            
            return etf_hist
            
        except Exception as e:
            logger.error(f"获取ETF {etf_code} 历史数据失败: {str(e)}")
            return pd.DataFrame()
    
    @staticmethod
    def get_etf_nav_history(etf_code: str, days: int = 365, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取ETF基金净值历史数据（单位净值、累计净值）
        
        参数：
        etf_code: ETF代码
        days: 历史数据天数（当start_date和end_date未指定时使用）
        start_date: 开始日期 (YYYY-MM-DD格式)
        end_date: 结束日期 (YYYY-MM-DD格式)
        
        返回：
        DataFrame: ETF净值历史数据，包含单位净值、累计净值、日增长率
        """
        try:
            # 处理日期参数
            if end_date:
                end_date_str = end_date.replace('-', '')
            else:
                end_date_str = datetime.now().strftime('%Y%m%d')
            
            if start_date:
                start_date_str = start_date.replace('-', '')
            else:
                start_date_str = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            
            # 使用akshare获取ETF基金净值历史数据
            nav_hist = ak.fund_etf_fund_info_em(
                fund=etf_code,
                start_date=start_date_str,
                end_date=end_date_str
            )
            
            if nav_hist is None or nav_hist.empty:
                logger.warning(f"ETF {etf_code} 净值历史数据API返回空")
                return pd.DataFrame()
            
            # 重命名列
            column_mapping = {
                '净值日期': 'date',
                '单位净值': 'unit_nav',
                '累计净值': 'acc_nav',
                '日增长率': 'change_percent',
                '申购状态': 'purchase_status',
                '赎回状态': 'redeem_status'
            }
            
            existing_columns = {k: v for k, v in column_mapping.items() if k in nav_hist.columns}
            nav_hist = nav_hist.rename(columns=existing_columns)
            
            # 转换日期格式
            if 'date' in nav_hist.columns:
                nav_hist['date'] = pd.to_datetime(nav_hist['date'])
            
            # 确保数值类型正确
            for col in ['unit_nav', 'acc_nav', 'change_percent']:
                if col in nav_hist.columns:
                    nav_hist[col] = pd.to_numeric(nav_hist[col], errors='coerce')
            
            # 计算复权净值（基于累计净值和单位净值的比例调整）
            # 复权净值 = 单位净值 * (累计净值 / 单位净值的历史调整因子)
            # 简化处理：使用累计净值作为复权净值的近似
            if 'unit_nav' in nav_hist.columns and 'acc_nav' in nav_hist.columns:
                # 计算复权因子
                nav_hist['adj_nav'] = nav_hist['acc_nav']
            
            logger.info(f"成功获取ETF {etf_code} 的 {len(nav_hist)} 条净值历史数据")
            return nav_hist
            
        except Exception as e:
            logger.error(f"获取ETF {etf_code} 净值历史数据失败: {str(e)}")
            return pd.DataFrame()
    
    @staticmethod
    def get_etf_performance(etf_code: str, days: int = 365) -> Dict:
        """
        计算ETF绩效指标
        
        参数：
        etf_code: ETF代码
        days: 历史数据天数
        
        返回：
        dict: ETF绩效指标
        """
        try:
            hist_data = EnhancedFundData.get_etf_history(etf_code, days)
            
            if hist_data.empty or len(hist_data) < 2:
                return EnhancedFundData._get_default_metrics()
            
            # 计算日收益率
            if 'close' in hist_data.columns:
                daily_returns = hist_data['close'].pct_change().dropna()
            elif 'change_percent' in hist_data.columns:
                daily_returns = hist_data['change_percent'] / 100
                daily_returns = daily_returns.dropna()
            else:
                return EnhancedFundData._get_default_metrics()
            
            if len(daily_returns) < 2:
                return EnhancedFundData._get_default_metrics()
            
            # 创建一个模拟的hist_data用于计算
            calc_data = pd.DataFrame({
                'nav': hist_data['close'] if 'close' in hist_data.columns else hist_data['current_price'],
                'daily_return': daily_returns
            })
            
            return EnhancedFundData._calculate_metrics(daily_returns, calc_data)
            
        except Exception as e:
            logger.error(f"计算ETF {etf_code} 绩效指标失败: {str(e)}")
            return EnhancedFundData._get_default_metrics()


# 模块级函数，供测试使用
def parse_date_string(date_str: str) -> Optional[datetime]:
    """
    解析日期字符串为datetime对象
    
    参数:
        date_str: 日期字符串（支持多种格式）
        
    返回:
        datetime对象，解析失败返回None
    """
    if not date_str:
        return None
    
    date_formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%Y%m%d',
        '%d-%m-%Y',
        '%d/%m/%Y',
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    return None


def get_trading_days(start_date: datetime, end_date: datetime) -> List[datetime]:
    """
    获取指定日期范围内的交易日（排除周末）
    
    参数:
        start_date: 开始日期
        end_date: 结束日期
        
    返回:
        交易日列表
    """
    trading_days = []
    current = start_date
    
    while current <= end_date:
        # 排除周末（周一=0，周日=6）
        if current.weekday() < 5:
            trading_days.append(current)
        current += timedelta(days=1)
    
    return trading_days


if __name__ == "__main__":
    # 测试代码
    test_codes = ['025833', '012061']
    
    # 测试单个基金数据获取
    for code in test_codes:
        print(f"\n测试基金 {code}:")
        basic_info = EnhancedFundData.get_fund_basic_info(code)
        print(f"基本信息: {basic_info}")
        
        realtime_data = EnhancedFundData.get_realtime_data(code)
        print(f"实时数据: {realtime_data}")
        
        performance_metrics = EnhancedFundData.get_performance_metrics(code)
        print(f"绩效指标: {performance_metrics}")
    
    # 测试批量数据获取
    print(f"\n测试批量数据获取:")
    batch_data = EnhancedFundData.get_batch_fund_data(test_codes)
    print(batch_data)