#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
新版持仓路由 (v2)
替代原有的 holdings.py，使用新架构
"""

from flask import request
import pandas as pd
import numpy as np
import logging
from datetime import datetime

from web.decorators import api_endpoint, validate_params
from services import fund_business_service
from data_access.repositories import HoldingsRepository

logger = logging.getLogger(__name__)


def register_routes(app, **dependencies):
    """
    注册持仓管理路由
    
    Args:
        app: Flask 应用实例
        **dependencies: 依赖项
    """
    db_manager = dependencies.get('db_manager')
    if db_manager:
        fund_business_service.db_manager = db_manager
        if hasattr(fund_business_service, 'holdings_repo'):
            fund_business_service.holdings_repo.db_manager = db_manager
    
    holdings_repo = HoldingsRepository(db_manager) if db_manager else None
    
    logger.info("注册新版持仓路由 v2")
    
    _register_holding_query_routes(app, holdings_repo)
    _register_holding_management_routes(app, holdings_repo)
    _register_holding_analysis_routes(app, holdings_repo)


def _register_holding_query_routes(app, holdings_repo):
    """注册持仓查询路由"""
    
    @app.route('/api/holdings', methods=['GET'])
    @api_endpoint
    def get_holdings_v2():
        """获取用户持仓列表"""
        user_id = request.args.get('user_id', 'default_user')
        fund_code = request.args.get('fund_code')
        
        if fund_code:
            # 获取单个基金持仓
            df = holdings_repo.get_user_holdings(user_id, fund_code) if holdings_repo else pd.DataFrame()
        else:
            # 获取所有持仓（使用业务服务层）
            holdings = fund_business_service.get_user_holdings_detail(user_id)
            if holdings:
                df = pd.DataFrame([{
                    'id': h.holding_id,
                    'fund_code': h.fund_code,
                    'fund_name': h.fund_name,
                    'holding_shares': h.holding_shares,
                    'cost_price': h.cost_price,
                    'holding_amount': h.holding_amount,
                    'current_nav': h.current_nav,
                    'current_value': h.current_value,
                    'today_return': h.today_return,
                    'holding_profit': h.holding_profit,
                    'holding_profit_rate': h.holding_profit_rate
                } for h in holdings])
            else:
                df = pd.DataFrame()
        
        if df.empty:
            return []
        
        # 清理 NaN 值
        df = df.replace({np.nan: None})
        
        return df.to_dict('records')
    
    
    @app.route('/api/holdings/summary', methods=['GET'])
    @api_endpoint
    def get_holdings_summary_v2():
        """获取持仓汇总统计"""
        user_id = request.args.get('user_id', 'default_user')
        
        summary = fund_business_service.get_portfolio_summary(user_id)
        
        return {
            'fund_count': summary.get('fund_count', 0),
            'total_cost': summary.get('total_cost', 0),
            'total_current_value': summary.get('total_current_value', 0),
            'total_holding_profit': summary.get('total_holding_profit', 0),
            'total_holding_profit_rate': summary.get('total_holding_profit_rate', 0),
            'total_today_profit': summary.get('total_today_profit', 0)
        }
    
    
    @app.route('/api/holdings/detail', methods=['GET'])
    @api_endpoint
    def get_holdings_detail_v2():
        """获取持仓详情（包含分析数据）"""
        user_id = request.args.get('user_id', 'default_user')
        
        if holdings_repo:
            df = holdings_repo.get_holdings_with_analysis(user_id)
        else:
            df = pd.DataFrame()
        
        if df.empty:
            return []
        
        # 清理 NaN 值
        df = df.replace({np.nan: None})
        
        return df.to_dict('records')


def _register_holding_management_routes(app, holdings_repo):
    """注册持仓管理路由"""
    
    @app.route('/api/holdings', methods=['POST'])
    @api_endpoint
    def add_holding_v2():
        """添加持仓"""
        data = request.get_json()
        
        if not data:
            return {'error': '请提供持仓数据'}, 400
        
        fund_code = data.get('fund_code')
        fund_name = data.get('fund_name')
        holding_shares = data.get('holding_shares')
        cost_price = data.get('cost_price')
        user_id = data.get('user_id', 'default_user')
        
        # 验证必填字段
        if not all([fund_code, fund_name, holding_shares, cost_price]):
            return {'error': '请提供完整的持仓信息（基金代码、名称、份额、成本价）'}, 400
        
        try:
            holding_shares = float(holding_shares)
            cost_price = float(cost_price)
        except (ValueError, TypeError):
            return {'error': '份额和成本价必须是数字'}, 400
        
        if holdings_repo:
            success = holdings_repo.add_holding(
                fund_code=fund_code,
                fund_name=fund_name,
                holding_shares=holding_shares,
                cost_price=cost_price,
                user_id=user_id
            )
            
            if success:
                return {'message': '持仓添加成功'}
            else:
                return {'error': '持仓添加失败'}, 500
        else:
            return {'error': '数据库未初始化'}, 500
    
    
    @app.route('/api/holdings/<int:holding_id>', methods=['PUT'])
    @api_endpoint
    def update_holding_v2(holding_id: int):
        """更新持仓"""
        data = request.get_json()
        
        if not data:
            return {'error': '请提供更新数据'}, 400
        
        # 允许的更新字段
        allowed_fields = ['holding_shares', 'cost_price', 'fund_name']
        updates = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not updates:
            return {'error': '没有可更新的字段'}, 400
        
        if holdings_repo:
            success = holdings_repo.update_holding(holding_id, updates)
            
            if success:
                return {'message': '持仓更新成功'}
            else:
                return {'error': '持仓更新失败'}, 500
        else:
            return {'error': '数据库未初始化'}, 500
    
    
    @app.route('/api/holdings/<int:holding_id>', methods=['DELETE'])
    @api_endpoint
    def delete_holding_v2(holding_id: int):
        """删除持仓"""
        if holdings_repo:
            success = holdings_repo.delete_holding(holding_id)
            
            if success:
                return {'message': '持仓删除成功'}
            else:
                return {'error': '持仓删除失败'}, 500
        else:
            return {'error': '数据库未初始化'}, 500


def _register_holding_analysis_routes(app, holdings_repo):
    """注册持仓分析路由"""
    
    @app.route('/api/holdings/analysis', methods=['GET'])
    @api_endpoint
    def get_holdings_analysis_v2():
        """获取持仓分析（收益率分布等）"""
        user_id = request.args.get('user_id', 'default_user')
        
        # 获取持仓详情
        holdings = fund_business_service.get_user_holdings_detail(user_id)
        
        if not holdings:
            return {
                'total_value': 0,
                'total_cost': 0,
                'total_profit': 0,
                'profit_rate': 0,
                'distribution': {}
            }
        
        # 计算分布
        profit_rates = [h.holding_profit_rate for h in holdings if h.holding_profit_rate is not None]
        
        distribution = {
            'profit_count': len([r for r in profit_rates if r > 0]),
            'loss_count': len([r for r in profit_rates if r < 0]),
            'break_even_count': len([r for r in profit_rates if r == 0]),
            'avg_profit_rate': sum(profit_rates) / len(profit_rates) if profit_rates else 0,
            'max_profit_rate': max(profit_rates) if profit_rates else 0,
            'max_loss_rate': min(profit_rates) if profit_rates else 0
        }
        
        summary = fund_business_service.get_portfolio_summary(user_id)
        
        return {
            'total_value': summary.get('total_current_value', 0),
            'total_cost': summary.get('total_cost', 0),
            'total_profit': summary.get('total_holding_profit', 0),
            'profit_rate': summary.get('total_holding_profit_rate', 0),
            'distribution': distribution,
            'holdings_count': len(holdings)
        }
