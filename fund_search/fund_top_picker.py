#!/usr/bin/env python
# coding: utf-8

"""
基金筛选模块

该模块实现了从akshare获取每日排名靠前的基金，并进行初步筛选的功能。
"""

import akshare as ak
import pandas as pd
from datetime import datetime

class FundTopPicker:
    """
    基金筛选类
    
    该类实现了从akshare获取每日排名靠前的基金，并进行初步筛选的功能。
    """
    
    def __init__(self):
        """
        初始化基金筛选类
        """
        pass
    
    def get_top_funds_by_daily_return(self, top_n=20, fund_type='全部'):
        """
        根据日增长率获取排名靠前的基金
        
        参数：
        top_n: int, 要获取的基金数量，默认为20
        fund_type: str, 基金类型，默认为'全部'
        
        返回：
        pandas.DataFrame, 排名靠前的基金数据
        """
        try:
            # 从akshare获取开放式基金排名数据
            fund_rank = ak.fund_open_fund_rank_em(symbol=fund_type)
            
            # 检查数据是否为空
            if fund_rank.empty:
                print("没有获取到基金排名数据")
                return None
            
            # 将日增长率转换为浮点数
            fund_rank['日增长率'] = pd.to_numeric(fund_rank['日增长率'], errors='coerce')
            
            # 按日增长率降序排序
            fund_rank_sorted = fund_rank.sort_values(by='日增长率', ascending=False)
            
            # 获取排名前top_n的基金
            top_funds = fund_rank_sorted.head(top_n)
            
            # 重置索引
            top_funds = top_funds.reset_index(drop=True)
            
            return top_funds
        except Exception as e:
            print(f"获取基金排名数据时出错: {e}")
            return None
    
    def get_top_funds_by_weekly_return(self, top_n=20, fund_type='全部'):
        """
        根据周增长率获取排名靠前的基金
        
        参数：
        top_n: int, 要获取的基金数量，默认为20
        fund_type: str, 基金类型，默认为'全部'
        
        返回：
        pandas.DataFrame, 排名靠前的基金数据
        """
        try:
            # 从akshare获取开放式基金排名数据
            fund_rank = ak.fund_open_fund_rank_em(symbol=fund_type)
            
            # 检查数据是否为空
            if fund_rank.empty:
                print("没有获取到基金排名数据")
                return None
            
            # 将周增长率转换为浮点数
            fund_rank['近1周'] = pd.to_numeric(fund_rank['近1周'], errors='coerce')
            
            # 按周增长率降序排序
            fund_rank_sorted = fund_rank.sort_values(by='近1周', ascending=False)
            
            # 获取排名前top_n的基金
            top_funds = fund_rank_sorted.head(top_n)
            
            # 重置索引
            top_funds = top_funds.reset_index(drop=True)
            
            return top_funds
        except Exception as e:
            print(f"获取基金排名数据时出错: {e}")
            return None
    
    def get_top_funds_by_monthly_return(self, top_n=20, fund_type='全部'):
        """
        根据月增长率获取排名靠前的基金
        
        参数：
        top_n: int, 要获取的基金数量，默认为20
        fund_type: str, 基金类型，默认为'全部'
        
        返回：
        pandas.DataFrame, 排名靠前的基金数据
        """
        try:
            # 从akshare获取开放式基金排名数据
            fund_rank = ak.fund_open_fund_rank_em(symbol=fund_type)
            
            # 检查数据是否为空
            if fund_rank.empty:
                print("没有获取到基金排名数据")
                return None
            
            # 将月增长率转换为浮点数
            fund_rank['近1月'] = pd.to_numeric(fund_rank['近1月'], errors='coerce')
            
            # 按月增长率降序排序
            fund_rank_sorted = fund_rank.sort_values(by='近1月', ascending=False)
            
            # 获取排名前top_n的基金
            top_funds = fund_rank_sorted.head(top_n)
            
            # 重置索引
            top_funds = top_funds.reset_index(drop=True)
            
            return top_funds
        except Exception as e:
            print(f"获取基金排名数据时出错: {e}")
            return None
    
    def filter_funds_by_criteria(self, fund_df, min_return=0, max_fee=1.5):
        """
        根据条件筛选基金
        
        参数：
        fund_df: pandas.DataFrame, 基金数据
        min_return: float, 最低收益率要求，默认为0
        max_fee: float, 最高手续费要求，默认为1.5%
        
        返回：
        pandas.DataFrame, 筛选后的基金数据
        """
        try:
            # 将日增长率转换为浮点数
            fund_df['日增长率'] = pd.to_numeric(fund_df['日增长率'], errors='coerce')
            
            # 将手续费转换为浮点数
            fund_df['手续费'] = pd.to_numeric(fund_df['手续费'].str.rstrip('%'), errors='coerce')
            
            # 根据条件筛选
            filtered_funds = fund_df[fund_df['日增长率'] >= min_return]
            filtered_funds = filtered_funds[filtered_funds['手续费'] <= max_fee]
            
            # 重置索引
            filtered_funds = filtered_funds.reset_index(drop=True)
            
            return filtered_funds
        except Exception as e:
            print(f"筛选基金时出错: {e}")
            return fund_df

# 示例用法
if __name__ == "__main__":
    # 创建基金筛选实例
    picker = FundTopPicker()
    
    # 获取日增长率排名前20的基金
    top_20_daily = picker.get_top_funds_by_daily_return(top_n=20)
    print("日增长率排名前20的基金：")
    print(top_20_daily[['基金代码', '基金简称', '日增长率', '近1周', '近1月', '手续费']])
    
    # 获取周增长率排名前20的基金
    top_20_weekly = picker.get_top_funds_by_weekly_return(top_n=20)
    print("\n周增长率排名前20的基金：")
    print(top_20_weekly[['基金代码', '基金简称', '近1周', '近1月', '手续费']])
    
    # 获取月增长率排名前20的基金
    top_20_monthly = picker.get_top_funds_by_monthly_return(top_n=20)
    print("\n月增长率排名前20的基金：")
    print(top_20_monthly[['基金代码', '基金简称', '近1月', '近3月', '手续费']])
