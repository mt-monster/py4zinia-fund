#!/usr/bin/env python
# coding: utf-8

"""
真实数据获取器
用于获取沪深300指数和基金的真实历史净值数据
"""

import os
from pathlib import Path

# 设置 Tushare 缓存目录到项目目录（避免权限问题）
# 必须在导入 tushare 之前设置，因为 tushare 使用 os.path.expanduser('~')
_cache_dir = Path(__file__).parent.parent / '.cache' / 'tushare'
_cache_dir.mkdir(parents=True, exist_ok=True)
os.environ['HOME'] = str(_cache_dir)
os.environ['USERPROFILE'] = str(_cache_dir)
os.environ['TUSHARE_CACHE_DIR'] = str(_cache_dir)


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
            
            # 过滤日期范围 - 修复：不应该使用 .tail(days) 限制，因为我们已经按日期过滤了
            df = df[df['date'] >= start_date]
            df = df.sort_values('date', ascending=True).reset_index(drop=True)
            
            # 检查并处理列名（akshare不同版本可能返回中英文列名）
            logger.info(f"沪深300原始数据列名: {list(df.columns)}")
            
            # 重命名列 - 处理中英文列名
            column_mapping = {}
            if 'close' in df.columns:
                column_mapping['close'] = 'price'
            elif '收盘' in df.columns:
                column_mapping['收盘'] = 'price'
            
            if column_mapping:
                df = df.rename(columns=column_mapping)
            
            # 只保留需要的列
            if 'price' in df.columns:
                df = df[['date', 'price']]
            else:
                logger.error(f"无法找到价格列，可用列名: {list(df.columns)}")
                return pd.DataFrame()
            
            # 检查数据有效性
            if df['price'].isna().all():
                logger.error("沪深300价格数据全为NaN")
                return pd.DataFrame()
            
            logger.info(f"成功获取沪深300指数 {len(df)} 条历史数据，日期范围: {df['date'].min()} 至 {df['date'].max()}")
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
    def get_index_latest(symbol: str = "sh000300") -> Dict[str, Optional[float]]:
        """
        获取指数最新行情（实时）- 优先使用Tushare
        
        参数:
            symbol: 指数代码，例如 sh000300
            
        返回:
            dict: {name, price, change, change_percent, date}
        """
        try:
            logger.info(f"正在获取指数最新行情: {symbol}")
            
            # 优先尝试Tushare获取指数数据
            tushare_result = RealDataFetcher._get_index_from_tushare(symbol)
            if tushare_result:
                logger.info(f"使用Tushare获取指数 {symbol} 成功")
                return tushare_result
            
            # 如果Tushare失败，回退到AkShare
            spot_fetchers = [
                ("stock_zh_index_spot_em", {}),
                ("stock_zh_index_spot", {}),
                ("stock_zh_index_spot_sina", {})
            ]

            df = None
            used_source = None
            max_retries = 3
            retry_delay = 1  # 秒
            
            for fetcher_name, kwargs in spot_fetchers:
                if hasattr(ak, fetcher_name):
                    # 为每个数据源添加重试机制
                    for attempt in range(max_retries):
                        try:
                            df = getattr(ak, fetcher_name)(**kwargs)
                            if df is not None and len(df) > 0:
                                used_source = fetcher_name
                                logger.info(f"{fetcher_name} 获取成功 (尝试 {attempt + 1}/{max_retries})")
                                break
                            else:
                                logger.warning(f"{fetcher_name} 返回空数据 (尝试 {attempt + 1}/{max_retries})")
                        except Exception as e:
                            error_type = type(e).__name__
                            error_msg = str(e)
                            logger.warning(f"{fetcher_name} 获取失败 (尝试 {attempt + 1}/{max_retries}): {error_type} - {error_msg}")
                            if attempt < max_retries - 1:
                                import time
                                time.sleep(retry_delay)
                            continue
                    
                    if df is not None and len(df) > 0:
                        break

            if df is None or df.empty:
                logger.error("指数最新行情获取失败，返回空结果")
                return {}

            def pick_col(candidates):
                for c in candidates:
                    if c in df.columns:
                        return c
                return None

            code_col = pick_col(['代码', '指数代码', 'symbol', 'code'])
            name_col = pick_col(['名称', '指数名称', 'name'])
            price_col = pick_col(['最新价', '最新', 'price', '最新值', 'close'])
            change_col = pick_col(['涨跌额', '涨跌', 'change', '涨跌值'])
            change_pct_col = pick_col(['涨跌幅', 'change_percent', '涨跌幅%'])
            date_col = pick_col(['日期', '时间', 'date', 'datetime'])

            symbol_norm = symbol.lower().replace('.', '').replace('sh', '').replace('sz', '')
            row = None

            if code_col:
                df[code_col] = df[code_col].astype(str)
                row = df[df[code_col].str.contains(symbol_norm, na=False)]
            if (row is None or row.empty) and name_col:
                row = df[df[name_col].astype(str).str.contains('沪深300', na=False)]
            if row is None or row.empty:
                row = df.head(1)

            row = row.iloc[0]
            name = row[name_col] if name_col and name_col in row else '沪深300'
            price = float(row[price_col]) if price_col and pd.notna(row[price_col]) else None
            change = float(row[change_col]) if change_col and pd.notna(row[change_col]) else None
            change_percent = None
            if change_pct_col and pd.notna(row[change_pct_col]):
                change_percent = float(str(row[change_pct_col]).replace('%', '').strip())

            date_value = None
            if date_col and pd.notna(row[date_col]):
                date_value = str(row[date_col])

            return {
                'name': name,
                'price': price,
                'change': change,
                'change_percent': change_percent,
                'date': date_value,
                'source': used_source
            }
        except Exception as e:
            logger.error(f"获取指数最新行情失败: {str(e)}")
            return {}

    @staticmethod
    def _get_index_from_tushare(symbol: str) -> Optional[Dict]:
        """
        从Tushare获取指数数据
        
        参数:
            symbol: 指数代码，例如 sh000300
            
        返回:
            dict: 指数数据字典，失败返回None
        """
        try:
            import tushare as ts
            from shared.enhanced_config import DATA_SOURCE_CONFIG
            
            # 获取Tushare token
            tushare_token = DATA_SOURCE_CONFIG.get('tushare', {}).get('token')
            if not tushare_token:
                logger.warning("Tushare token未配置，跳过Tushare数据源")
                return None
                
            # 初始化Tushare
            ts.set_token(tushare_token)
            pro = ts.pro_api()
            
            # 转换指数代码格式
            ts_symbol = RealDataFetcher._convert_symbol_for_tushare(symbol)
            if not ts_symbol:
                logger.warning(f"无法转换指数代码: {symbol}")
                return None
            
            logger.info(f"正在使用Tushare获取指数数据: {ts_symbol}")
            
            # 获取指数行情数据
            df = pro.index_daily(ts_code=ts_symbol, limit=1)
            
            if df is None or df.empty:
                logger.warning(f"Tushare未返回 {ts_symbol} 数据")
                return None
            
            # 提取数据
            row = df.iloc[0]
            name = row.get('name', '沪深300')
            price = float(row.get('close', 0))
            pre_close = float(row.get('pre_close', price))
            change = price - pre_close
            change_percent = (change / pre_close * 100) if pre_close != 0 else 0
            
            return {
                'name': name,
                'price': price,
                'change': change,
                'change_percent': change_percent,
                'date': str(row.get('trade_date', '')),
                'source': 'tushare'
            }
            
        except Exception as e:
            logger.warning(f"Tushare获取指数 {symbol} 失败: {str(e)}")
            return None
    
    @staticmethod
    def _convert_symbol_for_tushare(symbol: str) -> Optional[str]:
        """
        转换指数代码为Tushare格式
        
        参数:
            symbol: 原始指数代码
            
        返回:
            str: Tushare格式的指数代码，无法转换返回None
        """
        symbol_lower = symbol.lower()
        
        # 沪深300
        if '000300' in symbol_lower or 'sh000300' in symbol_lower:
            return '000300.SH'
        
        # 上证指数
        if '000001' in symbol_lower or 'sh000001' in symbol_lower:
            return '000001.SH'
        
        # 深证成指
        if '399001' in symbol_lower or 'sz399001' in symbol_lower:
            return '399001.SZ'
        
        # 创业板指
        if '399006' in symbol_lower or 'sz399006' in symbol_lower:
            return '399006.SZ'
        
        logger.warning(f"不支持的指数代码格式: {symbol}")
        return None
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

    @staticmethod
    def get_fear_greed_index(days: int = 7) -> Dict:
        """
        计算 A 股市场情绪指数（恐贪指数）
        
        综合以下因子（均来自 Tushare，akshare 作为兜底）：
          1. 涨跌家数比        (40%) —— 当日上涨股票数 / 总股票数
          2. 量能变化          (20%) —— 今日成交量 / 20日均量
          3. 北向资金净流入    (20%) —— 沪深港通北向当日净流入
          4. 沪深300偏离均线  (20%) —— 收盘价偏离 20 日均线幅度

        参数：
            days: 返回最近 N 天的历史数据（用于迷你图）

        返回：
            {
              "value": 65,          # 今日指数 0-100
              "classification": "Greed",
              "history": [          # 最近 N 天列表（含今日，倒序）
                {"date": "2026-02-27", "value": 65, "classification": "Greed"},
                ...
              ]
            }
        """
        import tushare as ts
        from shared.enhanced_config import DATA_SOURCE_CONFIG

        tushare_token = DATA_SOURCE_CONFIG.get('tushare', {}).get('token')
        ts.set_token(tushare_token)
        pro = ts.pro_api()

        today = datetime.now()
        # 取 60 个交易日以便计算均线
        start_60 = (today - timedelta(days=90)).strftime('%Y%m%d')
        end_today = today.strftime('%Y%m%d')

        # ── 因子1：涨跌家数 ─────────────────────────────────────────────
        def get_advance_decline(trade_date: str) -> Optional[float]:
            """返回上涨股票占比 0-1，失败返回 None"""
            try:
                df = pro.daily_basic(trade_date=trade_date,
                                     fields='ts_code,change,pct_chg')
                if df is None or df.empty:
                    return None
                total = len(df)
                up = (df['pct_chg'] > 0).sum()
                return up / total if total > 0 else None
            except Exception as e:
                logger.warning(f"涨跌家数获取失败 {trade_date}: {e}")
                return None

        # ── 因子2：量能变化 ─────────────────────────────────────────────
        def get_volume_ratio(trade_date: str, hist_df: pd.DataFrame) -> Optional[float]:
            """返回成交量相对 20 日均量的倍数（取 0-2 区间归一化），失败返回 None"""
            try:
                if hist_df is None or hist_df.empty:
                    return None
                row = hist_df[hist_df['trade_date'] == trade_date]
                if row.empty:
                    return None
                idx = hist_df.index[hist_df['trade_date'] == trade_date].tolist()
                if not idx:
                    return None
                pos = hist_df.index.get_loc(idx[0])
                if pos < 19:
                    return None
                window = hist_df.iloc[max(0, pos - 19): pos + 1]
                ma20_vol = window['amount'].mean()
                today_vol = float(row.iloc[0]['amount'])
                ratio = today_vol / ma20_vol if ma20_vol > 0 else 1.0
                # 归一化：ratio=1 → 0.5，ratio>2 → 1，ratio<0.5 → 0
                normalized = min(max((ratio - 0.5) / 1.5, 0.0), 1.0)
                return normalized
            except Exception as e:
                logger.warning(f"量能变化计算失败 {trade_date}: {e}")
                return None

        # ── 因子3：北向资金 ─────────────────────────────────────────────
        def get_north_flow(trade_date: str, flow_df: pd.DataFrame) -> Optional[float]:
            """北向净流入归一化 0-1。失败返回 None"""
            try:
                if flow_df is None or flow_df.empty:
                    return None
                col_date = 'trade_date' if 'trade_date' in flow_df.columns else flow_df.columns[0]
                row = flow_df[flow_df[col_date] == trade_date]
                if row.empty:
                    return None
                # 尝试获取北向合计净流入（hk2sh_north_money 或 north_money）
                net_col = None
                for c in ['north_money', 'hgt_buy_elg', 'net_buy_value']:
                    if c in flow_df.columns:
                        net_col = c
                        break
                if net_col is None:
                    return None
                net = float(row.iloc[0][net_col])
                # 用 ±40亿 作归一化边界
                normalized = min(max((net / 4_000_000_000 + 1) / 2, 0.0), 1.0)
                return normalized
            except Exception as e:
                logger.warning(f"北向资金获取失败 {trade_date}: {e}")
                return None

        # ── 因子4：沪深300偏离均线 ──────────────────────────────────────
        def get_ma_deviation(trade_date: str, idx_df: pd.DataFrame) -> Optional[float]:
            """收盘价偏离 20 日均线归一化 0-1。失败返回 None"""
            try:
                if idx_df is None or idx_df.empty:
                    return None
                row_idx = idx_df.index[idx_df['trade_date'] == trade_date].tolist()
                if not row_idx:
                    return None
                pos = idx_df.index.get_loc(row_idx[0])
                if pos < 19:
                    return None
                window = idx_df.iloc[max(0, pos - 19): pos + 1]
                ma20 = window['close'].mean()
                close = float(idx_df.iloc[pos]['close'])
                deviation = (close - ma20) / ma20  # -0.1 ~ +0.1 典型区间
                normalized = min(max((deviation / 0.1 + 1) / 2, 0.0), 1.0)
                return normalized
            except Exception as e:
                logger.warning(f"均线偏离计算失败 {trade_date}: {e}")
                return None

        # ── 分类 ────────────────────────────────────────────────────────
        def classify(score: float) -> str:
            if score >= 75:
                return 'Extreme Greed'
            elif score >= 55:
                return 'Greed'
            elif score >= 45:
                return 'Neutral'
            elif score >= 25:
                return 'Fear'
            else:
                return 'Extreme Fear'

        # ── 获取基础数据 ─────────────────────────────────────────────────
        logger.info("开始获取 A 股情绪指数基础数据...")

        # 获取 60 日沪深300指数数据
        try:
            idx_df = pro.index_daily(ts_code='000300.SH',
                                     start_date=start_60, end_date=end_today,
                                     fields='trade_date,close')
            if idx_df is not None and not idx_df.empty:
                idx_df = idx_df.sort_values('trade_date').reset_index(drop=True)
        except Exception as e:
            logger.warning(f"沪深300历史数据获取失败: {e}")
            idx_df = pd.DataFrame()

        # 获取 60 日全市场日线（用于量能）
        # 使用上证指数成交量代替（pro.daily 全市场太慢，用index_daily沪深300成交量作为代理）
        try:
            mkt_vol_df = pro.index_daily(ts_code='000001.SH',
                                         start_date=start_60, end_date=end_today,
                                         fields='trade_date,amount')
            if mkt_vol_df is not None and not mkt_vol_df.empty:
                mkt_vol_df = mkt_vol_df.sort_values('trade_date').reset_index(drop=True)
        except Exception as e:
            logger.warning(f"市场成交量数据获取失败: {e}")
            mkt_vol_df = pd.DataFrame()

        # 获取北向资金
        try:
            flow_df = pro.moneyflow_hsgt(start_date=start_60, end_date=end_today)
            if flow_df is not None and not flow_df.empty:
                flow_df = flow_df.sort_values('trade_date').reset_index(drop=True)
        except Exception as e:
            logger.warning(f"北向资金数据获取失败: {e}")
            flow_df = pd.DataFrame()

        # ── 取最近 N 个交易日 ────────────────────────────────────────────
        # 以沪深300数据的交易日为基准
        if idx_df is None or idx_df.empty:
            logger.error("无法获取指数数据，情绪指数计算失败")
            return {}

        recent_trade_dates = idx_df['trade_date'].tolist()[-max(days, 1):]

        history = []
        for trade_date in reversed(recent_trade_dates):  # 最新在前
            # 因子1：涨跌家数（每次单独调用，成本较高，放最后）
            f1 = get_advance_decline(trade_date)
            f2 = get_volume_ratio(trade_date, mkt_vol_df)
            f3 = get_north_flow(trade_date, flow_df)
            f4 = get_ma_deviation(trade_date, idx_df)

            # 加权计算（跳过获取失败的因子并重新归一化）
            weights = {'f1': 0.40, 'f2': 0.20, 'f3': 0.20, 'f4': 0.20}
            factors = {'f1': f1, 'f2': f2, 'f3': f3, 'f4': f4}
            total_w = sum(w for k, w in weights.items() if factors[k] is not None)
            if total_w == 0:
                score = 50.0
            else:
                score = sum(factors[k] * weights[k] for k in weights if factors[k] is not None)
                score = score / total_w  # 归一化到 0-1
                score = round(score * 100)

            date_fmt = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
            classification = classify(score)
            history.append({
                'date': date_fmt,
                'value': int(score),
                'classification': classification
            })

        if not history:
            return {}

        latest = history[0]
        return {
            'value': latest['value'],
            'classification': latest['classification'],
            'date': latest['date'],
            'history': history
        }


# 全局实例
data_fetcher = RealDataFetcher()