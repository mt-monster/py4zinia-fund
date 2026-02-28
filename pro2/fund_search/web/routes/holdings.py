#!/usr/bin/env python
# coding: utf-8

"""
持仓管理相关 API 路由
从 app.py 中提取的持仓管理功能
"""

import os
import sys
import json
import math
import time
import logging
import traceback
import concurrent.futures
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import akshare as ak
import requests
from flask import Flask, render_template, jsonify, request

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.enhanced_config import DATABASE_CONFIG, NOTIFICATION_CONFIG
from data_access.enhanced_database import EnhancedDatabaseManager
from backtesting.strategies.enhanced_strategy import EnhancedInvestmentStrategy
from backtesting.core.unified_strategy_engine import UnifiedStrategyEngine
from backtesting.analysis.strategy_evaluator import StrategyEvaluator
from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
from data_retrieval.parsers.fund_screenshot_ocr import recognize_fund_screenshot, validate_recognized_fund
from data_retrieval.fetchers.heavyweight_stocks_fetcher import fetch_heavyweight_stocks, get_fetcher
from services.fund_type_service import (
    FundTypeService, classify_fund, get_fund_type_display, 
    get_fund_type_css_class, FUND_TYPE_CN, FUND_TYPE_CSS_CLASS
)
from shared.json_utils import safe_jsonify, create_safe_response
from shared.fund_helpers import (
    get_fund_name_from_db as _get_fund_name_from_db_helper,
    get_fund_type_for_allocation as _get_fund_type_for_allocation_helper,
)


# 添加安全的浮点数处理函数
def _safe_round_float(value, decimals=4, multiplier=1):
    """
    安全地处理浮点数，避免NaN和无穷大值
    
    Args:
        value: 要处理的值
        decimals: 保留小数位数
        multiplier: 乘数（如转换为百分比时用100）
    
    Returns:
        处理后的数值或None
    """
    try:
        # 检查是否为None
        if value is None:
            return None
        
        # 特殊处理字符串形式的NaN
        if isinstance(value, str):
            upper_val = value.upper()
            if upper_val == 'NAN' or upper_val == 'NULL' or upper_val == 'NONE':
                return None
        
        # 转换为float
        float_val = float(value)
        
        # 检查NaN和无穷大
        if math.isnan(float_val) or math.isinf(float_val):
            return None
        
        # 应用乘数
        result = float_val * multiplier
        
        # 四舍五入
        return round(result, decimals)
        
    except (ValueError, TypeError):
        return None

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 全局变量（由 register_routes 函数初始化）
db_manager = None
holding_service = None
cache_manager = None


def update_fund_analysis_results(fund_code, fund_name):
    """
    计算并更新基金的绩效指标到 fund_analysis_results 表
    
    Args:
        fund_code: 基金代码
        fund_name: 基金名称
        
    Returns:
        bool: 是否成功
    """
    try:
        from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
        from backtesting.strategies.enhanced_strategy import EnhancedInvestmentStrategy
        from datetime import datetime
        
        # 初始化数据适配器和策略引擎
        fund_data_manager = MultiSourceDataAdapter()
        strategy_engine = EnhancedInvestmentStrategy()
        
        # 获取实时数据
        realtime_data = fund_data_manager.get_realtime_data(fund_code, fund_name)
        performance_metrics = fund_data_manager.get_performance_metrics(fund_code)
        
        # 获取收益率数据
        today_return = float(realtime_data.get('today_return', 0.0))
        prev_day_return = float(realtime_data.get('prev_day_return', 0.0))
        
        # 投资策略分析
        strategy_result = strategy_engine.analyze_strategy(today_return, prev_day_return, performance_metrics)
        
        # 准备数据
        analysis_date = datetime.now().date()
        
        # 获取数据库管理器
        global db_manager
        if db_manager is None:
            from data_access.enhanced_database import EnhancedDatabaseManager
            from shared.enhanced_config import DATABASE_CONFIG
            db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        
        # 插入或更新 fund_analysis_results 表
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
        
        params = {
            'fund_code': fund_code,
            'fund_name': fund_name or realtime_data.get('fund_name', f'基金{fund_code}'),
            'analysis_date': analysis_date,
            'yesterday_nav': realtime_data.get('previous_nav'),
            'current_estimate': realtime_data.get('current_nav'),
            'today_return': today_return,
            'prev_day_return': prev_day_return,
            'status_label': strategy_result.get('status_label', '待分析'),
            'operation_suggestion': strategy_result.get('operation_suggestion', '持有观察'),
            'execution_amount': strategy_result.get('execution_amount', '0'),
            'is_buy': strategy_result.get('is_buy', False),
            'buy_multiplier': strategy_result.get('buy_multiplier', 1.0),
            'redeem_amount': strategy_result.get('redeem_amount', 0.0),
            'comparison_value': strategy_result.get('comparison_value', 0.0),
            'annualized_return': performance_metrics.get('annualized_return'),
            'sharpe_ratio': performance_metrics.get('sharpe_ratio'),
            'sharpe_ratio_ytd': performance_metrics.get('sharpe_ratio_ytd'),
            'sharpe_ratio_1y': performance_metrics.get('sharpe_ratio_1y'),
            'sharpe_ratio_all': performance_metrics.get('sharpe_ratio_all'),
            'max_drawdown': performance_metrics.get('max_drawdown'),
            'volatility': performance_metrics.get('volatility'),
            'calmar_ratio': performance_metrics.get('calmar_ratio'),
            'sortino_ratio': performance_metrics.get('sortino_ratio'),
            'var_95': performance_metrics.get('var_95'),
            'win_rate': performance_metrics.get('win_rate'),
            'profit_loss_ratio': performance_metrics.get('profit_loss_ratio'),
            'total_return': performance_metrics.get('total_return'),
            'composite_score': performance_metrics.get('composite_score')
        }
        
        success = db_manager.execute_sql(update_sql, params)
        
        if success:
            logger.info(f"基金 {fund_code} 绩效指标更新成功")
        else:
            logger.warning(f"基金 {fund_code} 绩效指标更新失败")
            
        return success
        
    except Exception as e:
        logger.error(f"更新基金 {fund_code} 绩效指标时出错: {e}")
        traceback.print_exc()
        return False


def register_routes(app, **kwargs):
    """注册持仓管理相关路由
    
    Args:
        app: Flask 应用实例
        **kwargs: 包含以下可选参数:
            - db_manager 或 database_manager: 数据库管理器实例
            - holding_service: 持仓服务实例
            - cache_manager: 缓存管理器实例
    """
    global db_manager, holding_service, cache_manager
    db_manager = kwargs.get('db_manager') or kwargs.get('database_manager')
    holding_service = kwargs.get('holding_service')
    cache_manager = kwargs.get('cache_manager')
    
    # 如果 kwargs 中没有，尝试从 app 属性获取
    if db_manager is None:
        db_manager = app.db_manager if hasattr(app, 'db_manager') else None
    if holding_service is None:
        holding_service = app.holding_service if hasattr(app, 'holding_service') else None
    if cache_manager is None:
        cache_manager = app.cache_manager if hasattr(app, 'cache_manager') else None
    
    # 注册所有路由
    app.route('/api/user-holdings', methods=['GET'])(get_user_holdings)
    app.route('/api/strategies/metadata', methods=['GET'])(get_strategies_metadata)
    app.route('/api/holdings', methods=['GET'])(get_holdings)
    app.route('/api/holdings/list', methods=['GET'])(get_holdings)  # 兼容 dashboard.html 的调用
    app.route('/api/holdings/import/screenshot', methods=['POST'])(import_holding_screenshot)
    app.route('/api/holdings/import/confirm', methods=['POST'])(import_holding_confirm)
    app.route('/api/holdings', methods=['POST'])(add_holding)
    app.route('/api/holdings/<fund_code>', methods=['PUT'])(update_holding)
    app.route('/api/holdings/clear', methods=['DELETE'])(clear_holdings)
    app.route('/api/holdings/analyze/correlation-interactive', methods=['POST'])(analyze_fund_correlation_interactive)
    app.route('/api/holdings/analyze/correlation', methods=['POST'])(analyze_fund_correlation)
    app.route('/api/holdings/analyze/comprehensive', methods=['POST'])(analyze_comprehensive)
    app.route('/api/holdings/analyze/personalized-advice', methods=['POST'])(analyze_personalized_advice)
    app.route('/api/analysis', methods=['POST'])(start_analysis)
    app.route('/api/holdings/<fund_code>', methods=['DELETE'])(delete_holding)
    
    app.route('/api/dip/returns', methods=['GET', 'POST'])(get_dip_returns)
    app.route('/api/dip/returns/<fund_code>', methods=['GET'])(get_fund_dip_returns)
    app.route('/api/dip/portfolio/returns', methods=['POST'])(get_portfolio_dip_returns)
    app.route('/api/dip/transactions', methods=['POST'])(add_dip_transaction)
    app.route('/api/dip/transactions/<fund_code>', methods=['GET'])(get_dip_transactions)
    
    # 重构版投资建议页面 API
    app.route('/api/investment-advice/holdings', methods=['GET'])(get_investment_advice_holdings)
    app.route('/api/investment-advice/strategies', methods=['GET'])(get_investment_advice_strategies)
    app.route('/api/investment-advice/backtest', methods=['POST'])(run_investment_advice_backtest)
    app.route('/api/investment-advice/generate', methods=['POST'])(generate_investment_advice_api)
    app.route('/api/investment-advice/valuation', methods=['GET', 'POST'])(get_investment_advice_valuation)


# ==================== API 路由函数 ====================

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
            return safe_jsonify({'success': True, 'data': []})
        
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
        
        return safe_jsonify({'success': True, 'data': holdings})
        
    except Exception as e:
        logger.error(f"获取用户持仓失败: {str(e)}")
        return safe_jsonify({'success': False, 'error': str(e)}), 500


def get_strategies_metadata():
    """获取策略元数据
    
    返回预定义的策略信息列表
    """
    try:
        # 导入策略元数据模块
        from .strategy_metadata import get_strategy_metadata as get_predefined_strategies
        
        # 使用预定义的策略数据
        result = get_predefined_strategies()
        return safe_jsonify(result)
        
    except ImportError as e:
        logger.warning(f"无法导入策略元数据模块: {str(e)}，使用备用方案")
        # 备用方案：直接返回预定义数据
        strategies = [
            {
                'strategy_id': 'dual_ma',
                'name': '双均线策略',
                'description': '基于短期与长期移动平均线交叉信号进行交易。当短期均线上穿长期均线时产生买入信号，反之产生卖出信号。适合捕捉中长期趋势行情。',
                'total_return': 45.2,
                'annualized_return': 15.8,
                'annualized_volatility': 18.5,
                'max_drawdown': -22.3,
                'sharpe_ratio': 0.85,
                'win_rate': 58.7,
                'profit_loss_ratio': 1.42,
                'trades_count': 156,
                'final_value': 145200.0
            },
            {
                'strategy_id': 'mean_reversion',
                'name': '均值回归策略',
                'description': '基于价格偏离均值程度进行交易。当价格显著高于均值时卖出，低于均值时买入。适合震荡市场环境。',
                'total_return': 38.7,
                'annualized_return': 13.2,
                'annualized_volatility': 16.8,
                'max_drawdown': -18.9,
                'sharpe_ratio': 0.78,
                'win_rate': 62.3,
                'profit_loss_ratio': 1.28,
                'trades_count': 234,
                'final_value': 138700.0
            },
            {
                'strategy_id': 'target_value',
                'name': '目标市值策略',
                'description': '设定目标市值水平，当实际市值低于目标时补仓，高于目标时减仓。适合长期定投优化。',
                'total_return': 52.1,
                'annualized_return': 17.9,
                'annualized_volatility': 14.2,
                'max_drawdown': -15.6,
                'sharpe_ratio': 1.26,
                'win_rate': 67.8,
                'profit_loss_ratio': 1.65,
                'trades_count': 89,
                'final_value': 152100.0
            },
            {
                'strategy_id': 'grid',
                'name': '网格交易策略',
                'description': '在预设价格区间内设置多个买卖点位，价格触及相应价位时自动交易。适合波动较大的市场。',
                'total_return': 31.5,
                'annualized_return': 10.8,
                'annualized_volatility': 22.1,
                'max_drawdown': -28.4,
                'sharpe_ratio': 0.49,
                'win_rate': 54.2,
                'profit_loss_ratio': 1.15,
                'trades_count': 312,
                'final_value': 131500.0
            },
            {
                'strategy_id': 'enhanced_rule_based',
                'name': '增强型规则策略',
                'description': '综合多种技术指标和市场特征的复合策略。结合趋势判断、波动率调整和风险控制机制。',
                'total_return': 58.9,
                'annualized_return': 19.2,
                'annualized_volatility': 16.7,
                'max_drawdown': -20.1,
                'sharpe_ratio': 1.15,
                'win_rate': 65.4,
                'profit_loss_ratio': 1.78,
                'trades_count': 187,
                'final_value': 158900.0
            }
        ]
        
        logger.info(f"成功加载 {len(strategies)} 个策略元数据（备用方案）")
        return safe_jsonify({'success': True, 'data': strategies})
        
    except Exception as e:
        logger.error(f"获取策略元数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def get_holdings():
    """获取用户持仓列表 - 使用缓存服务优化"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        search = request.args.get('search', '')
        
        # 优先使用 holding_service 获取数据（带缓存机制）
        if holding_service is not None:
            logger.info(f"使用 holding_service 获取持仓数据（带缓存）")
            holdings_data = holding_service.get_holdings_data(user_id)
            
            # 如果有搜索条件，进行过滤
            if search:
                search_lower = search.lower()
                holdings_data = [
                    h for h in holdings_data 
                    if search_lower in h.get('fund_code', '').lower() 
                    or search_lower in h.get('fund_name', '').lower()
                ]
            
            # 从 fund_analysis_results 补充绩效数据（holding_service 可能缺失）
            fund_codes = [h.get('fund_code') for h in holdings_data]
            analysis_data_map = {}
            if fund_codes:
                try:
                    placeholders = ','.join([f':code{i}' for i in range(len(fund_codes))])
                    analysis_sql = f"""
                        SELECT 
                            fund_code, today_return, prev_day_return,
                            current_estimate as current_nav, yesterday_nav as previous_nav,
                            sharpe_ratio, sharpe_ratio_ytd, sharpe_ratio_1y, sharpe_ratio_all,
                            max_drawdown, volatility, annualized_return, 
                            calmar_ratio, sortino_ratio, composite_score
                        FROM fund_analysis_results
                        WHERE (fund_code, analysis_date) IN (
                            SELECT fund_code, MAX(analysis_date) as max_date
                            FROM fund_analysis_results
                            WHERE fund_code IN ({placeholders})
                            GROUP BY fund_code
                        )
                    """
                    params = {f'code{i}': code for i, code in enumerate(fund_codes)}
                    analysis_df = db_manager.execute_query(analysis_sql, params)
                    if not analysis_df.empty:
                        analysis_data_map = analysis_df.set_index('fund_code').to_dict('index')
                except Exception as e:
                    logger.warning(f"获取 fund_analysis_results 数据失败: {e}")
            
            # 转换格式以兼容前端
            holdings = []
            for data in holdings_data:
                fund_code = data.get('fund_code', '')
                fund_name = data.get('fund_name', '')
                
                # 从 fund_analysis_results 获取补充数据
                analysis_data = analysis_data_map.get(fund_code, {})
                
                # 使用 fund_analysis_results 的数据优先（如果 holding_service 数据缺失）
                today_return = data.get('today_return') if data.get('today_return') is not None else analysis_data.get('today_return')
                prev_day_return = data.get('yesterday_return') if data.get('yesterday_return') is not None else analysis_data.get('prev_day_return')
                current_nav = data.get('current_nav') if data.get('current_nav') is not None else analysis_data.get('current_nav')
                
                # 昨日盈亏率数据时效性标记 - 优先使用 holding_service 的数据
                yesterday_return_date = data.get('yesterday_return_date')
                yesterday_return_days_diff = data.get('yesterday_return_days_diff')
                yesterday_return_is_stale = data.get('yesterday_return_is_stale', False)
                
                # 如果 holding_service 没有提供标记，但 prev_day_return 来自 fund_analysis_results，
                # 设置为非延迟数据（因为 fund_analysis_results 通常是 T-1 数据）
                if prev_day_return is not None and yesterday_return_days_diff is None:
                    yesterday_return_days_diff = 1  # 默认为 T-1
                    yesterday_return_is_stale = False
                
                # 绩效指标优先使用 fund_analysis_results 的数据
                # 使用安全的NaN检查
                def _is_valid_number(val):
                    if val is None:
                        return False
                    try:
                        float_val = float(val)
                        return not (math.isnan(float_val) or math.isinf(float_val))
                    except (ValueError, TypeError):
                        return False
                
                # 夏普比率 - 分别获取不同时期的值（独立处理，不使用fallback）
                sharpe_ratio_all = analysis_data.get('sharpe_ratio_all') if _is_valid_number(analysis_data.get('sharpe_ratio_all')) else data.get('sharpe_ratio_all')
                sharpe_ratio_1y = analysis_data.get('sharpe_ratio_1y') if _is_valid_number(analysis_data.get('sharpe_ratio_1y')) else data.get('sharpe_ratio_1y')
                sharpe_ratio_ytd = analysis_data.get('sharpe_ratio_ytd') if _is_valid_number(analysis_data.get('sharpe_ratio_ytd')) else data.get('sharpe_ratio_ytd')
                # 默认sharpe_ratio优先使用近一年，其次成立以来
                sharpe_ratio = analysis_data.get('sharpe_ratio') if _is_valid_number(analysis_data.get('sharpe_ratio')) else None
                if sharpe_ratio is None:
                    sharpe_ratio = sharpe_ratio_1y if sharpe_ratio_1y is not None else sharpe_ratio_all
                
                max_drawdown = analysis_data.get('max_drawdown') if _is_valid_number(analysis_data.get('max_drawdown')) else data.get('max_drawdown')
                annualized_return = analysis_data.get('annualized_return') if _is_valid_number(analysis_data.get('annualized_return')) else data.get('annualized_return')
                volatility = analysis_data.get('volatility') if _is_valid_number(analysis_data.get('volatility')) else data.get('volatility')
                calmar_ratio = analysis_data.get('calmar_ratio') if _is_valid_number(analysis_data.get('calmar_ratio')) else data.get('calmar_ratio')
                sortino_ratio = analysis_data.get('sortino_ratio') if _is_valid_number(analysis_data.get('sortino_ratio')) else data.get('sortino_ratio')
                composite_score = analysis_data.get('composite_score') if _is_valid_number(analysis_data.get('composite_score')) else data.get('composite_score')
                
                # 使用基金类型服务获取标准化基金类型
                fund_type_code = classify_fund(fund_name, fund_code, data.get('fund_type', ''))
                fund_type_cn = get_fund_type_display(fund_type_code)
                fund_type_class = get_fund_type_css_class(fund_type_code)
                
                holding = {
                    'id': fund_code,
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'fund_type': fund_type_code,
                    'fund_type_cn': fund_type_cn,
                    'fund_type_class': fund_type_class,
                    'holding_shares': data.get('holding_shares', 0),
                    'cost_price': data.get('cost_price', 0),
                    'holding_amount': data.get('holding_amount', 0),
                    'current_nav': current_nav,
                    'current_value': data.get('current_market_value'),
                    'buy_date': '',  # holding_service 不返回 buy_date
                    'notes': '',
                    # 盈亏指标
                    'today_profit': data.get('today_profit'),
                    'today_profit_rate': today_return,
                    'holding_profit': data.get('holding_profit'),
                    'holding_profit_rate': data.get('holding_profit_rate'),
                    'total_profit': data.get('holding_profit'),
                    'total_profit_rate': data.get('holding_profit_rate'),
                    'today_return': today_return,
                    'prev_day_return': prev_day_return,
                    'yesterday_profit': data.get('yesterday_profit'),
                    'yesterday_profit_rate': prev_day_return,
                    # 昨日盈亏率数据时效性标记
                    'yesterday_return_date': yesterday_return_date,
                    'yesterday_return_days_diff': yesterday_return_days_diff,
                    'yesterday_return_is_stale': yesterday_return_is_stale,
                    # 绩效指标 - 夏普比率（默认优先使用近一年）
                    'sharpe_ratio': sharpe_ratio,
                    'sharpe_ratio_ytd': sharpe_ratio_ytd,  # 今年以来（独立值）
                    'sharpe_ratio_1y': sharpe_ratio_1y,    # 近一年（独立值）
                    'sharpe_ratio_all': sharpe_ratio_all,  # 成立以来（独立值）
                    'max_drawdown': max_drawdown,
                    'volatility': volatility,
                    'annualized_return': annualized_return,
                    'calmar_ratio': calmar_ratio,
                    'sortino_ratio': sortino_ratio,
                    'composite_score': composite_score
                }
                holdings.append(holding)
            
            return jsonify({'success': True, 'data': holdings, 'total': len(holdings)})
        
        # 降级到原有逻辑（holding_service 不可用时）
        logger.warning("holding_service 不可用，使用降级逻辑（可能较慢）")
        
        sql = """
        SELECT h.*, 
               far.today_return, far.prev_day_return,
               far.current_estimate as current_nav,
               far.yesterday_nav as previous_nav,
               far.sharpe_ratio, far.sharpe_ratio_ytd, far.sharpe_ratio_1y, far.sharpe_ratio_all,
               far.max_drawdown, far.volatility,
               far.annualized_return, far.calmar_ratio, far.sortino_ratio,
               far.composite_score
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
            # 基础持仓数据（必须有的）
            holding_shares = float(row['holding_shares']) if pd.notna(row['holding_shares']) else 0
            cost_price = float(row['cost_price']) if pd.notna(row['cost_price']) else 0
            holding_amount = float(row['holding_amount']) if pd.notna(row['holding_amount']) else 0
            
            # 分析数据（可能缺失）- 缺失时返回 None 而不是 0
            has_analysis_data = pd.notna(row['current_nav'])  # 用 current_nav 判断是否有分析数据
            
            current_nav = float(row['current_nav']) if pd.notna(row['current_nav']) else None
            previous_nav = float(row['previous_nav']) if pd.notna(row['previous_nav']) else None
            today_return = float(row['today_return']) if pd.notna(row['today_return']) else None
            prev_day_return = float(row['prev_day_return']) if pd.notna(row['prev_day_return']) else None
            sharpe_ratio = float(row['sharpe_ratio']) if pd.notna(row['sharpe_ratio']) else None
            sharpe_ratio_ytd = float(row['sharpe_ratio_ytd']) if pd.notna(row['sharpe_ratio_ytd']) else None
            sharpe_ratio_1y = float(row['sharpe_ratio_1y']) if pd.notna(row['sharpe_ratio_1y']) else None
            sharpe_ratio_all = float(row['sharpe_ratio_all']) if pd.notna(row['sharpe_ratio_all']) else None
            max_drawdown = float(row['max_drawdown']) if pd.notna(row['max_drawdown']) else None
            volatility = float(row['volatility']) if pd.notna(row['volatility']) else None
            annualized_return = float(row['annualized_return']) if pd.notna(row['annualized_return']) else None
            calmar_ratio = float(row['calmar_ratio']) if pd.notna(row['calmar_ratio']) else None
            sortino_ratio = float(row['sortino_ratio']) if pd.notna(row['sortino_ratio']) else None
            composite_score = float(row['composite_score']) if pd.notna(row['composite_score']) else None
            
            # 只有当有分析数据时才计算相关指标
            if has_analysis_data:
                # 当前市值
                current_value = holding_shares * current_nav
                # 昨日市值
                previous_value = holding_shares * (previous_nav if previous_nav else current_nav)
                
                # 持有盈亏
                holding_profit = current_value - holding_amount
                holding_profit_rate = (holding_profit / holding_amount * 100) if holding_amount > 0 else 0
                
                # 当日盈亏
                today_profit = current_value - previous_value
                today_profit_rate = (today_profit / previous_value * 100) if previous_value > 0 else 0
                
                # 昨日盈亏 - 基于昨日市值和基金昨日涨跌幅计算
                if prev_day_return is not None:
                    yesterday_profit = previous_value * (prev_day_return / 100)
                    yesterday_profit_rate = prev_day_return
                else:
                    yesterday_profit = 0
                    yesterday_profit_rate = None
                
                # 累计盈亏（与持有盈亏相同）
                total_profit = holding_profit
                total_profit_rate = holding_profit_rate
            else:
                # 没有分析数据时，相关字段为 None
                current_value = None
                previous_value = None
                holding_profit = None
                holding_profit_rate = None
                today_profit = None
                today_profit_rate = None
                yesterday_profit = None
                yesterday_profit_rate = None
                total_profit = None
                total_profit_rate = None
            
            # 使用基金类型服务获取标准化基金类型
            fund_name = row['fund_name']
            fund_code = row['fund_code']
            # 尝试从fund_basic_info获取官方类型
            official_type = row.get('fund_type', '')
            fund_type_code = classify_fund(fund_name, fund_code, official_type)
            fund_type_cn = get_fund_type_display(fund_type_code)
            fund_type_class = get_fund_type_css_class(fund_type_code)
            
            holding = {
                'id': int(row['id']),
                'fund_code': fund_code,
                'fund_name': fund_name,
                'fund_type': fund_type_code,          # 基金类型代码
                'fund_type_cn': fund_type_cn,         # 基金类型中文名
                'fund_type_class': fund_type_class,   # 基金类型CSS类
                'holding_shares': round(holding_shares, 4),
                'cost_price': round(cost_price, 4),
                'holding_amount': round(holding_amount, 2),
                'current_nav': round(current_nav, 4) if current_nav is not None else None,
                'current_value': round(current_value, 2) if current_value is not None else None,
                'buy_date': str(row['buy_date']),
                'notes': row['notes'] if pd.notna(row['notes']) else '',
                # 盈亏指标
                'today_profit': round(today_profit, 2) if today_profit is not None else None,
                'today_profit_rate': round(today_profit_rate, 2) if today_profit_rate is not None else None,
                'holding_profit': round(holding_profit, 2) if holding_profit is not None else None,
                'holding_profit_rate': round(holding_profit_rate, 2) if holding_profit_rate is not None else None,
                'total_profit': round(total_profit, 2) if total_profit is not None else None,
                'total_profit_rate': round(total_profit_rate, 2) if total_profit_rate is not None else None,
                'today_return': round(today_return, 2) if today_return is not None else None,
                'prev_day_return': round(prev_day_return, 2) if prev_day_return is not None else None,
                'yesterday_profit': round(yesterday_profit, 2) if yesterday_profit is not None else None,
                'yesterday_profit_rate': round(yesterday_profit_rate, 2) if yesterday_profit_rate is not None else None,
                # 昨日盈亏率数据时效性标记（降级逻辑默认为T-1）
                'yesterday_return_date': None,
                'yesterday_return_days_diff': 1 if prev_day_return is not None else None,
                'yesterday_return_is_stale': False,
                # 绩效指标 - 加强NaN值处理
                'sharpe_ratio': _safe_round_float(sharpe_ratio, 4),
                'sharpe_ratio_ytd': _safe_round_float(sharpe_ratio_ytd, 4),
                'sharpe_ratio_1y': _safe_round_float(sharpe_ratio_1y, 4),
                'sharpe_ratio_all': _safe_round_float(sharpe_ratio_all, 4) if _safe_round_float(sharpe_ratio_all, 4) is not None else None,
                'max_drawdown': _safe_round_float(max_drawdown, 2, multiplier=100),
                'volatility': _safe_round_float(volatility, 2, multiplier=100),
                'annualized_return': _safe_round_float(annualized_return, 2, multiplier=100),
                'calmar_ratio': _safe_round_float(calmar_ratio, 4),
                'sortino_ratio': _safe_round_float(sortino_ratio, 4),
                'composite_score': _safe_round_float(composite_score, 4)
            }
            holdings.append(holding)
        
        # 最终清理：确保没有NaN值
        for holding in holdings:
            for key, value in holding.items():
                if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                    holding[key] = None
                elif isinstance(value, str) and value.upper() in ['NAN', 'NULL', 'NONE']:
                    holding[key] = None
        
        return safe_jsonify({'success': True, 'data': holdings, 'total': len(holdings)})
        
    except Exception as e:
        logger.error(f"获取持仓列表失败: {str(e)}")
        return safe_jsonify({'success': False, 'error': str(e)}), 500


def import_holding_screenshot():
    """通过截图导入基金持仓"""
    try:
        data = request.get_json()
        image_data = data.get('image')
        use_gpu = data.get('use_gpu', False)
        ocr_engine = data.get('ocr_engine', 'baidu')
        user_id = data.get('user_id', 'default_user')
        
        if not image_data:
            return jsonify({'success': False, 'error': '未提供图片数据'}), 400
            
        # 调用OCR识别函数
        from data_retrieval.parsers.fund_screenshot_ocr import recognize_fund_screenshot
        
        recognized_funds = recognize_fund_screenshot(
            image_data=image_data,
            use_gpu=use_gpu,
            import_to_portfolio=False,  # 先识别，不直接导入
            user_id=user_id,
            ocr_engine=ocr_engine
        )
        
        return jsonify({
            'success': True,
            'data': recognized_funds,
            'message': f'成功识别到 {len(recognized_funds)} 只基金'
        })
        
    except Exception as e:
        logger.error(f"截图导入失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def import_holding_confirm():
    """手工导入基金持仓确认"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default_user')
        funds = data.get('funds', [])
        
        if not funds:
            return jsonify({'success': False, 'error': '没有提供基金数据'}), 400
            
        imported_count = 0
        errors = []
        
        for fund_data in funds:
            try:
                fund_code = fund_data.get('fund_code')
                fund_name = fund_data.get('fund_name')
                holding_shares = float(fund_data.get('holding_shares', 0))
                cost_price = float(fund_data.get('cost_price', 0))
                buy_date = fund_data.get('buy_date')
                # 处理空字符串或无效日期
                if buy_date is None or buy_date == '' or buy_date.lower() in ['none', 'null']:
                    buy_date = None
                notes = fund_data.get('notes', '手工导入')
                
                # 计算持有金额
                holding_amount = holding_shares * cost_price
                
                # 检查基金是否已存在
                check_sql = "SELECT COUNT(*) FROM user_holdings WHERE user_id = :user_id AND fund_code = :fund_code"
                existing_result = db_manager.fetch_one(check_sql, {
                    'user_id': user_id,
                    'fund_code': fund_code
                })
                
                existing_count = existing_result[0] if existing_result else 0
                
                if existing_count > 0:
                    # 基金已存在，更新持仓
                    update_sql = """
                    UPDATE user_holdings 
                    SET holding_shares = :holding_shares, 
                        cost_price = :cost_price, 
                        holding_amount = :holding_amount,
                        buy_date = :buy_date,
                        notes = :notes
                    WHERE user_id = :user_id AND fund_code = :fund_code
                    """
                    success = db_manager.execute_sql(update_sql, {
                        'user_id': user_id,
                        'fund_code': fund_code,
                        'holding_shares': holding_shares,
                        'cost_price': cost_price,
                        'holding_amount': holding_amount,
                        'buy_date': buy_date,
                        'notes': notes
                    })
                    logger.info(f"更新基金 {fund_code} 持仓成功")
                else:
                    # 基金不存在，插入新记录
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
                    logger.info(f"插入基金 {fund_code} 持仓成功")
                
                if success:
                    imported_count += 1
                    # 导入成功后立即计算并更新绩效指标
                    try:
                        update_fund_analysis_results(fund_code, fund_name)
                    except Exception as e:
                        logger.warning(f"基金 {fund_code} 绩效指标计算失败: {e}")
                else:
                    errors.append(f"基金 {fund_code} 导入失败")
                    
            except Exception as e:
                error_msg = f"基金 {fund_data.get('fund_code', 'unknown')} 处理异常: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        if imported_count > 0:
            message = f"成功导入 {imported_count} 只基金"
            if errors:
                message += f"，{len(errors)} 只基金导入失败"
            return jsonify({
                'success': True, 
                'message': message,
                'imported_count': imported_count,
                'errors': errors
            })
        else:
            return jsonify({
                'success': False, 
                'error': '所有基金导入失败',
                'errors': errors
            }), 500
            
    except Exception as e:
        logger.error(f"导入持仓失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


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
        # 处理空字符串或无效日期
        if buy_date is None or buy_date == '' or buy_date.lower() in ['none', 'null']:
            buy_date = None
        
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
            # 添加成功后立即计算并更新绩效指标
            try:
                update_fund_analysis_results(fund_code, fund_name)
            except Exception as e:
                logger.warning(f"基金 {fund_code} 绩效指标计算失败: {e}")
            
            return jsonify({'success': True, 'message': '持仓添加成功'})
        else:
            return jsonify({'success': False, 'error': '持仓添加失败'}), 500
            
    except Exception as e:
        logger.error(f"添加持仓失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


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
            if 'holding_shares' in data:
                old_data['holding_shares'] = float(data['holding_shares'])
            if 'cost_price' in data:
                old_data['cost_price'] = float(data['cost_price'])
            if 'buy_date' in data:
                old_data['buy_date'] = data['buy_date']
            if 'notes' in data:
                old_data['notes'] = data['notes']
            
            # 重新计算持有金额
            holding_shares = float(old_data.get('holding_shares', 0))
            cost_price = float(old_data.get('cost_price', 0))
            old_data['holding_amount'] = round(holding_shares * cost_price, 2)
            logger.info(f"基金代码变更-重新计算持有金额: {holding_shares} × {cost_price} = {old_data['holding_amount']}")
            
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
                'holding_shares': holding_shares,
                'cost_price': cost_price,
                'holding_amount': old_data['holding_amount'],
                'buy_date': old_data.get('buy_date') if old_data.get('buy_date') and old_data.get('buy_date').strip() else None,
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
            
            # 重新计算持有金额（始终根据份额和成本价计算，忽略前端发送的值）
            if 'holding_shares' in data or 'cost_price' in data:
                # 获取当前值（用于部分更新的情况）
                sql_get = "SELECT holding_shares, cost_price FROM user_holdings WHERE user_id = :user_id AND fund_code = :fund_code"
                df = db_manager.execute_query(sql_get, {'user_id': user_id, 'fund_code': fund_code})
                if not df.empty:
                    current_shares = params.get('holding_shares', float(df.iloc[0]['holding_shares']))
                    current_price = params.get('cost_price', float(df.iloc[0]['cost_price']))
                    params['holding_amount'] = round(current_shares * current_price, 2)
                    update_fields.append('holding_amount = :holding_amount')
                    logger.info(f"重新计算持有金额: {current_shares} × {current_price} = {params['holding_amount']}")
            
            if 'buy_date' in data:
                buy_date = data['buy_date']
                # 处理空字符串或无效日期
                if buy_date is None or buy_date == '' or buy_date.lower() in ['none', 'null']:
                    update_fields.append('buy_date = NULL')
                else:
                    update_fields.append('buy_date = :buy_date')
                    params['buy_date'] = buy_date
            
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
            from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
            from backtesting.strategies.enhanced_strategy import EnhancedInvestmentStrategy
            
            fund_data_manager = MultiSourceDataAdapter()
            strategy_engine = EnhancedInvestmentStrategy()
            
            # 获取实时数据 - 传入fund_name以便正确识别QDII基金
            realtime_data = fund_data_manager.get_realtime_data(fund_code, fund_name)
            performance_metrics = fund_data_manager.get_performance_metrics(fund_code)
            
            # 计算今日和昨日收益率
            today_return = float(realtime_data.get('today_return', 0.0))
            prev_day_return = float(realtime_data.get('prev_day_return', 0.0))
            
            # 投资策略分析
            strategy_result = strategy_engine.analyze_strategy(today_return, prev_day_return, performance_metrics)
            
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
                'prev_day_return': prev_day_return,
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


def analyze_fund_correlation_interactive():
    """
    分析基金相关性（交互式图表版本 - 优化版，支持懒加载和详细性能监控）
    """
    api_start_time = time.perf_counter()
    
    try:
        data = request.get_json()
        fund_codes = data.get('fund_codes', [])
        # 支持指定要查看详情的基金对（懒加载模式）
        detail_pair = data.get('detail_pair')  # {'fund1': 'code1', 'fund2': 'code2'}
        
        logger.info(f"[API Performance] 收到相关性分析请求，基金数量: {len(fund_codes)}")
        
        if len(fund_codes) < 2:
            return jsonify({'success': False, 'error': '至少需要2只基金进行相关性分析'})
        
        # 步骤1: 批量获取基金名称
        step_start = time.perf_counter()
        fund_names = _batch_get_fund_names(fund_codes)
        step_elapsed = (time.perf_counter() - step_start) * 1000
        logger.info(f"[API Performance] 步骤1-获取基金名称: {step_elapsed:.2f} ms, 成功: {len(fund_names)}只")
        
        # 步骤2: 批量获取基金历史数据
        step_start = time.perf_counter()
        fund_data_dict = _batch_get_fund_historical_data(fund_codes)
        step_elapsed = (time.perf_counter() - step_start) * 1000
        logger.info(f"[API Performance] 步骤2-数据库获取数据: {step_elapsed:.2f} ms, 成功: {len(fund_data_dict)}只")
        
        # 步骤3: 如果数据库数据不足，从akshare获取
        if len(fund_data_dict) < 2:
            logger.warning(f"[API Performance] 数据库数据不足({len(fund_data_dict)}只)，开始从akshare获取...")
            step_start = time.perf_counter()
            fund_data_dict = _fetch_fund_data_from_akshare_optimized(fund_codes, fund_names)
            step_elapsed = (time.perf_counter() - step_start) * 1000
            logger.info(f"[API Performance] 步骤3-akshare获取数据: {step_elapsed:.2f} ms, 成功: {len(fund_data_dict)}只")
        
        if len(fund_data_dict) < 2:
            return jsonify({'success': False, 'error': '数据不足，无法进行相关性分析'})

        # 步骤4: 执行相关性分析
        step_start = time.perf_counter()
        from backtesting.analysis.enhanced_correlation import EnhancedCorrelationAnalyzer
        analyzer = EnhancedCorrelationAnalyzer()
        
        # 如果请求了特定基金对的详情，则只返回该基金对的数据
        if detail_pair and detail_pair.get('fund1') and detail_pair.get('fund2'):
            fund1_code = detail_pair['fund1']
            fund2_code = detail_pair['fund2']
            
            pair_detail = analyzer.generate_pair_detail_data(
                fund_data_dict, fund_names, fund1_code, fund2_code
            )
            
            if not pair_detail:
                return jsonify({'success': False, 'error': '无法生成指定基金对的详细数据'})
            
            step_elapsed = (time.perf_counter() - step_start) * 1000
            api_elapsed = (time.perf_counter() - api_start_time) * 1000
            logger.info(f"[API Performance] 步骤4-生成详情数据: {step_elapsed:.2f} ms")
            logger.info(f"[API Performance] API总耗时（单对详情）: {api_elapsed:.2f} ms")
            
            return jsonify({
                'success': True,
                'data': {
                    'pair_detail': pair_detail,
                    'is_lazy_load': True
                }
            })
        
        # 否则返回懒加载格式的数据（主组合+精简列表）
        interactive_data = analyzer.generate_interactive_correlation_data(
            fund_data_dict, fund_names, lazy_load=True
        )
        
        step_elapsed = (time.perf_counter() - step_start) * 1000
        logger.info(f"[API Performance] 步骤4-相关性分析计算: {step_elapsed:.2f} ms")
        
        if not interactive_data:
            return jsonify({'success': False, 'error': '无法生成相关性分析数据'})
        
        api_elapsed = (time.perf_counter() - api_start_time) * 1000
        logger.info(f"[API Performance] API总耗时（懒加载模式）: {api_elapsed:.2f} ms ({api_elapsed/1000:.3f} s)")
        
        # 添加性能数据到响应
        interactive_data['_api_performance'] = {
            'total_time_ms': api_elapsed,
            'fund_count': len(fund_codes),
            'data_source': 'akshare' if len(fund_data_dict) > len(_batch_get_fund_historical_data(fund_codes)) else 'database'
        }
        
        return jsonify({
            'success': True,
            'data': interactive_data
        })
        
    except Exception as e:
        api_elapsed = (time.perf_counter() - api_start_time) * 1000
        logger.error(f"[API Performance] 交互式相关性分析失败，耗时: {api_elapsed:.2f} ms, 错误: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


def _batch_get_fund_names(fund_codes: list) -> dict:
    """
    批量获取基金名称 - 优化版，减少数据库查询次数
    修复SQL参数格式问题
    
    参数:
    fund_codes: 基金代码列表
    
    返回:
    dict: 基金代码到名称的映射
    """
    fund_names = {}
    
    if not fund_codes:
        return fund_names
    
    try:
        # 使用%s占位符（与SQLAlchemy兼容）
        placeholders = ','.join(['%s'] * len(fund_codes))
        
        # 批量从 fund_basic_info 获取
        sql_basic = f"""
        SELECT fund_code, fund_name 
        FROM fund_basic_info 
        WHERE fund_code IN ({placeholders})
        """
        
        with db_manager.engine.connect() as conn:
            df_basic = pd.read_sql(sql_basic, conn, params=tuple(fund_codes))
        
        for _, row in df_basic.iterrows():
            if pd.notna(row['fund_name']):
                fund_names[row['fund_code']] = row['fund_name']
        
        # 对于没有找到的，从 fund_analysis_results 获取
        missing_codes = [code for code in fund_codes if code not in fund_names]
        if missing_codes:
            placeholders2 = ','.join(['%s'] * len(missing_codes))
            
            sql_analysis = f"""
            SELECT t1.fund_code, t1.fund_name 
            FROM fund_analysis_results t1
            INNER JOIN (
                SELECT fund_code, MAX(analysis_date) as max_date
                FROM fund_analysis_results 
                WHERE fund_code IN ({placeholders2})
                GROUP BY fund_code
            ) t2 ON t1.fund_code = t2.fund_code AND t1.analysis_date = t2.max_date
            """
            
            with db_manager.engine.connect() as conn:
                df_analysis = pd.read_sql(sql_analysis, conn, params=tuple(missing_codes))
            
            for _, row in df_analysis.iterrows():
                if pd.notna(row['fund_name']):
                    fund_names[row['fund_code']] = row['fund_name']
        
        # 剩下的使用代码作为名称
        for code in fund_codes:
            if code not in fund_names:
                fund_names[code] = code
        
        logger.info(f"批量获取基金名称成功: {len(fund_names)} 只基金")
        return fund_names
        
    except Exception as e:
        logger.error(f"批量获取基金名称失败: {e}")
        traceback.print_exc()
        return {code: code for code in fund_codes}


def _fetch_fund_data_from_akshare_optimized(fund_codes: list, fund_names: dict) -> dict:
    """
    从akshare获取基金历史数据 - 优化版（使用线程池并发获取，增加并发数）
    
    参数:
    fund_codes: 基金代码列表
    fund_names: 基金名称映射
    
    返回:
    dict: 基金代码到DataFrame的映射
    """
    fund_data_dict = {}
    start_time = time.perf_counter()
    
    def fetch_single_fund(code):
        """获取单只基金数据"""
        fund_start = time.perf_counter()
        try:
            nav_df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
            
            if nav_df is not None and not nav_df.empty and len(nav_df) >= 30:
                nav_df = nav_df.rename(columns={
                    '净值日期': 'date',
                    '单位净值': 'nav'
                })
                nav_df['date'] = pd.to_datetime(nav_df['date'])
                nav_df = nav_df.sort_values('date')
                
                # 只取最近一年的数据
                one_year_ago = datetime.now() - timedelta(days=365)
                nav_df = nav_df[nav_df['date'] >= one_year_ago]
                
                nav_df['nav'] = pd.to_numeric(nav_df['nav'], errors='coerce')
                nav_df = nav_df.dropna(subset=['nav'])
                nav_df['daily_return'] = nav_df['nav'].pct_change() * 100
                nav_df = nav_df.dropna()
                
                if len(nav_df) >= 10:
                    elapsed = (time.perf_counter() - fund_start) * 1000
                    logger.info(f"[AKShare] 基金 {code} 获取成功: {len(nav_df)}条, 耗时: {elapsed:.2f}ms")
                    return code, nav_df
        except Exception as e:
            elapsed = (time.perf_counter() - fund_start) * 1000
            logger.warning(f"[AKShare] 基金 {code} 获取失败: {str(e)}, 耗时: {elapsed:.2f}ms")
        return code, None
    
    # 使用线程池并发获取 - 增加并发数以加快获取速度
    # 对于14只基金，10个并发可以在2轮内完成
    max_workers = min(10, len(fund_codes))
    logger.info(f"[AKShare] 开始并发获取 {len(fund_codes)} 只基金数据，并发数: {max_workers}")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_code = {executor.submit(fetch_single_fund, code): code for code in fund_codes}
        for future in concurrent.futures.as_completed(future_to_code):
            code, df = future.result()
            if df is not None:
                fund_data_dict[code] = df
    
    total_elapsed = (time.perf_counter() - start_time) * 1000
    logger.info(f"[AKShare] 数据获取完成: {len(fund_data_dict)}/{len(fund_codes)} 只基金, 总耗时: {total_elapsed:.2f}ms")
    return fund_data_dict


def get_recent_activities(user_id: str = 'default_user') -> list:
    """
    获取用户的最近活动记录
    从数据库查询真实的操作记录
    """
    try:
        activities = []
        
        # 查询最近的数据导入记录（从持仓更新历史）
        sql_import = """
        SELECT fund_code, fund_name, updated_at 
        FROM user_holdings 
        WHERE user_id = :user_id 
        ORDER BY updated_at DESC LIMIT 2
        """
        import_df = db_manager.execute_query(sql_import, {'user_id': user_id})
        
        if not import_df.empty:
            for _, row in import_df.iterrows():
                updated_at = row['updated_at']
                time_str = format_time_ago(updated_at) if updated_at else '最近'
                activities.append({
                    'icon': 'bi-plus-circle',
                    'description': f"更新持仓: {row['fund_name'][:10]}..." if len(str(row['fund_name'])) > 10 else f"更新持仓: {row['fund_name']}",
                    'time': time_str
                })
        
        # 查询最近的基金分析记录
        sql_analysis = """
        SELECT MAX(analysis_date) as last_analysis 
        FROM fund_analysis_results
        """
        analysis_df = db_manager.execute_query(sql_analysis)
        if not analysis_df.empty and analysis_df.iloc[0]['last_analysis']:
            last_analysis = analysis_df.iloc[0]['last_analysis']
            time_str = format_time_ago(last_analysis) if last_analysis else '最近'
            activities.append({
                'icon': 'bi-graph-up',
                'description': '更新基金净值数据',
                'time': time_str
            })
        
        # 查询最近的策略回测记录
        sql_backtest = """
        SELECT MAX(created_at) as last_backtest 
        FROM strategy_backtest_results
        WHERE status = 'completed'
        """
        backtest_df = db_manager.execute_query(sql_backtest)
        if not backtest_df.empty and backtest_df.iloc[0]['last_backtest']:
            last_backtest = backtest_df.iloc[0]['last_backtest']
            time_str = format_time_ago(last_backtest) if last_backtest else '最近'
            activities.append({
                'icon': 'bi-check-circle',
                'description': '完成策略回测分析',
                'time': time_str
            })
        
        # 如果没有记录，返回空列表
        if not activities:
            return []
            
        return activities
        
    except Exception as e:
        logger.warning(f"获取最近活动失败: {str(e)}")
        return []


def format_time_ago(timestamp) -> str:
    """格式化时间为相对时间（如：10分钟前）"""
    try:
        if timestamp is None:
            return '最近'
        
        if isinstance(timestamp, str):
            timestamp = pd.to_datetime(timestamp)
        
        now = datetime.now()
        if hasattr(timestamp, 'to_pydatetime'):
            timestamp = timestamp.to_pydatetime()
        
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days}天前"
        elif diff.seconds >= 3600:
            return f"{diff.seconds // 3600}小时前"
        elif diff.seconds >= 60:
            return f"{diff.seconds // 60}分钟前"
        else:
            return "刚刚"
    except:
        return '最近'


def get_real_holding_distribution(user_id: str = 'default_user') -> list:
    """
    获取真实的持仓分布数据 - 使用证监会标准分类
    根据用户的实际持仓按基金类型统计
    """
    try:
        # 第一步：获取用户持仓
        sql_holdings = """
        SELECT h.fund_code, h.holding_shares, h.cost_price
        FROM user_holdings h
        WHERE h.user_id = :user_id
        """
        
        df_holdings = db_manager.execute_query(sql_holdings, {'user_id': user_id})
        
        if df_holdings.empty:
            logger.info(f"用户 {user_id} 没有持仓数据")
            return []
        
        logger.info(f"获取到 {len(df_holdings)} 条持仓记录")
        
        # 第二步：为每个基金获取类型（使用新的基金类型服务）
        fund_codes = df_holdings['fund_code'].tolist()
        fund_type_map = {}
        
        for fund_code in fund_codes:
            # 使用统一的基金类型获取方法
            fund_type_code = get_fund_type_for_allocation(fund_code)
            fund_type_map[fund_code] = fund_type_code
        
        # 第三步：按基金类型统计持仓金额
        type_amounts = {}
        total_amount = 0
        
        for _, row in df_holdings.iterrows():
            fund_code = row['fund_code']
            fund_type = fund_type_map.get(fund_code, 'unknown')
            
            holding_amount = float(row['holding_shares']) * float(row['cost_price'])
            
            if fund_type in type_amounts:
                type_amounts[fund_type] += holding_amount
            else:
                type_amounts[fund_type] = holding_amount
            
            total_amount += holding_amount
            
            logger.debug(f"基金 {fund_code}: 类型={fund_type}, 金额={holding_amount}")
        
        if total_amount == 0:
            logger.warning("总持仓金额为0")
            return []
        
        logger.info(f"持仓分布统计完成: {type_amounts}")
        
        # 类型代码到中文名称的映射
        cn_name_map = {
            'stock': '股票型',
            'bond': '债券型',
            'hybrid': '混合型',
            'money': '货币型',
            'index': '指数型',
            'qdii': 'QDII',
            'etf': 'ETF',
            'fof': 'FOF',
            'unknown': '其他'
        }
        
        # Bootstrap颜色类映射
        color_map = {
            'stock': 'success',
            'bond': 'info',
            'hybrid': 'warning',
            'money': 'secondary',
            'index': 'primary',
            'qdii': 'secondary',
            'etf': 'danger',
            'fof': 'dark',
            'unknown': 'light'
        }
        
        # 颜色十六进制值（用于前端显示）
        color_hex_map = {
            'stock': '#28a745',
            'bond': '#17a2b8',
            'hybrid': '#ffc107',
            'money': '#6c757d',
            'index': '#007bff',
            'qdii': '#9b59b6',
            'etf': '#e74c3c',
            'fof': '#fd7e14',
            'unknown': '#adb5bd'
        }
        
        # 统计每个类型的基金数量
        type_count = {}
        for _, row in df_holdings.iterrows():
            fund_code = row['fund_code']
            fund_type = fund_type_map.get(fund_code, 'unknown')
            
            if fund_type in type_count:
                type_count[fund_type] += 1
            else:
                type_count[fund_type] = 1
        
        # 构建分布数据
        distribution = []
        for fund_type, amount in sorted(type_amounts.items(), key=lambda x: x[1], reverse=True):
            percentage = round((amount / total_amount) * 100, 1)
            count = type_count.get(fund_type, 0)
            distribution.append({
                'name': f'{cn_name_map.get(fund_type, fund_type)}基金',
                'type_code': fund_type,
                'percentage': percentage,
                'count': count,
                'color': color_map.get(fund_type, 'primary'),
                'colorHex': color_hex_map.get(fund_type, '#007bff'),
                'amount': round(amount, 2)
            })
        
        logger.info(f"持仓分布: {distribution}")
        return distribution
        
    except Exception as e:
        logger.error(f"获取持仓分布失败: {str(e)}", exc_info=True)
        return []


def get_fund_type_for_allocation(fund_code: str) -> str:
    """为资产配置获取基金类型（委托 shared.fund_helpers 统一实现）"""
    return _get_fund_type_for_allocation_helper(fund_code, db_manager)


def infer_fund_type_from_name(fund_name: str) -> str:
    """
    从基金名称推断基金类型
    """
    if not fund_name:
        return '其他'
    
    fund_name = str(fund_name).upper()
    
    # 股票型关键词
    if any(kw in fund_name for kw in ['股票', '股票型', 'EQUITY', 'GROWTH', 'VALUE']):
        return '股票型'
    
    # 债券型关键词
    if any(kw in fund_name for kw in ['债券', '债券型', 'BOND', '固收', '纯债', '信用债']):
        return '债券型'
    
    # 货币型关键词
    if any(kw in fund_name for kw in ['货币', '货币型', 'CASH', '活期', '理财']):
        return '货币型'
    
    # 指数型关键词
    if any(kw in fund_name for kw in ['指数', '指数型', 'ETF', 'INDEX', '沪深300', '中证500', '上证50']):
        return '指数型'
    
    # QDII关键词
    if any(kw in fund_name for kw in ['QDII', '全球', '海外', '美国', '香港', '亚太', '环球']):
        return 'QDII'
    
    # 混合型（默认，如果包含混合字样）
    if any(kw in fund_name for kw in ['混合', '混合型', 'MIX', '灵活配置', '偏股', '偏债']):
        return '混合型'
    
    # FOF
    if 'FOF' in fund_name:
        return 'FOF'
    
    # 默认其他
    return '其他'


def normalize_fund_type(fund_type: str) -> str:
    """标准化基金类型名称"""
    if not fund_type:
        return '其他'
    
    fund_type = str(fund_type).lower()
    
    if '股票' in fund_type or 'equity' in fund_type:
        return '股票型'
    elif '债券' in fund_type or 'bond' in fund_type or '固收' in fund_type:
        return '债券型'
    elif '混合' in fund_type or 'mix' in fund_type or '灵活配置' in fund_type:
        return '混合型'
    elif '货币' in fund_type or 'cash' in fund_type or '理财' in fund_type:
        return '货币型'
    elif '指数' in fund_type or 'etf' in fund_type or '指数' in fund_type:
        return '指数型'
    elif 'qdii' in fund_type or '境外' in fund_type:
        return 'QDII'
    else:
        return '其他'


def analyze_fund_correlation():
    """
    分析基金相关性（增强版）- 优化版本，带超时控制
    """
    start_time = time.time()
    
    try:
        data = request.get_json()
        if not data or 'fund_codes' not in data:
            return jsonify({'success': False, 'error': '缺少基金代码'})
        
        fund_codes = data['fund_codes']
        if len(fund_codes) < 2:
            return jsonify({'success': False, 'error': '至少需要2只基金进行相关性分析'})
        
        # 获取增强分析选项
        enhanced_analysis = data.get('enhanced_analysis', True)
        
        logger.info(f"[Correlation] 开始分析 {len(fund_codes)} 只基金的相关性")
        
        # 导入相关性分析模块
        from services.fund_analyzer import FundAnalyzer
        from backtesting.analysis.enhanced_correlation import EnhancedCorrelationAnalyzer
        
        # 基础相关性分析 - 优先使用数据库
        analyzer = FundAnalyzer()
        basic_result = analyzer.analyze_correlation(fund_codes, use_cache=True)
        
        result = {
            'success': True,
            'data': {
                'basic_correlation': basic_result
            }
        }
        
        logger.info(f"[Correlation] 基础分析完成，耗时: {time.time() - start_time:.2f}s")
        
        # 增强相关性分析
        if enhanced_analysis:
            try:
                # 优先从数据库获取数据
                fund_data_dict = {}
                fund_names = {}
                
                # 使用批量查询从数据库获取数据
                db_fund_data = _batch_get_fund_historical_data(fund_codes)
                
                for fund_code in fund_codes:
                    try:
                        # 获取基金名称
                        fund_name = analyzer._get_fund_name(fund_code)
                        if not fund_name:
                            fund_name = fund_code
                        fund_names[fund_code] = fund_name
                        
                        # 优先使用数据库数据
                        if fund_code in db_fund_data and not db_fund_data[fund_code].empty:
                            fund_data_dict[fund_code] = db_fund_data[fund_code]
                            logger.debug(f"[Correlation] 基金 {fund_code} 使用数据库数据")
                        else:
                            logger.warning(f"[Correlation] 基金 {fund_code} 数据库数据缺失")
                            
                    except Exception as e:
                        logger.warning(f"[Correlation] 获取基金 {fund_code} 数据失败: {e}")
                        continue
                
                logger.info(f"[Correlation] 数据准备完成，有效基金: {len(fund_data_dict)}/{len(fund_codes)}")
                
                if len(fund_data_dict) >= 2:
                    enhanced_analyzer = EnhancedCorrelationAnalyzer()
                    enhanced_result = enhanced_analyzer.analyze_enhanced_correlation(
                        fund_data_dict, fund_names
                    )
                    
                    # 生成相关性图表
                    chart_data = enhanced_analyzer.generate_correlation_charts(
                        fund_data_dict, fund_names
                    )
                    
                    result['data']['enhanced_analysis'] = enhanced_result
                    if chart_data:
                        result['data']['charts'] = chart_data
                else:
                    logger.warning(f"[Correlation] 有效基金数量不足: {len(fund_data_dict)}")
                    result['data']['enhanced_error'] = f"有效基金数量不足 ({len(fund_data_dict)} < 2)，无法进行分析"
                    
            except Exception as e:
                logger.error(f"[Correlation] 增强相关性分析失败: {e}")
                result['data']['enhanced_error'] = str(e)
        
        total_time = time.time() - start_time
        logger.info(f"[Correlation] 分析完成，总耗时: {total_time:.2f}s")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"[Correlation] 分析基金相关性失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


def _batch_get_fund_historical_data(fund_codes: list, min_records: int = 100) -> dict:
    """
    批量从数据库获取基金历史数据
    如果数据不足，自动从akshare获取补充
    
    Args:
        fund_codes: 基金代码列表
        min_records: 每只基金最少需要的记录数，默认100条
        
    Returns:
        dict: 基金代码 -> DataFrame 的映射
    """
    result = {}
    funds_needing_update = []
    
    try:
        db = EnhancedDatabaseManager(DATABASE_CONFIG)
        
        # 构建批量查询 - 使用命名参数
        placeholders = ','.join([f':code_{i}' for i in range(len(fund_codes))])
        sql = f"""
            SELECT 
                fund_code,
                analysis_date as date,
                current_estimate as nav,
                today_return as daily_return
            FROM fund_analysis_results
            WHERE fund_code IN ({placeholders})
              AND analysis_date >= DATE_SUB(CURDATE(), INTERVAL 365 DAY)
            ORDER BY fund_code, analysis_date
        """
        
        # 构建参数字典
        params = {f'code_{i}': code for i, code in enumerate(fund_codes)}
        df = db.execute_query(sql, params)
        
        if df.empty:
            logger.warning("[Correlation] 数据库中没有找到基金历史数据")
            funds_needing_update = fund_codes
        else:
            # 按基金代码分组
            for fund_code in fund_codes:
                fund_df = df[df['fund_code'] == fund_code].copy()
                if not fund_df.empty:
                    # 转换日期格式
                    fund_df['date'] = pd.to_datetime(fund_df['date'])
                    # 按日期排序
                    fund_df = fund_df.sort_values('date', ascending=True)
                    
                    # 检查数据量是否充足
                    if len(fund_df) >= min_records:
                        result[fund_code] = fund_df
                        logger.info(f"[Correlation] 基金 {fund_code}: {len(fund_df)} 条记录（充足）")
                    else:
                        logger.warning(f"[Correlation] 基金 {fund_code}: 仅 {len(fund_df)} 条记录（不足{min_records}），需要从akshare获取")
                        funds_needing_update.append(fund_code)
                else:
                    logger.warning(f"[Correlation] 基金 {fund_code}: 数据库中无数据")
                    funds_needing_update.append(fund_code)
        
        logger.info(f"[Correlation] 数据库数据充足: {len(result)}/{len(fund_codes)} 只，需要从akshare获取: {len(funds_needing_update)} 只")
        
        # 对于数据不足的基金，从akshare获取
        if funds_needing_update:
            logger.info(f"[Correlation] 开始从akshare获取 {len(funds_needing_update)} 只基金数据...")
            akshare_data = _fetch_fund_data_from_akshare_optimized(funds_needing_update, {})
            
            # 合并结果
            for fund_code, fund_df in akshare_data.items():
                if fund_df is not None and not fund_df.empty:
                    result[fund_code] = fund_df
                    logger.info(f"[Correlation] 基金 {fund_code}: 从akshare获取 {len(fund_df)} 条记录")
        
    except Exception as e:
        logger.error(f"[Correlation] 批量获取基金数据失败: {e}")
    
    return result


def analyze_comprehensive():
    """Comprehensive analysis of selected funds' positions"""
    try:
        data = request.get_json()
        fund_codes = data.get('fund_codes', [])
        
        if not fund_codes:
            return jsonify({'success': False, 'error': '请选择至少一只基金'})
        
        # Collect position data for each fund
        all_holdings = []
        total_asset = 0
        
        for fund_code in fund_codes:
            # Get fund position data
            holdings_df = get_fund_holdings_data(fund_code)
            if holdings_df is not None and not holdings_df.empty:
                all_holdings.append(holdings_df)
                # Assume fund size is 100 million for calculation (actual should be obtained from fund info)
                total_asset += 100000  # 100 million yuan
        
        # Integrate position data
        if not all_holdings:
            return jsonify({'success': False, 'error': '无法获取基金持仓数据'})
        
        combined_holdings = pd.concat(all_holdings, ignore_index=True)
        
        # Get fund count for weighted average calculation
        fund_codes_count = len(fund_codes)
        
        # Calculate asset allocation (with weighted average for multiple funds)
        asset_allocation = calculate_asset_allocation(combined_holdings, total_asset, fund_codes_count)
        
        # Calculate industry distribution (with weighted average for multiple funds)
        industry_distribution = calculate_industry_distribution(combined_holdings, total_asset, fund_codes_count)
        
        # Calculate top stocks (with weighted average for multiple funds)
        top_stocks = calculate_top_stocks(combined_holdings, total_asset, fund_codes_count)
        
        # Generate analysis summary
        summary = generate_analysis_summary(asset_allocation, industry_distribution, top_stocks, fund_codes_count)
        
        # 获取策略分析数据（集成enhanced_main.py逻辑）
        strategy_analysis = get_fund_strategy_analysis(fund_codes)
        
        return jsonify({
            'success': True,
            'data': {
                'asset_allocation': asset_allocation,
                'industry_distribution': industry_distribution,
                'top_stocks': top_stocks,
                'summary': summary,
                'strategy_analysis': strategy_analysis
            }
        })
    except Exception as e:
        logger.error(f"综合分析失败: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def start_analysis():
    """开始分析 - 重构版API"""
    try:
        data = request.get_json()
        funds = data.get('funds', [])
        
        if len(funds) < 2:
            return jsonify({'success': False, 'error': '请至少选择2只基金'}), 400
        
        # 调用现有的综合分析逻辑
        return analyze_comprehensive()
        
    except Exception as e:
        logger.error(f"开始分析失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


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


def analyze_personalized_advice():
    """
    个性化投资建议分析API
    为每只基金选择最优策略并生成个性化建议
    """
    try:
        # 使用并行处理版本以提升性能
        from web.routes.analysis import get_personalized_investment_advice_parallel
        
        # 导入MultiSourceDataAdapter用于缓存预热
        from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
        
        data = request.get_json()
        fund_codes = data.get('fund_codes', [])
        
        if not fund_codes:
            return safe_jsonify({'success': False, 'error': '请选择至少一只基金'}), 400
        
        logger.info(f"开始个性化投资建议分析（并行模式），基金: {fund_codes}")
        
        # 步骤1: 预热实时数据缓存
        logger.info(f"[缓存预热] 开始预热 {len(fund_codes)} 只基金的实时数据缓存...")
        try:
            # 使用线程本地存储获取或创建adapter
            from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
            adapter = MultiSourceDataAdapter()
            warmup_result = adapter.warmup_realtime_cache(fund_codes)
            logger.info(f"[缓存预热] 完成: 成功 {warmup_result['success_count']} 只，失败 {warmup_result['fail_count']} 只")
        except Exception as e:
            logger.warning(f"[缓存预热] 失败: {e}，将继续执行分析")
        
        # 步骤2: 根据基金数量动态设置并行数
        max_workers = min(5, len(fund_codes)) if len(fund_codes) > 0 else 5
        
        # 步骤3: 调用并行分析函数
        result = get_personalized_investment_advice_parallel(fund_codes, max_workers=max_workers)
        
        if result.get('success'):
            logger.info(f"分析完成，耗时: {result.get('summary', {}).get('elapsed_seconds', 'N/A')}秒")
            return safe_jsonify(result)
        else:
            return safe_jsonify(result), 500
            
    except Exception as e:
        logger.error(f"个性化投资建议分析失败: {str(e)}")
        traceback.print_exc()
        return safe_jsonify({'success': False, 'error': str(e)}), 500


# ==================== 辅助函数 ====================

def get_fund_holdings_data(fund_code):
    """
    获取基金持仓数据
    优先使用akshare，失败时依次尝试备用数据源
    
    Args:
        fund_code: 基金代码
        
    Returns:
        DataFrame: 持仓数据，包含以下列：
            - stock_name: 股票名称
            - stock_code: 股票代码
            - proportion: 持仓占比
            - industry: 所属行业
            - change_percent: 涨跌幅
            - fund_code: 基金代码
    """
    logger.info(f"开始获取基金 {fund_code} 的持仓数据")
    
    # 依次尝试不同的数据源
    data_sources = [
        _get_holdings_from_akshare,
        _get_holdings_from_eastmoney,
        _get_holdings_from_sina
    ]
    
    for source_func in data_sources:
        try:
            logger.info(f"尝试从 {source_func.__name__} 获取数据...")
            holdings_df = source_func(fund_code)
            
            if holdings_df is not None and not holdings_df.empty:
                logger.info(f"成功从 {source_func.__name__} 获取 {len(holdings_df)} 条持仓数据")
                logger.info(f"持仓数据列: {list(holdings_df.columns)}")
                return holdings_df
                
        except Exception as e:
            logger.warning(f"从 {source_func.__name__} 获取数据失败: {e}")
            continue
    
    logger.error(f"所有数据源均无法获取基金 {fund_code} 的持仓数据")
    return None


def _get_holdings_from_akshare(fund_code):
    """从akshare获取基金持仓数据"""
    try:
        df = ak.fund_portfolio_hold_em(symbol=fund_code, date=None)
        
        if df is None or df.empty:
            logger.warning(f"akshare返回空数据: {fund_code}")
            return None
        
        # 标准化列名
        column_mapping = {
            '股票名称': 'stock_name',
            '股票代码': 'stock_code',
            '占净值比例': 'proportion',
            '持仓市值': 'market_value',
            '涨跌幅': 'change_percent'
        }
        
        # 重命名列
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df[new_col] = df[old_col]
        
        # 添加基金代码
        df['fund_code'] = fund_code
        
        # 尝试获取行业信息
        df['industry'] = df['stock_name'].apply(_get_industry_by_stock_name)
        
        # 只保留需要的列
        required_cols = ['stock_name', 'stock_code', 'proportion', 'industry', 'change_percent', 'fund_code']
        available_cols = [col for col in required_cols if col in df.columns]
        df = df[available_cols].copy()
        
        return df.head(10)  # 只取前10大重仓股
        
    except Exception as e:
        logger.error(f"akshare获取数据失败: {e}")
        raise


def _get_holdings_from_eastmoney(fund_code):
    """从天天基金网获取基金持仓数据"""
    try:
        url = f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={fund_code}&topline=10"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        # 解析返回的JSONP数据
        text = response.text
        if 'var' in text:
            json_str = text[text.find('{'):text.rfind('}')+1]
            data = json.loads(json_str)
            
            if 'data' in data and len(data['data']) > 0:
                holdings = []
                for item in data['data'][:10]:
                    holdings.append({
                        'stock_name': item.get('GPM', ''),
                        'stock_code': item.get('GPJC', ''),
                        'proportion': float(item.get('JZBL', 0)),
                        'industry': _get_industry_by_stock_name(item.get('GPM', '')),
                        'change_percent': item.get('ZDF', '--'),
                        'fund_code': fund_code
                    })
                
                return pd.DataFrame(holdings)
        
        logger.warning(f"天天基金网返回数据格式异常: {fund_code}")
        return None
        
    except Exception as e:
        logger.error(f"天天基金网获取数据失败: {e}")
        raise


def _get_holdings_from_sina(fund_code):
    """从新浪财经获取基金持仓数据"""
    try:
        url = f"https://stock.finance.sina.com.cn/fundInfo/api/openapi.php/CaihuiFundInfoService.getFundPortDetail?symbol={fund_code}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if 'result' in data and 'data' in data['result']:
            holdings_data = data['result']['data']
            
            if holdings_data and len(holdings_data) > 0:
                holdings = []
                for item in holdings_data[:10]:
                    holdings.append({
                        'stock_name': item.get('name', ''),
                        'stock_code': item.get('code', ''),
                        'proportion': float(item.get('ratio', 0)),
                        'industry': _get_industry_by_stock_name(item.get('name', '')),
                        'change_percent': item.get('change', '--'),
                        'fund_code': fund_code
                    })
                
                return pd.DataFrame(holdings)
        
        logger.warning(f"新浪财经返回数据格式异常: {fund_code}")
        return None
        
    except Exception as e:
        logger.error(f"新浪财经获取数据失败: {e}")
        raise


def _get_industry_by_stock_name(stock_name):
    """根据股票名称推断所属行业（简化版）"""
    industry_mapping = {
        '茅台': '食品饮料', '五粮液': '食品饮料', '食品': '食品饮料', '饮料': '食品饮料',
        '宁德': '新能源', '隆基': '新能源', '阳光电源': '新能源', '新能源': '新能源',
        '银行': '银行', '招商': '银行', '平安银行': '银行', '工商银行': '银行',
        '保险': '保险', '中国平安': '保险', '人寿': '保险', '太保': '保险',
        '腾讯': '互联网', '阿里': '互联网', '美团': '互联网', '字节': '互联网',
        '医药': '医药生物', '药明': '医药生物', '恒瑞': '医药生物', '康龙': '医药生物',
        '白酒': '食品饮料', '啤酒': '食品饮料', '红酒': '食品饮料',
        '证券': '非银金融', '中信': '非银金融', '建投': '非银金融', '中金': '非银金融',
        '汽车': '汽车', '比亚迪': '汽车', '长城': '汽车', '上汽': '汽车',
        '电子': '电子', '立讯': '电子', '歌尔': '电子', '半导体': '电子',
        '化工': '化工', '万华': '化工', '石化': '化工',
        '机械': '机械设备', '三一': '机械设备', '中联': '机械设备'
    }
    
    for keyword, industry in industry_mapping.items():
        if keyword in stock_name:
            return industry
    
    return '其他'


def calculate_asset_allocation(holdings_df, total_asset, fund_codes_count=1):
    """
    Calculate asset allocation based on holdings data
    
    Args:
        holdings_df: 持仓数据DataFrame
        total_asset: 总资产（用于市值计算）
        fund_codes_count: 基金数量（用于加权平均）
    """
    try:
        # Group by asset type
        if 'asset_type' in holdings_df.columns:
            asset_groups = holdings_df.groupby('asset_type')['proportion'].sum()
        else:
            # Default to stock allocation if no asset type column
            # 当多个基金时，需要计算加权平均而不是简单相加
            stock_proportion = holdings_df['proportion'].sum()
            # 按基金数量加权平均，确保总比例不超过100%
            weighted_stock_proportion = stock_proportion / max(fund_codes_count, 1)
            asset_groups = pd.Series({'股票': weighted_stock_proportion, '债券': 0, '现金': 0, '其他': 0})
        
        # Convert to dictionary with percentage format
        asset_allocation = {}
        for asset_type, proportion in asset_groups.items():
            # 对多基金情况进行加权平均
            adjusted_proportion = proportion / max(fund_codes_count, 1)
            asset_allocation[str(asset_type)] = round(float(adjusted_proportion), 2)
        
        return asset_allocation
    except Exception as e:
        logger.error(f"计算资产配置失败: {e}")
        return {}


def calculate_industry_distribution(holdings_df, total_asset, fund_codes_count=1):
    """
    Calculate industry distribution based on holdings data
    
    Args:
        holdings_df: 持仓数据DataFrame
        total_asset: 总资产（用于市值计算）
        fund_codes_count: 基金数量（用于加权平均）
    """
    try:
        # Group by industry
        if 'industry' in holdings_df.columns:
            industry_groups = holdings_df.groupby('industry')['proportion'].sum()
        elif 'industry_name' in holdings_df.columns:
            industry_groups = holdings_df.groupby('industry_name')['proportion'].sum()
        else:
            # Default to empty if no industry column
            return {}
        
        # Sort by proportion
        industry_groups = industry_groups.sort_values(ascending=False)
        
        # Convert to dictionary with percentage format
        # 对多基金情况进行加权平均
        industry_distribution = {}
        for industry, proportion in industry_groups.items():
            adjusted_proportion = proportion / max(fund_codes_count, 1)
            industry_distribution[str(industry)] = round(float(adjusted_proportion), 2)
        
        return industry_distribution
    except Exception as e:
        logger.error(f"计算行业分布失败: {e}")
        return {}


def calculate_top_stocks(holdings_df, total_asset, fund_codes_count=1):
    """
    Calculate top stocks based on holdings data
    
    Args:
        holdings_df: 持仓数据DataFrame
        total_asset: 总资产（用于市值计算）
        fund_codes_count: 基金数量（用于加权平均）
    """
    try:
        # 首先收集每只股票关联的基金信息
        stock_fund_map = {}
        # 缓存基金名称避免重复查询
        fund_name_cache = {}
        
        if 'fund_code' in holdings_df.columns:
            for _, row in holdings_df.iterrows():
                stock_key = (str(row.get('stock_code', '')), str(row.get('stock_name', '')))
                fund_code = str(row.get('fund_code', ''))
                proportion = float(row.get('proportion', 0))
                
                # 获取基金名称（优先从缓存）
                if fund_code not in fund_name_cache:
                    fund_name = row.get('fund_name', '') or get_fund_name_from_db(fund_code) or fund_code
                    fund_name_cache[fund_code] = fund_name
                else:
                    fund_name = fund_name_cache[fund_code]
                
                if stock_key not in stock_fund_map:
                    stock_fund_map[stock_key] = []
                
                # 避免重复添加同一基金
                existing_codes = [f['fund_code'] for f in stock_fund_map[stock_key]]
                if fund_code and fund_code not in existing_codes:
                    stock_fund_map[stock_key].append({
                        'fund_code': fund_code,
                        'fund_name': fund_name,
                        'proportion': round(proportion, 2)
                    })
        
        # Group by stock code and name, sum the proportions
        grouped = holdings_df.groupby(['stock_code', 'stock_name'], as_index=False)['proportion'].sum()
        
        # Sort by proportion
        sorted_holdings = grouped.sort_values('proportion', ascending=False).head(10)
        
        # Convert to list of dictionaries
        # 对多基金情况进行加权平均
        top_stocks = []
        for _, row in sorted_holdings.iterrows():
            raw_proportion = float(row.get('proportion', 0))
            adjusted_proportion = raw_proportion / max(fund_codes_count, 1)
            stock_code = str(row.get('stock_code', row.get('code', '')))
            stock_name = str(row.get('stock_name', row.get('name', '')))
            stock_key = (stock_code, stock_name)
            
            # 获取关联基金列表
            related_funds = stock_fund_map.get(stock_key, [])
            fund_count = len(related_funds) if related_funds else 1
            
            stock_info = {
                'stock_name': stock_name,
                'stock_code': stock_code,
                'proportion': round(adjusted_proportion, 2),
                'market_value': round(adjusted_proportion * total_asset / 100, 2),
                'change_percent': row.get('change_percent', row.get('涨跌幅', '--')),
                'fund_count': fund_count,
                'related_funds': related_funds
            }
            top_stocks.append(stock_info)
        
        return top_stocks
    except Exception as e:
        logger.error(f"计算重仓股失败: {e}")
        traceback.print_exc()
        return []


def generate_analysis_summary(asset_allocation, industry_distribution, top_stocks, fund_codes_count=1):
    """
    Generate analysis summary based on calculated data
    
    Args:
        asset_allocation: 资产配置字典
        industry_distribution: 行业分布字典
        top_stocks: 重仓股列表
        fund_codes_count: 基金数量（用于说明数据已加权平均）
    """
    try:
        summary = {
            'total_stock_proportion': 0,
            'top_industry_concentration': 0,
            'top_stock_concentration': 0,
            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
            'fund_count': fund_codes_count,
            'calculation_method': 'weighted_average' if fund_codes_count > 1 else 'simple'
        }
        
        # Calculate total stock proportion (already weighted)
        if asset_allocation:
            summary['total_stock_proportion'] = asset_allocation.get('股票', 0)
        
        # Calculate top industry concentration (top 3 industries) - already weighted
        if industry_distribution:
            top_industries = sorted(industry_distribution.values(), reverse=True)[:3]
            summary['top_industry_concentration'] = round(sum(top_industries), 2)
        
        # Calculate top stock concentration (top 5 stocks) - already weighted
        if top_stocks:
            top_5_stocks = top_stocks[:5]
            summary['top_stock_concentration'] = round(sum(stock['proportion'] for stock in top_5_stocks), 2)
        
        return summary
    except Exception as e:
        logger.error(f"生成分析摘要失败: {e}")
        return {}


def get_fund_strategy_analysis(fund_codes):
    """
    获取基金策略分析数据（使用统一策略引擎）
    
    Args:
        fund_codes: 基金代码列表
        
    Returns:
        dict: 包含策略分析结果的字典
    """
    try:
        from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
        from backtesting.unified_strategy_engine import UnifiedStrategyEngine
        
        fund_data_manager = MultiSourceDataAdapter()
        strategy_engine = UnifiedStrategyEngine()
        
        results = []
        buy_count = 0
        sell_count = 0
        hold_count = 0
        
        for fund_code in fund_codes:
            try:
                # 获取基金名称
                fund_name = get_fund_name_from_db(fund_code) or fund_code
                
                # 获取实时数据
                realtime_data = fund_data_manager.get_realtime_data(fund_code, fund_name)
                performance_metrics = fund_data_manager.get_performance_metrics(fund_code)
                
                # 计算今日和昨日收益率
                today_return = float(realtime_data.get('today_return', 0.0))
                prev_day_return = float(realtime_data.get('prev_day_return', 0.0))
                
                # 投资策略分析（使用统一策略引擎）
                unified_result = strategy_engine.analyze(
                    today_return=today_return,
                    prev_day_return=prev_day_return,
                    performance_metrics=performance_metrics,
                    base_invest=100.0  # 使用默认基准定投金额
                )
                
                # 转换为字典格式
                strategy_result = strategy_engine.to_dict(unified_result)
                
                # 补充策略逻辑说明
                strategy_explanation = get_strategy_explanation(today_return, prev_day_return, strategy_result)
                
                fund_result = {
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'today_return': round(today_return, 2),
                    'prev_day_return': round(prev_day_return, 2),
                    'return_diff': round(today_return - prev_day_return, 2),
                    'status_label': strategy_result.get('status_label', ''),
                    'operation_suggestion': strategy_result.get('operation_suggestion', ''),
                    'execution_amount': strategy_result.get('execution_amount', ''),
                    'action': strategy_result.get('action', 'hold'),
                    'buy_multiplier': strategy_result.get('final_buy_multiplier', 0.0),
                    'redeem_amount': strategy_result.get('redeem_amount', 0.0),
                    'strategy_explanation': strategy_explanation,
                    'composite_score': performance_metrics.get('composite_score', 0.0),
                    'sharpe_ratio': performance_metrics.get('sharpe_ratio', 0.0)
                }
                
                results.append(fund_result)
                
                # 统计操作类型
                action = strategy_result.get('action', 'hold')
                if action in ['buy', 'strong_buy', 'weak_buy']:
                    buy_count += 1
                elif action in ['sell', 'redeem']:
                    sell_count += 1
                else:
                    hold_count += 1
                    
            except Exception as e:
                logger.warning(f"分析基金 {fund_code} 策略失败: {e}")
                results.append({
                    'fund_code': fund_code,
                    'fund_name': fund_code,
                    'today_return': 0,
                    'prev_day_return': 0,
                    'return_diff': 0,
                    'status_label': '🔴 数据获取失败',
                    'operation_suggestion': '暂无建议',
                    'execution_amount': '持有不动',
                    'action': 'hold',
                    'buy_multiplier': 0,
                    'redeem_amount': 0,
                    'strategy_explanation': '无法获取数据，建议人工核查',
                    'composite_score': 0,
                    'sharpe_ratio': 0
                })
                hold_count += 1
        
        return {
            'funds': results,
            'summary': {
                'total_count': len(fund_codes),
                'buy_count': buy_count,
                'sell_count': sell_count,
                'hold_count': hold_count,
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
        }
        
    except Exception as e:
        logger.error(f"获取策略分析数据失败: {e}")
        return {'funds': [], 'summary': {'total_count': 0, 'buy_count': 0, 'sell_count': 0, 'hold_count': 0}}


def get_strategy_explanation(today_return, prev_day_return, strategy_result):
    """
    生成策略判断的详细解释
    
    Args:
        today_return: 今日收益率
        prev_day_return: 昨日收益率
        strategy_result: 策略分析结果
        
    Returns:
        str: 策略解释文本
    """
    return_diff = today_return - prev_day_return
    action = strategy_result.get('action', 'hold')
    status_label = strategy_result.get('status_label', '')
    
    explanation_parts = []
    
    # 收益率趋势分析
    if today_return > 0 and prev_day_return > 0:
        if return_diff > 1:
            explanation_parts.append(f"连续上涨且涨幅扩大(差值+{return_diff:.2f}%)，处于上升趋势强势区")
        elif return_diff > 0:
            explanation_parts.append(f"连续上涨但涨幅放缓(差值+{return_diff:.2f}%)，可能接近阶段顶部")
        elif return_diff >= -1:
            explanation_parts.append(f"连续上涨涨幅收窄(差值{return_diff:.2f}%)，上涨动能减弱")
        else:
            explanation_parts.append(f"连续上涨但涨幅大幅回落(差值{return_diff:.2f}%)，注意回调风险")
    elif today_return > 0 and prev_day_return <= 0:
        explanation_parts.append(f"由跌转涨形成反转(今日+{today_return:.2f}% vs 昨日{prev_day_return:.2f}%)，可能是买入时机")
    elif today_return == 0 and prev_day_return > 0:
        explanation_parts.append(f"涨势暂停进入休整(今日0% vs 昨日+{prev_day_return:.2f}%)，观察后续走势")
    elif today_return < 0 and prev_day_return > 0:
        explanation_parts.append(f"由涨转跌形成反转(今日{today_return:.2f}% vs 昨日+{prev_day_return:.2f}%)，需要防范风险")
    elif today_return == 0 and prev_day_return <= 0:
        explanation_parts.append(f"下跌企稳(今日0% vs 昨日{prev_day_return:.2f}%)，可能是建仓时机")
    elif today_return < 0 and prev_day_return == 0:
        if today_return <= -2:
            explanation_parts.append(f"首次大跌(今日{today_return:.2f}%)，跌幅较大可考虑分批建仓")
        elif today_return <= -0.5:
            explanation_parts.append(f"首次下跌(今日{today_return:.2f}%)，可适度建仓")
        else:
            explanation_parts.append(f"微跌试探(今日{today_return:.2f}%)，观察为主")
    elif today_return < 0 and prev_day_return < 0:
        if return_diff > 1 and today_return <= -2:
            explanation_parts.append(f"连续下跌且跌幅加速(差值+{return_diff:.2f}%)，暴跌中可分批抄底")
        elif return_diff > 1:
            explanation_parts.append(f"连续下跌跌幅扩大(差值+{return_diff:.2f}%)，下跌趋势加速")
        elif (prev_day_return - today_return) > 0 and prev_day_return <= -2:
            explanation_parts.append(f"暴跌后跌幅收窄(差值{return_diff:.2f}%)，可能企稳")
        elif (prev_day_return - today_return) > 0:
            explanation_parts.append(f"下跌动能减弱(差值{return_diff:.2f}%)，跌速放缓")
        else:
            explanation_parts.append(f"阴跌持续(差值{return_diff:.2f}%)，可能在筑底")
    
    # 操作建议解释
    if action in ['buy', 'strong_buy', 'weak_buy']:
        buy_mult = strategy_result.get('buy_multiplier', 1.0)
        explanation_parts.append(f"策略建议：买入({buy_mult}×定投额)")
    elif action in ['sell', 'redeem']:
        redeem_amt = strategy_result.get('redeem_amount', 0)
        explanation_parts.append(f"策略建议：赎回(¥{redeem_amt})")
    else:
        explanation_parts.append("策略建议：持有观望")
    
    return '；'.join(explanation_parts)


def get_fund_name_from_db(fund_code):
    """从数据库获取基金名称（委托 shared.fund_helpers 统一实现）"""
    return _get_fund_name_from_db_helper(fund_code, db_manager)


def _get_holdings_from_db():
    """从数据库获取持仓列表"""
    try:
        sql = "SELECT fund_code, fund_name FROM user_holdings WHERE user_id = 'default_user'"
        result = db_manager.execute_query(sql)
        if result is not None and not result.empty:
            return result.to_dict('records')
        return []
    except Exception as e:
        logger.warning(f"获取持仓失败: {e}")
        return []


def get_dip_returns():
    """获取所有基金的定投收益率曲线"""
    try:
        from services.dip_return_calculator import get_dip_calculator
        
        calculator = get_dip_calculator(db_manager)
        
        data = request.get_json() or {}
        fund_codes = data.get('fund_codes', [])
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not fund_codes:
            holdings = _get_holdings_from_db()
            fund_codes = [h['fund_code'] for h in holdings]
        
        if not fund_codes:
            return safe_jsonify({'success': False, 'error': '没有持仓基金'}), 400
        
        portfolio_returns = calculator.get_portfolio_returns(
            fund_codes, 
            start_date=start_date, 
            end_date=end_date
        )
        
        if portfolio_returns.empty:
            return safe_jsonify({'success': False, 'error': '无法获取数据'}), 400
        
        chart_data = {
            'dates': [str(d) for d in portfolio_returns['date'].tolist()],
            'market_value': portfolio_returns['market_value'].tolist(),
            'total_cost': portfolio_returns['total_cost'].tolist(),
            'total_return': portfolio_returns['total_return'].tolist(),
            'return_rate': (portfolio_returns['return_rate'] * 100).tolist()
        }
        
        latest = portfolio_returns.iloc[-1]
        
        return safe_jsonify({
            'success': True,
            'chart_data': chart_data,
            'summary': {
                'market_value': float(latest['market_value']),
                'total_cost': float(latest['total_cost']),
                'total_return': float(latest['total_return']),
                'return_rate': float(latest['return_rate']) * 100
            }
        })
        
    except Exception as e:
        logger.error(f"获取定投收益失败: {e}")
        return safe_jsonify({'success': False, 'error': str(e)}), 500


def get_fund_dip_returns(fund_code):
    """获取单只基金的定投收益率"""
    try:
        from services.dip_return_calculator import get_dip_calculator
        
        calculator = get_dip_calculator(db_manager)
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        df = calculator.calculate_daily_returns(fund_code, start_date, end_date)
        
        if df.empty:
            return safe_jsonify({'success': False, 'error': '无法获取数据'}), 400
        
        chart_data = {
            'dates': [str(d) for d in df['date'].tolist()],
            'nav': df['nav'].tolist(),
            'shares': df['shares'].tolist(),
            'market_value': df['market_value'].tolist(),
            'total_cost': df['total_cost'].tolist(),
            'total_return': df['total_return'].tolist(),
            'return_rate': (df['return_rate'] * 100).tolist()
        }
        
        summary = calculator.get_return_summary(fund_code, start_date)
        
        return safe_jsonify({
            'success': True,
            'fund_code': fund_code,
            'chart_data': chart_data,
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"获取基金 {fund_code} 定投收益失败: {e}")
        return safe_jsonify({'success': False, 'error': str(e)}), 500


def get_portfolio_dip_returns():
    """获取组合的定投收益率"""
    try:
        from services.dip_return_calculator import get_dip_calculator
        
        calculator = get_dip_calculator(db_manager)
        
        data = request.get_json() or {}
        fund_codes = data.get('fund_codes', [])
        weights = data.get('weights')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not fund_codes:
            return safe_jsonify({'success': False, 'error': '请提供基金代码列表'}), 400
        
        df = calculator.get_portfolio_returns(fund_codes, weights, start_date, end_date)
        
        if df.empty:
            return safe_jsonify({'success': False, 'error': '无法获取数据'}), 400
        
        chart_data = {
            'dates': [str(d) for d in df['date'].tolist()],
            'market_value': df['market_value'].tolist(),
            'total_cost': df['total_cost'].tolist(),
            'total_return': df['total_return'].tolist(),
            'return_rate': (df['return_rate'] * 100).tolist()
        }
        
        latest = df.iloc[-1]
        
        return safe_jsonify({
            'success': True,
            'chart_data': chart_data,
            'summary': {
                'market_value': float(latest['market_value']),
                'total_cost': float(latest['total_cost']),
                'total_return': float(latest['total_return']),
                'return_rate': float(latest['return_rate']) * 100
            }
        })
        
    except Exception as e:
        logger.error(f"获取组合定投收益失败: {e}")
        return safe_jsonify({'success': False, 'error': str(e)}), 500


def add_dip_transaction():
    """添加定投交易记录"""
    try:
        data = request.get_json() or {}
        
        fund_code = data.get('fund_code')
        fund_name = data.get('fund_name', fund_code)
        trade_date = data.get('trade_date')
        trade_type = data.get('trade_type', 'buy')
        amount = float(data.get('amount', 0))
        nav = float(data.get('nav', 0))
        
        if not fund_code or not trade_date or amount <= 0 or nav <= 0:
            return safe_jsonify({'success': False, 'error': '参数不完整'}), 400
        
        shares = amount / nav
        
        total_shares, total_cost, avg_cost = _calculate_cumulative(fund_code, trade_date, amount, shares)
        
        sql = """
            INSERT INTO dip_transactions 
            (user_id, fund_code, fund_name, trade_date, trade_type, amount, nav, shares, 
             total_shares, total_cost, avg_cost)
            VALUES ('default_user', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        db_manager.execute_sql(sql, (
            fund_code, fund_name, trade_date, trade_type, 
            amount, nav, shares, total_shares, total_cost, avg_cost
        ))
        
        return safe_jsonify({
            'success': True,
            'message': '交易记录添加成功',
            'data': {
                'fund_code': fund_code,
                'trade_date': trade_date,
                'amount': amount,
                'nav': nav,
                'shares': shares,
                'total_shares': total_shares,
                'total_cost': total_cost,
                'avg_cost': avg_cost
            }
        })
        
    except Exception as e:
        logger.error(f"添加定投交易记录失败: {e}")
        return safe_jsonify({'success': False, 'error': str(e)}), 500


def _calculate_cumulative(fund_code: str, trade_date: str, amount: float, shares: float):
    """计算累计份额、成本和平均成本"""
    try:
        sql = """
            SELECT total_shares, total_cost 
            FROM dip_transactions 
            WHERE user_id = 'default_user' AND fund_code = %s
            ORDER BY trade_date DESC LIMIT 1
        """
        result = db_manager.execute_query(sql, (fund_code,))
        
        if result is not None and not result.empty:
            prev_total_shares = float(result.iloc[0]['total_shares'])
            prev_total_cost = float(result.iloc[0]['total_cost'])
        else:
            prev_total_shares = 0
            prev_total_cost = 0
        
        total_shares = prev_total_shares + shares
        total_cost = prev_total_cost + amount
        avg_cost = total_cost / total_shares if total_shares > 0 else 0
        
        return total_shares, total_cost, avg_cost
        
    except Exception as e:
        logger.warning(f"计算累计数据失败: {e}")
        return shares, amount, amount / shares if shares > 0 else 0


def get_dip_transactions(fund_code):
    """获取基金的定投交易记录"""
    try:
        sql = """
            SELECT id, trade_date, trade_type, amount, nav, shares, 
                   total_shares, total_cost, avg_cost, notes, created_at
            FROM dip_transactions
            WHERE user_id = 'default_user' AND fund_code = %s
            ORDER BY trade_date DESC
        """
        
        result = db_manager.execute_query(sql, (fund_code,))
        
        if result is None or result.empty:
            return safe_jsonify({'success': True, 'transactions': []})
        
        transactions = result.to_dict('records')
        
        for t in transactions:
            t['amount'] = float(t['amount'])
            t['nav'] = float(t['nav'])
            t['shares'] = float(t['shares'])
            t['total_shares'] = float(t['total_shares'])
            t['total_cost'] = float(t['total_cost'])
            t['avg_cost'] = float(t['avg_cost'])
        
        return safe_jsonify({
            'success': True,
            'transactions': transactions
        })
        
    except Exception as e:
        logger.error(f"获取定投交易记录失败: {e}")
        return safe_jsonify({'success': False, 'error': str(e)}), 500



# ==================== 重构版投资建议页面 API ====================

def get_investment_advice_holdings():
    """
    获取投资建议页面的持仓列表
    
    Returns:
        持仓基金列表，包含基金代码、名称、份额、成本等信息
    """
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        sql = """
        SELECT 
            h.fund_code,
            h.fund_name,
            h.holding_shares as shares,
            h.cost_price,
            h.holding_amount as total_cost,
            h.notes,
            h.updated_at as last_updated,
            COALESCE(f.latest_nav, 0) as latest_nav,
            COALESCE(f.nav_date, '') as nav_date,
            COALESCE(f.today_return, 0) as today_return
        FROM user_holdings h
        LEFT JOIN fund_nav f ON h.fund_code = f.fund_code
        WHERE h.user_id = :user_id
        ORDER BY h.holding_amount DESC
        """
        
        df = db_manager.execute_query(sql, {'user_id': user_id})
        
        if df.empty:
            return safe_jsonify({'success': True, 'data': [], 'total': 0})
        
        holdings = []
        for _, row in df.iterrows():
            shares = _safe_round_float(row.get('shares'), 0)
            cost_price = _safe_round_float(row.get('cost_price'), 0)
            latest_nav = _safe_round_float(row.get('latest_nav'), 0)
            today_return = _safe_round_float(row.get('today_return'), 0)
            
            market_value = shares * latest_nav if shares and latest_nav else 0
            total_cost = _safe_round_float(row.get('total_cost'), 0)
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
        
        return safe_jsonify({
            'success': True, 
            'data': holdings, 
            'total': len(holdings)
        })
        
    except Exception as e:
        logger.error(f"获取投资建议持仓列表失败: {str(e)}")
        traceback.print_exc()
        return safe_jsonify({'success': False, 'error': str(e)}), 500


def get_investment_advice_strategies():
    """
    获取投资建议页面的策略列表
    
    Returns:
        用户策略列表
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
            return safe_jsonify({'success': True, 'data': [], 'total': 0})
        
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
        
        return safe_jsonify({
            'success': True, 
            'data': strategies, 
            'total': len(strategies)
        })
        
    except Exception as e:
        logger.error(f"获取策略列表失败: {str(e)}")
        traceback.print_exc()
        return safe_jsonify({'success': False, 'error': str(e)}), 500


def run_investment_advice_backtest():
    """
    执行组合回测
    
    Request Body:
        - fund_codes: 基金代码列表
        - strategy_id: 策略ID（可选）
        - start_date: 开始日期
        - end_date: 结束日期
        - initial_capital: 初始资金
    """
    try:
        data = request.get_json()
        fund_codes = data.get('fund_codes', [])
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        initial_capital = data.get('initial_capital', 100000.0)
        weights = data.get('weights', {})
        
        if not fund_codes:
            return safe_jsonify({'success': False, 'error': '请选择至少一只基金'}), 400
        
        # 如果没有指定日期，使用最近一年
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start = datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=365)
            start_date = start.strftime('%Y-%m-%d')
        
        # 导入回测相关模块
        from backtesting.core.akshare_data_fetcher import fetch_fund_history_from_akshare
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
            return safe_jsonify({'success': False, 'error': '无法获取基金历史数据'}), 400
        
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

        # 加权汇总最大回撤和夏普比率
        weighted_max_dd = 0.0
        weighted_sharpe = 0.0
        weight_sum = 0.0
        for fr in fund_results:
            fw = weights.get(fr['fund_code'], 1.0 / len(portfolio_data))
            weighted_max_dd += fr['max_drawdown'] * fw
            weighted_sharpe += fr['sharpe_ratio'] * fw
            weight_sum += fw
        if weight_sum > 0:
            weighted_max_dd = round(weighted_max_dd / weight_sum, 2)
            weighted_sharpe = round(weighted_sharpe / weight_sum, 2)

        # 生成简化收益曲线
        chart_data = _generate_simple_return_curve(portfolio_data, weights, initial_capital)
        
        result = {
            'fund_codes': fund_codes,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': initial_capital,
            'fund_results': fund_results,
            'portfolio_summary': {
                'total_return': round(total_return, 2),
                'annualized_return': round(annualized_return, 2),
                'max_drawdown': weighted_max_dd,
                'sharpe_ratio': weighted_sharpe,
                'backtest_days': 365
            },
            'chart_data': chart_data
        }
        
        return safe_jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"执行组合回测失败: {str(e)}")
        traceback.print_exc()
        return safe_jsonify({'success': False, 'error': str(e)}), 500


def _generate_simple_return_curve(portfolio_data, weights, initial_capital):
    """生成简化收益曲线数据"""
    try:
        # 使用第一个基金的数据生成简化曲线
        if not portfolio_data:
            return {
                'dates': [],
                'portfolio_values': [],
                'initial_capital': initial_capital,
                'final_value': initial_capital
            }
        
        df = portfolio_data[0]['data'].copy()
        
        # 检查日期列的名称
        date_col = None
        for col in df.columns:
            if col.lower() in ['date', 'datetime', 'time', '日期']:
                date_col = col
                break
        
        if date_col is None:
            # 如果没有日期列，使用索引作为x轴
            dates = [f"第{i+1}天" for i in range(len(df))]
        else:
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.sort_values(date_col)
            dates = df[date_col].dt.strftime('%Y-%m-%d').tolist()
        
        nav_values = df['nav'].astype(float).values
        
        # 计算累计收益率
        start_nav = nav_values[0]
        cumulative_returns = [(nav / start_nav - 1) for nav in nav_values]
        
        # 计算组合市值
        portfolio_values = [initial_capital * (1 + r) for r in cumulative_returns]
        
        return {
            'dates': dates,
            'portfolio_values': [round(v, 2) for v in portfolio_values],
            'initial_capital': initial_capital,
            'final_value': round(portfolio_values[-1], 2) if portfolio_values else initial_capital
        }
        
    except Exception as e:
        logger.error(f"生成收益曲线失败: {e}")
        return {
            'dates': [],
            'portfolio_values': [],
            'initial_capital': initial_capital,
            'final_value': initial_capital
        }


def generate_investment_advice_api():
    """
    生成专业投资建议（基金经理视角）
    
    Request Body:
        - fund_codes: 基金代码列表
        - strategy_id: 策略ID（可选）
        - initial_capital: 初始资金（可选，默认100000）
    """
    try:
        data = request.get_json()
        fund_codes = data.get('fund_codes', [])
        initial_capital = data.get('initial_capital', 100000)
        
        if not fund_codes:
            return safe_jsonify({'success': False, 'error': '请选择至少一只基金'}), 400
        
        # 调用现有的个性化建议生成逻辑
        from web.routes.analysis import get_personalized_investment_advice_parallel
        from web.routes.holdings_advice_enhanced import enhance_investment_advice_professional
        
        advice_result = get_personalized_investment_advice_parallel(fund_codes)
        
        if not advice_result.get('success'):
            return safe_jsonify(advice_result), 500
        
        # 增强建议的专业性（基金经理视角）
        enhanced_result = enhance_investment_advice_professional(
            fund_codes, advice_result, initial_capital, db_manager
        )
        
        return safe_jsonify(enhanced_result)
        
    except Exception as e:
        logger.error(f"生成投资建议失败: {str(e)}")
        traceback.print_exc()
        return safe_jsonify({'success': False, 'error': str(e)}), 500


def get_investment_advice_valuation():
    """获取基金估值数据"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            fund_codes = data.get('fund_codes', [])
        else:
            fund_codes = request.args.getlist('fund_codes')
        
        if not fund_codes:
            return safe_jsonify({'success': False, 'error': '请提供基金代码'}), 400
        
        from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
        
        adapter = MultiSourceDataAdapter()
        valuations = []
        
        for fund_code in fund_codes:
            try:
                data = adapter.get_realtime_data(fund_code, '')
                valuations.append({
                    'fund_code': fund_code,
                    'fund_name': data.get('name', fund_code),
                    'today_return': _safe_round_float(data.get('today_return'), 0),
                    'estimated_nav': _safe_round_float(data.get('estimated_nav'), 0),
                    'last_nav': _safe_round_float(data.get('last_nav'), 0),
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
        
        return safe_jsonify({
            'success': True,
            'data': valuations
        })
        
    except Exception as e:
        logger.error(f"获取基金估值失败: {str(e)}")
        return safe_jsonify({'success': False, 'error': str(e)}), 500
