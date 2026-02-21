#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析数据 Repository
提供基金分析相关的数据访问
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd

from .base import BaseRepository


class AnalysisRepository(BaseRepository[Dict[str, Any]]):
    """分析数据仓储"""
    
    def _get_table_name(self) -> str:
        return 'fund_analysis_results'
    
    def _to_entity(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return dict(row)
    
    def get_latest_analysis(
        self,
        fund_code: Optional[str] = None,
        user_id: str = 'default_user'
    ) -> pd.DataFrame:
        """获取最新分析结果"""
        try:
            if fund_code:
                query = """
                    SELECT * FROM fund_analysis_results
                    WHERE fund_code = %s AND user_id = %s
                    ORDER BY analysis_date DESC
                    LIMIT 1
                """
                params = (fund_code, user_id)
            else:
                query = """
                    SELECT * FROM fund_analysis_results
                    WHERE (fund_code, analysis_date) IN (
                        SELECT fund_code, MAX(analysis_date)
                        FROM fund_analysis_results
                        WHERE user_id = %s
                        GROUP BY fund_code
                    )
                    AND user_id = %s
                """
                params = (user_id, user_id)
            
            return self.db.execute_query(query, params)
            
        except Exception as e:
            self.logger.error(f"获取最新分析结果失败: {e}")
            return pd.DataFrame()
    
    def get_analysis_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        fund_code: Optional[str] = None,
        user_id: str = 'default_user'
    ) -> pd.DataFrame:
        """获取日期范围内的分析结果"""
        try:
            if fund_code:
                query = """
                    SELECT * FROM fund_analysis_results
                    WHERE fund_code = %s AND user_id = %s
                    AND analysis_date BETWEEN %s AND %s
                    ORDER BY analysis_date DESC
                """
                params = (fund_code, user_id, start_date, end_date)
            else:
                query = """
                    SELECT * FROM fund_analysis_results
                    WHERE user_id = %s
                    AND analysis_date BETWEEN %s AND %s
                    ORDER BY analysis_date DESC
                """
                params = (user_id, start_date, end_date)
            
            return self.db.execute_query(query, params)
            
        except Exception as e:
            self.logger.error(f"获取分析历史失败: {e}")
            return pd.DataFrame()
    
    def get_top_performers(
        self,
        metric: str = 'annualized_return',
        limit: int = 10,
        user_id: str = 'default_user'
    ) -> pd.DataFrame:
        """获取表现最佳的基金"""
        try:
            query = f"""
                SELECT 
                    fund_code,
                    fund_name,
                    {metric},
                    analysis_date
                FROM fund_analysis_results
                WHERE (fund_code, analysis_date) IN (
                    SELECT fund_code, MAX(analysis_date)
                    FROM fund_analysis_results
                    WHERE user_id = %s
                    GROUP BY fund_code
                )
                AND user_id = %s
                ORDER BY {metric} DESC
                LIMIT %s
            """
            return self.db.execute_query(query, (user_id, user_id, limit))
            
        except Exception as e:
            self.logger.error(f"获取最佳表现基金失败: {e}")
            return pd.DataFrame()
    
    def get_summary_stats(self, user_id: str = 'default_user') -> Dict[str, Any]:
        """获取汇总统计"""
        try:
            query = """
                SELECT 
                    COUNT(DISTINCT fund_code) as total_funds,
                    AVG(today_return) as avg_today_return,
                    AVG(annualized_return) as avg_annualized_return,
                    AVG(max_drawdown) as avg_max_drawdown,
                    AVG(sharpe_ratio) as avg_sharpe_ratio
                FROM fund_analysis_results
                WHERE (fund_code, analysis_date) IN (
                    SELECT fund_code, MAX(analysis_date)
                    FROM fund_analysis_results
                    WHERE user_id = %s
                    GROUP BY fund_code
                )
                AND user_id = %s
            """
            df = self.db.execute_query(query, (user_id, user_id))
            
            if df.empty:
                return {}
            
            row = df.iloc[0]
            return {
                'total_funds': int(row['total_funds'] or 0),
                'avg_today_return': float(row['avg_today_return'] or 0),
                'avg_annualized_return': float(row['avg_annualized_return'] or 0),
                'avg_max_drawdown': float(row['avg_max_drawdown'] or 0),
                'avg_sharpe_ratio': float(row['avg_sharpe_ratio'] or 0)
            }
            
        except Exception as e:
            self.logger.error(f"获取汇总统计失败: {e}")
            return {}
    
    def batch_save_analysis(
        self,
        data_list: List[Dict[str, Any]],
        user_id: str = 'default_user'
    ) -> int:
        """批量保存分析结果"""
        success_count = 0
        
        for data in data_list:
            try:
                insert_data = {
                    'user_id': user_id,
                    'analysis_date': datetime.now(),
                    **data
                }
                
                if self.create(insert_data):
                    success_count += 1
                    
            except Exception as e:
                self.logger.error(f"批量保存单条失败: {e}")
                continue
        
        return success_count
