#!/usr/bin/env python
# coding: utf-8

"""
单个基金数据流测试脚本
追踪从数据获取到数据库插入的完整流程
"""

import sys
import os
from datetime import datetime

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_retrieval.enhanced_fund_data import EnhancedFundData
from backtesting.enhanced_strategy import EnhancedInvestmentStrategy
from shared.enhanced_config import DATABASE_CONFIG
from data_retrieval.enhanced_database import EnhancedDatabaseManager


def test_fund_data_flow(fund_code: str, fund_name: str):
    """测试单个基金的数据流"""
    print("=" * 80)
    print(f"测试基金数据流: {fund_code} - {fund_name}")
    print("=" * 80)
    print()
    
    fund_data_manager = EnhancedFundData()
    strategy_engine = EnhancedInvestmentStrategy()
    
    # 步骤1: 获取实时数据
    print("步骤1: 获取实时数据")
    print("-" * 80)
    try:
        realtime_data = fund_data_manager.get_realtime_data(fund_code)
        print(f"✅ 实时数据获取成功:")
        print(f"  - fund_code: {realtime_data.get('fund_code')}")
        print(f"  - current_nav: {realtime_data.get('current_nav')}")
        print(f"  - previous_nav: {realtime_data.get('previous_nav')}")
        print(f"  - daily_return: {realtime_data.get('daily_return')}")
        print(f"  - yesterday_return: {realtime_data.get('yesterday_return')}")
        print(f"  - today_return: {realtime_data.get('today_return')} ⬅️ 关键字段")
        print(f"  - data_source: {realtime_data.get('data_source')}")
        print()
    except Exception as e:
        print(f"❌ 实时数据获取失败: {str(e)}")
        return
    
    # 步骤2: 获取历史数据
    print("步骤2: 获取历史数据")
    print("-" * 80)
    try:
        historical_data = fund_data_manager.get_historical_data(fund_code, days=30)
        if not historical_data.empty:
            print(f"✅ 历史数据获取成功: {len(historical_data)} 条记录")
            if 'daily_growth_rate' in historical_data.columns:
                recent = historical_data.tail(2)
                print(f"  最近2天的日增长率:")
                for _, row in recent.iterrows():
                    print(f"    {row['date']}: {row['daily_growth_rate']}")
            print()
        else:
            print(f"⚠️  历史数据为空")
            print()
    except Exception as e:
        print(f"❌ 历史数据获取失败: {str(e)}")
        print()
    
    # 步骤3: 计算收益率
    print("步骤3: 计算收益率")
    print("-" * 80)
    
    # 模拟 enhanced_main.py 中的逻辑
    today_return = realtime_data.get('today_return', 0.0)
    try:
        today_return = float(today_return)
        if abs(today_return) > 100:
            print(f"⚠️  today_return 异常: {today_return}%，使用默认值0.0%")
            today_return = 0.0
    except (ValueError, TypeError):
        print(f"⚠️  today_return 解析失败，使用默认值0.0%")
        today_return = 0.0
    
    yesterday_return = 0.0
    if 'yesterday_return' in realtime_data:
        yesterday_return = realtime_data['yesterday_return']
        try:
            yesterday_return = float(yesterday_return)
            if abs(yesterday_return) > 100:
                print(f"⚠️  yesterday_return 异常: {yesterday_return}%")
                yesterday_return = 0.0
        except (ValueError, TypeError):
            print(f"⚠️  yesterday_return 解析失败")
            yesterday_return = 0.0
    
    # 如果实时数据中的昨日收益率不可用，从历史数据获取
    if yesterday_return == 0.0 and not historical_data.empty:
        if 'daily_growth_rate' in historical_data.columns:
            recent_growth = historical_data['daily_growth_rate'].dropna().tail(1)
            if len(recent_growth) >= 1:
                try:
                    import pandas as pd
                    raw_value = float(recent_growth.iloc[-1]) if pd.notna(recent_growth.iloc[-1]) else 0.0
                    # AKShare返回的日增长率已经是百分比格式，不需要额外处理
                    yesterday_return = raw_value
                    
                    if abs(yesterday_return) > 100:
                        print(f"⚠️  历史数据中的昨日收益率异常: {yesterday_return}%")
                        yesterday_return = 0.0
                except (ValueError, TypeError):
                    print(f"⚠️  历史数据解析失败")
                    yesterday_return = 0.0
    
    today_return = round(today_return, 2)
    prev_day_return = round(yesterday_return, 2)
    
    print(f"✅ 收益率计算完成:")
    print(f"  - today_return: {today_return}% ⬅️ 将插入数据库")
    print(f"  - prev_day_return: {prev_day_return}%")
    print()
    
    # 步骤4: 策略分析
    print("步骤4: 策略分析")
    print("-" * 80)
    try:
        performance_metrics = fund_data_manager.get_performance_metrics(fund_code)
        strategy_result = strategy_engine.analyze_strategy(today_return, prev_day_return, performance_metrics)
        
        print(f"✅ 策略分析完成:")
        print(f"  - status_label: {strategy_result.get('status_label')}")
        print(f"  - action: {strategy_result.get('action')}")
        print(f"  - buy_multiplier: {strategy_result.get('buy_multiplier')}")
        print()
    except Exception as e:
        print(f"❌ 策略分析失败: {str(e)}")
        print()
    
    # 步骤5: 准备插入数据
    print("步骤5: 准备插入数据")
    print("-" * 80)
    
    fund_analysis_data = {
        'fund_code': fund_code,
        'fund_name': fund_name,
        'analysis_date': datetime.now().date(),
        'today_return': today_return,  # ⬅️ 关键字段
        'prev_day_return': prev_day_return,
        'status_label': strategy_result.get('status_label', ''),
        'operation_suggestion': strategy_result.get('operation_suggestion', ''),
        'execution_amount': strategy_result.get('execution_amount', ''),
        'yesterday_nav': realtime_data.get('previous_nav', 0.0),
        'current_estimate': realtime_data.get('estimate_nav', 0.0),
        'is_buy': 1 if strategy_result.get('action') in ['buy', 'strong_buy', 'weak_buy'] else 0,
        'redeem_amount': strategy_result.get('redeem_amount', 0.0),
        'comparison_value': strategy_result.get('comparison_value', 0.0),
        'buy_multiplier': strategy_result.get('buy_multiplier', 0.0)
    }
    
    print(f"准备插入的数据:")
    print(f"  - fund_code: {fund_analysis_data['fund_code']}")
    print(f"  - fund_name: {fund_analysis_data['fund_name']}")
    print(f"  - today_return: {fund_analysis_data['today_return']} ⬅️ 关键字段")
    print(f"  - prev_day_return: {fund_analysis_data['prev_day_return']}")
    print(f"  - status_label: {fund_analysis_data['status_label']}")
    print()
    
    # 步骤6: 插入数据库
    print("步骤6: 插入数据库")
    print("-" * 80)
    try:
        db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        success = db_manager.insert_fund_analysis_results(fund_analysis_data)
        
        if success:
            print(f"✅ 数据插入成功")
            print()
            
            # 验证插入的数据
            print("步骤7: 验证数据库中的数据")
            print("-" * 80)
            
            verify_sql = f"""
            SELECT fund_code, fund_name, today_return, prev_day_return, status_label, analysis_date
            FROM fund_analysis_results
            WHERE fund_code = '{fund_code}'
            ORDER BY analysis_date DESC
            LIMIT 1
            """
            
            verify_df = db_manager.execute_query(verify_sql)
            
            if not verify_df.empty:
                row = verify_df.iloc[0]
                print(f"✅ 数据库验证:")
                print(f"  - fund_code: {row['fund_code']}")
                print(f"  - fund_name: {row['fund_name']}")
                print(f"  - today_return: {row['today_return']} ⬅️ 数据库中的值")
                print(f"  - prev_day_return: {row['prev_day_return']}")
                print(f"  - status_label: {row['status_label']}")
                print(f"  - analysis_date: {row['analysis_date']}")
                print()
                
                # 比较
                if float(row['today_return']) == today_return:
                    print("✅ 数据一致性检查通过")
                else:
                    print(f"❌ 数据不一致!")
                    print(f"  预期: {today_return}")
                    print(f"  实际: {row['today_return']}")
            else:
                print(f"❌ 数据库中未找到记录")
        else:
            print(f"❌ 数据插入失败")
    except Exception as e:
        print(f"❌ 数据库操作失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == '__main__':
    # 测试一个普通基金
    print("\n测试1: 普通基金")
    test_fund_data_flow('001270', '英大灵活配置A')
    
    print("\n\n")
    
    # 测试一个QDII基金
    print("测试2: QDII基金")
    test_fund_data_flow('006105', '宏利印度股票(QDII)A')
