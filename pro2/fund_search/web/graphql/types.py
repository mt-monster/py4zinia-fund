#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GraphQL 类型定义
定义基金分析平台的所有GraphQL对象类型
"""

import graphene
from graphene import relay
from datetime import datetime
from typing import Optional


class FundType(graphene.ObjectType):
    """
    基金类型
    基金基本信息和实时数据
    """
    class Meta:
        interfaces = (relay.Node,)
        description = "基金基本信息"
    
    # 基本信息
    fund_code = graphene.String(required=True, description="基金代码")
    fund_name = graphene.String(description="基金名称")
    fund_type = graphene.String(description="基金类型")
    fund_type_cn = graphene.String(description="基金类型中文名")
    
    # 管理信息
    manager = graphene.String(description="基金经理")
    company = graphene.String(description="基金公司")
    establishment_date = graphene.Date(description="成立日期")
    
    # 实时数据
    current_nav = graphene.Float(description="当前净值")
    yesterday_nav = graphene.Float(description="昨日净值")
    daily_return = graphene.Float(description="日涨跌幅(%)")
    estimate_nav = graphene.Float(description="估算净值")
    estimate_return = graphene.Float(description="估算涨跌幅(%)")
    
    # 更新时间
    update_time = graphene.DateTime(description="数据更新时间")
    data_source = graphene.String(description="数据来源")
    
    # 扩展字段
    def resolve_fund_type_cn(self, info):
        """获取基金类型中文名"""
        type_mapping = {
            'equity': '股票型',
            'bond': '债券型',
            'hybrid': '混合型',
            'money': '货币型',
            'index': '指数型',
            'qdii': 'QDII',
            'fof': 'FOF',
            'etf': 'ETF',
            'lof': 'LOF',
            'unknown': '未知'
        }
        return type_mapping.get(self.fund_type, '未知')


class FundNavType(graphene.ObjectType):
    """
    基金净值类型
    历史净值记录
    """
    class Meta:
        description = "基金历史净值"
    
    date = graphene.Date(required=True, description="日期")
    nav = graphene.Float(description="单位净值")
    accum_nav = graphene.Float(description="累计净值")
    daily_return = graphene.Float(description="日涨跌幅(%)")
    
    # 计算字段
    change = graphene.Float(description="净值变化")
    
    def resolve_change(self, info):
        """计算净值变化"""
        if self.nav and self.daily_return:
            return round(self.nav * self.daily_return / 100, 4)
        return None


class FundPerformanceType(graphene.ObjectType):
    """
    基金绩效类型
    绩效指标和风险指标
    """
    class Meta:
        description = "基金绩效指标"
    
    # 收益率指标
    total_return = graphene.Float(description="总收益率(%)")
    annualized_return = graphene.Float(description="年化收益率(%)")
    ytd_return = graphene.Float(description="年初至今收益率(%)")
    return_1m = graphene.Float(description="近1个月收益率(%)")
    return_3m = graphene.Float(description="近3个月收益率(%)")
    return_6m = graphene.Float(description="近6个月收益率(%)")
    return_1y = graphene.Float(description="近1年收益率(%)")
    return_3y = graphene.Float(description="近3年收益率(%)")
    
    # 风险指标
    volatility = graphene.Float(description="波动率(%)")
    max_drawdown = graphene.Float(description="最大回撤(%)")
    var_95 = graphene.Float(description="VaR(95%)")
    beta = graphene.Float(description="Beta系数")
    
    # 复合指标
    sharpe_ratio = graphene.Float(description="夏普比率(默认)")
    sharpe_ratio_ytd = graphene.Float(description="夏普比率(年初至今)")
    sharpe_ratio_1y = graphene.Float(description="夏普比率(近1年)")
    sharpe_ratio_all = graphene.Float(description="夏普比率(成立以来)")
    sortino_ratio = graphene.Float(description="索提诺比率")
    calmar_ratio = graphene.Float(description="卡玛比率")
    
    # 赢亏指标
    win_rate = graphene.Float(description="胜率(%)")
    profit_loss_ratio = graphene.Float(description="盈亏比")
    
    # 综合评分
    composite_score = graphene.Float(description="综合评分(0-1)")
    
    # 日期
    analysis_date = graphene.Date(description="分析日期")


class UserHoldingType(graphene.ObjectType):
    """
    用户持仓类型
    用户持有的基金和盈亏信息
    """
    class Meta:
        interfaces = (relay.Node,)
        description = "用户基金持仓"
    
    # 基本信息
    id = graphene.ID(required=True, description="持仓ID")
    user_id = graphene.String(required=True, description="用户ID")
    fund_code = graphene.String(required=True, description="基金代码")
    fund_name = graphene.String(description="基金名称")
    fund_type = graphene.String(description="基金类型")
    
    # 持仓信息
    holding_shares = graphene.Float(description="持有份额")
    cost_price = graphene.Float(description="成本价格")
    holding_amount = graphene.Float(description="持有金额")
    buy_date = graphene.Date(description="购买日期")
    notes = graphene.String(description="备注")
    
    # 实时数据
    current_nav = graphene.Float(description="当前净值")
    current_value = graphene.Float(description="当前市值")
    today_return = graphene.Float(description="今日涨跌幅(%)")
    yesterday_return = graphene.Float(description="昨日涨跌幅(%)")
    
    # 盈亏计算
    holding_profit = graphene.Float(description="持有盈亏")
    holding_profit_rate = graphene.Float(description="持有盈亏率(%)")
    today_profit = graphene.Float(description="今日盈亏")
    yesterday_profit = graphene.Float(description="昨日盈亏")
    
    # 昨日数据时效性标记
    yesterday_return_date = graphene.Date(description="昨日收益率对应日期")
    yesterday_return_days_diff = graphene.Int(description="昨日收益率日期差(T-1=1)")
    yesterday_return_is_stale = graphene.Boolean(description="昨日收益率是否为延迟数据")
    
    # 绩效指标
    annualized_return = graphene.Float(description="年化收益率(%)")
    max_drawdown = graphene.Float(description="最大回撤(%)")
    sharpe_ratio = graphene.Float(description="夏普比率")
    sharpe_ratio_ytd = graphene.Float(description="夏普比率(年初至今)")
    sharpe_ratio_1y = graphene.Float(description="夏普比率(近1年)")
    sharpe_ratio_all = graphene.Float(description="夏普比率(成立以来)")
    volatility = graphene.Float(description="波动率(%)")
    calmar_ratio = graphene.Float(description="卡玛比率")
    sortino_ratio = graphene.Float(description="索提诺比率")
    composite_score = graphene.Float(description="综合评分")
    
    # 时间戳
    created_at = graphene.DateTime(description="创建时间")
    updated_at = graphene.DateTime(description="更新时间")
    
    # 关联基金详情
    fund = graphene.Field(FundType, description="基金详情")
    
    def resolve_fund(self, info):
        """获取关联的基金信息"""
        # 这里可以从上下文获取fund_data_service来查询
        context = info.context
        if hasattr(context, 'fund_data_service'):
            fund_info = context.fund_data_service.get_fund_basic_info(self.fund_code)
            if fund_info:
                return FundType(
                    fund_code=self.fund_code,
                    fund_name=fund_info.get('fund_name', self.fund_name),
                    fund_type=fund_info.get('fund_type', self.fund_type),
                    current_nav=self.current_nav,
                    yesterday_nav=None,
                    daily_return=self.today_return,
                    update_time=datetime.now()
                )
        return None


class BacktestTradeType(graphene.ObjectType):
    """
    回测交易记录类型
    """
    class Meta:
        description = "回测交易记录"
    
    date = graphene.Date(required=True, description="交易日期")
    action = graphene.String(description="交易动作(buy/sell/hold)")
    nav = graphene.Float(description="当日净值")
    shares = graphene.Float(description="交易份额")
    amount = graphene.Float(description="交易金额")
    cash = graphene.Float(description="剩余现金")
    total_value = graphene.Float(description="总资产")
    strategy = graphene.String(description="策略标签")


class BacktestResultType(graphene.ObjectType):
    """
    回测结果类型
    回测结果包含绩效指标和交易历史
    """
    class Meta:
        interfaces = (relay.Node,)
        description = "回测结果"
    
    # 基本信息
    id = graphene.ID(required=True, description="回测ID")
    fund_code = graphene.String(required=True, description="基金代码")
    fund_name = graphene.String(description="基金名称")
    
    # 回测参数
    start_date = graphene.Date(description="开始日期")
    end_date = graphene.Date(description="结束日期")
    base_amount = graphene.Float(description="基准定投金额")
    initial_cash = graphene.Float(description="初始现金")
    
    # 策略信息
    strategy_id = graphene.String(description="使用的策略ID")
    strategy_name = graphene.String(description="策略名称")
    
    # 回测结果 - 策略
    total_return_strategy = graphene.Float(description="策略总收益率(%)")
    annualized_return_strategy = graphene.Float(description="策略年化收益率(%)")
    max_drawdown_strategy = graphene.Float(description="策略最大回撤(%)")
    sharpe_ratio_strategy = graphene.Float(description="策略夏普比率")
    volatility_strategy = graphene.Float(description="策略波动率(%)")
    win_rate_strategy = graphene.Float(description="策略胜率(%)")
    sortino_ratio_strategy = graphene.Float(description="策略索提诺比率")
    calmar_ratio_strategy = graphene.Float(description="策略卡玛比率")
    alpha_strategy = graphene.Float(description="策略Alpha")
    beta_strategy = graphene.Float(description="策略Beta")
    
    # 回测结果 - 基准
    total_return_benchmark = graphene.Float(description="基准总收益率(%)")
    annualized_return_benchmark = graphene.Float(description="基准年化收益率(%)")
    max_drawdown_benchmark = graphene.Float(description="基准最大回撤(%)")
    sharpe_ratio_benchmark = graphene.Float(description="基准夏普比率")
    volatility_benchmark = graphene.Float(description="基准波动率(%)")
    win_rate_benchmark = graphene.Float(description="基准胜率(%)")
    
    # 超额收益
    excess_return = graphene.Float(description="超额收益率(%)")
    excess_annualized_return = graphene.Float(description="超额年化收益率(%)")
    
    # 期末资产
    final_value_strategy = graphene.Float(description="策略期末资产")
    final_value_benchmark = graphene.Float(description="基准期末资产")
    
    # 交易记录
    trades = graphene.List(BacktestTradeType, description="交易历史")
    total_trades = graphene.Int(description="总交易次数")
    
    # 回测状态
    status = graphene.String(description="回测状态(running/completed/failed)")
    error_message = graphene.String(description="错误信息")
    
    # 时间戳
    created_at = graphene.DateTime(description="创建时间")
    completed_at = graphene.DateTime(description="完成时间")


class StrategyConditionType(graphene.ObjectType):
    """
    策略条件类型
    """
    class Meta:
        description = "策略条件"
    
    today_return_min = graphene.Float(description="今日收益率最小值(%)")
    today_return_max = graphene.Float(description="今日收益率最大值(%)")
    prev_day_return_min = graphene.Float(description="昨日收益率最小值(%)")
    prev_day_return_max = graphene.Float(description="昨日收益率最大值(%)")


class StrategyType(graphene.ObjectType):
    """
    策略类型
    投资策略定义
    """
    class Meta:
        interfaces = (relay.Node,)
        description = "投资策略"
    
    # 基本信息
    id = graphene.ID(required=True, description="策略ID")
    strategy_id = graphene.String(required=True, description="策略标识符")
    name = graphene.String(required=True, description="策略名称")
    description = graphene.String(description="策略描述")
    category = graphene.String(description="策略分类")
    
    # 策略规则
    action = graphene.String(description="操作动作(buy/sell/hold/strong_buy/weak_buy)")
    buy_multiplier = graphene.Float(description="买入倍数")
    redeem_amount = graphene.Float(description="赎回金额")
    label = graphene.String(description="状态标签")
    
    # 条件
    conditions = graphene.List(StrategyConditionType, description="触发条件")
    
    # 优先级
    priority = graphene.Int(description="优先级权重")
    
    # 策略统计
    total_return = graphene.Float(description="历史回测总收益率(%)")
    annualized_return = graphene.Float(description="历史回测年化收益率(%)")
    max_drawdown = graphene.Float(description="历史回测最大回撤(%)")
    sharpe_ratio = graphene.Float(description="历史回测夏普比率")
    win_rate = graphene.Float(description="历史回测胜率(%)")
    trades_count = graphene.Int(description="历史回测交易次数")
    
    # 状态
    is_active = graphene.Boolean(description="是否启用")
    is_builtin = graphene.Boolean(description="是否为内置策略")
    
    # 时间戳
    created_at = graphene.DateTime(description="创建时间")
    updated_at = graphene.DateTime(description="更新时间")
    
    # 创建者
    created_by = graphene.String(description="创建者")


class PageInfoType(graphene.ObjectType):
    """
    分页信息类型
    """
    class Meta:
        description = "分页信息"
    
    has_next_page = graphene.Boolean(description="是否有下一页")
    has_previous_page = graphene.Boolean(description="是否有上一页")
    start_cursor = graphene.String(description="起始游标")
    end_cursor = graphene.String(description="结束游标")
    total_count = graphene.Int(description="总记录数")


class FundConnection(relay.Connection):
    """
    基金连接类型（用于分页）
    """
    class Meta:
        node = FundType
    
    total_count = graphene.Int(description="总记录数")
    
    def resolve_total_count(self, info):
        return self.length


class UserHoldingConnection(relay.Connection):
    """
    用户持仓连接类型（用于分页）
    """
    class Meta:
        node = UserHoldingType
    
    total_count = graphene.Int(description="总记录数")
    portfolio_value = graphene.Float(description="组合总市值")
    total_profit = graphene.Float(description="组合总盈亏")
    
    def resolve_total_count(self, info):
        return self.length


class BacktestResultConnection(relay.Connection):
    """
    回测结果连接类型（用于分页）
    """
    class Meta:
        node = BacktestResultType
    
    total_count = graphene.Int(description="总记录数")


class StrategyConnection(relay.Connection):
    """
    策略连接类型（用于分页）
    """
    class Meta:
        node = StrategyType
    
    total_count = graphene.Int(description="总记录数")


class DashboardSummaryType(graphene.ObjectType):
    """
    仪表盘汇总类型
    """
    class Meta:
        description = "仪表盘汇总数据"
    
    # 持仓汇总
    total_holdings = graphene.Int(description="持仓数量")
    total_portfolio_value = graphene.Float(description="总市值")
    total_cost = graphene.Float(description="总成本")
    total_profit = graphene.Float(description="总盈亏")
    total_profit_rate = graphene.Float(description="总盈亏率(%)")
    
    # 今日盈亏
    today_profit = graphene.Float(description="今日总盈亏")
    today_profit_rate = graphene.Float(description="今日盈亏率(%)")
    
    # 回测汇总
    total_backtests = graphene.Int(description="回测数量")
    completed_backtests = graphene.Int(description="已完成回测数量")
    
    # 策略汇总
    total_strategies = graphene.Int(description="策略数量")
    active_strategies = graphene.Int(description="启用策略数量")


class ErrorType(graphene.ObjectType):
    """
    错误信息类型
    """
    class Meta:
        description = "错误信息"
    
    field = graphene.String(description="错误字段")
    message = graphene.String(description="错误消息")
    code = graphene.String(description="错误代码")


# 导出所有类型
__all__ = [
    'FundType',
    'FundNavType',
    'FundPerformanceType',
    'UserHoldingType',
    'BacktestTradeType',
    'BacktestResultType',
    'StrategyConditionType',
    'StrategyType',
    'PageInfoType',
    'FundConnection',
    'UserHoldingConnection',
    'BacktestResultConnection',
    'StrategyConnection',
    'DashboardSummaryType',
    'ErrorType',
]
