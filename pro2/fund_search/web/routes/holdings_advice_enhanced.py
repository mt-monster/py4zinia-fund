# -*- coding: utf-8 -*-
"""
专业投资建议增强模块
以基金经理视角生成投资建议
参考 strategy_config_optimized.yaml 策略配置
"""

import pandas as pd
import logging
import traceback
import yaml
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# 加载策略配置
_strategy_config = None

def load_strategy_config():
    """加载策略配置文件"""
    global _strategy_config
    if _strategy_config is not None:
        return _strategy_config
    
    try:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'shared', 'strategy_config_optimized.yaml'
        )
        with open(config_path, 'r', encoding='utf-8') as f:
            _strategy_config = yaml.safe_load(f)
        logger.info("策略配置加载成功")
        return _strategy_config
    except Exception as e:
        logger.error(f"加载策略配置失败: {e}")
        # 返回默认配置
        return {
            'strategies': {},
            'buy_multipliers': {
                'strong_buy': 2.5,
                'buy': 1.5,
                'weak_buy': 1.2,
                'hold': 0.0,
                'sell': 0.0,
                'weak_sell': 0.0,
                'stop_loss': 0.0
            }
        }


def enhance_investment_advice_professional(fund_codes, advice_result, initial_capital, db_manager):
    """
    增强投资建议的专业性（基金经理视角）
    
    Args:
        fund_codes: 基金代码列表
        advice_result: 原始建议结果
        initial_capital: 初始资金
        db_manager: 数据库管理器
        
    Returns:
        增强后的建议结果
    """
    try:
        enhanced_funds = []
        for fund in advice_result.get('funds', []):
            enhanced_fund = enhance_single_fund_advice(fund, initial_capital, db_manager)
            enhanced_funds.append(enhanced_fund)
        
        advice_result['funds'] = enhanced_funds
        
        # 添加组合层级建议
        advice_result['portfolio_advice'] = generate_portfolio_advice(enhanced_funds, initial_capital)
        
        return advice_result
        
    except Exception as e:
        logger.error(f"增强投资建议失败: {e}")
        traceback.print_exc()
        return advice_result


def enhance_single_fund_advice(fund, initial_capital, db_manager):
    """增强单只基金建议的专业性（参考策略配置）"""
    fund_code = fund.get('fund_code', '')
    fund_name = fund.get('fund_name', fund_code)
    advice = fund.get('advice', {})
    action = advice.get('action', 'hold')
    today_return = fund.get('today_return', 0)
    prev_day_return = fund.get('prev_day_return', 0)
    
    # 加载策略配置
    config = load_strategy_config()
    
    # 获取当前持仓信息
    holding_info = get_holding_info(fund_code, db_manager)
    current_shares = holding_info.get('shares', 0)
    current_nav = holding_info.get('nav', 0)
    current_market_value = current_shares * current_nav if current_nav > 0 else 0
    
    # 计算今日预估收益变化
    today_profit = current_market_value * today_return / 100 if today_return else 0
    prev_profit = current_market_value * prev_day_return / 100 if prev_day_return else 0
    profit_change = today_profit - prev_profit
    
    # 根据策略配置确定具体的操作建议
    strategy_info = determine_strategy_by_config(today_return, prev_day_return, config)
    strategy_label = strategy_info.get('label', '')
    strategy_desc = strategy_info.get('description', '')
    strategy_action = strategy_info.get('action', action)
    buy_multiplier = strategy_info.get('buy_multiplier', 1.0)
    redeem_amount = strategy_info.get('redeem_amount', 0.0)
    
    # 基础定投金额
    base_amount = initial_capital / 10
    
    suggested_amount = 0
    sell_ratio = 0
    operation_detail = ""
    
    # 根据策略配置生成具体操作
    if strategy_action in ['strong_buy', 'buy']:
        # 买入策略
        suggested_amount = base_amount * buy_multiplier
        operation_detail = f"<strong>{strategy_label}</strong><br>"
        operation_detail += f"建议买入 <strong>¥{int(suggested_amount):,}</strong>"
        if current_shares > 0:
            operation_detail += f"<br>当前持有 {current_shares:.2f} 份，市值 ¥{current_market_value:,.2f}"
        else:
            operation_detail += "<br>当前未持有该基金"
        buy_reasons = generate_strategy_buy_reason(fund, today_return, prev_day_return, strategy_info, config)
    elif strategy_action in ['sell', 'weak_sell']:
        # 卖出/止盈策略
        sell_ratio = redeem_amount
        if sell_ratio > 0 and current_shares > 0:
            suggested_sell_value = current_market_value * sell_ratio
            suggested_sell_shares = current_shares * sell_ratio
            operation_detail = f"<strong>{strategy_label}</strong><br>"
            operation_detail += f"建议赎回 <strong>{sell_ratio*100:.0f}%</strong> 持仓"
            operation_detail += f"<br>相当于 <strong>{suggested_sell_shares:.2f} 份</strong>，约 <strong>¥{suggested_sell_value:,.2f}</strong>"
        elif current_shares > 0:
            operation_detail = f"<strong>{strategy_label}</strong><br>建议部分止盈"
            operation_detail += f"<br>当前持有 {current_shares:.2f} 份，市值 ¥{current_market_value:,.2f}"
        else:
            operation_detail = f"<strong>{strategy_label}</strong><br>当前未持有该基金，无法执行卖出操作"
        buy_reasons = generate_strategy_sell_reason(fund, today_return, prev_day_return, strategy_info, config)
    else:
        # 持有策略
        suggested_amount = 0
        operation_detail = f"<strong>{strategy_label}</strong><br>"
        operation_detail += "建议持有观望"
        if current_shares > 0:
            operation_detail += f"<br>当前持有 {current_shares:.2f} 份，市值 ¥{current_market_value:,.2f}"
        buy_reasons = generate_strategy_hold_reason(fund, today_return, prev_day_return, strategy_info, config)
    
    # 构建专业的收益分析
    profit_analysis = {
        'today_return': today_return,
        'prev_day_return': prev_day_return,
        'today_profit': round(today_profit, 2),
        'prev_profit': round(prev_profit, 2),
        'profit_change': round(profit_change, 2),
        'profit_change_pct': round(profit_change / abs(prev_profit) * 100, 2) if prev_profit != 0 else 0,
        'current_market_value': round(current_market_value, 2),
        'current_shares': current_shares
    }
    
    # 更新建议内容
    fund['detailed_advice'] = {
        'action_name': get_professional_action_name(action),
        'operation_detail': operation_detail,
        'suggested_amount': round(suggested_amount, 2) if action in ['buy', 'strong_buy'] else 0,
        'suggested_sell_ratio': sell_ratio,
        'adjustment': buy_reasons['adjustment'],
        'valuation_comment': buy_reasons['valuation_comment'],
        'risk_assessment': buy_reasons['risk_assessment'],
        'portfolio_impact': buy_reasons['portfolio_impact'],
        'execution_plan': buy_reasons['execution_plan']
    }
    
    fund['profit_analysis'] = profit_analysis
    fund['professional_summary'] = generate_professional_summary(fund, profit_analysis, action)
    
    return fund


def get_holding_info(fund_code, db_manager):
    """获取基金持仓信息"""
    try:
        sql = """
            SELECT fund_code, fund_name, shares, cost_price, nav,
                   (shares * nav) as market_value
            FROM user_holdings 
            WHERE fund_code = :fund_code 
            LIMIT 1
        """
        df = db_manager.execute_query(sql, {'fund_code': fund_code})
        if not df.empty:
            return {
                'shares': float(df.iloc[0]['shares']) if pd.notna(df.iloc[0]['shares']) else 0,
                'cost_price': float(df.iloc[0]['cost_price']) if pd.notna(df.iloc[0]['cost_price']) else 0,
                'nav': float(df.iloc[0]['nav']) if pd.notna(df.iloc[0]['nav']) else 0,
                'market_value': float(df.iloc[0]['market_value']) if pd.notna(df.iloc[0]['market_value']) else 0
            }
    except Exception as e:
        logger.warning(f"获取持仓信息失败: {e}")
    
    return {'shares': 0, 'cost_price': 0, 'nav': 0, 'market_value': 0}


def generate_professional_buy_reason(fund, today_return, prev_day_return, profit_change):
    """生成专业的买入理由"""
    trend = "上涨" if today_return > 0 else "下跌"
    change_desc = "加速" if abs(today_return) > abs(prev_day_return) else "减速"
    
    return {
        'adjustment': f"基于当前市场环境和基金表现，建议<strong>适度增仓</strong>。今日基金{trend}{abs(today_return):.2f}%，较昨日{change_desc}。",
        'valuation_comment': generate_valuation_comment(fund, today_return),
        'risk_assessment': generate_risk_assessment(fund),
        'portfolio_impact': f"此次操作将增加组合权重，建议关注后续市场走势，如出现明显调整及时止盈或止损。",
        'execution_plan': f"建议分批建仓，避免单时点集中投入。可考虑在未来1-3个交易日内分次完成买入。"
    }


def determine_strategy_by_config(today_return, prev_day_return, config):
    """
    根据当日和昨日净值变化幅度，参考策略配置确定策略类型
    
    Args:
        today_return: 当日收益率(%)
        prev_day_return: 昨日收益率(%)
        config: 策略配置
        
    Returns:
        dict: 匹配的策略信息
    """
    strategies = config.get('strategies', {})
    
    # 遍历所有策略，检查条件是否匹配
    for strategy_name, strategy_config in strategies.items():
        conditions = strategy_config.get('conditions', [])
        for condition in conditions:
            # 检查当日收益率条件
            today_min = condition.get('today_return_min', float('-inf'))
            today_max = condition.get('today_return_max', float('inf'))
            
            # 检查昨日收益率条件
            prev_min = condition.get('prev_day_return_min', float('-inf'))
            prev_max = condition.get('prev_day_return_max', float('inf'))
            
            # 判断是否在区间内
            if (today_min <= today_return <= today_max and 
                prev_min <= prev_day_return <= prev_max):
                return {
                    'name': strategy_name,
                    'label': strategy_config.get('label', ''),
                    'description': strategy_config.get('description', ''),
                    'action': strategy_config.get('action', 'hold'),
                    'buy_multiplier': strategy_config.get('buy_multiplier', 0.0),
                    'redeem_amount': strategy_config.get('redeem_amount', 0.0)
                }
    
    # 如果没有匹配的策略，返回默认策略
    default = config.get('default_strategy', {})
    return {
        'name': 'default',
        'label': default.get('label', '⚪ 观望'),
        'description': default.get('description', '走势不明，建议观望'),
        'action': default.get('action', 'hold'),
        'buy_multiplier': default.get('buy_multiplier', 0.0),
        'redeem_amount': default.get('redeem_amount', 0.0)
    }


def generate_strategy_buy_reason(fund, today_return, prev_day_return, strategy_info, config):
    """根据策略配置生成买入理由"""
    strategy_name = strategy_info.get('name', '')
    strategy_desc = strategy_info.get('description', '')
    multiplier = strategy_info.get('buy_multiplier', 1.0)
    
    # 判断是小跌买入还是大跌抄底
    if strategy_name == 'bottom_fishing':
        adjustment = f"<strong>{strategy_desc}</strong><br>基金今日大跌{abs(today_return):.2f}%，市场恐慌情绪较重，但可能是较好的抄底机会。"
        execution = f"建议积极买入，买入倍数为基准定投的{multiplier}倍。可分2-3次建仓，避免一次性重仓。"
    else:  # gentle_fall
        adjustment = f"<strong>{strategy_desc}</strong><br>基金今日小幅下跌{abs(today_return):.2f}%，适合逢低补仓摊低成本。"
        execution = f"建议适度买入，买入倍数为基准定投的{multiplier}倍。可在今日收盘前完成操作。"
    
    return {
        'adjustment': adjustment,
        'valuation_comment': generate_valuation_comment(fund, today_return),
        'risk_assessment': generate_risk_assessment(fund),
        'portfolio_impact': f"此次买入将增加该基金在组合中的权重，建议关注后续市场走势，如继续下跌可考虑分批加仓。",
        'execution_plan': execution
    }


def generate_strategy_sell_reason(fund, today_return, prev_day_return, strategy_info, config):
    """根据策略配置生成卖出/止盈理由"""
    strategy_name = strategy_info.get('name', '')
    strategy_desc = strategy_info.get('description', '')
    redeem_amount = strategy_info.get('redeem_amount', 0.0)
    
    if strategy_name == 'take_profit':
        adjustment = f"<strong>{strategy_desc}</strong><br>基金连续上涨，今日涨幅{today_return:.2f}%，建议部分止盈锁定收益。"
        execution = f"建议赎回{redeem_amount*100:.0f}%的持仓，剩余部分继续观察。可在今日15:00前提交赎回申请。"
    elif strategy_name == 'reversal_down':
        adjustment = f"<strong>{strategy_desc}</strong><br>基金由涨转跌，今日下跌{abs(today_return):.2f}%，昨日上涨{prev_day_return:.2f}%，短期趋势可能反转。"
        execution = f"建议赎回{redeem_amount*100:.0f}%的持仓止盈，防止利润回吐。"
    else:
        adjustment = f"<strong>{strategy_desc}</strong><br>建议适度减仓，锁定部分收益。"
        execution = f"建议赎回部分持仓，剩余继续持有观察。"
    
    return {
        'adjustment': adjustment,
        'valuation_comment': generate_valuation_comment(fund, today_return),
        'risk_assessment': generate_risk_assessment(fund),
        'portfolio_impact': f"此次赎回将释放部分资金，降低组合风险暴露，可择机配置其他优质资产。",
        'execution_plan': execution
    }


def generate_strategy_hold_reason(fund, today_return, prev_day_return, strategy_info, config):
    """根据策略配置生成持有理由"""
    strategy_name = strategy_info.get('name', '')
    strategy_desc = strategy_info.get('description', '')
    
    if strategy_name == 'gentle_rise':
        adjustment = f"<strong>{strategy_desc}</strong><br>基金今日上涨{today_return:.2f}%，走势温和健康，无需频繁操作。"
    elif strategy_name == 'reversal_up':
        adjustment = f"<strong>{strategy_desc}</strong><br>基金由跌转涨，今日涨幅{today_return:.2f}%，趋势向好，建议持有观察。"
    else:
        trend = "上涨" if today_return > 0 else "下跌"
        adjustment = f"<strong>{strategy_desc}</strong><br>基金今日{trend}{abs(today_return):.2f}%，市场表现相对平稳，建议继续持有。"
    
    return {
        'adjustment': adjustment,
        'valuation_comment': generate_valuation_comment(fund, today_return),
        'risk_assessment': generate_risk_assessment(fund),
        'portfolio_impact': f"维持当前配置，不增加额外风险暴露。建议持续关注市场动态和基金表现。",
        'execution_plan': f"暂无操作必要，建议持续关注。如后续出现明显趋势变化，再考虑调整。"
    }


def generate_professional_sell_reason(fund, today_return, prev_day_return, profit_change):
    """生成专业的卖出理由（兼容旧代码）"""
    trend = "上涨" if today_return > 0 else "下跌"
    
    return {
        'adjustment': f"基于风险管理原则，建议<strong>适度减仓</strong>。今日基金{trend}{abs(today_return):.2f}%，考虑到目前市场环境和基金波动性，适时锁定部分收益。",
        'valuation_comment': generate_valuation_comment(fund, today_return),
        'risk_assessment': generate_risk_assessment(fund),
        'portfolio_impact': f"此次卖出将降低组合风险暴露，释放部分资金用于更优质资产的配置。",
        'execution_plan': f"建议在今日15:00前完成申请，以确保按今日净值确认。可考虑分批卖出以平滑成本。"
    }


def generate_professional_hold_reason(fund, today_return, prev_day_return, profit_change):
    """生成专业的持有理由"""
    trend = "上涨" if today_return > 0 else "下跌"
    
    return {
        'adjustment': f"基金今日{trend}{abs(today_return):.2f}%，市场表现相对平稳。基于当前策略匹配度和风险收益比，建议<strong>继续持有</strong>观望。",
        'valuation_comment': generate_valuation_comment(fund, today_return),
        'risk_assessment': generate_risk_assessment(fund),
        'portfolio_impact': f"维持当前配置，不增加额外风险暴露。建议持续关注市场动态和基金表现。",
        'execution_plan': f"暂无操作必要，建议持续关注。如后续出现明显趋势变化，再考虑调整。"
    }


def generate_valuation_comment(fund, today_return):
    """生成估值评论"""
    profile = fund.get('fund_profile', {})
    sharpe = profile.get('sharpe_ratio', 0)
    volatility = profile.get('volatility', 0)
    
    comments = []
    
    if today_return > 2:
        comments.append(f"今日大涨{today_return:.2f}%")
    elif today_return < -2:
        comments.append(f"今日大跌{abs(today_return):.2f}%")
    else:
        comments.append(f"今日波动较小，涨跌幅{today_return:.2f}%")
    
    if sharpe > 1.5:
        comments.append("处于高性价比区间")
    elif sharpe < 0.5:
        comments.append("风险调整中")
    
    if volatility > 0.3:
        comments.append("波动率较高")
    elif volatility < 0.15:
        comments.append("走势相对平稳")
    
    return "；".join(comments) if comments else "估值合理"


def generate_risk_assessment(fund):
    """生成风险评估"""
    profile = fund.get('fund_profile', {})
    risk_level = profile.get('risk_level', 'medium')
    volatility = profile.get('volatility', 0.2)
    max_drawdown = profile.get('max_drawdown', 0)
    
    risk_desc = {
        'low': '低风险',
        'medium': '中风险',
        'high': '高风险',
        'very_high': '极高风险'
    }
    
    assessment = f"风险等级：{risk_desc.get(risk_level, risk_level)}"
    
    if volatility > 0.25:
        assessment += f"，历史波动率较高({volatility*100:.1f}%)"
    
    if max_drawdown and max_drawdown < -0.15:
        assessment += f"，历史最大回撤达约{abs(max_drawdown)*100:.1f}%"
    
    return assessment


def get_professional_action_name(action):
    """获取专业的操作名称"""
    names = {
        'buy': '买入',
        'strong_buy': '重仓买入',
        'sell': '卖出',
        'redeem': '赎回',
        'hold': '持有观望'
    }
    return names.get(action, '持有')


def generate_professional_summary(fund, profit_analysis, action):
    """生成专业汇总"""
    fund_name = fund.get('fund_name', '')
    today_return = profit_analysis.get('today_return', 0)
    today_profit = profit_analysis.get('today_profit', 0)
    current_value = profit_analysis.get('current_market_value', 0)
    
    if current_value > 0:
        return f"【{fund_name}】今日涨跌幅{today_return:+.2f}%，预估{'盈利' if today_profit >= 0 else '亏损'}<strong>¥{abs(today_profit):,.2f}</strong>。建议{get_professional_action_name(action)}。"
    else:
        return f"【{fund_name}】今日涨跌幅{today_return:+.2f}%。建议{get_professional_action_name(action)}。"


def generate_portfolio_advice(funds, initial_capital):
    """生成组合层级建议"""
    if not funds:
        return {}
    
    total_today_profit = sum(f.get('profit_analysis', {}).get('today_profit', 0) for f in funds)
    total_prev_profit = sum(f.get('profit_analysis', {}).get('prev_profit', 0) for f in funds)
    profit_change = total_today_profit - total_prev_profit
    
    buy_count = sum(1 for f in funds if f.get('advice', {}).get('action') in ['buy', 'strong_buy'])
    sell_count = sum(1 for f in funds if f.get('advice', {}).get('action') in ['sell', 'redeem'])
    hold_count = len(funds) - buy_count - sell_count
    
    return {
        'summary_text': f"今日组合预估{'盈利' if total_today_profit >= 0 else '亏损'}<strong>¥{abs(total_today_profit):,.2f}</strong>，较昨日{'改善' if profit_change >= 0 else '恶化'}¥{abs(profit_change):,.2f}。建议买入{buy_count}只、卖出{sell_count}只、持有{hold_count}只。",
        'total_today_profit': round(total_today_profit, 2),
        'total_prev_profit': round(total_prev_profit, 2),
        'profit_change': round(profit_change, 2),
        'action_distribution': {
            'buy': buy_count,
            'sell': sell_count,
            'hold': hold_count
        },
        'manager_comment': generate_manager_comment(funds, total_today_profit, profit_change)
    }


def generate_manager_comment(funds, total_profit, profit_change):
    """生成基金经理观点的评论"""
    comments = []
    
    if total_profit > 0:
        if profit_change > 0:
            comments.append("今日组合表现良好，收益较昨日进一步改善，建议继续持有优质基金。")
        else:
            comments.append("今日组合实现正收益，但较昨日有所回落，建议关注市场走势。")
    else:
        if profit_change > 0:
            comments.append("今日组合亏损有所收窄，走势呈现好转迹象，建议保持耐心。")
        else:
            comments.append("今日组合面临调整压力，建议关注后续反弹机会，适时调整组合配置。")
    
    buy_funds = [f for f in funds if f.get('advice', {}).get('action') in ['buy', 'strong_buy']]
    if buy_funds:
        comments.append(f"关注{buy_funds[0].get('fund_name', '部分基金')}等买入机会，可适度增配。")
    
    return " ".join(comments)
