#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日投收益计算服务
用于计算定投的累计收益和收益率曲线
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DipReturnCalculator:
    """日投收益计算器"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
    
    def get_fund_nav_from_tushare(self, fund_code: str, days: int = 365) -> pd.DataFrame:
        """
        从Tushare获取基金历史净值
        
        Args:
            fund_code: 基金代码
            days: 获取最近多少天的数据
            
        Returns:
            DataFrame with columns: date, nav, daily_return
        """
        try:
            import tushare as ts
            
            pro = ts.pro_api()
            
            df = pro.fund_nav(ts_code=f'{fund_code}.OF')
            
            if df is None or df.empty:
                logger.warning(f"Tushare无法获取 {fund_code} 数据")
                return pd.DataFrame()
            
            df = df.sort_values('nav_date', ascending=True)
            
            df = df.rename(columns={
                'nav_date': 'date',
                'unit_nav': 'nav',
                'accum_nav': 'accum_nav',
                'daily_ret': 'daily_return'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            
            if days < 9999:
                start_date = datetime.now() - timedelta(days=days)
                df = df[df['date'] >= start_date]
            
            df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
            df['daily_return'] = pd.to_numeric(df['daily_return'], errors='coerce')
            
            return df[['date', 'nav', 'daily_return']].dropna()
            
        except Exception as e:
            logger.debug(f"Tushare获取 {fund_code} 数据失败: {e}")
        
        return self._get_fund_nav_from_akshare(fund_code, days)
    
    def _get_fund_nav_from_akshare(self, fund_code: str, days: int = 365) -> pd.DataFrame:
        """从Akshare获取基金历史净值（备用方案）"""
        try:
            import akshare as ak
            
            df = ak.fund_open_fund_info_em(symbol=fund_code, indicator='单位净值走势', period='最大值')
            
            if df is not None and not df.empty:
                df = df.rename(columns={
                    '净值日期': 'date',
                    '单位净值': 'nav',
                    '日增长率': 'daily_return'
                })
                
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date', ascending=True)
                
                if days < 9999:
                    start_date = datetime.now() - timedelta(days=days)
                    df = df[df['date'] >= start_date]
                
                df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
                df['daily_return'] = pd.to_numeric(df['daily_return'], errors='coerce')
                
                return df[['date', 'nav', 'daily_return']].dropna()
                
        except Exception as e:
            logger.warning(f"Akshare获取 {fund_code} 数据失败: {e}")
        
        return pd.DataFrame()
    
    def calculate_daily_returns(self, fund_code: str, start_date: str = None, 
                               end_date: str = None) -> pd.DataFrame:
        """
        计算每日收益数据（用于收益率曲线）
        
        Returns:
            DataFrame with columns:
            - date: 日期
            - nav: 净值
            - shares: 持有份额
            - market_value: 市值
            - total_cost: 累计投入
            - total_return: 累计收益
            - return_rate: 收益率
        """
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)
        
        nav_data = self.get_fund_nav_from_tushare(fund_code, days=400)
        
        if nav_data.empty:
            logger.warning(f"无法获取 {fund_code} 的净值数据")
            return pd.DataFrame()
        
        transactions = self._get_transactions_from_db(fund_code)
        
        if transactions.empty:
            logger.warning(f"没有 {fund_code} 的交易记录")
            return self._calculate_simulated_returns(fund_code, nav_data, start_date, end_date)
        
        return self._calculate_real_returns(nav_data, transactions, start_date, end_date)
    
    def _get_transactions_from_db(self, fund_code: str, user_id: str = 'default_user') -> pd.DataFrame:
        """从数据库获取交易记录"""
        if self.db_manager is None:
            return pd.DataFrame()
        
        try:
            sql = """
                SELECT trade_date, trade_type, amount, nav, shares, total_shares, total_cost, avg_cost
                FROM dip_transactions
                WHERE user_id = %s AND fund_code = %s
                ORDER BY trade_date ASC
            """
            df = self.db_manager.execute_query(sql, (user_id, fund_code))
            if df is not None and not df.empty:
                df['trade_date'] = pd.to_datetime(df['trade_date'])
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.warning(f"获取交易记录失败: {e}")
            return pd.DataFrame()
    
    def _calculate_real_returns(self, nav_data: pd.DataFrame, transactions: pd.DataFrame,
                                 start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """基于真实交易记录计算收益"""
        
        nav_data = nav_data[(nav_data['date'] >= start_date) & (nav_data['date'] <= end_date)]
        
        if nav_data.empty:
            return pd.DataFrame()
        
        results = []
        total_shares = 0
        total_cost = 0
        
        nav_dict = dict(zip(nav_data['date'].dt.date, nav_data['nav']))
        
        dates = sorted(nav_dict.keys())
        
        for date in dates:
            nav = nav_dict[date]
            
            day_transactions = transactions[transactions['trade_date'].dt.date == date]
            
            if not day_transactions.empty:
                for _, trade in day_transactions.iterrows():
                    if trade['trade_type'] == 'buy':
                        total_shares += float(trade['shares'])
                        total_cost += float(trade['amount'])
            
            market_value = total_shares * nav
            total_return = market_value - total_cost
            return_rate = total_return / total_cost if total_cost > 0 else 0
            
            results.append({
                'date': date,
                'nav': nav,
                'shares': total_shares,
                'market_value': market_value,
                'total_cost': total_cost,
                'total_return': total_return,
                'return_rate': return_rate
            })
        
        return pd.DataFrame(results)
    
    def _calculate_simulated_returns(self, fund_code: str, nav_data: pd.DataFrame,
                                     start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        模拟定投收益（假设每日定投）
        用于没有交易记录的情况
        """
        
        nav_data = nav_data[(nav_data['date'] >= start_date) & (nav_data['date'] <= end_date)]
        
        if nav_data.empty:
            return pd.DataFrame()
        
        daily_invest = 100
        
        results = []
        total_shares = 0
        total_cost = 0
        
        for _, row in nav_data.iterrows():
            nav = row['nav']
            date = row['date']
            
            shares_bought = daily_invest / nav
            total_shares += shares_bought
            total_cost += daily_invest
            
            market_value = total_shares * nav
            total_return = market_value - total_cost
            return_rate = total_return / total_cost if total_cost > 0 else 0
            
            results.append({
                'date': date.date() if hasattr(date, 'date') else date,
                'nav': nav,
                'shares': total_shares,
                'market_value': market_value,
                'total_cost': total_cost,
                'total_return': total_return,
                'return_rate': return_rate
            })
        
        return pd.DataFrame(results)
    
    def get_portfolio_returns(self, fund_codes: List[str], weights: List[float] = None,
                             start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        计算组合收益率（多只基金）
        
        Args:
            fund_codes: 基金代码列表
            weights: 权重列表，如果为None则平均分配
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame: 组合每日收益数据
        """
        if weights is None:
            weights = [1.0 / len(fund_codes)] * len(fund_codes)
        
        if len(fund_codes) != len(weights):
            logger.error("基金数量与权重数量不匹配")
            return pd.DataFrame()
        
        all_dates = set()
        fund_returns = {}
        
        for code in fund_codes:
            df = self.calculate_daily_returns(code, start_date, end_date)
            if not df.empty:
                fund_returns[code] = df
                all_dates.update(df['date'].tolist())
        
        if not fund_returns:
            return pd.DataFrame()
        
        all_dates = sorted(all_dates)
        
        results = []
        for date in all_dates:
            total_market_value = 0
            total_cost = 0
            
            for code, weight in zip(fund_codes, weights):
                if code in fund_returns:
                    fund_df = fund_returns[code]
                    day_data = fund_df[fund_df['date'] == date]
                    
                    if not day_data.empty:
                        total_market_value += day_data.iloc[0]['market_value'] * weight
                        total_cost += day_data.iloc[0]['total_cost'] * weight
            
            total_return = total_market_value - total_cost
            return_rate = total_return / total_cost if total_cost > 0 else 0
            
            results.append({
                'date': date,
                'market_value': total_market_value,
                'total_cost': total_cost,
                'total_return': total_return,
                'return_rate': return_rate
            })
        
        return pd.DataFrame(results)
    
    def get_return_summary(self, fund_code: str, start_date: str = None) -> Dict[str, Any]:
        """
        获取收益汇总信息
        
        Returns:
            Dict: 包含各项收益指标
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        
        df = self.calculate_daily_returns(fund_code, start_date)
        
        if df.empty:
            return {
                'fund_code': fund_code,
                'success': False,
                'error': '无法获取数据'
            }
        
        latest = df.iloc[-1]
        
        holding_days = (df['date'].iloc[-1] - df['date'].iloc[0]).days
        
        annualized_return = None
        if holding_days > 0 and latest['total_cost'] > 0:
            total_return_rate = latest['return_rate']
            annualized_return = (1 + total_return_rate) ** (365 / holding_days) - 1
        
        return {
            'fund_code': fund_code,
            'success': True,
            'current_nav': float(latest['nav']),
            'total_shares': float(latest['shares']),
            'total_cost': float(latest['total_cost']),
            'market_value': float(latest['market_value']),
            'total_return': float(latest['total_return']),
            'return_rate': float(latest['return_rate']),
            'annualized_return': float(annualized_return) if annualized_return else None,
            'holding_days': holding_days,
            'start_date': str(df['date'].iloc[0].date()),
            'end_date': str(df['date'].iloc[-1].date())
        }


_dip_calculator = None


def get_dip_calculator(db_manager=None) -> DipReturnCalculator:
    """获取日投收益计算器单例"""
    global _dip_calculator
    if _dip_calculator is None:
        _dip_calculator = DipReturnCalculator(db_manager)
    return _dip_calculator
