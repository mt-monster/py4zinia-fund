#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GraphQL API模块

使用Graphene实现的GraphQL API，优化数据查询：
- 精确数据获取，避免过度获取
- 单一端点处理所有查询
- 类型安全和自文档化
- 强大的查询能力（过滤、排序、分页）

使用方法:
    from graphql_api import schema
    
    # 执行查询
    result = schema.execute('{ funds { code name nav } }')
    
    # 在Flask中使用
    from graphql_api import graphql_blueprint
    app.register_blueprint(graphql_blueprint, url_prefix='/graphql')

配置要求:
    - graphene>=3.3.0
    - Flask-GraphQL>=2.0
"""

from .schema import schema
from .blueprint import graphql_blueprint
from .types import (
    FundType, FundNavType, FundPerformanceType,
    StrategyType, BacktestResultType, HoldingType,
    PortfolioType, AnalysisResultType
)

__all__ = [
    'schema',
    'graphql_blueprint',
    'FundType',
    'FundNavType',
    'FundPerformanceType',
    'StrategyType',
    'BacktestResultType',
    'HoldingType',
    'PortfolioType',
    'AnalysisResultType'
]
