#!/usr/bin/env python
# coding: utf-8

"""添加缺失的基金数据"""

import sqlite3
import datetime

def add_missing_funds():
    """添加缺失的基金数据"""
    print("添加缺失的基金数据...")
    
    try:
        conn = sqlite3.connect('fund_analysis.db')
        cursor = conn.cursor()
        
        # 需要添加的基金数据
        missing_funds = [
            ('020422', '华夏中证港股通内地金融ETF发起式联接A', 1.2, 1.2, datetime.date.today()),
            ('016667', '景顺长城全球半导体芯片股票A(QDII-LOF)', 1.69, 1.69, datetime.date.today()),
        ]
        
        for fund_code, fund_name, today_return, prev_day_return, analysis_date in missing_funds:
            # 检查是否已存在
            cursor.execute('SELECT COUNT(*) FROM fund_analysis_results WHERE fund_code = ?', (fund_code,))
            count = cursor.fetchone()[0]
            
            if count == 0:
                # 插入新数据
                sql = """
                INSERT INTO fund_analysis_results 
                (fund_code, fund_name, today_return, prev_day_return, analysis_date, status_label, is_buy) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(sql, (
                    fund_code, fund_name, today_return, prev_day_return, analysis_date,
                    '持有', 0  # 默认状态
                ))
                print(f"已添加基金: {fund_code} - {fund_name}")
            else:
                # 更新现有数据
                sql = """
                UPDATE fund_analysis_results 
                SET fund_name = ?, today_return = ?, prev_day_return = ?, analysis_date = ?
                WHERE fund_code = ?
                """
                cursor.execute(sql, (fund_name, today_return, prev_day_return, analysis_date, fund_code))
                print(f"已更新基金: {fund_code} - {fund_name}")
        
        conn.commit()
        
        # 验证数据
        cursor.execute('SELECT fund_code, fund_name FROM fund_analysis_results WHERE fund_code IN (?, ?)', ('020422', '016667'))
        results = cursor.fetchall()
        print("\n验证结果:")
        for fund_code, fund_name in results:
            print(f"  {fund_code}: {fund_name}")
            
        conn.close()
        print("数据添加完成!")
        
    except Exception as e:
        print(f"添加数据失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_missing_funds()