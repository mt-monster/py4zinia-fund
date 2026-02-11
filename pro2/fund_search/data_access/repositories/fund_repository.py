#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金数据 Repository
提供基金相关数据的访问接口
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd

from .base import BaseRepository


class FundRepository(BaseRepository[Dict[str, Any]]):
    """基金数据仓储"""
    
    def _get_table_name(self) -> str:
        return 'fund_basic_info'
    
    def _to_entity(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return dict(row)
    
    def get_by_code(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """根据基金代码获取基本信息"""
        try:
            query = "SELECT * FROM fund_basic_info WHERE fund_code = %s"
            df = self.db.execute_query(query, (fund_code,))
            
            if df.empty:
                return None
            
            return df.iloc[0].to_dict()
            
        except Exception as e:
            self.logger.error(f"根据代码获取基金失败: {e}")
            return None
    
    def get_by_codes(self, fund_codes: List[str]) -> pd.DataFrame:
        """根据多个基金代码获取信息"""
        try:
            placeholders = ', '.join(['%s'] * len(fund_codes))
            query = f"SELECT * FROM fund_basic_info WHERE fund_code IN ({placeholders})"
            
            return self.db.execute_query(query, tuple(fund_codes))
            
        except Exception as e:
            self.logger.error(f"批量获取基金失败: {e}")
            return pd.DataFrame()
    
    def search_by_name(self, keyword: str, limit: int = 20) -> pd.DataFrame:
        """根据名称搜索基金"""
        try:
            query = """
                SELECT * FROM fund_basic_info 
                WHERE fund_name LIKE %s OR fund_code LIKE %s
                LIMIT %s
            """
            params = (f'%{keyword}%', f'%{keyword}%', limit)
            
            return self.db.execute_query(query, params)
            
        except Exception as e:
            self.logger.error(f"搜索基金失败: {e}")
            return pd.DataFrame()
    
    def get_latest_analysis(
        self, 
        fund_code: str, 
        user_id: str = 'default_user'
    ) -> Optional[Dict[str, Any]]:
        """获取最新的分析结果"""
        try:
            query = """
                SELECT * FROM fund_analysis_results 
                WHERE fund_code = %s AND user_id = %s
                ORDER BY analysis_date DESC 
                LIMIT 1
            """
            df = self.db.execute_query(query, (fund_code, user_id))
            
            if df.empty:
                return None
            
            return df.iloc[0].to_dict()
            
        except Exception as e:
            self.logger.error(f"获取最新分析结果失败: {e}")
            return None
    
    def get_analysis_history(
        self,
        fund_code: str,
        user_id: str = 'default_user',
        days: int = 30
    ) -> pd.DataFrame:
        """获取分析历史"""
        try:
            query = """
                SELECT * FROM fund_analysis_results 
                WHERE fund_code = %s AND user_id = %s
                AND analysis_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
                ORDER BY analysis_date DESC
            """
            return self.db.execute_query(query, (fund_code, user_id, days))
            
        except Exception as e:
            self.logger.error(f"获取分析历史失败: {e}")
            return pd.DataFrame()
    
    def save_analysis_result(
        self,
        fund_code: str,
        fund_name: str,
        data: Dict[str, Any],
        user_id: str = 'default_user'
    ) -> bool:
        """保存分析结果"""
        try:
            # 构建插入数据
            insert_data = {
                'fund_code': fund_code,
                'fund_name': fund_name,
                'user_id': user_id,
                'analysis_date': datetime.now(),
                **data
            }
            
            # 使用 INSERT ... ON DUPLICATE KEY UPDATE
            columns = list(insert_data.keys())
            placeholders = ', '.join(['%s'] * len(columns))
            update_clause = ', '.join([f"{col} = VALUES({col})" for col in columns])
            
            query = f"""
                INSERT INTO fund_analysis_results ({', '.join(columns)})
                VALUES ({placeholders})
                ON DUPLICATE KEY UPDATE {update_clause}
            """
            
            self.db.execute_sql(query, tuple(insert_data.values()))
            return True
            
        except Exception as e:
            self.logger.error(f"保存分析结果失败: {e}")
            return False
    
    def get_performance_metrics(
        self,
        fund_code: str,
        user_id: str = 'default_user'
    ) -> Optional[Dict[str, Any]]:
        """获取绩效指标"""
        try:
            query = """
                SELECT * FROM fund_performance 
                WHERE fund_code = %s AND user_id = %s
                ORDER BY date DESC LIMIT 1
            """
            df = self.db.execute_query(query, (fund_code, user_id))
            
            if df.empty:
                return None
            
            return df.iloc[0].to_dict()
            
        except Exception as e:
            self.logger.error(f"获取绩效指标失败: {e}")
            return None
