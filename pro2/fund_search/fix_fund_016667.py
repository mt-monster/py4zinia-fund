#!/usr/bin/env python
# coding: utf-8

"""修复基金016667昨日盈亏率显示为0的问题"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_retrieval.multi_source_adapter import MultiSourceDataAdapter
from data_retrieval.enhanced_database import EnhancedDatabaseManager
from shared.enhanced_config import DATABASE_CONFIG
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_fund_016667_data():
    """修复基金016667的数据问题"""
    print("=" * 60)
    print("修复基金 016667 数据问题")
    print("=" * 60)
    
    try:
        # 1. 初始化组件
        print("\n1. 初始化数据适配器和数据库管理器...")
        adapter = MultiSourceDataAdapter(timeout=10)
        db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        print("   [OK] 组件初始化完成")
        
        # 2. 清除缓存
        print("\n2. 清除基金016667的缓存数据...")
        adapter.invalidate_fund_cache('016667')
        print("   [OK] 缓存已清除")
        
        # 3. 获取最新的实时数据
        print("\n3. 获取基金016667的最新实时数据...")
        realtime_data = adapter.get_realtime_data('016667')
        
        print(f"   基金代码: {realtime_data.get('fund_code')}")
        print(f"   基金名称: {realtime_data.get('fund_name')}")
        print(f"   当前净值: {realtime_data.get('current_nav')}")
        print(f"   昨日净值: {realtime_data.get('previous_nav')}")
        print(f"   昨日盈亏率: {realtime_data.get('prev_day_return')}%")
        print(f"   今日涨跌幅: {realtime_data.get('today_return')}%")
        print(f"   数据来源: {realtime_data.get('data_source')}")
        
        # 4. 准备更新数据库的数据
        print("\n4. 准备更新数据库数据...")
        today = datetime.now().date()
        
        fund_data = {
            'fund_code': '016667',
            'fund_name': realtime_data.get('fund_name', '景顺长城全球半导体芯片股票A(QDII-LOF)'),
            'current_estimate': realtime_data.get('current_nav'),
            'yesterday_nav': realtime_data.get('previous_nav'),
            'today_return': realtime_data.get('today_return'),
            'prev_day_return': realtime_data.get('prev_day_return'),
            'analysis_date': today,
            'data_source': realtime_data.get('data_source', 'tushare_qdii'),
            # 其他必要字段设置默认值
            'annualized_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'volatility': 0.0,
            'status_label': '待分析',
            'operation_suggestion': '持有观察'
        }
        
        print("   准备更新的数据:")
        for key, value in fund_data.items():
            print(f"     {key}: {value}")
        
        # 5. 更新数据库
        print("\n5. 更新数据库中的基金数据...")
        
        # 删除旧数据
        delete_sql = """
        DELETE FROM fund_analysis_results 
        WHERE fund_code = '016667' AND analysis_date = :analysis_date
        """
        db_manager.execute_sql(delete_sql, {'analysis_date': today})
        print("   [OK] 已删除今日的旧数据")
        
        # 插入新数据
        insert_sql = """
        INSERT INTO fund_analysis_results (
            fund_code, fund_name, current_estimate, yesterday_nav,
            today_return, prev_day_return, analysis_date,
            annualized_return, sharpe_ratio, max_drawdown, volatility,
            status_label, operation_suggestion
        ) VALUES (
            :fund_code, :fund_name, :current_estimate, :yesterday_nav,
            :today_return, :prev_day_return, :analysis_date,
            :annualized_return, :sharpe_ratio, :max_drawdown, :volatility,
            :status_label, :operation_suggestion
        )
        """
        
        db_manager.execute_sql(insert_sql, fund_data)
        print("   [OK] 新数据已插入数据库")
        
        # 6. 验证更新结果
        print("\n6. 验证数据库更新结果...")
        verify_sql = """
        SELECT fund_code, fund_name, prev_day_return, today_return, 
               analysis_date
        FROM fund_analysis_results 
        WHERE fund_code = '016667' 
        ORDER BY analysis_date DESC 
        LIMIT 1
        """
        
        verify_df = db_manager.execute_query(verify_sql)
        if not verify_df.empty:
            latest = verify_df.iloc[0]
            print(f"   数据库中最新数据:")
            print(f"     分析日期: {latest['analysis_date']}")
            print(f"     昨日盈亏率: {latest['prev_day_return']}%")
            print(f"     今日涨跌幅: {latest['today_return']}%")
            
            if latest['prev_day_return'] == realtime_data.get('prev_day_return'):
                print("   ✅ 数据库更新成功，与实时数据一致")
            else:
                print("   ⚠️  数据库更新可能存在问题")
        else:
            print("   ❌ 未能验证数据库更新结果")
        
        print("\n" + "=" * 60)
        print("修复完成！")
        print("=" * 60)
        print("\n建议操作:")
        print("1. 刷新前端页面查看基金016667的昨日盈亏率是否正确显示")
        print("2. 如仍有问题，可检查浏览器控制台是否有错误信息")
        
    except Exception as e:
        logger.error(f"修复失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = fix_fund_016667_data()
    if success:
        print("\n🎉 修复成功完成！")
    else:
        print("\n❌ 修复过程中出现错误")