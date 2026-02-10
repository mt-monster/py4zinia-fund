#!/usr/bin/env python
# coding: utf-8

"""
页面路由模块
提供前端页面路由
"""

from flask import render_template, request


def register_routes(app):
    """注册页面路由"""

    @app.route('/')
    def index():
        """首页 - 重定向到仪表盘"""
        return render_template('dashboard.html')

    @app.route('/dashboard')
    def dashboard():
        """仪表盘页面"""
        return render_template('dashboard.html')

    @app.route('/test')
    def test_api():
        """API测试页"""
        return render_template('test_api.html')

    @app.route('/fund/<fund_code>')
    def fund_detail(fund_code):
        """基金详情页"""
        return render_template('fund_detail.html', fund_code=fund_code)

    @app.route('/strategy')
    def strategy_page():
        """策略分析页"""
        return render_template('strategy.html')

    @app.route('/trade-detail-test')
    def trade_detail_test():
        """交易详情功能测试页"""
        return render_template('trade_detail_test.html')

    @app.route('/strategy-editor')
    def strategy_editor_page():
        """策略编辑器页"""
        return render_template('strategy_editor.html')

    @app.route('/etf')
    def etf_page():
        """ETF市场页"""
        return render_template('etf_market.html')

    @app.route('/correlation-analysis')
    def correlation_analysis_page():
        """基金相关性分析页面"""
        return render_template('correlation_analysis.html')

    @app.route('/investment-advice')
    def investment_advice_page():
        """投资建议分析页面"""
        return render_template('investment_advice.html')

    @app.route('/etf/<etf_code>')
    def etf_detail_page(etf_code):
        """ETF详情页"""
        return render_template('etf_detail.html', etf_code=etf_code)

    @app.route('/my-holdings')
    @app.route('/my_holdings')
    def my_holdings():
        """我的持仓页"""
        # 通过 query 参数 ?v=2 使用重构版模板
        use_refactored = request.args.get('v') == '2'
        template = 'my_holdings_refactored.html' if use_refactored else 'my_holdings.html'
        return render_template(template)

    @app.route('/my-holdings-new')
    def my_holdings_new():
        """我的持仓页 - 重构版"""
        return render_template('my_holdings_refactored.html')

    @app.route('/test-holding-recognition')
    def test_holding_recognition():
        """基金持仓识别测试页"""
        return render_template('test_holding_recognition.html')

    @app.route('/demo-holding-result')
    def demo_holding_result():
        """基金持仓识别结果演示页"""
        return render_template('demo_holding_result.html')

    @app.route('/holding-nav')
    def holding_nav():
        """基金持仓识别功能导航页"""
        return render_template('holding_nav.html')

    @app.route('/fund-analysis/<fund_code>')
    def fund_analysis(fund_code):
        """基金深度分析页"""
        return render_template('fund_analysis.html', fund_code=fund_code)

    @app.route('/portfolio-analysis')
    def portfolio_analysis():
        """投资组合分析页面 - 展示净值曲线和绩效指标"""
        return render_template('portfolio_analysis.html')

    @app.route('/strategy_test')
    def strategy_test():
        return render_template('strategy_test.html')

    @app.route('/chart_debug')
    def chart_debug():
        return render_template('chart_debug.html')
