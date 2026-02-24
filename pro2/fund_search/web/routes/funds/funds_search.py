#!/usr/bin/env python
# coding: utf-8

"""
基金搜索 API 路由
"""

import os
import sys
import logging
import pandas as pd
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


def register_funds_search_routes(app, **kwargs):
    """注册基金搜索路由"""
    init_components(**kwargs)
    
    @app.route('/api/funds/search', methods=['GET'])
    def search_funds():
        """搜索基金
        
        支持按代码或名称搜索
        """
        try:
            keyword = request.args.get('keyword', '').strip()
            limit = request.args.get('limit', 10, type=int)
            
            if not keyword:
                return safe_jsonify({
                    'success': True, 
                    'data': []
                })
            
            sql = """
            SELECT DISTINCT fund_code, fund_name 
            FROM fund_analysis_results 
            WHERE fund_code LIKE :keyword OR fund_name LIKE :keyword
            LIMIT :limit
            """
            
            df = db_manager.execute_query(sql, {
                'keyword': f'%{keyword}%',
                'limit': limit
            })
            
            if df.empty:
                return safe_jsonify({
                    'success': True, 
                    'data': []
                })
            
            results = df.to_dict('records')
            
            return safe_jsonify({
                'success': True, 
                'data': results
            })
            
        except Exception as e:
            logger.error(f"搜索基金失败: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/funds/suggest', methods=['GET'])
    def suggest_funds():
        """基金智能推荐
        
        根据综合评分推荐基金
        """
        try:
            top_n = request.args.get('top_n', 10, type=int)
            min_score = request.args.get('min_score', 0.6, type=float)
            
            date_sql = "SELECT MAX(analysis_date) as max_date FROM fund_analysis_results"
            date_df = db_manager.execute_query(date_sql)
            
            if date_df.empty or date_df.iloc[0]['max_date'] is None:
                return safe_jsonify({
                    'success': True, 
                    'data': []
                })
            
            max_date = date_df.iloc[0]['max_date']
            
            sql = """
            SELECT fund_code, fund_name, composite_score, 
                   today_return, sharpe_ratio, max_drawdown
            FROM fund_analysis_results 
            WHERE analysis_date = :max_date 
              AND composite_score >= :min_score
            ORDER BY composite_score DESC
            LIMIT :top_n
            """
            
            df = db_manager.execute_query(sql, {
                'max_date': max_date,
                'min_score': min_score,
                'top_n': top_n
            })
            
            if df.empty:
                return safe_jsonify({
                    'success': True, 
                    'data': []
                })
            
            results = df.to_dict('records')
            
            for item in results:
                for key in item:
                    if pd.isna(item[key]):
                        item[key] = None
            
            return safe_jsonify({
                'success': True, 
                'data': results
            })
            
        except Exception as e:
            logger.error(f"推荐基金失败: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    logger.info("基金搜索路由已注册")
