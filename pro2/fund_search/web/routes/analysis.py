#!/usr/bin/env python
# coding: utf-8

"""
基金综合分析模块
提供持仓数据获取、资产配置计算、行业分布分析等功能
"""

import os
import sys
import json
import time
import logging
import threading
import traceback
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import numpy as np
import akshare as ak
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.enhanced_config import DATABASE_CONFIG, NOTIFICATION_CONFIG
from data_access.enhanced_database import EnhancedDatabaseManager

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 线程本地存储：每个线程独立的实例
_thread_local = threading.local()


def _get_thread_local_objects():
    """获取线程本地的数据适配器和策略选择器（避免线程间共享状态）"""
    if not hasattr(_thread_local, 'fund_data_manager'):
        from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
        from backtesting import get_strategy_selector
        _thread_local.fund_data_manager = MultiSourceDataAdapter()
        _thread_local.strategy_selector = get_strategy_selector()
    return _thread_local.fund_data_manager, _thread_local.strategy_selector

# 初始化数据库管理器
db_manager = None

def init_db_manager(database_manager):
    """初始化数据库管理器"""
    global db_manager
    db_manager = database_manager


# ==================== 综合分析相关函数 ====================

def get_fund_holdings_data(fund_code):
    """
    获取基金持仓数据
    优先使用akshare，失败时依次尝试备用数据源
    
    Args:
        fund_code: 基金代码
        
    Returns:
        DataFrame: 持仓数据，包含以下列：
            - stock_name: 股票名称
            - stock_code: 股票代码
            - proportion: 持仓占比
            - industry: 所属行业
            - change_percent: 涨跌幅
            - fund_code: 基金代码
    """
    logger.info(f"开始获取基金 {fund_code} 的持仓数据")
    
    # 依次尝试不同的数据源
    data_sources = [
        _get_holdings_from_akshare,
        _get_holdings_from_eastmoney,
        _get_holdings_from_sina
    ]
    
    for source_func in data_sources:
        try:
            logger.info(f"尝试从 {source_func.__name__} 获取数据...")
            holdings_df = source_func(fund_code)
            
            if holdings_df is not None and not holdings_df.empty:
                logger.info(f"成功从 {source_func.__name__} 获取 {len(holdings_df)} 条持仓数据")
                logger.info(f"持仓数据列: {list(holdings_df.columns)}")
                return holdings_df
                
        except Exception as e:
            logger.warning(f"从 {source_func.__name__} 获取数据失败: {e}")
            continue
    
    logger.error(f"所有数据源均无法获取基金 {fund_code} 的持仓数据")
    return None


def _get_holdings_from_akshare(fund_code):
    """从akshare获取基金持仓数据"""
    try:
        df = ak.fund_portfolio_hold_em(symbol=fund_code, date=None)
        
        if df is None or df.empty:
            logger.warning(f"akshare返回空数据: {fund_code}")
            return None
        
        # 标准化列名
        column_mapping = {
            '股票名称': 'stock_name',
            '股票代码': 'stock_code',
            '占净值比例': 'proportion',
            '持仓市值': 'market_value',
            '涨跌幅': 'change_percent'
        }
        
        # 重命名列
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df[new_col] = df[old_col]
        
        # 添加基金代码
        df['fund_code'] = fund_code
        
        # 尝试获取行业信息
        df['industry'] = df['stock_name'].apply(_get_industry_by_stock_name)
        
        # 只保留需要的列
        required_cols = ['stock_name', 'stock_code', 'proportion', 'industry', 'change_percent', 'fund_code']
        available_cols = [col for col in required_cols if col in df.columns]
        df = df[available_cols].copy()
        
        return df.head(10)  # 只取前10大重仓股
        
    except Exception as e:
        logger.error(f"akshare获取数据失败: {e}")
        raise


def _get_holdings_from_eastmoney(fund_code):
    """从天天基金网获取基金持仓数据"""
    try:
        url = f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={fund_code}&topline=10"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        # 解析返回的JSONP数据
        text = response.text
        if 'var' in text:
            json_str = text[text.find('{'):text.rfind('}')+1]
            data = json.loads(json_str)
            
            if 'data' in data and len(data['data']) > 0:
                holdings = []
                for item in data['data'][:10]:
                    holdings.append({
                        'stock_name': item.get('GPM', ''),
                        'stock_code': item.get('GPJC', ''),
                        'proportion': float(item.get('JZBL', 0)),
                        'industry': _get_industry_by_stock_name(item.get('GPM', '')),
                        'change_percent': item.get('ZDF', '--'),
                        'fund_code': fund_code
                    })
                
                return pd.DataFrame(holdings)
        
        logger.warning(f"天天基金网返回数据格式异常: {fund_code}")
        return None
        
    except Exception as e:
        logger.error(f"天天基金网获取数据失败: {e}")
        raise


def _get_holdings_from_sina(fund_code):
    """从新浪财经获取基金持仓数据"""
    try:
        url = f"https://stock.finance.sina.com.cn/fundInfo/api/openapi.php/CaihuiFundInfoService.getFundPortDetail?symbol={fund_code}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if 'result' in data and 'data' in data['result']:
            holdings_data = data['result']['data']
            
            if holdings_data and len(holdings_data) > 0:
                holdings = []
                for item in holdings_data[:10]:
                    holdings.append({
                        'stock_name': item.get('name', ''),
                        'stock_code': item.get('code', ''),
                        'proportion': float(item.get('ratio', 0)),
                        'industry': _get_industry_by_stock_name(item.get('name', '')),
                        'change_percent': item.get('change', '--'),
                        'fund_code': fund_code
                    })
                
                return pd.DataFrame(holdings)
        
        logger.warning(f"新浪财经返回数据格式异常: {fund_code}")
        return None
        
    except Exception as e:
        logger.error(f"新浪财经获取数据失败: {e}")
        raise


def _get_industry_by_stock_name(stock_name):
    """根据股票名称推断所属行业（简化版）"""
    industry_mapping = {
        '茅台': '食品饮料', '五粮液': '食品饮料', '食品': '食品饮料', '饮料': '食品饮料',
        '宁德': '新能源', '隆基': '新能源', '阳光电源': '新能源', '新能源': '新能源',
        '银行': '银行', '招商': '银行', '平安银行': '银行', '工商银行': '银行',
        '保险': '保险', '中国平安': '保险', '人寿': '保险', '太保': '保险',
        '腾讯': '互联网', '阿里': '互联网', '美团': '互联网', '字节': '互联网',
        '医药': '医药生物', '药明': '医药生物', '恒瑞': '医药生物', '康龙': '医药生物',
        '白酒': '食品饮料', '啤酒': '食品饮料', '红酒': '食品饮料',
        '证券': '非银金融', '中信': '非银金融', '建投': '非银金融', '中金': '非银金融',
        '汽车': '汽车', '比亚迪': '汽车', '长城': '汽车', '上汽': '汽车',
        '电子': '电子', '立讯': '电子', '歌尔': '电子', '半导体': '电子',
        '化工': '化工', '万华': '化工', '石化': '化工',
        '机械': '机械设备', '三一': '机械设备', '中联': '机械设备'
    }
    
    for keyword, industry in industry_mapping.items():
        if keyword in stock_name:
            return industry
    
    return '其他'

def calculate_asset_allocation(holdings_df, total_asset, fund_codes_count=1):
    """
    Calculate asset allocation based on holdings data
    
    Args:
        holdings_df: 持仓数据DataFrame
        total_asset: 总资产（用于市值计算）
        fund_codes_count: 基金数量（用于加权平均）
    """
    try:
        # Group by asset type
        if 'asset_type' in holdings_df.columns:
            asset_groups = holdings_df.groupby('asset_type')['proportion'].sum()
        else:
            # Default to stock allocation if no asset type column
            # 当多个基金时，需要计算加权平均而不是简单相加
            stock_proportion = holdings_df['proportion'].sum()
            # 按基金数量加权平均，确保总比例不超过100%
            weighted_stock_proportion = stock_proportion / max(fund_codes_count, 1)
            asset_groups = pd.Series({'股票': weighted_stock_proportion, '债券': 0, '现金': 0, '其他': 0})
        
        # Convert to dictionary with percentage format
        asset_allocation = {}
        for asset_type, proportion in asset_groups.items():
            # 对多基金情况进行加权平均
            adjusted_proportion = proportion / max(fund_codes_count, 1)
            asset_allocation[str(asset_type)] = round(float(adjusted_proportion), 2)
        
        return asset_allocation
    except Exception as e:
        logger.error(f"计算资产配置失败: {e}")
        return {}

def calculate_industry_distribution(holdings_df, total_asset, fund_codes_count=1):
    """
    Calculate industry distribution based on holdings data
    
    Args:
        holdings_df: 持仓数据DataFrame
        total_asset: 总资产（用于市值计算）
        fund_codes_count: 基金数量（用于加权平均）
    """
    try:
        # Group by industry
        if 'industry' in holdings_df.columns:
            industry_groups = holdings_df.groupby('industry')['proportion'].sum()
        elif 'industry_name' in holdings_df.columns:
            industry_groups = holdings_df.groupby('industry_name')['proportion'].sum()
        else:
            # Default to empty if no industry column
            return {}
        
        # Sort by proportion
        industry_groups = industry_groups.sort_values(ascending=False)
        
        # Convert to dictionary with percentage format
        # 对多基金情况进行加权平均
        industry_distribution = {}
        for industry, proportion in industry_groups.items():
            adjusted_proportion = proportion / max(fund_codes_count, 1)
            industry_distribution[str(industry)] = round(float(adjusted_proportion), 2)
        
        return industry_distribution
    except Exception as e:
        logger.error(f"计算行业分布失败: {e}")
        return {}

def calculate_top_stocks(holdings_df, total_asset, fund_codes_count=1):
    """
    Calculate top stocks based on holdings data
    
    Args:
        holdings_df: 持仓数据DataFrame
        total_asset: 总资产（用于市值计算）
        fund_codes_count: 基金数量（用于加权平均）
    """
    try:
        # 首先收集每只股票关联的基金信息
        stock_fund_map = {}
        # 缓存基金名称避免重复查询
        fund_name_cache = {}
        
        if 'fund_code' in holdings_df.columns:
            for _, row in holdings_df.iterrows():
                stock_key = (str(row.get('stock_code', '')), str(row.get('stock_name', '')))
                fund_code = str(row.get('fund_code', ''))
                proportion = float(row.get('proportion', 0))
                
                # 获取基金名称（优先从缓存）
                if fund_code not in fund_name_cache:
                    fund_name = row.get('fund_name', '') or get_fund_name_from_db(fund_code) or fund_code
                    fund_name_cache[fund_code] = fund_name
                else:
                    fund_name = fund_name_cache[fund_code]
                
                if stock_key not in stock_fund_map:
                    stock_fund_map[stock_key] = []
                
                # 避免重复添加同一基金
                existing_codes = [f['fund_code'] for f in stock_fund_map[stock_key]]
                if fund_code and fund_code not in existing_codes:
                    stock_fund_map[stock_key].append({
                        'fund_code': fund_code,
                        'fund_name': fund_name,
                        'proportion': round(proportion, 2)
                    })
        
        # Group by stock code and name, sum the proportions
        grouped = holdings_df.groupby(['stock_code', 'stock_name'], as_index=False)['proportion'].sum()
        
        # Sort by proportion
        sorted_holdings = grouped.sort_values('proportion', ascending=False).head(10)
        
        # Convert to list of dictionaries
        # 对多基金情况进行加权平均
        top_stocks = []
        for _, row in sorted_holdings.iterrows():
            raw_proportion = float(row.get('proportion', 0))
            adjusted_proportion = raw_proportion / max(fund_codes_count, 1)
            stock_code = str(row.get('stock_code', row.get('code', '')))
            stock_name = str(row.get('stock_name', row.get('name', '')))
            stock_key = (stock_code, stock_name)
            
            # 获取关联基金列表
            related_funds = stock_fund_map.get(stock_key, [])
            fund_count = len(related_funds) if related_funds else 1
            
            stock_info = {
                'stock_name': stock_name,
                'stock_code': stock_code,
                'proportion': round(adjusted_proportion, 2),
                'market_value': round(adjusted_proportion * total_asset / 100, 2),
                'change_percent': row.get('change_percent', row.get('涨跌幅', '--')),
                'fund_count': fund_count,
                'related_funds': related_funds
            }
            top_stocks.append(stock_info)
        
        return top_stocks
    except Exception as e:
        logger.error(f"计算重仓股失败: {e}")
        traceback.print_exc()
        return []

def generate_analysis_summary(asset_allocation, industry_distribution, top_stocks, fund_codes_count=1):
    """
    Generate analysis summary based on calculated data
    
    Args:
        asset_allocation: 资产配置字典
        industry_distribution: 行业分布字典
        top_stocks: 重仓股列表
        fund_codes_count: 基金数量（用于说明数据已加权平均）
    """
    try:
        summary = {
            'total_stock_proportion': 0,
            'top_industry_concentration': 0,
            'top_stock_concentration': 0,
            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
            'fund_count': fund_codes_count,
            'calculation_method': 'weighted_average' if fund_codes_count > 1 else 'simple'
        }
        
        # Calculate total stock proportion (already weighted)
        if asset_allocation:
            summary['total_stock_proportion'] = asset_allocation.get('股票', 0)
        
        # Calculate top industry concentration (top 3 industries) - already weighted
        if industry_distribution:
            top_industries = sorted(industry_distribution.values(), reverse=True)[:3]
            summary['top_industry_concentration'] = round(sum(top_industries), 2)
        
        # Calculate top stock concentration (top 5 stocks) - already weighted
        if top_stocks:
            top_5_stocks = top_stocks[:5]
            summary['top_stock_concentration'] = round(sum(stock['proportion'] for stock in top_5_stocks), 2)
        
        return summary
    except Exception as e:
        logger.error(f"生成分析摘要失败: {e}")
        return {}


def get_fund_strategy_analysis(fund_codes):
    """
    获取基金策略分析数据（集成enhanced_main.py的策略逻辑）
    
    Args:
        fund_codes: 基金代码列表
        
    Returns:
        dict: 包含策略分析结果的字典
    """
    try:
        from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
        from backtesting.enhanced_strategy import EnhancedInvestmentStrategy
        
        fund_data_manager = MultiSourceDataAdapter()
        strategy_engine = EnhancedInvestmentStrategy()
        
        results = []
        buy_count = 0
        sell_count = 0
        hold_count = 0
        
        for fund_code in fund_codes:
            try:
                # 获取基金名称
                fund_name = get_fund_name_from_db(fund_code) or fund_code
                
                # 获取实时数据
                realtime_data = fund_data_manager.get_realtime_data(fund_code, fund_name)
                performance_metrics = fund_data_manager.get_performance_metrics(fund_code)
                
                # 计算今日和昨日收益率
                today_return = float(realtime_data.get('today_return', 0.0))
                prev_day_return = float(realtime_data.get('prev_day_return', 0.0))
                
                # 投资策略分析
                strategy_result = strategy_engine.analyze_strategy(today_return, prev_day_return, performance_metrics)
                
                # 补充策略逻辑说明
                strategy_explanation = get_strategy_explanation(today_return, prev_day_return, strategy_result)
                
                fund_result = {
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'today_return': round(today_return, 2),
                    'prev_day_return': round(prev_day_return, 2),
                    'return_diff': round(today_return - prev_day_return, 2),
                    'status_label': strategy_result.get('status_label', ''),
                    'operation_suggestion': strategy_result.get('operation_suggestion', ''),
                    'execution_amount': strategy_result.get('execution_amount', ''),
                    'action': strategy_result.get('action', 'hold'),
                    'buy_multiplier': strategy_result.get('buy_multiplier', 0.0),
                    'redeem_amount': strategy_result.get('redeem_amount', 0.0),
                    'strategy_explanation': strategy_explanation,
                    'composite_score': performance_metrics.get('composite_score', 0.0),
                    'sharpe_ratio': performance_metrics.get('sharpe_ratio', 0.0)
                }
                
                results.append(fund_result)
                
                # 统计操作类型
                action = strategy_result.get('action', 'hold')
                if action in ['buy', 'strong_buy', 'weak_buy']:
                    buy_count += 1
                elif action in ['sell', 'redeem']:
                    sell_count += 1
                else:
                    hold_count += 1
                    
            except Exception as e:
                logger.warning(f"分析基金 {fund_code} 策略失败: {e}")
                results.append({
                    'fund_code': fund_code,
                    'fund_name': fund_code,
                    'today_return': 0,
                    'prev_day_return': 0,
                    'return_diff': 0,
                    'status_label': '🔴 数据获取失败',
                    'operation_suggestion': '暂无建议',
                    'execution_amount': '持有不动',
                    'action': 'hold',
                    'buy_multiplier': 0,
                    'redeem_amount': 0,
                    'strategy_explanation': '无法获取数据，建议人工核查',
                    'composite_score': 0,
                    'sharpe_ratio': 0
                })
                hold_count += 1
        
        return {
            'funds': results,
            'summary': {
                'total_count': len(fund_codes),
                'buy_count': buy_count,
                'sell_count': sell_count,
                'hold_count': hold_count,
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
        }
        
    except Exception as e:
        logger.error(f"获取策略分析数据失败: {e}")
        return {'funds': [], 'summary': {'total_count': 0, 'buy_count': 0, 'sell_count': 0, 'hold_count': 0}}


def get_strategy_explanation(today_return, prev_day_return, strategy_result):
    """
    生成策略判断的详细解释
    
    Args:
        today_return: 今日收益率
        prev_day_return: 昨日收益率
        strategy_result: 策略分析结果
        
    Returns:
        str: 策略解释文本
    """
    return_diff = today_return - prev_day_return
    action = strategy_result.get('action', 'hold')
    status_label = strategy_result.get('status_label', '')
    
    explanation_parts = []
    
    # 收益率趋势分析
    if today_return > 0 and prev_day_return > 0:
        if return_diff > 1:
            explanation_parts.append(f"连续上涨且涨幅扩大(差值+{return_diff:.2f}%)，处于上升趋势强势区")
        elif return_diff > 0:
            explanation_parts.append(f"连续上涨但涨幅放缓(差值+{return_diff:.2f}%)，可能接近阶段顶部")
        elif return_diff >= -1:
            explanation_parts.append(f"连续上涨涨幅收窄(差值{return_diff:.2f}%)，上涨动能减弱")
        else:
            explanation_parts.append(f"连续上涨但涨幅大幅回落(差值{return_diff:.2f}%)，注意回调风险")
    elif today_return > 0 and prev_day_return <= 0:
        explanation_parts.append(f"由跌转涨形成反转(今日+{today_return:.2f}% vs 昨日{prev_day_return:.2f}%)，可能是买入时机")
    elif today_return == 0 and prev_day_return > 0:
        explanation_parts.append(f"涨势暂停进入休整(今日0% vs 昨日+{prev_day_return:.2f}%)，观察后续走势")
    elif today_return < 0 and prev_day_return > 0:
        explanation_parts.append(f"由涨转跌形成反转(今日{today_return:.2f}% vs 昨日+{prev_day_return:.2f}%)，需要防范风险")
    elif today_return == 0 and prev_day_return <= 0:
        explanation_parts.append(f"下跌企稳(今日0% vs 昨日{prev_day_return:.2f}%)，可能是建仓时机")
    elif today_return < 0 and prev_day_return == 0:
        if today_return <= -2:
            explanation_parts.append(f"首次大跌(今日{today_return:.2f}%)，跌幅较大可考虑分批建仓")
        elif today_return <= -0.5:
            explanation_parts.append(f"首次下跌(今日{today_return:.2f}%)，可适度建仓")
        else:
            explanation_parts.append(f"微跌试探(今日{today_return:.2f}%)，观察为主")
    elif today_return < 0 and prev_day_return < 0:
        if return_diff > 1 and today_return <= -2:
            explanation_parts.append(f"连续下跌且跌幅加速(差值+{return_diff:.2f}%)，暴跌中可分批抄底")
        elif return_diff > 1:
            explanation_parts.append(f"连续下跌跌幅扩大(差值+{return_diff:.2f}%)，下跌趋势加速")
        elif (prev_day_return - today_return) > 0 and prev_day_return <= -2:
            explanation_parts.append(f"暴跌后跌幅收窄(差值{return_diff:.2f}%)，可能企稳")
        elif (prev_day_return - today_return) > 0:
            explanation_parts.append(f"下跌动能减弱(差值{return_diff:.2f}%)，跌速放缓")
        else:
            explanation_parts.append(f"阴跌持续(差值{return_diff:.2f}%)，可能在筑底")
    
    # 操作建议解释
    if action in ['buy', 'strong_buy', 'weak_buy']:
        buy_mult = strategy_result.get('buy_multiplier', 1.0)
        explanation_parts.append(f"策略建议：买入({buy_mult}×定投额)")
    elif action in ['sell', 'redeem']:
        redeem_amt = strategy_result.get('redeem_amount', 0)
        explanation_parts.append(f"策略建议：赎回(¥{redeem_amt})")
    else:
        explanation_parts.append("策略建议：持有观望")
    
    return '；'.join(explanation_parts)


def get_fund_name_from_db(fund_code):
    """从数据库获取基金名称（支持多个数据源）"""
    try:
        # 1. 首先尝试从 fund_basic_info 表获取（标准基金信息表）
        try:
            sql = "SELECT fund_name FROM fund_basic_info WHERE fund_code = :fund_code"
            result = db_manager.execute_query(sql, {'fund_code': fund_code})
            if result is not None and not result.empty:
                name = result.iloc[0]['fund_name']
                if name and name != fund_code:
                    return name
        except Exception as e:
            logger.debug(f"从fund_basic_info获取基金名称失败: {e}")
        
        # 2. 尝试从用户持仓表获取
        try:
            sql = "SELECT fund_name FROM user_holdings WHERE fund_code = :fund_code LIMIT 1"
            result = db_manager.execute_query(sql, {'fund_code': fund_code})
            if result is not None and not result.empty:
                name = result.iloc[0]['fund_name']
                if name and name != fund_code:
                    return name
        except Exception as e:
            logger.debug(f"从user_holdings获取基金名称失败: {e}")
        
        # 3. 尝试从基金分析结果表获取
        try:
            sql = "SELECT fund_name FROM fund_analysis_results WHERE fund_code = :fund_code ORDER BY analysis_date DESC LIMIT 1"
            result = db_manager.execute_query(sql, {'fund_code': fund_code})
            if result is not None and not result.empty:
                name = result.iloc[0]['fund_name']
                if name and name != fund_code:
                    return name
        except Exception as e:
            logger.debug(f"从fund_analysis_results获取基金名称失败: {e}")
        
        # 4. 尝试使用akshare实时获取
        try:
            import akshare as ak
            # 方法1: 从基金列表获取
            try:
                fund_list = ak.fund_name_em()
                if '基金代码' in fund_list.columns and '基金简称' in fund_list.columns:
                    fund_row = fund_list[fund_list['基金代码'] == fund_code]
                    if not fund_row.empty:
                        return fund_row.iloc[0]['基金简称']
            except:
                pass
            
            # 方法2: 从基金基本信息获取
            try:
                fund_info = ak.fund_individual_basic_info_xq(symbol=fund_code)
                if '基金名称' in fund_info.columns:
                    return fund_info['基金名称'].values[0]
            except:
                pass
                
            # 方法3: 从每日基金数据获取
            try:
                fund_daily = ak.fund_open_fund_daily_em()
                if '基金代码' in fund_daily.columns and '基金简称' in fund_daily.columns:
                    fund_row = fund_daily[fund_daily['基金代码'] == fund_code]
                    if not fund_row.empty:
                        return fund_row.iloc[0]['基金简称']
            except:
                pass
        except Exception as e:
            logger.debug(f"从akshare获取基金名称失败: {e}")
        
        return None
    except Exception as e:
        logger.warning(f"获取基金名称失败: {e}")
        return None


def get_personalized_investment_advice(fund_codes):
    """
    获取个性化投资建议（基于策略选择器）
    
    为每只基金分析其历史数据、风险特征、收益模式，
    从策略库中选择最优策略进行个性化分析
    
    Args:
        fund_codes: 基金代码列表
        
    Returns:
        dict: 包含每只基金的个性化投资建议
    """
    try:
        from backtesting.akshare_data_fetcher import fetch_fund_history_from_akshare
        from backtesting.strategy_selector import get_strategy_selector
        from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
        
        fund_data_manager = MultiSourceDataAdapter()
        strategy_selector = get_strategy_selector()
        
        results = []
        strategy_stats = {}
        
        for fund_code in fund_codes:
            try:
                # 获取基金名称
                fund_name = get_fund_name_from_db(fund_code) or fund_code
                
                # 获取基金历史数据（用于策略分析）
                historical_data = fetch_fund_history_from_akshare(fund_code, days=252)
                
                # 获取实时数据
                realtime_data = fund_data_manager.get_realtime_data(fund_code, fund_name)
                performance_metrics = fund_data_manager.get_performance_metrics(fund_code)
                
                today_return = float(realtime_data.get('today_return', 0.0))
                prev_day_return = float(realtime_data.get('prev_day_return', 0.0))
                
                # 使用策略选择器选择最优策略
                if historical_data is not None and not historical_data.empty:
                    match_result = strategy_selector.select_best_strategy(historical_data)
                    
                    # 获取基金画像
                    fund_profile = strategy_selector.analyze_fund_characteristics(historical_data)
                    
                    # 获取所有策略对比（用于展示）
                    all_signals = strategy_selector.get_all_strategy_signals(historical_data)
                else:
                    # 数据不足时使用默认策略
                    from backtesting.advanced_strategies import EnhancedRuleBasedStrategy
                    default_strategy = EnhancedRuleBasedStrategy()
                    
                    # 创建最小数据集
                    match_result = type('obj', (object,), {
                        'strategy_name': '增强规则基准策略',
                        'strategy_type': 'enhanced_rule',
                        'match_score': 50.0,
                        'reason': '历史数据不足，使用默认策略',
                        'signal': default_strategy.generate_signal(
                            pd.DataFrame({'nav': [1.0, 1.0 + today_return/100]}), 
                            current_index=1
                        ),
                        'backtest_score': 50.0
                    })()
                    fund_profile = None
                    all_signals = []
                
                # 构建建议详情
                signal = match_result.signal
                
                fund_result = {
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'today_return': round(today_return, 2),
                    'prev_day_return': round(prev_day_return, 2),
                    
                    # 最优策略信息
                    'optimal_strategy': {
                        'name': match_result.strategy_name,
                        'type': match_result.strategy_type,
                        'match_score': match_result.match_score,
                        'selection_reason': match_result.reason,
                        'backtest_score': match_result.backtest_score
                    },
                    
                    # 基金特征画像
                    'fund_profile': {
                        'volatility': round(fund_profile.volatility, 4) if fund_profile else None,
                        'trend_strength': round(fund_profile.trend_strength, 4) if fund_profile else None,
                        'mean_reversion_score': round(fund_profile.mean_reversion_score, 4) if fund_profile else None,
                        'sharpe_ratio': round(fund_profile.sharpe_ratio, 4) if fund_profile else performance_metrics.get('sharpe_ratio', 0),
                        'max_drawdown': round(fund_profile.max_drawdown, 4) if fund_profile else None,
                        'risk_level': fund_profile.risk_level if fund_profile else 'unknown'
                    } if fund_profile else None,
                    
                    # 当前建议
                    'advice': {
                        'action': signal.action,
                        'amount_multiplier': round(signal.amount_multiplier, 2),
                        'reason': signal.reason,
                        'description': signal.description,
                        'suggestion': signal.suggestion if hasattr(signal, 'suggestion') else '',
                        'status_label': _get_status_label(signal.action, signal.reason),
                        'operation_suggestion': _get_operation_suggestion(signal.action, signal.amount_multiplier),
                        'execution_amount': _get_execution_amount(signal.action, signal.amount_multiplier)
                    },
                    
                    # 所有策略对比（可选展示）
                    'all_strategies_comparison': [
                        {
                            'strategy_name': s['strategy_name'],
                            'action': s['action'],
                            'multiplier': round(s['multiplier'], 2),
                            'reason': s['reason']
                        }
                        for s in all_signals
                    ] if all_signals else []
                }
                
                results.append(fund_result)
                
                # 统计策略使用情况
                strategy_type = match_result.strategy_type
                strategy_stats[strategy_type] = strategy_stats.get(strategy_type, 0) + 1
                
            except Exception as e:
                logger.warning(f"分析基金 {fund_code} 个性化建议失败: {e}")
                import traceback
                traceback.print_exc()
                
                # 添加失败记录
                results.append({
                    'fund_code': fund_code,
                    'fund_name': fund_code,
                    'today_return': 0,
                    'prev_day_return': 0,
                    'optimal_strategy': {
                        'name': '分析失败',
                        'type': 'error',
                        'match_score': 0,
                        'selection_reason': str(e),
                        'backtest_score': 0
                    },
                    'advice': {
                        'action': 'hold',
                        'amount_multiplier': 0,
                        'reason': '分析失败',
                        'description': '无法获取数据',
                        'status_label': '数据异常',
                        'operation_suggestion': '暂时持有',
                        'execution_amount': '持有不动'
                    }
                })
        
        # 统计汇总
        buy_count = sum(1 for r in results if r['advice']['action'] in ['buy', 'strong_buy'])
        sell_count = sum(1 for r in results if r['advice']['action'] in ['sell', 'redeem'])
        hold_count = sum(1 for r in results if r['advice']['action'] == 'hold')
        
        return {
            'success': True,
            'funds': results,
            'summary': {
                'total_count': len(fund_codes),
                'buy_count': buy_count,
                'sell_count': sell_count,
                'hold_count': hold_count,
                'strategy_distribution': strategy_stats,
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'is_personalized': True  # 标记为个性化分析
            }
        }
        
    except Exception as e:
        logger.error(f"获取个性化投资建议失败: {e}")
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'funds': [],
            'summary': {
                'total_count': len(fund_codes),
                'buy_count': 0,
                'sell_count': 0,
                'hold_count': 0
            }
        }


def _get_status_label(action, reason):
    """根据操作和原因生成状态标签"""
    action_icons = {
        'buy': '🟢',
        'strong_buy': '🟢',
        'weak_buy': '🟢',
        'sell': '🔴',
        'redeem': '🔴',
        'hold': '🟡'
    }
    
    icon = action_icons.get(action, '⚪')
    
    # 从reason中提取关键词
    if '低估' in reason or '超低' in reason:
        return f"{icon} 低估区域"
    elif '高估' in reason or '超高' in reason:
        return f"{icon} 高估区域"
    elif '金叉' in reason:
        return f"{icon} 金叉趋势"
    elif '死叉' in reason:
        return f"{icon} 死叉趋势"
    elif '网格' in reason:
        return f"{icon} 网格触发"
    else:
        return f"{icon} {reason[:10]}" if reason else f"{icon} 分析完成"


def _get_operation_suggestion(action, multiplier):
    """生成操作建议"""
    if action in ['buy', 'strong_buy']:
        if multiplier >= 2.0:
            return f"强烈买入({multiplier}×定投额)"
        elif multiplier >= 1.5:
            return f"积极买入({multiplier}×定投额)"
        else:
            return f"适度买入({multiplier}×定投额)"
    elif action in ['sell', 'redeem']:
        return "建议止盈出售"
    else:
        return "建议持有观望"


def _get_execution_amount(action, multiplier):
    """生成执行金额建议"""
    if action in ['buy', 'strong_buy']:
        return f"买入{multiplier}×基础定投额"
    elif action in ['sell', 'redeem']:
        return "赎回部分仓位"
    else:
        return "持有不动"


# 模块导出
__all__ = [
    'init_db_manager',
    'get_fund_holdings_data',
    '_get_holdings_from_akshare',
    '_get_holdings_from_eastmoney',
    '_get_holdings_from_sina',
    '_get_industry_by_stock_name',
    'calculate_asset_allocation',
    'calculate_industry_distribution',
    'calculate_top_stocks',
    'generate_analysis_summary',
    'get_fund_strategy_analysis',
    'get_strategy_explanation',
    'get_fund_name_from_db',
    'get_personalized_investment_advice',
    'get_personalized_investment_advice_parallel',  # 新增并行版本
]


# ==================== 并行处理优化 ====================

def _analyze_single_fund(fund_code: str) -> dict:
    """
    分析单只基金（用于并行处理）
    
    Args:
        fund_code: 基金代码
        
    Returns:
        dict: 单只基金的分析结果
    """
    try:
        # 使用线程本地对象
        fund_data_manager, strategy_selector = _get_thread_local_objects()
        
        # 导入akshare数据获取（支持缓存）
        from backtesting.akshare_data_fetcher import fetch_fund_history_from_akshare
        
        # 获取基金名称
        fund_name = get_fund_name_from_db(fund_code) or fund_code
        
        # 获取基金历史数据（使用缓存）
        historical_data = fetch_fund_history_from_akshare(fund_code, days=252)
        
        # 获取实时数据
        realtime_data = fund_data_manager.get_realtime_data(fund_code, fund_name)
        performance_metrics = fund_data_manager.get_performance_metrics(fund_code)
        
        today_return = float(realtime_data.get('today_return', 0.0))
        prev_day_return = float(realtime_data.get('prev_day_return', 0.0))
        
        # 使用策略选择器选择最优策略
        if historical_data is not None and not historical_data.empty:
            match_result = strategy_selector.select_best_strategy(historical_data)
            fund_profile = strategy_selector.analyze_fund_characteristics(historical_data)
            all_signals = strategy_selector.get_all_strategy_signals(historical_data)
        else:
            from backtesting.advanced_strategies import EnhancedRuleBasedStrategy
            default_strategy = EnhancedRuleBasedStrategy()
            match_result = type('obj', (object,), {
                'strategy_name': '增强规则基准策略',
                'strategy_type': 'enhanced_rule',
                'match_score': 50.0,
                'reason': '历史数据不足，使用默认策略',
                'signal': default_strategy.generate_signal(
                    pd.DataFrame({'nav': [1.0, 1.0 + today_return/100]}), 
                    current_index=1
                ),
                'backtest_score': 50.0
            })()
            fund_profile = None
            all_signals = []
        
        signal = match_result.signal
        
        return {
            'fund_code': fund_code,
            'fund_name': fund_name,
            'today_return': round(today_return, 2),
            'prev_day_return': round(prev_day_return, 2),
            'optimal_strategy': {
                'name': match_result.strategy_name,
                'type': match_result.strategy_type,
                'match_score': match_result.match_score,
                'selection_reason': match_result.reason,
                'backtest_score': match_result.backtest_score
            },
            'fund_profile': {
                'volatility': round(fund_profile.volatility, 4) if fund_profile else None,
                'trend_strength': round(fund_profile.trend_strength, 4) if fund_profile else None,
                'mean_reversion_score': round(fund_profile.mean_reversion_score, 4) if fund_profile else None,
                'sharpe_ratio': round(fund_profile.sharpe_ratio, 4) if fund_profile else performance_metrics.get('sharpe_ratio', 0),
                'max_drawdown': round(fund_profile.max_drawdown, 4) if fund_profile else None,
                'risk_level': fund_profile.risk_level if fund_profile else 'unknown'
            } if fund_profile else None,
            'advice': {
                'action': signal.action,
                'amount_multiplier': round(signal.amount_multiplier, 2),
                'reason': signal.reason,
                'description': signal.description,
                'suggestion': signal.suggestion if hasattr(signal, 'suggestion') else '',
                'status_label': _get_status_label(signal.action, signal.reason),
                'operation_suggestion': _get_operation_suggestion(signal.action, signal.amount_multiplier),
                'execution_amount': _get_execution_amount(signal.action, signal.amount_multiplier)
            },
            'all_strategies_comparison': [
                {
                    'strategy_name': s['strategy_name'],
                    'action': s['action'],
                    'multiplier': round(s['multiplier'], 2),
                    'reason': s['reason']
                }
                for s in all_signals
            ] if all_signals else [],
            'strategy_type': match_result.strategy_type,
            'success': True
        }
        
    except Exception as e:
        logger.warning(f"[并行分析] 基金 {fund_code} 分析失败: {e}")
        return {
            'fund_code': fund_code,
            'fund_name': fund_code,
            'today_return': 0,
            'prev_day_return': 0,
            'optimal_strategy': {
                'name': '分析失败',
                'type': 'error',
                'match_score': 0,
                'selection_reason': str(e),
                'backtest_score': 0
            },
            'advice': {
                'action': 'hold',
                'amount_multiplier': 0,
                'reason': '分析失败',
                'description': '无法获取数据',
                'status_label': '数据异常',
                'operation_suggestion': '暂时持有',
                'execution_amount': '持有不动'
            },
            'strategy_type': 'error',
            'success': False,
            'error': str(e)
        }


def get_personalized_investment_advice_parallel(fund_codes: list, max_workers: int = 5) -> dict:
    """
    获取个性化投资建议（并行处理版本）
    
    使用多线程并行处理多只基金，显著提升分析速度
    
    Args:
        fund_codes: 基金代码列表
        max_workers: 最大并行线程数，默认5
        
    Returns:
        dict: 包含每只基金的个性化投资建议
    """
    start_time = time.time()
    logger.info(f"[并行分析] 开始分析 {len(fund_codes)} 只基金，最大并行数: {max_workers}")
    
    results = []
    strategy_stats = {}
    
    try:
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_code = {
                executor.submit(_analyze_single_fund, code): code 
                for code in fund_codes
            }
            
            # 收集结果
            for future in as_completed(future_to_code):
                fund_code = future_to_code[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # 统计策略使用情况
                    if result.get('success'):
                        strategy_type = result.get('strategy_type', 'unknown')
                        strategy_stats[strategy_type] = strategy_stats.get(strategy_type, 0) + 1
                        logger.info(f"[并行分析] 基金 {fund_code} 分析完成，策略: {strategy_type}")
                    else:
                        logger.warning(f"[并行分析] 基金 {fund_code} 分析失败")
                        
                except Exception as e:
                    logger.error(f"[并行分析] 基金 {fund_code} 执行异常: {e}")
                    results.append({
                        'fund_code': fund_code,
                        'fund_name': fund_code,
                        'success': False,
                        'error': str(e)
                    })
        
        # 统计汇总
        buy_count = sum(1 for r in results if r.get('advice', {}).get('action') in ['buy', 'strong_buy'])
        sell_count = sum(1 for r in results if r.get('advice', {}).get('action') in ['sell', 'redeem'])
        hold_count = sum(1 for r in results if r.get('advice', {}).get('action') == 'hold')
        
        elapsed_time = time.time() - start_time
        logger.info(f"[并行分析] 分析完成，耗时: {elapsed_time:.2f}秒，平均每只基金: {elapsed_time/len(fund_codes):.2f}秒")
        
        return {
            'success': True,
            'funds': results,
            'summary': {
                'total_count': len(fund_codes),
                'buy_count': buy_count,
                'sell_count': sell_count,
                'hold_count': hold_count,
                'strategy_distribution': strategy_stats,
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'is_personalized': True,
                'is_parallel': True,
                'elapsed_seconds': round(elapsed_time, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"[并行分析] 获取个性化投资建议失败: {e}")
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'funds': [],
            'summary': {
                'total_count': len(fund_codes),
                'buy_count': 0,
                'sell_count': 0,
                'hold_count': 0
            }
        }
