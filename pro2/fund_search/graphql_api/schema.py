#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GraphQL Schema定义

组合所有查询和变更定义。
"""

import graphene

from .queries import Query
from .mutations import Mutation


class Subscription(graphene.ObjectType):
    """GraphQL订阅（WebSocket实时推送）"""
    
    # 实时净值更新订阅
    fund_nav_updated = graphene.Field(
        'graphql_api.types.FundNavType',
        fund_code=graphene.String(required=True, description="基金代码")
    )
    
    # 回测进度订阅
    backtest_progress = graphene.Field(
        graphene.ObjectType,
        task_id=graphene.String(required=True, description="任务ID")
    )
    
    # 持仓变动订阅
    holding_changed = graphene.Field(
        'graphql_api.types.HoldingType',
        user_id=graphene.String(required=True, description="用户ID")
    )


# 创建Schema
schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
    # subscription=Subscription  # 如需WebSocket支持可启用
)

# 导出schema
__all__ = ['schema', 'Query', 'Mutation', 'Subscription']
