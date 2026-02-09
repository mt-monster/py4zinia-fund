#!/usr/bin/env python
# coding: utf-8
"""
MultiSourceFundData 适配器
使 MultiSourceFundData 兼容 EnhancedFundData 的接口
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from .multi_source_fund_data import MultiSourceFundData

logger = logging.getLogger(__name__)


class MultiSourceDataAdapter(MultiSourceFundData):
    """
    MultiSourceFundData 适配器类
    兼容 EnhancedFundData 的接口方法
    """
    
    def __init__(self, tushare_token: Optional[str] = None, timeout: int = 10):
        """
        初始化适配器
        
        Args:
            tushare_token: Tushare API token，如果不提供则从配置中读取
            timeout: 请求超时时间(秒)
        """
        # 如果没有提供token，则从配置中获取
        if tushare_token is None:
            try:
                from shared.enhanced_config import DATA_SOURCE_CONFIG
                tushare_token = DATA_SOURCE_CONFIG.get('tushare', {}).get('token')
                logger.info(f"从配置文件获取Tushare token: {tushare_token[:10]}...")
            except ImportError:
                logger.warning("无法导入配置文件，使用默认Tushare token")
                tushare_token = '5ff19facae0e5b26a407d491d33707a9884a39a714a0d76b6495725b'
        
        super().__init__(tushare_token, timeout)
        logger.info("MultiSourceDataAdapter 初始化完成，Tushare优先级已启用")
    
    def get_realtime_data(self, fund_code: str, fund_name: str = None) -> Dict:
        """
        获取基金实时数据（兼容 EnhancedFundData 接口）
        
        Args:
            fund_code: 基金代码
            fund_name: 基金名称（可选）
            
        Returns:
            dict: 基金实时数据
        """
        try:
            # 判断是否为QDII基金
            is_qdii = self.is_qdii_fund(fund_code, fund_name)
            
            if is_qdii:
                # QDII基金使用专门方法
                qdii_data = self.get_qdii_fund_data(fund_code)
                if qdii_data:
                    return {
                        'fund_code': fund_code,
                        'fund_name': fund_name or f'基金{fund_code}',
                        'current_nav': qdii_data['current_nav'],
                        'previous_nav': qdii_data['previous_nav'],
                        'daily_return': qdii_data['daily_return'],
                        'today_return': qdii_data['daily_return'],
                        'yesterday_return': 0.0,  # QDII基金T+2更新，昨日数据需要特殊处理
                        'nav_date': qdii_data['nav_date'],
                        'data_source': f"tushare_qdii_{qdii_data['data_source']}",
                        'estimate_nav': qdii_data['current_nav'],
                        'estimate_return': qdii_data['daily_return']
                    }
            
            # 普通基金使用最新净值数据
            latest_nav = self.get_fund_latest_nav(fund_code)
            if latest_nav:
                # 获取昨日收益率：从历史数据中获取前一天的日增长率
                yesterday_return = self._get_yesterday_return(fund_code, latest_nav.get('date'))
                
                # 获取实时估值数据并计算今日收益率
                estimate_data = self._get_realtime_estimate(fund_code)
                if estimate_data and estimate_data.get('estimate_nav', 0) > 0:
                    # 有实时估值：today_return = (实时估值 - 昨日净值) / 昨日净值 * 100
                    estimate_nav = estimate_data['estimate_nav']
                    yesterday_nav = estimate_data.get('yesterday_nav', latest_nav['nav'])
                    if yesterday_nav > 0:
                        today_return = (estimate_nav - yesterday_nav) / yesterday_nav * 100
                        today_return = round(today_return, 2)
                    else:
                        today_return = latest_nav['daily_return']
                else:
                    # 无实时估值：使用历史数据中的日增长率
                    today_return = latest_nav['daily_return']
                    estimate_nav = latest_nav['nav']
                
                # 使用新浪实时数据中的昨日净值作为 previous_nav
                previous_nav = estimate_data.get('yesterday_nav', latest_nav['nav']) if estimate_data else latest_nav.get('previous_nav', latest_nav['nav'])
                
                return {
                    'fund_code': fund_code,
                    'fund_name': fund_name or f'基金{fund_code}',
                    'current_nav': latest_nav['nav'],
                    'previous_nav': previous_nav,
                    'daily_return': latest_nav['daily_return'],
                    'today_return': today_return,
                    'yesterday_return': yesterday_return,
                    'nav_date': latest_nav['date'],
                    'data_source': f"tushare_{latest_nav['source']}",
                    'estimate_nav': estimate_nav,
                    'estimate_return': today_return
                }
            
            # 降级到默认值
            return {
                'fund_code': fund_code,
                'fund_name': fund_name or f'基金{fund_code}',
                'current_nav': 0.0,
                'previous_nav': 0.0,
                'daily_return': 0.0,
                'today_return': 0.0,
                'yesterday_return': 0.0,
                'nav_date': datetime.now().strftime('%Y-%m-%d'),
                'data_source': 'tushare_failed',
                'estimate_nav': 0.0,
                'estimate_return': 0.0
            }
            
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 实时数据失败: {e}")
            return {
                'fund_code': fund_code,
                'fund_name': fund_name or f'基金{fund_code}',
                'current_nav': 0.0,
                'previous_nav': 0.0,
                'daily_return': 0.0,
                'today_return': 0.0,
                'yesterday_return': 0.0,
                'nav_date': datetime.now().strftime('%Y-%m-%d'),
                'data_source': 'tushare_error',
                'estimate_nav': 0.0,
                'estimate_return': 0.0
            }
    
    def _get_yesterday_return(self, fund_code: str, latest_date: str = None) -> float:
        """
        获取昨日收益率（最新净值相对于前一天净值的变化率）
        
        计算公式: (nav_latest - nav_yesterday) / nav_yesterday * 100
        
        Args:
            fund_code: 基金代码
            latest_date: 最新净值日期（可选）
            
        Returns:
            float: 昨日收益率（百分比），失败返回0.0
        """
        try:
            # 获取最近几天的历史数据
            df = self.get_fund_nav_history(fund_code, source='auto')
            
            if df is None or df.empty or len(df) < 2:
                return 0.0
            
            # 确保数据按日期倒序排列（最新在前）
            if 'date' in df.columns:
                df = df.sort_values('date', ascending=False)
            
            # 获取最新净值和前一天净值
            latest_nav = float(df.iloc[0]['nav'])
            yesterday_nav = float(df.iloc[1]['nav'])
            
            # 计算收益率: (最新 - 昨日) / 昨日 * 100
            if yesterday_nav > 0:
                yesterday_return = (latest_nav - yesterday_nav) / yesterday_nav * 100
                return round(yesterday_return, 2)
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"获取基金 {fund_code} 昨日收益率失败: {e}")
            return 0.0
    
    def _get_realtime_estimate(self, fund_code: str) -> Optional[Dict]:
        """
        获取基金实时估值数据
        
        尝试从多个数据源获取实时估值（按优先级）：
        1. 天天基金网（最实时，有当日估值）
        2. 新浪接口
        3. 东方财富估算接口
        
        Args:
            fund_code: 基金代码
            
        Returns:
            dict: 包含实时估值数据，失败返回None
            {
                'estimate_nav': 实时估值,
                'yesterday_nav': 昨日净值,
                'estimate_time': 估值时间
            }
        """
        import json
        from datetime import datetime
        import requests
        
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        # 1. 优先尝试天天基金网（有实时估值）
        try:
            url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200 and 'jsonpgz' in response.text:
                # 解析jsonp格式
                json_str = response.text.replace('jsonpgz(', '').replace(');', '')
                data = json.loads(json_str)
                
                gztime = data.get('gztime', '')
                # 检查是否是今天的数据
                if today_str in gztime:
                    logger.info(f"天天基金网获取 {fund_code} 实时估值成功: {data.get('gsz')} ({gztime})")
                    return {
                        'estimate_nav': float(data.get('gsz', 0)),  # 估算净值
                        'yesterday_nav': float(data.get('dwjz', 0)),  # 单位净值（昨日）
                        'estimate_time': gztime,
                        'daily_return': float(data.get('gszzl', 0)),  # 估算涨跌幅
                        'source': 'tiantian'
                    }
                else:
                    logger.debug(f"天天基金网 {fund_code} 估值不是今天: {gztime}")
        except Exception as e:
            logger.debug(f"天天基金网实时估值获取失败 {fund_code}: {e}")
        
        # 2. 尝试新浪接口
        try:
            url = f"https://hq.sinajs.cn/list=f_{fund_code}"
            headers = {'Referer': 'https://finance.sina.com.cn'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.text
                key = f'f_{fund_code}="'
                if key in data:
                    parts = data.split('"')[1].split(',')
                    if len(parts) >= 6:
                        # 新浪返回: [名称, 单位净值, 累计净值, 昨日净值, 日期, 日增长率]
                        return {
                            'estimate_nav': float(parts[1]) if len(parts) > 1 else 0.0,
                            'yesterday_nav': float(parts[3]) if len(parts) > 3 else 0.0,
                            'estimate_time': parts[4] if len(parts) > 4 else '',
                            'daily_return': float(parts[5]) if len(parts) > 5 else 0.0,
                            'source': 'sina'
                        }
        except Exception as e:
            logger.debug(f"新浪实时估值获取失败 {fund_code}: {e}")
        
        # 尝试东方财富估值接口
        try:
            import akshare as ak
            # 使用akshare获取估值数据
            df = ak.fund_value_estimation_em(symbol=fund_code)
            if not df.empty:
                latest = df.iloc[0]
                return {
                    'estimate_nav': float(latest.get('gsz', 0)),  # 估算值
                    'yesterday_nav': float(latest.get('dwjz', 0)),  # 单位净值
                    'estimate_time': str(latest.get('gztime', '')),
                    'daily_return': float(latest.get('gszzl', 0)),  # 估算增长率
                    'source': 'eastmoney_estimate'
                }
        except Exception as e:
            logger.debug(f"东方财富估值获取失败 {fund_code}: {e}")
        
        return None
    
    def get_historical_data(self, fund_code: str, days: int = 30, 
                          start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取基金历史数据（兼容 EnhancedFundData 接口）
        
        Args:
            fund_code: 基金代码
            days: 历史数据天数
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame: 历史数据
        """
        try:
            # 使用 MultiSourceFundData 的历史数据方法
            df = self.get_fund_nav_history(
                fund_code, 
                source='auto',
                start_date=start_date,
                end_date=end_date
            )
            
            if df is not None and not df.empty:
                # 转换列名为 EnhancedFundData 格式
                column_mapping = {
                    'date': '净值日期',
                    'nav': '单位净值',
                    'accum_nav': '累计净值',
                    'daily_return': '日增长率'
                }
                
                # 只映射存在的列
                existing_mapping = {k: v for k, v in column_mapping.items() if k in df.columns}
                df = df.rename(columns=existing_mapping)
                
                # 如果指定了天数限制，进行截取
                if days and len(df) > days:
                    df = df.tail(days)
                
                logger.info(f"成功获取基金 {fund_code} 的 {len(df)} 条历史数据 (Tushare优先)")
                return df
            
            logger.warning(f"基金 {fund_code} 历史数据获取为空")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 历史数据失败: {e}")
            return pd.DataFrame()
    
    def get_performance_metrics(self, fund_code: str, days: int = 3650) -> Dict:
        """
        获取基金绩效指标（兼容 EnhancedFundData 接口）
        
        Args:
            fund_code: 基金代码
            days: 历史数据天数
            
        Returns:
            dict: 绩效指标
        """
        try:
            # 获取历史数据
            hist_data = self.get_historical_data(fund_code, days)
            
            if hist_data.empty or len(hist_data) < 2:
                return self._get_default_metrics()
            
            # 提取日收益率（需要转换列名）
            daily_growth_col = '日增长率' if '日增长率' in hist_data.columns else 'daily_return'
            if daily_growth_col in hist_data.columns:
                daily_returns = hist_data[daily_growth_col].dropna()
                # 处理百分比格式
                daily_returns = pd.to_numeric(daily_returns, errors='coerce')
                # 如果数值很小，可能是小数格式，需要转换为百分比
                if abs(daily_returns).mean() < 1:
                    daily_returns = daily_returns * 100
            else:
                daily_returns = pd.Series([0.0])
            
            if len(daily_returns) < 2:
                return self._get_default_metrics()
            
            # 计算各种绩效指标
            return self._calculate_metrics(daily_returns, hist_data)
            
        except Exception as e:
            logger.error(f"计算基金 {fund_code} 绩效指标失败: {e}")
            return self._get_default_metrics()
    
    def _calculate_metrics(self, daily_returns: pd.Series, hist_data: pd.DataFrame) -> Dict:
        """
        计算绩效指标（与 EnhancedFundData 保持一致）
        """
        try:
            from shared.enhanced_config import PERFORMANCE_CONFIG, INVESTMENT_STRATEGY_CONFIG
        except ImportError:
            # 如果无法导入配置，使用默认值
            PERFORMANCE_CONFIG = {
                'trading_days_per_year': 250,
                'var_confidence': 0.05,
                'weights': {
                    'annualized_return': 0.3,
                    'sharpe_ratio': 0.25,
                    'max_drawdown': 0.2,
                    'volatility': 0.15,
                    'win_rate': 0.1
                }
            }
            INVESTMENT_STRATEGY_CONFIG = {
                'risk_free_rate': 0.02
            }
        
        # 获取配置参数
        risk_free_rate = INVESTMENT_STRATEGY_CONFIG['risk_free_rate']
        trading_days = PERFORMANCE_CONFIG['trading_days_per_year']
        var_confidence = PERFORMANCE_CONFIG['var_confidence']
        
        # 计算总收益率
        nav_col = '单位净值' if '单位净值' in hist_data.columns else 'nav'
        if nav_col in hist_data.columns:
            start_nav = float(hist_data[nav_col].iloc[0])
            end_nav = float(hist_data[nav_col].iloc[-1])
            total_return = (end_nav - start_nav) / start_nav if start_nav != 0 else 0.0
        else:
            total_return = 0.0
        
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
        if nav_col in hist_data.columns:
            nav_series = pd.to_numeric(hist_data[nav_col], errors='coerce')
            cumulative_max = nav_series.expanding().max()
            drawdown = (nav_series - cumulative_max) / cumulative_max
            max_drawdown = drawdown.min()
        else:
            max_drawdown = 0.0
        
        # 计算Calmar比率
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
        
        # 计算Sortino比率
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
            'sharpe_ratio_ytd': sharpe_ratio,
            'sharpe_ratio_1y': sharpe_ratio,
            'sharpe_ratio_all': sharpe_ratio,
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
    
    def _get_default_metrics(self) -> Dict:
        """
        获取默认绩效指标
        """
        return {
            'annualized_return': 0.0,
            'sharpe_ratio': 0.0,
            'sharpe_ratio_ytd': 0.0,
            'sharpe_ratio_1y': 0.0,
            'sharpe_ratio_all': 0.0,
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
    
    def get_fund_basic_info(self, fund_code: str) -> Dict:
        """
        获取基金基本信息（兼容 EnhancedFundData 接口）
        
        Args:
            fund_code: 基金代码
            
        Returns:
            dict: 基金基本信息
        """
        try:
            basic_info = super().get_fund_basic_info(fund_code, source='auto')
            if basic_info:
                return basic_info
            
            # 降级到默认值
            return {
                'fund_code': fund_code,
                'fund_name': f'基金{fund_code}',
                'fund_type': '未知',
                'establish_date': None,
                'fund_company': '未知',
                'fund_manager': '未知',
                'management_fee': 0.0,
                'custody_fee': 0.0
            }
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 基本信息失败: {e}")
            return {
                'fund_code': fund_code,
                'fund_name': f'基金{fund_code}',
                'fund_type': '未知',
                'establish_date': None,
                'fund_company': '未知',
                'fund_manager': '未知',
                'management_fee': 0.0,
                'custody_fee': 0.0
            }

    @staticmethod
    def is_qdii_fund(fund_code: str, fund_name: str = None) -> bool:
        """
        判断是否为QDII基金（静态方法，兼容 EnhancedFundData）
        """
        # QDII基金代码列表
        QDII_FUND_CODES = {
            '096001',  # 大成标普500等权重指数(QDII)A人民币
            '100055',  # 富国全球科技互联网股票(QDII)A
            '012061',  # 富国全球消费精选混合(QDII)美元现汇
            '006680',  # 广发道琼斯石油指数(QDII-LOF)C美元现汇
            '006373',  # 国富全球科技互联混合(QDII)人民币A
            '006105',  # 宏利印度股票(QDII)A
            '021540',  # 华安法国CAC40ETF发起式联接(QDII)C
            '015016',  # 华安国际龙头(DAX)ETF联接C
            '040047',  # 华安纳斯达克100ETF联接(QDII)A(美元现钞)
            '007844',  # 华宝油气C
            '008708',  # 建信富时100指数(QDII)C美元现汇
            '501225',  # 景顺长城全球半导体芯片股票A(QDII-LOF)(人民币)
            '162415',  # 美国消费
            '007721',  # 天弘标普500发起(QDII-FOF)A
        }
        
        # 代码匹配
        if fund_code in QDII_FUND_CODES:
            return True
        
        # 名称匹配
        if fund_name and 'QDII' in fund_name.upper():
            return True
        
        return False