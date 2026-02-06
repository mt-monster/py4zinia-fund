#!/usr/bin/env python
# coding: utf-8

"""
真实数据获取器
用于获取沪深300指数和基金的真实历史净值数据
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class RealDataFetcher:
    """真实数据获取器"""
    
    @staticmethod
    def get_csi300_history(days: int = 365) -> pd.DataFrame:
        """
        获取沪深300指数历史数据
        
        参数:
            days: 获取的天数
            
        返回:
            DataFrame: 包含日期和收盘价的DataFrame
        """
        try:
            logger.info(f"正在获取沪深300指数最近{days}天的历史数据...")
            
            # 获取沪深300指数历史行情数据
            # 使用 stock_zh_index_daily_tx 接口获取腾讯数据源的指数行情
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days+30)  # 多获取一些数据以防节假日
            
            # 获取沪深300指数代码 (000300.SH)
            df = ak.stock_zh_index_daily(symbol="sh000300")
            
            if df is None or len(df) == 0:
                logger.warning("沪深300数据获取失败，使用备用方案")
                return RealDataFetcher._get_csi300_fallback(days)
            
            # 确保日期列格式正确
            df['date'] = pd.to_datetime(df['date'])
            
            # 过滤日期范围
            df = df[df['date'] >= start_date]
            df = df.sort_values('date', ascending=True).tail(days).reset_index(drop=True)
            
            # 重命名列
            df = df.rename(columns={
                'date': 'date',
                'close': 'price'
            })
            
            # 只保留需要的列
            df = df[['date', 'price']]
            
            logger.info(f"成功获取沪深300指数 {len(df)} 条历史数据")
            return df
            
        except Exception as e:
            logger.error(f"获取沪深300数据失败: {str(e)}")
            return RealDataFetcher._get_csi300_fallback(days)
    
    @staticmethod
    def _get_csi300_fallback(days: int) -> pd.DataFrame:
        """
        沪深300数据获取的备用方案
        """
        try:
            logger.info("使用备用方案获取沪深300数据...")
            
            # 使用基金指数数据作为替代
            # 获取沪深300ETF基金的历史净值作为替代
            etf_codes = ['510300', '159919']  # 沪深300ETF代码
            
            for etf_code in etf_codes:
                try:
                    df = ak.fund_etf_hist_em(symbol=etf_code, period="daily")
                    if df is not None and len(df) > 0:
                        df['date'] = pd.to_datetime(df['日期'])
                        df = df.rename(columns={'收盘': 'price'})
                        df = df.sort_values('date', ascending=True).tail(days).reset_index(drop=True)
                        df = df[['date', 'price']]
                        logger.info(f"使用ETF {etf_code} 数据作为沪深300替代")
                        return df
                except Exception as e:
                    logger.warning(f"ETF {etf_code} 数据获取失败: {str(e)}")
                    continue
            
            # 如果都失败了，返回空DataFrame，不再生成模拟数据
            logger.error("无法获取沪深300数据，返回空结果")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"备用方案也失败: {str(e)}")
            return pd.DataFrame()
    

    @staticmethod
    def get_fund_nav_history(fund_code: str, days: int = 365) -> pd.DataFrame:
        """
        获取基金历史净值数据
        
        参数:
            fund_code: 基金代码
            days: 获取的天数
            
        返回:
            DataFrame: 包含日期和净值的DataFrame
        """
        try:
            logger.info(f"正在获取基金 {fund_code} 最近{days}天的历史净值...")
            
            # 使用 fund_open_fund_info_em 获取基金净值历史
            df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            
            if df is None or len(df) == 0:
                logger.warning(f"基金 {fund_code} 净值数据获取失败")
                return pd.DataFrame()
            
            # 处理数据
            df = df.rename(columns={
                '净值日期': 'date',
                '单位净值': 'nav'
            })
            
            # 确保日期格式正确
            df['date'] = pd.to_datetime(df['date'])
            
            # 按日期排序并取最近的数据
            df = df.sort_values('date', ascending=True)
            
            # 计算目标开始日期
            target_start_date = datetime.now() - timedelta(days=days+30)
            df = df[df['date'] >= target_start_date]
            
            # 只取最近的days天
            df = df.tail(days).reset_index(drop=True)
            
            # 确保净值为数值类型
            df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
            df = df.dropna(subset=['nav'])
            
            logger.info(f"成功获取基金 {fund_code} {len(df)} 条净值数据")
            return df[['date', 'nav']]
            
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 净值数据失败: {str(e)}")
            return pd.DataFrame()
    
    @staticmethod
    def calculate_portfolio_nav(fund_codes: List[str], weights: List[float], 
                              initial_amount: float = 10000, days: int = 365) -> pd.DataFrame:
        """
        计算投资组合的累计净值
        
        参数:
            fund_codes: 基金代码列表
            weights: 对应的权重列表
            initial_amount: 初始投资金额
            days: 回测天数
            
        返回:
            DataFrame: 包含日期和组合净值的DataFrame
        """
        try:
            if len(fund_codes) != len(weights):
                raise ValueError("基金代码数量和权重数量不匹配")
            
            if abs(sum(weights) - 1.0) > 0.001:
                raise ValueError("权重之和必须等于1")
            
            # 获取所有基金的历史净值数据
            fund_data_list = []
            valid_funds = []
            
            for i, fund_code in enumerate(fund_codes):
                fund_df = RealDataFetcher.get_fund_nav_history(fund_code, days)
                if not fund_df.empty and len(fund_df) > 10:  # 至少需要10天数据
                    fund_data_list.append(fund_df)
                    valid_funds.append((fund_code, weights[i]))
                    logger.info(f"基金 {fund_code} 数据有效，权重 {weights[i]:.2f}")
                else:
                    logger.warning(f"基金 {fund_code} 数据不足或无效，跳过")
            
            if not fund_data_list:
                logger.error("没有有效的基金数据")
                return pd.DataFrame()
            
            # 找到共同的日期范围
            all_dates = set()
            for fund_df in fund_data_list:
                all_dates.update(fund_df['date'].dt.date)
            
            common_dates = sorted(list(all_dates))
            if len(common_dates) < 10:
                logger.warning("共同日期太少，使用第一个基金的数据")
                common_dates = fund_data_list[0]['date'].dt.date.tolist()
            
            # 构建组合净值数据
            portfolio_data = []
            
            for date in common_dates:
                date_portfolio_value = 0
                valid_weights_sum = 0
                
                for i, (fund_df, (fund_code, weight)) in enumerate(zip(fund_data_list, valid_funds)):
                    # 找到该日期对应的净值
                    date_mask = fund_df['date'].dt.date == date
                    if date_mask.any():
                        nav = fund_df[date_mask]['nav'].iloc[0]
                        # 计算该基金在组合中的价值
                        fund_investment = initial_amount * weight
                        fund_shares = fund_investment / fund_df['nav'].iloc[0]  # 按第一天净值计算份额
                        fund_value = fund_shares * nav
                        date_portfolio_value += fund_value
                        valid_weights_sum += weight
                
                if valid_weights_sum > 0:
                    # 归一化处理缺失数据的情况
                    normalized_portfolio_value = date_portfolio_value * (1.0 / valid_weights_sum)
                    portfolio_data.append({
                        'date': datetime.combine(date, datetime.min.time()),
                        'portfolio_nav': normalized_portfolio_value
                    })
            
            if not portfolio_data:
                logger.error("无法构建组合净值数据")
                return pd.DataFrame()
            
            result_df = pd.DataFrame(portfolio_data)
            result_df = result_df.sort_values('date').reset_index(drop=True)
            
            logger.info(f"成功计算投资组合净值，共 {len(result_df)} 个数据点")
            return result_df
            
        except Exception as e:
            logger.error(f"计算投资组合净值失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

# 全局实例
data_fetcher = RealDataFetcher()