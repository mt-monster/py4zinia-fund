#!/usr/bin/env python
# coding: utf-8

"""
API文档配置模块
使用Flask-RESTX自动生成Swagger文档
"""

import logging
from flask_restx import Api, Namespace, fields

logger = logging.getLogger(__name__)

api = Api(
    version='1.0',
    title='基金分析系统 API',
    description='提供基金数据分析、回测、策略评估等功能',
    doc='/docs',
    prefix='/api'
)

ns_funds = Namespace('funds', description='基金相关操作')
ns_holdings = Namespace('holdings', description='持仓管理操作')
ns_strategies = Namespace('strategies', description='策略相关操作')
ns_backtest = Namespace('backtest', description='回测相关操作')

api.add_namespace(ns_funds, path='/funds')
api.add_namespace(ns_holdings, path='/holdings')
api.add_namespace(ns_strategies, path='/strategies')
api.add_namespace(ns_backtest, path='/backtest')

fund_model = api.model('Fund', {
    'fund_code': fields.String(required=True, description='基金代码'),
    'fund_name': fields.String(description='基金名称'),
    'today_return': fields.Float(description='今日收益率(%)'),
    'prev_day_return': fields.Float(description='昨日收益率(%)'),
    'annualized_return': fields.Float(description='年化收益率(%)'),
    'sharpe_ratio': fields.Float(description='夏普比率'),
    'max_drawdown': fields.Float(description='最大回撤(%)'),
    'composite_score': fields.Float(description='综合评分'),
    'status_label': fields.String(description='状态标签'),
    'operation_suggestion': fields.String(description='操作建议'),
})

fund_list_model = api.model('FundList', {
    'success': fields.Boolean(description='请求是否成功'),
    'data': fields.List(fields.Nested(fund_model), description='基金列表'),
    'total': fields.Integer(description='总数'),
    'page': fields.Integer(description='当前页码'),
    'per_page': fields.Integer(description='每页数量'),
})

holding_model = api.model('Holding', {
    'fund_code': fields.String(required=True, description='基金代码'),
    'fund_name': fields.String(description='基金名称'),
    'holding_shares': fields.Float(description='持有份额'),
    'cost_price': fields.Float(description='成本价'),
    'holding_amount': fields.Float(description='持有金额'),
    'holding_profit': fields.Float(description='持有盈亏'),
    'holding_profit_rate': fields.Float(description='持有收益率(%)'),
    'today_profit': fields.Float(description='今日盈亏'),
    'today_profit_rate': fields.Float(description='今日收益率(%)'),
})

holding_list_model = api.model('HoldingList', {
    'success': fields.Boolean(description='请求是否成功'),
    'data': fields.List(fields.Nested(holding_model), description='持仓列表'),
    'total': fields.Float(description='总资产'),
    'total_profit': fields.Float(description='总盈亏'),
})

strategy_model = api.model('Strategy', {
    'strategy_id': fields.String(description='策略ID'),
    'strategy_name': fields.String(description='策略名称'),
    'strategy_type': fields.String(description='策略类型'),
    'description': fields.String(description='策略描述'),
    'parameters': fields.Raw(description='策略参数'),
    'performance': fields.Raw(description='策略绩效'),
})

backtest_result_model = api.model('BacktestResult', {
    'success': fields.Boolean(description='回测是否成功'),
    'strategy_name': fields.String(description='策略名称'),
    'start_date': fields.String(description='开始日期'),
    'end_date': fields.String(description='结束日期'),
    'total_return': fields.Float(description='总收益率(%)'),
    'annualized_return': fields.Float(description='年化收益率(%)'),
    'max_drawdown': fields.Float(description='最大回撤(%)'),
    'sharpe_ratio': fields.Float(description='夏普比率'),
    'win_rate': fields.Float(description='胜率(%)'),
    'trade_count': fields.Integer(description='交易次数'),
})

error_model = api.model('Error', {
    'success': fields.Boolean(description='请求是否成功', default=False),
    'error': fields.Raw(description='错误信息', example={
        'code': 'FUND_NOT_FOUND',
        'message': '基金未找到',
        'details': {}
    }),
})

pagination_parser = api.parser()
pagination_parser.add_argument('page', type=int, default=1, help='页码')
pagination_parser.add_argument('per_page', type=int, default=20, help='每页数量')
pagination_parser.add_argument('sort_by', type=str, default='composite_score', help='排序字段')
pagination_parser.add_argument('sort_order', type=str, default='desc', choices=['asc', 'desc'], help='排序方向')

search_parser = api.parser()
search_parser.add_argument('keyword', type=str, required=True, help='搜索关键词')

history_parser = api.parser()
history_parser.add_argument('days', type=int, default=30, help='历史天数')
history_parser.add_argument('period', type=str, choices=['1m', '3m', '6m', '1y', 'ytd', 'all'], help='时间段')


def init_api_docs(app):
    """初始化API文档
    
    Args:
        app: Flask应用实例
    """
    api.init_app(app)
    logger.info("API文档已初始化，访问 /docs 查看")
    
    return api
