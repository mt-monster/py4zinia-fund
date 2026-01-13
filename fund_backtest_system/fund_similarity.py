#!/usr/bin/env python
# coding: utf-8

"""
基金相似性分析模块

该模块实现了基金之间的相似性分析和组合构建功能。
"""

import pandas as pd
import numpy as np
import akshare as ak
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta

class FundSimilarityAnalyzer:
    """
    基金相似性分析类
    
    该类实现了基金之间的相似性分析和组合构建功能，包括：
    1. 获取基金历史收益率数据
    2. 计算基金之间的相关性
    3. 使用聚类算法对基金进行分组
    4. 构建多样化的基金组合
    """
    
    def __init__(self, start_date=None, end_date=None, lookback_days=180):
        """
        初始化基金相似性分析类
        
        参数：
        start_date: str, 开始日期，格式为'YYYY-MM-DD'，默认为lookback_days天前
        end_date: str, 结束日期，格式为'YYYY-MM-DD'，默认为当前日期
        lookback_days: int, 回溯天数，默认为180天
        """
        # 如果未指定结束日期，使用当前日期
        self.end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')
        # 如果未指定开始日期，使用lookback_days天前的日期
        if start_date:
            self.start_date = start_date
        else:
            start_date_dt = datetime.now() - timedelta(days=lookback_days)
            self.start_date = start_date_dt.strftime('%Y-%m-%d')
        
        self.lookback_days = lookback_days
        self.fund_returns = None  # 存储基金收益率数据
        self.correlation_matrix = None  # 存储相关系数矩阵
    
    def get_fund_returns(self, fund_codes):
        """
        获取多只基金的历史收益率数据
        
        参数：
        fund_codes: list, 基金代码列表
        
        返回：
        pandas.DataFrame, 基金收益率数据，行索引为日期，列索引为基金代码
        """
        try:
            # 初始化收益率字典
            returns_dict = {}
            
            for fund_code in fund_codes:
                # 获取基金历史数据
                fund_hist = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
                
                if fund_hist.empty:
                    print(f"基金 {fund_code} 没有获取到历史数据")
                    continue
                
                # 将日期转换为datetime类型
                fund_hist['净值日期'] = pd.to_datetime(fund_hist['净值日期'])
                
                # 筛选日期范围
                fund_hist = fund_hist[(fund_hist['净值日期'] >= self.start_date) & (fund_hist['净值日期'] <= self.end_date)]
                
                if len(fund_hist) < 2:
                    print(f"基金 {fund_code} 数据不足，无法计算收益率")
                    continue
                
                # 按日期排序
                fund_hist = fund_hist.sort_values('净值日期')
                
                # 计算每日收益率
                fund_hist['return'] = fund_hist['单位净值'].pct_change().fillna(0)
                
                # 存储收益率数据，日期为索引
                returns_dict[fund_code] = fund_hist.set_index('净值日期')['return']
            
            # 将字典转换为DataFrame
            self.fund_returns = pd.DataFrame(returns_dict)
            
            return self.fund_returns
        except Exception as e:
            print(f"获取基金收益率数据时出错: {e}")
            return None
    
    def calculate_correlation(self):
        """
        计算基金之间的相关系数
        
        返回：
        pandas.DataFrame, 基金相关系数矩阵
        """
        try:
            if self.fund_returns is None:
                print("请先获取基金收益率数据")
                return None
            
            # 计算相关系数矩阵
            self.correlation_matrix = self.fund_returns.corr()
            
            return self.correlation_matrix
        except Exception as e:
            print(f"计算相关系数时出错: {e}")
            return None
    
    def cluster_funds(self, n_clusters=5):
        """
        使用K-means算法对基金进行聚类
        
        参数：
        n_clusters: int, 聚类数量，默认为5
        
        返回：
        dict, 聚类结果，键为聚类编号，值为基金代码列表
        """
        try:
            if self.correlation_matrix is None:
                print("请先计算基金相关系数")
                return None
            
            # 标准化数据
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(self.correlation_matrix)
            
            # 使用K-means算法聚类
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            clusters = kmeans.fit_predict(X_scaled)
            
            # 构建聚类结果字典
            cluster_dict = {}
            for fund_code, cluster_id in zip(self.correlation_matrix.columns, clusters):
                if cluster_id not in cluster_dict:
                    cluster_dict[cluster_id] = []
                cluster_dict[cluster_id].append(fund_code)
            
            return cluster_dict
        except Exception as e:
            print(f"聚类基金时出错: {e}")
            return None
    
    def build_diversified_portfolio(self, fund_codes, n_clusters=5, portfolio_size=10):
        """
        构建多样化的基金组合
        
        参数：
        fund_codes: list, 基金代码列表
        n_clusters: int, 聚类数量，默认为5
        portfolio_size: int, 组合中基金数量，默认为10
        
        返回：
        list, 多样化的基金组合
        """
        try:
            # 获取基金收益率数据
            self.get_fund_returns(fund_codes)
            
            # 计算相关系数
            self.calculate_correlation()
            
            # 聚类基金
            cluster_dict = self.cluster_funds(n_clusters=n_clusters)
            
            if cluster_dict is None:
                return []
            
            # 计算每个聚类的大小
            cluster_sizes = {k: len(v) for k, v in cluster_dict.items()}
            
            # 计算每个聚类应分配的基金数量
            portfolio = []
            remaining_size = portfolio_size
            
            # 按聚类大小降序排序
            sorted_clusters = sorted(cluster_dict.items(), key=lambda x: len(x[1]), reverse=True)
            
            for cluster_id, funds_in_cluster in sorted_clusters:
                # 计算该聚类应分配的基金数量
                # 基于聚类大小的比例分配
                cluster_ratio = len(funds_in_cluster) / len(fund_codes)
                assigned = max(1, min(len(funds_in_cluster), int(round(cluster_ratio * portfolio_size))))
                
                # 确保不超过剩余需要的基金数量
                assigned = min(assigned, remaining_size)
                
                # 从该聚类中随机选择assigned只基金
                selected_funds = np.random.choice(funds_in_cluster, size=assigned, replace=False).tolist()
                portfolio.extend(selected_funds)
                
                remaining_size -= assigned
                
                if remaining_size <= 0:
                    break
            
            # 如果还有剩余名额，从所有基金中随机选择
            if remaining_size > 0:
                all_funds = [f for f in fund_codes if f not in portfolio]
                if all_funds:
                    additional_funds = np.random.choice(all_funds, size=remaining_size, replace=False).tolist()
                    portfolio.extend(additional_funds)
            
            return portfolio
        except Exception as e:
            print(f"构建多样化组合时出错: {e}")
            return []
    
    def select_low_correlation_funds(self, fund_codes, portfolio_size=10, correlation_threshold=0.5):
        """
        选择低相关性的基金组合
        
        参数：
        fund_codes: list, 基金代码列表
        portfolio_size: int, 组合中基金数量，默认为10
        correlation_threshold: float, 相关性阈值，默认为0.5
        
        返回：
        list, 低相关性的基金组合
        """
        try:
            # 获取基金收益率数据
            self.get_fund_returns(fund_codes)
            
            # 计算相关系数
            self.calculate_correlation()
            
            if self.correlation_matrix is None:
                return []
            
            # 初始化组合
            portfolio = []
            
            # 首先选择收益率最高的基金
            avg_returns = self.fund_returns.mean()
            sorted_funds = avg_returns.sort_values(ascending=False).index.tolist()
            
            # 添加第一只基金
            if sorted_funds:
                portfolio.append(sorted_funds[0])
            
            # 依次添加相关性最低的基金
            for fund in sorted_funds[1:]:
                if len(portfolio) >= portfolio_size:
                    break
                
                # 计算该基金与组合中所有基金的平均相关性
                avg_corr = self.correlation_matrix.loc[fund, portfolio].mean()
                
                # 如果平均相关性低于阈值，添加到组合中
                if avg_corr < correlation_threshold:
                    portfolio.append(fund)
            
            # 如果组合数量不足，从剩余基金中选择相关性最低的
            remaining_funds = [f for f in sorted_funds if f not in portfolio]
            while len(portfolio) < portfolio_size and remaining_funds:
                # 计算每个剩余基金与组合的平均相关性
                min_avg_corr = float('inf')
                best_fund = None
                
                for fund in remaining_funds:
                    avg_corr = self.correlation_matrix.loc[fund, portfolio].mean()
                    if avg_corr < min_avg_corr:
                        min_avg_corr = avg_corr
                        best_fund = fund
                
                if best_fund:
                    portfolio.append(best_fund)
                    remaining_funds.remove(best_fund)
                else:
                    break
            
            return portfolio
        except Exception as e:
            print(f"选择低相关性基金时出错: {e}")
            return []

# 示例用法
if __name__ == "__main__":
    # 从基金筛选模块获取排名前20的基金
    from fund_top_picker import FundTopPicker
    
    # 创建基金筛选实例
    picker = FundTopPicker()
    
    # 获取日增长率排名前20的基金
    top_20_funds = picker.get_top_funds_by_daily_return(top_n=20)
    
    if top_20_funds is not None:
        # 获取基金代码列表
        fund_codes = top_20_funds['基金代码'].tolist()
        
        # 创建基金相似性分析实例
        analyzer = FundSimilarityAnalyzer(lookback_days=180)
        
        # 获取基金收益率数据
        returns = analyzer.get_fund_returns(fund_codes)
        print(f"获取到 {len(returns.columns)} 只基金的收益率数据")
        
        # 计算相关系数
        correlation = analyzer.calculate_correlation()
        print("\n基金相关系数矩阵：")
        print(correlation.round(2))
        
        # 聚类基金
        clusters = analyzer.cluster_funds(n_clusters=4)
        print("\n基金聚类结果：")
        for cluster_id, funds in clusters.items():
            print(f"聚类 {cluster_id}: {funds}")
        
        # 构建多样化组合
        diversified_portfolio = analyzer.build_diversified_portfolio(fund_codes, n_clusters=4, portfolio_size=8)
        print("\n多样化基金组合：")
        print(diversified_portfolio)
        
        # 选择低相关性基金
        low_corr_portfolio = analyzer.select_low_correlation_funds(fund_codes, portfolio_size=8, correlation_threshold=0.5)
        print("\n低相关性基金组合：")
        print(low_corr_portfolio)
