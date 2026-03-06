#!/usr/bin/env python
# coding: utf-8

"""
策略相关的 API 路由
"""

import os
import sys
import math
import logging
import traceback
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from flask import jsonify, request

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_access.enhanced_database import EnhancedDatabaseManager
from backtesting.strategies.enhanced_strategy import EnhancedInvestmentStrategy
from backtesting.core.unified_strategy_engine import UnifiedStrategyEngine
from backtesting.analysis.strategy_evaluator import StrategyEvaluator
from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter

# 设置日志
logger = logging.getLogger(__name__)

# 全局变量 - 将在 register_routes 中被初始化
strategy_engine = None
unified_strategy_engine = None
strategy_evaluator = None
db_manager = None
fund_data_manager = None


def register_routes(app, **kwargs):
    """注册策略相关的路由
    
    Args:
        app: Flask 应用实例
        kwargs: 可选的关键字参数，用于传递全局组件
    """
    global strategy_engine, unified_strategy_engine, strategy_evaluator, db_manager, fund_data_manager
    
    # 从 kwargs 获取全局组件，如果没有则尝试从 app 获取
    db_manager = kwargs.get('db_manager') or getattr(app, 'db_manager', None)
    strategy_engine = kwargs.get('strategy_engine') or getattr(app, 'strategy_engine', None)
    unified_strategy_engine = kwargs.get('unified_strategy_engine') or getattr(app, 'unified_strategy_engine', None)
    strategy_evaluator = kwargs.get('strategy_evaluator') or getattr(app, 'strategy_evaluator', None)
    fund_data_manager = kwargs.get('fund_data_manager') or getattr(app, 'fund_data_manager', None)
    
    # 注册路由
    app.route('/api/strategies', methods=['GET'])(get_strategies)
    app.route('/api/strategy/analyze', methods=['POST'])(analyze_strategy)
    app.route('/api/strategy/unified-analyze', methods=['POST'])(unified_analyze_strategy)
    app.route('/api/strategy/config', methods=['GET'])(get_strategy_config)
    app.route('/api/strategy/evaluate', methods=['POST'])(evaluate_strategy)
    app.route('/api/strategy/backtest', methods=['POST'])(backtest_strategy)
    app.route('/api/strategy/backtest-holdings', methods=['POST'])(backtest_holdings)
    app.route('/api/strategy/compare', methods=['POST'])(compare_strategies)
    app.route('/api/summary', methods=['GET'])(get_summary)
    app.route('/api/analysis/dates', methods=['GET'])(get_analysis_dates)
    app.route('/api/funds/by-date/<date>', methods=['GET'])(get_funds_by_date)
    
    logger.info("策略路由注册完成")


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


def analyze_strategy():
    """执行策略分析（使用统一策略引擎）"""
    try:
        data = request.get_json()
        today_return = data.get('today_return', 0)
        prev_day_return = data.get('prev_day_return', 0)
        returns_history = data.get('returns_history', None)
        cumulative_pnl = data.get('cumulative_pnl', None)
        performance_metrics = data.get('performance_metrics', None)
        base_invest = data.get('base_invest', 100)  # 添加基准定投金额参数
        
        # 使用统一策略引擎进行分析
        result = unified_strategy_engine.analyze(
            today_return=today_return,
            prev_day_return=prev_day_return,
            returns_history=returns_history,
            cumulative_pnl=cumulative_pnl,
            performance_metrics=performance_metrics,
            base_invest=base_invest
        )
        
        # 转换为字典格式
        result_dict = unified_strategy_engine.to_dict(result)
        
        return jsonify({'success': True, 'data': result_dict})
    except Exception as e:
        logger.error(f"策略分析失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


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
        for key, value in result_dict.items():
            if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
                result_dict[key] = None
        
        return jsonify({'success': True, 'data': result_dict})
    except Exception as e:
        logger.error(f"策略评估失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def backtest_strategy():
    """策略回测（使用统一策略引擎）"""
    global unified_strategy_engine, db_manager
    
    # 检查 unified_strategy_engine 是否已初始化
    if unified_strategy_engine is None:
        from backtesting.core.unified_strategy_engine import UnifiedStrategyEngine
        unified_strategy_engine = UnifiedStrategyEngine()
    
    try:
        data = request.get_json()
        fund_code = data.get('fund_code')
        strategy_id = data.get('strategy_id', 'enhanced_rule_based')
        initial_amount = data.get('initial_amount', 10000)
        days = data.get('days', 90)
        base_invest = data.get('base_invest', 100)
        
        if not fund_code:
            return jsonify({'success': False, 'error': '请输入基金代码'}), 400
        
        logger.info(f"回测请求: fund_code={fund_code}, strategy_id={strategy_id}, days={days}")
        
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
        
        # 使用 _execute_single_fund_backtest 函数执行回测（支持策略选择）
        result = _execute_single_fund_backtest(fund_code, strategy_id, initial_amount, base_invest, days)
        
        if result is None:
            return jsonify({
                'success': False,
                'error': f'没有找到基金 {fund_code} 的历史数据，请确认基金代码是否正确'
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"策略回测失败: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def _execute_single_fund_backtest(fund_code, strategy_id, initial_amount, base_invest, days):
    """
    Execute backtest for a single fund.
    
    Returns backtest result dictionary or None if no data found.
    Requirements: 4.1, 4.2, 4.3, 4.4
    """
    try:
        from backtesting.core.akshare_data_fetcher import fetch_fund_history_with_fallback
        from backtesting.strategies.strategy_adapter import get_strategy_adapter
        
        df = fetch_fund_history_with_fallback(fund_code, days, db_manager)
        
        if df.empty:
            logger.warning(f"无法获取基金 {fund_code} 的历史数据")
            return None
        
        logger.info(f"基金 {fund_code} 获取到 {len(df)} 条历史数据，使用策略 {strategy_id} 开始回测...")
        
        df = df.sort_values('analysis_date', ascending=True)
        
        strategy_adapter = get_strategy_adapter()
        
        if isinstance(strategy_id, int) or (isinstance(strategy_id, str) and strategy_id.isdigit()):
            logger.info(f"策略类型: 用户自定义策略 ID={strategy_id}，使用 enhanced_rule_based 策略执行")
            actual_strategy_id = 'enhanced_rule_based'
        elif strategy_adapter.is_advanced_strategy(strategy_id):
            logger.info(f"策略类型: 内置高级策略 - {strategy_id}")
            actual_strategy_id = strategy_id
        else:
            logger.warning(f"未知的策略ID: {strategy_id}，将使用默认策略")
            actual_strategy_id = 'enhanced_rule_based'
        
        balance = initial_amount
        holdings = 0
        trades = []
        returns_history = []
        cumulative_pnl = 0.0
        
        dates = []
        equity_curve_values = []
        benchmark_values = []
        drawdown_values = []
        benchmark_value = initial_amount
        peak = initial_amount
        
        backtest_df = df.copy()
        if 'nav' not in backtest_df.columns:
            if 'current_estimate' in backtest_df.columns:
                backtest_df['nav'] = backtest_df['current_estimate']
            elif 'yesterday_nav' in backtest_df.columns:
                backtest_df['nav'] = backtest_df['yesterday_nav']
            else:
                backtest_df['nav'] = 1.0
                for i in range(1, len(backtest_df)):
                    prev_nav = backtest_df.iloc[i-1]['nav']
                    today_ret = backtest_df.iloc[i]['today_return'] / 100 if pd.notna(backtest_df.iloc[i]['today_return']) else 0
                    backtest_df.iloc[i, backtest_df.columns.get_loc('nav')] = prev_nav * (1 + today_ret)
        
        strategy_returns = []
        
        for idx, (df_idx, row) in enumerate(df.iterrows()):
            today_return = float(row['today_return']) if pd.notna(row['today_return']) else 0
            
            total_value_before = balance + holdings
            
            if holdings > 0:
                cumulative_pnl = (holdings - initial_amount + balance) / initial_amount - 1
            
            try:
                signal = strategy_adapter.generate_signal(
                    strategy_id=actual_strategy_id,
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
                logger.error(f"策略 {actual_strategy_id} 执行失败: {str(e)}")
                pass
            
            holdings *= (1 + today_return / 100)
            
            total_value_after = balance + holdings
            
            if total_value_before > 0:
                daily_strategy_return = (total_value_after - total_value_before) / total_value_before
                strategy_returns.append(daily_strategy_return)
            
            date_str = str(row['analysis_date'])[:10]
            dates.append(date_str)
            equity_curve_values.append(round(total_value_after, 2))
            
            benchmark_values.append(round(benchmark_value * (1 + today_return / 100), 2))
            benchmark_value = benchmark_values[-1]
            
            if peak > 0:
                dd = (peak - total_value_after) / peak * 100
            else:
                dd = 0
            drawdown_values.append(round(dd, 2))
            
            if total_value_after > peak:
                peak = total_value_after

        final_value = balance + holdings
        total_return = (final_value - initial_amount) / initial_amount * 100
        
        years = days / 365.0
        annual_return = ((final_value / initial_amount) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        peak = initial_amount
        max_dd = 0
        for v in equity_curve_values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        
        if len(strategy_returns) > 1:
            import numpy as np
            returns_array = np.array(strategy_returns)
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            sharpe_ratio = (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0
            volatility = float(np.std(returns_array) * np.sqrt(252) * 100)
        else:
            sharpe_ratio = 0
            volatility = 0
        
        evaluation = strategy_evaluator.evaluate(trades)
        evaluation_dict = strategy_evaluator.to_dict(evaluation)
        
        for key, value in evaluation_dict.items():
            if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
                evaluation_dict[key] = None
        
        profit_factor = evaluation_dict.get('profit_factor', 0)
        
        monthly_returns = {}
        if len(dates) > 0 and len(strategy_returns) > 0:
            for i, date_str in enumerate(dates):
                try:
                    dt = pd.to_datetime(date_str)
                    month_key = f"{dt.year}-{dt.month:02d}"
                    if month_key not in monthly_returns:
                        monthly_returns[month_key] = []
                    if i < len(strategy_returns):
                        monthly_returns[month_key].append(strategy_returns[i])
                except:
                    pass
        
        monthly_return_data = {}
        for month_key, returns in monthly_returns.items():
            if returns:
                cum_ret = 1.0
                for r in returns:
                    cum_ret *= (1 + r)
                monthly_return_data[month_key] = round((cum_ret - 1) * 100, 2)
        
        logger.info(f"回测完成: 策略={actual_strategy_id}, 最终价值={final_value:.2f}, 总收益率={total_return:.2f}%, 交易次数={len(trades)}")
        
        return {
            'fund_code': fund_code,
            'strategy_id': actual_strategy_id,
            'initial_amount': initial_amount,
            'final_value': round(final_value, 2),
            'total_return': round(total_return, 2),
            'annual_return': round(annual_return, 2),
            'max_drawdown': round(max_dd, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'volatility': round(volatility, 2),
            'profit_factor': profit_factor,
            'trades_count': len(trades),
            'trades': trades,
            'dates': dates,
            'equity_curve': equity_curve_values,
            'benchmark_curve': benchmark_values,
            'drawdown_curve': drawdown_values,
            'monthly_returns': monthly_return_data,
            'evaluation': evaluation_dict
        }

    except Exception as e:
        logger.error(f"Single fund backtest failed for {fund_code}: {str(e)}")
        traceback.print_exc()
        return None


def _execute_multi_fund_backtest(fund_codes, strategy_id, initial_amount, base_invest, days, period=None):
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
        
        # Prepare individual fund summary (including equity_curve and trades for visualization)
        # 获取基金名称映射
        fund_name_map = {}
        for result in individual_results:
            fund_code = result['fund_code']
            fund_name = fund_code  # 默认使用基金代码作为名称
            
            # 尝试从数据库获取基金名称
            name_found = False
            try:
                sql = """
                SELECT fund_name FROM fund_analysis_results 
                WHERE fund_code = :fund_code 
                ORDER BY analysis_date DESC LIMIT 1
                """
                df_name = db_manager.execute_query(sql, {'fund_code': fund_code})
                if not df_name.empty and pd.notna(df_name.iloc[0]['fund_name']):
                    fund_name = df_name.iloc[0]['fund_name']
                    logger.info(f"从 fund_analysis_results 获取基金 {fund_code} 名称: {fund_name}")
                    name_found = True
                else:
                    # 尝试从 fund_basic_info 表获取
                    try:
                        fund_info = db_manager.get_fund_detail(fund_code)
                        if fund_info and 'fund_name' in fund_info and fund_info['fund_name']:
                            fund_name = fund_info['fund_name']
                            logger.info(f"从 fund_basic_info 获取基金 {fund_code} 名称: {fund_name}")
                            name_found = True
                    except Exception as e2:
                        logger.warning(f"从 fund_basic_info 获取基金 {fund_code} 名称失败: {str(e2)}")
            except Exception as e:
                logger.warning(f"从数据库获取基金 {fund_code} 名称失败: {str(e)}")
            
            # 如果数据库中没有，尝试从 akshare 获取
            if not name_found:
                try:
                    import akshare as ak
                    # 使用 fund_name_em 接口获取基金列表
                    fund_list = ak.fund_name_em()
                    if fund_list is not None and not fund_list.empty:
                        # 使用列位置而不是列名（避免编码问题）
                        # 假设：第0列是基金代码，第3列是基金名称
                        fund_list.columns = ['code', 'pinyin_short', 'name', 'type', 'pinyin_full']
                        fund_row = fund_list[fund_list['code'] == fund_code]
                        if not fund_row.empty:
                            fund_name = fund_row.iloc[0]['name']
                            logger.info(f"从 akshare 获取基金 {fund_code} 名称: {fund_name}")
                            name_found = True
                except Exception as e3:
                    logger.warning(f"从 akshare 获取基金 {fund_code} 名称失败: {str(e3)}")
            
            fund_name_map[fund_code] = fund_name
            logger.info(f"基金 {fund_code} 最终名称: {fund_name} (来源: {'数据库' if name_found else '默认' })")
        
        fund_summaries = []
        for result in individual_results:
            fund_code = result['fund_code']
            fund_summaries.append({
                'fund_code': fund_code,
                'fund_name': fund_name_map.get(fund_code, fund_code),  # 添加基金名称
                'initial_amount': result['initial_amount'],
                'final_value': result['final_value'],
                'total_return': result['total_return'],
                'annualized_return': result['annualized_return'],
                'max_drawdown': result['max_drawdown'],
                'sharpe_ratio': result['sharpe_ratio'],
                'trades_count': result['trades_count'],
                'equity_curve': result.get('equity_curve', []),  # 添加净值曲线数据
                'trades': result.get('trades', [])  # 添加交易记录（买卖点）
            })
        
        # 组合净值曲线（使用回测引擎的 equity_curve 聚合）
        portfolio_equity_curve = []
        try:
            equity_curves = [r.get('equity_curve') for r in individual_results if r.get('equity_curve')]
            if equity_curves:
                date_sets = [set([p['date'] for p in curve]) for curve in equity_curves]
                common_dates = set.intersection(*date_sets) if date_sets else set()
                if not common_dates:
                    common_dates = set.union(*date_sets)
                sorted_dates = sorted(list(common_dates))
                curve_maps = [{p['date']: p['value'] for p in curve} for curve in equity_curves]
                
                # 获取沪深300数据作为基准
                try:
                    from web.real_data_fetcher import data_fetcher
                    from datetime import datetime
                    
                    # 根据回测的实际日期范围计算需要获取的数据天数
                    if sorted_dates:
                        first_trade_date = datetime.strptime(sorted_dates[0], '%Y-%m-%d')
                        last_trade_date = datetime.strptime(sorted_dates[-1], '%Y-%m-%d')
                        # 计算从回测开始到今天的总天数，再加一些缓冲
                        days_needed = (datetime.now() - first_trade_date).days + 60
                        logger.info(f"回测日期范围: {sorted_dates[0]} 至 {sorted_dates[-1]}, 需要获取 {days_needed} 天的沪深300数据")
                    else:
                        days_needed = days + 60
                    
                    csi300_data = data_fetcher.get_csi300_history(days_needed)
                    logger.info(f"沪深300数据获取结果: 行数={len(csi300_data) if csi300_data is not None else 0}")
                    if csi300_data is not None and not csi300_data.empty:
                        csi300_data = csi300_data.sort_values('date')
                        csi300_data['date_str'] = csi300_data['date'].dt.strftime('%Y-%m-%d')
                        price_map = dict(zip(csi300_data['date_str'], csi300_data['price']))
                        all_csi300_dates = sorted(csi300_data['date_str'].tolist())
                        
                        logger.info(f"沪深300数据日期范围: {all_csi300_dates[0] if all_csi300_dates else 'N/A'} 至 {all_csi300_dates[-1] if all_csi300_dates else 'N/A'}")
                        
                        # 找到第一个共同日期对应的沪深300价格作为基准
                        first_date = sorted_dates[0] if sorted_dates else None
                        first_price = None
                        if first_date:
                            logger.info(f"寻找基准价格，基金首日期: {first_date}")
                            if first_date in price_map:
                                first_price = price_map[first_date]
                                logger.info(f"在沪深300数据中找到精确匹配: {first_date} = {first_price}")
                            else:
                                # 查找之前最近的价格
                                earlier_dates = [d for d in all_csi300_dates if d <= first_date]
                                if earlier_dates:
                                    first_price = price_map[earlier_dates[-1]]
                                    logger.info(f"使用基金首日期之前的最近价格: {earlier_dates[-1]} = {first_price}")
                                elif all_csi300_dates:
                                    first_price = price_map[all_csi300_dates[0]]
                                    logger.warning(f"基金首日期 {first_date} 早于所有沪深300数据，使用最早可用价格: {all_csi300_dates[0]} = {first_price}")
                        
                        # 使用组合的初始金额作为基准初始值
                        base_initial_value = total_initial_amount
                        
                        if first_price is None:
                            logger.error("无法找到基准价格，基准值将保持为初始值")
                    else:
                        csi300_data = None
                        first_price = None
                        logger.warning("沪深300数据为空，基准值将保持为初始值")
                except Exception as e:
                    logger.warning(f"获取沪深300数据失败: {str(e)}")
                    csi300_data = None
                    first_price = None
                
                # 添加调试日志
                logger.info(f"开始生成组合净值曲线，基金日期数: {len(sorted_dates)}, 沪深300日期数: {len(all_csi300_dates)}")
                logger.info(f"基金首日期: {sorted_dates[0] if sorted_dates else 'N/A'}, 末日期: {sorted_dates[-1] if sorted_dates else 'N/A'}")
                logger.info(f"沪深300首日期: {all_csi300_dates[0] if all_csi300_dates else 'N/A'}, 末日期: {all_csi300_dates[-1] if all_csi300_dates else 'N/A'}")
                
                # 统计匹配情况
                matched_dates = 0
                fallback_dates = 0
                
                for date in sorted_dates:
                    total_value = 0
                    valid_count = 0
                    for curve_map in curve_maps:
                        if date in curve_map:
                            total_value += curve_map[date]
                            valid_count += 1
                    if valid_count > 0:
                        if valid_count < len(curve_maps):
                            total_value = total_value * (len(curve_maps) / valid_count)
                        
                        # 计算基准值
                        benchmark_value = base_initial_value  # 默认使用初始值
                        if csi300_data is not None and first_price is not None:
                            current_price = None
                            if date in price_map:
                                current_price = price_map[date]
                                matched_dates += 1
                            else:
                                # 查找之前最近的价格
                                earlier_dates = [d for d in all_csi300_dates if d <= date]
                                if earlier_dates:
                                    current_price = price_map[earlier_dates[-1]]
                                    fallback_dates += 1
                            
                            if current_price is not None and first_price > 0:
                                # 计算累计收益率并应用到初始值
                                cumulative_return = (current_price / first_price - 1)
                                benchmark_value = base_initial_value * (1 + cumulative_return)
                        
                        portfolio_equity_curve.append({
                            'date': date,
                            'value': round(total_value, 2),
                            'benchmark_value': round(benchmark_value, 2)  # 添加基准值
                        })
                
                logger.info(f"组合净值曲线生成完成，总数据点: {len(portfolio_equity_curve)}, 精确匹配: {matched_dates}, 使用前一日数据: {fallback_dates}")
            else:
                logger.warning("未找到有效的 equity_curve，无法生成组合净值曲线")
        except Exception as e:
            logger.warning(f"生成组合净值曲线失败: {str(e)}")
        
        # Return both individual and aggregated results (Requirement 6.4, 6.5)
        response_data = {

            'mode': 'multi_fund',
            'strategy_id': strategy_id,
            'total_funds': len(individual_results),
            'failed_funds': failed_funds,
            'days': days,
            
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
            'aggregated_fund_codes': [r['fund_code'] for r in individual_results],
            
            # 组合净值曲线（基于回测引擎）
            'portfolio_equity_curve': portfolio_equity_curve,

            
            # Full details for first fund (for UI display)
            'sample_fund_details': individual_results[0] if individual_results else None
        }

        
        # Add period information if provided
        if period is not None:
            response_data['period'] = period
        
        return jsonify({
            'success': True,
            'data': response_data
        })
        
    except Exception as e:
        logger.error(f"Multi-fund backtest failed: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


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
        period = data.get('period', 3)
        
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
        
        # Validate period (must be in [1, 2, 3, 5])
        try:
            period = int(period)
            if period not in [1, 2, 3, 5]:
                validation_errors.append('回测周期必须是1、2、3或5年')
        except (TypeError, ValueError):
            validation_errors.append('回测周期必须是有效数字')
        
        # Convert period (years) to days
        days_map = {1: 365, 2: 730, 3: 1095, 5: 1825}
        days = days_map.get(period, 1095)  # Default to 3 years (1095 days)
        
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
                fund_codes, strategy_id, initial_amount, base_invest, days, period
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
        
        # Add period information to result
        result['period'] = period
        
        # Return complete backtest results (Requirement 4.4)
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Enhanced backtest failed: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


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
        period = data.get('period', 3)
        
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
        
        # Validate period (must be in [1, 2, 3, 5])
        try:
            period = int(period)
            if period not in [1, 2, 3, 5]:
                validation_errors.append('回测周期必须是1、2、3或5年')
        except (TypeError, ValueError):
            validation_errors.append('回测周期必须是有效数字')
        
        # Convert period (years) to days
        days_map = {1: 365, 2: 730, 3: 1095, 5: 1825}
        days = days_map.get(period, 1095)  # Default to 3 years (1095 days)
        
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
        
        # 获取沪深300基准数据
        benchmark_curve = []
        try:
            from web.real_data_fetcher import data_fetcher
            csi300_data = data_fetcher.get_csi300_history(days + 60)  # 多获取一些数据以确保覆盖
            
            logger.info(f"沪深300数据获取结果: 类型={type(csi300_data)}, 空={csi300_data is None or (hasattr(csi300_data, 'empty') and csi300_data.empty)}")
            
            if csi300_data is not None and not csi300_data.empty:
                logger.info(f"沪深300数据列: {list(csi300_data.columns)}, 行数: {len(csi300_data)}")
                
                # 使用第一个策略的equity_curve日期作为基准
                if comparison_results and comparison_results[0].get('equity_curve'):
                    strategy_dates = [point['date'] for point in comparison_results[0]['equity_curve']]
                    logger.info(f"策略日期样本: 首={strategy_dates[0] if strategy_dates else 'N/A'}, 末={strategy_dates[-1] if strategy_dates else 'N/A'}, 总数={len(strategy_dates)}")
                    
                    # 处理沪深300数据 - 创建日期到价格的映射
                    csi300_data = csi300_data.sort_values('date')
                    csi300_data['date_str'] = csi300_data['date'].dt.strftime('%Y-%m-%d')
                    
                    # 创建日期->价格映射，便于快速查找
                    price_map = dict(zip(csi300_data['date_str'], csi300_data['price']))
                    all_csi300_dates = sorted(csi300_data['date_str'].tolist())
                    
                    logger.info(f"沪深300日期范围: {all_csi300_dates[0] if all_csi300_dates else 'N/A'} 至 {all_csi300_dates[-1] if all_csi300_dates else 'N/A'}")
                    
                    # 找到策略第一个日期对应的或之前最近的沪深300价格作为基准
                    first_strategy_date = strategy_dates[0] if strategy_dates else None
                    first_price = None
                    
                    # 查找基准价格：优先使用策略第一天的沪深300价格，否则使用之前最近的价格
                    if first_strategy_date:
                        if first_strategy_date in price_map:
                            first_price = price_map[first_strategy_date]
                        else:
                            # 查找策略开始日期之前最近的沪深300价格
                            earlier_dates = [d for d in all_csi300_dates if d <= first_strategy_date]
                            if earlier_dates:
                                first_price = price_map[earlier_dates[-1]]
                            elif all_csi300_dates:
                                # 如果没有更早的日期，使用沪深300最早的价格
                                first_price = price_map[all_csi300_dates[0]]
                    
                    if first_price is None and all_csi300_dates:
                        first_price = price_map[all_csi300_dates[0]]
                    
                    logger.info(f"基准起始价格: {first_price}")
                    
                    # 为每个策略日期生成基准数据
                    matched_count = 0
                    last_price = first_price  # 用于填充缺失日期
                    
                    for date_str in strategy_dates:
                        if date_str in price_map:
                            current_price = price_map[date_str]
                            last_price = current_price
                            matched_count += 1
                        else:
                            # 如果没有精确匹配，查找最近的历史价格
                            earlier_dates = [d for d in all_csi300_dates if d <= date_str]
                            if earlier_dates:
                                current_price = price_map[earlier_dates[-1]]
                                last_price = current_price
                            else:
                                current_price = last_price
                        
                        # 计算累计价值（归一化到初始金额）
                        if first_price and first_price > 0:
                            value = initial_amount * (current_price / first_price)
                        else:
                            value = initial_amount
                        
                        benchmark_curve.append({
                            'date': date_str,
                            'value': round(value, 2)
                        })
                    
                    logger.info(f"沪深300基准数据获取成功，共 {len(benchmark_curve)} 个数据点，精确匹配 {matched_count} 个日期")
                else:
                    logger.warning("没有找到策略的equity_curve数据")
            else:
                logger.warning("沪深300数据为空")
        except Exception as e:
            logger.warning(f"获取沪深300基准数据失败: {str(e)}")
            traceback.print_exc()
        
        logger.info(f"Strategy comparison completed: {len(comparison_results)} strategies, best={best_strategy_id}")
        
        # Return comparison results (Requirement 7.3, 7.5)

        return jsonify({
            'success': True,
            'data': {
                'fund_code': fund_code,
                'initial_amount': initial_amount,
                'base_invest': base_invest,
                'days': days,
                'period': period,
                'strategies': comparison_results,
                'best_strategy_id': best_strategy_id,
                'benchmark_curve': benchmark_curve  # 沪深300基准曲线
            }
        })
        
    except Exception as e:
        logger.error(f"Strategy comparison failed: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


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


def get_funds_by_date(date):
    """获取指定日期的基金分析结果"""
    try:
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort_by', 'composite_score')
        sort_order = request.args.get('sort_order', 'desc')
        
        sql = "SELECT * FROM fund_analysis_results WHERE analysis_date = :date"
        params = {'date': date}
        
        if search:
            sql += " AND (fund_code LIKE :search OR fund_name LIKE :search)"
            params['search'] = f'%{search}%'
        
        valid_sort_fields = ['composite_score', 'today_return', 'prev_day_return', 'annualized_return', 'sharpe_ratio', 'max_drawdown', 'fund_code']
        if sort_by not in valid_sort_fields:
            sort_by = 'composite_score'
        
        sort_direction = 'DESC' if sort_order == 'desc' else 'ASC'
        sql += f" ORDER BY {sort_by} {sort_direction}"
        
        df = db_manager.execute_query(sql, params)
        
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
            for key in ['today_return', 'prev_day_return']:
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
