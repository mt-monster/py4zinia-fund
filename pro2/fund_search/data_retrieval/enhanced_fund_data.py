#!/usr/bin/env python
# coding: utf-8

"""
增强版基金数据获取模块
提供从akshare获取基金实时和历史数据的功能
"""

import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnhancedFundData:
    """增强版基金数据类"""
    
    @staticmethod
    def get_fund_basic_info(fund_code: str) -> Dict:
        """
        获取基金基本信息
        
        参数：
        fund_code: 基金代码（6位数字）
        
        返回：
        dict: 基金基本信息
        """
        try:
            # 获取基金基本信息
            fund_info = ak.fund_open_fund_info_em(symbol=fund_code, indicator="基本信息")
            
            if fund_info.empty:
                # API返回空数据，但不一定是无效基金，可能是API限制或延迟
                logger.debug(f"基金 {fund_code} 基本信息API返回空，使用默认值")
                return {
                    'fund_code': fund_code,
                    'fund_name': f'基金{fund_code}',
                    'fund_type': '未知',
                    'establish_date': None,  # 返回None而不是空字符串
                    'fund_company': '未知',
                    'fund_manager': '未知',
                    'management_fee': 0.0,
                    'custody_fee': 0.0
                }
            
            # 提取基本信息
            info_dict = {}
            for _, row in fund_info.iterrows():
                info_dict[row['项目']] = row['数值']
            
            return {
                'fund_code': fund_code,
                'fund_name': info_dict.get('基金简称', f'基金{fund_code}'),
                'fund_type': info_dict.get('基金类型', '未知'),
                'establish_date': info_dict.get('成立日期', None),  # 返回None而不是空字符串
                'fund_company': info_dict.get('基金管理人', '未知'),
                'fund_manager': info_dict.get('基金经理', '未知'),
                'management_fee': float(info_dict.get('管理费率', 0.0)),
                'custody_fee': float(info_dict.get('托管费率', 0.0))
            }
        except Exception as e:
            error_msg = str(e)
            if "SyntaxError" in error_msg and "<!doctype html>" in error_msg:
                logger.debug(f"基金 {fund_code} API返回错误页面，使用默认值")
            else:
                logger.debug(f"获取基金 {fund_code} 基本信息失败: {error_msg}，使用默认值")
            return {
                'fund_code': fund_code,
                'fund_name': f'基金{fund_code}',
                'fund_type': '未知',
                'establish_date': None,  # 返回None而不是空字符串
                'fund_company': '未知',
                'fund_manager': '未知',
                'management_fee': 0.0,
                'custody_fee': 0.0
            }
    
    @staticmethod
    def get_realtime_data(fund_code: str) -> Dict:
        """
        获取基金实时数据
        
        参数：
        fund_code: 基金代码（6位数字）
        
        返回：
        dict: 基金实时数据
        """
        try:
            # 获取基金实时净值数据
            fund_nav = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            
            if fund_nav.empty:
                logger.debug(f"基金 {fund_code} 净值数据API返回空，使用默认值")
                return {
                    'fund_code': fund_code,
                    'current_nav': 0.0,
                    'previous_nav': 0.0,
                    'daily_return': 0.0,
                    'yesterday_return': 0.0,  # 新增昨日盈亏率
                    'nav_date': datetime.now().strftime('%Y-%m-%d'),
                    'estimate_nav': 0.0,
                    'estimate_return': 0.0
                }
            
            # 获取最新数据（注意：akshare返回的是按日期升序排列，最新数据在最后一行）
            latest_data = fund_nav.iloc[-1]
            
            # 获取前一日数据用于对比
            if len(fund_nav) > 1:
                previous_data = fund_nav.iloc[-2]
                previous_nav = float(previous_data.get('单位净值', 0))
                # 获取昨日盈亏率（前一日的日增长率）
                yesterday_return = float(previous_data.get('日增长率', 0))
            else:
                previous_nav = float(latest_data.get('单位净值', 0))
                yesterday_return = 0.0
            
            current_nav = float(latest_data.get('单位净值', 0))
            nav_date = str(latest_data.get('净值日期', datetime.now().strftime('%Y-%m-%d')))
            
            # 优先使用日增长率字段（已是百分比格式）
            daily_return_raw = latest_data.get('日增长率', None)
            if daily_return_raw is not None and pd.notna(daily_return_raw):
                daily_return = float(daily_return_raw)
            else:
                # 如果日增长率不可用，使用净值计算
                if previous_nav != 0:
                    daily_return = (current_nav - previous_nav) / previous_nav * 100
                else:
                    daily_return = 0.0
            
            # 确保日收益率格式正确，保留两位小数
            daily_return = round(daily_return, 2)
            yesterday_return = round(yesterday_return, 2)
            
            return {
                'fund_code': fund_code,
                'current_nav': current_nav,
                'previous_nav': previous_nav,
                'daily_return': daily_return,
                'yesterday_return': yesterday_return,  # 新增昨日盈亏率
                'nav_date': nav_date,
                'estimate_nav': float(latest_data.get('估算值', current_nav)),
                'estimate_return': float(latest_data.get('日增长率', daily_return))
            }
        except Exception as e:
            error_msg = str(e)
            if "SyntaxError" in error_msg and "<!doctype html>" in error_msg:
                logger.debug(f"基金 {fund_code} API返回错误页面，使用默认值")
            else:
                logger.debug(f"获取基金 {fund_code} 实时数据失败: {error_msg}，使用默认值")
            return {
                'fund_code': fund_code,
                'current_nav': 0.0,
                'previous_nav': 0.0,
                'daily_return': 0.0,
                'yesterday_return': 0.0,  # 新增昨日盈亏率
                'nav_date': datetime.now().strftime('%Y-%m-%d'),
                'estimate_nav': 0.0,
                'estimate_return': 0.0
            }
    
    @staticmethod
    def get_historical_data(fund_code: str, days: int = 365) -> pd.DataFrame:
        """
        获取基金历史数据
        
        参数：
        fund_code: 基金代码（6位数字）
        days: 历史数据天数（默认365天）
        
        返回：
        DataFrame: 基金历史数据
        """
        try:
            # 获取基金历史净值数据
            fund_hist = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            
            if fund_hist.empty:
                logger.debug(f"基金 {fund_code} 历史数据API返回空，使用空DataFrame")
                return pd.DataFrame()
            
            # 转换日期格式
            fund_hist['净值日期'] = pd.to_datetime(fund_hist['净值日期'])
            
            # 按日期排序
            fund_hist = fund_hist.sort_values('净值日期', ascending=True)
            
            # 过滤最近的数据
            start_date = datetime.now() - timedelta(days=days)
            fund_hist = fund_hist[fund_hist['净值日期'] >= start_date]
            
            if fund_hist.empty:
                return pd.DataFrame()
            
            # 计算日收益率
            fund_hist['daily_return'] = fund_hist['单位净值'].pct_change()
            
            # 重命名列
            fund_hist = fund_hist.rename(columns={
                '净值日期': 'date',
                '单位净值': 'nav',
                '累计净值': 'accumulated_nav',
                '日增长率': 'daily_growth_rate'
            })
            
            return fund_hist
        except Exception as e:
            error_msg = str(e)
            if "SyntaxError" in error_msg and "<!doctype html>" in error_msg:
                logger.debug(f"基金 {fund_code} API返回错误页面，使用空DataFrame")
            else:
                logger.debug(f"获取基金 {fund_code} 历史数据失败: {error_msg}，使用空DataFrame")
            return pd.DataFrame()
    
    @staticmethod
    def get_performance_metrics(fund_code: str, days: int = 365) -> Dict:
        """
        获取基金绩效指标
    
        参数：
        fund_code: 基金代码（6位数字）
        days: 历史数据天数（默认365天）
        
        返回：
        dict: 基金绩效指标
        """
        try:
            # 获取历史数据
            hist_data = EnhancedFundData.get_historical_data(fund_code, days)
            
            if hist_data.empty or len(hist_data) < 2:
                return EnhancedFundData._get_default_metrics()
            
            # 提取日收益率
            daily_returns = hist_data['daily_return'].dropna()
            
            if len(daily_returns) < 2:
                return EnhancedFundData._get_default_metrics()
            
            # 计算各种绩效指标
            return EnhancedFundData._calculate_metrics(daily_returns, hist_data)
        except Exception as e:
            logger.error(f"计算基金 {fund_code} 绩效指标失败: {str(e)}")
            return EnhancedFundData._get_default_metrics()
    
    @staticmethod
    def _calculate_metrics(daily_returns: pd.Series, hist_data: pd.DataFrame) -> Dict:
        """
        计算绩效指标
        
        参数：
        daily_returns: 日收益率序列
        hist_data: 历史数据DataFrame
        
        返回：
        dict: 绩效指标
        """
        from shared.enhanced_config import PERFORMANCE_CONFIG, INVESTMENT_STRATEGY_CONFIG
        
        # 获取配置参数
        risk_free_rate = INVESTMENT_STRATEGY_CONFIG['risk_free_rate']
        trading_days = PERFORMANCE_CONFIG['trading_days_per_year']
        var_confidence = PERFORMANCE_CONFIG['var_confidence']
        
        # 计算总收益率
        start_nav = hist_data['nav'].iloc[0]
        end_nav = hist_data['nav'].iloc[-1]
        total_return = (end_nav - start_nav) / start_nav if start_nav != 0 else 0.0
        
        # 计算年化收益率
        days = len(hist_data)
        if days > 0:
            annualized_return = (1 + total_return) ** (trading_days / days) - 1
        else:
            annualized_return = 0.0
        
        # 计算年化波动率
        volatility = daily_returns.std() * np.sqrt(trading_days)
        
        # 计算夏普比率
        sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility != 0 else 0.0
        
        # 计算最大回撤
        cumulative_returns = (1 + daily_returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min() if not drawdown.empty else 0.0
        
        # 计算卡玛比率
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
        
        # 计算索提诺比率
        negative_returns = daily_returns[daily_returns < 0]
        downside_deviation = negative_returns.std() * np.sqrt(trading_days) if len(negative_returns) > 0 else volatility
        sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation if downside_deviation != 0 else 0.0
        
        # 计算VaR (95%)
        var_95 = daily_returns.quantile(var_confidence) if not daily_returns.empty else 0.0
        
        # 计算胜率
        win_rate = (daily_returns > 0).sum() / len(daily_returns) if len(daily_returns) > 0 else 0.0
        
        # 计算盈亏比
        positive_returns = daily_returns[daily_returns > 0]
        negative_returns = daily_returns[daily_returns < 0]
        avg_positive = positive_returns.mean() if len(positive_returns) > 0 else 0.0
        avg_negative = abs(negative_returns.mean()) if len(negative_returns) > 0 else 0.0
        profit_loss_ratio = avg_positive / avg_negative if avg_negative != 0 else 0.0
        
        # 计算综合评分
        weights = PERFORMANCE_CONFIG['weights']
        composite_score = (
            weights['annualized_return'] * max(0, min(1, (annualized_return + 0.5) / 1.0)) +
            weights['sharpe_ratio'] * max(0, min(1, (sharpe_ratio + 2) / 4.0)) +
            weights['max_drawdown'] * max(0, min(1, 1 - abs(max_drawdown) / 0.5)) +
            weights['volatility'] * max(0, min(1, 1 - volatility / 0.5)) +
            weights['win_rate'] * win_rate
        )
        
        return {
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'calmar_ratio': calmar_ratio,
            'sortino_ratio': sortino_ratio,
            'var_95': var_95,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'composite_score': composite_score,
            'total_return': total_return,
            'data_days': days
        }
    
    @staticmethod
    def _get_default_metrics() -> Dict:
        """
        获取默认绩效指标
        
        返回：
        dict: 默认绩效指标
        """
        return {
            'annualized_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'volatility': 0.0,
            'calmar_ratio': 0.0,
            'sortino_ratio': 0.0,
            'var_95': 0.0,
            'win_rate': 0.0,
            'profit_loss_ratio': 0.0,
            'composite_score': 0.0,
            'total_return': 0.0,
            'data_days': 0
        }
    
    @staticmethod
    def get_batch_fund_data(fund_codes: List[str]) -> pd.DataFrame:
        """
        批量获取基金数据
        
        参数：
        fund_codes: 基金代码列表
        
        返回：
        DataFrame: 批量基金数据
        """
        results = []
        
        for fund_code in fund_codes:
            try:
                # 获取基本信息
                basic_info = EnhancedFundData.get_fund_basic_info(fund_code)
                
                # 获取实时数据
                realtime_data = EnhancedFundData.get_realtime_data(fund_code)
                
                # 获取绩效指标
                performance_metrics = EnhancedFundData.get_performance_metrics(fund_code)
                
                # 合并数据
                fund_data = {
                    'fund_code': fund_code,
                    'fund_name': basic_info['fund_name'],
                    'fund_type': basic_info['fund_type'],
                    'fund_company': basic_info['fund_company'],
                    'fund_manager': basic_info['fund_manager'],
                    'current_nav': realtime_data['current_nav'],
                    'previous_nav': realtime_data['previous_nav'],
                    'daily_return': realtime_data['daily_return'],
                    'nav_date': realtime_data['nav_date'],
                    **performance_metrics
                }
                
                results.append(fund_data)
                logger.info(f"成功获取基金 {fund_code} 的数据")
                
            except Exception as e:
                logger.error(f"获取基金 {fund_code} 数据失败: {str(e)}")
                continue
        
        return pd.DataFrame(results)


if __name__ == "__main__":
    # 测试代码
    test_codes = ['025833', '012061']
    
    # 测试单个基金数据获取
    for code in test_codes:
        print(f"\n测试基金 {code}:")
        basic_info = EnhancedFundData.get_fund_basic_info(code)
        print(f"基本信息: {basic_info}")
        
        realtime_data = EnhancedFundData.get_realtime_data(code)
        print(f"实时数据: {realtime_data}")
        
        performance_metrics = EnhancedFundData.get_performance_metrics(code)
        print(f"绩效指标: {performance_metrics}")
    
    # 测试批量数据获取
    print(f"\n测试批量数据获取:")
    batch_data = EnhancedFundData.get_batch_fund_data(test_codes)
    print(batch_data)