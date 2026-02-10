#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
新版基金路由 (v2)
使用业务服务层和统一装饰器
大幅简化代码，消除重复逻辑
"""

from flask import request

from web.decorators import api_endpoint, validate_params
from services import fund_business_service, fund_data_service


def register_routes(app, **dependencies):
    """注册基金路由"""
    
    # 初始化业务服务（传入 db_manager）
    db_manager = dependencies.get('db_manager')
    if db_manager:
        fund_business_service.db_manager = db_manager
        fund_business_service.fund_repo.db_manager = db_manager
        fund_business_service.holdings_repo.db_manager = db_manager
        fund_business_service.analysis_repo.db_manager = db_manager
    
    
    @app.route('/api/v2/fund/<fund_code>/detail', methods=['GET'])
    @api_endpoint
    def get_fund_detail_v2(fund_code: str):
        """
        获取基金完整详情
        
        Query Args:
            include_history: 是否包含净值历史 (true/false)
            days: 历史数据天数 (默认30)
        """
        include_history = request.args.get('include_history', 'false').lower() == 'true'
        days = request.args.get('days', 30, type=int)
        
        detail = fund_business_service.get_fund_detail(
            fund_code,
            include_history=include_history,
            days=days
        )
        
        return {
            'fund_code': detail.fund_code,
            'fund_name': detail.fund_name,
            'basic_info': detail.basic_info,
            'realtime_data': detail.realtime_data,
            'analysis_data': detail.analysis_data,
            'performance_metrics': detail.performance_metrics,
            'nav_history': (
                detail.nav_history.to_dict('records')
                if detail.nav_history is not None else None
            )
        }
    
    
    @app.route('/api/v2/fund/<fund_code>/nav', methods=['GET'])
    @api_endpoint
    @validate_params(days=lambda x: 1 <= int(x) <= 3650)
    def get_fund_nav_v2(fund_code: str):
        """
        获取基金净值历史
        
        Query Args:
            days: 获取天数 (默认30, 最大3650)
        """
        days = request.args.get('days', 30, type=int)
        
        df = fund_data_service.get_fund_nav_history(fund_code, days=days)
        
        if df.empty:
            return {'data': [], 'message': '未找到数据'}
        
        return df.to_dict('records')
    
    
    @app.route('/api/v2/fund/<fund_code>/realtime', methods=['GET'])
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
            'update_time': (
                realtime.update_time.isoformat()
                if realtime.update_time else None
            )
        }
    
    
    @app.route('/api/v2/fund/search', methods=['GET'])
    @api_endpoint
    def search_funds_v2():
        """
        搜索基金
        
        Query Args:
            keyword: 搜索关键词
            limit: 返回数量限制 (默认20)
        """
        keyword = request.args.get('keyword', '')
        limit = request.args.get('limit', 20, type=int)
        
        if not keyword:
            return {'error': '请提供搜索关键词'}, 400
        
        results = fund_business_service.search_funds(keyword, limit)
        
        return results.to_dict('records') if not results.empty else []
    
    
    @app.route('/api/v2/holdings', methods=['GET'])
    @api_endpoint
    def get_user_holdings_v2():
        """获取用户持仓详情"""
        holdings = fund_business_service.get_user_holdings_detail()
        
        return [
            {
                'holding_id': h.holding_id,
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
            }
            for h in holdings
        ]
    
    
    @app.route('/api/v2/portfolio/summary', methods=['GET'])
    @api_endpoint
    def get_portfolio_summary_v2():
        """获取投资组合汇总"""
        summary = fund_business_service.get_portfolio_summary()
        
        return {
            'fund_count': summary.get('fund_count', 0),
            'total_cost': summary.get('total_cost', 0),
            'total_current_value': summary.get('total_current_value', 0),
            'total_holding_profit': summary.get('total_holding_profit', 0),
            'total_holding_profit_rate': summary.get('total_holding_profit_rate', 0),
            'total_today_profit': summary.get('total_today_profit', 0)
        }
    
    
    @app.route('/api/v2/system/health', methods=['GET'])
    @api_endpoint
    def get_system_health_v2():
        """获取系统健康状态"""
        return {
            'data_sources': fund_data_service.get_health_status(),
            'cache': fund_data_service.get_cache_stats()
        }
    
    
    print("✅ 新版基金路由 v2 已注册 (/api/v2/...)")
