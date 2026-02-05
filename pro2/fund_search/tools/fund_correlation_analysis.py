"""
基金相关性分析工具
==================
用于计算两只基金之间的相关性，包括日收益率相关性、滚动相关性、不同周期相关性等。

使用方法:
    python fund_correlation_analysis.py

作者: AI Assistant
日期: 2026-02-05
"""

import akshare as ak
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 设置matplotlib后端为非GUI模式
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats
import seaborn as sns

# 设置matplotlib中文字体支持（Windows优先使用微软雅黑）
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# ============== 配置参数 ==============
# 基金代码和名称
FUND_1_CODE = "002179"  # 华安事件驱动量化混合A
FUND_1_NAME = "华安事件驱动量化混合A"

FUND_2_CODE = "013277"  # 富国创业板ETF联接C
FUND_2_NAME = "富国创业板ETF联接C"

# 分析起始日期 (可选)
START_DATE = None  # 例如: "2023-01-01", None表示使用全部数据

# 滚动窗口天数
ROLLING_WINDOW = 60

# 输出图表路径
OUTPUT_CHART = "fund_correlation_analysis.png"


# ============== 核心函数 ==============

def fetch_fund_nav(fund_code: str, fund_name: str) -> pd.DataFrame:
    """
    获取基金历史净值数据
    
    参数:
        fund_code: 基金代码
        fund_name: 基金名称
    
    返回:
        DataFrame包含净值日期和单位净值
    """
    print(f"正在获取 {fund_name}({fund_code}) 的数据...")
    nav_data = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
    nav_data['净值日期'] = pd.to_datetime(nav_data['净值日期'])
    nav_data = nav_data.sort_values('净值日期')
    nav_data = nav_data.rename(columns={'单位净值': 'nav'})
    
    print(f"✅ {fund_name} 数据获取成功")
    print(f"   数据范围: {nav_data['净值日期'].min().strftime('%Y-%m-%d')} 至 {nav_data['净值日期'].max().strftime('%Y-%m-%d')}")
    print(f"   数据条数: {len(nav_data)}")
    
    return nav_data


def calculate_returns(nav_data: pd.DataFrame) -> pd.DataFrame:
    """
    计算日收益率
    
    参数:
        nav_data: 包含nav列的DataFrame
    
    返回:
        添加了return列的DataFrame
    """
    data = nav_data.copy()
    data['return'] = data['nav'].pct_change() * 100  # 转换为百分比
    return data.dropna()


def calculate_correlation(returns_1: pd.Series, returns_2: pd.Series) -> dict:
    """
    计算多种相关系数
    
    参数:
        returns_1: 基金1的收益率序列
        returns_2: 基金2的收益率序列
    
    返回:
        包含各种相关系数的字典
    """
    # 皮尔逊相关系数 (线性相关)
    pearson_corr, pearson_p = stats.pearsonr(returns_1, returns_2)
    
    # 斯皮尔曼相关系数 (秩相关)
    spearman_corr, spearman_p = stats.spearmanr(returns_1, returns_2)
    
    # 肯德尔相关系数
    kendall_corr, kendall_p = stats.kendalltau(returns_1, returns_2)
    
    return {
        'pearson': {'corr': pearson_corr, 'p_value': pearson_p},
        'spearman': {'corr': spearman_corr, 'p_value': spearman_p},
        'kendall': {'corr': kendall_corr, 'p_value': kendall_p}
    }


def interpret_correlation(corr: float) -> str:
    """
    解读相关系数的强度
    
    参数:
        corr: 相关系数值
    
    返回:
        相关性强度描述
    """
    abs_corr = abs(corr)
    if abs_corr >= 0.8:
        strength = "极强相关"
    elif abs_corr >= 0.6:
        strength = "强相关"
    elif abs_corr >= 0.4:
        strength = "中等相关"
    elif abs_corr >= 0.2:
        strength = "弱相关"
    else:
        strength = "极弱相关或无相关"
    
    direction = "正相关" if corr > 0 else "负相关"
    return f"{strength} ({direction})"


def calculate_rolling_correlation(returns_1: pd.Series, returns_2: pd.Series, 
                                   window: int = 60) -> pd.Series:
    """
    计算滚动相关系数
    
    参数:
        returns_1: 基金1的收益率序列
        returns_2: 基金2的收益率序列
        window: 滚动窗口大小
    
    返回:
        滚动相关系数序列
    """
    return returns_1.rolling(window=window).corr(returns_2)


def calculate_period_correlation(nav_1: pd.Series, nav_2: pd.Series, 
                                  period: int) -> float:
    """
    计算指定周期的收益率相关性
    
    参数:
        nav_1: 基金1的净值序列
        nav_2: 基金2的净值序列
        period: 周期天数
    
    返回:
        相关系数
    """
    ret_1 = nav_1.pct_change(period) * 100
    ret_2 = nav_2.pct_change(period) * 100
    return ret_1.corr(ret_2)


def plot_correlation_analysis(merged_data: pd.DataFrame, returns_data: pd.DataFrame,
                               corr_results: dict, fund_1_name: str, fund_2_name: str,
                               output_path: str):
    """
    绘制相关性分析图表
    
    参数:
        merged_data: 合并后的净值数据
        returns_data: 收益率数据
        corr_results: 相关性结果字典
        fund_1_name: 基金1名称
        fund_2_name: 基金2名称
        output_path: 输出图表路径
    """
    pearson_corr = corr_results['pearson']['corr']
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'基金相关性分析: {fund_1_name} vs {fund_2_name}', 
                 fontsize=14, fontweight='bold')
    
    # 1. 散点图
    ax1 = axes[0, 0]
    ax1.scatter(returns_data['return_2'], returns_data['return_1'], 
                alpha=0.5, s=20, c='steelblue', edgecolors='none')
    z = np.polyfit(returns_data['return_2'], returns_data['return_1'], 1)
    p = np.poly1d(z)
    ax1.plot(returns_data['return_2'], p(returns_data['return_2']), 
             "r--", linewidth=2, label=f'趋势线: y={z[0]:.3f}x+{z[1]:.3f}')
    ax1.set_xlabel(f'{fund_2_name} 日收益率 (%)', fontsize=10)
    ax1.set_ylabel(f'{fund_1_name} 日收益率 (%)', fontsize=10)
    ax1.set_title(f'日收益率散点图 (Pearson r={pearson_corr:.4f})', fontsize=11)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
    ax1.axvline(x=0, color='k', linestyle='-', linewidth=0.5)
    
    # 2. 净值走势对比
    ax2 = axes[0, 1]
    norm_1 = merged_data['nav_1'] / merged_data['nav_1'].iloc[0] * 100
    norm_2 = merged_data['nav_2'] / merged_data['nav_2'].iloc[0] * 100
    ax2.plot(merged_data['净值日期'], norm_1, label=fund_1_name, 
             linewidth=1.5, color='#1f77b4')
    ax2.plot(merged_data['净值日期'], norm_2, label=fund_2_name, 
             linewidth=1.5, color='#ff7f0e')
    ax2.set_xlabel('日期', fontsize=10)
    ax2.set_ylabel('归一化净值 (起始=100)', fontsize=10)
    ax2.set_title('净值走势对比 (归一化)', fontsize=11)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 3. 滚动相关性
    ax3 = axes[1, 0]
    rolling_corr = calculate_rolling_correlation(
        returns_data['return_1'], returns_data['return_2'], ROLLING_WINDOW
    )
    ax3.plot(returns_data['净值日期'], rolling_corr, linewidth=1.5, color='green')
    ax3.axhline(y=pearson_corr, color='r', linestyle='--', linewidth=1.5, 
                label=f'整体相关性: {pearson_corr:.4f}')
    ax3.set_xlabel('日期', fontsize=10)
    ax3.set_ylabel(f'滚动相关系数 ({ROLLING_WINDOW}日)', fontsize=10)
    ax3.set_title(f'滚动相关性变化 ({ROLLING_WINDOW}日窗口)', fontsize=11)
    ax3.legend(loc='lower right')
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(-1, 1)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 4. 收益率分布
    ax4 = axes[1, 1]
    bins = np.linspace(-10, 10, 50)
    ax4.hist(returns_data['return_1'], bins=bins, alpha=0.6, 
             label=fund_1_name, color='#1f77b4', density=True)
    ax4.hist(returns_data['return_2'], bins=bins, alpha=0.6, 
             label=fund_2_name, color='#ff7f0e', density=True)
    ax4.set_xlabel('日收益率 (%)', fontsize=10)
    ax4.set_ylabel('概率密度', fontsize=10)
    ax4.set_title('日收益率分布对比', fontsize=11)
    ax4.legend(loc='upper right')
    ax4.grid(True, alpha=0.3)
    ax4.axvline(x=0, color='k', linestyle='-', linewidth=0.5)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ 图表已保存至: {output_path}")
    plt.show()


def print_analysis_report(fund_1_name: str, fund_2_name: str,
                          corr_results: dict, sample_size: int,
                          start_date: str, end_date: str):
    """
    打印分析报告
    
    参数:
        fund_1_name: 基金1名称
        fund_2_name: 基金2名称
        corr_results: 相关性结果字典
        sample_size: 样本数量
        start_date: 起始日期
        end_date: 结束日期
    """
    pearson = corr_results['pearson']
    spearman = corr_results['spearman']
    kendall = corr_results['kendall']
    
    print("\n" + "=" * 70)
    print("📊 基金相关性分析报告")
    print("=" * 70)
    print(f"\n基金1: {fund_1_name}")
    print(f"基金2: {fund_2_name}")
    print(f"分析期间: {start_date} 至 {end_date}")
    print(f"样本数量: {sample_size} 个交易日")
    
    print("\n" + "-" * 70)
    print("📈 相关性系数:")
    print("-" * 70)
    print(f"  皮尔逊相关系数 (Pearson):   {pearson['corr']:.4f} (p值: {pearson['p_value']:.2e})")
    print(f"  斯皮尔曼相关系数 (Spearman): {spearman['corr']:.4f} (p值: {spearman['p_value']:.2e})")
    print(f"  肯德尔相关系数 (Kendall):    {kendall['corr']:.4f} (p值: {kendall['p_value']:.2e})")
    print("-" * 70)
    
    interpretation = interpret_correlation(pearson['corr'])
    print(f"\n📋 结论: 两只基金呈 {interpretation}")
    print("=" * 70)


# ============== 主程序 ==============

def main():
    """主函数"""
    print("=" * 70)
    print("基金相关性分析工具")
    print("=" * 70)
    
    # 1. 获取基金数据
    fund_1_nav = fetch_fund_nav(FUND_1_CODE, FUND_1_NAME)
    fund_2_nav = fetch_fund_nav(FUND_2_CODE, FUND_2_NAME)
    
    # 2. 数据对齐
    merged_data = pd.merge(
        fund_1_nav[['净值日期', 'nav']].rename(columns={'nav': 'nav_1'}),
        fund_2_nav[['净值日期', 'nav']].rename(columns={'nav': 'nav_2'}),
        on='净值日期',
        how='inner'
    )
    
    # 根据起始日期筛选
    if START_DATE:
        merged_data = merged_data[merged_data['净值日期'] >= START_DATE]
    
    print(f"\n对齐后的数据条数: {len(merged_data)}")
    print(f"共同数据范围: {merged_data['净值日期'].min().strftime('%Y-%m-%d')} 至 {merged_data['净值日期'].max().strftime('%Y-%m-%d')}")
    
    # 3. 计算收益率
    merged_data['return_1'] = merged_data['nav_1'].pct_change() * 100
    merged_data['return_2'] = merged_data['nav_2'].pct_change() * 100
    returns_data = merged_data.dropna()
    
    # 4. 计算相关性
    corr_results = calculate_correlation(
        returns_data['return_1'], 
        returns_data['return_2']
    )
    
    # 5. 打印报告
    print_analysis_report(
        FUND_1_NAME, FUND_2_NAME,
        corr_results, len(returns_data),
        returns_data['净值日期'].min().strftime('%Y-%m-%d'),
        returns_data['净值日期'].max().strftime('%Y-%m-%d')
    )
    
    # 6. 计算不同周期的相关性
    print("\n📊 不同周期收益率相关性:")
    periods = [5, 10, 20, 60]
    period_names = ['周收益(5日)', '双周收益(10日)', '月收益(20日)', '季度收益(60日)']
    for p, name in zip(periods, period_names):
        corr_p = calculate_period_correlation(
            merged_data['nav_1'], merged_data['nav_2'], p
        )
        print(f"  {name}: {corr_p:.4f}")
    
    # 7. 绘制图表
    plot_correlation_analysis(
        merged_data, returns_data,
        corr_results, FUND_1_NAME, FUND_2_NAME,
        OUTPUT_CHART
    )


if __name__ == "__main__":
    main()
