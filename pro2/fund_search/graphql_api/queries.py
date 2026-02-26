#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GraphQL查询定义

定义所有GraphQL查询操作。
"""

import graphene
from graphene import relay
from graphene.types import datetime
from typing import List, Optional

from .types import (
    FundType, FundConnection, FundPerformanceType,
    StrategyType, BacktestResultType, BacktestConnection,
    PortfolioType, AnalysisResultType, HoldingType
)


class MarketOverviewType(graphene.ObjectType):
    """市场概览类型"""
    
    class Meta:
        description = "市场概览"
    
    total_funds = graphene.Int(description="基金总数")
    total_asset = graphene.Float(description="市场总规模")
    avg_return = graphene.Float(description="平均收益率")
    market_sentiment = graphene.String(description="市场情绪")
    
    def resolve_total_funds(self, info):
        return 10000
    
    def resolve_total_asset(self, info):
        return 250000.0
    
    def resolve_avg_return(self, info):
        return 5.2
    
    def resolve_market_sentiment(self, info):
        return "中性"


class Query(graphene.ObjectType):
    """GraphQL查询根类型"""
    
    # ============ 基金相关查询 ============
    
    fund = graphene.Field(
        FundType,
        code=graphene.String(required=True, description="基金代码"),
        description="根据代码查询基金信息"
    )
    
    funds = relay.ConnectionField(
        FundConnection,
        search=graphene.String(description="搜索关键词"),
        fund_type=graphene.String(description="基金类型过滤"),
        sort_by=graphene.String(default_value="code", description="排序字段"),
        sort_order=graphene.String(default_value="asc", description="排序方向"),
        description="查询基金列表（支持分页）"
    )
    
    fund_performance = graphene.Field(
        FundPerformanceType,
        code=graphene.String(required=True, description="基金代码"),
        period=graphene.String(default_value="1y", description="时间周期"),
        description="查询基金绩效指标"
    )
    
    # ============ 策略相关查询 ============
    
    strategy = graphene.Field(
        StrategyType,
        id=graphene.ID(required=True, description="策略ID"),
        description="根据ID查询策略"
    )
    
    strategies = graphene.List(
        StrategyType,
        user_id=graphene.String(description="用户ID过滤"),
        strategy_type=graphene.String(description="策略类型过滤"),
        description="查询策略列表"
    )
    
    # ============ 回测相关查询 ============
    
    backtest = graphene.Field(
        BacktestResultType,
        id=graphene.ID(required=True, description="回测ID"),
        description="根据ID查询回测结果"
    )
    
    backtests = relay.ConnectionField(
        BacktestConnection,
        user_id=graphene.String(description="用户ID过滤"),
        strategy_id=graphene.String(description="策略ID过滤"),
        status=graphene.String(description="状态过滤"),
        start_date=graphene.Date(description="开始日期过滤"),
        end_date=graphene.Date(description="结束日期过滤"),
        description="查询回测结果列表（支持分页）"
    )
    
    # ============ 持仓相关查询 ============
    
    portfolio = graphene.Field(
        PortfolioType,
        user_id=graphene.String(required=True, description="用户ID"),
        realtime=graphene.Boolean(default_value=True, description="是否获取实时数据"),
        description="查询用户投资组合"
    )
    
    holding = graphene.Field(
        HoldingType,
        user_id=graphene.String(required=True, description="用户ID"),
        fund_code=graphene.String(required=True, description="基金代码"),
        description="查询单个持仓详情"
    )
    
    # ============ 分析相关查询 ============
    
    analysis = graphene.Field(
        AnalysisResultType,
        fund_code=graphene.String(required=True, description="基金代码"),
        analysis_type=graphene.String(default_value="comprehensive", description="分析类型"),
        description="查询基金分析结果"
    )
    
    # ============ 系统相关查询 ============
    
    fund_types = graphene.List(
        graphene.String,
        description="获取所有基金类型"
    )
    
    market_overview = graphene.Field(
        lambda: MarketOverviewType,
        description="市场概览"
    )
    
    # ============ Resolver实现 ============
    
    def resolve_fund(self, info, code: str) -> Optional[FundType]:
        """解析单个基金"""
        try:
            from services.fund_data_preloader import get_preloader
            preloader = get_preloader()
            
            basic_info = preloader.get_fund_basic_info(code)
            if basic_info:
                return FundType(
                    code=code,
                    name=basic_info.get('name'),
                    type=basic_info.get('type'),
                    manager=basic_info.get('manager'),
                    company=basic_info.get('company')
                )
        except Exception as e:
            print(f"获取基金信息失败: {e}")
        return None
    
    def resolve_funds(self, info, **kwargs) -> List[FundType]:
        """解析基金列表"""
        try:
            import akshare as ak
            
            # 获取基金列表
            fund_df = ak.fund_open_fund_daily_em()
            
            # 搜索过滤
            search = kwargs.get('search')
            if search:
                fund_df = fund_df[
                    fund_df['基金代码'].str.contains(search, na=False) |
                    fund_df['基金简称'].str.contains(search, na=False)
                ]
            
            # 类型过滤
            fund_type = kwargs.get('fund_type')
            if fund_type and '类型' in fund_df.columns:
                fund_df = fund_df[fund_df['类型'] == fund_type]
            
            # 排序
            sort_by = kwargs.get('sort_by', 'code')
            sort_order = kwargs.get('sort_order', 'asc')
            
            # 转换为FundType列表
            funds = []
            for _, row in fund_df.head(100).iterrows():
                funds.append(FundType(
                    code=str(row.get('基金代码', '')),
                    name=str(row.get('基金简称', '')),
                    type=str(row.get('类型', ''))
                ))
            
            return funds
            
        except Exception as e:
            print(f"获取基金列表失败: {e}")
            return []
    
    def resolve_fund_performance(self, info, code: str, period: str = '1y') -> Optional[FundPerformanceType]:
        """解析基金绩效"""
        try:
            from services.fund_data_preloader import get_preloader
            preloader = get_preloader()
            
            perf = preloader.get_fund_performance(code)
            if perf:
                return FundPerformanceType(**perf)
        except Exception as e:
            print(f"获取基金绩效失败: {e}")
        return None
    
    def resolve_strategy(self, info, id: str) -> Optional[StrategyType]:
        """解析策略"""
        # 从数据库查询策略
        return None
    
    def resolve_strategies(self, info, user_id: str = None, strategy_type: str = None) -> List[StrategyType]:
        """解析策略列表"""
        return []
    
    def resolve_backtest(self, info, id: str) -> Optional[BacktestResultType]:
        """解析回测结果"""
        try:
            from microservices.backtest_service.service import get_service
            service = get_service()
            
            result = service.get_task_result(id)
            if result:
                task = result.get('task', {})
                summary = result.get('summary', {})
                
                return BacktestResultType(
                    id=id,
                    task_id=task.get('task_id'),
                    start_date=task.get('start_date'),
                    end_date=task.get('end_date'),
                    initial_capital=task.get('initial_capital'),
                    total_return=summary.get('total_return'),
                    max_drawdown=summary.get('max_drawdown')
                )
        except Exception:
            pass
        return None
    
    def resolve_backtests(self, info, **kwargs) -> List[BacktestResultType]:
        """解析回测列表"""
        try:
            from microservices.backtest_service.service import get_service
            service = get_service()
            
            tasks = service.list_tasks(
                user_id=kwargs.get('user_id'),
                status=kwargs.get('status')
            )
            
            backtests = []
            for task in tasks:
                backtests.append(BacktestResultType(
                    id=task.get('task_id'),
                    task_id=task.get('task_id'),
                    start_date=task.get('start_date'),
                    end_date=task.get('end_date'),
                    created_at=task.get('created_at')
                ))
            
            return backtests
            
        except Exception:
            return []
    
    def resolve_portfolio(self, info, user_id: str, realtime: bool = True) -> Optional[PortfolioType]:
        """解析投资组合"""
        try:
            from services.holding_realtime_service import HoldingRealtimeService
            from data_access.enhanced_database import EnhancedDatabaseManager
            from shared.config_manager import config_manager
            
            config = config_manager.get_database_config()
            db_manager = EnhancedDatabaseManager({
                'host': config.host,
                'user': config.user,
                'password': config.password,
                'database': config.database,
                'port': config.port,
                'charset': config.charset
            })
            
            service = HoldingRealtimeService(db_manager)
            holdings_data = service.get_holdings_realtime(user_id)
            
            holdings = []
            for h in holdings_data.get('holdings', []):
                holdings.append(HoldingType(
                    fund_code=h.get('fund_code'),
                    fund_name=h.get('fund_name'),
                    shares=h.get('shares'),
                    cost_price=h.get('cost_price'),
                    current_nav=h.get('current_nav'),
                    current_value=h.get('current_value'),
                    profit_loss=h.get('profit_loss'),
                    profit_loss_percent=h.get('profit_loss_percent')
                ))
            
            return PortfolioType(
                user_id=user_id,
                total_cost=holdings_data.get('total_cost'),
                total_value=holdings_data.get('total_value'),
                total_profit_loss=holdings_data.get('total_profit_loss'),
                total_return=holdings_data.get('total_return'),
                daily_profit=holdings_data.get('daily_profit'),
                daily_return=holdings_data.get('daily_return'),
                holdings=holdings
            )
            
        except Exception as e:
            print(f"获取投资组合失败: {e}")
            return None
    
    def resolve_holding(self, info, user_id: str, fund_code: str) -> Optional[HoldingType]:
        """解析单个持仓"""
        # 复用portfolio的解析逻辑
        portfolio = self.resolve_portfolio(info, user_id)
        if portfolio:
            for h in portfolio.holdings:
                if h.fund_code == fund_code:
                    return h
        return None
    
    def resolve_analysis(self, info, fund_code: str, analysis_type: str = 'comprehensive') -> Optional[AnalysisResultType]:
        """解析分析结果"""
        try:
            from services.fund_analyzer import FundAnalyzer
            
            analyzer = FundAnalyzer()
            result = analyzer.analyze_fund(fund_code)
            
            if result:
                return AnalysisResultType(
                    fund_code=fund_code,
                    analysis_type=analysis_type,
                    score=result.get('score'),
                    rating=result.get('rating'),
                    recommendation=result.get('recommendation'),
                    risk_level=result.get('risk_level')
                )
        except Exception:
            pass
        return None
    
    def resolve_fund_types(self, info) -> List[str]:
        """解析基金类型列表"""
        return ['股票型', '债券型', '混合型', '指数型', 'QDII', '货币型', 'FOF']
    
    def resolve_market_overview(self, info):
        """解析市场概览"""
        return MarketOverviewType()
