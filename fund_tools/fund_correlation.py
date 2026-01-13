import pandas as pd
import numpy as np
import akshare as ak
import matplotlib.pyplot as plt
import seaborn as sns
import datetime

class FundCorrelation:
    def __init__(self, start_date='2020-01-01', end_date=None):
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.datetime.now().strftime('%Y-%m-%d')
        self.fund_data = {}
        
    def get_fund_history(self, fund_code):
        """从akshare获取基金历史数据"""
        try:
            # 获取基金历史净值数据
            fund_hist = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            if fund_hist.empty:
                print(f"基金 {fund_code} 没有获取到历史数据")
                return None
            
            # 过滤日期范围
            fund_hist['净值日期'] = pd.to_datetime(fund_hist['净值日期'])
            fund_hist = fund_hist[(fund_hist['净值日期'] >= self.start_date) & (fund_hist['净值日期'] <= self.end_date)]
            
            # 转换数据类型
            fund_hist['单位净值'] = pd.to_numeric(fund_hist['单位净值'], errors='coerce')
            fund_hist = fund_hist.dropna(subset=['单位净值'])
            
            # 计算日收益率
            fund_hist['日收益率'] = fund_hist['单位净值'].pct_change().fillna(0)
            
            # 重置索引
            fund_hist = fund_hist.reset_index(drop=True)
            
            self.fund_data[fund_code] = fund_hist
            return fund_hist
        except Exception as e:
            print(f"获取基金 {fund_code} 历史数据时出错: {e}")
            return None
    
    def get_multiple_funds(self, fund_codes):
        """获取多只基金的历史数据"""
        for fund_code in fund_codes:
            print(f"正在获取基金 {fund_code} 的历史数据...")
            self.get_fund_history(fund_code)
        
        # 过滤掉没有获取到数据的基金
        valid_funds = [code for code in fund_codes if code in self.fund_data]
        if len(valid_funds) < 2:
            print("获取到的有效基金数量不足2只，无法计算相关性")
            return False
        
        print(f"成功获取 {len(valid_funds)} 只基金的数据")
        return True
    
    def calculate_correlation(self, method='pearson', based_on='returns'):
        """计算基金之间的相关性
        
        参数:
        method: 相关性计算方法，可选pearson, spearman, kendall
        based_on: 基于什么数据计算相关性，可选'returns'(收益率)或'nav'(净值)
        """
        if len(self.fund_data) < 2:
            print("没有足够的基金数据来计算相关性")
            return None
        
        # 选择要使用的数据列
        if based_on == 'returns':
            data_col = '日收益率'
            print(f"基于日收益率计算相关性")
        elif based_on == 'nav':
            data_col = '单位净值'
            print(f"基于单位净值计算相关性")
        else:
            print(f"无效的based_on参数: {based_on}，将默认使用日收益率")
            data_col = '日收益率'
            based_on = 'returns'
        
        # 合并所有基金的指定数据列
        merged_df = None
        for fund_code, data in self.fund_data.items():
            fund_data = data[['净值日期', data_col]].copy()
            fund_data = fund_data.rename(columns={data_col: fund_code})
            
            if merged_df is None:
                merged_df = fund_data
            else:
                merged_df = merged_df.merge(fund_data, on='净值日期', how='inner')
        
        # 检查合并后的数据
        if merged_df is None or merged_df.shape[1] < 3:
            print("无法合并基金数据，可能是日期范围没有重叠")
            return None
        
        # 计算相关性矩阵
        data_df = merged_df.drop('净值日期', axis=1)
        correlation_matrix = data_df.corr(method=method)
        
        return correlation_matrix
    
    def visualize_correlation(self, correlation_matrix, based_on='returns'):
        """可视化相关性矩阵"""
        if correlation_matrix is None:
            print("没有相关性数据可以可视化")
            return
        
        # 设置中文显示
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 创建热图
        plt.figure(figsize=(10, 8))
        sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0, 
                    fmt='.2f', square=True, linewidths=0.5)
        
        # 调整图表标题
        data_basis = "单位净值" if based_on == 'nav' else "日收益率"
        plt.title(f'基金组合相关性矩阵 ({data_basis}) - {self.start_date} 至 {self.end_date}')
        plt.tight_layout()
        
        # 保存图表
        chart_filename = f"fund_correlation_{based_on}_{self.start_date}_{self.end_date}.png"
        plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
        print(f"相关性热图已保存到文件: {chart_filename}")
        
        # 尝试显示图表
        try:
            plt.show()
        except:
            print("图表已保存但无法显示（可能是因为没有图形界面）")
    
    def run_analysis(self, fund_codes, method='pearson', based_on='returns'):
        """运行完整的相关性分析流程"""
        print(f"开始基金组合相关性分析")
        print(f"时间范围: {self.start_date} 至 {self.end_date}")
        print(f"基金列表: {fund_codes}")
        print(f"相关性计算方法: {method}")
        print(f"分析基础: {'单位净值' if based_on == 'nav' else '日收益率'}")
        print("=" * 60)
        
        # 获取基金数据
        if not self.get_multiple_funds(fund_codes):
            return None
        
        # 计算相关性
        correlation_matrix = self.calculate_correlation(method, based_on)
        if correlation_matrix is None:
            return None
        
        # 显示相关性矩阵
        print("\n相关性矩阵:")
        print(correlation_matrix)
        
        # 可视化相关性
        self.visualize_correlation(correlation_matrix, based_on)
        
        return correlation_matrix

# 示例用法
if __name__ == "__main__":
    # 创建相关性分析实例
    analyzer = FundCorrelation(start_date='2020-01-01', end_date='2023-12-31')
    
    # 示例基金组合（可以根据需要修改）
    fund_codes = ['005827', '110022', '000001', '001475', '000988']
    
    # 运行相关性分析 - 基于单位净值（基金本身）
    analyzer.run_analysis(fund_codes, method='pearson', based_on='nav')
