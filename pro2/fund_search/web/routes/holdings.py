#!/usr/bin/env python
# coding: utf-8

"""
持仓管理相关 API 路由
从 app.py 中提取的持仓管理功能
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
from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
from data_retrieval.fund_screenshot_ocr import recognize_fund_screenshot, validate_recognized_fund
from data_retrieval.heavyweight_stocks_fetcher import fetch_heavyweight_stocks, get_fetcher
from services.fund_type_service import (
    FundTypeService, classify_fund, get_fund_type_display, 
    get_fund_type_css_class, FUND_TYPE_CN, FUND_TYPE_CSS_CLASS
)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 全局变量（由 register_routes 函数初始化）
db_manager = None
holding_service = None
cache_manager = None


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
    app.route('/api/holdings/import/screenshot', methods=['POST'])(import_holding_screenshot)
    app.route('/api/holdings/import/confirm', methods=['POST'])(import_holding_confirm)
    app.route('/api/holdings', methods=['POST'])(add_holding)
    app.route('/api/holdings/<fund_code>', methods=['PUT'])(update_holding)
    app.route('/api/holdings/clear', methods=['DELETE'])(clear_holdings)
    app.route('/api/holdings/analyze/correlation-interactive', methods=['POST'])(analyze_fund_correlation_interactive)
    app.route('/api/holdings/analyze/correlation', methods=['POST'])(analyze_fund_correlation)
    app.route('/api/holdings/analyze/comprehensive', methods=['POST'])(analyze_comprehensive)
    app.route('/api/analysis', methods=['POST'])(start_analysis)
    app.route('/api/holdings/<fund_code>', methods=['DELETE'])(delete_holding)


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


def get_strategies_metadata():
    """获取策略元数据（从策略对比报告中解析）
    
    返回五个策略的详细信息，包括绩效指标
    """
    try:
        from backtesting.strategy_report_parser import StrategyReportParser
        
        # 策略报告路径 - 使用绝对路径
        import os
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        report_path = os.path.join(base_path, 'fund_backtest', 'strategy_results', 'strategy_comparison_report.md')
        
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
                
                # 绩效指标优先使用 fund_analysis_results 的数据
                sharpe_ratio = analysis_data.get('sharpe_ratio') if analysis_data.get('sharpe_ratio') is not None else data.get('sharpe_ratio')
                max_drawdown = analysis_data.get('max_drawdown') if analysis_data.get('max_drawdown') is not None else data.get('max_drawdown')
                annualized_return = analysis_data.get('annualized_return') if analysis_data.get('annualized_return') is not None else data.get('annualized_return')
                volatility = analysis_data.get('volatility') if analysis_data.get('volatility') is not None else data.get('volatility')
                calmar_ratio = analysis_data.get('calmar_ratio') if analysis_data.get('calmar_ratio') is not None else data.get('calmar_ratio')
                sortino_ratio = analysis_data.get('sortino_ratio') if analysis_data.get('sortino_ratio') is not None else data.get('sortino_ratio')
                composite_score = analysis_data.get('composite_score') if analysis_data.get('composite_score') is not None else data.get('composite_score')
                
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
                    # 绩效指标
                    'sharpe_ratio': sharpe_ratio,
                    'sharpe_ratio_ytd': analysis_data.get('sharpe_ratio_ytd') if analysis_data.get('sharpe_ratio_ytd') is not None else sharpe_ratio,
                    'sharpe_ratio_1y': analysis_data.get('sharpe_ratio_1y') if analysis_data.get('sharpe_ratio_1y') is not None else sharpe_ratio,
                    'sharpe_ratio_all': analysis_data.get('sharpe_ratio_all') if analysis_data.get('sharpe_ratio_all') is not None else sharpe_ratio,
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
                # 绩效指标
                'sharpe_ratio': round(sharpe_ratio, 4) if sharpe_ratio is not None else None,
                'sharpe_ratio_ytd': round(sharpe_ratio_ytd, 4) if sharpe_ratio_ytd is not None else None,
                'sharpe_ratio_1y': round(sharpe_ratio_1y, 4) if sharpe_ratio_1y is not None else None,
                'sharpe_ratio_all': round(sharpe_ratio_all, 4) if sharpe_ratio_all is not None else None,
                'max_drawdown': round(max_drawdown * 100, 2) if max_drawdown is not None else None,
                'volatility': round(volatility * 100, 2) if volatility is not None else None,
                'annualized_return': round(annualized_return * 100, 2) if annualized_return is not None else None,
                'calmar_ratio': round(calmar_ratio, 4) if calmar_ratio is not None else None,
                'sortino_ratio': round(sortino_ratio, 4) if sortino_ratio is not None else None,
                'composite_score': round(composite_score, 4) if composite_score is not None else None
            }
            holdings.append(holding)
        
        return jsonify({'success': True, 'data': holdings, 'total': len(holdings)})
        
    except Exception as e:
        logger.error(f"获取持仓列表失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


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
        from data_retrieval.fund_screenshot_ocr import recognize_fund_screenshot
        
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
            from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
            from backtesting.enhanced_strategy import EnhancedInvestmentStrategy
            
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
    分析基金相关性（交互式图表版本）
    """
    try:
        data = request.get_json()
        fund_codes = data.get('fund_codes', [])
        
        if len(fund_codes) < 2:
            return jsonify({'success': False, 'error': '至少需要2只基金进行相关性分析'})
        
        # 获取基金名称映射
        fund_names = {}
        for code in fund_codes:
            fund_name = None
            
            # 首先尝试从 fund_basic_info 表获取
            try:
                fund_info = db_manager.get_fund_detail(code)
                if fund_info and 'fund_name' in fund_info:
                    fund_name = fund_info['fund_name']
            except Exception as e:
                logger.warning(f"从fund_basic_info获取基金 {code} 信息失败: {e}")
            
            # 如果fund_basic_info中没有，尝试从fund_analysis_results表获取
            if not fund_name:
                try:
                    sql = """
                    SELECT fund_name FROM fund_analysis_results 
                    WHERE fund_code = %(fund_code)s 
                    LIMIT 1
                    """
                    df = pd.read_sql(sql, db_manager.engine, params={'fund_code': code})
                    if not df.empty and pd.notna(df.iloc[0]['fund_name']):
                        fund_name = df.iloc[0]['fund_name']
                except Exception as e:
                    logger.warning(f"从fund_analysis_results获取基金 {code} 名称失败: {e}")
            
            # 如果都没有找到，使用基金代码作为名称
            fund_names[code] = fund_name if fund_name else code
            
            logger.info(f"基金 {code} 的名称: {fund_names[code]}")
        
        # 获取基金历史数据
        fund_data_dict = {}
        for code in fund_codes:
            # 直接查询数据库获取净值历史数据
            try:
                from datetime import datetime, timedelta
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=365)
                
                sql = """
                SELECT nav_date as date, current_nav as nav 
                FROM fund_analysis_results 
                WHERE fund_code = %(fund_code)s 
                AND nav_date BETWEEN %(start_date)s AND %(end_date)s
                ORDER BY nav_date
                """
                
                df = pd.read_sql(sql, db_manager.engine, params={
                    'fund_code': code,
                    'start_date': start_date,
                    'end_date': end_date
                })
                
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.sort_values('date')
                    # 计算日收益率
                    df['daily_return'] = df['nav'].pct_change() * 100
                    fund_data_dict[code] = df
            except Exception as e:
                logger.warning(f"获取基金 {code} 历史数据失败: {e}")
                continue
        
        if len(fund_data_dict) < 2:
            # 如果没有足够的真实数据，尝试从akshare获取
            logger.warning("数据库数据不足，尝试从akshare获取")
            fund_data_dict = _fetch_fund_data_from_akshare(fund_codes, fund_names)
        
        if len(fund_data_dict) < 2:
            return jsonify({'success': False, 'error': '数据不足，无法进行相关性分析'})

        # 导入相关性分析模块
        from backtesting.enhanced_correlation import EnhancedCorrelationAnalyzer
        
        # 创建分析器实例
        analyzer = EnhancedCorrelationAnalyzer()
        
        # 生成交互式图表数据
        interactive_data = analyzer.generate_interactive_correlation_data(
            fund_data_dict, fund_names
        )
        
        if not interactive_data:
            return jsonify({'success': False, 'error': '无法生成相关性分析数据'})
        
        return jsonify({
            'success': True,
            'data': interactive_data
        })
        
    except Exception as e:
        logger.error(f"交互式相关性分析失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


def _fetch_fund_data_from_akshare(fund_codes: list, fund_names: dict) -> dict:
    """
    从akshare获取基金历史净值数据
    用于相关性分析时数据库数据不足的情况
    """
    import akshare as ak
    from datetime import datetime, timedelta
    
    fund_data_dict = {}
    
    for code in fund_codes:
        try:
            # 获取基金历史净值
            nav_df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
            
            if nav_df is not None and not nav_df.empty and len(nav_df) >= 30:
                # 处理数据
                nav_df = nav_df.rename(columns={
                    '净值日期': 'date',
                    '单位净值': 'nav'
                })
                
                # 确保日期格式正确
                nav_df['date'] = pd.to_datetime(nav_df['date'])
                
                # 按日期排序
                nav_df = nav_df.sort_values('date')
                
                # 只取最近一年的数据
                one_year_ago = datetime.now() - timedelta(days=365)
                nav_df = nav_df[nav_df['date'] >= one_year_ago]
                
                # 确保净值为数值类型
                nav_df['nav'] = pd.to_numeric(nav_df['nav'], errors='coerce')
                nav_df = nav_df.dropna(subset=['nav'])
                
                # 计算日收益率
                nav_df['daily_return'] = nav_df['nav'].pct_change() * 100
                nav_df = nav_df.dropna()
                
                if len(nav_df) >= 10:
                    fund_data_dict[code] = nav_df
                    logger.info(f"从akshare获取基金 {code} 数据成功: {len(nav_df)} 条记录")
        
        except Exception as e:
            logger.warning(f"从akshare获取基金 {code} 数据失败: {str(e)}")
            continue
    
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
    """为资产配置获取基金类型 - 使用证监会标准分类"""
    # 首先从fund_basic_info获取官方类型
    try:
        sql = """
        SELECT fund_name, fund_type FROM fund_basic_info 
        WHERE fund_code = :fund_code 
        LIMIT 1
        """
        df = db_manager.execute_query(sql, {'fund_code': fund_code})
        if not df.empty:
            fund_name = df.iloc[0]['fund_name'] if pd.notna(df.iloc[0]['fund_name']) else ''
            official_type = df.iloc[0]['fund_type'] if pd.notna(df.iloc[0]['fund_type']) else ''
            return classify_fund(fund_name, fund_code, official_type)
    except:
        pass
    
    # 备选：从fund_analysis_results获取基金名称
    try:
        sql = """
        SELECT fund_name FROM fund_analysis_results 
        WHERE fund_code = :fund_code 
        ORDER BY analysis_date DESC LIMIT 1
        """
        df = db_manager.execute_query(sql, {'fund_code': fund_code})
        if not df.empty and pd.notna(df.iloc[0]['fund_name']):
            return classify_fund(df.iloc[0]['fund_name'], fund_code)
    except:
        pass
    
    return 'unknown'


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
    分析基金相关性（增强版）
    """
    try:
        data = request.get_json()
        if not data or 'fund_codes' not in data:
            return jsonify({'success': False, 'error': '缺少基金代码'})
        
        fund_codes = data['fund_codes']
        if len(fund_codes) < 2:
            return jsonify({'success': False, 'error': '至少需要2只基金进行相关性分析'})
        
        # 获取增强分析选项
        enhanced_analysis = data.get('enhanced_analysis', True)
        
        # 导入相关性分析模块
        from data_retrieval.fund_analyzer import FundAnalyzer
        from backtesting.enhanced_correlation import EnhancedCorrelationAnalyzer
        
        # 基础相关性分析
        analyzer = FundAnalyzer()
        basic_result = analyzer.analyze_correlation(fund_codes, use_cache=False)
        
        result = {
            'success': True,
            'data': {
                'basic_correlation': basic_result
            }
        }
        
        # 增强相关性分析
        if enhanced_analysis:
            try:
                # 获取基金详细数据用于增强分析
                from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
                fund_data_manager = MultiSourceDataAdapter()
                
                fund_data_dict = {}
                fund_names = {}
                
                for fund_code in fund_codes:
                    try:
                        # 获取基金名称
                        fund_name = analyzer._get_fund_name(fund_code)
                        if not fund_name:
                            fund_info = fund_data_manager.get_fund_basic_info(fund_code)
                            fund_name = fund_info.get('fund_name', fund_code)
                        fund_names[fund_code] = fund_name
                        
                        # 获取历史数据
                        nav_data = fund_data_manager.get_historical_data(fund_code, days=365)
                        if not nav_data.empty and 'daily_return' in nav_data.columns:
                            fund_data_dict[fund_code] = nav_data
                            
                    except Exception as e:
                        logger.warning(f"获取基金 {fund_code} 数据失败: {e}")
                        continue
                
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
                    
            except Exception as e:
                logger.error(f"增强相关性分析失败: {e}")
                # 即使增强分析失败，也要返回基础分析结果
                result['data']['enhanced_error'] = str(e)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"分析基金相关性失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def start_analysis():
    """开始分析 - 重构版API"""
    try:
        data = request.get_json()
        funds = data.get('funds', [])
        
        if len(funds) < 2:
            return jsonify({'success': False, 'error': '请至少选择2只基金'}), 400
        
        if len(funds) > 20:
            return jsonify({'success': False, 'error': '最多支持20只基金同时分析'}), 400
        
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
        import akshare as ak
        
        # 获取基金持仓数据
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
        import requests
        import json
        
        # 天天基金网API
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
        import requests
        
        # 新浪财经API
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
        if 'fund_code' in holdings_df.columns:
            for _, row in holdings_df.iterrows():
                stock_key = (str(row.get('stock_code', '')), str(row.get('stock_name', '')))
                fund_code = str(row.get('fund_code', ''))
                proportion = float(row.get('proportion', 0))
                
                if stock_key not in stock_fund_map:
                    stock_fund_map[stock_key] = []
                
                # 避免重复添加同一基金
                existing_codes = [f['fund_code'] for f in stock_fund_map[stock_key]]
                if fund_code and fund_code not in existing_codes:
                    stock_fund_map[stock_key].append({
                        'fund_code': fund_code,
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
        import traceback
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
    获取基金策略分析数据（集成enhanced_main.py的策略逻辑）
    
    Args:
        fund_codes: 基金代码列表
        
    Returns:
        dict: 包含策略分析结果的字典
    """
    try:
        from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
        from backtesting.enhanced_strategy import EnhancedInvestmentStrategy
        
        fund_data_manager = MultiSourceDataAdapter()
        strategy_engine = EnhancedInvestmentStrategy()
        
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
                
                # 投资策略分析
                strategy_result = strategy_engine.analyze_strategy(today_return, prev_day_return, performance_metrics)
                
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
                    'buy_multiplier': strategy_result.get('buy_multiplier', 0.0),
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
    """从数据库获取基金名称"""
    try:
        sql = "SELECT fund_name FROM user_holdings WHERE fund_code = :fund_code LIMIT 1"
        result = db_manager.execute_query(sql, {'fund_code': fund_code})
        if result is not None and not result.empty:
            return result.iloc[0]['fund_name']
        return None
    except Exception as e:
        logger.warning(f"获取基金名称失败: {e}")
        return None
