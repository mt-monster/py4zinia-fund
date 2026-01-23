#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
向user_holdings表插入测试数据
"""

import sys
sys.path.append('.')

from data_retrieval.enhanced_database import EnhancedDatabaseManager
from shared.enhanced_config import DATABASE_CONFIG


def insert_holdings_data():
    """
    向user_holdings表插入测试数据
    """
    try:
        # 初始化数据库管理器
        db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        
        # 测试数据
        test_data = [
            {
                'user_id': 'default_user',
                'fund_code': '005911',
                'fund_name': '广发双擎升级混合A',
                'holding_shares': 1000.0000,
                'cost_price': 1.5000,
                'holding_amount': 1500.00,
                'buy_date': '2023-01-01'
            },
            {
                'user_id': 'default_user',
                'fund_code': '001475',
                'fund_name': '易方达国防军工混合',
                'holding_shares': 2000.0000,
                'cost_price': 1.2000,
                'holding_amount': 2400.00,
                'buy_date': '2023-02-01'
            },
            {
                'user_id': 'default_user',
                'fund_code': '110011',
                'fund_name': '易方达优质精选混合(QDII)',
                'holding_shares': 500.0000,
                'cost_price': 2.0000,
                'holding_amount': 1000.00,
                'buy_date': '2023-03-01'
            }
        ]
        
        # 插入数据
        for data in test_data:
            sql = """
            INSERT INTO user_holdings (user_id, fund_code, fund_name, holding_shares, cost_price, holding_amount, buy_date)
            VALUES (:user_id, :fund_code, :fund_name, :holding_shares, :cost_price, :holding_amount, :buy_date)
            ON DUPLICATE KEY UPDATE
                holding_shares = VALUES(holding_shares),
                cost_price = VALUES(cost_price),
                holding_amount = VALUES(holding_amount),
                buy_date = VALUES(buy_date)
            """
            result = db_manager.execute_sql(sql, data)
            print(f"成功插入/更新基金 {data['fund_code']} 的持仓数据")
        
        # 验证数据插入
        print("\n验证数据插入结果:")
        verify_sql = "SELECT fund_code, fund_name, holding_amount FROM user_holdings WHERE user_id = 'default_user'"
        verify_result = db_manager.execute_query_raw(verify_sql)
        for row in verify_result:
            print(row)
        
    except Exception as e:
        print(f"插入数据失败: {e}")


if __name__ == "__main__":
    insert_holdings_data()
