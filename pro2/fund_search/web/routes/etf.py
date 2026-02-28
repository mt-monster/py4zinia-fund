#!/usr/bin/env python
# coding: utf-8

"""
ETF 相关 API 路由
"""

import os
import sys
import logging
import traceback
from datetime import datetime, timedelta

import pandas as pd
import akshare as ak
from flask import Flask, render_template, jsonify, request

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_access.enhanced_database import EnhancedDatabaseManager
from backtesting.strategies.enhanced_strategy import EnhancedInvestmentStrategy
from backtesting.core.unified_strategy_engine import UnifiedStrategyEngine
from backtesting.analysis.strategy_evaluator import StrategyEvaluator
from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
from data_retrieval.fetchers.heavyweight_stocks_fetcher import fetch_heavyweight_stocks, get_fetcher
from services.fund_type_service import (
    FundTypeService, classify_fund, get_fund_type_display, 
    get_fund_type_css_class, FUND_TYPE_CN, FUND_TYPE_CSS_CLASS
)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 全局组件引用（由 register_routes 注入）
db_manager = None
strategy_engine = None
unified_strategy_engine = None
strategy_evaluator = None
fund_data_manager = None


def register_routes(app, **kwargs):
    """注册 ETF 相关路由
    
    Args:
        app: Flask 应用实例
        **kwargs: 包含各组件的可选参数
    """
    global db_manager, strategy_engine, unified_strategy_engine, strategy_evaluator, fund_data_manager
    
    # 从 kwargs 获取组件（支持新旧两种方式）
    components = kwargs.get('components')
    if components:
        db_manager = components.get('db_manager')
        strategy_engine = components.get('strategy_engine')
        unified_strategy_engine = components.get('unified_strategy_engine')
        strategy_evaluator = components.get('strategy_evaluator')
        fund_data_manager = components.get('fund_data_manager')
    else:
        db_manager = kwargs.get('db_manager') or kwargs.get('database_manager')
        strategy_engine = kwargs.get('strategy_engine')
        unified_strategy_engine = kwargs.get('unified_strategy_engine')
        strategy_evaluator = kwargs.get('strategy_evaluator')
        fund_data_manager = kwargs.get('fund_data_manager')
    
    # 如果 kwargs 中没有，尝试从 app 属性获取
    if db_manager is None:
        db_manager = app.db_manager if hasattr(app, 'db_manager') else None
    if strategy_engine is None:
        strategy_engine = app.strategy_engine if hasattr(app, 'strategy_engine') else None
    if unified_strategy_engine is None:
        unified_strategy_engine = app.unified_strategy_engine if hasattr(app, 'unified_strategy_engine') else None
    if strategy_evaluator is None:
        strategy_evaluator = app.strategy_evaluator if hasattr(app, 'strategy_evaluator') else None
    if fund_data_manager is None:
        fund_data_manager = app.fund_data_manager if hasattr(app, 'fund_data_manager') else None
    
    # 注册所有路由
    app.route('/api/etf/list', methods=['GET'])(get_etf_list)
    app.route('/api/etf/<etf_code>', methods=['GET'])(get_etf_detail)
    app.route('/api/etf/<etf_code>/history', methods=['GET'])(get_etf_history)
    app.route('/api/etf/<etf_code>/holdings', methods=['GET'])(get_etf_holdings)
    app.route('/api/etf/<etf_code>/info', methods=['GET'])(get_etf_info)
    
    logger.info("ETF 路由注册完成")


# ==================== ETF市场 API ====================

def get_etf_list():
    """获取全市场ETF列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort_by', 'turnover')
        sort_order = request.args.get('sort_order', 'desc')
        
        # 获取ETF列表
        etf_df = fund_data_manager.get_etf_list()
        
        if etf_df.empty:
            return jsonify({'success': True, 'data': [], 'total': 0, 'page': page, 'per_page': per_page})
        
        # 搜索过滤
        if search:
            mask = (etf_df['etf_code'].str.contains(search, na=False) | 
                   etf_df['etf_name'].str.contains(search, na=False))
            etf_df = etf_df[mask]
        
        # 排序
        valid_sort_fields = ['etf_code', 'etf_name', 'current_price', 'change_percent', 
                            'volume', 'turnover', 'turnover_rate', 'amplitude']
        if sort_by in valid_sort_fields and sort_by in etf_df.columns:
            ascending = sort_order != 'desc'
            etf_df = etf_df.sort_values(sort_by, ascending=ascending, na_position='last')
        
        total = len(etf_df)
        
        # 分页
        start = (page - 1) * per_page
        etf_page = etf_df.iloc[start:start + per_page]
        
        # 转换为字典列表
        etf_list = []
        for _, row in etf_page.iterrows():
            etf_item = row.to_dict()
            # 清理NaN值
            for key in etf_item:
                if pd.isna(etf_item[key]):
                    etf_item[key] = None
                elif isinstance(etf_item[key], float):
                    etf_item[key] = round(etf_item[key], 4)
            etf_list.append(etf_item)
        
        return jsonify({
            'success': True, 
            'data': etf_list, 
            'total': total, 
            'page': page, 
            'per_page': per_page
        })
        
    except Exception as e:
        logger.error(f"获取ETF列表失败: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def get_etf_detail(etf_code):
    """获取单个ETF详情"""
    try:
        # 获取ETF列表找到该ETF
        etf_df = fund_data_manager.get_etf_list()
        
        if etf_df.empty:
            return jsonify({'success': False, 'error': 'ETF数据获取失败'}), 500
        
        etf_row = etf_df[etf_df['etf_code'] == etf_code]
        
        if etf_row.empty:
            return jsonify({'success': False, 'error': 'ETF不存在'}), 404
        
        etf_data = etf_row.iloc[0].to_dict()
        
        # 获取绩效指标
        performance = fund_data_manager.get_etf_performance(etf_code)
        etf_data.update(performance)
        
        # 清理NaN值
        for key in etf_data:
            if pd.isna(etf_data[key]):
                etf_data[key] = None
            elif isinstance(etf_data[key], float):
                etf_data[key] = round(etf_data[key], 4)
        
        return jsonify({'success': True, 'data': etf_data})
        
    except Exception as e:
        logger.error(f"获取ETF详情失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def get_etf_history(etf_code):
    """获取ETF历史行情和净值数据"""
    try:
        from datetime import datetime as dt
        
        period = request.args.get('period', '')
        days = request.args.get('days', 30, type=int)
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        # 如果有自定义日期范围
        if start_date and end_date:
            start = dt.strptime(start_date, '%Y-%m-%d')
            end = dt.strptime(end_date, '%Y-%m-%d')
            days = (end - start).days + 1
        else:
            # 根据period计算days
            today = dt.now()
            if period == '1m':
                days = 30
            elif period == '3m':
                days = 90
            elif period == '6m':
                days = 180
            elif period == '1y':
                days = 365
            elif period == '3y':
                days = 1095
            elif period == 'ytd':
                year_start = dt(today.year, 1, 1)
                days = (today - year_start).days + 1
            elif period == 'all':
                days = 9999
        
        # 获取ETF净值历史数据（包含单位净值、累计净值）
        nav_data = fund_data_manager.get_etf_nav_history(etf_code, days, start_date, end_date)
        
        if nav_data.empty:
            # 如果净值数据为空，尝试获取行情数据作为备选
            hist_data = fund_data_manager.get_etf_history(etf_code, days)
            if hist_data.empty:
                return jsonify({'success': True, 'data': []})
            
            # 如果有自定义日期范围，进行过滤
            if start_date and end_date:
                hist_data['date'] = pd.to_datetime(hist_data['date'])
                hist_data = hist_data[(hist_data['date'] >= start_date) & (hist_data['date'] <= end_date)]
            
            # 转换日期格式
            if 'date' in hist_data.columns:
                hist_data['date'] = pd.to_datetime(hist_data['date']).dt.strftime('%Y-%m-%d')
            
            # 清理NaN值
            result_data = []
            for _, row in hist_data.iterrows():
                item = row.to_dict()
                for key in item:
                    if pd.isna(item[key]):
                        item[key] = None
                    elif isinstance(item[key], float):
                        item[key] = round(item[key], 4)
                result_data.append(item)
            
            return jsonify({'success': True, 'data': result_data})
        
        # 如果有自定义日期范围，进行过滤
        if start_date and end_date:
            nav_data['date'] = pd.to_datetime(nav_data['date'])
            nav_data = nav_data[(nav_data['date'] >= start_date) & (nav_data['date'] <= end_date)]
        
        # 转换日期格式
        if 'date' in nav_data.columns:
            nav_data['date'] = pd.to_datetime(nav_data['date']).dt.strftime('%Y-%m-%d')
        
        # 清理NaN值并构建结果
        result_data = []
        for _, row in nav_data.iterrows():
            item = row.to_dict()
            for key in item:
                if pd.isna(item[key]):
                    item[key] = None
                elif isinstance(item[key], float):
                    item[key] = round(item[key], 4)
            result_data.append(item)
        
        return jsonify({'success': True, 'data': result_data})
        
    except Exception as e:
        logger.error(f"获取ETF历史数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def get_etf_holdings(etf_code):
    """获取ETF持仓数据"""
    try:
        holdings = []
        update_date = None
        
        try:
            holdings_df = ak.fund_etf_fund_info_em(fund=etf_code)
            
            if holdings_df is not None and not holdings_df.empty:
                # 处理持仓数据
                for _, row in holdings_df.head(20).iterrows():
                    holding = {}
                    for col in holdings_df.columns:
                        val = row[col]
                        if pd.isna(val):
                            holding[col] = None
                        elif isinstance(val, float):
                            holding[col] = round(val, 4)
                        else:
                            holding[col] = str(val)
                    holdings.append(holding)
        except Exception as e:
            logger.warning(f"获取ETF持仓失败: {str(e)}")
            # 尝试备用方法
            try:
                holdings_df = ak.fund_portfolio_hold_em(symbol=etf_code, date="2024")
                if holdings_df is not None and not holdings_df.empty:
                    if '季度' in holdings_df.columns:
                        update_date = str(holdings_df['季度'].iloc[0])
                    
                    for _, row in holdings_df.head(10).iterrows():
                        holdings.append({
                            'stock_code': str(row.get('股票代码', '')),
                            'stock_name': str(row.get('股票名称', '')),
                            'ratio': round(float(row.get('占净值比例', 0)), 2) if pd.notna(row.get('占净值比例')) else None,
                            'shares': row.get('持股数', None),
                            'value': row.get('持仓市值', None)
                        })
            except:
                pass
        
        return jsonify({
            'success': True,
            'data': {
                'holdings': holdings,
                'update_date': update_date
            }
        })
        
    except Exception as e:
        logger.error(f"获取ETF持仓失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def get_etf_info(etf_code):
    """获取ETF基金公司和基金经理信息"""
    try:
        info = {
            'fund_company': None,
            'fund_manager': None,
            'establish_date': None,
            'fund_type': 'ETF',
            'benchmark': None,
            'management_fee': None,
            'custody_fee': None,
            'fund_size': None
        }
        
        try:
            # 获取基金基本信息
            fund_info = ak.fund_individual_basic_info_xq(symbol=etf_code)
            if fund_info is not None and not fund_info.empty:
                info_dict = {}
                for _, row in fund_info.iterrows():
                    key = row.iloc[0] if len(row) > 0 else None
                    val = row.iloc[1] if len(row) > 1 else None
                    if key:
                        info_dict[str(key)] = val
                
                info['fund_company'] = info_dict.get('基金公司', info_dict.get('管理人', None))
                info['fund_manager'] = info_dict.get('基金经理', None)
                info['establish_date'] = info_dict.get('成立日期', info_dict.get('成立时间', None))
                info['benchmark'] = info_dict.get('业绩比较基准', None)
                info['management_fee'] = info_dict.get('管理费率', None)
                info['custody_fee'] = info_dict.get('托管费率', None)
                info['fund_size'] = info_dict.get('基金规模', info_dict.get('资产规模', None))
        except Exception as e:
            logger.warning(f"从雪球获取基金信息失败: {str(e)}")
            
            # 备用方法：从天天基金获取
            try:
                fund_info = ak.fund_open_fund_info_em(symbol=etf_code, indicator="基本信息")
                if fund_info is not None and not fund_info.empty:
                    info_dict = {}
                    for _, row in fund_info.iterrows():
                        info_dict[row['项目']] = row['数值']
                    
                    info['fund_company'] = info_dict.get('基金管理人', None)
                    info['fund_manager'] = info_dict.get('基金经理', None)
                    info['establish_date'] = info_dict.get('成立日期', None)
                    info['management_fee'] = info_dict.get('管理费率', None)
                    info['custody_fee'] = info_dict.get('托管费率', None)
            except:
                pass
        
        return jsonify({'success': True, 'data': info})
        
    except Exception as e:
        logger.error(f"获取ETF信息失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
