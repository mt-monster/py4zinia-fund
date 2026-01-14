#!/usr/bin/env python
# coding: utf-8

"""
基金分析系统 Web 应用
提供前端界面和 API 接口
"""

import os
import sys
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import pandas as pd
from datetime import datetime, timedelta
import logging

# 添加父目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_config import DATABASE_CONFIG, NOTIFICATION_CONFIG
from enhanced_database import EnhancedDatabaseManager
from enhanced_strategy import EnhancedInvestmentStrategy
from enhanced_fund_data import EnhancedFundData

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# 初始化组件
db_manager = None
strategy_engine = None
fund_data_manager = None

def init_components():
    """初始化系统组件"""
    global db_manager, strategy_engine, fund_data_manager
    try:
        db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        strategy_engine = EnhancedInvestmentStrategy()
        fund_data_manager = EnhancedFundData()
        logger.info("系统组件初始化完成")
    except Exception as e:
        logger.error(f"系统组件初始化失败: {str(e)}")

# ==================== 页面路由 ====================

@app.route('/')
def index():
    """首页"""
    return render_template('fund_index.html')

@app.route('/fund/<fund_code>')
def fund_detail(fund_code):
    """基金详情页"""
    return render_template('fund_detail.html', fund_code=fund_code)

@app.route('/strategy')
def strategy_page():
    """策略分析页"""
    return render_template('strategy.html')


# ==================== API 路由 ====================

@app.route('/api/funds', methods=['GET'])
def get_funds():
    """获取基金列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort_by', 'composite_score')
        sort_order = request.args.get('sort_order', 'desc')
        
        logger.info(f"搜索参数: search={search}, sort_by={sort_by}, page={page}")
        
        date_sql = "SELECT MAX(analysis_date) as max_date FROM fund_analysis_results"
        date_df = db_manager.execute_query(date_sql)
        
        if date_df.empty or date_df.iloc[0]['max_date'] is None:
            return jsonify({'success': True, 'data': [], 'total': 0, 'page': page, 'per_page': per_page})
        
        max_date = date_df.iloc[0]['max_date']
        
        sql = f"""
        SELECT DISTINCT fund_code, fund_name, today_return, prev_day_return,
               annualized_return, sharpe_ratio, max_drawdown, volatility,
               composite_score, status_label, operation_suggestion, analysis_date
        FROM fund_analysis_results WHERE analysis_date = '{max_date}'
        """
        
        if search:
            sql += f" AND (fund_code LIKE '%%{search}%%' OR fund_name LIKE '%%{search}%%')"
        
        valid_sort_fields = ['composite_score', 'today_return', 'annualized_return', 'sharpe_ratio', 'max_drawdown', 'fund_code']
        if sort_by not in valid_sort_fields:
            sort_by = 'composite_score'
        
        sql += f" ORDER BY {sort_by} {'DESC' if sort_order == 'desc' else 'ASC'}"
        
        df = db_manager.execute_query(sql)
        
        if df.empty:
            return jsonify({'success': True, 'data': [], 'total': 0, 'page': page, 'per_page': per_page})
        
        total = len(df)
        start = (page - 1) * per_page
        df_page = df.iloc[start:start + per_page]
        funds = df_page.to_dict('records')
        
        for fund in funds:
            for key in ['today_return', 'prev_day_return', 'annualized_return', 'max_drawdown', 'volatility']:
                if fund.get(key) is not None:
                    fund[key] = round(float(fund[key]) * 100, 2)
            for key in ['sharpe_ratio', 'composite_score']:
                if fund.get(key) is not None:
                    fund[key] = round(float(fund[key]), 4)
        
        return jsonify({'success': True, 'data': funds, 'total': total, 'page': page, 'per_page': per_page})
        
    except Exception as e:
        logger.error(f"获取基金列表失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/fund/<fund_code>', methods=['GET'])
def get_fund_detail(fund_code):
    """获取单个基金详情"""
    try:
        sql = f"SELECT * FROM fund_analysis_results WHERE fund_code = '{fund_code}' ORDER BY analysis_date DESC LIMIT 1"
        df = db_manager.execute_query(sql)
        
        if df.empty:
            return jsonify({'success': False, 'error': '基金不存在'}), 404
        
        fund = df.iloc[0].to_dict()
        
        for key in ['today_return', 'prev_day_return', 'annualized_return', 'max_drawdown', 'volatility', 'win_rate']:
            if fund.get(key) is not None:
                fund[key] = round(float(fund[key]) * 100, 2)
        for key in ['sharpe_ratio', 'calmar_ratio', 'sortino_ratio', 'var_95', 'profit_loss_ratio', 'composite_score']:
            if fund.get(key) is not None:
                fund[key] = round(float(fund[key]), 4)
        
        return jsonify({'success': True, 'data': fund})
        
    except Exception as e:
        logger.error(f"获取基金详情失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/fund/<fund_code>/history', methods=['GET'])
def get_fund_history(fund_code):
    """获取基金历史绩效数据"""
    try:
        days = request.args.get('days', 30, type=int)
        sql = f"""
        SELECT analysis_date, today_return, annualized_return, sharpe_ratio,
               max_drawdown, volatility, composite_score, status_label
        FROM fund_analysis_results WHERE fund_code = '{fund_code}'
        ORDER BY analysis_date DESC LIMIT {days}
        """
        df = db_manager.execute_query(sql)
        
        if df.empty:
            return jsonify({'success': True, 'data': []})
        
        df['analysis_date'] = df['analysis_date'].astype(str)
        
        for key in ['today_return', 'annualized_return', 'max_drawdown', 'volatility']:
            if key in df.columns:
                df[key] = df[key].apply(lambda x: round(float(x) * 100, 2) if pd.notna(x) else None)
        for key in ['sharpe_ratio', 'composite_score']:
            if key in df.columns:
                df[key] = df[key].apply(lambda x: round(float(x), 4) if pd.notna(x) else None)
        
        return jsonify({'success': True, 'data': df.to_dict('records')})
        
    except Exception as e:
        logger.error(f"获取基金历史数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategies', methods=['GET'])
def get_strategies():
    """获取可用的策略列表"""
    try:
        strategies = []
        for name, rule in strategy_engine.strategy_rules.items():
            strategies.append({
                'name': name, 'label': rule['label'], 'description': rule['description'],
                'action': rule['action'], 'redeem_amount': rule['redeem_amount']
            })
        return jsonify({'success': True, 'data': strategies})
    except Exception as e:
        logger.error(f"获取策略列表失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategy/analyze', methods=['POST'])
def analyze_strategy():
    """执行策略分析"""
    try:
        data = request.get_json()
        today_return = data.get('today_return', 0)
        prev_day_return = data.get('prev_day_return', 0)
        performance_metrics = data.get('performance_metrics', None)
        result = strategy_engine.analyze_strategy(today_return, prev_day_return, performance_metrics)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"策略分析失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategy/backtest', methods=['POST'])
def backtest_strategy():
    """策略回测"""
    try:
        data = request.get_json()
        fund_code = data.get('fund_code')
        initial_amount = data.get('initial_amount', 10000)
        days = data.get('days', 90)
        
        if not fund_code:
            return jsonify({'success': False, 'error': '请输入基金代码'})
        
        sql = f"""
        SELECT analysis_date, today_return, prev_day_return, status_label, 
               operation_suggestion, buy_multiplier, redeem_amount
        FROM fund_analysis_results WHERE fund_code = '{fund_code}'
        ORDER BY analysis_date DESC LIMIT {days}
        """
        df = db_manager.execute_query(sql)
        
        if df.empty:
            return jsonify({'success': False, 'error': f'没有找到基金 {fund_code} 的历史数据'})
        
        df = df.sort_values('analysis_date', ascending=True)
        balance = initial_amount
        holdings = 0
        trades = []
        
        for _, row in df.iterrows():
            today_return = float(row['today_return']) if pd.notna(row['today_return']) else 0
            buy_multiplier = float(row['buy_multiplier']) if pd.notna(row['buy_multiplier']) else 0
            redeem_amount = float(row['redeem_amount']) if pd.notna(row['redeem_amount']) else 0
            
            if buy_multiplier > 0:
                buy_amount = 100 * buy_multiplier
                if balance >= buy_amount:
                    balance -= buy_amount
                    holdings += buy_amount
                    trades.append({'date': str(row['analysis_date']), 'action': 'buy', 'amount': buy_amount,
                                   'balance': round(balance, 2), 'holdings': round(holdings, 2)})
            
            if redeem_amount > 0 and holdings >= redeem_amount:
                holdings -= redeem_amount
                balance += redeem_amount
                trades.append({'date': str(row['analysis_date']), 'action': 'sell', 'amount': redeem_amount,
                               'balance': round(balance, 2), 'holdings': round(holdings, 2)})
            
            holdings *= (1 + today_return)
        
        total_value = balance + holdings
        total_return = (total_value - initial_amount) / initial_amount * 100
        
        return jsonify({
            'success': True,
            'data': {
                'fund_code': fund_code, 'initial_amount': initial_amount,
                'final_balance': round(balance, 2), 'final_holdings': round(holdings, 2),
                'total_value': round(total_value, 2), 'total_return': round(total_return, 2),
                'trades_count': len(trades), 'trades': trades, 'backtest_days': days, 'data_count': len(df)
            }
        })
    except Exception as e:
        logger.error(f"策略回测失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/summary', methods=['GET'])
def get_summary():
    """获取分析汇总"""
    try:
        sql = "SELECT * FROM analysis_summary ORDER BY analysis_date DESC LIMIT 1"
        df = db_manager.execute_query(sql)
        
        if df.empty:
            sql = """
            SELECT COUNT(*) as total_funds,
                   SUM(CASE WHEN buy_multiplier > 0 THEN 1 ELSE 0 END) as buy_signals,
                   SUM(CASE WHEN redeem_amount > 0 THEN 1 ELSE 0 END) as sell_signals,
                   AVG(today_return) as avg_today_return, AVG(composite_score) as avg_composite_score,
                   MAX(analysis_date) as analysis_date
            FROM fund_analysis_results WHERE analysis_date = (SELECT MAX(analysis_date) FROM fund_analysis_results)
            """
            df = db_manager.execute_query(sql)
        
        if df.empty:
            return jsonify({'success': True, 'data': {}})
        
        summary = df.iloc[0].to_dict()
        if summary.get('avg_today_return') is not None:
            summary['avg_today_return'] = round(float(summary['avg_today_return']) * 100, 2)
        if summary.get('avg_composite_score') is not None:
            summary['avg_composite_score'] = round(float(summary['avg_composite_score']), 4)
        
        return jsonify({'success': True, 'data': summary})
    except Exception as e:
        logger.error(f"获取汇总数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analysis/dates', methods=['GET'])
def get_analysis_dates():
    """获取可用的分析日期列表"""
    try:
        sql = "SELECT DISTINCT analysis_date FROM fund_analysis_results ORDER BY analysis_date DESC LIMIT 30"
        df = db_manager.execute_query(sql)
        dates = df['analysis_date'].astype(str).tolist() if not df.empty else []
        return jsonify({'success': True, 'data': dates})
    except Exception as e:
        logger.error(f"获取分析日期失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/funds/by-date/<date>', methods=['GET'])
def get_funds_by_date(date):
    """获取指定日期的基金分析结果"""
    try:
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort_by', 'composite_score')
        sort_order = request.args.get('sort_order', 'desc')
        
        sql = f"SELECT * FROM fund_analysis_results WHERE analysis_date = '{date}'"
        
        if search:
            sql += f" AND (fund_code LIKE '%%{search}%%' OR fund_name LIKE '%%{search}%%')"
        
        valid_sort_fields = ['composite_score', 'today_return', 'annualized_return', 'sharpe_ratio', 'max_drawdown', 'fund_code']
        if sort_by not in valid_sort_fields:
            sort_by = 'composite_score'
        
        sql += f" ORDER BY {sort_by} {'DESC' if sort_order == 'desc' else 'ASC'}"
        
        df = db_manager.execute_query(sql)
        
        if df.empty:
            return jsonify({'success': True, 'data': [], 'total': 0})
        
        funds = df.to_dict('records')
        
        for fund in funds:
            for key in ['today_return', 'prev_day_return', 'annualized_return', 'max_drawdown', 'volatility', 'win_rate']:
                if fund.get(key) is not None:
                    fund[key] = round(float(fund[key]) * 100, 2)
            for key in ['sharpe_ratio', 'calmar_ratio', 'sortino_ratio', 'var_95', 'profit_loss_ratio', 'composite_score']:
                if fund.get(key) is not None:
                    fund[key] = round(float(fund[key]), 4)
        
        return jsonify({'success': True, 'data': funds, 'total': len(funds)})
    except Exception as e:
        logger.error(f"获取指定日期基金数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    init_components()
    app.run(host='0.0.0.0', port=5000, debug=True)
