#!/usr/bin/env python
# coding: utf-8

"""
Dashboard 相关 API 路由
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
from data_access.enhanced_database import EnhancedDatabaseManager
from backtesting import EnhancedInvestmentStrategy
from backtesting import UnifiedStrategyEngine
from backtesting import StrategyEvaluator
from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
from data_retrieval.fund_screenshot_ocr import recognize_fund_screenshot, validate_recognized_fund
from data_retrieval.heavyweight_stocks_fetcher import fetch_heavyweight_stocks, get_fetcher
from services.fund_type_service import (
    FundTypeService, classify_fund, get_fund_type_display, 
    get_fund_type_css_class, FUND_TYPE_CN, FUND_TYPE_CSS_CLASS
)
from shared.cache_utils import cached, _global_cache

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 全局变量（将在主 app 中初始化）
db_manager = None
strategy_engine = None
unified_strategy_engine = None
strategy_evaluator = None
fund_data_manager = None

# 缓存服务组件
cache_manager = None
holding_service = None
sync_service = None


def get_recent_activities(user_id='default_user'):
    """获取最近活动记录"""
    try:
        # 从数据库查询实际操作记录
        sql = """
        SELECT 
            operation_date as date,
            operation_type as type,
            fund_name,
            operation_detail as detail
        FROM user_operations
        WHERE user_id = :user_id
        ORDER BY operation_date DESC
        LIMIT 5
        """
        
        df = db_manager.execute_query(sql, {'user_id': user_id})
        
        if df.empty:
            # 如果没有操作记录，返回空列表
            return []
        
        activities = []
        for _, row in df.iterrows():
            activities.append({
                'date': str(row['date']),
                'type': row['type'],
                'fund': row['fund_name'],
                'detail': row['detail']
            })
        
        return activities
    except Exception as e:
        logger.warning(f"获取最近活动失败: {str(e)}")
        return []


def get_real_holding_distribution(user_id='default_user'):
    """获取真实的持仓分布"""
    try:
        sql = """
        SELECT 
            fund_code,
            holding_shares * cost_price as amount
        FROM user_holdings
        WHERE user_id = :user_id
        """
        
        df = db_manager.execute_query(sql, {'user_id': user_id})
        
        if df.empty:
            return []
        
        # 按金额分组
        total = df['amount'].sum()
        if total == 0:
            return []
        
        # 简化处理：按持仓金额比例返回
        distribution = []
        for _, row in df.iterrows():
            distribution.append({
                'name': row['fund_code'],
                'value': round(row['amount'] / total * 100, 1)
            })
        
        return distribution
    except Exception as e:
        logger.warning(f"获取持仓分布失败: {str(e)}")
        return []


# ==================== API 路由 ====================

@cached(ttl=60, key_prefix='dashboard_stats')  # 缓存1分钟
def get_dashboard_stats():
    """获取仪表盘统计数据"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # 获取用户持仓数据
        sql = """
        SELECT h.*, far.today_return, far.prev_day_return, far.sharpe_ratio,
               far.current_estimate as current_nav, far.yesterday_nav as previous_nav
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
        
        df = db_manager.execute_query(sql, {'user_id': user_id})
        
        total_assets = 0  # 总资产 = 持有金额之和
        today_profit = 0
        yesterday_profit = 0  # 昨日收益（用于计算profitChange）
        total_cost = 0
        total_sharpe = 0
        sharpe_count = 0
        
        if not df.empty:
            for _, row in df.iterrows():
                holding_shares = float(row['holding_shares']) if pd.notna(row['holding_shares']) else 0
                cost_price = float(row['cost_price']) if pd.notna(row['cost_price']) else 0
                
                # 分析数据可能缺失
                current_nav = float(row['current_nav']) if pd.notna(row['current_nav']) else None
                previous_nav = float(row['previous_nav']) if pd.notna(row['previous_nav']) else None
                today_return = float(row['today_return']) if pd.notna(row['today_return']) else None
                prev_day_return = float(row['prev_day_return']) if pd.notna(row['prev_day_return']) else None
                sharpe = float(row['sharpe_ratio']) if pd.notna(row['sharpe_ratio']) else None
                
                # 持有金额（成本）= 持有份额 × 成本价
                holding_amount = holding_shares * cost_price
                
                # 总资产 = 所有持仓基金的持有金额之和
                total_assets += holding_amount
                
                # 总成本（与总资产相同，用于计算收益率）
                total_cost += holding_amount
                
                # 计算今日收益
                if current_nav is not None and previous_nav is not None and current_nav != previous_nav:
                    # 当前市值 = 持有份额 × 当前净值（用于计算今日收益）
                    current_value = holding_shares * current_nav
                    previous_value = holding_shares * previous_nav
                    
                    # 今日收益 = (当前市值 - 昨日市值)
                    today_profit += (current_value - previous_value)
                    
                    # 昨日收益 = 昨日市值 × 昨日收益率
                    if prev_day_return is not None:
                        yesterday_profit += previous_value * (prev_day_return / 100)
                elif today_return is not None and holding_amount > 0:
                    # 备选方案：使用今日收益率计算
                    # 今日收益 = 持仓金额 × 今日收益率
                    today_profit += holding_amount * (today_return / 100)
                    
                    # 昨日收益 = 持仓金额 × 昨日收益率
                    if prev_day_return is not None:
                        yesterday_profit += holding_amount * (prev_day_return / 100)
                
                if sharpe is not None and sharpe != 0:
                    total_sharpe += sharpe
                    sharpe_count += 1
        
        # 计算资产变化百分比（今日收益占总资产的比例）
        # 资产变化基于今日收益占持仓金额的比例
        assets_change = (today_profit / total_assets * 100) if total_assets > 0 else 0
        
        # 计算收益变化百分比（今日收益相对于昨日收益的变化）
        # profitChange = (今日收益 - 昨日收益) / |昨日收益| × 100%
        if yesterday_profit != 0:
            profit_change = ((today_profit - yesterday_profit) / abs(yesterday_profit)) * 100
        elif yesterday_profit == 0 and today_profit != 0:
            # 昨日收益为0但今日有收益，视为大幅增长
            profit_change = 100.0 if today_profit > 0 else -100.0
        elif yesterday_profit != 0 and today_profit == 0:
            # 今日收益为0但昨日有收益，显示昨日的收益情况（转为负数）
            profit_change = -100.0
        else:
            # 昨日和今日都没有收益，保持为0
            profit_change = 0
        
        avg_sharpe = total_sharpe / sharpe_count if sharpe_count > 0 else 0
        
        # 计算本月新增基金数
        from datetime import datetime
        today = datetime.now()
        first_day_of_month = today.replace(day=1).date()
        new_fund_count = 0
        if not df.empty and 'buy_date' in df.columns:
            for _, row in df.iterrows():
                buy_date = row.get('buy_date')
                if buy_date:
                    try:
                        if isinstance(buy_date, str):
                            buy_date_obj = datetime.strptime(buy_date.split()[0], '%Y-%m-%d').date()
                        else:
                            buy_date_obj = buy_date.date() if hasattr(buy_date, 'date') else buy_date
                        if buy_date_obj >= first_day_of_month:
                            new_fund_count += 1
                    except:
                        pass
        
        # 获取系统状态 - 从数据库获取最新更新时间
        try:
            last_update_sql = "SELECT MAX(analysis_date) as last_date FROM fund_analysis_results"
            last_update_df = db_manager.execute_query(last_update_sql)
            last_update = last_update_df.iloc[0]['last_date'].strftime('%Y-%m-%d %H:%M') if not last_update_df.empty and last_update_df.iloc[0]['last_date'] else datetime.now().strftime('%Y-%m-%d %H:%M')
        except:
            last_update = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        system_status = {
            'lastUpdate': last_update,
            'apiResponseTime': '45',
            'load': 35
        }
        
        # 获取最近活动 - 从数据库查询实际操作记录
        activities = get_recent_activities(user_id)
        
        # 获取真实的持仓分布
        distribution = get_real_holding_distribution(user_id)
        
        return jsonify({
            'success': True,
            'data': {
                'totalAssets': total_assets,
                'assetsChange': assets_change,
                'todayProfit': today_profit,
                'profitChange': profit_change,
                'holdingCount': len(df) if not df.empty else 0,
                'newFundCount': new_fund_count,
                'sharpeRatio': avg_sharpe,
                'system': system_status,
                'activities': activities,
                'distribution': distribution,
                'data_source': {
                    'holdings': 'database:user_holdings',
                    'analysis': 'database:fund_analysis_results',
                    'as_of': system_status.get('lastUpdate')
                }
            }
        })
        
    except Exception as e:
        logger.error(f"获取仪表盘统计数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cached(ttl=300, key_prefix='profit_trend')  # 缓存5分钟，历史数据变化不频繁
def get_profit_trend():
    """获取收益趋势数据（使用真实历史数据）"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        days = request.args.get('days', 90, type=int)  # 修改默认为90天（三个月）
        total_return = request.args.get('total_return', 20, type=float)  # 默认20%总收益
        fund_codes = request.args.get('fund_codes', '000001')  # 基金代码，逗号分隔
        weights = request.args.get('weights', '1.0')  # 权重，逗号分隔
        
        # 优先从预加载器获取（如果已预计算）
        try:
            from services.fund_data_preloader import get_preloader
            preloader = get_preloader()
            cached_trend = preloader.get_profit_trend(days)
            if cached_trend and cached_trend.get('labels'):
                logger.info(f"从预加载缓存获取收益趋势数据（{days}天）")
                return jsonify({
                    'success': True,
                    'data': {
                        'labels': cached_trend['labels'],
                        'profit': cached_trend['profit'],
                        'benchmark': cached_trend['benchmark'],
                        'fund_codes': cached_trend.get('fund_codes', []),
                        'weights': cached_trend.get('weights', []),
                        'data_source': 'preloaded_cache',
                        'benchmark_name': cached_trend.get('benchmark_name', '沪深300'),
                        'benchmark_description': '以沪深300指数作为业绩比较基准'
                    }
                })
        except Exception as e:
            logger.debug(f"从预加载器获取收益趋势失败: {e}")
        
        # 解析基金代码和权重
        fund_code_list = [code.strip() for code in fund_codes.split(',')]
        weight_list = [float(w.strip()) for w in weights.split(',')]
        
        # 检查用户是否有持仓数据
        has_holdings = False
        try:
            holdings_sql = """
            SELECT fund_code, holding_shares, cost_price
            FROM user_holdings 
            WHERE user_id = :user_id AND holding_shares > 0
            """
            holdings_df = db_manager.execute_query(holdings_sql, {'user_id': user_id})
            has_holdings = not holdings_df.empty
        except Exception as e:
            logger.warning(f"检查用户持仓失败: {str(e)}")
            has_holdings = False
        
        # 如果没有持仓数据，返回空数据提示
        if not has_holdings:
            return jsonify({
                'success': True,
                'data': {
                    'labels': [],
                    'profit': [],
                    'benchmark': [],
                    'fund_codes': [],
                    'weights': [],
                    'data_source': 'no_holdings',
                    'message': '暂无持仓数据，请先添加基金持仓',
                    'benchmark_name': '沪深300',
                    'benchmark_description': '以沪深300指数作为业绩比较基准'
                }
            })
        
        # 如果没有提供基金代码且有持仓，则获取用户的持仓基金
        if fund_codes == '000001':
            try:
                # 获取用户持仓数据
                holdings_sql = """
                SELECT fund_code, holding_shares, cost_price
                FROM user_holdings 
                WHERE user_id = :user_id AND holding_shares > 0
                """
                holdings_df = db_manager.execute_query(holdings_sql, {'user_id': user_id})
                
                if not holdings_df.empty:
                    fund_code_list = holdings_df['fund_code'].tolist()
                    # 计算权重基于持仓金额
                    total_amount = 0
                    amounts = []
                    for _, row in holdings_df.iterrows():
                        amount = float(row['holding_shares'] or 0) * float(row['cost_price'] or 0)
                        amounts.append(amount)
                        total_amount += amount
                    
                    if total_amount > 0:
                        weight_list = [amount/total_amount for amount in amounts]
                    else:
                        weight_list = [1.0/len(fund_code_list)] * len(fund_code_list)
            except Exception as e:
                logger.warning(f"获取用户持仓失败: {str(e)}, 使用默认基金")
        
        # 确保权重和基金代码数量一致（仅当不是从持仓获取时）
        if fund_codes != '000001' or user_id == 'default_user':
            if len(weight_list) == 1 and len(fund_code_list) > 1:
                # 如果只有一个权重，平均分配
                weight_list = [1.0/len(fund_code_list)] * len(fund_code_list)
            elif len(weight_list) != len(fund_code_list):
                # 如果权重数量不匹配，平均分配
                weight_list = [1.0/len(fund_code_list)] * len(fund_code_list)
        
        # 归一化权重
        weight_sum = sum(weight_list)
        if weight_sum > 0:
            weight_list = [w/weight_sum for w in weight_list]
        
        # 导入真实数据获取器
        from web.real_data_fetcher import data_fetcher
        
        # 获取沪深300真实历史数据
        csi300_data = data_fetcher.get_csi300_history(days)
        
        # 获取基金组合真实历史净值
        portfolio_data = data_fetcher.calculate_portfolio_nav(
            fund_code_list, weight_list, initial_amount=10000, days=days
        )
        
        if csi300_data.empty or portfolio_data.empty:
            # 如果获取真实数据失败，返回错误
            return jsonify({
                'success': False,
                'error': '无法获取真实历史数据，请检查网络连接或基金代码是否正确'
            }), 500
        
        # 准备返回数据
        labels = []
        profit_data = []
        benchmark_data = []
        
        # 找到共同的日期范围
        portfolio_dates = set(portfolio_data['date'].dt.date)
        csi300_dates = set(csi300_data['date'].dt.date)
        common_dates = sorted(list(portfolio_dates.intersection(csi300_dates)))[:days]
        
        if not common_dates:
            # 如果没有共同日期，分别处理
            logger.warning("没有共同日期，分别处理数据")
            
            # 使用沪深300数据的时间范围
            csi300_sorted = csi300_data.sort_values('date')
            base_portfolio_value = 10000  # 基准初始值
            base_benchmark_value = 10000  # 基准初始值
            
            for _, row in csi300_sorted.tail(days).iterrows():
                labels.append(row['date'].strftime('%m-%d'))
                # 基于基准值计算相对收益
                benchmark_return = (row['price'] / csi300_sorted.iloc[0]['price'] - 1) * 100
                benchmark_data.append(round(base_benchmark_value * (1 + benchmark_return/100), 2))
                
                # 基金数据使用最近的可用数据计算相对收益
                if not portfolio_data.empty:
                    latest_portfolio = portfolio_data.iloc[-1]['portfolio_nav']
                    first_portfolio = portfolio_data.iloc[0]['portfolio_nav']
                    portfolio_return = (latest_portfolio / first_portfolio - 1) * 100
                    profit_data.append(round(base_portfolio_value * (1 + portfolio_return/100), 2))
                else:
                    profit_data.append(base_portfolio_value)  # 默认值
        else:
            # 有共同日期的情况
            # 使用第一个共同日期作为基准点
            base_date = common_dates[0]
            base_portfolio_value = None
            base_benchmark_value = None
            
            for date in common_dates:
                # 格式化日期标签
                labels.append(date.strftime('%m-%d'))
                
                # 获取沪深300数据
                csi300_row = csi300_data[csi300_data['date'].dt.date == date]
                if not csi300_row.empty:
                    current_benchmark = csi300_row.iloc[0]['price']
                    
                    # 设置基准值
                    if base_benchmark_value is None:
                        base_benchmark_value = current_benchmark
                        benchmark_data.append(10000)  # 基准点设为10000
                    else:
                        # 计算相对于基准点的收益
                        benchmark_return = (current_benchmark / base_benchmark_value - 1) * 100
                        benchmark_data.append(round(10000 * (1 + benchmark_return/100), 2))
                else:
                    benchmark_data.append(benchmark_data[-1] if benchmark_data else 10000)
                
                # 获取基金组合数据
                portfolio_row = portfolio_data[portfolio_data['date'].dt.date == date]
                if not portfolio_row.empty:
                    current_portfolio = portfolio_row.iloc[0]['portfolio_nav']
                    
                    # 设置基准值
                    if base_portfolio_value is None:
                        base_portfolio_value = current_portfolio
                        profit_data.append(10000)  # 基准点设为10000
                    else:
                        # 计算相对于基准点的收益
                        portfolio_return = (current_portfolio / base_portfolio_value - 1) * 100
                        profit_data.append(round(10000 * (1 + portfolio_return/100), 2))
                else:
                    profit_data.append(profit_data[-1] if profit_data else 10000)
        
        return jsonify({
            'success': True,
            'data': {
                'labels': labels,
                'profit': profit_data,
                'benchmark': benchmark_data,
                'fund_codes': fund_code_list,
                'weights': weight_list,
                'data_source': 'real_historical_data',  # 标记数据来源
                'data_source_detail': {
                    'portfolio_nav': 'akshare:fund_open_fund_info_em',
                    'benchmark': 'akshare:stock_zh_index_daily',
                    'as_of': datetime.now().strftime('%Y-%m-%d %H:%M')
                },
                'benchmark_name': '沪深300',  # 明确标识基准为沪深300
                'benchmark_description': '以沪深300指数作为业绩比较基准'
            }
        })
        
    except Exception as e:
        logger.error(f"获取收益趋势数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cached(ttl=30, key_prefix='market_index')  # 缓存30秒，市场数据较实时
def get_market_index():
    """获取市场指数实时数据（沪深300）"""
    try:
        symbol = request.args.get('symbol', 'sh000300')
        from web.real_data_fetcher import data_fetcher
        index_data = data_fetcher.get_index_latest(symbol)
        if not index_data:
            return jsonify({'success': False, 'error': '无法获取指数实时数据'}), 500

        return jsonify({
            'success': True,
            'data': {
                'name': index_data.get('name', '沪深300'),
                'value': index_data.get('price'),
                'change': index_data.get('change'),
                'changePercent': index_data.get('change_percent'),
                'date': index_data.get('date')
            },
            'data_source': {
                'index': 'akshare',
                'detail': index_data.get('source')
            }
        })
    except Exception as e:
        logger.error(f"获取市场指数失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cached(ttl=120, key_prefix='allocation')  # 缓存2分钟
def get_allocation():
    """获取资产配置数据 - 按基金类型分布"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # 获取用户持仓
        sql_holdings = """
        SELECT h.fund_code, h.holding_shares, h.cost_price
        FROM user_holdings h
        WHERE h.user_id = :user_id
        """
        
        df_holdings = db_manager.execute_query(sql_holdings, {'user_id': user_id})
        
        if df_holdings.empty:
            return jsonify({
                'success': True,
                'data': {
                    'distribution': [],
                    'totalCount': 0,
                    'totalAmount': 0
                }
            })
        
        # 获取每个基金的类型
        fund_type_map = {}
        for fund_code in df_holdings['fund_code'].tolist():
            fund_type = get_fund_type_for_allocation(fund_code)
            fund_type_map[fund_code] = fund_type
        
        # 按基金类型统计
        type_amounts = {}
        type_count = {}
        total_amount = 0
        
        for _, row in df_holdings.iterrows():
            fund_code = row['fund_code']
            fund_type = fund_type_map.get(fund_code, 'unknown')
            
            holding_amount = float(row['holding_shares']) * float(row['cost_price'])
            
            if fund_type in type_amounts:
                type_amounts[fund_type] += holding_amount
                type_count[fund_type] += 1
            else:
                type_amounts[fund_type] = holding_amount
                type_count[fund_type] = 1
            
            total_amount += holding_amount
        
        # 颜色映射 - 使用证监会标准分类颜色
        from services.fund_type_service import FUND_TYPE_COLORS, FundType
        color_map = {
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
        # 中文名称映射
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
        
        # 构建分布数据
        distribution = []
        for fund_type, amount in sorted(type_amounts.items(), key=lambda x: x[1], reverse=True):
            percentage = round((amount / total_amount) * 100, 1) if total_amount > 0 else 0
            distribution.append({
                'name': f'{cn_name_map.get(fund_type, fund_type)}基金',
                'type_code': fund_type,
                'percentage': percentage,
                'count': type_count.get(fund_type, 0),
                'amount': round(amount, 2),
                'color': color_map.get(fund_type, '#adb5bd')
            })
        
        return jsonify({
            'success': True,
            'data': {
                'distribution': distribution,
                'totalCount': len(df_holdings),
                'totalAmount': round(total_amount, 2),
                'labels': list(type_amounts.keys()),
                'values': list(type_amounts.values())
            }
        })
        
    except Exception as e:
        logger.error(f"获取资产配置数据失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


def get_fund_type_for_allocation(fund_code: str) -> str:
    """为资产配置获取基金类型 - 使用证监会标准分类"""
    
    # 首先尝试从预加载器缓存获取（优先，因为预加载器已加载所有持仓基金信息）
    try:
        from services.fund_data_preloader import get_preloader
        preloader = get_preloader()
        basic_info = preloader.get_fund_basic_info(fund_code)
        if basic_info:
            fund_name = basic_info.get('fund_name', '')
            official_type = basic_info.get('fund_type', '')
            if fund_name or official_type:
                return classify_fund(fund_name, fund_code, official_type)
    except:
        pass
    
    # 备选：从fund_basic_info表获取
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


@cached(ttl=600, key_prefix='holding_stocks')  # 缓存10分钟，重仓股变化不频繁
def get_holding_stocks():
    """
    获取用户持仓基金的重仓股票统计
    
    使用数据库缓存优化，当接口获取太慢时从数据库读取
    """
    try:
        user_id = request.args.get('user_id', 'default_user')
        top_n = request.args.get('top', 10, type=int)
        
        # 获取用户持仓的所有基金
        sql = """
        SELECT h.fund_code, h.fund_name, h.holding_shares, h.cost_price
        FROM user_holdings h
        WHERE h.user_id = :user_id
        """
        df_holdings = db_manager.execute_query(sql, {'user_id': user_id})
        
        if df_holdings.empty:
            return jsonify({
                'success': True,
                'data': {
                    'stocks': [],
                    'totalFunds': 0,
                    'totalStocks': 0
                }
            })
        
        # 汇总所有基金的重仓股
        all_stocks = {}
        total_funds = len(df_holdings)
        fund_codes = df_holdings['fund_code'].tolist()
        fund_name_map = dict(zip(df_holdings['fund_code'], df_holdings['fund_name']))
        
        # 使用批量获取接口，优先从数据库缓存读取
        from data_retrieval.heavyweight_stocks_fetcher import fetch_heavyweight_stocks_batch
        
        logger.info(f"开始批量获取 {len(fund_codes)} 只基金的重仓股数据")
        batch_results = fetch_heavyweight_stocks_batch(fund_codes)
        
        for fund_code in fund_codes:
            fund_name = fund_name_map.get(fund_code, fund_code)
            result = batch_results.get(fund_code, {})
            
            if not result.get('success'):
                logger.warning(f"获取基金 {fund_code} 重仓股失败: {result.get('error', '未知错误')}")
                continue
            
            stocks = result.get('data', [])
            if not stocks:
                continue
            
            # 累加重仓股数据
            for stock in stocks:
                stock_code = stock.get('code', '').strip()
                stock_name = stock.get('name', '').strip()
                # 解析持仓比例（移除%符号）
                ratio_str = stock.get('holding_ratio', '0')
                try:
                    ratio = float(ratio_str.replace('%', '').strip()) if ratio_str != '--' else 0
                except:
                    ratio = 0
                
                if stock_code and stock_name and ratio > 0:
                    if stock_code in all_stocks:
                        all_stocks[stock_code]['count'] += 1
                        all_stocks[stock_code]['total_ratio'] += ratio
                        if fund_name not in all_stocks[stock_code]['funds']:
                            all_stocks[stock_code]['funds'].append(fund_name)
                    else:
                        all_stocks[stock_code] = {
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'count': 1,
                            'total_ratio': ratio,
                            'funds': [fund_name]
                        }
        
        # 转换为列表并排序（按被持仓基金数量排序）
        stocks_list = list(all_stocks.values())
        stocks_list.sort(key=lambda x: (x['count'], x['total_ratio']), reverse=True)
        
        # 取前N只
        top_stocks = stocks_list[:top_n]
        
        # 计算平均持仓比例
        for stock in top_stocks:
            stock['avg_ratio'] = round(stock['total_ratio'] / stock['count'], 2)
            stock['fund_count'] = stock['count']
            del stock['count']
            del stock['total_ratio']
        
        logger.info(f"重仓股统计完成：共 {total_funds} 只基金，{len(stocks_list)} 只不同股票")
        
        return jsonify({
            'success': True,
            'data': {
                'stocks': top_stocks,
                'totalFunds': total_funds,
                'totalStocks': len(stocks_list)
            }
        })
        
    except Exception as e:
        logger.error(f"获取重仓股统计失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


def register_routes(app, **kwargs):
    """注册 Dashboard 相关路由到 Flask 应用"""
    global db_manager, strategy_engine, unified_strategy_engine, strategy_evaluator, fund_data_manager
    global cache_manager, holding_service, sync_service
    
    logger.info(f"Dashboard路由注册开始，收到参数: {list(kwargs.keys())}")
    
    # 从 kwargs 获取组件
    db_manager = kwargs.get('db_manager') or kwargs.get('database_manager')
    strategy_engine = kwargs.get('strategy_engine')
    unified_strategy_engine = kwargs.get('unified_strategy_engine')
    strategy_evaluator = kwargs.get('strategy_evaluator')
    fund_data_manager = kwargs.get('fund_data_manager')
    cache_manager = kwargs.get('cache_manager')
    holding_service = kwargs.get('holding_service')
    sync_service = kwargs.get('sync_service')
    
    logger.info(f"组件初始化状态 - db_manager: {db_manager is not None}, fund_data_manager: {fund_data_manager is not None}")
    
    # 如果 kwargs 中没有，尝试从 app 属性获取
    if db_manager is None:
        db_manager = app.db_manager if hasattr(app, 'db_manager') else None
    if strategy_engine is None:
        strategy_engine = app.strategy_engine if hasattr(app, 'strategy_engine') else None
    if unified_strategy_engine is None:
        unified_strategy_engine = app.unified_strategy_engine if hasattr(app, 'unified_strategy_engine') else None
    if strategy_evaluator is None:
        strategy_evaluator = app.strategy_evaluator if hasattr(app, 'strategy_evaluator') else None
    if fund_data_manager is None:
        fund_data_manager = app.fund_data_manager if hasattr(app, 'fund_data_manager') else None
    if cache_manager is None:
        cache_manager = app.cache_manager if hasattr(app, 'cache_manager') else None
    if holding_service is None:
        holding_service = app.holding_service if hasattr(app, 'holding_service') else None
    if sync_service is None:
        sync_service = app.sync_service if hasattr(app, 'sync_service') else None
    
    logger.info(f"最终组件状态 - db_manager: {db_manager is not None}, fund_data_manager: {fund_data_manager is not None}")
    
    # 检查必需组件是否存在
    if db_manager is None:
        logger.error("数据库管理器未初始化，无法注册dashboard路由")
        return
    
    # 注册路由
    logger.info("开始注册dashboard路由...")
    app.route('/api/dashboard/stats', methods=['GET'])(get_dashboard_stats)
    app.route('/api/dashboard/profit-trend', methods=['GET'])(get_profit_trend)
    app.route('/api/market/index', methods=['GET'])(get_market_index)
    app.route('/api/dashboard/allocation', methods=['GET'])(get_allocation)
    app.route('/api/dashboard/holding-stocks', methods=['GET'])(get_holding_stocks)
    app.route('/api/dashboard/recent-activities', methods=['GET'])(lambda: jsonify({'success': True, 'data': get_recent_activities()}))
    
    # 验证路由是否注册成功
    logger.info(f"应用路由数量: {len(app.url_map._rules)}")
    dashboard_routes = [rule.rule for rule in app.url_map._rules if 'dashboard' in rule.rule]
    logger.info(f"已注册的dashboard路由: {dashboard_routes}")
    
    logger.info("Dashboard 路由注册完成")

    # 清除缓存的端点（仅用于调试）
    @app.route('/api/cache/clear', methods=['POST'])
    def clear_dashboard_cache():
        """清除仪表盘缓存"""
        try:
            from flask import jsonify
            if _global_cache:
                _global_cache.clear()
                logger.info("仪表盘缓存已清除")
                return jsonify({'success': True, 'message': '缓存已清除'})
            return jsonify({'success': False, 'error': '缓存未初始化'})
        except Exception as e:
            logger.error(f"清除缓存失败: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
