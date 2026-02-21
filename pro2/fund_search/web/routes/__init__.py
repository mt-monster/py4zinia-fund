#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
路由模块
自动注册所有路由

说明：
- 主基金路由: funds.py
- 主持仓路由: holdings.py
- 其他功能路由: analysis.py, strategies.py 等

已移除的 v2 版本路由（注册失败）：
- funds_v2.py (删除)
- funds_v2_complete.py (删除)
- fund_api_new.py (删除)
- holdings_v2.py (删除)

当前使用 funds.py 和 holdings.py 作为主路由文件
"""

import logging

logger = logging.getLogger(__name__)


def register_all_routes(app, **dependencies):
    """
    注册所有路由
    
    注意：v2 版本路由已移除，使用 funds.py 和 holdings.py 作为主路由
    
    Args:
        app: Flask 应用实例
        **dependencies: 依赖项（db_manager, strategy_engine 等）
    """
    logger.info("路由注册由 auto_router 处理，跳过新版路由注册")
    pass
