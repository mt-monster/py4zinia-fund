#!/usr/bin/env python
# coding: utf-8

"""
重构版投资建议页面 API 路由
提供基金组合选择、策略应用、回测分析和投资建议生成功能
"""

import os
import sys
import json
import math
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import pandas as pd
import numpy as np
from flask import jsonify, request

# 添加父目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 初始化日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 全局变量（由 register_routes 函数初始化）
db_manager = None
fund_data_manager = None
holding_service = None


def _safe_float(value, default=0.0):
    """安全地转换浮点数"""
    try:
        if value is None:
            return default
        if isinstance(value, str):
            if value.upper() in ('NAN', 'NULL', 'NONE', ''):
                return default
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except:
        return default


# ==================== API路由 ====================


def get_my_holdings():
    """
    获取我的持仓列表
    
    Returns:
        持仓基金列表，包含基金代码、名称、份额、成本等信息
    """
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        sql = """
        SELECT 
            h.fund_code,
            h.fund_name,
            h.shares,
            h.cost_price,
            h.total_cost,
            h.notes,
            h.last_updated,
            COALESCE(f.latest_nav, 0) as latest_nav,
            COALESCE(f.nav_date, '') as nav_date,
            COALESCE(f.today_return, 0) as today_return
        FROM user_holdings h
        LEFT JOIN fund_nav f ON h.fund_code = f.fund_code
        WHERE h.user_id = :user_id
        ORDER BY h.total_cost DESC
        """
        
        df = db_manager.execute_query(sql, {'user_id': user_id})
        
        if df.empty:
            return jsonify({'success': True, 'data': [], 'total': 0})
        
        holdings = []
        for _, row in df.iterrows():
            shares = _safe_float(row.get('shares'), 0)
            cost_price = _safe_float(row.get('cost_price'), 0)
            latest_nav = _safe_float(row.get('latest_nav'), 0)
            today_return = _safe_float(row.get('today_return'), 0)
            
            # 计算市值和盈亏
            market_value = shares * latest_nav if shares and latest_nav else 0
            total_cost = _safe_float(row.get('total_cost'), shares * cost_price if shares and cost_price else 0)
            profit_loss = market_value - total_cost if market_value and total_cost else 0
            profit_loss_pct = (profit_loss / total_cost * 100) if total_cost else 0
            
            holding = {
                'fund_code': row['fund_code'],
                'fund_name': row['fund_name'] if pd.notna(row['fund_name']) else row['fund_code'],
                'shares': round(shares, 4) if shares else 0,
                'cost_price': round(cost_price, 4) if cost_price else 0,
                'latest_nav': round(latest_nav, 4) if latest_nav else 0,
                'total_cost': round(total_cost, 2) if total_cost else 0,
                'market_value': round(market_value, 2) if market_value else 0,
                'profit_loss': round(profit_loss, 2) if profit_loss else 0,
                'profit_loss_pct': round(profit_loss_pct, 2) if profit_loss_pct else 0,
                'today_return': round(today_return, 2) if today_return else 0,
                'nav_date': str(row['nav_date']) if pd.notna(row['nav_date']) else '',
                'notes': row['notes'] if pd.notna(row['notes']) else '',
                'last_updated': str(row['last_updated']) if pd.notna(row['last_updated']) else ''
            }
            holdings.append(holding)
        
        return jsonify({
            'success': True, 
            'data': holdings, 
            'total': len(holdings)
        })
        
    except Exception as e:
        logger.error(f"获取持仓列表失败: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def get_my_strategies():
    """
    获取我的策略列表
    
    Returns:
        用户策略列表，包含策略配置和描述
    """
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        sql = """
        SELECT 
            id,
            name,
            description,
            config,
            created_at,
            updated_at
        FROM user_strategies
        WHERE user_id = :user_id
        ORDER BY updated_at DESC
        """
        
        df = db_manager.execute_query(sql, {'user_id': user_id})
        
        if df.empty:
            return jsonify({'success': True, 'data': [], 'total': 0})
        
        strategies = []
        strategy_type_map = {
            'fixed_amount': '固定金额定投',
            'fixed_ratio': '固定比例定投',
            'value_averaging': '价值平均定投',
            'momentum': '动量策略',
            'mean_reversion': '均值回归',
            'dual_ma': '双均线策略',
            'grid_trading': '网格交易',
            'enhanced': '增强策略',
            'custom': '自定义策略'
        }
        
        for _, row in df.iterrows():
            config = {}
            if pd.notna(row['config']):
                try:
                    config = json.loads(row['config']) if isinstance(row['config'], str) else row['config']
                except:
                    config = {}
            
            strategy_type = config.get('strategy_type', 'custom')
            
            strategy = {
                'id': int(row['id']),
                'name': row['name'],
                'description': row['description'] if pd.notna(row['description']) else '',
                'type': strategy_type,
                'type_name': strategy_type_map.get(strategy_type, '自定义'),
                'config': config,
                'created_at': str(row['created_at']) if pd.notna(row['created_at']) else '',
                'updated_at': str(row['updated_at']) if pd.notna(row['updated_at']) else ''
            }
            strategies.append(strategy)
        
        return jsonify({
            'success': True, 
            'data': strategies, 
            'total': len(strategies)
        })
        
    except Exception as e:
        logger.error(f"获取策略列表失败: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def run_portfolio_backtest():
    """
    执行组合回测
    
    Request Body:
        - fund_codes: 基金代码列表
        - strategy_id: 策略ID（可选，使用默认策略）
        - start_date: 开始日期 (YYYY-MM-DD)
        - end_date: 结束日期 (YYYY-MM-DD)
        - initial_capital: 初始资金
        - weights: 基金权重（可选）
    
    Returns:
        回测结果，包含收益曲线、绩效指标等
    """
    try:
        data = request.get_json()
        fund_codes = data.get('fund_codes', [])
        strategy_id = data.get('strategy_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        initial_capital = data.get('initial_capital', 100000.0)
        weights = data.get('weights', {})
        
        if not fund_codes:
            return jsonify({'success': False, 'error': '请选择至少一只基金'}), 400
        
        # 如果没有指定日期，使用最近一年
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start = datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=365)
            start_date = start.strftime('%Y-%m-%d')
        
        # 构建回测结果
        from backtesting.core.akshare_data_fetcher import fetch_fund_history_from_akshare
        from backtesting.strategies.enhanced_strategy import EnhancedInvestmentStrategy
        from backtesting.analysis.calculators import calculate_sharpe_ratio, calculate_max_drawdown
        
        portfolio_data = []
        fund_results = []
        
        # 获取每只基金的历史数据
        for fund_code in fund_codes:
            try:
                hist_data = fetch_fund_history_from_akshare(fund_code, days=365)
                if hist_data is not None and not hist_data.empty:
                    portfolio_data.append({
                        'fund_code': fund_code,
                        'data': hist_data
                    })
            except Exception as e:
                logger.warning(f"获取基金 {fund_code} 历史数据失败: {e}")
        
        if not portfolio_data:
            return jsonify({'success': False, 'error': '无法获取基金历史数据'}), 400
        
        # 执行回测逻辑
        strategy = EnhancedInvestmentStrategy()
        
        # 模拟回测结果
        # 实际应该根据策略配置执行完整回测
        backtest_results = []
        dates = []
        portfolio_values = []
        
        # 简化回测：计算等权重组合的表现
        total_return = 0
        weighted_returns = []
        
        for fund_info in portfolio_data:
            fund_code = fund_info['fund_code']
            df = fund_info['data']
            
            # 计算基金收益率
            if len(df) >= 2:
                start_nav = float(df.iloc[0]['nav'])
                end_nav = float(df.iloc[-1]['nav'])
                fund_return = (end_nav - start_nav) / start_nav * 100
                
                # 计算最大回撤
                nav_series = df['nav'].astype(float)
                max_dd = calculate_max_drawdown(nav_series)
                
                # 计算夏普比率
                returns = nav_series.pct_change().dropna()
                sharpe = calculate_sharpe_ratio(returns) if len(returns) > 1 else 0
                
                fund_weight = weights.get(fund_code, 1.0 / len(portfolio_data))
                weighted_return = fund_return * fund_weight
                weighted_returns.append(weighted_return)
                
                fund_results.append({
                    'fund_code': fund_code,
                    'fund_name': get_fund_name_from_db(fund_code) or fund_code,
                    'start_nav': round(start_nav, 4),
                    'end_nav': round(end_nav, 4),
                    'total_return': round(fund_return, 2),
                    'max_drawdown': round(max_dd * 100, 2) if max_dd else 0,
                    'sharpe_ratio': round(sharpe, 2) if sharpe else 0,
                    'weight': round(fund_weight * 100, 2),
                    'data_points': len(df)
                })
        
        # 计算组合整体指标
        total_return = sum(weighted_returns)
        annualized_return = total_return / 365 * 252 if total_return else 0
        
        # 生成收益曲线数据（简化版本）
        chart_data = generate_portfolio_return_curve(portfolio_data, weights, initial_capital)
        
        result = {
            'fund_codes': fund_codes,
            'strategy_id': strategy_id,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': initial_capital,
            'fund_results': fund_results,
            'portfolio_summary': {
                'total_return': round(total_return, 2),
                'annualized_return': round(annualized_return, 2),
                'backtest_days': 365
            },
            'chart_data': chart_data
        }
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"执行组合回测失败: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def generate_portfolio_return_curve(portfolio_data, weights, initial_capital):
    """生成组合收益曲线数据"""
    try:
        # 合并所有基金的日期
        all_dates = set()
        fund_returns = {}
        
        for fund_info in portfolio_data:
            fund_code = fund_info['fund_code']
            df = fund_info['data'].copy()
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            fund_weight = weights.get(fund_code, 1.0 / len(portfolio_data))
            
            # 计算每日收益率
            df['daily_return'] = df['nav'].astype(float).pct_change()
            
            fund_returns[fund_code] = {
                'data': df,
                'weight': fund_weight
            }
            
            all_dates.update(df['date'].tolist())
        
        # 按日期排序
        sorted_dates = sorted(all_dates)
        
        # 计算组合每日价值
        portfolio_values = []
        dates = []
        
        current_value = initial_capital
        
        for date in sorted_dates:
            daily_portfolio_return = 0
            valid_funds = 0
            
            for fund_code, fund_data in fund_returns.items():
                df = fund_data['data']
                weight = fund_data['weight']
                
                # 查找当天的数据
                day_data = df[df['date'] == date]
                if not day_data.empty:
                    daily_return = day_data['daily_return'].values[0]
                    if not pd.isna(daily_return):
                        daily_portfolio_return += daily_return * weight
                        valid_funds += 1
            
            if valid_funds > 0:
                current_value = current_value * (1 + daily_portfolio_return)
            
            dates.append(date.strftime('%Y-%m-%d'))
            portfolio_values.append(round(current_value, 2))
        
        return {
            'dates': dates,
            'portfolio_values': portfolio_values,
            'initial_capital': initial_capital,
            'final_value': portfolio_values[-1] if portfolio_values else initial_capital
        }
        
    except Exception as e:
        logger.error(f"生成收益曲线失败: {e}")
        return {
            'dates': [],
            'portfolio_values': [],
            'initial_capital': initial_capital,
            'final_value': initial_capital
        }


def generate_investment_advice():
    """
    生成综合投资建议
    
    基于持仓基金、策略回测结果和当日估值数据生成投资建议
    
    Request Body:
        - fund_codes: 基金代码列表
        - strategy_id: 策略ID（可选）
        - backtest_data: 回测结果数据（可选）
    
    Returns:
        针对每只基金的具体投资建议
    """
    try:
        data = request.get_json()
        fund_codes = data.get('fund_codes', [])
        strategy_id = data.get('strategy_id')
        
        if not fund_codes:
            return jsonify({'success': False, 'error': '请选择至少一只基金'}), 400
        
        # 调用原有的个性化建议生成逻辑
        from web.routes.analysis import get_personalized_investment_advice_parallel
        
        advice_result = get_personalized_investment_advice_parallel(fund_codes)
        
        if not advice_result.get('success'):
            return jsonify(advice_result), 500
        
        # 获取持仓信息
        user_id = data.get('user_id', 'default_user')
        holdings = get_holdings_for_advice(user_id, fund_codes)
        
        # 整合持仓信息到建议结果
        for fund in advice_result.get('funds', []):
            fund_code = fund.get('fund_code')
            if fund_code in holdings:
                fund['holding'] = holdings[fund_code]
                
                # 根据持仓和估值生成具体操作建议
                fund['detailed_advice'] = generate_detailed_advice(fund, holdings[fund_code])
        
        # 添加策略信息
        if strategy_id:
            strategy = get_strategy_info(strategy_id)
            advice_result['strategy'] = strategy
        
        return jsonify(advice_result)
        
    except Exception as e:
        logger.error(f"生成投资建议失败: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def get_holdings_for_advice(user_id: str, fund_codes: List[str]) -> Dict[str, Any]:
    """获取用于建议的持仓信息"""
    try:
        if not fund_codes:
            return {}
        
        placeholders = ','.join([f':code_{i}' for i in range(len(fund_codes))])
        params = {f'code_{i}': code for i, code in enumerate(fund_codes)}
        params['user_id'] = user_id
        
        sql = f"""
        SELECT 
            h.fund_code,
            h.shares,
            h.cost_price,
            h.total_cost,
            COALESCE(f.latest_nav, 0) as latest_nav,
            COALESCE(f.today_return, 0) as today_return
        FROM user_holdings h
        LEFT JOIN fund_nav f ON h.fund_code = f.fund_code
        WHERE h.user_id = :user_id AND h.fund_code IN ({placeholders})
        """
        
        df = db_manager.execute_query(sql, params)
        
        holdings = {}
        for _, row in df.iterrows():
            shares = _safe_float(row.get('shares'), 0)
            cost_price = _safe_float(row.get('cost_price'), 0)
            latest_nav = _safe_float(row.get('latest_nav'), 0)
            today_return = _safe_float(row.get('today_return'), 0)
            
            market_value = shares * latest_nav if shares and latest_nav else 0
            total_cost = _safe_float(row.get('total_cost'), 0)
            profit_loss = market_value - total_cost if market_value and total_cost else 0
            profit_loss_pct = (profit_loss / total_cost * 100) if total_cost else 0
            
            holdings[row['fund_code']] = {
                'shares': round(shares, 4),
                'cost_price': round(cost_price, 4),
                'latest_nav': round(latest_nav, 4),
                'market_value': round(market_value, 2),
                'total_cost': round(total_cost, 2),
                'profit_loss': round(profit_loss, 2),
                'profit_loss_pct': round(profit_loss_pct, 2),
                'today_return': round(today_return, 2)
            }
        
        return holdings
        
    except Exception as e:
        logger.error(f"获取持仓信息失败: {e}")
        return {}


def get_strategy_info(strategy_id: int) -> Optional[Dict]:
    """获取策略信息"""
    try:
        sql = """
        SELECT id, name, description, config
        FROM user_strategies
        WHERE id = :strategy_id
        """
        df = db_manager.execute_query(sql, {'strategy_id': strategy_id})
        
        if df.empty:
            return None
        
        row = df.iloc[0]
        config = {}
        if pd.notna(row['config']):
            try:
                config = json.loads(row['config']) if isinstance(row['config'], str) else row['config']
            except:
                pass
        
        return {
            'id': int(row['id']),
            'name': row['name'],
            'description': row['description'] if pd.notna(row['description']) else '',
            'config': config
        }
        
    except Exception as e:
        logger.error(f"获取策略信息失败: {e}")
        return None


def generate_detailed_advice(fund_data: Dict, holding: Dict) -> Dict:
    """
    生成详细的投资建议
    
    基于估值、持仓盈亏和策略信号生成具体操作建议
    """
    advice = fund_data.get('advice', {})
    action = advice.get('action', 'hold')
    today_return = fund_data.get('today_return', 0)
    profit_loss_pct = holding.get('profit_loss_pct', 0)
    market_value = holding.get('market_value', 0)
    
    # 基础建议
    detailed = {
        'action': action,
        'action_name': get_action_name(action),
        'reason': advice.get('reason', ''),
        'suggestion': advice.get('suggestion', '')
    }
    
    # 根据持仓盈亏调整建议
    if profit_loss_pct > 20 and action in ['sell', 'strong_sell']:
        detailed['adjustment'] = '建议止盈'
        detailed['amount_suggestion'] = f'可考虑减仓 {min(30, int(profit_loss_pct / 2))}%'
    elif profit_loss_pct < -15 and action in ['buy', 'strong_buy']:
        detailed['adjustment'] = '适合补仓'
        detailed['amount_suggestion'] = '建议分批补仓，单次不超过持仓的20%'
    elif -5 <= profit_loss_pct <= 5:
        detailed['adjustment'] = '成本区附近'
        detailed['amount_suggestion'] = '可小仓位操作或观望'
    else:
        detailed['adjustment'] = '正常持有'
        detailed['amount_suggestion'] = '按策略信号执行'
    
    # 今日估值判断
    if today_return > 2:
        detailed['valuation_comment'] = '今日大涨，不适合追高买入'
    elif today_return < -2:
        detailed['valuation_comment'] = '今日大跌，是买入机会'
    else:
        detailed['valuation_comment'] = '今日估值正常'
    
    # 计算建议金额（如果有持仓）
    if market_value > 0:
        multiplier = advice.get('amount_multiplier', 1.0)
        base_amount = market_value * 0.1 * multiplier  # 建议为市值的10% * 倍数
        detailed['suggested_amount'] = round(base_amount, 2)
    
    return detailed


def get_action_name(action: str) -> str:
    """获取操作名称"""
    action_names = {
        'buy': '买入',
        'strong_buy': '强烈买入',
        'weak_buy': '弱买入',
        'sell': '卖出',
        'strong_sell': '强烈卖出',
        'redeem': '赎回',
        'hold': '持有',
        'watch': '观望'
    }
    return action_names.get(action, '持有')


def get_fund_name_from_db(fund_code: str) -> Optional[str]:
    """从数据库获取基金名称"""
    try:
        sql = "SELECT name FROM fund_basic WHERE code = :code"
        df = db_manager.execute_query(sql, {'code': fund_code})
        if not df.empty and pd.notna(df.iloc[0]['name']):
            return df.iloc[0]['name']
        return fund_code
    except:
        return fund_code


def get_fund_valuation():
    """获取基金估值数据"""
    try:
        fund_codes = request.args.getlist('fund_codes') or request.json.get('fund_codes', [])
        
        if not fund_codes:
            return jsonify({'success': False, 'error': '请提供基金代码'}), 400
        
        from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
        
        adapter = MultiSourceDataAdapter()
        valuations = []
        
        for fund_code in fund_codes:
            try:
                data = adapter.get_realtime_data(fund_code, '')
                valuations.append({
                    'fund_code': fund_code,
                    'fund_name': data.get('name', fund_code),
                    'today_return': _safe_float(data.get('today_return'), 0),
                    'estimated_nav': _safe_float(data.get('estimated_nav'), 0),
                    'last_nav': _safe_float(data.get('last_nav'), 0),
                    'update_time': data.get('update_time', '')
                })
            except Exception as e:
                logger.warning(f"获取基金 {fund_code} 估值失败: {e}")
                valuations.append({
                    'fund_code': fund_code,
                    'fund_name': fund_code,
                    'today_return': 0,
                    'estimated_nav': 0,
                    'last_nav': 0,
                    'update_time': ''
                })
        
        return jsonify({
            'success': True,
            'data': valuations
        })
        
    except Exception as e:
        logger.error(f"获取基金估值失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 路由注册 ====================

def register_routes(app, database_manager, holding_svc=None, cache_svc=None, fund_data_svc=None):
    """注册投资建议页面路由"""
    global db_manager, holding_service, fund_data_manager
    
    db_manager = database_manager
    holding_service = holding_svc
    fund_data_manager = fund_data_svc
    
    # 基金组合选择
    app.route('/api/investment-advice/holdings')(get_my_holdings)
    
    # 策略应用
    app.route('/api/investment-advice/strategies')(get_my_strategies)
    
    # 回测分析
    app.route('/api/investment-advice/backtest', methods=['POST'])(run_portfolio_backtest)
    
    # 生成投资建议
    app.route('/api/investment-advice/generate', methods=['POST'])(generate_investment_advice)
    
    # 基金估值
    app.route('/api/investment-advice/valuation')(get_fund_valuation)
    app.route('/api/investment-advice/valuation', methods=['POST'])(get_fund_valuation)
    
    logger.info("✅ 重构版投资建议页面路由已注册")
