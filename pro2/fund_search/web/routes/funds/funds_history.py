#!/usr/bin/env python
# coding: utf-8

"""
基金历史数据 API 路由
"""

import os
import sys
import logging
import pandas as pd
from datetime import datetime, timedelta
from flask import jsonify, request

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.json_utils import safe_jsonify

logger = logging.getLogger(__name__)

db_manager = None
fund_data_manager = None


def init_components(**kwargs):
    """初始化组件"""
    global db_manager, fund_data_manager
    db_manager = kwargs.get('db_manager')
    fund_data_manager = kwargs.get('fund_data_manager')


def register_funds_history_routes(app, **kwargs):
    """注册基金历史数据路由"""
    init_components(**kwargs)
    
    @app.route('/api/fund/<fund_code>/history', methods=['GET'])
    def get_fund_history(fund_code):
        """获取基金历史绩效数据
        
        支持的时间维度:
        - days: 天数 (7, 30, 90, 180, 365)
        - period: 时间段 ('1m'=近一月, '3m'=近三月, '6m'=近半年, '1y'=近一年, 'ytd'=今年来)
        """
        try:
            period = request.args.get('period', '')
            days = request.args.get('days', 30, type=int)
            
            today = datetime.now()
            
            period_mapping = {
                '1m': 30,
                '3m': 90,
                '6m': 180,
                '1y': 365,
                'all': 9999
            }
            
            if period in period_mapping:
                days = period_mapping[period]
            elif period == 'ytd':
                year_start = datetime(today.year, 1, 1)
                days = (today - year_start).days + 1
            
            try:
                hist_data = fund_data_manager.get_historical_data(fund_code, days=days)
                logger.info(f"原始获取到的历史数据形状: {hist_data.shape if hist_data is not None else 'None'}")
                
                if hist_data is not None and not hist_data.empty:
                    logger.info(f"原始数据列名: {list(hist_data.columns)}")
                    
                    hist_data = hist_data.dropna(subset=['nav'])
                    logger.info(f"清理NaN后数据形状: {hist_data.shape}")
                    
                    if not hist_data.empty:
                        if not pd.api.types.is_datetime64_any_dtype(hist_data['date']):
                            hist_data['date'] = pd.to_datetime(hist_data['date'])
                        
                        hist_data['date'] = hist_data['date'].dt.strftime('%Y-%m-%d')
                        hist_data['nav'] = hist_data['nav'].astype(float)
                        result_data = hist_data[['date', 'nav']].tail(days).to_dict('records')
                        logger.info(f"最终返回数据条数: {len(result_data)}")
                        
                        for item in result_data:
                            for key in item:
                                if pd.isna(item[key]):
                                    item[key] = None
                        
                        return safe_jsonify({
                            'success': True, 
                            'data': result_data, 
                            'source': 'akshare'
                        })
                    else:
                        logger.warning("清理NaN值后数据为空")
                else:
                    logger.warning("获取到的历史数据为空")
            except Exception as e:
                logger.warning(f"从AKShare获取历史数据失败: {str(e)}, 尝试从数据库获取")
            
            sql = """
            SELECT nav_date as date, current_nav as nav 
            FROM fund_performance 
            WHERE fund_code = :fund_code 
            ORDER BY nav_date DESC 
            LIMIT :days
            """
            df = db_manager.execute_query(sql, {'fund_code': fund_code, 'days': days})
            
            if df.empty:
                return jsonify({
                    'success': False, 
                    'error': '未找到历史数据'
                }), 404
            
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            result_data = df.to_dict('records')
            
            return safe_jsonify({
                'success': True, 
                'data': result_data, 
                'source': 'database'
            })
            
        except Exception as e:
            logger.error(f"获取基金历史数据失败: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    logger.info("基金历史数据路由已注册")
