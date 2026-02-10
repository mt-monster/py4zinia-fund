#!/usr/bin/env python
# coding: utf-8

"""
基金分析系统 Web 应用
提供前端界面和 API 接口

代码结构优化：路由按功能拆分到 routes/ 目录下
"""

import os
import sys
import json
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import pandas as pd
from datetime import datetime, timedelta
import logging

# 添加父目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.enhanced_config import DATABASE_CONFIG, NOTIFICATION_CONFIG
from data_retrieval.enhanced_database import EnhancedDatabaseManager
from backtesting.enhanced_strategy import EnhancedInvestmentStrategy
from backtesting.unified_strategy_engine import UnifiedStrategyEngine
from backtesting.strategy_evaluator import StrategyEvaluator
from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
from data_retrieval.fund_screenshot_ocr import recognize_fund_screenshot, validate_recognized_fund
from data_retrieval.heavyweight_stocks_fetcher import fetch_heavyweight_stocks, get_fetcher
from services.fund_type_service import (
    FundTypeService, classify_fund, get_fund_type_display, 
    get_fund_type_css_class, FUND_TYPE_CN, FUND_TYPE_CSS_CLASS
)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# 初始化组件
db_manager = None
strategy_engine = None
unified_strategy_engine = None
strategy_evaluator = None
fund_data_manager = None

# 缓存服务组件
cache_manager = None
holding_service = None
sync_service = None


def init_components():
    """初始化系统组件"""
    global db_manager, strategy_engine, unified_strategy_engine, strategy_evaluator, fund_data_manager
    global cache_manager, holding_service, sync_service
    
    try:
        db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        strategy_engine = EnhancedInvestmentStrategy()
        unified_strategy_engine = UnifiedStrategyEngine()
        strategy_evaluator = StrategyEvaluator()
        fund_data_manager = MultiSourceDataAdapter()
        
        # 初始化重仓股数据获取器的数据库连接
        from data_retrieval.heavyweight_stocks_fetcher import init_fetcher
        init_fetcher(db_manager)
        
        # 初始化缓存服务
        try:
            from services import FundNavCacheManager, HoldingRealtimeService, FundDataSyncService
            from services.cache_api_routes import init_cache_routes
            
            cache_manager = FundNavCacheManager(db_manager, default_ttl_minutes=15)
            holding_service = HoldingRealtimeService(db_manager, cache_manager)
            sync_service = FundDataSyncService(cache_manager, db_manager)
            
            # 启动定时同步服务（生产环境启用）
            if os.environ.get('ENABLE_SYNC_SERVICE', 'true').lower() == 'true':
                sync_service.start()
                logger.info("数据同步服务已启动")
            
            # 注册缓存相关API路由
            init_cache_routes(app, cache_manager, holding_service, sync_service)
            
            logger.info("缓存服务初始化完成")
        except Exception as cache_e:
            logger.warning(f"缓存服务初始化失败（非致命）: {cache_e}")
        
        logger.info("系统组件初始化完成（含统一策略引擎）")
        logger.info(f"db_manager: {db_manager is not None}")
        logger.info(f"strategy_engine: {strategy_engine is not None}")
        logger.info(f"fund_data_manager: {fund_data_manager is not None}")
        logger.info(f"cache_manager: {cache_manager is not None}")
        logger.info(f"holding_service: {holding_service is not None}")
    except Exception as e:
        logger.error(f"系统组件初始化失败: {str(e)}", exc_info=True)
        raise


def register_all_routes():
    """注册所有路由模块"""
    global db_manager, strategy_engine, unified_strategy_engine, strategy_evaluator, fund_data_manager
    global cache_manager, holding_service, sync_service
    
    # 导入并注册页面路由
    try:
        from routes.pages import register_routes as register_pages
        register_pages(app)
        logger.info("页面路由注册完成")
    except Exception as e:
        logger.error(f"页面路由注册失败: {e}")
    
    # 导入并注册 Dashboard API 路由
    try:
        from routes.dashboard import register_routes as register_dashboard
        register_dashboard(app, db_manager=db_manager, strategy_engine=strategy_engine,
                          holding_service=holding_service, cache_manager=cache_manager)
        logger.info("Dashboard 路由注册完成")
    except Exception as e:
        logger.error(f"Dashboard 路由注册失败: {e}")
    
    # 导入并注册基金 API 路由
    try:
        from routes.funds import register_routes as register_funds
        register_funds(app, db_manager=db_manager, strategy_engine=strategy_engine,
                      unified_strategy_engine=unified_strategy_engine,
                      strategy_evaluator=strategy_evaluator,
                      fund_data_manager=fund_data_manager)
        logger.info("基金路由注册完成")
    except Exception as e:
        logger.error(f"基金路由注册失败: {e}")
    
    # 导入并注册策略 API 路由
    try:
        from routes.strategies import register_routes as register_strategies
        register_strategies(app, db_manager=db_manager, strategy_engine=strategy_engine,
                           unified_strategy_engine=unified_strategy_engine,
                           strategy_evaluator=strategy_evaluator,
                           fund_data_manager=fund_data_manager)
        logger.info("策略路由注册完成")
    except Exception as e:
        logger.error(f"策略路由注册失败: {e}")
    
    # 导入并注册持仓 API 路由
    try:
        from routes.holdings import register_routes as register_holdings
        register_holdings(app, db_manager=db_manager, holding_service=holding_service,
                         cache_manager=cache_manager, fund_data_manager=fund_data_manager)
        logger.info("持仓路由注册完成")
    except Exception as e:
        logger.error(f"持仓路由注册失败: {e}")
    
    # 导入并注册 ETF API 路由
    try:
        from routes.etf import register_routes as register_etf
        register_etf(app, db_manager=db_manager)
        logger.info("ETF 路由注册完成")
    except Exception as e:
        logger.error(f"ETF 路由注册失败: {e}")
    
    # 导入并注册用户策略 API 路由
    try:
        from routes.user_strategies import register_routes as register_user_strategies
        register_user_strategies(app, db_manager=db_manager)
        logger.info("用户策略路由注册完成")
    except Exception as e:
        logger.error(f"用户策略路由注册失败: {e}")
    
    # 导入并注册内置策略 API 路由
    try:
        from routes.builtin_strategies import register_routes as register_builtin
        register_builtin(app, db_manager=db_manager)
        logger.info("内置策略路由注册完成")
    except Exception as e:
        logger.error(f"内置策略路由注册失败: {e}")
    
    # 导入并注册回测 API 路由
    try:
        from routes.backtest import register_routes as register_backtest
        register_backtest(app, db_manager=db_manager)
        logger.info("回测路由注册完成")
    except Exception as e:
        logger.error(f"回测路由注册失败: {e}")


# 初始化组件
init_components()

# 注册所有路由
register_all_routes()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
