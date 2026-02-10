#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
路由模块
自动注册所有路由
"""

import logging
from .funds_v2_complete import register_routes as register_funds_v2
from .holdings_v2 import register_routes as register_holdings_v2

logger = logging.getLogger(__name__)


def register_all_routes(app, **dependencies):
    """
    注册所有新版路由
    
    这个函数会在应用启动时自动调用，注册所有路由模块
    
    Args:
        app: Flask 应用实例
        **dependencies: 依赖项（db_manager, strategy_engine 等）
    """
    logger.info("开始注册新版路由...")
    
    # 注册基金路由 v2
    try:
        register_funds_v2(app, **dependencies)
        logger.info("✅ 基金路由 v2 注册成功")
    except Exception as e:
        logger.error(f"❌ 基金路由 v2 注册失败: {e}")
    
    # 注册持仓路由 v2
    try:
        register_holdings_v2(app, **dependencies)
        logger.info("✅ 持仓路由 v2 注册成功")
    except Exception as e:
        logger.error(f"❌ 持仓路由 v2 注册失败: {e}")
    
    logger.info("新版路由注册完成")
