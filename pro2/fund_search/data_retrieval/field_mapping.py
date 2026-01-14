#!/usr/bin/env python
# coding: utf-8

"""
中英文字段映射表
提供数据库字段名到中文显示名称的映射
"""

# 基本字段映射
FIELD_MAPPINGS = {
    # 基本信息字段
    'fund_code': '基金代码',
    'fund_name': '基金名称',
    'analysis_date': '分析日期',
    
    # 净值相关字段
    'yesterday_nav': '昨日净值',
    'current_estimate': '今日估值',
    'daily_return': '日收益率',
    'total_return': '总收益率',
    
    # 收益率相关字段
    'today_return': '今日收益率',
    'prev_day_return': '前一日收益率',
    'annualized_return': '年化收益率',
    
    # 绩效分析字段
    'sharpe_ratio': '夏普比率',
    'max_drawdown': '最大回撤',
    'volatility': '波动率',
    'calmar_ratio': '卡玛比率',
    'sortino_ratio': '索提诺比率',
    'var_95': '95%置信度VaR',
    'win_rate': '胜率',
    'profit_loss_ratio': '盈亏比',
    'composite_score': '综合评分',
    
    # 交易建议字段
    'status_label': '状态标签',
    'is_buy': '是否买入',
    'redeem_amount': '赎回金额',
    'comparison_value': '比较值',
    'operation_suggestion': '操作建议',
    'execution_amount': '执行金额',
    'buy_multiplier': '买入倍数'
}

# 邮件专用的字段映射（更专业的命名）
EMAIL_FIELD_MAPPINGS = {
    **FIELD_MAPPINGS,
    'sharpe_ratio': '夏普比率',
    'max_drawdown': '最大回撤率',
    'volatility': '年化波动率',
    'calmar_ratio': '卡尔玛比率',
    'sortino_ratio': '索提诺比率',
    'var_95': '风险价值(VaR)',
    'win_rate': '盈利胜率',
    'profit_loss_ratio': '盈亏比率',
    'composite_score': '综合绩效评分'
}

# 用于绩效分析报告的字段顺序
PERFORMANCE_FIELDS_ORDER = [
    'fund_code',
    'fund_name',
    'yesterday_nav',
    'current_estimate',
    'today_return',
    'prev_day_return',
    'annualized_return',
    'sharpe_ratio',
    'max_drawdown',
    'volatility',
    'calmar_ratio',
    'sortino_ratio',
    'var_95',
    'win_rate',
    'profit_loss_ratio',
    'composite_score',
    'status_label',
    'operation_suggestion',
    'redeem_amount',
    'execution_amount'
]

# 用于收益率分析报告的字段顺序
RETURN_FIELDS_ORDER = [
    'fund_code',
    'fund_name',
    'yesterday_nav',
    'current_estimate',
    'today_return',
    'prev_day_return',
    'daily_return',
    'total_return',
    'status_label',
    'comparison_value',
    'operation_suggestion',
    'execution_amount'
]


def get_field_display_name(field_name: str, mapping_type: str = 'default') -> str:
    """
    获取字段的显示名称
    
    参数：
    field_name: 字段名称
    mapping_type: 映射类型 ('default', 'email', 'performance', 'return')
    
    返回：
    str: 显示名称
    """
    if mapping_type == 'email':
        return EMAIL_FIELD_MAPPINGS.get(field_name, field_name)
    elif mapping_type == 'performance':
        return FIELD_MAPPINGS.get(field_name, field_name)
    elif mapping_type == 'return':
        return FIELD_MAPPINGS.get(field_name, field_name)
    else:
        return FIELD_MAPPINGS.get(field_name, field_name)


def get_fields_order(order_type: str = 'performance') -> list:
    """
    获取字段的显示顺序
    
    参数：
    order_type: 顺序类型 ('performance', 'return')
    
    返回：
    list: 字段名称列表
    """
    if order_type == 'return':
        return RETURN_FIELDS_ORDER
    else:
        return PERFORMANCE_FIELDS_ORDER


def format_value(field_name: str, value: any) -> str:
    """
    根据字段类型格式化值
    
    参数：
    field_name: 字段名称
    value: 字段值
    
    返回：
    str: 格式化后的值
    """
    if value is None or pd.isna(value):
        return 'N/A'
    
    # 百分比类型字段
    percent_fields = [
        'today_return', 'prev_day_return', 'daily_return', 'total_return',
        'annualized_return', 'max_drawdown', 'volatility',
        'win_rate', 'profit_loss_ratio'
    ]
    
    # 小数类型字段
    decimal_fields = [
        'sharpe_ratio', 'calmar_ratio', 'sortino_ratio', 'var_95',
        'composite_score'
    ]
    
    # 货币类型字段
    currency_fields = [
        'yesterday_nav', 'current_estimate', 'redeem_amount'
    ]
    
    if field_name in percent_fields:
        return f"{value*100:.2f}%"
    elif field_name in decimal_fields:
        return f"{value:.4f}"
    elif field_name in currency_fields:
        return f"¥{value:.2f}"
    elif field_name == 'is_buy':
        return '是' if value == 1 else '否'
    elif isinstance(value, str):
        return value
    else:
        return str(value)


# 导入pandas以支持值格式化
import pandas as pd
