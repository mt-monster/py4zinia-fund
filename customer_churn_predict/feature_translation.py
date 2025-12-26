# 特征名中英文映射字典
feature_name_mapping = {
    'stock_market_value_cv': '股票市值波动率',
    'total_guarantee_cv': '总担保金波动率',
    'liquid_assets_cv': '流动资产波动率',
    'a_stock_volume_cv': 'A股交易量波动率',
    'liquid_assets_trend': '流动资产趋势',
    'stock_market_value_trend': '股票市值趋势',
    'risk_tolerance': '风险承受能力',
    'customer_type': '客户类型',
    'guarantee_to_volume': '担保金周转率',
    'pnl_to_guarantee': '盈亏担保比',
    'last_login_max': '最后登录间隔',
    'fund_flow_total': '资金流总额',
    'fund_flow_negative_weeks': '资金净流出周数',
    'age': '年龄',
    'has_financial_product': '是否有金融产品',
    'has_visited': '是否访问过',
    'daily_pnl_trend': '日盈亏趋势',
    'login_days_trend': '登录天数趋势',
    'commission_trend': '佣金趋势',
    'commission_max': '最大佣金'
}

# 输出所有翻译结果
print("特征名中英文翻译：")
for en, zh in feature_name_mapping.items():
    print(f"{en} -> {zh}")
