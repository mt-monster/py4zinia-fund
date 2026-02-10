#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
新版基金 API 路由（使用新架构）
展示如何使用统一数据服务和装饰器
"""

from flask import request

from web.decorators import api_endpoint, validate_params
from services import fund_data_service


def register_routes(app, **dependencies):
    """
    注册基金 API 路由
    
    Args:
        app: Flask 应用实例
        **dependencies: 依赖项（此模块不需要额外依赖）
    """
    
    @app.route('/api/v2/fund/<fund_code>/nav', methods=['GET'])
    @api_endpoint  # 统一响应格式和错误处理
    @validate_params(days=lambda x: 1 <= int(x) <= 3650)  # 参数验证
    def get_fund_nav_v2(fund_code: str):
        """
        获取基金净值历史（新版）
        
        使用统一数据服务，自动处理缓存和数据源降级
        
        Query Args:
            days: 获取天数（默认30，最大3650）
            
        Returns:
            {
                "success": true,
                "data": [...],
                "timestamp": "..."
            }
        """
        days = request.args.get('days', 30, type=int)
        
        # 一行代码获取数据，自动使用缓存
        df = fund_data_service.get_fund_nav_history(fund_code, days=days)
        
        if df.empty:
            return {'data': [], 'message': '未找到数据'}
        
        return df.to_dict('records')
    
    
    @app.route('/api/v2/fund/<fund_code>/realtime', methods=['GET'])
    @api_endpoint
    def get_fund_realtime_v2(fund_code: str):
        """
        获取基金实时数据（新版）
        
        Returns:
            {
                "success": true,
                "data": {
                    "fund_code": "...",
                    "fund_name": "...",
                    "current_nav": ...,
                    "daily_return": ...,
                    ...
                }
            }
        """
        # 使用统一服务获取实时数据
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
    
    
    @app.route('/api/v2/fund/<fund_code>/info', methods=['GET'])
    @api_endpoint
    def get_fund_info_v2(fund_code: str):
        """
        获取基金基本信息（新版）
        """
        info = fund_data_service.get_fund_basic_info(fund_code)
        return info or {}
    
    
    @app.route('/api/v2/system/health', methods=['GET'])
    @api_endpoint
    def get_system_health_v2():
        """
        获取系统健康状态
        
        包括数据源状态和缓存统计
        """
        return {
            'data_sources': fund_data_service.get_health_status(),
            'cache': fund_data_service.get_cache_stats()
        }
    
    
    print("✅ 新版基金 API 路由已注册 (/api/v2/...)")
