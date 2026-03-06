#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""详细测试基金评价 API"""

import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.config_manager import config_manager
from data_access.enhanced_database import EnhancedDatabaseManager

# 获取数据库配置
db_config = config_manager.get_database_config()

# 创建数据库管理器
db_manager = EnhancedDatabaseManager({
    'host': db_config.host,
    'user': db_config.user,
    'password': db_config.password,
    'database': db_config.database,
    'port': db_config.port,
    'charset': db_config.charset
})

# 模拟 get_fund_list 函数
def get_fund_list(fund_type='all'):
    """获取基金列表 - 从用户持仓中获取真实基金"""
    try:
        if db_manager:
            user_id = 'default_user'
            
            # 直接从 user_holdings 获取用户持仓的基金信息
            holdings_sql = f"""
            SELECT 
                fund_code as code,
                fund_name as name,
                holding_shares,
                cost_price,
                current_price
            FROM user_holdings 
            WHERE user_id = '{user_id}' AND holding_shares > 0
            """
            holdings_df = db_manager.execute_query(holdings_sql)
            print(f"查询持仓SQL结果: {len(holdings_df) if not holdings_df.empty else 0} 条")
            
            if not holdings_df.empty:
                funds = []
                
                # 为每个基金构建评分数据（如果没有分析数据则使用默认值）
                for _, row in holdings_df.iterrows():
                    code = row['code']
                    name = row['name'] or code
                    
                    fund_data = {
                        'code': code,
                        'name': name,
                        'type': '混合型',
                        'return_3m': 10.0,  # 默认值
                        'return_6m': 20.0,
                        'return_1y': 40.0,
                        'sharpe_ratio': 1.0,
                        'max_drawdown': 15.0,
                        'volatility': 18.0,
                        'manager_tenure': 3.0,
                        'fund_scale': 10.0,
                        'institution_holdings': 30.0,
                        'today_return': 0.0
                    }
                    funds.append(fund_data)
                    print(f"添加基金: {code} - {name}")
                
                print(f"从用户持仓获取到 {len(funds)} 只基金")
                return funds
            
            print("用户暂无持仓基金")
            return []

        print("db_manager 未初始化")
        return []

    except Exception as e:
        print(f"获取基金列表失败: {e}")
        import traceback
        traceback.print_exc()
        return []


# 模拟 calculate_fund_scores 函数
def calculate_fund_scores(fund, weights):
    """计算基金各维度评分"""
    import numpy as np
    
    # 收益评分 (0-100)
    return_3m = fund.get('return_3m', 0)
    return_score = min(100, max(0, 50 + return_3m * 2))

    # 风险评分 (0-100) - 夏普比率越高越好，回撤越低越好
    sharpe = fund.get('sharpe_ratio', 1)
    max_dd = fund.get('max_drawdown', 20)
    risk_score = min(100, sharpe * 40 - max_dd * 1.5 + 50)

    # 经理评分 (0-100)
    tenure = fund.get('manager_tenure', 0)
    manager_score = min(100, tenure * 10)

    # 综合评分
    total_score = (
        return_score * weights.get('return', 30) / 100 +
        risk_score * weights.get('risk', 25) / 100 +
        manager_score * weights.get('manager', 20) / 100 +
        np.random.uniform(60, 90) * weights.get('scale', 15) / 100 +
        np.random.uniform(50, 80) * weights.get('institution', 10) / 100
    )

    return {
        'return_score': round(return_score, 1),
        'risk_score': round(risk_score, 1),
        'manager_score': round(manager_score, 1),
        'total_score': round(total_score, 1)
    }


# 测试流程
print("=" * 60)
print("测试基金评价流程")
print("=" * 60)

# 1. 获取基金列表
weights = {
    'return': 30,
    'risk': 25,
    'manager': 20,
    'scale': 15,
    'institution': 10
}
fund_type = 'all'
min_score = 0

print(f"\n1. 获取基金列表 (type={fund_type})...")
funds = get_fund_list(fund_type)

if not funds:
    print("未获取到基金列表，退出")
    sys.exit(1)

print(f"\n2. 评价 {len(funds)} 只基金...")
evaluated_funds = []
for fund in funds:
    print(f"\n  评价基金: {fund['code']} - {fund['name']}")
    scores = calculate_fund_scores(fund, weights)
    print(f"    评分结果: {scores}")
    
    if scores['total_score'] >= min_score:
        evaluated_fund = {
            'code': fund.get('code', ''),
            'name': fund.get('name', ''),
            'type': fund.get('type', '混合型'),
            'return_score': scores['return_score'],
            'risk_score': scores['risk_score'],
            'manager_score': scores['manager_score'],
            'total_score': scores['total_score']
        }
        evaluated_funds.append(evaluated_fund)
        print(f"    ✓ 加入结果列表")
    else:
        print(f"    ✗ 未达到最低评分 {min_score}")

print(f"\n3. 评价完成，共 {len(evaluated_funds)} 只基金满足条件")

# 按总分排序
evaluated_funds.sort(key=lambda x: x['total_score'], reverse=True)

print("\n4. 排序后的结果:")
for i, fund in enumerate(evaluated_funds[:5], 1):
    print(f"  {i}. {fund['code']} - {fund['name']}: {fund['total_score']}分")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
