"""
从 AkShare 获取基金历史数据用于回测
"""
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def fetch_fund_history_from_akshare(fund_code: str, days: int = 90) -> pd.DataFrame:
    """
    从 AkShare 获取基金历史净值数据
    
    参数:
        fund_code: 基金代码
        days: 需要获取的天数
        
    返回:
        DataFrame: 包含历史数据的DataFrame
    """
    try:
        logger.info(f"从 AkShare 获取基金 {fund_code} 的历史数据...")
        
        # 获取基金历史净值数据
        # 使用 fund_open_fund_info_em 获取开放式基金净值
        # 参数: symbol (基金代码), indicator (指标), period (时间周期)
        df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势", period="成立来")
        
        if df is None or len(df) == 0:
            logger.warning(f"基金 {fund_code} 没有历史数据")
            return pd.DataFrame()
        
        # 重命名列
        df = df.rename(columns={
            '净值日期': 'date',
            '单位净值': 'nav'
        })
        
        # 确保日期格式正确
        df['date'] = pd.to_datetime(df['date'])
        
        # 按日期排序
        df = df.sort_values('date', ascending=True).reset_index(drop=True)
        
        # 只取最近的 days 天数据
        if len(df) > days:
            df = df.tail(days).reset_index(drop=True)
        
        # 计算收益率
        df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
        df['previous_nav'] = df['nav'].shift(1)
        
        # 计算当日收益率 (%)
        df['today_return'] = ((df['nav'] - df['previous_nav']) / df['previous_nav'] * 100).fillna(0)
        
        # 计算前一日收益率
        df['prev_day_return'] = df['today_return'].shift(1).fillna(0)
        
        # 重命名列以匹配回测引擎的期望
        result_df = pd.DataFrame({
            'analysis_date': df['date'],
            'today_return': df['today_return'],
            'prev_day_return': df['prev_day_return'],
            'current_estimate': df['nav'],
            'yesterday_nav': df['previous_nav'],
            'nav': df['nav'],  # 兼容性：同时提供nav列
            '单位净值': df['nav'],  # 兼容性：同时提供中文列名
            'status_label': '正常',  # 默认值
            'operation_suggestion': '持有',  # 默认值
            'buy_multiplier': 1.0,  # 默认值
            'redeem_amount': 0.0,  # 默认值
            'sharpe_ratio': 0.0,  # 默认值
            'max_drawdown': 0.0,  # 默认值
            'volatility': df['today_return'].std() if len(df) > 1 else 0.0,  # 计算波动率
            'annualized_return': 0.0  # 默认值
        })
        
        # 移除第一行（因为没有前一日数据）
        result_df = result_df.iloc[1:].reset_index(drop=True)
        
        logger.info(f"成功获取基金 {fund_code} 的 {len(result_df)} 条历史数据")
        return result_df
        
    except Exception as e:
        logger.error(f"从 AkShare 获取基金 {fund_code} 数据失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def fetch_fund_history_with_fallback(fund_code: str, days: int, db_manager) -> pd.DataFrame:
    """
    获取基金历史数据，优先从数据库获取，如果数据不足则从 AkShare 获取
    
    参数:
        fund_code: 基金代码
        days: 需要的天数
        db_manager: 数据库管理器
        
    返回:
        DataFrame: 历史数据
    """
    try:
        # 首先尝试从数据库获取
        sql = f"""
        SELECT analysis_date, today_return, prev_day_return,
               status_label, operation_suggestion, buy_multiplier, redeem_amount,
               current_estimate, yesterday_nav,
               sharpe_ratio, max_drawdown, volatility, annualized_return
        FROM fund_analysis_results WHERE fund_code = '{fund_code}'
        ORDER BY analysis_date DESC LIMIT {days}
        """
        
        df = db_manager.execute_query(sql)
        
        # 添加兼容字段

        # 如果数据库中有足够的数据（至少需要 days 的 50%）
        if not df.empty and len(df) >= days * 0.5:
            logger.info(f"从数据库获取到基金 {fund_code} 的 {len(df)} 条数据")
            return df.sort_values('analysis_date', ascending=True)
        
        # 数据不足，从 AkShare 获取
        logger.info(f"数据库中基金 {fund_code} 数据不足（{len(df) if not df.empty else 0} 条），从 AkShare 获取...")
        akshare_df = fetch_fund_history_from_akshare(fund_code, days)
        
        if not akshare_df.empty:
            return akshare_df
        
        # 如果 AkShare 也获取失败，返回数据库中的数据（即使不足）
        if not df.empty:
            logger.warning(f"AkShare 获取失败，使用数据库中的 {len(df)} 条数据")
            return df.sort_values('analysis_date', ascending=True)
        
        # 都失败了，返回空DataFrame
        logger.error(f"无法获取基金 {fund_code} 的历史数据")
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"获取基金 {fund_code} 历史数据失败: {str(e)}")
        return pd.DataFrame()
