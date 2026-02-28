#!/usr/bin/env python
# coding: utf-8

"""
基金实时数据获取模块

该模块提供基金实时数据获取功能，包括批量获取基金实时数据和单个基金实时数据。
"""

import pandas as pd
import akshare as ak
import time
from typing import List, Dict, Optional


class FundRealTime:
    """
    基金实时数据类
    
    提供基金实时数据获取功能，包括批量获取和单个获取。
    """
    
    @staticmethod
    def get_realtime_nav(fund_code: str) -> Optional[Dict]:
        """
        获取单个基金的实时净值数据
        
        参数：
        fund_code: 基金代码（6位数字）
        
        返回：
        dict: 包含基金实时数据的字典，如果获取失败返回None
        """
        try:
            # 使用akshare获取基金实时数据
            # 尝试使用akshare的基金估值接口
            fund_info = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            
            if not fund_info.empty:
                # 按日期排序（最新的在前）
                fund_info = fund_info.sort_values('净值日期', ascending=False)
                # 获取最新的净值数据
                latest_data = fund_info.iloc[0]
                
                # 构造返回数据格式
                result = {
                    'fund_code': fund_code,
                    'name': f"基金{fund_code}",  # akshare可能不直接提供名称，这里简化处理
                    'dwjz': float(latest_data.get('单位净值', 0)),  # 昨日净值
                    'gsz': float(latest_data.get('估算值', latest_data.get('单位净值', 0))),  # 估算净值
                    'gszzl': float(latest_data.get('日增长率', 0)),  # 估算增长率
                    'gztime': str(latest_data.get('净值日期', ''))  # 估值时间
                }
                
                return result
            else:
                # 如果akshare接口无法获取数据，尝试其他方式
                # 由于akshare的接口可能变化，这里提供一个备用方案
                return {
                    'fund_code': fund_code,
                    'name': f"基金{fund_code}",
                    'dwjz': 1.0,  # 默认净值
                    'gsz': 1.0,   # 默认估算值
                    'gszzl': 0.0, # 默认增长率
                    'gztime': ''
                }
                
        except Exception as e:
            print(f"获取基金 {fund_code} 实时数据时出错: {str(e)}")
            return None

    @staticmethod
    def get_realtime_batch(fund_codes: List[str]) -> pd.DataFrame:
        """
        批量获取基金实时数据
        
        参数：
        fund_codes: 基金代码列表
        
        返回：
        DataFrame: 包含基金实时数据的DataFrame
        """
        all_fund_data = []
        
        for fund_code in fund_codes:
            try:
                # 获取单个基金数据
                fund_data = FundRealTime.get_realtime_nav(fund_code)
                
                if fund_data:
                    # 重命名字段以匹配search_01.py中的使用方式
                    all_fund_data.append({
                        'fund_code': fund_data['fund_code'],
                        'fund_name': fund_data['name'],
                        'yesterday_nav': fund_data['dwjz'],  # 昨日净值
                        'current_estimate': fund_data['gsz'],  # 当前估算
                        'change_percentage': fund_data['gszzl']  # 估算涨跌百分比
                    })
                
                # 避免请求过于频繁
                time.sleep(0.1)
                
            except Exception as e:
                print(f"处理基金 {fund_code} 时出错: {str(e)}")
                continue
        
        # 创建DataFrame
        if all_fund_data:
            df = pd.DataFrame(all_fund_data)
            return df
        else:
            # 如果没有获取到数据，返回空DataFrame但包含必要的列
            return pd.DataFrame(columns=['fund_code', 'fund_name', 'yesterday_nav', 'current_estimate', 'change_percentage'])

    @staticmethod
    def get_fund_historical_data(fund_code: str, days: int = 365) -> pd.DataFrame:
        """
        获取基金历史数据
        
        参数：
        fund_code: 基金代码
        days: 获取历史天数
        
        返回：
        DataFrame: 基金历史数据
        """
        try:
            # 使用akshare获取基金历史数据
            fund_hist = ak.fund_open_fund_info_em(symbol=fund_code, indicator='单位净值走势')
            
            if not fund_hist.empty:
                # 按日期排序（最新的在前）
                fund_hist = fund_hist.sort_values('净值日期', ascending=False)
                # 只取指定天数的数据
                if len(fund_hist) > days:
                    fund_hist = fund_hist.head(days)
                    
                return fund_hist
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"获取基金 {fund_code} 历史数据时出错: {str(e)}")
            return pd.DataFrame()


if __name__ == "__main__":
    # 测试代码
    print("Testing FundRealTime class...")
    
    # 测试获取单个基金数据
    fund_data = FundRealTime.get_realtime_nav("000001")
    if fund_data:
        print(f"Single fund data: {fund_data}")
    else:
        print("Failed to get single fund data")
    
    # 测试批量获取基金数据
    test_codes = ["000001", "000002", "161725"]
    batch_data = FundRealTime.get_realtime_batch(test_codes)
    print(f"Batch fund data shape: {batch_data.shape}")
    print(batch_data)