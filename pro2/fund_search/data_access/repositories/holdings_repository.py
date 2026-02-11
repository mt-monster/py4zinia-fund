#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
持仓数据 Repository
提供用户持仓相关的数据访问
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd

from .base import BaseRepository


class HoldingsRepository(BaseRepository[Dict[str, Any]]):
    """持仓数据仓储"""
    
    def _get_table_name(self) -> str:
        return 'user_holdings'
    
    def _to_entity(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return dict(row)
    
    def get_user_holdings(
        self,
        user_id: str = 'default_user',
        fund_code: Optional[str] = None
    ) -> pd.DataFrame:
        """获取用户持仓"""
        try:
            if fund_code:
                query = """
                    SELECT * FROM user_holdings 
                    WHERE user_id = %s AND fund_code = %s
                    ORDER BY created_at DESC
                """
                params = (user_id, fund_code)
            else:
                query = """
                    SELECT * FROM user_holdings 
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                """
                params = (user_id,)
            
            return self.db.execute_query(query, params)
            
        except Exception as e:
            self.logger.error(f"获取用户持仓失败: {e}")
            return pd.DataFrame()
    
    def get_holding_summary(self, user_id: str = 'default_user') -> Dict[str, Any]:
        """获取持仓汇总"""
        try:
            query = """
                SELECT 
                    COUNT(DISTINCT fund_code) as fund_count,
                    SUM(holding_amount) as total_amount,
                    SUM(holding_shares) as total_shares
                FROM user_holdings 
                WHERE user_id = %s
            """
            df = self.db.execute_query(query, (user_id,))
            
            if df.empty:
                return {'fund_count': 0, 'total_amount': 0, 'total_shares': 0}
            
            return {
                'fund_count': int(df.iloc[0]['fund_count'] or 0),
                'total_amount': float(df.iloc[0]['total_amount'] or 0),
                'total_shares': float(df.iloc[0]['total_shares'] or 0)
            }
            
        except Exception as e:
            self.logger.error(f"获取持仓汇总失败: {e}")
            return {'fund_count': 0, 'total_amount': 0, 'total_shares': 0}
    
    def add_holding(
        self,
        fund_code: str,
        fund_name: str,
        holding_shares: float,
        cost_price: float,
        user_id: str = 'default_user'
    ) -> bool:
        """添加持仓"""
        try:
            holding_amount = holding_shares * cost_price
            
            data = {
                'user_id': user_id,
                'fund_code': fund_code,
                'fund_name': fund_name,
                'holding_shares': holding_shares,
                'cost_price': cost_price,
                'holding_amount': holding_amount,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            return self.create(data) is not None
            
        except Exception as e:
            self.logger.error(f"添加持仓失败: {e}")
            return False
    
    def update_holding(
        self,
        holding_id: int,
        updates: Dict[str, Any]
    ) -> bool:
        """更新持仓"""
        try:
            updates['updated_at'] = datetime.now()
            return self.update(holding_id, updates)
            
        except Exception as e:
            self.logger.error(f"更新持仓失败: {e}")
            return False
    
    def delete_holding(self, holding_id: int) -> bool:
        """删除持仓"""
        return self.delete(holding_id)
    
    def get_holdings_with_analysis(
        self,
        user_id: str = 'default_user'
    ) -> pd.DataFrame:
        """获取持仓及其分析数据"""
        try:
            query = """
                SELECT 
                    h.*,
                    a.today_return,
                    a.prev_day_return,
                    a.annualized_return,
                    a.max_drawdown,
                    a.sharpe_ratio
                FROM user_holdings h
                LEFT JOIN (
                    SELECT fund_code, today_return, prev_day_return,
                           annualized_return, max_drawdown, sharpe_ratio
                    FROM fund_analysis_results
                    WHERE (fund_code, analysis_date) IN (
                        SELECT fund_code, MAX(analysis_date)
                        FROM fund_analysis_results
                        WHERE user_id = %s
                        GROUP BY fund_code
                    )
                ) a ON h.fund_code = a.fund_code
                WHERE h.user_id = %s
                ORDER BY h.holding_amount DESC
            """
            return self.db.execute_query(query, (user_id, user_id))
            
        except Exception as e:
            self.logger.error(f"获取持仓分析数据失败: {e}")
            return pd.DataFrame()
