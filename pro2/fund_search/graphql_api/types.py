#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GraphQL类型定义

定义所有GraphQL Schema类型，对应系统中的数据模型。
"""

import graphene
from graphene import relay
from graphene.types import datetime
from typing import List


class FundType(graphene.ObjectType):
    """基金类型"""
    
    class Meta:
        interfaces = (relay.Node,)
        description = "基金基本信息"
    
    # 基本字段
    code = graphene.String(description="基金代码")
    name = graphene.String(description="基金名称")
    type = graphene.String(description="基金类型")
    manager = graphene.String(description="基金经理")
    company = graphene.String(description="基金公司")
    
    # 日期字段
    established_date = graphene.Date(description="成立日期")
    
    # 关联字段
    nav_history = graphene.List(lambda: FundNavType, 
                                 days=graphene.Int(default_value=30),
                                 description="历史净值")
    performance = graphene.Field(lambda: FundPerformanceType, 
                                  description="绩效指标")
    holdings = graphene.List(lambda: HoldingType,
                              description="持仓信息")
    
    def resolve_nav_history(self, info, days=30):
        """解析净值历史"""
        try:
            from services.fund_data_preloader import get_preloader
            preloader = get_preloader()
            df = preloader.get_fund_nav(self.code, days=days)
            
            if df is not None and not df.empty:
                return [
                    FundNavType(
                        date=row.get('date'),
                        nav=row.get('nav'),
                        acc_nav=row.get('acc_nav'),
                        daily_return=row.get('daily_return')
                    )
                    for _, row in df.iterrows()
                ]
        except Exception:
            pass
        return []
    
    def resolve_performance(self, info):
        """解析绩效指标"""
        try:
            from services.fund_data_preloader import get_preloader
            preloader = get_preloader()
            perf = preloader.get_fund_performance(self.code)
            
            if perf:
                return FundPerformanceType(**perf)
        except Exception:
            pass
        return None


class FundNavType(graphene.ObjectType):
    """基金净值类型"""
    
    class Meta:
        description = "基金净值数据"
    
    date = graphene.Date(description="日期")
    nav = graphene.Float(description="单位净值")
    acc_nav = graphene.Float(description="累计净值")
    daily_return = graphene.Float(description="日收益率")


class FundPerformanceType(graphene.ObjectType):
    """基金绩效类型"""
    
    class Meta:
        description = "基金绩效指标"
    
    # 收益指标
    total_return = graphene.Float(description="总收益率")
    annualized_return = graphene.Float(description="年化收益率")
    
    # 风险指标
    volatility = graphene.Float(description="波动率")
    max_drawdown = graphene.Float(description="最大回撤")
    
    # 风险调整收益
    sharpe_ratio = graphene.Float(description="夏普比率")
    sortino_ratio = graphene.Float(description="索提诺比率")
    calmar_ratio = graphene.Float(description="卡玛比率")
    
    # 其他指标
    alpha = graphene.Float(description="阿尔法")
    beta = graphene.Float(description="贝塔")
    
    # 时间范围
    period_start = graphene.Date(description="统计开始日期")
    period_end = graphene.Date(description="统计结束日期")


class StrategyType(graphene.ObjectType):
    """策略类型"""
    
    class Meta:
        interfaces = (relay.Node,)
        description = "投资策略"
    
    id = graphene.ID(required=True)
    name = graphene.String(description="策略名称")
    description = graphene.String(description="策略描述")
    type = graphene.String(description="策略类型")
    
    # 配置参数
    params = graphene.JSONString(description="策略参数")
    
    # 创建信息
    created_at = graphene.DateTime(description="创建时间")
    updated_at = graphene.DateTime(description="更新时间")
    user_id = graphene.String(description="所属用户")
    
    # 关联数据
    backtests = graphene.List(lambda: BacktestResultType,
                               description="回测结果列表")
    
    def resolve_backtests(self, info):
        """解析回测结果"""
        # 从数据库查询回测结果
        return []


class BacktestResultType(graphene.ObjectType):
    """回测结果类型"""
    
    class Meta:
        interfaces = (relay.Node,)
        description = "策略回测结果"
    
    id = graphene.ID(required=True)
    task_id = graphene.String(description="任务ID")
    
    # 时间范围
    start_date = graphene.Date(description="开始日期")
    end_date = graphene.Date(description="结束日期")
    
    # 资金信息
    initial_capital = graphene.Float(description="初始资金")
    final_capital = graphene.Float(description="最终资金")
    
    # 收益指标
    total_return = graphene.Float(description="总收益率")
    annualized_return = graphene.Float(description="年化收益率")
    
    # 风险指标
    max_drawdown = graphene.Float(description="最大回撤")
    volatility = graphene.Float(description="波动率")
    sharpe_ratio = graphene.Float(description="夏普比率")
    
    # 交易统计
    total_trades = graphene.Int(description="总交易次数")
    win_rate = graphene.Float(description="胜率")
    
    # 关联
    strategy = graphene.Field(StrategyType, description="所属策略")
    trades = graphene.List(lambda: TradeType, description="交易记录")
    
    # 时间戳
    created_at = graphene.DateTime(description="创建时间")


class TradeType(graphene.ObjectType):
    """交易记录类型"""
    
    class Meta:
        description = "交易记录"
    
    date = graphene.DateTime(description="交易日期")
    fund_code = graphene.String(description="基金代码")
    action = graphene.String(description="操作类型")
    shares = graphene.Float(description="交易份额")
    price = graphene.Float(description="交易价格")
    amount = graphene.Float(description="交易金额")


class HoldingType(graphene.ObjectType):
    """持仓类型"""
    
    class Meta:
        description = "基金持仓"
    
    fund_code = graphene.String(description="基金代码")
    fund_name = graphene.String(description="基金名称")
    
    # 持仓信息
    shares = graphene.Float(description="持有份额")
    cost_price = graphene.Float(description="成本价")
    cost_amount = graphene.Float(description="成本金额")
    
    # 实时数据
    current_nav = graphene.Float(description="当前净值")
    current_value = graphene.Float(description="当前市值")
    
    # 盈亏
    profit_loss = graphene.Float(description="盈亏金额")
    profit_loss_percent = graphene.Float(description="盈亏比例")
    
    # 日涨跌
    daily_return = graphene.Float(description="日涨跌幅")
    daily_profit = graphene.Float(description="日盈亏")


class PortfolioType(graphene.ObjectType):
    """投资组合类型"""
    
    class Meta:
        description = "用户投资组合"
    
    user_id = graphene.String(description="用户ID")
    
    # 汇总信息
    total_cost = graphene.Float(description="总成本")
    total_value = graphene.Float(description="总市值")
    total_profit_loss = graphene.Float(description="总盈亏")
    total_return = graphene.Float(description="总收益率")
    
    # 日盈亏
    daily_profit = graphene.Float(description="当日盈亏")
    daily_return = graphene.Float(description="当日收益率")
    
    # 持仓列表
    holdings = graphene.List(HoldingType, description="持仓列表")
    
    # 配置
    rebalance_freq = graphene.String(description="再平衡频率")
    risk_level = graphene.String(description="风险等级")


class AnalysisResultType(graphene.ObjectType):
    """分析结果类型"""
    
    class Meta:
        description = "基金分析结果"
    
    fund_code = graphene.String(description="基金代码")
    analysis_type = graphene.String(description="分析类型")
    
    # 分析数据
    score = graphene.Float(description="评分")
    rating = graphene.String(description="评级")
    recommendation = graphene.String(description="推荐建议")
    
    # 详细分析
    pros = graphene.List(graphene.String, description="优点")
    cons = graphene.List(graphene.String, description="缺点")
    
    # 风险分析
    risk_level = graphene.String(description="风险等级")
    risk_factors = graphene.List(graphene.String, description="风险因素")
    
    # 时间戳
    analyzed_at = graphene.DateTime(description="分析时间")


class PageInfo(graphene.ObjectType):
    """分页信息"""
    
    class Meta:
        description = "分页信息"
    
    has_next_page = graphene.Boolean(description="是否有下一页")
    has_previous_page = graphene.Boolean(description="是否有上一页")
    start_cursor = graphene.String(description="起始游标")
    end_cursor = graphene.String(description="结束游标")
    total_count = graphene.Int(description="总数量")


class FundConnection(relay.Connection):
    """基金连接类型（用于分页）"""
    
    class Meta:
        node = FundType
    
    total_count = graphene.Int()
    
    def resolve_total_count(self, info):
        return self.length


class BacktestConnection(relay.Connection):
    """回测结果连接类型（用于分页）"""
    
    class Meta:
        node = BacktestResultType
    
    total_count = graphene.Int()
    
    def resolve_total_count(self, info):
        return self.length
