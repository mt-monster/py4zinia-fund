#!/usr/bin/env python
# coding: utf-8

"""
策略回测和基金配置相关的 API 路由
"""

import os
import sys
from flask import Flask, render_template, jsonify, request, Response
import pandas as pd
from datetime import datetime, timedelta
import logging

# 添加父目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_access.enhanced_database import EnhancedDatabaseManager
from backtesting.strategies.enhanced_strategy import EnhancedInvestmentStrategy
from backtesting.core.unified_strategy_engine import UnifiedStrategyEngine
from backtesting.analysis.strategy_evaluator import StrategyEvaluator
from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
from data_retrieval.fetchers.heavyweight_stocks_fetcher import fetch_heavyweight_stocks, get_fetcher
from services.fund_type_service import (
    FundTypeService, classify_fund, get_fund_type_display, 
    get_fund_type_css_class, FUND_TYPE_CN, FUND_TYPE_CSS_CLASS
)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 初始化组件
db_manager = None
strategy_engine = None
unified_strategy_engine = None
strategy_evaluator = None
fund_data_manager = None

# 缓存服务组件
cache_manager = None
holding_service = None
sync_service = None

# ==================== 策略回测 API ====================

from backtesting.core.backtest_api import (
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


def export_backtest_trades(task_id):
    """导出交易记录为CSV"""
    try:
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


def get_fund_asset_allocation(fund_code):
    """获取基金资产配置数据"""
    try:
        import akshare as ak
        
        # 获取基金资产配置数据
        try:
            # fund_portfolio_hold_em 获取基金持仓数据
            allocation_df = ak.fund_portfolio_hold_em(symbol=fund_code, date="2024")
            
            if allocation_df is None or allocation_df.empty:
                allocation_df = ak.fund_portfolio_hold_em(symbol=fund_code, date="2023")
            
            if allocation_df is not None and not allocation_df.empty:
                # 计算资产配置比例
                stock_ratio = 0
                bond_ratio = 0
                cash_ratio = 0
                other_ratio = 0
                
                # 从持仓数据中统计
                if '占净值比例' in allocation_df.columns:
                    stock_ratio = allocation_df['占净值比例'].sum()
                    # 假设剩余部分为债券、现金等
                    remaining = 100 - stock_ratio
                    bond_ratio = remaining * 0.6  # 假设60%为债券
                    cash_ratio = remaining * 0.3  # 假设30%为现金
                    other_ratio = remaining * 0.1  # 假设10%为其他
                
                return jsonify({
                    'success': True,
                    'data': {
                        'stock_ratio': round(stock_ratio, 2),
                        'bond_ratio': round(bond_ratio, 2),
                        'cash_ratio': round(cash_ratio, 2),
                        'other_ratio': round(other_ratio, 2)
                    }
                })
        except Exception as e:
            logger.warning(f"获取基金资产配置失败: {str(e)}")
        
        # 返回默认数据
        return jsonify({
            'success': True,
            'data': {
                'stock_ratio': 0,
                'bond_ratio': 0,
                'cash_ratio': 0,
                'other_ratio': 0
            }
        })
        
    except Exception as e:
        logger.error(f"获取基金资产配置失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def get_fund_industry_allocation(fund_code):
    """获取基金行业配置数据"""
    try:
        import akshare as ak
        
        # 获取基金行业配置数据
        try:
            # fund_portfolio_industry_allocation_em 获取基金行业配置
            industry_df = ak.fund_portfolio_industry_allocation_em(symbol=fund_code, indicator="行业配置")
            
            if industry_df is not None and not industry_df.empty:
                industries = []
                for _, row in industry_df.head(10).iterrows():
                    industry_name = str(row.get('行业类别', ''))
                    ratio = row.get('占净值比例', 0)
                    market_value = row.get('市值', 0)
                    
                    if pd.notna(ratio):
                        ratio = float(ratio)
                    else:
                        ratio = 0
                    
                    if pd.notna(market_value):
                        market_value = float(market_value)
                    else:
                        market_value = 0
                    
                    industries.append({
                        'name': industry_name,
                        'ratio': round(ratio, 2),
                        'market_value': round(market_value, 2)
                    })
                
                return jsonify({
                    'success': True,
                    'data': industries
                })
        except Exception as e:
            logger.warning(f"获取基金行业配置失败: {str(e)}")
        
        # 返回空数据
        return jsonify({
            'success': True,
            'data': []
        })
        
    except Exception as e:
        logger.error(f"获取基金行业配置失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def get_fund_bond_allocation(fund_code):
    """获取基金债券配置数据"""
    try:
        import akshare as ak
        
        # 获取基金债券配置数据
        try:
            # fund_portfolio_bond_hold_em 获取基金债券持仓
            bond_df = ak.fund_portfolio_bond_hold_em(symbol=fund_code, date="2024")
            
            if bond_df is None or bond_df.empty:
                bond_df = ak.fund_portfolio_bond_hold_em(symbol=fund_code, date="2023")
            
            if bond_df is not None and not bond_df.empty:
                bonds = []
                for _, row in bond_df.head(10).iterrows():
                    bond_name = str(row.get('债券名称', ''))
                    bond_code = str(row.get('债券代码', ''))
                    ratio = row.get('占净值比例', 0)
                    market_value = row.get('市值', 0)
                    
                    if pd.notna(ratio):
                        ratio = float(ratio)
                    else:
                        ratio = 0
                    
                    if pd.notna(market_value):
                        market_value = float(market_value)
                    else:
                        market_value = 0
                    
                    bonds.append({
                        'name': bond_name,
                        'code': bond_code,
                        'ratio': round(ratio, 2),
                        'market_value': round(market_value, 2)
                    })
                
                return jsonify({
                    'success': True,
                    'data': bonds
                })
        except Exception as e:
            logger.warning(f"获取基金债券配置失败: {str(e)}")
        
        # 返回空数据
        return jsonify({
            'success': True,
            'data': []
        })
        
    except Exception as e:
        logger.error(f"获取基金债券配置失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def get_fund_heavyweight_stocks(fund_code):
    """
    获取基金重仓股数据（实时）
    
    Args:
        fund_code: 基金代码
        
    Query Parameters:
        date: 报告期日期（可选，格式：YYYYMMDD）
        refresh: 是否强制刷新缓存（可选，true/false）
        
    Returns:
        JSON: {
            success: bool,
            data: [
                {
                    name: str,          # 股票名称
                    code: str,          # 股票代码
                    holding_ratio: str, # 持仓占比
                    market_value: str,  # 市值（万）
                    change_percent: str # 涨跌幅
                }
            ],
            source: str,        # 数据来源
            timestamp: str,     # 数据时间戳
            error: str          # 错误信息（如果失败）
        }
    """
    try:
        # 获取查询参数
        date = request.args.get('date', None)
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        logger.info(f"获取基金 {fund_code} 的重仓股数据，日期: {date}, 刷新: {refresh}")
        
        # 如果强制刷新，清除缓存
        if refresh:
            fetcher = get_fetcher()
            fetcher.clear_cache(fund_code)
        
        # 获取重仓股数据
        result = fetch_heavyweight_stocks(fund_code, date=date, use_cache=not refresh)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['data'],
                'source': result['source'],
                'timestamp': result['timestamp']
            })
        else:
            logger.error(f"获取重仓股数据失败: {result.get('error', '未知错误')}")
            return jsonify({
                'success': False,
                'error': result.get('error', '获取数据失败'),
                'data': [],
                'timestamp': result.get('timestamp', datetime.now().isoformat())
            }), 500
            
    except Exception as e:
        logger.error(f"获取基金重仓股数据失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}',
            'data': [],
            'timestamp': datetime.now().isoformat()
        }), 500


def clear_heavyweight_stocks_cache(fund_code):
    """
    清除基金重仓股数据缓存
    
    Args:
        fund_code: 基金代码
        
    Returns:
        JSON: {success: bool, message: str}
    """
    try:
        fetcher = get_fetcher()
        fetcher.clear_cache(fund_code)
        
        return jsonify({
            'success': True,
            'message': f'基金 {fund_code} 的重仓股数据缓存已清除'
        })
    except Exception as e:
        logger.error(f"清除缓存失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def run_strategy_backtest_async():
    """
    异步执行策略回测（Celery 版本）

    将耗时回测任务提交到 Celery 队列，立即返回 task_id。
    客户端通过 GET /api/strategy-backtest/async/<task_id> 轮询结果。

    Request JSON:
        strategy_id: 策略ID
        user_id: 用户ID（可选，默认 default_user）
        start_date: 开始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD
        initial_capital: 初始资金（可选，默认 100000）
        rebalance_freq: 再平衡频率（可选，默认 monthly）
    """
    try:
        data = request.get_json()
        strategy_id = data.get('strategy_id')
        if not strategy_id:
            return jsonify({'success': False, 'error': '策略ID不能为空'}), 400

        user_id = data.get('user_id', 'default_user')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        initial_capital = float(data.get('initial_capital', 100000.0))
        rebalance_freq = data.get('rebalance_freq', 'monthly')

        # 尝试使用 Celery 异步提交
        try:
            from celery_tasks import run_backtest_task
            task = run_backtest_task.apply_async(
                kwargs={
                    'strategy_id': strategy_id,
                    'user_id': user_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'initial_capital': initial_capital,
                    'rebalance_freq': rebalance_freq,
                },
                queue='backtest'
            )
            return jsonify({
                'success': True,
                'async': True,
                'task_id': task.id,
                'status': 'PENDING',
                'message': '回测任务已提交，请通过 task_id 轮询结果',
                'poll_url': f'/api/strategy-backtest/async/{task.id}'
            })
        except Exception as celery_err:
            logger.warning(f"Celery 不可用，降级为同步回测: {celery_err}")
            # 降级：同步执行
            handler = get_backtest_handler()
            success, result = handler.run_backtest(
                strategy_id=strategy_id, user_id=user_id,
                start_date=start_date, end_date=end_date,
                initial_capital=initial_capital, rebalance_freq=rebalance_freq
            )
            if success:
                return jsonify({'success': True, 'async': False, 'data': result})
            return jsonify({'success': False, 'error': result.get('error', '回测失败')}), 500

    except Exception as e:
        logger.error(f"提交异步回测失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def get_async_backtest_status(task_id):
    """
    查询 Celery 异步回测任务状态

    Response:
        status: PENDING / STARTED / SUCCESS / FAILURE / RETRY
        result: 任务结果（SUCCESS 时有效）
        error:  错误信息（FAILURE 时有效）
    """
    try:
        from celery_tasks import run_backtest_task
        task = run_backtest_task.AsyncResult(task_id)

        response = {
            'success': True,
            'task_id': task_id,
            'status': task.state,
        }

        if task.state == 'SUCCESS':
            response['result'] = task.result
        elif task.state == 'FAILURE':
            response['error'] = str(task.result)
        elif task.state == 'PENDING':
            response['message'] = '任务排队中，等待 Worker 执行'
        elif task.state == 'STARTED':
            response['message'] = '任务执行中'

        return jsonify(response)

    except ImportError:
        return jsonify({'success': False, 'error': 'Celery 不可用'}), 503
    except Exception as e:
        logger.error(f"查询异步回测状态失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def register_routes(app, **kwargs):
    """注册所有回测相关路由"""
    global db_manager, strategy_engine, unified_strategy_engine, strategy_evaluator
    global fund_data_manager, cache_manager, holding_service, sync_service
    
    # 从 kwargs 获取依赖
    db_manager = kwargs.get('db_manager')
    strategy_engine = kwargs.get('strategy_engine')
    unified_strategy_engine = kwargs.get('unified_strategy_engine')
    strategy_evaluator = kwargs.get('strategy_evaluator')
    fund_data_manager = kwargs.get('fund_data_manager')
    cache_manager = kwargs.get('cache_manager')
    holding_service = kwargs.get('holding_service')
    
    # 注册路由
    app.route('/api/strategy-backtest', methods=['POST'])(run_strategy_backtest)
    app.route('/api/strategy-backtest/async', methods=['POST'])(run_strategy_backtest_async)
    app.route('/api/strategy-backtest/async/<task_id>', methods=['GET'])(get_async_backtest_status)
    app.route('/api/strategy-backtest/status/<task_id>', methods=['GET'])(get_backtest_status)
    app.route('/api/strategy-backtest/result/<task_id>', methods=['GET'])(get_backtest_result)
    app.route('/api/strategy-backtest/export/<task_id>', methods=['GET'])(export_backtest_trades)
    app.route('/api/strategy-backtest/trades/filter', methods=['POST'])(filter_backtest_trades)
    app.route('/api/fund/<fund_code>/asset-allocation', methods=['GET'])(get_fund_asset_allocation)
    app.route('/api/fund/<fund_code>/industry-allocation', methods=['GET'])(get_fund_industry_allocation)
    app.route('/api/fund/<fund_code>/bond-allocation', methods=['GET'])(get_fund_bond_allocation)
    app.route('/api/fund/<fund_code>/heavyweight-stocks', methods=['GET'])(get_fund_heavyweight_stocks)
    app.route('/api/fund/<fund_code>/heavyweight-stocks/cache', methods=['DELETE'])(clear_heavyweight_stocks_cache)
