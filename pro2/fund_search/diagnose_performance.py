#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金相关性分析性能诊断工具
用于分析和定位性能瓶颈
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_retrieval.enhanced_database import EnhancedDatabaseManager
from shared.enhanced_config import DATABASE_CONFIG
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def diagnose_database_connection():
    """诊断数据库连接"""
    print("\n" + "=" * 70)
    print("【诊断1】数据库连接")
    print("=" * 70)
    
    try:
        start = time.perf_counter()
        db = EnhancedDatabaseManager(DATABASE_CONFIG)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"✅ 数据库连接成功，耗时: {elapsed:.2f} ms")
        return db
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return None


def diagnose_fund_basic_info(db, fund_codes):
    """诊断基金基本信息表"""
    print("\n" + "=" * 70)
    print("【诊断2】基金基本信息表 (fund_basic_info)")
    print("=" * 70)
    
    try:
        # 检查表是否存在
        from sqlalchemy import text
        with db.engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES LIKE 'fund_basic_info'"))
            if not result.fetchall():
                print("❌ fund_basic_info 表不存在")
                return False
        
        # 查询基金名称
        start = time.perf_counter()
        placeholders = ','.join(['%s'] * len(fund_codes))
        sql = f"SELECT fund_code, fund_name FROM fund_basic_info WHERE fund_code IN ({placeholders})"
        
        with db.engine.connect() as conn:
            df = pd.read_sql(sql, conn, params=tuple(fund_codes))
        
        elapsed = (time.perf_counter() - start) * 1000
        print(f"✅ 查询成功，找到 {len(df)}/{len(fund_codes)} 只基金")
        print(f"   耗时: {elapsed:.2f} ms")
        
        if len(df) < len(fund_codes):
            missing = set(fund_codes) - set(df['fund_code'].tolist())
            print(f"   缺失基金: {list(missing)[:5]}{'...' if len(missing) > 5 else ''}")
        
        return True
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return False


def diagnose_fund_analysis_results(db, fund_codes):
    """诊断基金分析结果表"""
    print("\n" + "=" * 70)
    print("【诊断3】基金分析结果表 (fund_analysis_results)")
    print("=" * 70)
    
    try:
        from sqlalchemy import text
        
        # 检查表是否存在
        with db.engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES LIKE 'fund_analysis_results'"))
            if not result.fetchall():
                print("❌ fund_analysis_results 表不存在")
                return False
        
        # 检查表结构
        with db.engine.connect() as conn:
            result = conn.execute(text("DESCRIBE fund_analysis_results"))
            columns = [row[0] for row in result.fetchall()]
        
        print(f"   表字段: {columns[:10]}...")
        
        # 查询历史数据
        start = time.perf_counter()
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=365)
        
        placeholders = ','.join(['%s'] * len(fund_codes))
        sql = f"""
        SELECT fund_code, analysis_date as date, current_estimate as nav 
        FROM fund_analysis_results 
        WHERE fund_code IN ({placeholders})
        AND analysis_date BETWEEN %s AND %s
        """
        
        with db.engine.connect() as conn:
            df = pd.read_sql(sql, conn, params=tuple(fund_codes) + (start_date, end_date))
        
        elapsed = (time.perf_counter() - start) * 1000
        
        # 统计每只基金的数据量
        fund_counts = df.groupby('fund_code').size()
        valid_funds = (fund_counts >= 10).sum()
        
        print(f"✅ 查询成功，总记录数: {len(df)}")
        print(f"   有历史数据的基金: {len(fund_counts)}/{len(fund_codes)} 只")
        print(f"   数据量充足的基金 (>=10条): {valid_funds}/{len(fund_codes)} 只")
        print(f"   耗时: {elapsed:.2f} ms")
        
        if len(fund_counts) < len(fund_codes):
            print(f"   ⚠️ 警告: {len(fund_codes) - len(fund_counts)} 只基金缺少历史数据")
            print(f"       将从akshare获取，每只约需1-3秒")
        
        return valid_funds >= 2
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def diagnose_akshare_connection():
    """诊断akshare连接"""
    print("\n" + "=" * 70)
    print("【诊断4】AKShare数据源")
    print("=" * 70)
    
    try:
        import akshare as ak
        
        print("正在测试akshare连接...")
        start = time.perf_counter()
        
        # 尝试获取一只基金的数据
        test_code = "000001"  # 华夏成长
        df = ak.fund_open_fund_info_em(symbol=test_code, indicator="单位净值走势")
        
        elapsed = (time.perf_counter() - start) * 1000
        
        if df is not None and not df.empty:
            print(f"✅ AKShare连接正常")
            print(f"   单只基金获取时间: {elapsed:.2f} ms")
            print(f"   预估14只基金时间: {elapsed * 14 / 1000:.1f} 秒 (串行)")
            print(f"   预估14只基金时间: {elapsed * 14 / 1000 / 5:.1f} 秒 (5并发)")
            return True
        else:
            print("❌ AKShare返回空数据")
            return False
            
    except Exception as e:
        print(f"❌ AKShare连接失败: {e}")
        return False


def generate_optimization_report(db, fund_codes):
    """生成优化建议报告"""
    print("\n" + "=" * 70)
    print("【优化建议报告】")
    print("=" * 70)
    
    # 检查数据库中可用的基金数量
    try:
        from sqlalchemy import text
        placeholders = ','.join(['%s'] * len(fund_codes))
        sql = f"""
        SELECT fund_code, COUNT(*) as count 
        FROM fund_analysis_results 
        WHERE fund_code IN ({placeholders})
        AND analysis_date >= DATE_SUB(NOW(), INTERVAL 1 YEAR)
        GROUP BY fund_code
        HAVING count >= 10
        """
        
        with db.engine.connect() as conn:
            df = pd.read_sql(sql, conn, params=tuple(fund_codes))
        
        available_in_db = len(df)
        
        print(f"\n当前状况:")
        print(f"  - 总基金数: {len(fund_codes)} 只")
        print(f"  - 数据库中有历史数据的: {available_in_db} 只")
        print(f"  - 需要从akshare获取的: {len(fund_codes) - available_in_db} 只")
        
        if available_in_db < len(fund_codes):
            print(f"\n⚠️  性能瓶颈分析:")
            print(f"  由于 {len(fund_codes) - available_in_db} 只基金需要从akshare获取数据，")
            print(f"  每只基金获取约需 1-3 秒，这将显著增加总耗时。")
            
            print(f"\n✅ 优化建议:")
            print(f"  1. 【推荐】预先通过数据同步脚本填充 fund_analysis_results 表")
            print(f"  2. 【临时】增加akshare并发数（当前已优化为10并发）")
            print(f"  3. 【长期】建立定时任务，每日更新基金历史数据到数据库")
        else:
            print(f"\n✅ 所有基金数据都在数据库中，性能应该良好。")
            print(f"  如果仍然缓慢，请检查:")
            print(f"  1. 数据库查询是否使用了索引")
            print(f"  2. 网络延迟是否正常")
            print(f"  3. 服务器资源是否充足")
        
    except Exception as e:
        print(f"生成报告失败: {e}")


def main():
    """主函数"""
    print("=" * 70)
    print("基金相关性分析性能诊断工具")
    print("=" * 70)
    
    # 测试基金代码
    test_fund_codes = [
        '006614', '017962', '006718', '012509', '006486',
        '010391', '003017', '004666', '006373', '018048',
        '016667', '022714', '005550', '015577'
    ]
    
    print(f"\n测试基金代码: {test_fund_codes}")
    
    # 运行诊断
    db = diagnose_database_connection()
    if not db:
        print("\n❌ 数据库连接失败，无法继续诊断")
        return 1
    
    diagnose_fund_basic_info(db, test_fund_codes)
    has_db_data = diagnose_fund_analysis_results(db, test_fund_codes)
    diagnose_akshare_connection()
    
    # 生成报告
    generate_optimization_report(db, test_fund_codes)
    
    print("\n" + "=" * 70)
    print("诊断完成")
    print("=" * 70)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
