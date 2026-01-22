#!/usr/bin/env python
# coding: utf-8

"""
测试截图导入全流程
验证从OCR识别到数据库保存的完整流程
"""

import sys
import os

# 添加父目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.enhanced_config import DATABASE_CONFIG
from data_retrieval.enhanced_database import EnhancedDatabaseManager
import pandas as pd
from datetime import datetime

def test_screenshot_import_flow():
    """测试截图导入全流程"""
    
    print("=" * 80)
    print("测试截图导入全流程")
    print("=" * 80)
    
    db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
    
    # 模拟OCR识别结果
    mock_ocr_results = [
        {
            'fund_code': '013048',
            'fund_name': '富国中证新能源汽车指数(LOF)C',
            'holding_amount': 276.65,
            'profit_amount': 13.45,
            'current_value': 290.10,
            'nav_value': 1.234,
            'confidence': 0.95,
            'source': 'OCR',
            'original_text': '富国中证新能源汽车指数(LOF)C 013048 276.65 13.45'
        },
        {
            'fund_code': '013277',
            'fund_name': '富国中证新能源汽车指数(LOF)A',
            'holding_amount': 274.58,
            'profit_amount': 5.20,
            'current_value': 279.78,
            'nav_value': 1.235,
            'confidence': 0.92,
            'source': 'OCR',
            'original_text': '富国中证新能源汽车指数(LOF)A 013277 274.58 5.20'
        },
        {
            'fund_code': '006106',
            'fund_name': '华宝中证科技龙头ETF联接C',
            'holding_amount': 262.57,
            'profit_amount': 4.08,
            'current_value': 266.65,
            'nav_value': 1.123,
            'confidence': 0.88,
            'source': 'OCR',
            'original_text': '华宝中证科技龙头ETF联接C 006106 262.57 4.08'
        }
    ]
    
    print("\n步骤1: 模拟OCR识别结果")
    print("-" * 80)
    for fund in mock_ocr_results:
        print(f"  基金代码: {fund['fund_code']}")
        print(f"  基金名称: {fund['fund_name']}")
        print(f"  持仓金额: ¥{fund['holding_amount']:.2f}")
        print(f"  盈亏金额: ¥{fund['profit_amount']:.2f}")
        print(f"  当前市值: ¥{fund['current_value']:.2f}")
        print(f"  净值: {fund['nav_value']:.4f}")
        print(f"  置信度: {fund['confidence']:.2%}")
        print()
    
    # 步骤2: 数据转换（计算持有份额和成本价）
    print("\n步骤2: 数据转换（计算持有份额和成本价）")
    print("-" * 80)
    
    funds_to_import = []
    for fund in mock_ocr_results:
        holding_amount = fund['holding_amount']
        current_value = fund['current_value']
        nav_value = fund['nav_value']
        
        if nav_value and nav_value > 0 and current_value > 0:
            # 持有份额 = 当前市值 / 当前净值
            holding_shares = current_value / nav_value
            # 成本价 = 持仓金额 / 持有份额
            cost_price = holding_amount / holding_shares if holding_shares > 0 else 0
            
            print(f"  {fund['fund_code']}: 使用净值计算")
            print(f"    持有份额 = {current_value:.2f} / {nav_value:.4f} = {holding_shares:.2f}")
            print(f"    成本价 = {holding_amount:.2f} / {holding_shares:.2f} = {cost_price:.4f}")
        else:
            # 简化方法
            holding_shares = holding_amount
            cost_price = 1.0
            print(f"  {fund['fund_code']}: 使用简化计算")
            print(f"    持有份额 = {holding_shares:.2f}")
            print(f"    成本价 = {cost_price:.4f}")
        
        funds_to_import.append({
            'fund_code': fund['fund_code'],
            'fund_name': fund['fund_name'],
            'holding_shares': holding_shares,
            'cost_price': cost_price,
            'buy_date': datetime.now().strftime('%Y-%m-%d'),
            'confidence': fund['confidence']
        })
        print()
    
    # 步骤3: 保存到数据库
    print("\n步骤3: 保存到数据库（user_holdings表）")
    print("-" * 80)
    
    user_id = 'test_user'
    imported = []
    failed = []
    
    for fund_info in funds_to_import:
        fund_code = fund_info['fund_code']
        fund_name = fund_info['fund_name']
        holding_shares = fund_info['holding_shares']
        cost_price = fund_info['cost_price']
        buy_date = fund_info['buy_date']
        confidence = fund_info['confidence']
        notes = f"通过截图识别导入 - 置信度: {confidence:.2%}"
        
        holding_amount = holding_shares * cost_price
        
        sql_holdings = """
        INSERT INTO user_holdings 
        (user_id, fund_code, fund_name, holding_shares, cost_price, holding_amount, buy_date, notes)
        VALUES (:user_id, :fund_code, :fund_name, :holding_shares, :cost_price, :holding_amount, :buy_date, :notes)
        ON DUPLICATE KEY UPDATE
            holding_shares = holding_shares + :add_shares,
            holding_amount = holding_amount + :add_amount,
            cost_price = (holding_amount + :add_amount) / (holding_shares + :add_shares),
            notes = CONCAT(notes, '; ', :notes),
            updated_at = NOW()
        """
        
        try:
            success = db_manager.execute_sql(sql_holdings, {
                'user_id': user_id,
                'fund_code': fund_code,
                'fund_name': fund_name,
                'holding_shares': holding_shares,
                'cost_price': cost_price,
                'holding_amount': holding_amount,
                'buy_date': buy_date,
                'notes': notes,
                'add_shares': holding_shares,
                'add_amount': holding_amount
            })
            
            if success:
                print(f"  ✅ {fund_code} 保存成功")
                imported.append(fund_code)
            else:
                print(f"  ❌ {fund_code} 保存失败")
                failed.append(fund_code)
                
        except Exception as e:
            print(f"  ❌ {fund_code} 保存失败: {e}")
            failed.append(fund_code)
    
    print(f"\n  成功导入: {len(imported)} 个基金")
    print(f"  失败: {len(failed)} 个基金")
    
    # 步骤4: 查询最新净值并计算盈亏
    print("\n步骤4: 查询最新净值并计算盈亏")
    print("-" * 80)
    
    for fund_code in imported:
        # 获取持仓信息
        sql_holding = """
        SELECT holding_shares, cost_price, holding_amount 
        FROM user_holdings 
        WHERE user_id = :user_id AND fund_code = :fund_code
        """
        holding_df = db_manager.execute_query(sql_holding, {
            'user_id': user_id,
            'fund_code': fund_code
        })
        
        if holding_df.empty:
            print(f"  ❌ {fund_code}: 未找到持仓信息")
            continue
        
        holding_shares = float(holding_df.iloc[0]['holding_shares'])
        cost_price = float(holding_df.iloc[0]['cost_price'])
        holding_amount = float(holding_df.iloc[0]['holding_amount'])
        
        # 获取最新净值
        sql_nav = """
        SELECT current_estimate, yesterday_nav 
        FROM fund_analysis_results 
        WHERE fund_code = :fund_code 
        ORDER BY analysis_date DESC 
        LIMIT 1
        """
        nav_df = db_manager.execute_query(sql_nav, {'fund_code': fund_code})
        
        if nav_df.empty:
            print(f"  ⚠️  {fund_code}: 未找到净值信息，使用成本价")
            current_nav = cost_price
            previous_nav = cost_price
        else:
            current_nav = float(nav_df.iloc[0]['current_estimate']) if pd.notna(nav_df.iloc[0]['current_estimate']) else cost_price
            previous_nav = float(nav_df.iloc[0]['yesterday_nav']) if pd.notna(nav_df.iloc[0]['yesterday_nav']) else cost_price
        
        # 计算盈亏
        current_value = holding_shares * current_nav
        previous_value = holding_shares * previous_nav
        
        holding_profit = current_value - holding_amount
        holding_profit_rate = (holding_profit / holding_amount * 100) if holding_amount > 0 else 0
        
        today_profit = current_value - previous_value
        today_profit_rate = (today_profit / previous_value * 100) if previous_value > 0 else 0
        
        print(f"\n  {fund_code}:")
        print(f"    持有份额: {holding_shares:.2f}")
        print(f"    成本价: {cost_price:.4f}")
        print(f"    持仓金额: ¥{holding_amount:.2f}")
        print(f"    当前净值: {current_nav:.4f}")
        print(f"    昨日净值: {previous_nav:.4f}")
        print(f"    当前市值: ¥{current_value:.2f}")
        print(f"    持有盈亏: ¥{holding_profit:.2f} ({holding_profit_rate:+.2f}%)")
        print(f"    当日盈亏: ¥{today_profit:.2f} ({today_profit_rate:+.2f}%)")
    
    # 步骤5: 验证数据一致性
    print("\n步骤5: 验证数据一致性")
    print("-" * 80)
    
    sql_verify = """
    SELECT 
        h.fund_code,
        h.fund_name,
        h.holding_shares,
        h.cost_price,
        h.holding_amount,
        far.current_estimate as current_nav,
        far.yesterday_nav as previous_nav
    FROM user_holdings h
    LEFT JOIN fund_analysis_results far ON h.fund_code = far.fund_code
    WHERE h.user_id = :user_id
    ORDER BY far.analysis_date DESC
    """
    
    verify_df = db_manager.execute_query(sql_verify, {'user_id': user_id})
    
    if not verify_df.empty:
        print(f"  ✅ 查询到 {len(verify_df)} 条持仓记录")
        for _, row in verify_df.iterrows():
            fund_code = row['fund_code']
            holding_shares = float(row['holding_shares']) if pd.notna(row['holding_shares']) else 0
            cost_price = float(row['cost_price']) if pd.notna(row['cost_price']) else 0
            holding_amount = float(row['holding_amount']) if pd.notna(row['holding_amount']) else 0
            
            # 验证：持仓金额 = 持有份额 × 成本价
            calculated_amount = holding_shares * cost_price
            is_consistent = abs(calculated_amount - holding_amount) < 0.01
            
            status = "✅" if is_consistent else "❌"
            print(f"  {status} {fund_code}: 持仓金额={holding_amount:.2f}, 计算值={calculated_amount:.2f}")
    else:
        print("  ❌ 未查询到持仓记录")
    
    # 清理测试数据
    print("\n步骤6: 清理测试数据")
    print("-" * 80)
    
    sql_cleanup = "DELETE FROM user_holdings WHERE user_id = :user_id"
    try:
        db_manager.execute_sql(sql_cleanup, {'user_id': user_id})
        print(f"  ✅ 已清理测试用户 {user_id} 的持仓数据")
    except Exception as e:
        print(f"  ❌ 清理失败: {e}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == '__main__':
    test_screenshot_import_flow()
