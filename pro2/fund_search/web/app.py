#!/usr/bin/env python
# coding: utf-8

"""
基金分析系统 Web 应用
提供前端界面和 API 接口
"""

import os
import sys
import json
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
from data_retrieval.fund_screenshot_ocr import recognize_fund_screenshot, validate_recognized_fund

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
        logger.info(f"db_manager: {db_manager is not None}")
        logger.info(f"strategy_engine: {strategy_engine is not None}")
        logger.info(f"fund_data_manager: {fund_data_manager is not None}")
    except Exception as e:
        logger.error(f"系统组件初始化失败: {str(e)}", exc_info=True)
        raise

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

@app.route('/etf/<etf_code>')
def etf_detail_page(etf_code):
    """ETF详情页"""
    return render_template('etf_detail.html', etf_code=etf_code)

@app.route('/my-holdings')
@app.route('/my_holdings')
def my_holdings():
    """我的持仓页"""
    return render_template('my_holdings.html')

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
            far.fund_code, far.fund_name, far.today_return, far.prev_day_return,
            far.annualized_return, far.sharpe_ratio, far.sharpe_ratio_ytd, far.sharpe_ratio_1y, far.sharpe_ratio_all,
            far.max_drawdown, far.volatility,
            far.composite_score, far.status_label, far.operation_suggestion, far.analysis_date,
            far.current_estimate as current_nav, far.yesterday_nav as previous_nav,
            far.execution_amount, far.buy_multiplier, far.redeem_amount,
            h.holding_shares, h.cost_price, h.holding_amount, h.buy_date
        FROM fund_analysis_results far
        LEFT JOIN user_holdings h ON far.fund_code = h.fund_code AND h.user_id = 'default_user'
        WHERE far.analysis_date = '{max_date}'
        """
        
        if search:
            sql += f" AND (far.fund_code LIKE '%{search}%' OR far.fund_name LIKE '%{search}%')"
        
        # 如果不是持仓相关字段，使用数据库排序
        if sort_by not in ['today_profit_rate', 'holding_profit_rate', 'holding_amount']:
            valid_sort_fields = ['composite_score', 'today_return', 'prev_day_return', 'annualized_return', 
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
            
            for key in ['today_return', 'prev_day_return']:
                if fund.get(key) is not None and pd.notna(fund[key]):
                    fund[key] = round(float(fund[key]), 2)
            
            for key in ['sharpe_ratio', 'sharpe_ratio_ytd', 'sharpe_ratio_1y', 'sharpe_ratio_all', 'composite_score']:
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


@app.route('/api/fund/<fund_code>/info', methods=['GET'])
def get_fund_info(fund_code):
    """获取基金基本信息（包括成立日期等）"""
    try:
        import akshare as ak
        
        # 使用 akshare 获取基金基本信息
        try:
            # fund_individual_basic_info_xq: 雪球-基金-基本信息
            fund_info = ak.fund_individual_basic_info_xq(symbol=fund_code)
            
            if fund_info is not None and not fund_info.empty:
                info_dict = {}
                for _, row in fund_info.iterrows():
                    item = row.get('item', '')
                    value = row.get('value', '')
                    # 处理NaN值和NAType
                    if pd.isna(value):
                        value = None
                    else:
                        value = str(value).strip()
                    info_dict[item] = value
                
                # 提取成立日期
                inception_date = info_dict.get('成立日期', None)
                fund_manager = info_dict.get('基金经理', None)
                fund_company = info_dict.get('基金公司', None)
                fund_type = info_dict.get('基金类型', None)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'inception_date': inception_date,
                        'fund_manager': fund_manager,
                        'fund_company': fund_company,
                        'fund_type': fund_type,
                        'raw_info': info_dict
                    }
                })
        except Exception as e:
            logger.warning(f"从雪球获取基金信息失败: {str(e)}, 尝试其他数据源")
        
        # 备用方案：从天天基金网获取
        try:
            # 使用正确的方法名：fund_open_fund_info_em
            fund_info_em = ak.fund_open_fund_info_em(symbol=fund_code, indicator="基本信息")
            if fund_info_em is not None and not fund_info_em.empty:
                info_dict = {}
                for _, row in fund_info_em.iterrows():
                    item = row.get('项目', '')
                    value = row.get('数值', '')
                    # 处理NaN值
                    if pd.isna(value):
                        value = None
                    else:
                        value = str(value).strip()
                    info_dict[item] = value
                
                inception_date = info_dict.get('成立日期', None)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'inception_date': inception_date,
                        'raw_info': info_dict
                    }
                })
        except Exception as e:
            logger.warning(f"从天天基金网获取基金信息失败: {str(e)}")
        
        return jsonify({'success': False, 'error': '无法获取基金信息'})
        
    except Exception as e:
        logger.error(f"获取基金信息失败: {str(e)}")
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
            return jsonify({'success': False, 'error': '请输入基金代码'}), 400
        
        # Validate parameters according to requirements 10.4
        validation_errors = []
        
        # Validate initial_amount (must be >= 100)
        try:
            initial_amount = float(initial_amount)
            if initial_amount < 100:
                validation_errors.append('初始金额必须大于等于100元')
        except (TypeError, ValueError):
            validation_errors.append('初始金额必须是有效数字')
        
        # Validate base_invest (must be >= 10)
        try:
            base_invest = float(base_invest)
            if base_invest < 10:
                validation_errors.append('基准定投金额必须大于等于10元')
        except (TypeError, ValueError):
            validation_errors.append('基准定投金额必须是有效数字')
        
        # Validate days (must be in [30, 60, 90, 180, 365])
        try:
            days = int(days)
            if days not in [30, 60, 90, 180, 365]:
                validation_errors.append('回测天数必须是30、60、90、180或365天')
        except (TypeError, ValueError):
            validation_errors.append('回测天数必须是有效数字')
        
        # Return validation errors if any
        if validation_errors:
            return jsonify({
                'success': False, 
                'error': '; '.join(validation_errors)
            }), 400
        
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
            yesterday_return = float(row['yesterday_return']) if pd.notna(row['yesterday_return']) else 0
            sharpe_ratio = float(row['sharpe_ratio']) if pd.notna(row['sharpe_ratio']) else 0
            max_drawdown = float(row['max_drawdown']) if pd.notna(row['max_drawdown']) else 0
            volatility = float(row['volatility']) if pd.notna(row['volatility']) else 0
            annualized_return = float(row['annualized_return']) if pd.notna(row['annualized_return']) else 0
            calmar_ratio = float(row['calmar_ratio']) if pd.notna(row['calmar_ratio']) else 0
            sortino_ratio = float(row['sortino_ratio']) if pd.notna(row['sortino_ratio']) else 0
            sharpe_ratio = float(row['sharpe_ratio']) if pd.notna(row['sharpe_ratio']) else 0
            max_drawdown = float(row['max_drawdown']) if pd.notna(row['max_drawdown']) else 0
            volatility = float(row['volatility']) if pd.notna(row['volatility']) else 0
            annualized_return = float(row['annualized_return']) if pd.notna(row['annualized_return']) else 0
            calmar_ratio = float(row['calmar_ratio']) if pd.notna(row['calmar_ratio']) else 0
            sortino_ratio = float(row['sortino_ratio']) if pd.notna(row['sortino_ratio']) else 0
            sharpe_ratio = float(row['sharpe_ratio']) if pd.notna(row['sharpe_ratio']) else 0
            max_drawdown = float(row['max_drawdown']) if pd.notna(row['max_drawdown']) else 0
            volatility = float(row['volatility']) if pd.notna(row['volatility']) else 0
            annualized_return = float(row['annualized_return']) if pd.notna(row['annualized_return']) else 0
            calmar_ratio = float(row['calmar_ratio']) if pd.notna(row['calmar_ratio']) else 0
            sortino_ratio = float(row['sortino_ratio']) if pd.notna(row['sortino_ratio']) else 0
            sharpe_ratio = float(row['sharpe_ratio']) if pd.notna(row['sharpe_ratio']) else 0
            max_drawdown = float(row['max_drawdown']) if pd.notna(row['max_drawdown']) else 0
            volatility = float(row['volatility']) if pd.notna(row['volatility']) else 0
            annualized_return = float(row['annualized_return']) if pd.notna(row['annualized_return']) else 0
            calmar_ratio = float(row['calmar_ratio']) if pd.notna(row['calmar_ratio']) else 0
            sortino_ratio = float(row['sortino_ratio']) if pd.notna(row['sortino_ratio']) else 0
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


def _execute_single_fund_backtest(fund_code, strategy_id, initial_amount, base_invest, days):
    """
    Execute backtest for a single fund.
    
    Returns backtest result dictionary or None if no data found.
    Requirements: 4.1, 4.2, 4.3, 4.4
    """
    try:
        # 导入 AkShare 数据获取模块
        from backtesting.akshare_data_fetcher import fetch_fund_history_with_fallback
        from backtesting.strategy_adapter import get_strategy_adapter
        
        # 获取历史数据（优先数据库，不足时从 AkShare 获取）
        df = fetch_fund_history_with_fallback(fund_code, days, db_manager)
        
        if df.empty:
            logger.warning(f"无法获取基金 {fund_code} 的历史数据")
            return None
        
        logger.info(f"基金 {fund_code} 获取到 {len(df)} 条历史数据，使用策略 {strategy_id} 开始回测...")
        
        df = df.sort_values('analysis_date', ascending=True)
        
        # 检查是否为高级策略（dual_ma, mean_reversion, target_value, grid, enhanced_rule_based）
        strategy_adapter = get_strategy_adapter()
        use_advanced_strategy = strategy_adapter.is_advanced_strategy(strategy_id)
        
        if not use_advanced_strategy:
            logger.warning(f"未知的策略ID: {strategy_id}，将使用默认策略")
            strategy_id = 'enhanced_rule_based'
            use_advanced_strategy = True
        
        logger.info(f"策略类型: 高级策略 - {strategy_id}")
        
        # Initialize backtest variables
        balance = initial_amount
        holdings = 0
        trades = []
        returns_history = []
        cumulative_pnl = 0.0
        
        # 为高级策略准备DataFrame（需要包含nav列）
        if use_advanced_strategy:
            # 创建包含nav列的DataFrame
            backtest_df = df.copy()
            if 'nav' not in backtest_df.columns:
                # 从current_estimate或yesterday_nav计算nav
                if 'current_estimate' in backtest_df.columns:
                    backtest_df['nav'] = backtest_df['current_estimate']
                elif 'yesterday_nav' in backtest_df.columns:
                    backtest_df['nav'] = backtest_df['yesterday_nav']
                else:
                    # 使用today_return反推nav
                    backtest_df['nav'] = 1.0
                    for i in range(1, len(backtest_df)):
                        prev_nav = backtest_df.iloc[i-1]['nav']
                        today_ret = backtest_df.iloc[i]['today_return'] / 100 if pd.notna(backtest_df.iloc[i]['today_return']) else 0
                        backtest_df.iloc[i, backtest_df.columns.get_loc('nav')] = prev_nav * (1 + today_ret)
        
        # Run backtest simulation (Requirement 4.3 - Apply selected strategy rules)
        # 所有策略都使用高级策略实现
        strategy_returns = []  # Track strategy-specific returns for Sharpe ratio calculation
        
        for idx, (df_idx, row) in enumerate(df.iterrows()):
            today_return = float(row['today_return']) if pd.notna(row['today_return']) else 0
            
            # Calculate total portfolio value before applying today's return
            total_value_before = balance + holdings
            
            # Calculate cumulative P&L
            if holdings > 0:
                cumulative_pnl = (holdings - initial_amount + balance) / initial_amount - 1
            
            # 使用高级策略
            try:
                signal = strategy_adapter.generate_signal(
                    strategy_id=strategy_id,
                    history_df=backtest_df,
                    current_index=idx,
                    current_holdings=holdings,
                    cash=balance,
                    base_invest=base_invest
                )
                
                # 执行买入
                if signal.action == 'buy' and signal.buy_multiplier > 0:
                    buy_amount = base_invest * signal.buy_multiplier
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
                            'multiplier': signal.buy_multiplier,
                            'reason': signal.reason,
                            'description': signal.description
                        })
                
                # 执行卖出
                elif signal.action == 'sell' and signal.redeem_amount > 0:
                    # 如果redeem_amount是比例（0-1之间）
                    if 0 < signal.redeem_amount <= 1:
                        sell_amount = holdings * signal.redeem_amount
                    else:
                        sell_amount = min(signal.redeem_amount, holdings)
                    
                    if sell_amount > 0:
                        holdings -= sell_amount
                        balance += sell_amount
                        trades.append({
                            'date': str(row['analysis_date']),
                            'action': 'sell',
                            'amount': sell_amount,
                            'balance': round(balance, 2),
                            'holdings': round(holdings, 2),
                            'profit': 0,
                            'reason': signal.reason,
                            'description': signal.description
                        })
            
            except Exception as e:
                logger.error(f"策略 {strategy_id} 执行失败: {str(e)}")
                # 策略执行失败时，默认持有
                pass
            
            # Update holdings value based on daily return
            holdings *= (1 + today_return / 100)
            
            # Calculate total portfolio value after applying today's return
            total_value_after = balance + holdings
            
            # Calculate daily return for strategy performance
            if total_value_before > 0:
                daily_strategy_return = (total_value_after - total_value_before) / total_value_before
                strategy_returns.append(daily_strategy_return)
        
        # Calculate final results (Requirement 4.4)
        final_value = balance + holdings
        total_return = (final_value - initial_amount) / initial_amount * 100
        
        # Calculate annualized return
        years = days / 365.0
        annualized_return = ((final_value / initial_amount) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        # Calculate max drawdown
        peak = initial_amount
        max_dd = 0
        for trade in trades:
            current_value = trade['balance'] + trade['holdings']
            if current_value > peak:
                peak = current_value
            drawdown = (peak - current_value) / peak * 100 if peak > 0 else 0
            if drawdown > max_dd:
                max_dd = drawdown
        
        # Calculate Sharpe ratio (simplified) - now based on strategy performance
        if len(strategy_returns) > 1:
            import numpy as np
            returns_array = np.array(strategy_returns)
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            sharpe_ratio = (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Evaluate strategy performance (Requirement 4.4)
        evaluation = strategy_evaluator.evaluate(trades)
        evaluation_dict = strategy_evaluator.to_dict(evaluation)
        
        # Clean up Infinity and NaN values
        import math
        for key, value in evaluation_dict.items():
            if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
                evaluation_dict[key] = None
        
        logger.info(f"回测完成: 策略={strategy_id}, 最终价值={final_value:.2f}, 总收益率={total_return:.2f}%, 交易次数={len(trades)}")
        
        # Return complete backtest results
        return {
            'fund_code': fund_code,
            'strategy_id': strategy_id,
            'initial_amount': initial_amount,
            'final_value': round(final_value, 2),
            'total_return': round(total_return, 2),
            'annualized_return': round(annualized_return, 2),
            'max_drawdown': round(max_dd, 2),
            'sharpe_ratio': round(sharpe_ratio, 4),
            'trades_count': len(trades),
            'trades': trades,
            'evaluation': evaluation_dict
        }
    except Exception as e:
        logger.error(f"Single fund backtest failed for {fund_code}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def _execute_multi_fund_backtest(fund_codes, strategy_id, initial_amount, base_invest, days):
    """
    Execute independent backtests for multiple funds and aggregate results.
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
    """
    try:
        # Execute independent backtests for each fund (Requirement 6.2)
        individual_results = []
        failed_funds = []
        
        # Divide initial amount equally among funds
        amount_per_fund = initial_amount / len(fund_codes)
        
        for fund_code in fund_codes:
            result = _execute_single_fund_backtest(
                fund_code, strategy_id, amount_per_fund, base_invest, days
            )
            
            if result is not None:
                individual_results.append(result)
            else:
                failed_funds.append(fund_code)
        
        if not individual_results:
            return jsonify({
                'success': False,
                'error': f'无法获取任何基金的历史数据: {", ".join(failed_funds)}'
            }), 404
        
        # Calculate aggregated portfolio metrics (Requirement 6.3)
        total_final_value = sum(r['final_value'] for r in individual_results)
        total_initial_amount = sum(r['initial_amount'] for r in individual_results)
        
        portfolio_total_return = (total_final_value - total_initial_amount) / total_initial_amount * 100
        
        # Calculate portfolio annualized return
        years = days / 365.0
        portfolio_annualized_return = ((total_final_value / total_initial_amount) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        # Calculate weighted average metrics
        weights = [r['initial_amount'] / total_initial_amount for r in individual_results]
        portfolio_max_drawdown = sum(r['max_drawdown'] * w for r, w in zip(individual_results, weights))
        portfolio_sharpe_ratio = sum(r['sharpe_ratio'] * w for r, w in zip(individual_results, weights))
        
        total_trades = sum(r['trades_count'] for r in individual_results)
        
        # Identify best and worst performing funds (Requirement 6.5)
        best_fund = max(individual_results, key=lambda x: x['total_return'])
        worst_fund = min(individual_results, key=lambda x: x['total_return'])
        
        # Prepare individual fund summary (without full trade history for brevity)
        fund_summaries = []
        for result in individual_results:
            fund_summaries.append({
                'fund_code': result['fund_code'],
                'initial_amount': result['initial_amount'],
                'final_value': result['final_value'],
                'total_return': result['total_return'],
                'annualized_return': result['annualized_return'],
                'max_drawdown': result['max_drawdown'],
                'sharpe_ratio': result['sharpe_ratio'],
                'trades_count': result['trades_count']
            })
        
        # Return both individual and aggregated results (Requirement 6.4, 6.5)
        return jsonify({
            'success': True,
            'data': {
                'mode': 'multi_fund',
                'strategy_id': strategy_id,
                'total_funds': len(individual_results),
                'failed_funds': failed_funds,
                
                # Aggregated portfolio metrics (Requirement 6.3)
                'portfolio': {
                    'initial_amount': round(total_initial_amount, 2),
                    'final_value': round(total_final_value, 2),
                    'total_return': round(portfolio_total_return, 2),
                    'annualized_return': round(portfolio_annualized_return, 2),
                    'max_drawdown': round(portfolio_max_drawdown, 2),
                    'sharpe_ratio': round(portfolio_sharpe_ratio, 4),
                    'total_trades': total_trades
                },
                
                # Best and worst performing funds (Requirement 6.5)
                'best_fund': {
                    'fund_code': best_fund['fund_code'],
                    'total_return': best_fund['total_return'],
                    'final_value': best_fund['final_value']
                },
                'worst_fund': {
                    'fund_code': worst_fund['fund_code'],
                    'total_return': worst_fund['total_return'],
                    'final_value': worst_fund['final_value']
                },
                
                # Individual fund results (Requirement 6.4)
                'individual_funds': fund_summaries,
                'funds': fund_summaries,  # 添加funds键以兼容前端
                
                # Full details for first fund (for UI display)
                'sample_fund_details': individual_results[0] if individual_results else None
            }
        })
        
    except Exception as e:
        logger.error(f"Multi-fund backtest failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategy/backtest-holdings', methods=['POST'])
def backtest_holdings():
    """
    Enhanced backtest API endpoint for user holdings with strategy selection
    
    Accepts fund_codes array, strategy_id, and backtest parameters.
    Integrates with existing backtest engine and applies selected strategy rules.
    Returns complete backtest results with evaluation metrics.
    
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 6.1, 6.2, 6.3, 6.4, 6.5
    """
    try:
        data = request.get_json()
        fund_codes = data.get('fund_codes', [])
        strategy_id = data.get('strategy_id', 'enhanced_rule_based')
        initial_amount = data.get('initial_amount', 10000)
        base_invest = data.get('base_invest', 100)
        days = data.get('days', 90)
        
        # Validate parameters (Requirement 4.5)
        validation_errors = []
        
        # Validate fund_codes
        if not fund_codes or not isinstance(fund_codes, list):
            validation_errors.append('fund_codes必须是非空数组')
        elif len(fund_codes) == 0:
            validation_errors.append('至少需要选择一个基金')
        
        # Validate initial_amount (must be >= 100)
        try:
            initial_amount = float(initial_amount)
            if initial_amount < 100:
                validation_errors.append('初始金额必须大于等于100元')
        except (TypeError, ValueError):
            validation_errors.append('初始金额必须是有效数字')
        
        # Validate base_invest (must be >= 10)
        try:
            base_invest = float(base_invest)
            if base_invest < 10:
                validation_errors.append('基准定投金额必须大于等于10元')
        except (TypeError, ValueError):
            validation_errors.append('基准定投金额必须是有效数字')
        
        # Validate days (must be in [30, 60, 90, 180, 365])
        try:
            days = int(days)
            if days not in [30, 60, 90, 180, 365]:
                validation_errors.append('回测天数必须是30、60、90、180或365天')
        except (TypeError, ValueError):
            validation_errors.append('回测天数必须是有效数字')
        
        # Validate strategy_id
        from backtesting.strategy_report_parser import StrategyReportParser
        report_path = 'pro2/fund_backtest/strategy_results/strategy_comparison_report.md'
        
        try:
            parser = StrategyReportParser(report_path)
            available_strategies = parser.get_all_strategy_ids()
            
            if strategy_id not in available_strategies:
                validation_errors.append(f'无效的策略ID: {strategy_id}，可用策略: {", ".join(available_strategies)}')
        except Exception as e:
            logger.warning(f"无法验证策略ID: {str(e)}")
        
        # Return validation errors if any
        if validation_errors:
            return jsonify({
                'success': False,
                'error': '; '.join(validation_errors)
            }), 400
        
        # Multi-fund backtesting (Requirements 6.1, 6.2, 6.3, 6.4, 6.5)
        if len(fund_codes) > 1:
            return _execute_multi_fund_backtest(
                fund_codes, strategy_id, initial_amount, base_invest, days
            )
        
        # Single fund backtest (Requirement 4.1, 4.2, 4.3)
        fund_code = fund_codes[0]
        result = _execute_single_fund_backtest(
            fund_code, strategy_id, initial_amount, base_invest, days
        )
        
        if result is None:
            return jsonify({
                'success': False,
                'error': f'没有找到基金 {fund_code} 的历史数据'
            }), 404
        
        # Return complete backtest results (Requirement 4.4)
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Enhanced backtest failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategy/compare', methods=['POST'])
def compare_strategies():
    """
    Strategy comparison API endpoint
    
    Accepts a single fund_code and multiple strategy_ids.
    Executes backtests for all selected strategies with identical parameters.
    Returns side-by-side comparison results with best strategy highlighted.
    
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
    """
    try:
        data = request.get_json()
        fund_code = data.get('fund_code')
        strategy_ids = data.get('strategy_ids', [])
        initial_amount = data.get('initial_amount', 10000)
        base_invest = data.get('base_invest', 100)
        days = data.get('days', 90)
        
        # Validate parameters
        validation_errors = []
        
        # Validate fund_code
        if not fund_code:
            validation_errors.append('fund_code是必需的')
        
        # Validate strategy_ids
        if not strategy_ids or not isinstance(strategy_ids, list):
            validation_errors.append('strategy_ids必须是非空数组')
        elif len(strategy_ids) < 2:
            validation_errors.append('至少需要选择两个策略进行比较')
        
        # Validate initial_amount (must be >= 100)
        try:
            initial_amount = float(initial_amount)
            if initial_amount < 100:
                validation_errors.append('初始金额必须大于等于100元')
        except (TypeError, ValueError):
            validation_errors.append('初始金额必须是有效数字')
        
        # Validate base_invest (must be >= 10)
        try:
            base_invest = float(base_invest)
            if base_invest < 10:
                validation_errors.append('基准定投金额必须大于等于10元')
        except (TypeError, ValueError):
            validation_errors.append('基准定投金额必须是有效数字')
        
        # Validate days (must be in [30, 60, 90, 180, 365])
        try:
            days = int(days)
            if days not in [30, 60, 90, 180, 365]:
                validation_errors.append('回测天数必须是30、60、90、180或365天')
        except (TypeError, ValueError):
            validation_errors.append('回测天数必须是有效数字')
        
        # Validate strategy_ids
        from backtesting.strategy_report_parser import StrategyReportParser
        report_path = 'pro2/fund_backtest/strategy_results/strategy_comparison_report.md'
        
        try:
            parser = StrategyReportParser(report_path)
            available_strategies = parser.get_all_strategy_ids()
            
            for strategy_id in strategy_ids:
                if strategy_id not in available_strategies:
                    validation_errors.append(f'无效的策略ID: {strategy_id}')
        except Exception as e:
            logger.warning(f"无法验证策略ID: {str(e)}")
        
        # Return validation errors if any
        if validation_errors:
            return jsonify({
                'success': False,
                'error': '; '.join(validation_errors)
            }), 400
        
        # Execute backtests for all strategies with identical parameters (Requirement 7.2)
        comparison_results = []
        
        for strategy_id in strategy_ids:
            result = _execute_single_fund_backtest(
                fund_code, strategy_id, initial_amount, base_invest, days
            )
            
            if result is None:
                return jsonify({
                    'success': False,
                    'error': f'没有找到基金 {fund_code} 的历史数据'
                }), 404
            
            comparison_results.append(result)
        
        # Identify best performing strategy by total return (Requirement 7.4)
        best_strategy = max(comparison_results, key=lambda x: x['total_return'])
        best_strategy_id = best_strategy['strategy_id']
        
        # Mark the best strategy
        for result in comparison_results:
            result['is_best'] = (result['strategy_id'] == best_strategy_id)
        
        # Return comparison results (Requirement 7.3, 7.5)
        return jsonify({
            'success': True,
            'data': {
                'fund_code': fund_code,
                'initial_amount': initial_amount,
                'base_invest': base_invest,
                'days': days,
                'strategies': comparison_results,
                'best_strategy_id': best_strategy_id
            }
        })
        
    except Exception as e:
        logger.error(f"Strategy comparison failed: {str(e)}")
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

@app.route('/api/user-holdings', methods=['GET'])
def get_user_holdings():
    """获取用户持仓列表（简化版，用于策略页面）
    
    返回用户的基金持仓基本信息，不包含复杂的盈亏计算
    """
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        sql = """
        SELECT fund_code, fund_name, holding_shares, cost_price, 
               holding_amount, buy_date
        FROM user_holdings 
        WHERE user_id = :user_id
        ORDER BY holding_amount DESC
        """
        
        df = db_manager.execute_query(sql, {'user_id': user_id})
        
        if df.empty:
            return jsonify({'success': True, 'data': []})
        
        # 转换为字典列表
        holdings = []
        for _, row in df.iterrows():
            holding = {
                'fund_code': row['fund_code'],
                'fund_name': row['fund_name'],
                'holding_shares': round(float(row['holding_shares']), 4) if pd.notna(row['holding_shares']) else 0,
                'cost_price': round(float(row['cost_price']), 4) if pd.notna(row['cost_price']) else 0,
                'holding_amount': round(float(row['holding_amount']), 2) if pd.notna(row['holding_amount']) else 0,
                'buy_date': str(row['buy_date']) if pd.notna(row['buy_date']) else None
            }
            holdings.append(holding)
        
        return jsonify({'success': True, 'data': holdings})
        
    except Exception as e:
        logger.error(f"获取用户持仓失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategies/metadata', methods=['GET'])
def get_strategies_metadata():
    """获取策略元数据（从策略对比报告中解析）
    
    返回五个策略的详细信息，包括绩效指标
    """
    try:
        from backtesting.strategy_report_parser import StrategyReportParser
        
        # 策略报告路径
        report_path = 'pro2/fund_backtest/strategy_results/strategy_comparison_report.md'
        
        # 解析策略报告
        parser = StrategyReportParser(report_path)
        strategies = parser.parse()
        
        return jsonify({'success': True, 'data': strategies})
        
    except FileNotFoundError as e:
        logger.error(f"策略报告文件未找到: {str(e)}")
        return jsonify({'success': False, 'error': '策略报告文件未找到'}), 500
    except ValueError as e:
        logger.error(f"策略报告解析失败: {str(e)}")
        return jsonify({'success': False, 'error': f'策略报告解析失败: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"获取策略元数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/holdings', methods=['GET'])
def get_holdings():
    """获取用户持仓列表"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        search = request.args.get('search', '')
        
        sql = """
        SELECT h.*, 
               far.today_return, far.prev_day_return as yesterday_return,
               far.current_estimate as current_nav,
               far.yesterday_nav as previous_nav,
               far.sharpe_ratio, far.sharpe_ratio_ytd, far.sharpe_ratio_1y, far.sharpe_ratio_all,
               far.max_drawdown, far.volatility,
               far.annualized_return, far.calmar_ratio, far.sortino_ratio
        FROM user_holdings h
        LEFT JOIN (
            SELECT * FROM fund_analysis_results
            WHERE (fund_code, analysis_date) IN (
                SELECT fund_code, MAX(analysis_date) as max_date
                FROM fund_analysis_results
                GROUP BY fund_code
            )
        ) far ON h.fund_code = far.fund_code
        WHERE h.user_id = :user_id
        """
        
        params = {'user_id': user_id}
        
        if search:
            sql += " AND (h.fund_code LIKE :search OR h.fund_name LIKE :search)"
            params['search'] = f'%{search}%'
        
        sql += " ORDER BY h.buy_date DESC"
        
        df = db_manager.execute_query(sql, params)
        
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
            yesterday_return = float(row['yesterday_return']) if pd.notna(row['yesterday_return']) else 0
            sharpe_ratio = float(row['sharpe_ratio']) if pd.notna(row['sharpe_ratio']) else 0
            sharpe_ratio_ytd = float(row['sharpe_ratio_ytd']) if pd.notna(row['sharpe_ratio_ytd']) else 0
            sharpe_ratio_1y = float(row['sharpe_ratio_1y']) if pd.notna(row['sharpe_ratio_1y']) else 0
            sharpe_ratio_all = float(row['sharpe_ratio_all']) if pd.notna(row['sharpe_ratio_all']) else 0
            max_drawdown = float(row['max_drawdown']) if pd.notna(row['max_drawdown']) else 0
            volatility = float(row['volatility']) if pd.notna(row['volatility']) else 0
            annualized_return = float(row['annualized_return']) if pd.notna(row['annualized_return']) else 0
            calmar_ratio = float(row['calmar_ratio']) if pd.notna(row['calmar_ratio']) else 0
            sortino_ratio = float(row['sortino_ratio']) if pd.notna(row['sortino_ratio']) else 0
            
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
                'today_return': round(today_return, 2),
                'yesterday_return': round(yesterday_return, 2),
                # 绩效指标
                'sharpe_ratio': round(sharpe_ratio, 4),
                'sharpe_ratio_ytd': round(sharpe_ratio_ytd, 4),
                'sharpe_ratio_1y': round(sharpe_ratio_1y, 4),
                'sharpe_ratio_all': round(sharpe_ratio_all, 4),
                'max_drawdown': round(max_drawdown * 100, 2),
                'volatility': round(volatility * 100, 2),
                'annualized_return': round(annualized_return * 100, 2),
                'calmar_ratio': round(calmar_ratio, 4),
                'sortino_ratio': round(sortino_ratio, 4)
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
    """更新持仓并刷新实时数据"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default_user')
        
        # 检查是否修改了 fund_code
        new_fund_code = data.get('fund_code')
        fund_code_changed = new_fund_code and new_fund_code != fund_code
        
        # 如果 fund_code 改变了，需要特殊处理
        if fund_code_changed:
            # 检查新的 fund_code 是否已存在
            check_sql = "SELECT COUNT(*) as count FROM user_holdings WHERE user_id = :user_id AND fund_code = :fund_code"
            check_result = db_manager.execute_query(check_sql, {'user_id': user_id, 'fund_code': new_fund_code})
            if not check_result.empty and check_result.iloc[0]['count'] > 0:
                return jsonify({'success': False, 'error': f'基金代码 {new_fund_code} 已存在'}), 400
            
            # 获取旧记录的所有数据
            get_sql = "SELECT * FROM user_holdings WHERE user_id = :user_id AND fund_code = :fund_code"
            old_record = db_manager.execute_query(get_sql, {'user_id': user_id, 'fund_code': fund_code})
            
            if old_record.empty:
                return jsonify({'success': False, 'error': '未找到原始记录'}), 404
            
            old_data = old_record.iloc[0].to_dict()
            
            # 更新字段值
            old_data['fund_code'] = new_fund_code
            if 'fund_name' in data:
                old_data['fund_name'] = data['fund_name']
            if 'holding_amount' in data:
                old_data['holding_amount'] = float(data['holding_amount'])
            
            # 删除旧记录
            delete_sql = "DELETE FROM user_holdings WHERE user_id = :user_id AND fund_code = :fund_code"
            db_manager.execute_sql(delete_sql, {'user_id': user_id, 'fund_code': fund_code})
            
            # 插入新记录
            insert_sql = """
            INSERT INTO user_holdings (user_id, fund_code, fund_name, holding_shares, cost_price, 
                                      holding_amount, buy_date, notes)
            VALUES (:user_id, :fund_code, :fund_name, :holding_shares, :cost_price, 
                    :holding_amount, :buy_date, :notes)
            """
            insert_params = {
                'user_id': user_id,
                'fund_code': old_data['fund_code'],
                'fund_name': old_data['fund_name'],
                'holding_shares': float(old_data.get('holding_shares', 0)),
                'cost_price': float(old_data.get('cost_price', 0)),
                'holding_amount': float(old_data.get('holding_amount', 0)),
                'buy_date': old_data.get('buy_date'),
                'notes': old_data.get('notes', '')
            }
            success = db_manager.execute_sql(insert_sql, insert_params)
            
            if not success:
                return jsonify({'success': False, 'error': '更新基金代码失败'}), 500
            
            # 使用新的 fund_code 继续后续处理
            fund_code = new_fund_code
            fund_name = old_data['fund_name']
        else:
            # fund_code 没有改变，正常更新
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
            if 'holding_amount' in data:
                update_fields.append('holding_amount = :holding_amount')
                params['holding_amount'] = float(data['holding_amount'])
            elif 'holding_shares' in data or 'cost_price' in data:
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
            
            if not success:
                return jsonify({'success': False, 'error': '持仓更新失败'}), 500
            
            # 获取基金名称
            fund_name = params.get('fund_name')
            if not fund_name:
                sql_name = "SELECT fund_name FROM user_holdings WHERE user_id = :user_id AND fund_code = :fund_code"
                df_name = db_manager.execute_query(sql_name, {'user_id': user_id, 'fund_code': fund_code})
                if not df_name.empty:
                    fund_name = df_name.iloc[0]['fund_name']
        
        # 更新成功后，获取最新实时数据并更新fund_analysis_results表
        try:
            from data_retrieval.enhanced_fund_data import EnhancedFundData
            from backtesting.enhanced_strategy import EnhancedInvestmentStrategy
            
            fund_data_manager = EnhancedFundData()
            strategy_engine = EnhancedInvestmentStrategy()
            
            # 获取实时数据
            realtime_data = fund_data_manager.get_realtime_data(fund_code)
            performance_metrics = fund_data_manager.get_performance_metrics(fund_code)
            
            # 计算今日和昨日收益率
            today_return = float(realtime_data.get('today_return', 0.0))
            yesterday_return = float(realtime_data.get('yesterday_return', 0.0))
            
            # 投资策略分析
            strategy_result = strategy_engine.analyze_strategy(today_return, yesterday_return, performance_metrics)
            
            # 更新fund_analysis_results表
            from datetime import datetime
            analysis_date = datetime.now().date()
            
            update_sql = """
            INSERT INTO fund_analysis_results (
                fund_code, fund_name, analysis_date,
                yesterday_nav, current_estimate, today_return, prev_day_return,
                status_label, operation_suggestion, execution_amount,
                is_buy, buy_multiplier, redeem_amount, comparison_value,
                annualized_return, sharpe_ratio, sharpe_ratio_ytd, sharpe_ratio_1y, sharpe_ratio_all,
                max_drawdown, volatility, calmar_ratio, sortino_ratio, var_95,
                win_rate, profit_loss_ratio, total_return, composite_score
            ) VALUES (
                :fund_code, :fund_name, :analysis_date,
                :yesterday_nav, :current_estimate, :today_return, :prev_day_return,
                :status_label, :operation_suggestion, :execution_amount,
                :is_buy, :buy_multiplier, :redeem_amount, :comparison_value,
                :annualized_return, :sharpe_ratio, :sharpe_ratio_ytd, :sharpe_ratio_1y, :sharpe_ratio_all,
                :max_drawdown, :volatility, :calmar_ratio, :sortino_ratio, :var_95,
                :win_rate, :profit_loss_ratio, :total_return, :composite_score
            ) ON DUPLICATE KEY UPDATE
                fund_name = VALUES(fund_name),
                yesterday_nav = VALUES(yesterday_nav),
                current_estimate = VALUES(current_estimate),
                today_return = VALUES(today_return),
                prev_day_return = VALUES(prev_day_return),
                status_label = VALUES(status_label),
                operation_suggestion = VALUES(operation_suggestion),
                execution_amount = VALUES(execution_amount),
                is_buy = VALUES(is_buy),
                buy_multiplier = VALUES(buy_multiplier),
                redeem_amount = VALUES(redeem_amount),
                comparison_value = VALUES(comparison_value),
                annualized_return = VALUES(annualized_return),
                sharpe_ratio = VALUES(sharpe_ratio),
                sharpe_ratio_ytd = VALUES(sharpe_ratio_ytd),
                sharpe_ratio_1y = VALUES(sharpe_ratio_1y),
                sharpe_ratio_all = VALUES(sharpe_ratio_all),
                max_drawdown = VALUES(max_drawdown),
                volatility = VALUES(volatility),
                calmar_ratio = VALUES(calmar_ratio),
                sortino_ratio = VALUES(sortino_ratio),
                var_95 = VALUES(var_95),
                win_rate = VALUES(win_rate),
                profit_loss_ratio = VALUES(profit_loss_ratio),
                total_return = VALUES(total_return),
                composite_score = VALUES(composite_score)
            """
            
            update_params = {
                'fund_code': fund_code,
                'fund_name': fund_name or fund_code,
                'analysis_date': analysis_date,
                'yesterday_nav': realtime_data.get('previous_nav', 0.0),
                'current_estimate': realtime_data.get('estimate_nav', 0.0),
                'today_return': today_return,
                'prev_day_return': yesterday_return,
                'status_label': strategy_result.get('status_label', ''),
                'operation_suggestion': strategy_result.get('operation_suggestion', ''),
                'execution_amount': strategy_result.get('execution_amount', ''),
                'is_buy': 1 if strategy_result.get('action') in ['buy', 'strong_buy', 'weak_buy'] else 0,
                'buy_multiplier': strategy_result.get('buy_multiplier', 0.0),
                'redeem_amount': strategy_result.get('redeem_amount', 0.0),
                'comparison_value': strategy_result.get('comparison_value', 0.0),
                'annualized_return': performance_metrics.get('annualized_return', 0.0),
                'sharpe_ratio': performance_metrics.get('sharpe_ratio', 0.0),
                'sharpe_ratio_ytd': performance_metrics.get('sharpe_ratio_ytd', 0.0),
                'sharpe_ratio_1y': performance_metrics.get('sharpe_ratio_1y', 0.0),
                'sharpe_ratio_all': performance_metrics.get('sharpe_ratio_all', 0.0),
                'max_drawdown': performance_metrics.get('max_drawdown', 0.0),
                'volatility': performance_metrics.get('volatility', 0.0),
                'calmar_ratio': performance_metrics.get('calmar_ratio', 0.0),
                'sortino_ratio': performance_metrics.get('sortino_ratio', 0.0),
                'var_95': performance_metrics.get('var_95', 0.0),
                'win_rate': performance_metrics.get('win_rate', 0.0),
                'profit_loss_ratio': performance_metrics.get('profit_loss_ratio', 0.0),
                'total_return': performance_metrics.get('total_return', 0.0),
                'composite_score': performance_metrics.get('composite_score', 0.0)
            }
            
            db_manager.execute_sql(update_sql, update_params)
            logger.info(f"已更新基金 {fund_code} 的实时数据和指标")
            
        except Exception as e:
            logger.warning(f"更新实时数据失败: {str(e)}")
            # 即使更新实时数据失败，也返回成功（因为持仓已更新）
        
        return jsonify({'success': True, 'message': '持仓更新成功，实时数据已刷新'})
            
    except Exception as e:
        logger.error(f"更新持仓失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/holdings/clear', methods=['DELETE'])
def clear_holdings():
    """
    清空用户持仓
    """
    try:
        user_id = request.args.get('user_id', 'default_user')
        # 删除用户的所有持仓记录
        sql = "DELETE FROM user_holdings WHERE user_id = :user_id"
        success = db_manager.execute_sql(sql, {'user_id': user_id})
        
        if success:
            return jsonify({'success': True, 'message': '持仓已清空'})
        else:
            return jsonify({'success': False, 'error': '清空失败'})
    except Exception as e:
        logger.error(f"清空持仓失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/holdings/analyze/correlation', methods=['POST'])
def analyze_fund_correlation():
    """
    分析基金相关性
    """
    try:
        data = request.get_json()
        if not data or 'fund_codes' not in data:
            return jsonify({'success': False, 'error': '缺少基金代码'})
        
        fund_codes = data['fund_codes']
        if len(fund_codes) < 2:
            return jsonify({'success': False, 'error': '至少需要2只基金进行相关性分析'})
        
        # 导入相关性分析模块
        from data_retrieval.fund_analyzer import FundAnalyzer
        
        analyzer = FundAnalyzer()
        # 使用 use_cache=False 确保获取最新的基金名称
        result = analyzer.analyze_correlation(fund_codes, use_cache=False)
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"分析基金相关性失败: {e}")
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


# ==================== 截图识别导入 API ====================

@app.route('/api/holdings/import/screenshot', methods=['POST'])
def import_holding_screenshot():
    """
    通过截图识别导入持仓
    接收Base64格式的图片，识别其中的基金信息
    """
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'success': False, 'error': '未提供图片数据'}), 400
        
        image_data = data['image']
        use_gpu = data.get('use_gpu', True)
        
        logger.info("开始识别基金截图...")
        
        recognized_funds = recognize_fund_screenshot(image_data, use_gpu=use_gpu)
        
        if not recognized_funds:
            return jsonify({
                'success': False, 
                'error': '未能识别到基金信息，请确保图片清晰可读',
                'suggestion': '建议上传更清晰的基金持仓截图，确保基金代码和名称清晰可见'
            }), 400
        
        validated_funds = []
        seen_codes = set()  # 用于去重
        
        # 计算汇总信息
        total_holding_amount = 0
        total_profit_amount = 0
        
        for fund in recognized_funds:
            fund_code = fund.get('fund_code')
            
            # 跳过重复的基金代码
            if fund_code in seen_codes:
                logger.debug(f"跳过重复基金: {fund_code}")
                continue
            
            is_valid, error_msg = validate_recognized_fund(fund)
            if is_valid:
                # 添加持仓信息到返回数据中
                fund_data = {
                    'fund_code': fund_code,
                    'fund_name': fund.get('fund_name', ''),
                    'confidence': fund.get('confidence', 0),
                    'source': fund.get('source', ''),
                    'original_text': fund.get('original_text', ''),
                    # 持仓相关信息
                    'holding_amount': fund.get('holding_amount'),
                    'profit_amount': fund.get('profit_amount'),
                    'profit_rate': fund.get('profit_rate'),
                    'nav_value': fund.get('nav_value'),
                    # 计算当前市值
                    'current_value': None
                }
                
                # 计算当前市值
                if fund_data['holding_amount'] is not None and fund_data['profit_amount'] is not None:
                    fund_data['current_value'] = fund_data['holding_amount'] + fund_data['profit_amount']
                    total_holding_amount += fund_data['holding_amount']
                    total_profit_amount += fund_data['profit_amount']
                
                validated_funds.append(fund_data)
                seen_codes.add(fund_code)
                logger.debug(f"验证通过: {fund_code} - {fund.get('fund_name', 'N/A')}")
            else:
                logger.warning(f"识别结果验证失败: {error_msg}, 基金信息: {fund}")
        
        if not validated_funds:
            return jsonify({
                'success': False,
                'error': '未能识别到有效的基金代码',
                'recognized': recognized_funds,
                'debug_info': f'原始识别数量: {len(recognized_funds)}, 验证通过数量: 0'
            }), 400
        
        # 计算投资组合汇总
        total_current_value = total_holding_amount + total_profit_amount
        total_profit_rate = (total_profit_amount / total_holding_amount * 100) if total_holding_amount > 0 else 0
        
        # 找出表现最好和最差的基金
        best_fund = None
        worst_fund = None
        if validated_funds:
            funds_with_rate = [f for f in validated_funds if f.get('profit_rate') is not None]
            if funds_with_rate:
                best_fund = max(funds_with_rate, key=lambda x: x.get('profit_rate', -999))
                worst_fund = min(funds_with_rate, key=lambda x: x.get('profit_rate', 999))
        
        portfolio_summary = {
            'total_funds': len(validated_funds),
            'total_holding_amount': round(total_holding_amount, 2) if total_holding_amount > 0 else 0,
            'total_profit_amount': round(total_profit_amount, 2),
            'total_current_value': round(total_current_value, 2) if total_current_value > 0 else 0,
            'total_profit_rate': round(total_profit_rate, 2),
            'best_fund': {
                'fund_name': best_fund.get('fund_name', '')[:25] + '...' if best_fund and len(best_fund.get('fund_name', '')) > 25 else best_fund.get('fund_name', '') if best_fund else '',
                'profit_rate': round(best_fund.get('profit_rate', 0), 2) if best_fund else 0
            } if best_fund else None,
            'worst_fund': {
                'fund_name': worst_fund.get('fund_name', '')[:25] + '...' if worst_fund and len(worst_fund.get('fund_name', '')) > 25 else worst_fund.get('fund_name', '') if worst_fund else '',
                'profit_rate': round(worst_fund.get('profit_rate', 0), 2) if worst_fund else 0
            } if worst_fund else None
        }
        
        logger.info(f"成功识别 {len(validated_funds)} 个基金 (原始识别: {len(recognized_funds)} 个)")
        
        return jsonify({
            'success': True,
            'data': validated_funds,
            'portfolio_summary': portfolio_summary,
            'message': f'成功识别 {len(validated_funds)} 个基金，请确认信息后导入',
            'debug_info': f'原始识别数量: {len(recognized_funds)}, 最终数量: {len(validated_funds)}'
        })
        
    except Exception as e:
        logger.error(f"截图识别失败: {str(e)}")
        return jsonify({'success': False, 'error': f'识别失败: {str(e)}'}), 500


@app.route('/api/holdings/import/confirm', methods=['POST'])
def confirm_import_holdings():
    """
    确认导入识别到的基金到持仓列表
    同时更新相关的持仓盈亏信息
    """
    try:
        data = request.get_json()
        if not data or 'funds' not in data:
            return jsonify({'success': False, 'error': '未提供基金数据'}), 400
        
        user_id = data.get('user_id', 'default_user')
        funds = data['funds']
        
        if not funds:
            return jsonify({'success': False, 'error': '基金列表为空'}), 400
        
        imported = []
        failed = []
        
        for fund_info in funds:
            fund_code = fund_info.get('fund_code', '').strip()
            fund_name = fund_info.get('fund_name', '').strip()
            holding_shares = float(fund_info.get('holding_shares', 0) or 0)
            cost_price = float(fund_info.get('cost_price', 0) or 0)
            buy_date = fund_info.get('buy_date', '')
            confidence = fund_info.get('confidence', 0)
            notes = f"通过截图识别导入 - 置信度: {confidence:.2%}"
            
            if not fund_code:
                failed.append({'fund': fund_info, 'error': '基金代码为空'})
                continue
            
            holding_amount = holding_shares * cost_price
            
            # 1. 保存到 user_holdings 表
            sql_holdings = """
            INSERT INTO user_holdings 
            (user_id, fund_code, fund_name, holding_shares, cost_price, holding_amount, buy_date, notes)
            VALUES (:user_id, :fund_code, :fund_name, :holding_shares, :cost_price, :holding_amount, :buy_date, :notes)
            ON DUPLICATE KEY UPDATE
                holding_shares = holding_shares + :add_shares,
                holding_amount = holding_amount + :add_amount,
                cost_price = (holding_amount + :add_amount) / (holding_shares + :add_shares),
                notes = CONCAT(notes, '; ', :notes),
                updated_at = NOW()
            """
            
            try:
                # 保存到 user_holdings
                success = db_manager.execute_sql(sql_holdings, {
                    'user_id': user_id,
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'holding_shares': holding_shares,
                    'cost_price': cost_price,
                    'holding_amount': holding_amount,
                    'buy_date': buy_date,
                    'notes': notes,
                    'add_shares': holding_shares,
                    'add_amount': holding_amount
                })
                
                if success:
                    # 2. 检查是否存在分析结果数据，如果不存在则生成
                    sql_check = """
                    SELECT COUNT(*) as count 
                    FROM fund_analysis_results 
                    WHERE fund_code = :fund_code 
                    """
                    check_df = db_manager.execute_query(sql_check, {'fund_code': fund_code})
                    
                    # 生成并保存分析结果数据
                    try:
                        logger.info(f"为基金 {fund_code} 生成分析结果...")
                        # 获取基金绩效指标
                        metrics = EnhancedFundData.get_performance_metrics(fund_code)
                        
                        # 获取实时数据
                        realtime_data = EnhancedFundData.get_realtime_data(fund_code)
                        logger.info(f"获取基金 {fund_code} 实时数据成功: {realtime_data}")
                        
                        # 构造分析结果数据
                        analysis_data = {
                            'fund_code': fund_code,
                            'fund_name': fund_name,
                            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
                            'current_estimate': realtime_data.get('current_nav', cost_price),
                            'yesterday_nav': realtime_data.get('previous_nav', cost_price),
                            'today_return': realtime_data.get('today_return', 0.0),
                            'prev_day_return': realtime_data.get('yesterday_return', 0.0),
                            'annualized_return': metrics.get('annualized_return', 0.0),
                            'sharpe_ratio': metrics.get('sharpe_ratio', 0.0),
                            'sharpe_ratio_ytd': metrics.get('sharpe_ratio_ytd', 0.0),
                            'sharpe_ratio_1y': metrics.get('sharpe_ratio_1y', 0.0),
                            'sharpe_ratio_all': metrics.get('sharpe_ratio_all', 0.0),
                            'max_drawdown': metrics.get('max_drawdown', 0.0),
                            'volatility': metrics.get('volatility', 0.0),
                            'calmar_ratio': metrics.get('calmar_ratio', 0.0),
                            'sortino_ratio': metrics.get('sortino_ratio', 0.0),
                            'var_95': metrics.get('var_95', 0.0),
                            'win_rate': metrics.get('win_rate', 0.0),
                            'profit_loss_ratio': metrics.get('profit_loss_ratio', 0.0),
                            'total_return': metrics.get('total_return', 0.0),
                            'composite_score': metrics.get('composite_score', 0.0)
                        }
                        
                        # 保存到 fund_analysis_results 表（使用 INSERT ... ON DUPLICATE KEY UPDATE 语句）
                        sql_insert_analysis = """
                        INSERT INTO fund_analysis_results (
                            fund_code, fund_name, analysis_date, current_estimate, yesterday_nav,
                            today_return, prev_day_return, annualized_return, sharpe_ratio,
                            sharpe_ratio_ytd, sharpe_ratio_1y, sharpe_ratio_all, max_drawdown,
                            volatility, calmar_ratio, sortino_ratio, var_95, win_rate,
                            profit_loss_ratio, total_return, composite_score
                        ) VALUES (
                            :fund_code, :fund_name, :analysis_date, :current_estimate, :yesterday_nav,
                            :today_return, :prev_day_return, :annualized_return, :sharpe_ratio,
                            :sharpe_ratio_ytd, :sharpe_ratio_1y, :sharpe_ratio_all, :max_drawdown,
                            :volatility, :calmar_ratio, :sortino_ratio, :var_95, :win_rate,
                            :profit_loss_ratio, :total_return, :composite_score
                        ) ON DUPLICATE KEY UPDATE
                            fund_name = VALUES(fund_name),
                            analysis_date = VALUES(analysis_date),
                            current_estimate = VALUES(current_estimate),
                            yesterday_nav = VALUES(yesterday_nav),
                            today_return = VALUES(today_return),
                            prev_day_return = VALUES(prev_day_return),
                            annualized_return = VALUES(annualized_return),
                            sharpe_ratio = VALUES(sharpe_ratio),
                            sharpe_ratio_ytd = VALUES(sharpe_ratio_ytd),
                            sharpe_ratio_1y = VALUES(sharpe_ratio_1y),
                            sharpe_ratio_all = VALUES(sharpe_ratio_all),
                            max_drawdown = VALUES(max_drawdown),
                            volatility = VALUES(volatility),
                            calmar_ratio = VALUES(calmar_ratio),
                            sortino_ratio = VALUES(sortino_ratio),
                            var_95 = VALUES(var_95),
                            win_rate = VALUES(win_rate),
                            profit_loss_ratio = VALUES(profit_loss_ratio),
                            total_return = VALUES(total_return),
                            composite_score = VALUES(composite_score)
                        """
                        
                        db_manager.execute_sql(sql_insert_analysis, analysis_data)
                        logger.info(f"为基金 {fund_code} 生成分析结果成功")
                    except Exception as e:
                        logger.error(f"为基金 {fund_code} 生成分析结果失败: {str(e)}")
                    
                    # 3. 获取最新的基金净值信息（从 fund_analysis_results）
                    sql_nav = """
                    SELECT current_estimate, yesterday_nav 
                    FROM fund_analysis_results 
                    WHERE fund_code = :fund_code 
                    ORDER BY analysis_date DESC 
                    LIMIT 1
                    """
                    nav_df = db_manager.execute_query(sql_nav, {'fund_code': fund_code})
                    
                    # 3. 计算持仓盈亏信息
                    if not nav_df.empty:
                        current_nav = float(nav_df.iloc[0]['current_estimate']) if pd.notna(nav_df.iloc[0]['current_estimate']) else cost_price
                        previous_nav = float(nav_df.iloc[0]['yesterday_nav']) if pd.notna(nav_df.iloc[0]['yesterday_nav']) else cost_price
                        
                        # 当前市值和昨日市值
                        current_value = holding_shares * current_nav
                        previous_value = holding_shares * previous_nav
                        
                        # 持有盈亏
                        holding_profit = current_value - holding_amount
                        holding_profit_rate = (holding_profit / holding_amount * 100) if holding_amount > 0 else 0
                        
                        # 当日盈亏
                        today_profit = current_value - previous_value
                        today_profit_rate = (today_profit / previous_value * 100) if previous_value > 0 else 0
                        
                        logger.info(f"导入基金 {fund_code}: 持仓金额={holding_amount:.2f}, 当前市值={current_value:.2f}, 持有盈亏={holding_profit:.2f} ({holding_profit_rate:.2f}%)")
                    
                    imported.append({
                        'fund_code': fund_code,
                        'fund_name': fund_name,
                        'holding_shares': holding_shares,
                        'cost_price': cost_price,
                        'holding_amount': holding_amount
                    })
                else:
                    failed.append({'fund_code': fund_code, 'error': '数据库插入失败'})
                    
            except Exception as db_error:
                logger.error(f"导入基金 {fund_code} 失败: {db_error}")
                failed.append({'fund_code': fund_code, 'error': str(db_error)})
        
        return jsonify({
            'success': True,
            'imported': imported,
            'failed': failed,
            'message': f'成功导入 {len(imported)} 个基金，{len(failed)} 个失败'
        })
        
    except Exception as e:
        logger.error(f"确认导入失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/holdings/import/ocr-status', methods=['GET'])
def get_ocr_status():
    """检查OCR功能状态"""
    try:
        ocr_available = False
        try:
            import easyocr
            ocr_available = True
        except ImportError:
            pass
        
        return jsonify({
            'success': True,
            'data': {
                'ocr_available': ocr_available,
                'gpu_available': True,
                'supported_formats': ['png', 'jpg', 'jpeg'],
                'max_file_size': '10MB'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== ETF市场 API ====================

@app.route('/api/etf/list', methods=['GET'])
def get_etf_list():
    """获取全市场ETF列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort_by', 'turnover')
        sort_order = request.args.get('sort_order', 'desc')
        
        # 获取ETF列表
        etf_df = fund_data_manager.get_etf_list()
        
        if etf_df.empty:
            return jsonify({'success': True, 'data': [], 'total': 0, 'page': page, 'per_page': per_page})
        
        # 搜索过滤
        if search:
            mask = (etf_df['etf_code'].str.contains(search, na=False) | 
                   etf_df['etf_name'].str.contains(search, na=False))
            etf_df = etf_df[mask]
        
        # 排序
        valid_sort_fields = ['etf_code', 'etf_name', 'current_price', 'change_percent', 
                            'volume', 'turnover', 'turnover_rate', 'amplitude']
        if sort_by in valid_sort_fields and sort_by in etf_df.columns:
            ascending = sort_order != 'desc'
            etf_df = etf_df.sort_values(sort_by, ascending=ascending, na_position='last')
        
        total = len(etf_df)
        
        # 分页
        start = (page - 1) * per_page
        etf_page = etf_df.iloc[start:start + per_page]
        
        # 转换为字典列表
        etf_list = []
        for _, row in etf_page.iterrows():
            etf_item = row.to_dict()
            # 清理NaN值
            for key in etf_item:
                if pd.isna(etf_item[key]):
                    etf_item[key] = None
                elif isinstance(etf_item[key], float):
                    etf_item[key] = round(etf_item[key], 4)
            etf_list.append(etf_item)
        
        return jsonify({
            'success': True, 
            'data': etf_list, 
            'total': total, 
            'page': page, 
            'per_page': per_page
        })
        
    except Exception as e:
        logger.error(f"获取ETF列表失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/etf/<etf_code>', methods=['GET'])
def get_etf_detail(etf_code):
    """获取单个ETF详情"""
    try:
        # 获取ETF列表找到该ETF
        etf_df = fund_data_manager.get_etf_list()
        
        if etf_df.empty:
            return jsonify({'success': False, 'error': 'ETF数据获取失败'}), 500
        
        etf_row = etf_df[etf_df['etf_code'] == etf_code]
        
        if etf_row.empty:
            return jsonify({'success': False, 'error': 'ETF不存在'}), 404
        
        etf_data = etf_row.iloc[0].to_dict()
        
        # 获取绩效指标
        performance = fund_data_manager.get_etf_performance(etf_code)
        etf_data.update(performance)
        
        # 清理NaN值
        for key in etf_data:
            if pd.isna(etf_data[key]):
                etf_data[key] = None
            elif isinstance(etf_data[key], float):
                etf_data[key] = round(etf_data[key], 4)
        
        return jsonify({'success': True, 'data': etf_data})
        
    except Exception as e:
        logger.error(f"获取ETF详情失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/etf/<etf_code>/history', methods=['GET'])
def get_etf_history(etf_code):
    """获取ETF历史行情和净值数据"""
    try:
        from datetime import datetime as dt
        
        period = request.args.get('period', '')
        days = request.args.get('days', 30, type=int)
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        # 如果有自定义日期范围
        if start_date and end_date:
            start = dt.strptime(start_date, '%Y-%m-%d')
            end = dt.strptime(end_date, '%Y-%m-%d')
            days = (end - start).days + 1
        else:
            # 根据period计算days
            today = dt.now()
            if period == '1m':
                days = 30
            elif period == '3m':
                days = 90
            elif period == '6m':
                days = 180
            elif period == '1y':
                days = 365
            elif period == '3y':
                days = 1095
            elif period == 'ytd':
                year_start = dt(today.year, 1, 1)
                days = (today - year_start).days + 1
            elif period == 'all':
                days = 9999
        
        # 获取ETF净值历史数据（包含单位净值、累计净值）
        nav_data = fund_data_manager.get_etf_nav_history(etf_code, days, start_date, end_date)
        
        if nav_data.empty:
            # 如果净值数据为空，尝试获取行情数据作为备选
            hist_data = fund_data_manager.get_etf_history(etf_code, days)
            if hist_data.empty:
                return jsonify({'success': True, 'data': []})
            
            # 如果有自定义日期范围，进行过滤
            if start_date and end_date:
                hist_data['date'] = pd.to_datetime(hist_data['date'])
                hist_data = hist_data[(hist_data['date'] >= start_date) & (hist_data['date'] <= end_date)]
            
            # 转换日期格式
            if 'date' in hist_data.columns:
                hist_data['date'] = pd.to_datetime(hist_data['date']).dt.strftime('%Y-%m-%d')
            
            # 清理NaN值
            result_data = []
            for _, row in hist_data.iterrows():
                item = row.to_dict()
                for key in item:
                    if pd.isna(item[key]):
                        item[key] = None
                    elif isinstance(item[key], float):
                        item[key] = round(item[key], 4)
                result_data.append(item)
            
            return jsonify({'success': True, 'data': result_data})
        
        # 如果有自定义日期范围，进行过滤
        if start_date and end_date:
            nav_data['date'] = pd.to_datetime(nav_data['date'])
            nav_data = nav_data[(nav_data['date'] >= start_date) & (nav_data['date'] <= end_date)]
        
        # 转换日期格式
        if 'date' in nav_data.columns:
            nav_data['date'] = pd.to_datetime(nav_data['date']).dt.strftime('%Y-%m-%d')
        
        # 清理NaN值并构建结果
        result_data = []
        for _, row in nav_data.iterrows():
            item = row.to_dict()
            for key in item:
                if pd.isna(item[key]):
                    item[key] = None
                elif isinstance(item[key], float):
                    item[key] = round(item[key], 4)
            result_data.append(item)
        
        return jsonify({'success': True, 'data': result_data})
        
    except Exception as e:
        logger.error(f"获取ETF历史数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/etf/<etf_code>/holdings', methods=['GET'])
def get_etf_holdings(etf_code):
    """获取ETF持仓数据"""
    try:
        import akshare as ak
        
        holdings = []
        update_date = None
        
        try:
            # 尝试获取ETF持仓
            holdings_df = ak.fund_etf_fund_info_em(fund=etf_code)
            
            if holdings_df is not None and not holdings_df.empty:
                # 处理持仓数据
                for _, row in holdings_df.head(20).iterrows():
                    holding = {}
                    for col in holdings_df.columns:
                        val = row[col]
                        if pd.isna(val):
                            holding[col] = None
                        elif isinstance(val, float):
                            holding[col] = round(val, 4)
                        else:
                            holding[col] = str(val)
                    holdings.append(holding)
        except Exception as e:
            logger.warning(f"获取ETF持仓失败: {str(e)}")
            # 尝试备用方法
            try:
                holdings_df = ak.fund_portfolio_hold_em(symbol=etf_code, date="2024")
                if holdings_df is not None and not holdings_df.empty:
                    if '季度' in holdings_df.columns:
                        update_date = str(holdings_df['季度'].iloc[0])
                    
                    for _, row in holdings_df.head(10).iterrows():
                        holdings.append({
                            'stock_code': str(row.get('股票代码', '')),
                            'stock_name': str(row.get('股票名称', '')),
                            'ratio': round(float(row.get('占净值比例', 0)), 2) if pd.notna(row.get('占净值比例')) else None,
                            'shares': row.get('持股数', None),
                            'value': row.get('持仓市值', None)
                        })
            except:
                pass
        
        return jsonify({
            'success': True,
            'data': {
                'holdings': holdings,
                'update_date': update_date
            }
        })
        
    except Exception as e:
        logger.error(f"获取ETF持仓失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/etf/<etf_code>/info', methods=['GET'])
def get_etf_info(etf_code):
    """获取ETF基金公司和基金经理信息"""
    try:
        import akshare as ak
        
        info = {
            'fund_company': None,
            'fund_manager': None,
            'establish_date': None,
            'fund_type': 'ETF',
            'benchmark': None,
            'management_fee': None,
            'custody_fee': None,
            'fund_size': None
        }
        
        try:
            # 获取基金基本信息
            fund_info = ak.fund_individual_basic_info_xq(symbol=etf_code)
            if fund_info is not None and not fund_info.empty:
                info_dict = {}
                for _, row in fund_info.iterrows():
                    key = row.iloc[0] if len(row) > 0 else None
                    val = row.iloc[1] if len(row) > 1 else None
                    if key:
                        info_dict[str(key)] = val
                
                info['fund_company'] = info_dict.get('基金公司', info_dict.get('管理人', None))
                info['fund_manager'] = info_dict.get('基金经理', None)
                info['establish_date'] = info_dict.get('成立日期', info_dict.get('成立时间', None))
                info['benchmark'] = info_dict.get('业绩比较基准', None)
                info['management_fee'] = info_dict.get('管理费率', None)
                info['custody_fee'] = info_dict.get('托管费率', None)
                info['fund_size'] = info_dict.get('基金规模', info_dict.get('资产规模', None))
        except Exception as e:
            logger.warning(f"从雪球获取基金信息失败: {str(e)}")
            
            # 备用方法：从天天基金获取
            try:
                fund_info = ak.fund_open_fund_info_em(symbol=etf_code, indicator="基本信息")
                if fund_info is not None and not fund_info.empty:
                    info_dict = {}
                    for _, row in fund_info.iterrows():
                        info_dict[row['项目']] = row['数值']
                    
                    info['fund_company'] = info_dict.get('基金管理人', None)
                    info['fund_manager'] = info_dict.get('基金经理', None)
                    info['establish_date'] = info_dict.get('成立日期', None)
                    info['management_fee'] = info_dict.get('管理费率', None)
                    info['custody_fee'] = info_dict.get('托管费率', None)
            except:
                pass
        
        return jsonify({'success': True, 'data': info})
        
    except Exception as e:
        logger.error(f"获取ETF信息失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 用户策略管理 API ====================

from backtesting.strategy_models import (
    StrategyConfig, FilterCondition, StrategyValidator, 
    calculate_equal_weights, validate_weights_sum
)
from backtesting.builtin_strategies import get_builtin_strategies_manager


@app.route('/api/user-strategies', methods=['GET'])
def get_user_strategies():
    """获取用户策略列表"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        sql = """
        SELECT id, user_id, name, description, config, created_at, updated_at
        FROM user_strategies
        WHERE user_id = :user_id
        ORDER BY updated_at DESC
        """
        
        df = db_manager.execute_query(sql, {'user_id': user_id})
        
        if df.empty:
            return jsonify({'success': True, 'data': [], 'total': 0})
        
        strategies = []
        for _, row in df.iterrows():
            strategy = {
                'id': int(row['id']),
                'user_id': row['user_id'],
                'name': row['name'],
                'description': row['description'] if pd.notna(row['description']) else '',
                'config': json.loads(row['config']) if isinstance(row['config'], str) else row['config'],
                'created_at': str(row['created_at']),
                'updated_at': str(row['updated_at'])
            }
            strategies.append(strategy)
        
        return jsonify({'success': True, 'data': strategies, 'total': len(strategies)})
        
    except Exception as e:
        logger.error(f"获取用户策略列表失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user-strategies', methods=['POST'])
def create_user_strategy():
    """创建新策略"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default_user')
        name = data.get('name', '').strip()
        description = data.get('description', '')
        config_data = data.get('config', {})
        
        # 验证策略名称
        if not name:
            return jsonify({'success': False, 'error': '策略名称不能为空'}), 400
        
        # 构建策略配置对象并验证
        try:
            strategy_config = StrategyConfig.from_dict(config_data)
            strategy_config.name = name
            strategy_config.description = description
            
            is_valid, errors = StrategyValidator.validate_strategy_config(strategy_config)
            if not is_valid:
                error_messages = [err.to_dict() for err in errors]
                return jsonify({
                    'success': False, 
                    'error': '策略配置验证失败',
                    'validation_errors': error_messages
                }), 400
        except Exception as e:
            return jsonify({'success': False, 'error': f'策略配置解析失败: {str(e)}'}), 400
        
        # 序列化配置为JSON
        config_json = json.dumps(strategy_config.to_dict(), ensure_ascii=False)
        
        sql = """
        INSERT INTO user_strategies (user_id, name, description, config)
        VALUES (:user_id, :name, :description, :config)
        """
        
        success = db_manager.execute_sql(sql, {
            'user_id': user_id,
            'name': name,
            'description': description,
            'config': config_json
        })
        
        if success:
            # 获取新创建的策略ID
            id_sql = "SELECT LAST_INSERT_ID() as id"
            id_df = db_manager.execute_query(id_sql)
            new_id = int(id_df.iloc[0]['id']) if not id_df.empty else None
            
            return jsonify({
                'success': True, 
                'message': '策略创建成功',
                'data': {'id': new_id, 'name': name}
            })
        else:
            return jsonify({'success': False, 'error': '策略创建失败'}), 500
            
    except Exception as e:
        logger.error(f"创建策略失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user-strategies/<int:strategy_id>', methods=['GET'])
def get_user_strategy(strategy_id):
    """获取策略详情"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        sql = """
        SELECT id, user_id, name, description, config, created_at, updated_at
        FROM user_strategies
        WHERE id = :strategy_id AND user_id = :user_id
        """
        
        df = db_manager.execute_query(sql, {'strategy_id': strategy_id, 'user_id': user_id})
        
        if df.empty:
            return jsonify({'success': False, 'error': '策略不存在'}), 404
        
        row = df.iloc[0]
        strategy = {
            'id': int(row['id']),
            'user_id': row['user_id'],
            'name': row['name'],
            'description': row['description'] if pd.notna(row['description']) else '',
            'config': json.loads(row['config']) if isinstance(row['config'], str) else row['config'],
            'created_at': str(row['created_at']),
            'updated_at': str(row['updated_at'])
        }
        
        return jsonify({'success': True, 'data': strategy})
        
    except Exception as e:
        logger.error(f"获取策略详情失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user-strategies/<int:strategy_id>', methods=['PUT'])
def update_user_strategy(strategy_id):
    """更新策略"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default_user')
        
        # 检查策略是否存在
        check_sql = "SELECT id FROM user_strategies WHERE id = :strategy_id AND user_id = :user_id"
        check_df = db_manager.execute_query(check_sql, {'strategy_id': strategy_id, 'user_id': user_id})
        
        if check_df.empty:
            return jsonify({'success': False, 'error': '策略不存在'}), 404
        
        # 构建更新字段
        update_fields = []
        params = {'strategy_id': strategy_id, 'user_id': user_id}
        
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({'success': False, 'error': '策略名称不能为空'}), 400
            update_fields.append('name = :name')
            params['name'] = name
        
        if 'description' in data:
            update_fields.append('description = :description')
            params['description'] = data['description']
        
        if 'config' in data:
            config_data = data['config']
            try:
                strategy_config = StrategyConfig.from_dict(config_data)
                
                # 如果更新了名称，同步到config
                if 'name' in data:
                    strategy_config.name = data['name'].strip()
                if 'description' in data:
                    strategy_config.description = data['description']
                
                is_valid, errors = StrategyValidator.validate_strategy_config(strategy_config)
                if not is_valid:
                    error_messages = [err.to_dict() for err in errors]
                    return jsonify({
                        'success': False,
                        'error': '策略配置验证失败',
                        'validation_errors': error_messages
                    }), 400
                
                config_json = json.dumps(strategy_config.to_dict(), ensure_ascii=False)
                update_fields.append('config = :config')
                params['config'] = config_json
            except Exception as e:
                return jsonify({'success': False, 'error': f'策略配置解析失败: {str(e)}'}), 400
        
        if not update_fields:
            return jsonify({'success': False, 'error': '没有要更新的字段'}), 400
        
        sql = f"""
        UPDATE user_strategies 
        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
        WHERE id = :strategy_id AND user_id = :user_id
        """
        
        success = db_manager.execute_sql(sql, params)
        
        if success:
            return jsonify({'success': True, 'message': '策略更新成功'})
        else:
            return jsonify({'success': False, 'error': '策略更新失败'}), 500
            
    except Exception as e:
        logger.error(f"更新策略失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user-strategies/<int:strategy_id>', methods=['DELETE'])
def delete_user_strategy(strategy_id):
    """删除策略"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # 检查策略是否存在
        check_sql = "SELECT id FROM user_strategies WHERE id = :strategy_id AND user_id = :user_id"
        check_df = db_manager.execute_query(check_sql, {'strategy_id': strategy_id, 'user_id': user_id})
        
        if check_df.empty:
            return jsonify({'success': False, 'error': '策略不存在'}), 404
        
        sql = "DELETE FROM user_strategies WHERE id = :strategy_id AND user_id = :user_id"
        success = db_manager.execute_sql(sql, {'strategy_id': strategy_id, 'user_id': user_id})
        
        if success:
            return jsonify({'success': True, 'message': '策略删除成功'})
        else:
            return jsonify({'success': False, 'error': '策略删除失败'}), 500
            
    except Exception as e:
        logger.error(f"删除策略失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user-strategies/<int:strategy_id>/copy', methods=['POST'])
def copy_user_strategy(strategy_id):
    """复制策略"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        new_name = data.get('name', '').strip()
        
        # 获取原策略
        sql = """
        SELECT name, description, config
        FROM user_strategies
        WHERE id = :strategy_id AND user_id = :user_id
        """
        
        df = db_manager.execute_query(sql, {'strategy_id': strategy_id, 'user_id': user_id})
        
        if df.empty:
            return jsonify({'success': False, 'error': '原策略不存在'}), 404
        
        row = df.iloc[0]
        original_name = row['name']
        description = row['description'] if pd.notna(row['description']) else ''
        config = row['config']
        
        # 生成新名称
        if not new_name:
            new_name = f"{original_name} (副本)"
        
        # 更新config中的名称
        config_dict = json.loads(config) if isinstance(config, str) else config
        config_dict['name'] = new_name
        config_json = json.dumps(config_dict, ensure_ascii=False)
        
        # 插入新策略
        insert_sql = """
        INSERT INTO user_strategies (user_id, name, description, config)
        VALUES (:user_id, :name, :description, :config)
        """
        
        success = db_manager.execute_sql(insert_sql, {
            'user_id': user_id,
            'name': new_name,
            'description': description,
            'config': config_json
        })
        
        if success:
            # 获取新创建的策略ID
            id_sql = "SELECT LAST_INSERT_ID() as id"
            id_df = db_manager.execute_query(id_sql)
            new_id = int(id_df.iloc[0]['id']) if not id_df.empty else None
            
            return jsonify({
                'success': True,
                'message': '策略复制成功',
                'data': {'id': new_id, 'name': new_name}
            })
        else:
            return jsonify({'success': False, 'error': '策略复制失败'}), 500
            
    except Exception as e:
        logger.error(f"复制策略失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user-strategies/validate', methods=['POST'])
def validate_strategy_config():
    """验证策略配置（不保存）"""
    try:
        data = request.get_json()
        config_data = data.get('config', {})
        
        try:
            strategy_config = StrategyConfig.from_dict(config_data)
            is_valid, errors = StrategyValidator.validate_strategy_config(strategy_config)
            
            if is_valid:
                return jsonify({
                    'success': True,
                    'valid': True,
                    'message': '策略配置验证通过'
                })
            else:
                error_messages = [err.to_dict() for err in errors]
                return jsonify({
                    'success': True,
                    'valid': False,
                    'validation_errors': error_messages
                })
        except Exception as e:
            return jsonify({
                'success': True,
                'valid': False,
                'error': f'策略配置解析失败: {str(e)}'
            })
            
    except Exception as e:
        logger.error(f"验证策略配置失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user-strategies/filter-fields', methods=['GET'])
def get_filter_fields():
    """获取支持的筛选字段列表"""
    try:
        from backtesting.strategy_models import SUPPORTED_FILTER_FIELDS, SUPPORTED_SORT_FIELDS
        
        filter_fields = []
        for field_name, field_info in SUPPORTED_FILTER_FIELDS.items():
            filter_fields.append({
                'name': field_name,
                'type': field_info['type'],
                'description': field_info['description']
            })
        
        return jsonify({
            'success': True,
            'data': {
                'filter_fields': filter_fields,
                'sort_fields': SUPPORTED_SORT_FIELDS,
                'operators': ['>', '<', '>=', '<=', '==', '!='],
                'filter_logic': ['AND', 'OR'],
                'sort_orders': ['ASC', 'DESC'],
                'weight_modes': ['equal', 'custom']
            }
        })
        
    except Exception as e:
        logger.error(f"获取筛选字段失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 内置策略 API ====================

@app.route('/api/builtin-strategies', methods=['GET'])
def get_builtin_strategies():
    """获取内置策略列表
    
    Returns:
        所有内置策略的 key, name, description
    """
    try:
        manager = get_builtin_strategies_manager()
        strategies = manager.get_all()
        
        return jsonify({
            'success': True,
            'data': strategies,
            'total': len(strategies)
        })
        
    except Exception as e:
        logger.error(f"获取内置策略列表失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/builtin-strategies/<strategy_key>', methods=['GET'])
def get_builtin_strategy_detail(strategy_key):
    """获取内置策略详情
    
    Args:
        strategy_key: 策略唯一标识
        
    Returns:
        完整的策略配置（key, name, description, config）
    """
    try:
        manager = get_builtin_strategies_manager()
        strategy = manager.get_by_key(strategy_key)
        
        if strategy is None:
            return jsonify({
                'success': False,
                'error': f'内置策略不存在: {strategy_key}'
            }), 404
        
        return jsonify({
            'success': True,
            'data': strategy.to_dict()
        })
        
    except Exception as e:
        logger.error(f"获取内置策略详情失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/builtin-strategies/<strategy_key>/apply', methods=['POST'])
def apply_builtin_strategy(strategy_key):
    """应用内置策略创建新的用户策略
    
    Args:
        strategy_key: 策略唯一标识
        
    Request Body:
        custom_name (optional): 自定义策略名称
        user_id (optional): 用户ID，默认为 'default_user'
        
    Returns:
        新创建的策略 ID 和详情
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        custom_name = data.get('custom_name', '').strip()
        
        # 获取内置策略
        manager = get_builtin_strategies_manager()
        builtin_strategy = manager.get_by_key(strategy_key)
        
        if builtin_strategy is None:
            return jsonify({
                'success': False,
                'error': f'内置策略不存在: {strategy_key}'
            }), 404
        
        # 确定策略名称
        if custom_name:
            strategy_name = custom_name
        else:
            # 使用内置策略名称加时间戳后缀
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            strategy_name = f"{builtin_strategy.name}_{timestamp}"
        
        # 复制策略配置
        config_dict = builtin_strategy.config.to_dict()
        config_dict['name'] = strategy_name
        
        # 序列化配置为JSON
        config_json = json.dumps(config_dict, ensure_ascii=False)
        
        # 保存到数据库
        sql = """
        INSERT INTO user_strategies (user_id, name, description, config)
        VALUES (:user_id, :name, :description, :config)
        """
        
        success = db_manager.execute_sql(sql, {
            'user_id': user_id,
            'name': strategy_name,
            'description': builtin_strategy.description,
            'config': config_json
        })
        
        if success:
            # 获取新创建的策略ID
            id_sql = "SELECT LAST_INSERT_ID() as id"
            id_df = db_manager.execute_query(id_sql)
            new_id = int(id_df.iloc[0]['id']) if not id_df.empty else None
            
            return jsonify({
                'success': True,
                'message': '策略应用成功',
                'data': {
                    'id': new_id,
                    'name': strategy_name,
                    'description': builtin_strategy.description,
                    'config': config_dict,
                    'source_builtin_key': strategy_key
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '创建策略失败'
            }), 500
            
    except Exception as e:
        logger.error(f"应用内置策略失败: {str(e)}")
        return jsonify({'success': False, 'error': f'创建策略失败: {str(e)}'}), 500


# ==================== 策略回测 API ====================

from backtesting.backtest_api import (
    BacktestAPIHandler, TradeRecordFilter, CSVExporter,
    get_task_manager
)

# 全局回测API处理器
backtest_handler = None

def get_backtest_handler():
    """获取回测API处理器"""
    global backtest_handler
    if backtest_handler is None:
        backtest_handler = BacktestAPIHandler(
            db_manager=db_manager,
            fund_data_manager=fund_data_manager
        )
    return backtest_handler


@app.route('/api/strategy-backtest/run', methods=['POST'])
def run_strategy_backtest():
    """执行策略回测"""
    try:
        data = request.get_json()
        strategy_id = data.get('strategy_id')
        user_id = data.get('user_id', 'default_user')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        initial_capital = data.get('initial_capital', 100000.0)
        rebalance_freq = data.get('rebalance_freq', 'monthly')
        
        if not strategy_id:
            return jsonify({'success': False, 'error': '策略ID不能为空'}), 400
        
        handler = get_backtest_handler()
        success, result = handler.run_backtest(
            strategy_id=strategy_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            rebalance_freq=rebalance_freq
        )
        
        if success:
            return jsonify({'success': True, 'data': result})
        else:
            return jsonify({'success': False, 'error': result.get('error', '回测失败')}), 500
            
    except Exception as e:
        logger.error(f"执行策略回测失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategy-backtest/status/<task_id>', methods=['GET'])
def get_backtest_status(task_id):
    """获取回测状态"""
    try:
        handler = get_backtest_handler()
        success, result = handler.get_backtest_status(task_id)
        
        if success:
            return jsonify({'success': True, 'data': result})
        else:
            return jsonify({'success': False, 'error': result.get('error', '获取状态失败')}), 404
            
    except Exception as e:
        logger.error(f"获取回测状态失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategy-backtest/result/<task_id>', methods=['GET'])
def get_backtest_result(task_id):
    """获取回测结果"""
    try:
        # 获取筛选参数
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        fund_code = request.args.get('fund_code')
        action = request.args.get('action')
        
        handler = get_backtest_handler()
        success, result = handler.get_backtest_result(
            task_id=task_id,
            start_date=start_date,
            end_date=end_date,
            fund_code=fund_code,
            action=action
        )
        
        if success:
            return jsonify({'success': True, 'data': result})
        else:
            status_code = 404 if '不存在' in result.get('error', '') else 400
            return jsonify({'success': False, 'error': result.get('error', '获取结果失败')}), status_code
            
    except Exception as e:
        logger.error(f"获取回测结果失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategy-backtest/export/<task_id>', methods=['GET'])
def export_backtest_trades(task_id):
    """导出交易记录为CSV"""
    try:
        from flask import Response
        
        # 获取筛选参数
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        fund_code = request.args.get('fund_code')
        action = request.args.get('action')
        
        handler = get_backtest_handler()
        success, result = handler.export_trades_csv(
            task_id=task_id,
            start_date=start_date,
            end_date=end_date,
            fund_code=fund_code,
            action=action
        )
        
        if success:
            # 返回CSV文件
            filename = f"trades_{task_id}.csv"
            return Response(
                result,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename={filename}',
                    'Content-Type': 'text/csv; charset=utf-8-sig'
                }
            )
        else:
            return jsonify({'success': False, 'error': result}), 404
            
    except Exception as e:
        logger.error(f"导出交易记录失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategy-backtest/trades/filter', methods=['POST'])
def filter_backtest_trades():
    """筛选交易记录（独立接口）"""
    try:
        data = request.get_json()
        trades = data.get('trades', [])
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        fund_code = data.get('fund_code')
        action = data.get('action')
        
        filtered_trades = TradeRecordFilter.filter_trades(
            trades=trades,
            start_date=start_date,
            end_date=end_date,
            fund_code=fund_code,
            action=action
        )
        
        return jsonify({
            'success': True,
            'data': {
                'trades': filtered_trades,
                'total': len(filtered_trades)
            }
        })
        
    except Exception as e:
        logger.error(f"筛选交易记录失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    init_components()
    app.run(host='0.0.0.0', port=5000, debug=True)
else:
    # 当作为模块导入时，自动初始化组件
    init_components()
