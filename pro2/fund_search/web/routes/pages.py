#!/usr/bin/env python
# coding: utf-8

"""
页面路由模块

提供前端页面路由，所有页面路由统一在此模块中注册。
遵循 RESTful 风格命名，使用连字符作为 URL 分隔符。
"""

import logging
from typing import Dict, Callable
from functools import wraps

from flask import Flask, render_template, request

# 设置日志
logger = logging.getLogger(__name__)


# =============================================================================
# 模板名称常量 - 集中管理避免硬编码错误
# =============================================================================

class Templates:
    """模板文件名称常量"""
    DASHBOARD = "dashboard.html"
    TEST_API = "test_api.html"
    FUND_DETAIL = "fund_detail.html"
    FUND_ANALYSIS = "fund_analysis.html"
    STRATEGY = "strategy.html"
    STRATEGY_EDITOR = "strategy_editor.html"
    STRATEGY_TEST = "strategy_test.html"
    TRADE_DETAIL_TEST = "trade_detail_test.html"
    ETF_MARKET = "etf_market.html"
    ETF_DETAIL = "etf_detail.html"
    CORRELATION_ANALYSIS = "correlation_analysis.html"
    INVESTMENT_ADVICE = "investment_advice.html"
    STRATEGY_MANAGEMENT = "strategy_management.html"
    MY_HOLDINGS = "my_holdings.html"
    MY_HOLDINGS_REFACTORED = "my_holdings_refactored.html"
    TEST_HOLDING_RECOGNITION = "test_holding_recognition.html"
    DEMO_HOLDING_RESULT = "demo_holding_result.html"
    HOLDING_NAV = "holding_nav.html"
    PORTFOLIO_ANALYSIS = "portfolio_analysis.html"
    CHART_DEBUG = "chart_debug.html"
    COLOR_TEST = "color_convention_test.html"


# =============================================================================
# 错误处理装饰器
# =============================================================================

def handle_template_errors(func: Callable) -> Callable:
    """
    模板渲染错误处理装饰器
    
    捕获模板渲染过程中的异常，记录日志并返回友好的错误页面。
    
    Args:
        func: 被装饰的视图函数
        
    Returns:
        包装后的函数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"渲染模板失败 [{func.__name__}]: {str(e)}", exc_info=True)
            return render_template(
                "error.html",
                error_title="页面加载失败",
                error_message="抱歉，页面加载时出现错误，请稍后重试。",
                error_detail=str(e) if logger.isEnabledFor(logging.DEBUG) else None
            ), 500
    return wrapper


# =============================================================================
# 路由处理器类
# =============================================================================

class PageRoutes:
    """
    页面路由处理器
    
    统一管理所有前端页面路由，按功能分组组织。
    """
    
    def __init__(self, app: Flask):
        """
        初始化路由处理器
        
        Args:
            app: Flask 应用实例
        """
        self.app = app
        self._register_all_routes()
    
    def _register_all_routes(self) -> None:
        """注册所有路由"""
        self._register_core_routes()
        self._register_fund_routes()
        self._register_strategy_routes()
        self._register_etf_routes()
        self._register_analysis_routes()
        self._register_holding_routes()
        self._register_test_routes()
    
    def _route(self, rule: str, **options) -> Callable:
        """
        路由装饰器工厂
        
        Args:
            rule: URL 规则
            **options: 其他路由选项
            
        Returns:
            装饰器函数
        """
        def decorator(func: Callable) -> Callable:
            @self.app.route(rule, **options)
            @handle_template_errors
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    # =========================================================================
    # 核心页面路由
    # =========================================================================
    
    def _register_core_routes(self) -> None:
        """注册核心页面路由"""
        
        @self._route("/")
        def index() -> str:
            """首页 - 重定向到仪表盘"""
            return render_template(Templates.DASHBOARD)
        
        @self._route("/dashboard")
        def dashboard() -> str:
            """仪表盘页面 - 展示基金数据概览"""
            return render_template(Templates.DASHBOARD)
    
    # =========================================================================
    # 基金相关路由
    # =========================================================================
    
    def _register_fund_routes(self) -> None:
        """注册基金相关页面路由"""
        
        @self._route("/fund/<fund_code>")
        def fund_detail(fund_code: str) -> str:
            """
            基金详情页
            
            Args:
                fund_code: 基金代码
            """
            return render_template(Templates.FUND_DETAIL, fund_code=fund_code)
        
        @self._route("/fund-analysis/<fund_code>")
        def fund_analysis(fund_code: str) -> str:
            """
            基金深度分析页
            
            Args:
                fund_code: 基金代码
            """
            return render_template(Templates.FUND_ANALYSIS, fund_code=fund_code)
    
    # =========================================================================
    # 策略相关路由
    # =========================================================================
    
    def _register_strategy_routes(self) -> None:
        """注册策略相关页面路由"""
        
        @self._route("/strategy")
        def strategy_page() -> str:
            """策略分析页 - 策略回测与分析"""
            return render_template(Templates.STRATEGY)
        
        @self._route("/strategy-editor")
        def strategy_editor_page() -> str:
            """策略编辑器页 - 自定义策略规则"""
            return render_template(Templates.STRATEGY_EDITOR)
    
    # =========================================================================
    # ETF 相关路由
    # =========================================================================
    
    def _register_etf_routes(self) -> None:
        """注册 ETF 相关页面路由"""
        
        @self._route("/etf")
        def etf_page() -> str:
            """ETF 市场页 - ETF 行情展示"""
            return render_template(Templates.ETF_MARKET)
        
        @self._route("/etf/<etf_code>")
        def etf_detail_page(etf_code: str) -> str:
            """
            ETF 详情页
            
            Args:
                etf_code: ETF 代码
            """
            return render_template(Templates.ETF_DETAIL, etf_code=etf_code)
    
    # =========================================================================
    # 分析工具路由
    # =========================================================================
    
    def _register_analysis_routes(self) -> None:
        """注册分析工具页面路由"""
        
        @self._route("/correlation-analysis")
        def correlation_analysis_page() -> str:
            """基金相关性分析页面"""
            return render_template(Templates.CORRELATION_ANALYSIS)
        
        @self._route("/investment-advice")
        def investment_advice_page() -> str:
            """投资建议分析页面"""
            return render_template(Templates.INVESTMENT_ADVICE)
        
        @self._route("/strategy-management")
        def strategy_management_page() -> str:
            """策略管理页面 - 回测验证、参数调优、用户反馈"""
            return render_template(Templates.STRATEGY_MANAGEMENT)
        
        @self._route("/portfolio-analysis")
        def portfolio_analysis() -> str:
            """投资组合分析页面 - 展示净值曲线和绩效指标"""
            return render_template(Templates.PORTFOLIO_ANALYSIS)
    
    # =========================================================================
    # 持仓管理路由
    # =========================================================================
    
    def _register_holding_routes(self) -> None:
        """注册持仓管理页面路由"""
        
        @self._route("/my-holdings")
        def my_holdings() -> str:
            """
            我的持仓页
            
            通过 query 参数 ?v=2 可使用重构版模板
            """
            use_refactored = request.args.get("v") == "2"
            template = (
                Templates.MY_HOLDINGS_REFACTORED 
                if use_refactored 
                else Templates.MY_HOLDINGS
            )
            return render_template(template)
        
        @self._route("/my-holdings-new")
        def my_holdings_new() -> str:
            """我的持仓页 - 重构版"""
            return render_template(Templates.MY_HOLDINGS_REFACTORED)
    
    # =========================================================================
    # 测试与开发路由
    # =========================================================================
    
    def _register_test_routes(self) -> None:
        """注册测试与开发页面路由"""
        
        @self._route("/test")
        def test_api() -> str:
            """API 测试页"""
            return render_template(Templates.TEST_API)
        
        @self._route("/trade-detail-test")
        def trade_detail_test() -> str:
            """交易详情功能测试页"""
            return render_template(Templates.TRADE_DETAIL_TEST)
        
        @self._route("/test-holding-recognition")
        def test_holding_recognition() -> str:
            """基金持仓识别测试页"""
            return render_template(Templates.TEST_HOLDING_RECOGNITION)
        
        @self._route("/demo-holding-result")
        def demo_holding_result() -> str:
            """基金持仓识别结果演示页"""
            return render_template(Templates.DEMO_HOLDING_RESULT)
        
        @self._route("/holding-nav")
        def holding_nav() -> str:
            """基金持仓识别功能导航页"""
            return render_template(Templates.HOLDING_NAV)
        
        @self._route("/strategy-test")
        def strategy_test() -> str:
            """策略测试页"""
            return render_template(Templates.STRATEGY_TEST)
        
        @self._route("/chart-debug")
        def chart_debug() -> str:
            """图表调试页"""
            return render_template(Templates.CHART_DEBUG)
        
        @self._route("/color-test")
        def color_test() -> str:
            """金融颜色规范测试页面"""
            return render_template(Templates.COLOR_TEST)


# =============================================================================
# 模块接口
# =============================================================================

def register_routes(app: Flask, **kwargs) -> None:
    """
    注册页面路由
    
    这是模块的统一入口函数，创建 PageRoutes 实例并注册所有页面路由。
    
    Args:
        app: Flask 应用实例
        **kwargs: 其他依赖项（为了与其他路由模块保持一致）
    """
    logger.info("开始注册页面路由...")
    PageRoutes(app)
    logger.info("页面路由注册完成")
