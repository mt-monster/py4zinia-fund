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

from shared.enhanced_config import DATABASE_CONFIG, NOTIFICATION_CONFIG
from data_retrieval.enhanced_database import EnhancedDatabaseManager
from backtesting.enhanced_strategy import EnhancedInvestmentStrategy
from backtesting.unified_strategy_engine import UnifiedStrategyEngine
from backtesting.strategy_evaluator import StrategyEvaluator
from data_retrieval.enhanced_fund_data import EnhancedFundData

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# 初始化组件
db_manager = None
strategy_engine = None
unified_strategy_engine = None
strategy_evaluator = None
fund_data_manager = None

def init_components():
    """初始化系统组件"""
    global db_manager, strategy_engine, unified_strategy_engine, strategy_evaluator, fund_data_manager
    try:
        db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        strategy_engine = EnhancedInvestmentStrategy()
        unified_strategy_engine = UnifiedStrategyEngine()
        strategy_evaluator = StrategyEvaluator()
        fund_data_manager = EnhancedFundData()
        logger.info("系统组件初始化完成（含统一策略引擎）")
    except Exception as e:
        logger.error(f"系统组件初始化失败: {str(e)}")

# ==================== 页面路由 ====================

@app.route('/')
def index():
    """首页"""
    return render_template('fund_index.html')

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


# ==================== API 路由 ====================

@app.route('/api/funds', methods=['GET'])
def get_funds():
    """获取基金列表（包含持仓盈亏数据）"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort_by', 'composite_score')
        sort_order = request.args.get('sort_order', 'desc')
        user_id = request.args.get('user_id', 'default_user')
        
        logger.info(f"搜索参数: search={search}, sort_by={sort_by}, page={page}")
        
        date_sql = "SELECT MAX(analysis_date) as max_date FROM fund_analysis_results"
        date_df = db_manager.execute_query(date_sql)
        
        if date_df.empty or date_df.iloc[0]['max_date'] is None:
            return jsonify({'success': True, 'data': [], 'total': 0, 'page': page, 'per_page': per_page})
        
        max_date = date_df.iloc[0]['max_date']
        
        # 联合查询基金数据和持仓数据
        sql = f"""
        SELECT DISTINCT 
            far.fund_code, far.fund_name, far.today_return, far.yesterday_return, far.prev_day_return,
            far.annualized_return, far.sharpe_ratio, far.max_drawdown, far.volatility,
            far.composite_score, far.status_label, far.operation_suggestion, far.analysis_date,
            far.current_estimate as current_nav, far.yesterday_nav as previous_nav,
            h.holding_shares, h.cost_price, h.holding_amount, h.buy_date
        FROM fund_analysis_results far
        LEFT JOIN user_holdings h ON far.fund_code = h.fund_code AND h.user_id = 'default_user'
        WHERE far.analysis_date = '{max_date}'
        """
        
        if search:
            sql += f" AND (far.fund_code LIKE '%{search}%' OR far.fund_name LIKE '%{search}%')"
        
        # 如果不是持仓相关字段，使用数据库排序
        if sort_by not in ['today_profit_rate', 'holding_profit_rate', 'holding_amount']:
            valid_sort_fields = ['composite_score', 'today_return', 'yesterday_return', 'annualized_return', 
                                'sharpe_ratio', 'max_drawdown', 'fund_code']
            if sort_by in valid_sort_fields:
                sql += f" ORDER BY far.{sort_by} {'DESC' if sort_order == 'desc' else 'ASC'}"
        
        df = db_manager.execute_query(sql)
        
        if df.empty:
            return jsonify({'success': True, 'data': [], 'total': 0, 'page': page, 'per_page': per_page})
        
        # 计算盈亏指标
        funds_with_profit = []
        for _, row in df.iterrows():
            fund = row.to_dict()
            
            # 清理NaN值，将其转换为None（JSON兼容）
            for key in fund:
                if pd.isna(fund[key]):
                    fund[key] = None
            
            # 基础数据格式化
            for key in ['annualized_return', 'max_drawdown', 'volatility']:
                if fund.get(key) is not None and pd.notna(fund[key]):
                    fund[key] = round(float(fund[key]) * 100, 2)
            
            for key in ['today_return', 'yesterday_return', 'prev_day_return']:
                if fund.get(key) is not None and pd.notna(fund[key]):
                    fund[key] = round(float(fund[key]), 2)
            
            for key in ['sharpe_ratio', 'composite_score']:
                if fund.get(key) is not None and pd.notna(fund[key]):
                    fund[key] = round(float(fund[key]), 4)
            
            # 计算持仓盈亏
            if pd.notna(fund.get('holding_shares')) and fund.get('holding_shares') is not None:
                holding_shares = float(fund['holding_shares'])
                cost_price = float(fund['cost_price']) if pd.notna(fund.get('cost_price')) else 0
                holding_amount = float(fund['holding_amount']) if pd.notna(fund.get('holding_amount')) else 0
                current_nav = float(fund['current_nav']) if pd.notna(fund.get('current_nav')) else cost_price
                previous_nav = float(fund['previous_nav']) if pd.notna(fund.get('previous_nav')) else cost_price
                
                # 当前市值和昨日市值
                current_value = holding_shares * current_nav
                previous_value = holding_shares * previous_nav
                
                # 持有盈亏
                holding_profit = current_value - holding_amount
                holding_profit_rate = (holding_profit / holding_amount * 100) if holding_amount > 0 else 0
                
                # 当日盈亏
                today_profit = current_value - previous_value
                today_profit_rate = (today_profit / previous_value * 100) if previous_value > 0 else 0
                
                # 累计盈亏
                total_profit = holding_profit
                total_profit_rate = holding_profit_rate
                
                fund['holding_amount'] = round(holding_amount, 2)
                fund['today_profit'] = round(today_profit, 2)
                fund['today_profit_rate'] = round(today_profit_rate, 2)
                fund['holding_profit'] = round(holding_profit, 2)
                fund['holding_profit_rate'] = round(holding_profit_rate, 2)
                fund['total_profit'] = round(total_profit, 2)
                fund['total_profit_rate'] = round(total_profit_rate, 2)
            else:
                # 没有持仓数据
                fund['holding_amount'] = None
                fund['today_profit'] = None
                fund['today_profit_rate'] = None
                fund['holding_profit'] = None
                fund['holding_profit_rate'] = None
                fund['total_profit'] = None
                fund['total_profit_rate'] = None
            
            funds_with_profit.append(fund)
        
        # 排序（如果是持仓相关字段）
        if sort_by in ['today_profit_rate', 'holding_profit_rate', 'holding_amount']:
            funds_with_profit.sort(
                key=lambda x: x.get(sort_by) if x.get(sort_by) is not None else float('-inf'),
                reverse=(sort_order == 'desc')
            )
        
        total = len(funds_with_profit)
        start = (page - 1) * per_page
        funds_page = funds_with_profit[start:start + per_page]
        
        return jsonify({'success': True, 'data': funds_page, 'total': total, 'page': page, 'per_page': per_page})
        
    except Exception as e:
        logger.error(f"获取基金列表失败: {str(e)}")
        import traceback
        traceback.print_exc()
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
        
        # 清理NaN值，将其转换为None（JSON兼容）
        for key in fund:
            if pd.isna(fund[key]):
                fund[key] = None
        
        # today_return 和 prev_day_return 已经是百分比格式，不需要乘100
        for key in ['annualized_return', 'max_drawdown', 'volatility', 'win_rate']:
            if fund.get(key) is not None:
                fund[key] = round(float(fund[key]) * 100, 2)
        # 单独处理已经是百分比格式的字段
        for key in ['today_return', 'yesterday_return', 'prev_day_return']:
            if fund.get(key) is not None:
                fund[key] = round(float(fund[key]), 2)
        for key in ['sharpe_ratio', 'calmar_ratio', 'sortino_ratio', 'var_95', 'profit_loss_ratio', 'composite_score']:
            if fund.get(key) is not None:
                fund[key] = round(float(fund[key]), 4)
        
        return jsonify({'success': True, 'data': fund})
        
    except Exception as e:
        logger.error(f"获取基金详情失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/fund/<fund_code>/history', methods=['GET'])
def get_fund_history(fund_code):
    """获取基金历史绩效数据
    
    支持的时间维度:
    - days: 天数 (7, 30, 90, 180, 365)
    - period: 时间段 ('1m'=近一月, '3m'=近三月, '6m'=近半年, '1y'=近一年, 'ytd'=今年来)
    """
    try:
        # 支持两种参数方式
        period = request.args.get('period', '')
        days = request.args.get('days', 30, type=int)
        
        # 根据period计算days
        from datetime import datetime, timedelta
        today = datetime.now()
        
        if period == '1m':
            days = 30
        elif period == '3m':
            days = 90
        elif period == '6m':
            days = 180
        elif period == '1y':
            days = 365
        elif period == 'ytd':
            # 今年来：从1月1日到今天
            year_start = datetime(today.year, 1, 1)
            days = (today - year_start).days + 1
        elif period == 'all':
            # 成立以来：获取所有数据
            days = 9999
        
        # 尝试从AKShare获取实时净值数据
        try:
            hist_data = fund_data_manager.get_historical_data(fund_code, days=days)
            if hist_data is not None and not hist_data.empty:
                # 清理NaN值
                hist_data = hist_data.dropna(subset=['nav'])
                if not hist_data.empty:
                    # 转换日期格式
                    hist_data['date'] = hist_data['date'].dt.strftime('%Y-%m-%d')
                    # 确保nav是数值类型
                    hist_data['nav'] = hist_data['nav'].astype(float)
                    result_data = hist_data[['date', 'nav']].tail(days).to_dict('records')
                    # 清理可能的NaN值
                    for item in result_data:
                        for key in item:
                            if pd.isna(item[key]):
                                item[key] = None
                    return jsonify({'success': True, 'data': result_data, 'source': 'akshare'})
        except Exception as e:
            logger.warning(f"从AKShare获取历史数据失败: {str(e)}, 尝试从数据库获取")
        
        # 备用方案：从数据库获取
        sql = f"""
        SELECT analysis_date as date, today_return, annualized_return, sharpe_ratio,
               max_drawdown, volatility, composite_score, status_label, 
               COALESCE(current_estimate, yesterday_nav) as nav
        FROM fund_analysis_results WHERE fund_code = '{fund_code}'
        ORDER BY analysis_date DESC LIMIT {days}
        """
        df = db_manager.execute_query(sql)
        
        if df.empty:
            return jsonify({'success': True, 'data': [], 'source': 'database'})
        
        df['date'] = df['date'].astype(str)
        
        # today_return 和 prev_day_return 已经是百分比格式，不需要乘100
        for key in ['annualized_return', 'max_drawdown', 'volatility']:
            if key in df.columns:
                df[key] = df[key].apply(lambda x: round(float(x) * 100, 2) if pd.notna(x) else None)
        # 单独处理已经是百分比格式的字段
        for key in ['today_return']:
            if key in df.columns:
                df[key] = df[key].apply(lambda x: round(float(x), 2) if pd.notna(x) else None)
        for key in ['sharpe_ratio', 'composite_score']:
            if key in df.columns:
                df[key] = df[key].apply(lambda x: round(float(x), 4) if pd.notna(x) else None)
        
        # 清理所有剩余的NaN值
        df = df.where(pd.notna(df), None)
        
        return jsonify({'success': True, 'data': df.to_dict('records'), 'source': 'database'})
        
    except Exception as e:
        logger.error(f"获取基金历史数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/fund/<fund_code>/holdings', methods=['GET'])
def get_fund_holdings(fund_code):
    """获取基金持仓数据（股票持仓）"""
    try:
        import akshare as ak
        
        # 使用akshare获取基金持仓数据
        # fund_portfolio_hold_em: 天天基金网-基金档案-投资组合-基金持仓
        try:
            holdings_df = ak.fund_portfolio_hold_em(symbol=fund_code, date="2024")
            
            if holdings_df is None or holdings_df.empty:
                # 尝试获取2023年数据
                holdings_df = ak.fund_portfolio_hold_em(symbol=fund_code, date="2023")
            
            if holdings_df is not None and not holdings_df.empty:
                # 只取最新一期的前10大持仓
                # 按季度分组，取最新季度
                if '季度' in holdings_df.columns:
                    latest_quarter = holdings_df['季度'].iloc[0]
                    holdings_df = holdings_df[holdings_df['季度'] == latest_quarter]
                
                holdings = []
                total_ratio = 0
                
                for _, row in holdings_df.head(10).iterrows():
                    stock_code = str(row.get('股票代码', ''))
                    stock_name = str(row.get('股票名称', ''))
                    ratio = row.get('占净值比例', 0)
                    ratio_change = row.get('较上期变化', None)
                    
                    # 清理数据
                    if pd.notna(ratio):
                        ratio = float(ratio)
                        total_ratio += ratio
                    else:
                        ratio = None
                    
                    if pd.notna(ratio_change):
                        ratio_change = float(ratio_change)
                    else:
                        ratio_change = None
                    
                    holdings.append({
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'ratio': round(ratio, 2) if ratio else None,
                        'ratio_change': round(ratio_change, 2) if ratio_change else None,
                        'stock_return': None,  # 暂不获取实时涨幅，避免超时
                        'change_direction': 'up' if ratio_change and ratio_change > 0 else ('down' if ratio_change and ratio_change < 0 else 'new' if ratio_change is None else 'same')
                    })
                
                # 获取更新日期
                update_date = None
                if '季度' in holdings_df.columns:
                    update_date = str(holdings_df['季度'].iloc[0])
                
                return jsonify({
                    'success': True, 
                    'data': {
                        'holdings': holdings,
                        'total_ratio': round(total_ratio, 2),
                        'update_date': update_date
                    }
                })
        except Exception as e:
            logger.warning(f"从akshare获取基金持仓失败: {str(e)}")
        
        return jsonify({'success': True, 'data': {'holdings': [], 'total_ratio': 0, 'update_date': None}})
        
    except Exception as e:
        logger.error(f"获取基金持仓失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/fund/<fund_code>/stage-returns', methods=['GET'])
def get_fund_stage_returns(fund_code):
    """获取基金阶段涨幅数据（与沪深300对比）"""
    try:
        from datetime import datetime, timedelta
        today = datetime.now()
        
        # 定义各阶段的天数
        stages = {
            'week': 7,
            'month': 30,
            'quarter': 90,
            'half_year': 180,
            'year': 365,
            'three_year': 1095
        }
        
        result = {}
        
        # 获取基金历史数据
        try:
            fund_hist = fund_data_manager.get_historical_data(fund_code, days=1100)
            if fund_hist is not None and not fund_hist.empty:
                fund_hist = fund_hist.dropna(subset=['nav'])
                fund_hist = fund_hist.sort_values('date')
                
                if not fund_hist.empty:
                    latest_nav = fund_hist.iloc[-1]['nav']
                    
                    for stage_name, days in stages.items():
                        target_date = today - timedelta(days=days)
                        # 找到最接近目标日期的数据
                        past_data = fund_hist[fund_hist['date'] <= target_date]
                        if not past_data.empty:
                            past_nav = past_data.iloc[-1]['nav']
                            if past_nav and past_nav != 0:
                                stage_return = ((latest_nav - past_nav) / past_nav) * 100
                                result[f'{stage_name}_return'] = round(stage_return, 2)
                            else:
                                result[f'{stage_name}_return'] = None
                        else:
                            result[f'{stage_name}_return'] = None
        except Exception as e:
            logger.warning(f"获取基金阶段涨幅失败: {str(e)}")
        
        # 获取沪深300数据作为对比
        try:
            import akshare as ak
            hs300_hist = ak.index_zh_a_hist(symbol="000300", period="daily", 
                                           start_date=(today - timedelta(days=1100)).strftime('%Y%m%d'),
                                           end_date=today.strftime('%Y%m%d'))
            if hs300_hist is not None and not hs300_hist.empty:
                hs300_hist['date'] = pd.to_datetime(hs300_hist['日期'])
                hs300_hist = hs300_hist.sort_values('date')
                latest_close = hs300_hist.iloc[-1]['收盘']
                
                for stage_name, days in stages.items():
                    target_date = today - timedelta(days=days)
                    past_data = hs300_hist[hs300_hist['date'] <= target_date]
                    if not past_data.empty:
                        past_close = past_data.iloc[-1]['收盘']
                        if past_close and past_close != 0:
                            stage_return = ((latest_close - past_close) / past_close) * 100
                            result[f'hs300_{stage_name}_return'] = round(stage_return, 2)
                        else:
                            result[f'hs300_{stage_name}_return'] = None
                    else:
                        result[f'hs300_{stage_name}_return'] = None
        except Exception as e:
            logger.warning(f"获取沪深300阶段涨幅失败: {str(e)}")
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        logger.error(f"获取阶段涨幅失败: {str(e)}")
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
    """执行策略分析（使用统一策略引擎）"""
    try:
        data = request.get_json()
        today_return = data.get('today_return', 0)
        prev_day_return = data.get('prev_day_return', 0)
        returns_history = data.get('returns_history', None)
        cumulative_pnl = data.get('cumulative_pnl', None)
        performance_metrics = data.get('performance_metrics', None)
        
        # 使用统一策略引擎进行分析
        result = unified_strategy_engine.analyze(
            today_return=today_return,
            prev_day_return=prev_day_return,
            returns_history=returns_history,
            cumulative_pnl=cumulative_pnl,
            performance_metrics=performance_metrics
        )
        
        # 转换为字典格式
        result_dict = unified_strategy_engine.to_dict(result)
        
        return jsonify({'success': True, 'data': result_dict})
    except Exception as e:
        logger.error(f"策略分析失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategy/unified-analyze', methods=['POST'])
def unified_analyze_strategy():
    """统一策略分析（包含止损、趋势、波动率调整）"""
    try:
        data = request.get_json()
        fund_code = data.get('fund_code')
        today_return = data.get('today_return', 0)
        prev_day_return = data.get('prev_day_return', 0)
        cumulative_pnl = data.get('cumulative_pnl', None)
        
        # 获取历史收益率数据
        returns_history = None
        if fund_code:
            try:
                hist_data = fund_data_manager.get_historical_data(fund_code, days=30)
                if hist_data is not None and not hist_data.empty and 'nav' in hist_data.columns:
                    hist_data = hist_data.sort_values('date')
                    navs = hist_data['nav'].values
                    if len(navs) > 1:
                        returns_history = [(navs[i] - navs[i-1]) / navs[i-1] for i in range(1, len(navs))]
            except Exception as e:
                logger.warning(f"获取历史数据失败: {str(e)}")
        
        # 使用统一策略引擎
        result = unified_strategy_engine.analyze(
            today_return=today_return,
            prev_day_return=prev_day_return,
            returns_history=returns_history,
            cumulative_pnl=cumulative_pnl
        )
        
        result_dict = unified_strategy_engine.to_dict(result)
        
        return jsonify({'success': True, 'data': result_dict})
    except Exception as e:
        logger.error(f"统一策略分析失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategy/config', methods=['GET'])
def get_strategy_config():
    """获取策略配置"""
    try:
        config = unified_strategy_engine.config
        return jsonify({
            'success': True,
            'data': {
                'stop_loss': config.get_stop_loss_config(),
                'volatility': config.get_volatility_config(),
                'trend': config.get_trend_config(),
                'risk_metrics': config.get_risk_metrics_config()
            }
        })
    except Exception as e:
        logger.error(f"获取策略配置失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategy/evaluate', methods=['POST'])
def evaluate_strategy():
    """评估策略有效性"""
    try:
        data = request.get_json()
        trades = data.get('trades', [])
        
        if not trades:
            return jsonify({'success': False, 'error': '没有交易数据'}), 400
        
        result = strategy_evaluator.evaluate(trades)
        result_dict = strategy_evaluator.to_dict(result)
        
        # 清理 Infinity 值（JSON 不支持）
        import math
        for key, value in result_dict.items():
            if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
                result_dict[key] = None
        
        return jsonify({'success': True, 'data': result_dict})
    except Exception as e:
        logger.error(f"策略评估失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategy/backtest', methods=['POST'])
def backtest_strategy():
    """策略回测（使用统一策略引擎）"""
    try:
        data = request.get_json()
        fund_code = data.get('fund_code')
        initial_amount = data.get('initial_amount', 10000)
        days = data.get('days', 90)
        base_invest = data.get('base_invest', 100)  # 基准定投金额
        
        if not fund_code:
            return jsonify({'success': False, 'error': '请输入基金代码'})
        
        # 获取历史数据
        sql = f"""
        SELECT analysis_date, today_return, prev_day_return, yesterday_return,
               status_label, operation_suggestion, buy_multiplier, redeem_amount,
               current_estimate as current_nav, yesterday_nav as previous_nav
        FROM fund_analysis_results WHERE fund_code = '{fund_code}'
        ORDER BY analysis_date DESC LIMIT {days}
        """
        df = db_manager.execute_query(sql)
        
        if df.empty:
            return jsonify({'success': False, 'error': f'没有找到基金 {fund_code} 的历史数据'})
        
        df = df.sort_values('analysis_date', ascending=True)
        
        # 准备历史收益率序列
        returns_history = []
        balance = initial_amount
        holdings = 0
        trades = []
        cumulative_pnl = 0.0
        
        for idx, row in df.iterrows():
            today_return = float(row['today_return']) if pd.notna(row['today_return']) else 0
            prev_day_return = float(row['prev_day_return']) if pd.notna(row['prev_day_return']) else 0
            
            # 更新历史收益率
            returns_history.append(today_return / 100)  # 转换为小数
            
            # 计算累计盈亏率
            if holdings > 0:
                cumulative_pnl = (holdings - initial_amount + balance) / initial_amount - 1
            
            # 使用统一策略引擎分析
            result = unified_strategy_engine.analyze(
                today_return=today_return,
                prev_day_return=prev_day_return,
                returns_history=returns_history[-30:] if len(returns_history) > 30 else returns_history,
                cumulative_pnl=cumulative_pnl if holdings > 0 else None
            )
            
            # 检查止损
            if result.stop_loss_triggered:
                if holdings > 0:
                    balance += holdings
                    trades.append({
                        'date': str(row['analysis_date']),
                        'action': 'stop_loss',
                        'amount': holdings,
                        'balance': round(balance, 2),
                        'holdings': 0,
                        'profit': holdings - (initial_amount - balance),
                        'reason': result.stop_loss_label
                    })
                    holdings = 0
                continue
            
            # 执行买入
            buy_multiplier = result.final_buy_multiplier
            if buy_multiplier > 0:
                buy_amount = base_invest * buy_multiplier
                if balance >= buy_amount:
                    balance -= buy_amount
                    holdings += buy_amount
                    trades.append({
                        'date': str(row['analysis_date']),
                        'action': 'buy',
                        'amount': buy_amount,
                        'balance': round(balance, 2),
                        'holdings': round(holdings, 2),
                        'profit': 0,
                        'multiplier': buy_multiplier,
                        'trend': result.trend,
                        'volatility_adj': result.volatility_adjustment
                    })
            
            # 执行赎回
            redeem_amount = result.redeem_amount
            if redeem_amount > 0 and holdings >= redeem_amount:
                holdings -= redeem_amount
                balance += redeem_amount
                trades.append({
                    'date': str(row['analysis_date']),
                    'action': 'sell',
                    'amount': redeem_amount,
                    'balance': round(balance, 2),
                    'holdings': round(holdings, 2),
                    'profit': 0
                })
            
            # 更新持仓价值
            holdings *= (1 + today_return / 100)
        
        # 计算最终结果
        total_value = balance + holdings
        total_return = (total_value - initial_amount) / initial_amount * 100
        
        # 计算交易盈亏
        for i, trade in enumerate(trades):
            if trade['action'] == 'sell' or trade['action'] == 'stop_loss':
                # 简化计算：假设卖出时的盈亏
                trade['profit'] = trade['amount'] * (total_return / 100) / len([t for t in trades if t['action'] in ['sell', 'stop_loss']] or [1])
        
        # 使用策略评估器评估
        evaluation = strategy_evaluator.evaluate(trades)
        evaluation_dict = strategy_evaluator.to_dict(evaluation)
        
        # 清理 Infinity 值（JSON 不支持）
        import math
        for key, value in evaluation_dict.items():
            if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
                evaluation_dict[key] = None
        
        return jsonify({
            'success': True,
            'data': {
                'fund_code': fund_code,
                'initial_amount': initial_amount,
                'final_balance': round(balance, 2),
                'final_holdings': round(holdings, 2),
                'total_value': round(total_value, 2),
                'total_return': round(total_return, 2),
                'trades_count': len(trades),
                'trades': trades,
                'backtest_days': days,
                'data_count': len(df),
                'evaluation': evaluation_dict
            }
        })
    except Exception as e:
        logger.error(f"策略回测失败: {str(e)}")
        import traceback
        traceback.print_exc()
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
        
        # 清理NaN值，将其转换为None（JSON兼容）
        for key in summary:
            if pd.isna(summary[key]):
                summary[key] = None
        
        # avg_today_return已经是百分比格式，不需要乘100
        if summary.get('avg_today_return') is not None:
            summary['avg_today_return'] = round(float(summary['avg_today_return']), 2)
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
        
        valid_sort_fields = ['composite_score', 'today_return', 'yesterday_return', 'annualized_return', 'sharpe_ratio', 'max_drawdown', 'fund_code']
        if sort_by not in valid_sort_fields:
            sort_by = 'composite_score'
        
        sql += f" ORDER BY {sort_by} {'DESC' if sort_order == 'desc' else 'ASC'}"
        
        df = db_manager.execute_query(sql)
        
        if df.empty:
            return jsonify({'success': True, 'data': [], 'total': 0})
        
        funds = df.to_dict('records')
        
        # 清理NaN值，将其转换为None（JSON兼容）
        for fund in funds:
            for key in fund:
                if pd.isna(fund[key]):
                    fund[key] = None
        
        for fund in funds:
            # today_return, prev_day_return, yesterday_return 已经是百分比格式，不需要乘100
            for key in ['today_return', 'prev_day_return', 'yesterday_return']:
                if fund.get(key) is not None:
                    fund[key] = round(float(fund[key]), 2)
            # 其他需要转换为百分比的字段
            for key in ['annualized_return', 'max_drawdown', 'volatility', 'win_rate']:
                if fund.get(key) is not None:
                    fund[key] = round(float(fund[key]) * 100, 2)
            for key in ['sharpe_ratio', 'calmar_ratio', 'sortino_ratio', 'var_95', 'profit_loss_ratio', 'composite_score']:
                if fund.get(key) is not None:
                    fund[key] = round(float(fund[key]), 4)
        
        return jsonify({'success': True, 'data': funds, 'total': len(funds)})
    except Exception as e:
        logger.error(f"获取指定日期基金数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 持仓管理 API ====================

@app.route('/api/holdings', methods=['GET'])
def get_holdings():
    """获取用户持仓列表"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        sql = """
        SELECT h.*, 
               far.today_return, far.yesterday_return,
               far.current_estimate as current_nav,
               far.yesterday_nav as previous_nav
        FROM user_holdings h
        LEFT JOIN fund_analysis_results far ON h.fund_code = far.fund_code
        WHERE h.user_id = :user_id
        AND far.analysis_date = (SELECT MAX(analysis_date) FROM fund_analysis_results WHERE fund_code = h.fund_code)
        ORDER BY h.buy_date DESC
        """
        
        df = db_manager.execute_query(sql, {'user_id': user_id})
        
        if df.empty:
            return jsonify({'success': True, 'data': [], 'total': 0})
        
        holdings = []
        for _, row in df.iterrows():
            # 计算盈亏指标
            holding_shares = float(row['holding_shares']) if pd.notna(row['holding_shares']) else 0
            cost_price = float(row['cost_price']) if pd.notna(row['cost_price']) else 0
            holding_amount = float(row['holding_amount']) if pd.notna(row['holding_amount']) else 0
            current_nav = float(row['current_nav']) if pd.notna(row['current_nav']) else cost_price
            previous_nav = float(row['previous_nav']) if pd.notna(row['previous_nav']) else cost_price
            today_return = float(row['today_return']) if pd.notna(row['today_return']) else 0
            
            # 当前市值
            current_value = holding_shares * current_nav
            # 昨日市值
            previous_value = holding_shares * previous_nav
            
            # 持有盈亏
            holding_profit = current_value - holding_amount
            holding_profit_rate = (holding_profit / holding_amount * 100) if holding_amount > 0 else 0
            
            # 当日盈亏
            today_profit = current_value - previous_value
            today_profit_rate = (today_profit / previous_value * 100) if previous_value > 0 else 0
            
            # 累计盈亏（与持有盈亏相同）
            total_profit = holding_profit
            total_profit_rate = holding_profit_rate
            
            holding = {
                'id': int(row['id']),
                'fund_code': row['fund_code'],
                'fund_name': row['fund_name'],
                'holding_shares': round(holding_shares, 4),
                'cost_price': round(cost_price, 4),
                'holding_amount': round(holding_amount, 2),
                'current_nav': round(current_nav, 4),
                'current_value': round(current_value, 2),
                'buy_date': str(row['buy_date']),
                'notes': row['notes'] if pd.notna(row['notes']) else '',
                # 盈亏指标
                'today_profit': round(today_profit, 2),
                'today_profit_rate': round(today_profit_rate, 2),
                'holding_profit': round(holding_profit, 2),
                'holding_profit_rate': round(holding_profit_rate, 2),
                'total_profit': round(total_profit, 2),
                'total_profit_rate': round(total_profit_rate, 2),
                'today_return': round(today_return, 2)
            }
            holdings.append(holding)
        
        return jsonify({'success': True, 'data': holdings, 'total': len(holdings)})
        
    except Exception as e:
        logger.error(f"获取持仓列表失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/holdings', methods=['POST'])
def add_holding():
    """添加持仓"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default_user')
        fund_code = data.get('fund_code')
        fund_name = data.get('fund_name')
        holding_shares = float(data.get('holding_shares', 0))
        cost_price = float(data.get('cost_price', 0))
        buy_date = data.get('buy_date')
        notes = data.get('notes', '')
        
        # 计算持有金额
        holding_amount = holding_shares * cost_price
        
        sql = """
        INSERT INTO user_holdings 
        (user_id, fund_code, fund_name, holding_shares, cost_price, holding_amount, buy_date, notes)
        VALUES (:user_id, :fund_code, :fund_name, :holding_shares, :cost_price, :holding_amount, :buy_date, :notes)
        """
        
        success = db_manager.execute_sql(sql, {
            'user_id': user_id,
            'fund_code': fund_code,
            'fund_name': fund_name,
            'holding_shares': holding_shares,
            'cost_price': cost_price,
            'holding_amount': holding_amount,
            'buy_date': buy_date,
            'notes': notes
        })
        
        if success:
            return jsonify({'success': True, 'message': '持仓添加成功'})
        else:
            return jsonify({'success': False, 'error': '持仓添加失败'}), 500
            
    except Exception as e:
        logger.error(f"添加持仓失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/holdings/<fund_code>', methods=['PUT'])
def update_holding(fund_code):
    """更新持仓"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default_user')
        
        # 构建更新字段
        update_fields = []
        params = {'user_id': user_id, 'fund_code': fund_code}
        
        if 'fund_name' in data:
            update_fields.append('fund_name = :fund_name')
            params['fund_name'] = data['fund_name']
        
        if 'holding_shares' in data:
            update_fields.append('holding_shares = :holding_shares')
            params['holding_shares'] = float(data['holding_shares'])
        
        if 'cost_price' in data:
            update_fields.append('cost_price = :cost_price')
            params['cost_price'] = float(data['cost_price'])
        
        # 重新计算持有金额
        if 'holding_shares' in data or 'cost_price' in data:
            # 获取当前值
            sql_get = "SELECT holding_shares, cost_price FROM user_holdings WHERE user_id = :user_id AND fund_code = :fund_code"
            df = db_manager.execute_query(sql_get, {'user_id': user_id, 'fund_code': fund_code})
            if not df.empty:
                current_shares = params.get('holding_shares', float(df.iloc[0]['holding_shares']))
                current_price = params.get('cost_price', float(df.iloc[0]['cost_price']))
                params['holding_amount'] = current_shares * current_price
                update_fields.append('holding_amount = :holding_amount')
        
        if 'buy_date' in data:
            update_fields.append('buy_date = :buy_date')
            params['buy_date'] = data['buy_date']
        
        if 'notes' in data:
            update_fields.append('notes = :notes')
            params['notes'] = data['notes']
        
        if not update_fields:
            return jsonify({'success': False, 'error': '没有要更新的字段'}), 400
        
        sql = f"""
        UPDATE user_holdings 
        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = :user_id AND fund_code = :fund_code
        """
        
        success = db_manager.execute_sql(sql, params)
        
        if success:
            return jsonify({'success': True, 'message': '持仓更新成功'})
        else:
            return jsonify({'success': False, 'error': '持仓更新失败'}), 500
            
    except Exception as e:
        logger.error(f"更新持仓失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/holdings/<fund_code>', methods=['DELETE'])
def delete_holding(fund_code):
    """删除持仓"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        sql = "DELETE FROM user_holdings WHERE user_id = :user_id AND fund_code = :fund_code"
        success = db_manager.execute_sql(sql, {'user_id': user_id, 'fund_code': fund_code})
        
        if success:
            return jsonify({'success': True, 'message': '持仓删除成功'})
        else:
            return jsonify({'success': False, 'error': '持仓删除失败'}), 500
            
    except Exception as e:
        logger.error(f"删除持仓失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    init_components()
    app.run(host='0.0.0.0', port=5000, debug=True)
