#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
新版基金路由 (v2 完整版)
替代原有的 funds.py，使用新架构
代码量减少约 80%，逻辑更清晰
"""

from flask import request
import pandas as pd
import numpy as np
import logging

from web.decorators import api_endpoint, validate_params
from services import fund_business_service, fund_data_service
from services.fund_type_service import (
    classify_fund, get_fund_type_display, get_fund_type_css_class
)
from shared.json_utils import safe_jsonify

logger = logging.getLogger(__name__)


def register_routes(app, **dependencies):
    """
    注册基金路由
    
    Args:
        app: Flask 应用实例
        **dependencies: 依赖项（db_manager 等）
    """
    # 初始化业务服务
    db_manager = dependencies.get('db_manager')
    if db_manager:
        fund_business_service.db_manager = db_manager
        if hasattr(fund_business_service, 'fund_repo'):
            fund_business_service.fund_repo.db_manager = db_manager
        if hasattr(fund_business_service, 'holdings_repo'):
            fund_business_service.holdings_repo.db_manager = db_manager
        if hasattr(fund_business_service, 'analysis_repo'):
            fund_business_service.analysis_repo.db_manager = db_manager
    
    logger.info("注册新版基金路由 v2 (complete)")
    
    _register_fund_list_routes(app)
    _register_fund_detail_routes(app)
    _register_fund_search_routes(app)
    _register_portfolio_routes(app)


def _register_fund_list_routes(app):
    """注册基金列表相关路由"""
    
    @app.route('/api/funds', methods=['GET'])
    @api_endpoint
    @validate_params(
        page=lambda x: int(x) > 0,
        per_page=lambda x: 1 <= int(x) <= 100
    )
    def get_funds_v2():
        """
        获取基金列表（包含持仓盈亏数据）
        
        Query Args:
            page: 页码（默认1）
            per_page: 每页数量（默认20）
            search: 搜索关键词
            sort_by: 排序字段
            sort_order: 排序方向（asc/desc）
            user_id: 用户ID
        """
        # 获取参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort_by', 'composite_score')
        sort_order = request.args.get('sort_order', 'desc')
        user_id = request.args.get('user_id', 'default_user')
        
        logger.info(f"获取基金列表: search={search}, sort_by={sort_by}, page={page}")
        
        # 使用业务服务层获取数据
        holdings = fund_business_service.get_user_holdings_detail(user_id)
        
        # 转换为 DataFrame 便于处理
        if holdings:
            holdings_data = []
            for h in holdings:
                fund_data = {
                    'fund_code': h.fund_code,
                    'fund_name': h.fund_name,
                    'holding_shares': h.holding_shares,
                    'cost_price': h.cost_price,
                    'holding_amount': h.holding_amount,
                    'current_nav': h.current_nav,
                    'current_value': h.current_value,
                    'today_return': h.today_return,
                    'holding_profit': h.holding_profit,
                    'holding_profit_rate': h.holding_profit_rate,
                    # 添加基金类型信息
                    'fund_type': classify_fund(h.fund_name, h.fund_code),
                    'fund_type_display': get_fund_type_display(classify_fund(h.fund_name, h.fund_code)),
                    'fund_type_class': get_fund_type_css_class(classify_fund(h.fund_name, h.fund_code))
                }
                holdings_data.append(fund_data)
            
            df = pd.DataFrame(holdings_data)
        else:
            df = pd.DataFrame()
        
        # 搜索过滤
        if search and not df.empty:
            mask = (
                df['fund_code'].str.contains(search, case=False, na=False) |
                df['fund_name'].str.contains(search, case=False, na=False)
            )
            df = df[mask]
        
        # 排序
        if not df.empty and sort_by in df.columns:
            ascending = (sort_order == 'asc')
            df = df.sort_values(by=sort_by, ascending=ascending, na_position='last')
        
        # 清理 NaN 值
        if not df.empty:
            df = df.replace({np.nan: None})
        
        # 分页
        total = len(df)
        start = (page - 1) * per_page
        end = start + per_page
        page_data = df.iloc[start:end].to_dict('records') if not df.empty else []
        
        return {
            'data': page_data,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if per_page > 0 else 1
        }


def _register_fund_detail_routes(app):
    """注册基金详情相关路由"""
    
    @app.route('/api/fund/<fund_code>', methods=['GET'])
    @api_endpoint
    def get_fund_detail_v2(fund_code: str):
        """
        获取单个基金详情
        
        Args:
            fund_code: 基金代码
        """
        include_history = request.args.get('include_history', 'false').lower() == 'true'
        days = request.args.get('days', 30, type=int)
        
        # 使用业务服务层获取完整详情
        detail = fund_business_service.get_fund_detail(
            fund_code,
            include_history=include_history,
            days=days
        )
        
        # 构建响应
        result = {
            'fund_code': detail.fund_code,
            'fund_name': detail.fund_name,
            'basic_info': _clean_nan_values(detail.basic_info),
            'realtime_data': _clean_nan_values(detail.realtime_data),
            'analysis_data': _clean_nan_values(detail.analysis_data),
            'performance_metrics': _clean_nan_values(detail.performance_metrics),
            'fund_type': classify_fund(detail.fund_name, fund_code),
            'fund_type_display': get_fund_type_display(classify_fund(detail.fund_name, fund_code)),
            'fund_type_class': get_fund_type_css_class(classify_fund(detail.fund_name, fund_code))
        }
        
        if detail.nav_history is not None and not detail.nav_history.empty:
            result['nav_history'] = detail.nav_history.replace({np.nan: None}).to_dict('records')
        else:
            result['nav_history'] = None
        
        return result
    
    
    @app.route('/api/fund/<fund_code>/nav', methods=['GET'])
    @api_endpoint
    @validate_params(days=lambda x: 1 <= int(x) <= 3650)
    def get_fund_nav_v2(fund_code: str):
        """获取基金净值历史"""
        days = request.args.get('days', 365, type=int)
        
        df = fund_data_service.get_fund_nav_history(fund_code, days=days)
        
        if df.empty:
            return {'data': [], 'message': '未找到数据'}
        
        # 清理 NaN 值
        df = df.replace({np.nan: None})
        
        return df.to_dict('records')
    
    
    @app.route('/api/fund/<fund_code>/realtime', methods=['GET'])
    @api_endpoint
    def get_fund_realtime_v2(fund_code: str):
        """获取基金实时数据"""
        realtime = fund_data_service.get_realtime_data(fund_code)
        
        return {
            'fund_code': realtime.fund_code,
            'fund_name': realtime.fund_name,
            'current_nav': realtime.current_nav,
            'yesterday_nav': realtime.yesterday_nav,
            'daily_return': realtime.daily_return,
            'estimate_nav': realtime.estimate_nav,
            'estimate_return': realtime.estimate_return,
            'data_source': realtime.data_source,
            'update_time': realtime.update_time.isoformat() if realtime.update_time else None
        }


def _register_fund_search_routes(app):
    """注册基金搜索相关路由"""
    
    @app.route('/api/fund/search', methods=['GET'])
    @api_endpoint
    def search_funds_v2():
        """搜索基金"""
        keyword = request.args.get('keyword', '').strip()
        limit = request.args.get('limit', 20, type=int)
        
        if not keyword:
            return {'error': '请提供搜索关键词'}, 400
        
        results = fund_business_service.search_funds(keyword, limit)
        
        if results.empty:
            return []
        
        # 添加基金类型信息
        results = results.copy()
        if 'fund_name' in results.columns and 'fund_code' in results.columns:
            results['fund_type'] = results.apply(
                lambda row: classify_fund(row.get('fund_name', ''), row.get('fund_code', '')),
                axis=1
            )
            results['fund_type_display'] = results['fund_type'].apply(get_fund_type_display)
        
        # 清理 NaN 值
        results = results.replace({np.nan: None})
        
        return results.to_dict('records')


def _register_portfolio_routes(app):
    """注册投资组合相关路由"""
    
    @app.route('/api/portfolio/summary', methods=['GET'])
    @api_endpoint
    def get_portfolio_summary_v2():
        """获取投资组合汇总"""
        user_id = request.args.get('user_id', 'default_user')
        
        summary = fund_business_service.get_portfolio_summary(user_id)
        
        return {
            'fund_count': summary.get('fund_count', 0),
            'total_cost': summary.get('total_cost', 0),
            'total_current_value': summary.get('total_current_value', 0),
            'total_holding_profit': summary.get('total_holding_profit', 0),
            'total_holding_profit_rate': summary.get('total_holding_profit_rate', 0),
            'total_today_profit': summary.get('total_today_profit', 0),
            'currency': 'CNY'
        }
    
    
    @app.route('/api/portfolio/holdings', methods=['GET'])
    @api_endpoint
    def get_portfolio_holdings_v2():
        """获取投资组合持仓详情"""
        user_id = request.args.get('user_id', 'default_user')
        
        holdings = fund_business_service.get_user_holdings_detail(user_id)
        
        result = []
        for h in holdings:
            result.append({
                'fund_code': h.fund_code,
                'fund_name': h.fund_name,
                'fund_type': classify_fund(h.fund_name, h.fund_code),
                'fund_type_display': get_fund_type_display(classify_fund(h.fund_name, h.fund_code)),
                'holding_shares': h.holding_shares,
                'cost_price': h.cost_price,
                'holding_amount': h.holding_amount,
                'current_nav': h.current_nav,
                'current_value': h.current_value,
                'today_return': h.today_return,
                'holding_profit': h.holding_profit,
                'holding_profit_rate': h.holding_profit_rate
            })
        
        return result


def _clean_nan_values(data: dict) -> dict:
    """清理字典中的 NaN 值"""
    if not data:
        return data
    
    cleaned = {}
    for key, value in data.items():
        if pd.isna(value):
            cleaned[key] = None
        else:
            cleaned[key] = value
    
    return cleaned
