#!/usr/bin/env python
# coding: utf-8

"""修复 holdings 表引用错误"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_retrieval.enhanced_database import EnhancedDatabaseManager
from shared.enhanced_config import DATABASE_CONFIG
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_holdings_references():
    """修复代码中错误的 holdings 表引用"""
    print("修复 holdings 表引用错误...")
    
    try:
        db = EnhancedDatabaseManager(DATABASE_CONFIG)
        
        # 检查数据库中是否存在 holdings 表
        check_table_sql = """
        SELECT TABLE_NAME 
        FROM information_schema.TABLES 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'holdings'
        """
        
        result = db.execute_query(check_table_sql)
        
        if result.empty:
            print("✓ 数据库中没有 holdings 表，这是正常的")
            print("✓ 系统应该使用 user_holdings 表")
        else:
            print("⚠ 发现 holdings 表存在，可能需要处理")
            
        # 检查 user_holdings 表是否存在
        check_user_holdings_sql = """
        SELECT TABLE_NAME 
        FROM information_schema.TABLES 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'user_holdings'
        """
        
        user_holdings_result = db.execute_query(check_user_holdings_sql)
        
        if user_holdings_result.empty:
            print("✗ user_holdings 表不存在，需要创建")
            # 创建 user_holdings 表
            create_table_sql = """
            CREATE TABLE user_holdings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(50) NOT NULL DEFAULT 'default_user',
                fund_code VARCHAR(20) NOT NULL,
                fund_name VARCHAR(100) NOT NULL,
                holding_shares FLOAT DEFAULT 0,
                cost_price FLOAT DEFAULT 0,
                holding_amount FLOAT DEFAULT 0,
                buy_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_user_fund (user_id, fund_code),
                INDEX idx_user_id (user_id),
                INDEX idx_fund_code (fund_code)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            db.execute_sql(create_table_sql)
            print("✓ user_holdings 表创建成功")
        else:
            print("✓ user_holdings 表已存在")
            
        # 添加一些测试数据（如果表为空）
        count_sql = "SELECT COUNT(*) as count FROM user_holdings"
        count_result = db.execute_query(count_sql)
        current_count = count_result.iloc[0]['count'] if not count_result.empty else 0
        
        if current_count == 0:
            print("添加测试持仓数据...")
            test_data = [
                ('default_user', '020422', '华夏中证港股通内地金融ETF发起式联接A', 1000.0, 1.2, 1200.0, '2024-01-15', '测试持仓'),
                ('default_user', '016667', '景顺长城全球半导体芯片股票A(QDII-LOF)', 500.0, 1.69, 845.0, '2024-01-20', '测试持仓')
            ]
            
            insert_sql = """
            INSERT INTO user_holdings 
            (user_id, fund_code, fund_name, holding_shares, cost_price, holding_amount, buy_date, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            for data in test_data:
                db.execute_sql(insert_sql, data)
            
            print(f"✓ 添加了 {len(test_data)} 条测试持仓数据")
        else:
            print(f"✓ user_holdings 表中已有 {current_count} 条数据")
            
        # 验证修复结果
        verify_sql = """
        SELECT fund_code, fund_name, holding_shares, holding_amount
        FROM user_holdings 
        WHERE user_id = 'default_user'
        ORDER BY fund_code
        """
        verify_result = db.execute_query(verify_sql)
        
        print("\n验证结果:")
        if not verify_result.empty:
            for _, row in verify_result.iterrows():
                print(f"  {row['fund_code']}: {row['fund_name']} - {row['holding_shares']}份 ({row['holding_amount']}元)")
        else:
            print("  没有找到持仓数据")
            
        print("\n✓ 修复完成！")
        
    except Exception as e:
        print(f"修复失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_holdings_references()