#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GraphQL变更定义

定义所有GraphQL变更（写操作）。
"""

import graphene
from graphene.types import datetime
from typing import Optional

from .types import (
    FundType, StrategyType, BacktestResultType,
    PortfolioType, HoldingType
)


# ============ 输入类型 ============

class CreateStrategyInput(graphene.InputObjectType):
    """创建策略输入"""
    name = graphene.String(required=True, description="策略名称")
    description = graphene.String(description="策略描述")
    strategy_type = graphene.String(required=True, description="策略类型")
    params = graphene.JSONString(description="策略参数")
    user_id = graphene.String(required=True, description="用户ID")


class UpdateStrategyInput(graphene.InputObjectType):
    """更新策略输入"""
    id = graphene.ID(required=True, description="策略ID")
    name = graphene.String(description="策略名称")
    description = graphene.String(description="策略描述")
    params = graphene.JSONString(description="策略参数")


class RunBacktestInput(graphene.InputObjectType):
    """运行回测输入"""
    strategy_id = graphene.String(required=True, description="策略ID")
    user_id = graphene.String(required=True, description="用户ID")
    start_date = graphene.Date(required=True, description="开始日期")
    end_date = graphene.Date(required=True, description="结束日期")
    initial_capital = graphene.Float(default_value=100000.0, description="初始资金")
    rebalance_freq = graphene.String(default_value="monthly", description="再平衡频率")


class AddHoldingInput(graphene.InputObjectType):
    """添加持仓输入"""
    user_id = graphene.String(required=True, description="用户ID")
    fund_code = graphene.String(required=True, description="基金代码")
    shares = graphene.Float(required=True, description="份额")
    cost_price = graphene.Float(required=True, description="成本价")


class UpdateHoldingInput(graphene.InputObjectType):
    """更新持仓输入"""
    user_id = graphene.String(required=True, description="用户ID")
    fund_code = graphene.String(required=True, description="基金代码")
    shares = graphene.Float(description="份额")
    cost_price = graphene.Float(description="成本价")


# ============ 输出类型 ============

class CreateStrategyPayload(graphene.ObjectType):
    """创建策略输出"""
    success = graphene.Boolean()
    strategy = graphene.Field(StrategyType)
    error = graphene.String()


class UpdateStrategyPayload(graphene.ObjectType):
    """更新策略输出"""
    success = graphene.Boolean()
    strategy = graphene.Field(StrategyType)
    error = graphene.String()


class DeleteStrategyPayload(graphene.ObjectType):
    """删除策略输出"""
    success = graphene.Boolean()
    error = graphene.String()


class RunBacktestPayload(graphene.ObjectType):
    """运行回测输出"""
    success = graphene.Boolean()
    task_id = graphene.String()
    backtest = graphene.Field(BacktestResultType)
    error = graphene.String()


class CancelBacktestPayload(graphene.ObjectType):
    """取消回测输出"""
    success = graphene.Boolean()
    error = graphene.String()


class AddHoldingPayload(graphene.ObjectType):
    """添加持仓输出"""
    success = graphene.Boolean()
    holding = graphene.Field(HoldingType)
    error = graphene.String()


class UpdateHoldingPayload(graphene.ObjectType):
    """更新持仓输出"""
    success = graphene.Boolean()
    holding = graphene.Field(HoldingType)
    error = graphene.String()


class DeleteHoldingPayload(graphene.ObjectType):
    """删除持仓输出"""
    success = graphene.Boolean()
    error = graphene.String()


class RefreshFundDataPayload(graphene.ObjectType):
    """刷新基金数据输出"""
    success = graphene.Boolean()
    fund = graphene.Field(FundType)
    error = graphene.String()


# ============ Mutation根类型 ============

class Mutation(graphene.ObjectType):
    """GraphQL变更根类型"""
    
    # ============ 策略变更 ============
    
    create_strategy = graphene.Field(
        CreateStrategyPayload,
        input=CreateStrategyInput(required=True),
        description="创建新策略"
    )
    
    update_strategy = graphene.Field(
        UpdateStrategyPayload,
        input=UpdateStrategyInput(required=True),
        description="更新策略"
    )
    
    delete_strategy = graphene.Field(
        DeleteStrategyPayload,
        id=graphene.ID(required=True, description="策略ID"),
        description="删除策略"
    )
    
    # ============ 回测变更 ============
    
    run_backtest = graphene.Field(
        RunBacktestPayload,
        input=RunBacktestInput(required=True),
        description="运行策略回测"
    )
    
    cancel_backtest = graphene.Field(
        CancelBacktestPayload,
        task_id=graphene.String(required=True, description="任务ID"),
        description="取消回测任务"
    )
    
    # ============ 持仓变更 ============
    
    add_holding = graphene.Field(
        AddHoldingPayload,
        input=AddHoldingInput(required=True),
        description="添加持仓"
    )
    
    update_holding = graphene.Field(
        UpdateHoldingPayload,
        input=UpdateHoldingInput(required=True),
        description="更新持仓"
    )
    
    delete_holding = graphene.Field(
        DeleteHoldingPayload,
        user_id=graphene.String(required=True, description="用户ID"),
        fund_code=graphene.String(required=True, description="基金代码"),
        description="删除持仓"
    )
    
    # ============ 数据刷新 ============
    
    refresh_fund_data = graphene.Field(
        RefreshFundDataPayload,
        code=graphene.String(required=True, description="基金代码"),
        description="刷新基金数据"
    )
    
    # ============ Resolver实现 ============
    
    def resolve_create_strategy(self, info, input: CreateStrategyInput) -> CreateStrategyPayload:
        """创建策略"""
        try:
            # 这里实现创建策略的逻辑
            # 可以通过Celery异步处理
            from celery_tasks.tasks import update_fund_data_task
            
            strategy = StrategyType(
                id="new_strategy_id",
                name=input.name,
                description=input.description or '',
                type=input.strategy_type,
                user_id=input.user_id
            )
            
            return CreateStrategyPayload(
                success=True,
                strategy=strategy
            )
        except Exception as e:
            return CreateStrategyPayload(
                success=False,
                error=str(e)
            )
    
    def resolve_update_strategy(self, info, input: UpdateStrategyInput) -> UpdateStrategyPayload:
        """更新策略"""
        try:
            # 实现更新逻辑
            strategy = StrategyType(
                id=input.id,
                name=input.name or '',
                type='updated'
            )
            
            return UpdateStrategyPayload(
                success=True,
                strategy=strategy
            )
        except Exception as e:
            return UpdateStrategyPayload(
                success=False,
                error=str(e)
            )
    
    def resolve_delete_strategy(self, info, id: str) -> DeleteStrategyPayload:
        """删除策略"""
        try:
            # 实现删除逻辑
            return DeleteStrategyPayload(success=True)
        except Exception as e:
            return DeleteStrategyPayload(
                success=False,
                error=str(e)
            )
    
    def resolve_run_backtest(self, info, input: RunBacktestInput) -> RunBacktestPayload:
        """运行回测"""
        try:
            # 使用微服务创建任务
            from microservices.backtest_service.service import get_service
            service = get_service()
            
            task = service.create_task(
                strategy_id=input.strategy_id,
                user_id=input.user_id,
                start_date=input.start_date.isoformat() if input.start_date else None,
                end_date=input.end_date.isoformat() if input.end_date else None,
                initial_capital=input.initial_capital,
                rebalance_freq=input.rebalance_freq
            )
            
            # 异步执行任务
            from celery_tasks.tasks import run_backtest_task
            run_backtest_task.delay(
                strategy_id=input.strategy_id,
                user_id=input.user_id,
                start_date=input.start_date.isoformat() if input.start_date else None,
                end_date=input.end_date.isoformat() if input.end_date else None,
                initial_capital=input.initial_capital,
                rebalance_freq=input.rebalance_freq
            )
            
            return RunBacktestPayload(
                success=True,
                task_id=task.task_id,
                backtest=BacktestResultType(
                    id=task.task_id,
                    task_id=task.task_id
                )
            )
        except Exception as e:
            return RunBacktestPayload(
                success=False,
                error=str(e)
            )
    
    def resolve_cancel_backtest(self, info, task_id: str) -> CancelBacktestPayload:
        """取消回测"""
        try:
            from microservices.backtest_service.service import get_service
            service = get_service()
            success = service.cancel_task(task_id)
            
            return CancelBacktestPayload(success=success)
        except Exception as e:
            return CancelBacktestPayload(
                success=False,
                error=str(e)
            )
    
    def resolve_add_holding(self, info, input: AddHoldingInput) -> AddHoldingPayload:
        """添加持仓"""
        try:
            # 实现添加持仓逻辑
            holding = HoldingType(
                fund_code=input.fund_code,
                shares=input.shares,
                cost_price=input.cost_price
            )
            
            # 触发缓存更新事件
            from messaging.event_bus import EventBus
            event_bus = EventBus()
            event_bus.emit('user.portfolio_updated', {
                'user_id': input.user_id,
                'action': 'add',
                'fund_code': input.fund_code
            })
            
            return AddHoldingPayload(
                success=True,
                holding=holding
            )
        except Exception as e:
            return AddHoldingPayload(
                success=False,
                error=str(e)
            )
    
    def resolve_update_holding(self, info, input: UpdateHoldingInput) -> UpdateHoldingPayload:
        """更新持仓"""
        try:
            holding = HoldingType(
                fund_code=input.fund_code,
                shares=input.shares,
                cost_price=input.cost_price
            )
            
            return UpdateHoldingPayload(
                success=True,
                holding=holding
            )
        except Exception as e:
            return UpdateHoldingPayload(
                success=False,
                error=str(e)
            )
    
    def resolve_delete_holding(self, info, user_id: str, fund_code: str) -> DeleteHoldingPayload:
        """删除持仓"""
        try:
            # 触发缓存更新事件
            from messaging.event_bus import EventBus
            event_bus = EventBus()
            event_bus.emit('user.portfolio_updated', {
                'user_id': user_id,
                'action': 'delete',
                'fund_code': fund_code
            })
            
            return DeleteHoldingPayload(success=True)
        except Exception as e:
            return DeleteHoldingPayload(
                success=False,
                error=str(e)
            )
    
    def resolve_refresh_fund_data(self, info, code: str) -> RefreshFundDataPayload:
        """刷新基金数据"""
        try:
            # 使用Celery异步刷新
            from celery_tasks.tasks import update_fund_data_task
            update_fund_data_task.delay(fund_code=code, data_type='all')
            
            fund = FundType(code=code)
            
            return RefreshFundDataPayload(
                success=True,
                fund=fund
            )
        except Exception as e:
            return RefreshFundDataPayload(
                success=False,
                error=str(e)
            )
