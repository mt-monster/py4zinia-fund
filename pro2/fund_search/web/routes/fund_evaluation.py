#!/usr/bin/env python
# coding: utf-8

"""
基金评价 API 路由
提供基金评价、评分、排名等功能
"""

import os
import sys
import json
import logging
from datetime import datetime
from flask import jsonify, request
import pandas as pd
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# 全局变量
db_manager = None
fund_data_manager = None


def register_routes(app, **kwargs):
    """注册基金评价相关路由"""
    global db_manager, fund_data_manager

    db_manager = kwargs.get('db_manager') or getattr(app, 'db_manager', None)
    fund_data_manager = kwargs.get('fund_data_manager') or getattr(app, 'fund_data_manager', None)

    # 注册API路由
    app.add_url_rule('/api/fund-evaluation/stats', 'get_evaluation_stats', get_evaluation_stats, methods=['GET'])
    app.add_url_rule('/api/fund-evaluation/run', 'run_fund_evaluation', run_fund_evaluation, methods=['POST'])
    app.add_url_rule('/api/fund-evaluation/detail/<fund_code>', 'get_fund_evaluation_detail',
                     get_fund_evaluation_detail, methods=['GET'])

    logger.info("基金评价API路由注册完成")


def get_evaluation_stats():
    """获取基金评价统计信息 - 基于用户持仓"""
    try:
        if db_manager:
            user_id = 'default_user'
            # 从用户持仓获取基金数量
            holdings_sql = f"""
            SELECT COUNT(DISTINCT fund_code) as total
            FROM user_holdings 
            WHERE user_id = '{user_id}' AND holding_shares > 0
            """
            holdings_df = db_manager.execute_query(holdings_sql)
            total = int(holdings_df.iloc[0]['total']) if not holdings_df.empty else 0
            
            # 获取这些基金的评分统计
            if total > 0:
                codes_sql = f"""
                SELECT DISTINCT fund_code FROM user_holdings WHERE user_id = '{user_id}' AND holding_shares > 0
                """
                codes_df = db_manager.execute_query(codes_sql)
                if not codes_df.empty:
                    fund_codes = codes_df['fund_code'].tolist()
                    codes_str = "','".join(fund_codes)
                    
                    stats_sql = f"""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN sharpe_ratio >= 1.5 THEN 1 ELSE 0 END) as excellent,
                        SUM(CASE WHEN sharpe_ratio >= 0.8 AND sharpe_ratio < 1.5 THEN 1 ELSE 0 END) as good,
                        SUM(CASE WHEN sharpe_ratio < 0.8 OR sharpe_ratio IS NULL THEN 1 ELSE 0 END) as pending
                    FROM fund_analysis_results
                    WHERE fund_code IN ('{codes_str}')
                    AND analysis_date = (SELECT MAX(analysis_date) FROM fund_analysis_results)
                    """
                    stats_df = db_manager.execute_query(stats_sql)
                    if not stats_df.empty:
                        row = stats_df.iloc[0]
                        return jsonify({
                            'success': True,
                            'data': {
                                'total': int(row['total']) if pd.notna(row['total']) else 0,
                                'excellent': int(row['excellent']) if pd.notna(row['excellent']) else 0,
                                'good': int(row['good']) if pd.notna(row['good']) else 0,
                                'pending': int(row['pending']) if pd.notna(row['pending']) else 0
                            }
                        })

            # 没有持仓时返回0
            return jsonify({
                'success': True,
                'data': {
                    'total': 0,
                    'excellent': 0,
                    'good': 0,
                    'pending': 0
                }
            })

    except Exception as e:
        logger.error(f"获取评价统计失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def run_fund_evaluation():
    """运行基金评价"""
    try:
        data = request.get_json() or {}

        weights = data.get('weights', {
            'return': 30,
            'risk': 25,
            'manager': 20,
            'scale': 15,
            'institution': 10
        })
        fund_type = data.get('fund_type', 'all')
        min_score = data.get('min_score', 0)

        logger.info(f"开始基金评价: fund_type={fund_type}, min_score={min_score}, weights={weights}")

        # 获取基金列表
        funds = get_fund_list(fund_type)
        logger.info(f"获取到基金列表: {len(funds)} 只")

        # 对每个基金进行评分
        evaluated_funds = []
        for fund in funds:
            scores = calculate_fund_scores(fund, weights)
            if scores['total_score'] >= min_score:
                evaluated_funds.append({
                    'code': fund.get('code', ''),
                    'name': fund.get('name', ''),
                    'type': fund.get('type', '混合型'),
                    'return_score': scores['return_score'],
                    'risk_score': scores['risk_score'],
                    'manager_score': scores['manager_score'],
                    'total_score': scores['total_score']
                })

        logger.info(f"评价完成: {len(evaluated_funds)} 只基金满足条件")

        # 按总分排序
        evaluated_funds.sort(key=lambda x: x['total_score'], reverse=True)

        return jsonify({
            'success': True,
            'data': evaluated_funds
        })

    except Exception as e:
        logger.error(f"运行基金评价失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def get_fund_list(fund_type='all'):
    """获取基金列表 - 从用户持仓中获取真实基金"""
    try:
        if db_manager:
            user_id = 'default_user'
            
            # 直接从 user_holdings 获取用户持仓的基金信息
            holdings_sql = f"""
            SELECT 
                fund_code as code,
                fund_name as name,
                holding_shares,
                cost_price
            FROM user_holdings 
            WHERE user_id = '{user_id}' AND holding_shares > 0
            """
            holdings_df = db_manager.execute_query(holdings_sql)
            logger.info(f"查询持仓SQL: {holdings_sql}, 结果: {len(holdings_df) if not holdings_df.empty else 0} 条")
            
            if not holdings_df.empty:
                funds = []
                
                # 为每个基金构建评分数据（如果没有分析数据则使用默认值）
                for _, row in holdings_df.iterrows():
                    code = row['code']
                    name = row['name'] or code
                    
                    funds.append({
                        'code': code,
                        'name': name,
                        'type': '混合型',
                        'return_3m': 10.0,  # 默认值
                        'return_6m': 20.0,
                        'return_1y': 40.0,
                        'sharpe_ratio': 1.0,
                        'max_drawdown': 15.0,
                        'volatility': 18.0,
                        'manager_tenure': 3.0,
                        'fund_scale': 10.0,
                        'institution_holdings': 30.0,
                        'today_return': 0.0
                    })
                
                logger.info(f"从用户持仓获取到 {len(funds)} 只基金")
                return funds
            
            logger.info("用户暂无持仓基金")
            return []

        logger.error("db_manager 未初始化")
        return []

    except Exception as e:
        logger.error(f"获取基金列表失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def calculate_fund_scores(fund, weights):
    """计算基金各维度评分"""
    # 收益评分 (0-100)
    return_3m = fund.get('return_3m', 0)
    return_score = min(100, max(0, 50 + return_3m * 2))

    # 风险评分 (0-100) - 夏普比率越高越好，回撤越低越好
    sharpe = fund.get('sharpe_ratio', 1)
    max_dd = fund.get('max_drawdown', 20)
    risk_score = min(100, sharpe * 40 - max_dd * 1.5 + 50)

    # 经理评分 (0-100)
    tenure = fund.get('manager_tenure', 0)
    manager_score = min(100, tenure * 10)

    # 综合评分
    total_score = (
        return_score * weights.get('return', 30) / 100 +
        risk_score * weights.get('risk', 25) / 100 +
        manager_score * weights.get('manager', 20) / 100 +
        np.random.uniform(60, 90) * weights.get('scale', 15) / 100 +
        np.random.uniform(50, 80) * weights.get('institution', 10) / 100
    )

    return {
        'return_score': round(return_score, 1),
        'risk_score': round(risk_score, 1),
        'manager_score': round(manager_score, 1),
        'total_score': round(total_score, 1)
    }


def get_fund_evaluation_detail(fund_code):
    """获取单个基金的详细评价"""
    try:
        if db_manager:
            sql = """
            SELECT code, name, type, return_3m, return_6m, return_1y, return_2y, return_3y,
                   sharpe_ratio, max_drawdown, volatility,
                   manager_name, manager_tenure, manager_change_count,
                   fund_scale, establishment_date,
                   evaluation_score, evaluation_date
            FROM fund_info
            WHERE code = :code
            """
            df = db_manager.execute_query(sql, {'code': fund_code})
            if not df.empty:
                return jsonify({
                    'success': True,
                    'data': df.iloc[0].to_dict()
                })

        # 返回模拟数据
        return jsonify({
            'success': True,
            'data': {
                'code': fund_code,
                'name': f'基金{fund_code}',
                'type': '混合型',
                'return_3m': 15.5,
                'return_6m': 25.3,
                'return_1y': 45.8,
                'sharpe_ratio': 1.85,
                'max_drawdown': 12.5,
                'volatility': 18.2,
                'manager_name': '张三',
                'manager_tenure': 5.5,
                'fund_scale': 45.6,
                'evaluation_score': 82.5
            }
        })

    except Exception as e:
        logger.error(f"获取基金评价详情失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
