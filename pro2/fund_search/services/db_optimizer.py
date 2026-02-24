#!/usr/bin/env python
# coding: utf-8

"""
数据库查询优化工具
提供向量化计算和批量操作能力
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProfitCalculationResult:
    """盈亏计算结果"""
    holding_amount: pd.Series
    today_profit: pd.Series
    today_profit_rate: pd.Series
    holding_profit: pd.Series
    holding_profit_rate: pd.Series
    total_profit: pd.Series
    total_profit_rate: pd.Series


class VectorizedProfitCalculator:
    """
    向量化盈亏计算器
    
    使用Pandas向量化操作替代循环计算，大幅提升性能
    """
    
    @staticmethod
    def calculate_profits(
        df: pd.DataFrame,
        shares_col: str = 'holding_shares',
        cost_col: str = 'cost_price',
        amount_col: str = 'holding_amount',
        current_nav_col: str = 'current_nav',
        previous_nav_col: str = 'previous_nav'
    ) -> ProfitCalculationResult:
        """
        向量化计算持仓盈亏
        
        Args:
            df: 包含持仓数据的DataFrame
            shares_col: 份额列名
            cost_col: 成本价列名
            amount_col: 持有金额列名
            current_nav_col: 当前净值列名
            previous_nav_col: 昨日净值列名
            
        Returns:
            ProfitCalculationResult: 盈亏计算结果
        """
        df = df.copy()
        
        has_holding = df[shares_col].notna() & (df[shares_col] > 0)
        
        df['holding_amount_calc'] = np.where(
            has_holding,
            df[amount_col].fillna(df[shares_col] * df[cost_col]),
            0.0
        )
        
        current_nav = df[current_nav_col].fillna(df[cost_col])
        previous_nav = df[previous_nav_col].fillna(df[cost_col])
        
        current_value = df[shares_col] * current_nav
        previous_value = df[shares_col] * previous_nav
        
        df['today_profit'] = np.where(
            has_holding,
            current_value - previous_value,
            0.0
        )
        
        df['today_profit_rate'] = np.where(
            has_holding & (previous_value > 0),
            (current_value - previous_value) / previous_value * 100,
            0.0
        )
        
        df['holding_profit'] = np.where(
            has_holding,
            current_value - df['holding_amount_calc'],
            0.0
        )
        
        df['holding_profit_rate'] = np.where(
            has_holding & (df['holding_amount_calc'] > 0),
            (current_value - df['holding_amount_calc']) / df['holding_amount_calc'] * 100,
            0.0
        )
        
        df['total_profit'] = df['holding_profit']
        df['total_profit_rate'] = df['holding_profit_rate']
        
        return ProfitCalculationResult(
            holding_amount=df['holding_amount_calc'].round(2),
            today_profit=df['today_profit'].round(2),
            today_profit_rate=df['today_profit_rate'].round(2),
            holding_profit=df['holding_profit'].round(2),
            holding_profit_rate=df['holding_profit_rate'].round(2),
            total_profit=df['total_profit'].round(2),
            total_profit_rate=df['total_profit_rate'].round(2)
        )
    
    @staticmethod
    def format_performance_metrics(
        df: pd.DataFrame,
        rate_cols: List[str] = ['annualized_return', 'max_drawdown', 'volatility'],
        percent_cols: List[str] = ['today_return', 'prev_day_return'],
        ratio_cols: List[str] = ['sharpe_ratio', 'sharpe_ratio_ytd', 'sharpe_ratio_1y', 
                                  'sharpe_ratio_all', 'composite_score']
    ) -> pd.DataFrame:
        """
        向量化格式化绩效指标
        
        Args:
            df: 原始DataFrame
            rate_cols: 需要乘100的列（小数转百分比）
            percent_cols: 已经是百分比的列
            ratio_cols: 比率列
            
        Returns:
            格式化后的DataFrame
        """
        df = df.copy()
        
        for col in rate_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce') * 100
                df[col] = df[col].round(2)
        
        for col in percent_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').round(2)
        
        for col in ratio_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').round(4)
        
        return df
    
    @staticmethod
    def clean_nan_values(df: pd.DataFrame) -> pd.DataFrame:
        """
        向量化清理NaN值
        
        Args:
            df: 原始DataFrame
            
        Returns:
            清理后的DataFrame
        """
        df = df.copy()
        
        for col in df.columns:
            if df[col].dtype in ['float64', 'float32']:
                mask = df[col].isna() | np.isinf(df[col])
                df.loc[mask, col] = None
        
        return df


class BatchDatabaseOperations:
    """
    批量数据库操作工具
    """
    
    @staticmethod
    def prepare_batch_insert(
        records: List[Dict[str, Any]],
        table_name: str,
        chunk_size: int = 1000
    ) -> List[Tuple[str, List[Dict]]]:
        """
        准备批量插入数据
        
        Args:
            records: 记录列表
            table_name: 表名
            chunk_size: 每批大小
            
        Returns:
            分批后的数据列表
        """
        chunks = []
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            chunks.append((table_name, chunk))
        
        return chunks
    
    @staticmethod
    def generate_upsert_sql(
        table_name: str,
        columns: List[str],
        unique_keys: List[str]
    ) -> str:
        """
        生成UPSERT SQL语句
        
        Args:
            table_name: 表名
            columns: 列名列表
            unique_keys: 唯一键列名
            
        Returns:
            SQL语句
        """
        placeholders = ', '.join([f':{col}' for col in columns])
        columns_str = ', '.join(columns)
        
        update_cols = [col for col in columns if col not in unique_keys]
        update_str = ', '.join([f'{col}=VALUES({col})' for col in update_cols])
        
        sql = f"""
        INSERT INTO {table_name} ({columns_str})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE {update_str}
        """
        
        return sql


DATABASE_INDEX_SQL = """
-- 数据库索引优化SQL
-- 执行这些SQL语句可以提升查询性能

-- 基金分析结果表索引
CREATE INDEX IF NOT EXISTS idx_fund_date_return 
ON fund_analysis_results(fund_code, analysis_date, today_return);

CREATE INDEX IF NOT EXISTS idx_analysis_date_return 
ON fund_analysis_results(analysis_date, today_return);

CREATE INDEX IF NOT EXISTS idx_composite_score 
ON fund_analysis_results(analysis_date, composite_score DESC);

-- 用户持仓表索引
CREATE INDEX IF NOT EXISTS idx_user_fund_amount 
ON user_holdings(user_id, holding_amount DESC);

-- 基金绩效表索引
CREATE INDEX IF NOT EXISTS idx_fund_perf_date 
ON fund_performance(fund_code, analysis_date DESC);

CREATE INDEX IF NOT EXISTS idx_fund_sharpe 
ON fund_performance(fund_code, sharpe_ratio DESC);
"""


def get_optimization_sql() -> str:
    """获取数据库优化SQL"""
    return DATABASE_INDEX_SQL


profit_calculator = VectorizedProfitCalculator()
batch_db_ops = BatchDatabaseOperations()
