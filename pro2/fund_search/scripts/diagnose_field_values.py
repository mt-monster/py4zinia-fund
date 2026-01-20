#!/usr/bin/env python
# coding: utf-8

"""
数据库字段值诊断脚本
检查 fund_analysis_results 表中的字段值情况
"""

import sys
import os
from datetime import datetime

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.enhanced_config import DATABASE_CONFIG
from data_retrieval.enhanced_database import EnhancedDatabaseManager


def diagnose_field_values():
    """诊断字段值情况"""
    print("=" * 80)
    print("基金分析结果表字段值诊断")
    print("=" * 80)
    print()
    
    # 初始化数据库管理器
    db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
    
    # 1. 检查表结构
    print("1. 检查表结构...")
    print("-" * 80)
    check_sql = """
    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'fund_analysis_results'
    ORDER BY ORDINAL_POSITION
    """
    
    columns_df = db_manager.execute_query(check_sql)
    if not columns_df.empty:
        print(f"表 fund_analysis_results 共有 {len(columns_df)} 个字段：")
        print()
        for _, row in columns_df.iterrows():
            print(f"  - {row['COLUMN_NAME']:25s} {row['DATA_TYPE']:15s} "
                  f"{'NULL' if row['IS_NULLABLE'] == 'YES' else 'NOT NULL':10s}")
        print()
        
        # 检查是否存在 yesterday_return 字段
        if 'yesterday_return' in columns_df['COLUMN_NAME'].values:
            print("⚠️  发现冗余字段: yesterday_return")
        else:
            print("✅ 冗余字段 yesterday_return 已删除")
        print()
    
    # 2. 检查最新数据
    print("2. 检查最新分析数据...")
    print("-" * 80)
    
    # 获取最新分析日期
    date_sql = "SELECT MAX(analysis_date) as max_date FROM fund_analysis_results"
    date_df = db_manager.execute_query(date_sql)
    
    if date_df.empty or date_df.iloc[0]['max_date'] is None:
        print("❌ 表中没有数据")
        return
    
    max_date = date_df.iloc[0]['max_date']
    print(f"最新分析日期: {max_date}")
    print()
    
    # 获取最新数据的统计信息
    stats_sql = f"""
    SELECT 
        COUNT(*) as total_count,
        COUNT(CASE WHEN today_return = 0 THEN 1 END) as today_return_zero_count,
        COUNT(CASE WHEN today_return != 0 THEN 1 END) as today_return_nonzero_count,
        COUNT(CASE WHEN prev_day_return = 0 THEN 1 END) as prev_day_return_zero_count,
        COUNT(CASE WHEN prev_day_return != 0 THEN 1 END) as prev_day_return_nonzero_count,
        AVG(today_return) as avg_today_return,
        AVG(prev_day_return) as avg_prev_day_return,
        MIN(today_return) as min_today_return,
        MAX(today_return) as max_today_return,
        MIN(prev_day_return) as min_prev_day_return,
        MAX(prev_day_return) as max_prev_day_return
    FROM fund_analysis_results
    WHERE analysis_date = '{max_date}'
    """
    
    stats_df = db_manager.execute_query(stats_sql)
    
    if not stats_df.empty:
        stats = stats_df.iloc[0]
        print(f"总基金数: {stats['total_count']}")
        print()
        print("today_return 字段统计:")
        print(f"  - 值为0的记录数: {stats['today_return_zero_count']} "
              f"({stats['today_return_zero_count']/stats['total_count']*100:.1f}%)")
        print(f"  - 值非0的记录数: {stats['today_return_nonzero_count']} "
              f"({stats['today_return_nonzero_count']/stats['total_count']*100:.1f}%)")
        print(f"  - 平均值: {stats['avg_today_return']:.4f}%")
        print(f"  - 最小值: {stats['min_today_return']:.4f}%")
        print(f"  - 最大值: {stats['max_today_return']:.4f}%")
        print()
        print("prev_day_return 字段统计:")
        print(f"  - 值为0的记录数: {stats['prev_day_return_zero_count']} "
              f"({stats['prev_day_return_zero_count']/stats['total_count']*100:.1f}%)")
        print(f"  - 值非0的记录数: {stats['prev_day_return_nonzero_count']} "
              f"({stats['prev_day_return_nonzero_count']/stats['total_count']*100:.1f}%)")
        print(f"  - 平均值: {stats['avg_prev_day_return']:.4f}%")
        print(f"  - 最小值: {stats['min_prev_day_return']:.4f}%")
        print(f"  - 最大值: {stats['max_prev_day_return']:.4f}%")
        print()
    
    # 3. 显示示例数据
    print("3. 示例数据（前10条）...")
    print("-" * 80)
    
    sample_sql = f"""
    SELECT 
        fund_code, fund_name, today_return, prev_day_return, 
        status_label, operation_suggestion
    FROM fund_analysis_results
    WHERE analysis_date = '{max_date}'
    ORDER BY fund_code
    LIMIT 10
    """
    
    sample_df = db_manager.execute_query(sample_sql)
    
    if not sample_df.empty:
        print(f"{'基金代码':<10s} {'基金名称':<20s} {'今日收益率':<12s} {'昨日收益率':<12s} {'状态':<15s}")
        print("-" * 80)
        for _, row in sample_df.iterrows():
            print(f"{row['fund_code']:<10s} {row['fund_name']:<20s} "
                  f"{row['today_return']:>10.2f}% {row['prev_day_return']:>10.2f}% "
                  f"{row['status_label']:<15s}")
        print()
    
    # 4. 检查异常数据
    print("4. 检查异常数据...")
    print("-" * 80)
    
    # 检查两个字段都为0的记录
    zero_sql = f"""
    SELECT fund_code, fund_name, today_return, prev_day_return
    FROM fund_analysis_results
    WHERE analysis_date = '{max_date}'
    AND today_return = 0 AND prev_day_return = 0
    LIMIT 5
    """
    
    zero_df = db_manager.execute_query(zero_sql)
    
    if not zero_df.empty:
        print(f"⚠️  发现 {len(zero_df)} 条记录的 today_return 和 prev_day_return 都为0：")
        for _, row in zero_df.iterrows():
            print(f"  - {row['fund_code']} {row['fund_name']}")
        print()
        print("可能原因：")
        print("  1. 非交易日，基金净值未更新")
        print("  2. 数据获取接口失败")
        print("  3. 实时估算数据未返回")
        print()
    else:
        print("✅ 没有发现两个字段都为0的异常记录")
        print()
    
    # 5. 建议
    print("5. 诊断建议...")
    print("-" * 80)
    
    if stats['today_return_zero_count'] > stats['total_count'] * 0.5:
        print("⚠️  超过50%的记录 today_return 为0，建议：")
        print("  1. 检查是否为非交易日")
        print("  2. 检查数据获取接口是否正常")
        print("  3. 查看日志文件 fund_analysis.log 获取详细错误信息")
    else:
        print("✅ today_return 字段数据正常")
    
    if stats['prev_day_return_zero_count'] > stats['total_count'] * 0.5:
        print("⚠️  超过50%的记录 prev_day_return 为0，建议：")
        print("  1. 检查历史数据获取是否正常")
        print("  2. 查看日志文件 fund_analysis.log 获取详细错误信息")
    else:
        print("✅ prev_day_return 字段数据正常")
    
    print()
    print("=" * 80)
    print("诊断完成")
    print("=" * 80)


if __name__ == '__main__':
    try:
        diagnose_field_values()
    except Exception as e:
        print(f"❌ 诊断过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
