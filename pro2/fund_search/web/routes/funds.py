#!/usr/bin/env python
# coding: utf-8

"""
基金相关 API 路由
从 app.py 中提取的基金相关路由函数
"""

import os
import sys
import logging
import numpy as np
from datetime import datetime, timedelta

import pandas as pd
import akshare as ak
from flask import Flask, jsonify, request

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings  # 使用统一配置管理
# 使用方式: settings.database (替代 DATABASE_CONFIG), settings.notification (替代 NOTIFICATION_CONFIG)
from data_access.enhanced_database import EnhancedDatabaseManager
from backtesting.strategies.enhanced_strategy import EnhancedInvestmentStrategy
from backtesting.core.unified_strategy_engine import UnifiedStrategyEngine
from backtesting.analysis.strategy_evaluator import StrategyEvaluator
from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
from services.fund_type_service import (
    FundTypeService, classify_fund, get_fund_type_display, 
    get_fund_type_css_class, FUND_TYPE_CN, FUND_TYPE_CSS_CLASS
)
from shared.json_utils import safe_jsonify, create_safe_response

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 全局变量 - 将在 register_routes 中初始化
db_manager = None
strategy_engine = None
unified_strategy_engine = None
strategy_evaluator = None
fund_data_manager = None


def register_routes(app, **kwargs):
    """注册基金相关路由到 Flask 应用
    
    Args:
        app: Flask 应用实例
        **kwargs: 可选的全局组件
            - db_manager: 数据库管理器
            - strategy_engine: 策略引擎
            - unified_strategy_engine: 统一策略引擎
            - strategy_evaluator: 策略评估器
            - fund_data_manager: 基金数据管理器
    """
    global db_manager, strategy_engine, unified_strategy_engine, strategy_evaluator, fund_data_manager
    
    # 从 kwargs 获取组件，如果不存在则尝试从 app 获取
    db_manager = kwargs.get('db_manager')
    strategy_engine = kwargs.get('strategy_engine')
    unified_strategy_engine = kwargs.get('unified_strategy_engine')
    strategy_evaluator = kwargs.get('strategy_evaluator')
    fund_data_manager = kwargs.get('fund_data_manager')
    
    # 注册路由
    _register_fund_routes(app)
    
    logger.info("基金相关路由已注册")


def _register_fund_routes(app):
    """内部函数：注册所有基金相关路由"""
    
    @app.route('/api/funds', methods=['GET'])
    def get_funds():
        """获取基金列表（包含持仓盈亏数据）"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            search = request.args.get('search', '').strip()
            sort_by = request.args.get('sort_by', 'composite_score')
            sort_order = request.args.get('sort_order', 'desc')
            user_id = request.args.get('user_id', 'default_user')
            
            logger.info(f"搜索参数: search={search}, sort_by={sort_by}, page={page}")
            
            date_sql = "SELECT MAX(analysis_date) as max_date FROM fund_analysis_results"
            date_df = db_manager.execute_query(date_sql)
            
            if date_df.empty or date_df.iloc[0]['max_date'] is None:
                return safe_jsonify({'success': True, 'data': [], 'total': 0, 'page': page, 'per_page': per_page})
            
            max_date = date_df.iloc[0]['max_date']
            
            sql = """
            SELECT DISTINCT 
                far.fund_code, far.fund_name, far.today_return, far.prev_day_return,
                far.annualized_return, far.sharpe_ratio, far.sharpe_ratio_ytd, far.sharpe_ratio_1y, far.sharpe_ratio_all,
                far.max_drawdown, far.volatility,
                far.composite_score, far.status_label, far.operation_suggestion, far.analysis_date,
                far.current_estimate as current_nav, far.yesterday_nav as previous_nav,
                far.execution_amount, far.buy_multiplier, far.redeem_amount,
                h.holding_shares, h.cost_price, h.holding_amount, h.buy_date
            FROM fund_analysis_results far
            LEFT JOIN user_holdings h ON far.fund_code = h.fund_code AND h.user_id = 'default_user'
            WHERE far.analysis_date = :max_date
            """
            
            params = {'max_date': max_date}
            
            if search:
                sql += " AND (far.fund_code LIKE :search OR far.fund_name LIKE :search)"
                params['search'] = f'%{search}%'
            
            if sort_by not in ['today_profit_rate', 'holding_profit_rate', 'holding_amount']:
                valid_sort_fields = ['composite_score', 'today_return', 'prev_day_return', 'annualized_return', 
                                    'sharpe_ratio', 'max_drawdown', 'fund_code']
                if sort_by in valid_sort_fields:
                    sort_direction = 'DESC' if sort_order == 'desc' else 'ASC'
                    sql += f" ORDER BY far.{sort_by} {sort_direction}"
            
            df = db_manager.execute_query(sql, params)
            
            if df.empty:
                return safe_jsonify({'success': True, 'data': [], 'total': 0, 'page': page, 'per_page': per_page})
            
            # 计算盈亏指标
            funds_with_profit = []
            for _, row in df.iterrows():
                fund = row.to_dict()
                
                # 清理NaN值，将其转换为None（JSON兼容）- 使用numpy的函数处理各种类型的NaN
                import numpy as np
                for key in list(fund.keys()):
                    val = fund[key]
                    # 检查各种类型的NaN和Infinity
                    try:
                        if val is None:
                            continue
                        if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
                            fund[key] = None
                        elif pd.isna(val):
                            fund[key] = None
                    except:
                        # 如果检查失败，保留原值
                        pass
                
                # 基础数据格式化
                for key in ['annualized_return', 'max_drawdown', 'volatility']:
                    if fund.get(key) is not None:
                        try:
                            fund[key] = round(float(fund[key]) * 100, 2)
                        except (ValueError, TypeError):
                            fund[key] = None
                
                for key in ['today_return', 'prev_day_return']:
                    if fund.get(key) is not None:
                        try:
                            fund[key] = round(float(fund[key]), 2)
                        except (ValueError, TypeError):
                            fund[key] = None
                
                # 当 today_return 为空或为0时，用实时估值和昨日净值计算
                if not fund.get('today_return'):
                    cur = fund.get('current_nav')
                    prev = fund.get('previous_nav')
                    try:
                        cur_f = float(cur)
                        prev_f = float(prev)
                        if prev_f > 0 and cur_f > 0 and cur_f != prev_f:
                            fund['today_return'] = round((cur_f - prev_f) / prev_f * 100, 2)
                    except (TypeError, ValueError, ZeroDivisionError):
                        pass
                
                for key in ['sharpe_ratio', 'sharpe_ratio_ytd', 'sharpe_ratio_1y', 'sharpe_ratio_all', 'composite_score']:
                    if fund.get(key) is not None:
                        try:
                            fund[key] = round(float(fund[key]), 4)
                        except (ValueError, TypeError):
                            fund[key] = None
                
                # 计算持仓盈亏
                if pd.notna(fund.get('holding_shares')) and fund.get('holding_shares') is not None:
                    holding_shares = float(fund['holding_shares'])
                    cost_price = float(fund['cost_price']) if pd.notna(fund.get('cost_price')) else 0
                    holding_amount = float(fund['holding_amount']) if pd.notna(fund.get('holding_amount')) else 0
                    current_nav = float(fund['current_nav']) if pd.notna(fund.get('current_nav')) else cost_price
                    previous_nav = float(fund['previous_nav']) if pd.notna(fund.get('previous_nav')) else cost_price
                    
                    # 当前市值和昨日市值
                    current_value = holding_shares * current_nav
                    previous_value = holding_shares * previous_nav
                    
                    # 持有盈亏
                    holding_profit = current_value - holding_amount
                    holding_profit_rate = (holding_profit / holding_amount * 100) if holding_amount > 0 else 0
                    
                    # 当日盈亏
                    today_profit = current_value - previous_value
                    today_profit_rate = (today_profit / previous_value * 100) if previous_value > 0 else 0
                    
                    # 累计盈亏
                    total_profit = holding_profit
                    total_profit_rate = holding_profit_rate
                    
                    fund['holding_amount'] = round(holding_amount, 2)
                    fund['today_profit'] = round(today_profit, 2)
                    fund['today_profit_rate'] = round(today_profit_rate, 2)
                    fund['holding_profit'] = round(holding_profit, 2)
                    fund['holding_profit_rate'] = round(holding_profit_rate, 2)
                    fund['total_profit'] = round(total_profit, 2)
                    fund['total_profit_rate'] = round(total_profit_rate, 2)
                else:
                    # 没有持仓数据
                    fund['holding_amount'] = None
                    fund['today_profit'] = None
                    fund['today_profit_rate'] = None
                    fund['holding_profit'] = None
                    fund['holding_profit_rate'] = None
                    fund['total_profit'] = None
                    fund['total_profit_rate'] = None
                
                funds_with_profit.append(fund)
            
            # 排序（如果是持仓相关字段）
            if sort_by in ['today_profit_rate', 'holding_profit_rate', 'holding_amount']:
                funds_with_profit.sort(
                    key=lambda x: x.get(sort_by) if x.get(sort_by) is not None else float('-inf'),
                    reverse=(sort_order == 'desc')
                )
            
            total = len(funds_with_profit)
            start = (page - 1) * per_page
            funds_page = funds_with_profit[start:start + per_page]
            
            return safe_jsonify({'success': True, 'data': funds_page, 'total': total, 'page': page, 'per_page': per_page})
            
        except Exception as e:
            logger.error(f"获取基金列表失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/fund/<fund_code>', methods=['GET'])
    def get_fund_detail(fund_code):
        """获取单个基金详情（实时数据）"""
        try:
            # 优先从实时数据获取
            try:
                fund_data = fund_data_manager.get_realtime_data(fund_code)
                if fund_data:
                    # 获取真实的基金名称
                    real_fund_name = fund_code  # 默认使用基金代码
                    try:
                        import akshare as ak
                        fund_list = ak.fund_name_em()
                        fund_info = fund_list[fund_list['基金代码'] == fund_code]
                        if not fund_info.empty:
                            real_fund_name = fund_info.iloc[0]['基金简称']
                    except Exception as e:
                        logger.warning(f"获取基金 {fund_code} 真实名称失败: {e}")
                    
                    # 获取历史数据用于计算prev_day_return
                    hist_data = fund_data_manager.get_historical_data(fund_code, days=10)
                    if hist_data is not None and not hist_data.empty:
                        # 计算prev_day_return（向前追溯逻辑）
                        if len(hist_data) >= 2:
                            current_return = fund_data.get('today_return', 0)
                            prev_return = 0.0
                            
                            # 优先使用fund_data_manager的内置前向追溯方法
                            try:
                                return_result = fund_data_manager._get_yesterday_return(fund_code)
                                prev_return = return_result.get('value', 0.0) if isinstance(return_result, dict) else return_result
                                logger.debug(f"基金 {fund_code} 使用内置方法获取prev_day_return: {prev_return}%")
                            except Exception as e:
                                logger.warning(f"基金 {fund_code} 内置方法获取prev_day_return失败: {e}")
                                # 降级到手动前向追溯
                                # 从倒数第二天开始向前追溯
                            for i in range(len(hist_data) - 2, -1, -1):
                                data_row = hist_data.iloc[i]
                                return_raw = data_row.get('daily_growth_rate', None)
                                
                                if pd.notna(return_raw):
                                    return_value = float(return_raw)
                                    # 格式转换处理
                                    if abs(return_value) < 0.1:
                                        return_value = return_value * 100
                                    return_value = round(return_value, 2)
                                    
                                    # 如果找到非零值，使用该值
                                    if return_value != 0.0:
                                        prev_return = return_value
                                        break
                            
                            fund_data['prev_day_return'] = prev_return
                        
                        fund = {
                            'fund_code': fund_code,
                            'fund_name': real_fund_name,  # 使用真实的基金名称
                            'today_return': round(float(fund_data.get('today_return', 0)), 2),
                            'prev_day_return': round(float(fund_data.get('prev_day_return', 0)), 2),
                            'current_estimate': fund_data.get('current_nav'),
                            'yesterday_nav': fund_data.get('previous_nav'),
                            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
                            'data_source': fund_data.get('data_source', 'unknown')
                        }
                        
                        return safe_jsonify({'success': True, 'data': fund})
            except Exception as e:
                logger.warning(f"获取实时数据失败: {str(e)}, 使用缓存数据")
            
            # 如果实时数据获取失败，回退到数据库缓存数据
            sql = "SELECT * FROM fund_analysis_results WHERE fund_code = :fund_code ORDER BY analysis_date DESC LIMIT 1"
            df = db_manager.execute_query(sql, {'fund_code': fund_code})
            
            if df.empty:
                return jsonify({'success': False, 'error': '基金不存在'}), 404
            
            fund = df.iloc[0].to_dict()
            
            # 清理NaN值，将其转换为None（JSON兼容）
            for key in fund:
                if pd.isna(fund[key]):
                    fund[key] = None
            
            # today_return 和 prev_day_return 已经是百分比格式，不需要乘100
            for key in ['annualized_return', 'max_drawdown', 'volatility', 'win_rate']:
                if fund.get(key) is not None:
                    fund[key] = round(float(fund[key]) * 100, 2)
            # 单独处理已经是百分比格式的字段
            for key in ['today_return', 'prev_day_return']:
                if fund.get(key) is not None:
                    fund[key] = round(float(fund[key]), 2)
            for key in ['sharpe_ratio', 'calmar_ratio', 'sortino_ratio', 'var_95', 'profit_loss_ratio', 'composite_score']:
                if fund.get(key) is not None:
                    fund[key] = round(float(fund[key]), 4)
            
            return safe_jsonify({'success': True, 'data': fund})
            
        except Exception as e:
            logger.error(f"获取基金详情失败: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/fund/<fund_code>/history', methods=['GET'])
    def get_fund_history(fund_code):
        """获取基金历史绩效数据
        
        支持的时间维度:
        - days: 天数 (7, 30, 90, 180, 365)
        - period: 时间段 ('1m'=近一月, '3m'=近三月, '6m'=近半年, '1y'=近一年, 'ytd'=今年来)
        """
        try:
            # 支持两种参数方式
            period = request.args.get('period', '')
            days = request.args.get('days', 30, type=int)
            
            # 根据period计算days
            from datetime import datetime, timedelta
            today = datetime.now()
            
            if period == '1m':
                days = 30
            elif period == '3m':
                days = 90
            elif period == '6m':
                days = 180
            elif period == '1y':
                days = 365
            elif period == 'ytd':
                # 今年来：从1月1日到今天
                year_start = datetime(today.year, 1, 1)
                days = (today - year_start).days + 1
            elif period == 'all':
                # 成立以来：获取所有数据
                days = 9999
            
            # 尝试从AKShare获取实时净值数据
            try:
                hist_data = fund_data_manager.get_historical_data(fund_code, days=days)
                logger.info(f"原始获取到的历史数据形状: {hist_data.shape if hist_data is not None else 'None'}")
                
                if hist_data is not None and not hist_data.empty:
                    logger.info(f"原始数据列名: {list(hist_data.columns)}")
                    if 'nav' in hist_data.columns:
                        nan_count = hist_data['nav'].isna().sum()
                        logger.info(f"nav列NaN值数量: {nan_count}/{len(hist_data)}")
                        if nan_count > 0:
                            logger.info(f"包含NaN的行:\n{hist_data[hist_data['nav'].isna()]}")
                    
                    # 清理NaN值
                    hist_data = hist_data.dropna(subset=['nav'])
                    logger.info(f"清理NaN后数据形状: {hist_data.shape}")
                    
                    if not hist_data.empty:
                        # 确保date列是datetime类型
                        if not pd.api.types.is_datetime64_any_dtype(hist_data['date']):
                            hist_data['date'] = pd.to_datetime(hist_data['date'])
                        
                        # 转换日期格式
                        hist_data['date'] = hist_data['date'].dt.strftime('%Y-%m-%d')
                        # 确保nav是数值类型
                        hist_data['nav'] = hist_data['nav'].astype(float)
                        result_data = hist_data[['date', 'nav']].tail(days).to_dict('records')
                        logger.info(f"最终返回数据条数: {len(result_data)}")
                        
                        # 清理可能的NaN值
                        for item in result_data:
                            for key in item:
                                if pd.isna(item[key]):
                                    item[key] = None
                        return safe_jsonify({'success': True, 'data': result_data, 'source': 'akshare'})
                    else:
                        logger.warning("清理NaN值后数据为空")
                else:
                    logger.warning("获取到的历史数据为空")
            except Exception as e:
                logger.warning(f"从AKShare获取历史数据失败: {str(e)}, 尝试从数据库获取")
            
            # 备用方案：从数据库获取
            sql = f"""
            SELECT analysis_date as date, today_return, annualized_return, sharpe_ratio,
                   max_drawdown, volatility, composite_score, status_label, 
                   COALESCE(current_estimate, yesterday_nav) as nav
            FROM fund_analysis_results WHERE fund_code = '{fund_code}'
            ORDER BY analysis_date DESC LIMIT {days}
            """
            df = db_manager.execute_query(sql)
            
            if df.empty:
                return jsonify({'success': True, 'data': [], 'source': 'database'})
            
            df['date'] = df['date'].astype(str)
            
            # today_return 和 prev_day_return 已经是百分比格式，不需要乘100
            for key in ['annualized_return', 'max_drawdown', 'volatility']:
                if key in df.columns:
                    df[key] = df[key].apply(lambda x: round(float(x) * 100, 2) if pd.notna(x) else None)
            # 单独处理已经是百分比格式的字段
            for key in ['today_return']:
                if key in df.columns:
                    df[key] = df[key].apply(lambda x: round(float(x), 2) if pd.notna(x) else None)
            for key in ['sharpe_ratio', 'composite_score']:
                if key in df.columns:
                    df[key] = df[key].apply(lambda x: round(float(x), 4) if pd.notna(x) else None)
            
            # 清理所有剩余的NaN值
            df = df.where(pd.notna(df), None)
            
            return safe_jsonify({'success': True, 'data': df.to_dict('records'), 'source': 'database'})
            
        except Exception as e:
            logger.error(f"获取基金历史数据失败: {str(e)}")
            return safe_jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/fund/<fund_code>/holdings', methods=['GET'])
    def get_fund_holdings(fund_code):
        """获取基金持仓数据（股票持仓）"""
        try:
            logger.info(f"开始获取基金持仓数据 {fund_code}")
            
            # 尝试从akshare获取真实持仓数据
            try:
                import akshare as ak
                
                # 获取基金持仓数据 - 使用天天基金网接口
                holdings_df = ak.fund_portfolio_hold_em(symbol=fund_code, date="2024")
                
                if holdings_df is None or holdings_df.empty:
                    # 尝试获取2023年数据
                    holdings_df = ak.fund_portfolio_hold_em(symbol=fund_code, date="2023")
                
                if holdings_df is not None and not holdings_df.empty:
                    # 获取最新季度的数据
                    if '季度' in holdings_df.columns:
                        latest_quarter = holdings_df['季度'].iloc[0]
                        holdings_df = holdings_df[holdings_df['季度'] == latest_quarter]
                    
                    holdings = []
                    total_ratio = 0
                    
                    for _, row in holdings_df.head(10).iterrows():
                        stock_code = str(row.get('股票代码', ''))
                        stock_name = str(row.get('股票名称', ''))
                        ratio = row.get('占净值比例', 0)
                        ratio_change = row.get('较上期变化', None)
                        
                        # 清理数据
                        if pd.notna(ratio):
                            ratio = float(ratio)
                            total_ratio += ratio
                        else:
                            ratio = None
                        
                        if pd.notna(ratio_change):
                            ratio_change = float(ratio_change)
                        else:
                            ratio_change = None
                        
                        # 计算市值（基于基金规模估算）
                        market_value = None
                        if ratio:
                            # 从fund_analysis_results获取基金规模估算
                            try:
                                fund_size_sql = """
                                SELECT holding_amount FROM user_holdings 
                                WHERE fund_code = :fund_code LIMIT 1
                                """
                                fund_size_df = db_manager.execute_query(fund_size_sql, {'fund_code': fund_code})
                                if not fund_size_df.empty:
                                    fund_size = float(fund_size_df.iloc[0]['holding_amount']) / 10000  # 转换为万元
                                else:
                                    fund_size = 100000  # 默认10亿元
                            except:
                                fund_size = 100000  # 默认10亿元
                            
                            market_value = round((ratio / 100) * fund_size, 2)
                        
                        # 尝试获取股票实时涨跌幅
                        stock_return = None
                        try:
                            # 获取A股实时行情
                            if len(stock_code) == 6 and stock_code.isdigit():
                                stock_data = ak.stock_zh_a_spot_em()
                                if stock_data is not None and not stock_data.empty:
                                    stock_info = stock_data[stock_data['代码'] == stock_code]
                                    if not stock_info.empty:
                                        stock_return = stock_info.iloc[0].get('涨跌幅', None)
                                        if pd.notna(stock_return):
                                            stock_return = float(stock_return)
                        except Exception as e:
                            logger.warning(f"获取股票 {stock_code} 涨跌幅失败: {str(e)}")
                        
                        holdings.append({
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'ratio': round(ratio, 2) if ratio else None,
                            'market_value': market_value,
                            'stock_return': round(stock_return, 2) if stock_return else None,
                            'ratio_change': round(ratio_change, 2) if ratio_change else None,
                            'change_direction': 'up' if ratio_change and ratio_change > 0 else ('down' if ratio_change and ratio_change < 0 else 'new' if ratio_change is None else 'same')
                        })
                    
                    # 计算其他资产占比
                    other_ratio = max(0, 100 - total_ratio)
                    
                    # 获取更新日期
                    update_date = None
                    if '季度' in holdings_df.columns:
                        update_date = str(holdings_df['季度'].iloc[0])
                    
                    logger.info(f"获取基金持仓数据成功 {fund_code}, 持仓数量: {len(holdings)}")
                    
                    return safe_jsonify({
                        'success': True,
                        'data': {
                            'holdings': holdings,
                            'other_ratio': round(other_ratio, 2),
                            'total_ratio': round(total_ratio, 2),
                            'update_date': update_date,
                            'source': 'akshare'
                        }
                    })
            
            except Exception as e:
                logger.warning(f"从akshare获取基金持仓失败: {str(e)}")
            
            # 如果无法获取数据，返回空结果
            logger.warning(f"无法获取基金 {fund_code} 的持仓数据")
            return jsonify({
                'success': True,
                'data': {
                    'holdings': [],
                    'other_ratio': 100,
                    'total_ratio': 0,
                    'update_date': None,
                    'source': 'empty'
                }
            })
            
        except Exception as e:
            logger.error(f"获取基金持仓失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/fund/<fund_code>/stage-returns', methods=['GET'])
    def get_fund_stage_returns(fund_code):
        """获取基金阶段涨幅数据（与沪深300对比）"""
        try:
            from datetime import datetime, timedelta
            today = datetime.now()
            
            # 定义各阶段的天数
            stages = {
                'week': 7,
                'month': 30,
                'quarter': 90,
                'half_year': 180,
                'year': 365,
                'three_year': 1095
            }
            
            result = {}
            
            # 获取基金历史数据
            try:
                fund_hist = fund_data_manager.get_historical_data(fund_code, days=1100)
                if fund_hist is not None and not fund_hist.empty:
                    fund_hist = fund_hist.dropna(subset=['nav'])
                    fund_hist = fund_hist.sort_values('date')
                    
                    if not fund_hist.empty:
                        latest_nav = fund_hist.iloc[-1]['nav']
                        
                        for stage_name, days in stages.items():
                            target_date = today - timedelta(days=days)
                            # 找到最接近目标日期的数据
                            past_data = fund_hist[fund_hist['date'] <= target_date]
                            if not past_data.empty:
                                past_nav = past_data.iloc[-1]['nav']
                                if past_nav and past_nav != 0:
                                    stage_return = ((latest_nav - past_nav) / past_nav) * 100
                                    result[f'{stage_name}_return'] = round(stage_return, 2)
                                else:
                                    result[f'{stage_name}_return'] = None
                            else:
                                result[f'{stage_name}_return'] = None
            except Exception as e:
                logger.warning(f"获取基金阶段涨幅失败: {str(e)}")
            
            # 获取沪深300数据作为对比
            try:
                import akshare as ak
                hs300_hist = ak.index_zh_a_hist(symbol="000300", period="daily", 
                                               start_date=(today - timedelta(days=1100)).strftime('%Y%m%d'),
                                               end_date=today.strftime('%Y%m%d'))
                if hs300_hist is not None and not hs300_hist.empty:
                    hs300_hist['date'] = pd.to_datetime(hs300_hist['日期'])
                    hs300_hist = hs300_hist.sort_values('date')
                    latest_close = hs300_hist.iloc[-1]['收盘']
                    
                    for stage_name, days in stages.items():
                        target_date = today - timedelta(days=days)
                        past_data = hs300_hist[hs300_hist['date'] <= target_date]
                        if not past_data.empty:
                            past_close = past_data.iloc[-1]['收盘']
                            if past_close and past_close != 0:
                                stage_return = ((latest_close - past_close) / past_close) * 100
                                result[f'hs300_{stage_name}_return'] = round(stage_return, 2)
                            else:
                                result[f'hs300_{stage_name}_return'] = None
                        else:
                            result[f'hs300_{stage_name}_return'] = None
            except Exception as e:
                logger.warning(f"获取沪深300阶段涨幅失败: {str(e)}")
            
            return safe_jsonify({'success': True, 'data': result})
            
        except Exception as e:
            logger.error(f"获取阶段涨幅失败: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/fund/<fund_code>/info', methods=['GET'])
    def get_fund_info(fund_code):
        """获取基金基本信息（包括成立日期等）"""
        try:
            import akshare as ak
            
            # 使用 akshare 获取基金基本信息
            try:
                # fund_individual_basic_info_xq: 雪球-基金-基本信息
                fund_info = ak.fund_individual_basic_info_xq(symbol=fund_code)
                
                if fund_info is not None and not fund_info.empty:
                    info_dict = {}
                    for _, row in fund_info.iterrows():
                        item = row.get('item', '')
                        value = row.get('value', '')
                        # 处理NaN值和NAType
                        if pd.isna(value):
                            value = None
                        else:
                            value = str(value).strip()
                        info_dict[item] = value
                    
                    # 提取成立日期
                    inception_date = info_dict.get('成立日期', None)
                    fund_manager = info_dict.get('基金经理', None)
                    fund_company = info_dict.get('基金公司', None)
                    fund_type = info_dict.get('基金类型', None)
                    
                    return jsonify({
                        'success': True,
                        'data': {
                            'inception_date': inception_date,
                            'fund_manager': fund_manager,
                            'fund_company': fund_company,
                            'fund_type': fund_type,
                            'raw_info': info_dict
                        }
                    })
            except Exception as e:
                logger.warning(f"从雪球获取基金信息失败: {str(e)}, 尝试其他数据源")
            
            # 备用方案：从天天基金网获取
            try:
                # 使用正确的方法名：fund_open_fund_info_em
                fund_info_em = ak.fund_open_fund_info_em(symbol=fund_code, indicator="基本信息")
                if fund_info_em is not None and not fund_info_em.empty:
                    info_dict = {}
                    for _, row in fund_info_em.iterrows():
                        item = row.get('项目', '')
                        value = row.get('数值', '')
                        # 处理NaN值
                        if pd.isna(value):
                            value = None
                        else:
                            value = str(value).strip()
                        info_dict[item] = value
                    
                    inception_date = info_dict.get('成立日期', None)
                    
                    return jsonify({
                        'success': True,
                        'data': {
                            'inception_date': inception_date,
                            'raw_info': info_dict
                        }
                    })
            except Exception as e:
                logger.warning(f"从天天基金网获取基金信息失败: {str(e)}")
            
            return jsonify({'success': False, 'error': '无法获取基金信息'})
            
        except Exception as e:
            logger.error(f"获取基金信息失败: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/fund/search', methods=['GET'])
    def search_funds():
        """搜索基金（支持代码和名称搜索）"""
        try:
            keyword = request.args.get('keyword', '').strip()
            
            if not keyword:
                return jsonify({'success': False, 'error': '请输入搜索关键词'}), 400
            
            # 尝试从AKShare搜索基金
            try:
                import akshare as ak
                
                # 使用基金搜索功能
                search_result = ak.fund_name_em()
                
                if search_result is not None and not search_result.empty:
                    # 确定基金名称列名
                    fund_name_col = '基金名称'
                    if '基金名称' not in search_result.columns:
                        fund_name_col = '基金简称' if '基金简称' in search_result.columns else None
                    
                    if fund_name_col:
                        # 过滤搜索结果
                        filtered = search_result[
                            (search_result['基金代码'].astype(str).str.contains(keyword)) |
                            (search_result[fund_name_col].str.contains(keyword))
                        ]
                    else:
                        # 如果没有找到基金名称列，只按代码搜索
                        filtered = search_result[
                            search_result['基金代码'].astype(str).str.contains(keyword)
                        ]
                    
                    if not filtered.empty:
                        # 限制结果数量
                        filtered = filtered.head(10)
                        
                        funds = []
                        for _, row in filtered.iterrows():
                            fund_code = str(row['基金代码'])
                            # 使用检测到的列名获取基金名称
                            fund_name = str(row[fund_name_col]) if fund_name_col else str(row.get('基金简称', fund_code))
                            
                            # 尝试获取基金类型和净值
                            fund_type = None
                            nav_value = None
                            nav_date = None
                            daily_change = None
                            
                            try:
                                # 获取基金基本信息
                                fund_info = ak.fund_open_fund_info_em(symbol=fund_code, indicator="基本信息")
                                if fund_info is not None and not fund_info.empty:
                                    for _, info_row in fund_info.iterrows():
                                        if info_row.get('项目') == '基金类型':
                                            fund_type = str(info_row.get('数值', '')).strip()
                                            break
                                
                                # 获取基金净值
                                fund_nav = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值")
                                if fund_nav is not None and not fund_nav.empty:
                                    latest_nav = fund_nav.iloc[0]
                                    nav_value = float(latest_nav.get('数值', 0)) if pd.notna(latest_nav.get('数值')) else None
                                    nav_date = str(latest_nav.get('日期', '')) if pd.notna(latest_nav.get('日期')) else None
                                    
                                    # 计算日涨跌幅
                                    if len(fund_nav) > 1:
                                        prev_nav = fund_nav.iloc[1]
                                        if pd.notna(prev_nav.get('数值')) and nav_value:
                                            prev_nav_value = float(prev_nav.get('数值'))
                                            if prev_nav_value > 0:
                                                daily_change = round(((nav_value - prev_nav_value) / prev_nav_value) * 100, 2)
                            except Exception as e:
                                logger.warning(f"获取基金 {fund_code} 详细信息失败: {str(e)}")
                            
                            funds.append({
                                'fund_code': fund_code,
                                'fund_name': fund_name,
                                'fund_type': fund_type,
                                'nav_value': nav_value,
                                'nav_date': nav_date,
                                'daily_change': daily_change
                            })
                        
                        return jsonify({'success': True, 'data': funds})
            except Exception as e:
                logger.error(f"从AKShare搜索基金失败: {str(e)}")
            
            # 备用方案：从数据库搜索
            try:
                # 检查数据库管理器是否可用
                if not hasattr(db_manager, 'execute_query'):
                    raise Exception("数据库管理器不可用")
                
                # 使用参数化查询避免SQL注入和格式问题
                sql = """
                SELECT fund_code, fund_name, fund_type
                FROM fund_basic_info
                WHERE fund_code LIKE :keyword OR fund_name LIKE :keyword
                LIMIT 10
                """
                
                df = db_manager.execute_query(sql, {'keyword': f'%{keyword}%'})
                
                if not df.empty:
                    funds = []
                    for _, row in df.iterrows():
                        funds.append({
                            'fund_code': str(row['fund_code']),
                            'fund_name': str(row['fund_name']),
                            'fund_type': str(row['fund_type']) if pd.notna(row['fund_type']) else None
                        })
                    
                    return jsonify({'success': True, 'data': funds})
            except Exception as e:
                error_msg = str(e)
                # 检查是否是表不存在错误
                if "Table" in error_msg and "doesn't exist" in error_msg:
                    logger.warning(f"数据库表不存在，跳过数据库搜索: {error_msg}")
                else:
                    logger.error(f"从数据库搜索基金失败: {error_msg}")
            
            # 如果都失败，返回空结果
            return jsonify({'success': True, 'data': []})
            
        except Exception as e:
            logger.error(f"搜索基金失败: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/fund/<fund_code>/allocation', methods=['GET'])
    def get_fund_allocation(fund_code):
        """获取基金资产配置数据"""
        try:
            import akshare as ak
            
            asset_allocation = {}
            industry_allocation = {}
            bond_allocation = {}
            latest_quarter = None
            has_real_data = False
            
            # 1. 获取资产配置数据
            try:
                allocation_data = ak.fund_portfolio_asset_em(symbol=fund_code)
                
                if allocation_data is not None and not allocation_data.empty:
                    # 按季度分组，取最新季度
                    if '季度' in allocation_data.columns:
                        latest_quarter = allocation_data['季度'].iloc[0]
                        latest_data = allocation_data[allocation_data['季度'] == latest_quarter]
                    else:
                        latest_data = allocation_data
                    
                    # 提取资产配置
                    for _, row in latest_data.iterrows():
                        asset_type = row.get('资产类型', '')
                        ratio = row.get('占净值比例', 0)
                        
                        if pd.notna(ratio) and asset_type:
                            ratio = float(ratio)
                            asset_allocation[asset_type] = ratio
                            has_real_data = True
            except Exception as e:
                logger.warning(f"获取资产配置数据失败: {str(e)}")
            
            # 2. 获取行业分布数据
            try:
                industry_data = ak.fund_portfolio_industry_allocation_em(symbol=fund_code)
                if industry_data is not None and not industry_data.empty:
                    # 获取最新季度数据
                    if '季度' in industry_data.columns:
                        latest_q = industry_data['季度'].iloc[0]
                        industry_data = industry_data[industry_data['季度'] == latest_q]
                    
                    for _, row in industry_data.iterrows():
                        industry_name = row.get('行业名称', '')
                        ratio = row.get('占净值比例', 0)
                        if pd.notna(ratio) and industry_name:
                            industry_allocation[industry_name] = float(ratio)
                            has_real_data = True
            except Exception as e:
                logger.warning(f"获取行业分布数据失败: {str(e)}")
            
            # 3. 如果是债券基金，尝试获取债券类型数据
            try:
                # 获取基金基本信息判断是否为债券基金
                fund_info = ak.fund_individual_basic_info_xq(symbol=fund_code)
                is_bond_fund = False
                if fund_info is not None and not fund_info.empty:
                    for _, row in fund_info.iterrows():
                        if '债券' in str(row.get('value', '')) or 'bond' in str(row.get('value', '')).lower():
                            is_bond_fund = True
                            break
                
                if is_bond_fund:
                    # 尝试获取债券类型配置（从资产配置中推断或从其他接口获取）
                    bond_detail = ak.fund_portfolio_bond_hold_em(symbol=fund_code, date="2024")
                    if bond_detail is not None and not bond_detail.empty:
                        # 这里可以进一步处理债券详情数据
                        pass
            except Exception as e:
                logger.warning(f"获取债券类型数据失败: {str(e)}")
            
            # 如果没有获取到任何真实数据，返回空结果
            if not has_real_data:
                return jsonify({
                    'success': True,
                    'data': {
                        'asset_allocation': {},
                        'industry_allocation': {},
                        'bond_allocation': {},
                        'update_date': None,
                        'source': 'empty'
                    }
                })
            
            return jsonify({
                'success': True,
                'data': {
                    'asset_allocation': asset_allocation,
                    'industry_allocation': industry_allocation,
                    'bond_allocation': bond_allocation,
                    'update_date': latest_quarter,
                    'source': 'akshare'
                }
            })
            
        except Exception as e:
            logger.error(f"获取基金资产配置失败: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/fund/<fund_code>/latest', methods=['GET'])
    def get_fund_latest(fund_code):
        """获取基金最新实时数据（简化版，用于实时更新）"""
        try:
            # 优先从实时数据获取
            try:
                fund_data = fund_data_manager.get_realtime_data(fund_code)
                if fund_data:
                    # 获取真实的基金名称
                    real_fund_name = fund_code
                    try:
                        import akshare as ak
                        fund_list = ak.fund_name_em()
                        fund_info = fund_list[fund_list['基金代码'] == fund_code]
                        if not fund_info.empty:
                            real_fund_name = fund_info.iloc[0]['基金简称']
                    except Exception as e:
                        logger.warning(f"获取基金 {fund_code} 真实名称失败: {e}")
                    
                    # 获取前一日涨跌幅
                    prev_return = 0.0
                    try:
                        return_result = fund_data_manager._get_yesterday_return(fund_code)
                        prev_return = return_result.get('value', 0.0) if isinstance(return_result, dict) else return_result
                    except Exception as e:
                        logger.debug(f"获取基金 {fund_code} prev_day_return 失败: {e}")
                    
                    result = {
                        'fund_code': fund_code,
                        'fund_name': real_fund_name,
                        'today_return': round(float(fund_data.get('today_return', 0)), 2),
                        'prev_day_return': round(float(prev_return), 2),
                        'current_nav': fund_data.get('current_nav'),
                        'previous_nav': fund_data.get('previous_nav'),
                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'data_source': fund_data.get('data_source', 'unknown')
                    }
                    return safe_jsonify({'success': True, 'data': result})
            except Exception as e:
                logger.warning(f"获取实时数据失败: {str(e)}, 使用缓存数据")
            
            # 如果实时数据获取失败，回退到数据库缓存数据
            sql = "SELECT * FROM fund_analysis_results WHERE fund_code = :fund_code ORDER BY analysis_date DESC LIMIT 1"
            df = db_manager.execute_query(sql, {'fund_code': fund_code})
            
            if df.empty:
                return jsonify({'success': False, 'error': '基金不存在'}), 404
            
            fund = df.iloc[0].to_dict()
            
            # 清理NaN值
            for key in fund:
                if pd.isna(fund[key]):
                    fund[key] = None
            
            result = {
                'fund_code': fund_code,
                'fund_name': fund.get('fund_name', fund_code),
                'today_return': round(float(fund.get('today_return', 0)), 2) if fund.get('today_return') is not None else 0,
                'prev_day_return': round(float(fund.get('prev_day_return', 0)), 2) if fund.get('prev_day_return') is not None else 0,
                'current_nav': fund.get('current_estimate'),
                'previous_nav': fund.get('yesterday_nav'),
                'update_time': fund.get('analysis_date'),
                'data_source': 'database'
            }
            
            return safe_jsonify({'success': True, 'data': result})
            
        except Exception as e:
            logger.error(f"获取基金最新数据失败: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/funds/realtime-estimates', methods=['POST'])
    def get_funds_realtime_estimates():
        """批量获取基金实时估值
        
        请求体: {"fund_codes": ["000001", "110022", ...]}
        返回: {"success": true, "data": {"000001": {"estimate_nav": 1.2345, ...}, ...}}
        """
        try:
            data = request.get_json()
            if not data or 'fund_codes' not in data:
                return jsonify({'success': False, 'error': '请提供基金代码列表'}), 400
            
            fund_codes = data['fund_codes']
            if not isinstance(fund_codes, list) or len(fund_codes) == 0:
                return jsonify({'success': False, 'error': '基金代码列表无效'}), 400
            
            # 限制一次请求的基金数量
            if len(fund_codes) > 100:
                fund_codes = fund_codes[:100]
            
            logger.info(f"批量获取 {len(fund_codes)} 只基金的实时估值")
            
            results = {}
            for fund_code in fund_codes:
                try:
                    # 获取实时数据
                    realtime_data = fund_data_manager.get_realtime_data(fund_code, '')
                    
                    # 提取估值相关字段
                    estimate_nav = realtime_data.get('estimate_nav') or realtime_data.get('current_nav')
                    previous_nav = realtime_data.get('previous_nav')
                    today_return = realtime_data.get('today_return')
                    
                    # 如果 today_return 为空或0，用净值差计算
                    if (not today_return or today_return == 0) and estimate_nav and previous_nav:
                        try:
                            e = float(estimate_nav)
                            p = float(previous_nav)
                            if p > 0 and e > 0:
                                today_return = round((e - p) / p * 100, 2)
                        except (TypeError, ValueError, ZeroDivisionError):
                            pass
                    
                    results[fund_code] = {
                        'fund_code': fund_code,
                        'estimate_nav': estimate_nav,
                        'current_nav': realtime_data.get('current_nav'),
                        'previous_nav': previous_nav,
                        'today_return': today_return,
                        'estimate_return': realtime_data.get('estimate_return'),
                        'data_source': realtime_data.get('data_source'),
                        'update_time': realtime_data.get('nav_date') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                except Exception as e:
                    logger.warning(f"获取基金 {fund_code} 实时估值失败: {str(e)}")
                    results[fund_code] = {
                        'fund_code': fund_code,
                        'estimate_nav': None,
                        'error': str(e)
                    }
            
            return safe_jsonify({'success': True, 'data': results})
            
        except Exception as e:
            logger.error(f"批量获取实时估值失败: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500


def get_fund_holdings_original(fund_code):
    """获取基金持仓数据（股票持仓）"""
    try:
        try:
            holdings_df = ak.fund_portfolio_hold_em(symbol=fund_code, date="2024")
            
            if holdings_df is None or holdings_df.empty:
                # 尝试获取2023年数据
                holdings_df = ak.fund_portfolio_hold_em(symbol=fund_code, date="2023")
            
            if holdings_df is not None and not holdings_df.empty:
                # 只取最新一期的前10大持仓
                # 按季度分组，取最新季度
                if '季度' in holdings_df.columns:
                    latest_quarter = holdings_df['季度'].iloc[0]
                    holdings_df = holdings_df[holdings_df['季度'] == latest_quarter]
                
                holdings = []
                total_ratio = 0
                
                for _, row in holdings_df.head(10).iterrows():
                    stock_code = str(row.get('股票代码', ''))
                    stock_name = str(row.get('股票名称', ''))
                    ratio = row.get('占净值比例', 0)
                    ratio_change = row.get('较上期变化', None)
                    
                    # 清理数据
                    if pd.notna(ratio):
                        ratio = float(ratio)
                        total_ratio += ratio
                    else:
                        ratio = None
                    
                    if pd.notna(ratio_change):
                        ratio_change = float(ratio_change)
                    else:
                        ratio_change = None
                    
                    # 计算市值（模拟数据，实际需要基金规模）
                    market_value = None
                    if ratio:
                        # 假设基金规模为10亿
                        fund_size = 100000  # 万元
                        market_value = round((ratio / 100) * fund_size, 2)
                    
                    # 尝试获取股票涨跌幅
                    stock_return = None
                    try:
                        import akshare as ak
                        # 获取股票实时数据
                        stock_data = ak.stock_zh_a_spot_em()
                        if stock_data is not None and not stock_data.empty:
                            stock_info = stock_data[stock_data['代码'] == stock_code]
                            if not stock_info.empty:
                                stock_return = stock_info.iloc[0].get('涨跌幅', None)
                                if pd.notna(stock_return):
                                    stock_return = float(stock_return)
                    except Exception as e:
                        logger.warning(f"获取股票 {stock_code} 涨跌幅失败: {str(e)}")
                    
                    holdings.append({
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'ratio': round(ratio, 2) if ratio else None,
                        'market_value': market_value,
                        'stock_return': round(stock_return, 2) if stock_return else None,
                        'ratio_change': round(ratio_change, 2) if ratio_change else None,
                        'change_direction': 'up' if ratio_change and ratio_change > 0 else ('down' if ratio_change and ratio_change < 0 else 'new' if ratio_change is None else 'same')
                    })
                
                # 获取更新日期
                update_date = None
                if '季度' in holdings_df.columns:
                    update_date = str(holdings_df['季度'].iloc[0])
                
                return jsonify({
                    'success': True, 
                    'data': {
                        'holdings': holdings,
                        'total_ratio': round(total_ratio, 2),
                        'update_date': update_date
                    }
                })
        except Exception as e:
            logger.warning(f"从akshare获取基金持仓失败: {str(e)}")
        
        return jsonify({'success': True, 'data': {'holdings': [], 'total_ratio': 0, 'update_date': None}})
        
    except Exception as e:
        logger.error(f"获取基金持仓失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
