#!/usr/bin/env python
# coding: utf-8

"""
基金列表 API 路由
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
from flask import jsonify, request

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.json_utils import safe_jsonify
from services.db_optimizer import profit_calculator

logger = logging.getLogger(__name__)

db_manager = None
fund_data_manager = None


def init_components(**kwargs):
    """初始化组件"""
    global db_manager, fund_data_manager
    db_manager = kwargs.get('db_manager')
    fund_data_manager = kwargs.get('fund_data_manager')


def register_funds_list_routes(app, **kwargs):
    """注册基金列表路由"""
    init_components(**kwargs)
    
    @app.route('/api/funds', methods=['GET'])
    def get_funds():
        """获取基金列表（包含持仓盈亏数据）"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            search = request.args.get('search', '').strip()
            sort_by = request.args.get('sort_by', 'composite_score')
            sort_order = request.args.get('sort_order', 'desc')
            
            logger.info(f"搜索参数: search={search}, sort_by={sort_by}, page={page}")
            
            date_sql = "SELECT MAX(analysis_date) as max_date FROM fund_analysis_results"
            date_df = db_manager.execute_query(date_sql)
            
            if date_df.empty or date_df.iloc[0]['max_date'] is None:
                return safe_jsonify({
                    'success': True, 
                    'data': [], 
                    'total': 0, 
                    'page': page, 
                    'per_page': per_page
                })
            
            max_date = date_df.iloc[0]['max_date']
            
            sql = """
            SELECT DISTINCT 
                far.fund_code, far.fund_name, far.today_return, far.prev_day_return,
                far.annualized_return, far.sharpe_ratio, far.sharpe_ratio_ytd, 
                far.sharpe_ratio_1y, far.sharpe_ratio_all,
                far.max_drawdown, far.volatility,
                far.composite_score, far.status_label, far.operation_suggestion, 
                far.analysis_date,
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
            
            valid_sort_fields = [
                'composite_score', 'today_return', 'prev_day_return', 
                'annualized_return', 'sharpe_ratio', 'max_drawdown', 'fund_code'
            ]
            
            if sort_by in valid_sort_fields:
                sort_direction = 'DESC' if sort_order == 'desc' else 'ASC'
                sql += f" ORDER BY far.{sort_by} {sort_direction}"
            
            df = db_manager.execute_query(sql, params)
            
            if df.empty:
                return safe_jsonify({
                    'success': True, 
                    'data': [], 
                    'total': 0, 
                    'page': page, 
                    'per_page': per_page
                })
            
            df = profit_calculator.clean_nan_values(df)
            df = profit_calculator.format_performance_metrics(df)
            
            profit_result = profit_calculator.calculate_profits(df)
            
            df['holding_amount'] = profit_result.holding_amount
            df['today_profit'] = profit_result.today_profit
            df['today_profit_rate'] = profit_result.today_profit_rate
            df['holding_profit'] = profit_result.holding_profit
            df['holding_profit_rate'] = profit_result.holding_profit_rate
            df['total_profit'] = profit_result.total_profit
            df['total_profit_rate'] = profit_result.total_profit_rate
            
            funds_list = df.to_dict('records')
            
            for fund in funds_list:
                for key in fund:
                    if pd.isna(fund[key]) or (isinstance(fund[key], float) and np.isinf(fund[key])):
                        fund[key] = None
            
            if sort_by in ['today_profit_rate', 'holding_profit_rate', 'holding_amount']:
                funds_list.sort(
                    key=lambda x: x.get(sort_by) if x.get(sort_by) is not None else float('-inf'),
                    reverse=(sort_order == 'desc')
                )
            
            total = len(funds_list)
            start = (page - 1) * per_page
            funds_page = funds_list[start:start + per_page]
            
            return safe_jsonify({
                'success': True, 
                'data': funds_page, 
                'total': total, 
                'page': page, 
                'per_page': per_page
            })
            
        except Exception as e:
            logger.error(f"获取基金列表失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    logger.info("基金列表路由已注册")
