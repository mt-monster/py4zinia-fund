#!/usr/bin/env python
# coding: utf-8

"""
增强版基金相关性分析模块
基于tools目录的fund_correlation_analysis.py功能，提供更全面的相关性分析

时间统计功能：记录各阶段耗时并输出优化状态报告
"""

import logging
import time
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from scipy import stats
import matplotlib
matplotlib.use('Agg')  # 设置matplotlib后端为非GUI模式
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
import base64
from io import BytesIO
import platform

# 导入性能监控工具
from .correlation_performance_monitor import (
    CorrelationPerformanceMonitor, 
    StageTimer,
    timed_correlation_analysis
)

logger = logging.getLogger(__name__)

# 全局配置matplotlib中文字体
def setup_chinese_font():
    """配置matplotlib支持中文显示"""
    system = platform.system()
    
    # 尝试查找可用的中文字体
    chinese_fonts = []
    if system == 'Windows':
        chinese_fonts = ['Microsoft YaHei', 'SimHei', 'SimSun', 'NSimSun', 'FangSong', 'KaiTi', '微软雅黑', '黑体', '宋体']
    elif system == 'Darwin':  # macOS
        chinese_fonts = ['Arial Unicode MS', 'Heiti TC', 'Heiti SC', 'PingFang SC', 'STHeiti']
    else:  # Linux
        chinese_fonts = ['WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 'Noto Sans CJK SC', 'SimHei']
    
    # 获取系统中所有可用字体
    available_fonts = set([f.name for f in font_manager.fontManager.ttflist])
    
    # 找到第一个可用的中文字体
    selected_font = None
    for font in chinese_fonts:
        if font in available_fonts:
            selected_font = font
            logger.info(f"选择中文字体: {font}")
            break
    
    # 如果找不到预定义的中文字体，尝试查找包含中文字符的任意字体
    if not selected_font:
        for font_prop in font_manager.fontManager.ttflist:
            # 检查字体名称是否包含中文相关关键词
            font_name = font_prop.name.lower()
            if any(keyword in font_name for keyword in ['yahei', 'hei', 'song', 'fang', 'pingfang', 'wenquan', 'noto']):
                selected_font = font_prop.name
                logger.info(f"选择备选中文字体: {selected_font}")
                break
    
    if selected_font:
        # 设置主要中文字体
        plt.rcParams['font.sans-serif'] = [selected_font, 'DejaVu Sans', 'Bitstream Vera Sans', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'sans-serif']
        logger.info(f"已设置中文字体: {selected_font}")
        
        # 强制设置所有文本元素的字体
        plt.rcParams['font.family'] = 'sans-serif'
        
        # 针对Windows系统额外优化
        if system == 'Windows':
            # 确保使用系统默认的高质量中文字体
            plt.rcParams['font.serif'] = ['Times New Roman', 'SimSun', selected_font]
            plt.rcParams['font.monospace'] = ['Courier New', 'FangSong', selected_font]
    else:
        # 如果没有找到中文字体，使用默认字体并记录警告
        logger.warning("未找到合适的中文字体，图表中文可能显示为方块")
        # 设置fallback字体以尽量减少乱码
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Bitstream Vera Sans', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'sans-serif']
        plt.rcParams['font.family'] = 'sans-serif'
    
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    
    # 抑制字体警告信息
    import warnings
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

# 初始化字体配置
setup_chinese_font()

class EnhancedCorrelationAnalyzer:
    """
    增强版基金相关性分析器
    """
    
    def __init__(self):
        """初始化分析器"""
        self.rolling_window = 60  # 默认滚动窗口天数
        # 字体配置已在模块级别全局设置
    
    def analyze_enhanced_correlation(self, fund_data_dict: Dict[str, pd.DataFrame], 
                                   fund_names: Dict[str, str]) -> Dict:
        """
        执行增强版相关性分析（含时间统计）
        
        参数:
        fund_data_dict: 基金代码到历史数据DataFrame的映射
        fund_names: 基金代码到基金名称的映射
        
        返回:
        dict: 增强的相关性分析结果（包含性能数据）
        """
        # 初始化性能监控
        monitor = CorrelationPerformanceMonitor()
        monitor.start("total")
        
        try:
            fund_codes = list(fund_data_dict.keys())
            if len(fund_codes) < 2:
                raise ValueError("至少需要2只基金进行相关性分析")
            
            logger.info(f"[Performance] 开始增强相关性分析，基金数量: {len(fund_codes)}")
            
            # 1. 数据预处理和对齐
            with StageTimer("数据预处理和对齐", monitor):
                aligned_data = self._align_fund_data(fund_data_dict)
            
            # 2. 计算基础相关性矩阵
            with StageTimer("基础相关性矩阵计算", monitor):
                basic_correlation = self._calculate_basic_correlation(aligned_data)
            
            # 3. 计算多种相关系数
            with StageTimer("多种相关系数计算", monitor):
                enhanced_correlation = self._calculate_enhanced_correlation(aligned_data)
            
            # 4. 计算滚动相关性
            with StageTimer("滚动相关性计算", monitor):
                rolling_correlation = self._calculate_rolling_correlation(aligned_data)
            
            # 5. 计算不同周期相关性
            with StageTimer("不同周期相关性计算", monitor):
                period_correlation = self._calculate_period_correlation(aligned_data)
            
            # 6. 识别高相关性基金组合
            with StageTimer("高相关性组合识别", monitor):
                high_correlation_pairs = self._identify_high_correlation_pairs(
                    fund_codes, fund_names, basic_correlation['correlation_matrix']
                )
            
            # 7. 生成相关性解读
            with StageTimer("相关性解读生成", monitor):
                interpretation = self._interpret_correlation_results(basic_correlation, enhanced_correlation)
            
            # 记录总耗时
            total_time = monitor.end("total")
            
            result = {
                'basic_correlation': basic_correlation,
                'enhanced_analysis': {
                    'correlation_methods': enhanced_correlation,
                    'rolling_correlation': rolling_correlation,
                    'period_correlation': period_correlation,
                    'interpretation': interpretation
                },
                'high_correlation_pairs': high_correlation_pairs,
                'analysis_metadata': {
                    'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'data_points': len(aligned_data),
                    'fund_count': len(fund_codes)
                },
                '_performance': {
                    'total_time_ms': total_time,
                    'stage_timings': monitor.timings,
                    'optimization_status': monitor.check_optimizations(),
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # 输出性能报告
            logger.info(f"[Performance] 增强相关性分析完成，基金数量: {len(fund_codes)}, 总耗时: {total_time:.2f} ms")
            monitor.log_report()
            
            return result
            
        except Exception as e:
            elapsed = monitor.end("total")
            logger.error(f"[Performance] 增强相关性分析失败，耗时: {elapsed:.2f} ms, 错误: {e}")
            raise
    
    def _align_fund_data(self, fund_data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        对齐多只基金的历史数据
        
        参数:
        fund_data_dict: 基金代码到历史数据DataFrame的映射
        
        返回:
        pd.DataFrame: 对齐后的数据，列为各基金的日收益率
        """
        # 合并所有基金数据
        merged_df = None
        for fund_code, df in fund_data_dict.items():
            if 'daily_return' not in df.columns:
                logger.warning(f"基金 {fund_code} 缺少 daily_return 列，跳过")
                continue
            
            # 只保留需要的列，避免数据过大
            df_clean = df[['date', 'daily_return']].copy()
            df_clean = df_clean.dropna(subset=['daily_return'])
            
            # 确保日期格式正确
            df_clean['date'] = pd.to_datetime(df_clean['date'])
            
            df_renamed = df_clean.rename(columns={'daily_return': fund_code})
            
            if merged_df is None:
                merged_df = df_renamed
            else:
                # 使用内连接只保留共同日期，避免数据量爆炸
                merged_df = pd.merge(merged_df, df_renamed, on='date', how='inner')
        
        if merged_df is None or len(merged_df) == 0:
            raise ValueError("无法对齐基金数据，基金可能没有共同的交易日")
        
        # 限制数据点数量，避免内存溢出（最多使用最近500个交易日）
        max_data_points = 500
        if len(merged_df) > max_data_points:
            logger.warning(f"数据点过多({len(merged_df)})，限制为最近{max_data_points}个交易日")
            merged_df = merged_df.sort_values('date').tail(max_data_points)
        
        # 数据清理
        merged_df = merged_df.dropna()
        numeric_columns = [col for col in merged_df.columns if col != 'date']
        merged_df[numeric_columns] = merged_df[numeric_columns].apply(pd.to_numeric, errors='coerce')
        merged_df = merged_df.dropna()
        
        # 过滤异常值（收益率超过±100%）
        for col in numeric_columns:
            merged_df = merged_df[merged_df[col].abs() <= 100]
        
        # 检查是否有足够的数据点
        if len(merged_df) < 2:
            logger.error(f"数据对齐后数据点不足: {len(merged_df)}，需要至少2个")
            # 输出每只基金的数据情况以便调试
            for fund_code, df in fund_data_dict.items():
                date_count = len(df) if 'date' in df.columns else 0
                return_count = len(df.dropna(subset=['daily_return'])) if 'daily_return' in df.columns else 0
                logger.info(f"基金 {fund_code}: 总记录 {date_count}, 有效收益率记录 {return_count}")
            raise ValueError(f"数据对齐后只有 {len(merged_df)} 个数据点，无法计算相关性")
        
        logger.info(f"数据对齐完成，共{len(merged_df)}个数据点，{len(numeric_columns)}只基金")
        return merged_df
    
    def _calculate_basic_correlation(self, aligned_data: pd.DataFrame) -> Dict:
        """
        计算基础相关性矩阵（皮尔逊相关系数）
        
        参数:
        aligned_data: 对齐后的基金数据
        
        返回:
        dict: 基础相关性结果
        """
        fund_columns = [col for col in aligned_data.columns if col != 'date']
        correlation_matrix = aligned_data[fund_columns].corr(method='pearson')
        
        return {
            'fund_codes': fund_columns,
            'correlation_matrix': correlation_matrix.values.tolist(),
            'method': 'pearson'
        }
    
    def _calculate_enhanced_correlation(self, aligned_data: pd.DataFrame) -> Dict:
        """
        计算多种相关系数
        
        参数:
        aligned_data: 对齐后的基金数据
        
        返回:
        dict: 包含皮尔逊、斯皮尔曼、肯德尔相关系数的结果
        """
        fund_columns = [col for col in aligned_data.columns if col != 'date']
        results = {}
        
        # 计算每对基金的相关系数
        for i in range(len(fund_columns)):
            for j in range(i + 1, len(fund_columns)):
                fund1 = fund_columns[i]
                fund2 = fund_columns[j]
                
                returns1 = aligned_data[fund1]
                returns2 = aligned_data[fund2]
                
                # 皮尔逊相关系数
                pearson_corr, pearson_p = stats.pearsonr(returns1, returns2)
                
                # 斯皮尔曼相关系数（秩相关）
                spearman_corr, spearman_p = stats.spearmanr(returns1, returns2)
                
                # 肯德尔相关系数
                kendall_corr, kendall_p = stats.kendalltau(returns1, returns2)
                
                pair_key = f"{fund1}_{fund2}"
                results[pair_key] = {
                    'pearson': {'corr': float(pearson_corr), 'p_value': float(pearson_p)},
                    'spearman': {'corr': float(spearman_corr), 'p_value': float(spearman_p)},
                    'kendall': {'corr': float(kendall_corr), 'p_value': float(kendall_p)}
                }
        
        return results
    
    def _calculate_rolling_correlation(self, aligned_data: pd.DataFrame) -> List[Dict]:
        """
        计算滚动相关系数
        
        参数:
        aligned_data: 对齐后的基金数据
        
        返回:
        list: 滚动相关系数时间序列
        """
        fund_columns = [col for col in aligned_data.columns if col != 'date']
        if len(fund_columns) < 2:
            return []
        
        # 只计算第一对基金的滚动相关性作为示例
        fund1, fund2 = fund_columns[0], fund_columns[1]
        returns1 = aligned_data[fund1]
        returns2 = aligned_data[fund2]
        
        # 计算滚动相关系数
        rolling_corr = returns1.rolling(window=self.rolling_window).corr(returns2)
        
        # 构造结果
        result = []
        for idx, corr_value in rolling_corr.items():
            if not pd.isna(corr_value):
                date_str = aligned_data.loc[idx, 'date'].strftime('%Y-%m-%d')
                result.append({
                    'date': date_str,
                    'correlation': float(corr_value)
                })
        
        return result[-200:]  # 只返回最近200个数据点以减少传输量
    
    def _calculate_period_correlation(self, aligned_data: pd.DataFrame) -> Dict:
        """
        计算不同周期的相关性
        
        参数:
        aligned_data: 对齐后的基金数据
        
        返回:
        dict: 不同周期的相关性系数
        """
        fund_columns = [col for col in aligned_data.columns if col != 'date']
        if len(fund_columns) < 2:
            return {}
        
        fund1, fund2 = fund_columns[0], fund_columns[1]
        nav1 = self._returns_to_nav(aligned_data[fund1])
        nav2 = self._returns_to_nav(aligned_data[fund2])
        
        periods = {
            'weekly': 5,      # 周收益(5日)
            'biweekly': 10,   # 双周收益(10日)  
            'monthly': 20,    # 月收益(20日)
            'quarterly': 60   # 季度收益(60日)
        }
        
        results = {}
        for period_name, period_days in periods.items():
            corr = self._calculate_period_corr(nav1, nav2, period_days)
            results[period_name] = float(corr) if not pd.isna(corr) else 0.0
        
        return results
    
    def _returns_to_nav(self, returns: pd.Series) -> pd.Series:
        """
        将收益率序列转换为净值序列
        
        参数:
        returns: 日收益率序列（百分比形式）
        
        返回:
        pd.Series: 净值序列
        """
        # 假设初始净值为100
        nav = [100]
        for ret in returns:
            new_nav = nav[-1] * (1 + ret / 100)
            nav.append(new_nav)
        return pd.Series(nav[:-1], index=returns.index)
    
    def _calculate_period_corr(self, nav1: pd.Series, nav2: pd.Series, period: int) -> float:
        """
        计算指定周期的收益率相关性
        
        参数:
        nav1: 基金1的净值序列
        nav2: 基金2的净值序列
        period: 周期天数
        
        返回:
        float: 相关系数
        """
        ret1 = nav1.pct_change(period) * 100
        ret2 = nav2.pct_change(period) * 100
        return ret1.corr(ret2)
    
    def _identify_high_correlation_pairs(self, fund_codes: List[str], fund_names: Dict[str, str],
                                       correlation_matrix: List[List[float]]) -> List[Dict]:
        """
        识别高相关性的基金组合
        
        参数:
        fund_codes: 基金代码列表
        fund_names: 基金代码到名称的映射
        correlation_matrix: 相关性矩阵
        
        返回:
        list: 高相关性基金组合列表
        """
        high_pairs = []
        threshold = 0.7  # 高相关性阈值
        
        for i in range(len(fund_codes)):
            for j in range(i + 1, len(fund_codes)):
                correlation = correlation_matrix[i][j]
                if abs(correlation) >= threshold:
                    fund1_code = fund_codes[i]
                    fund2_code = fund_codes[j]
                    
                    high_pairs.append({
                        'fund1_code': fund1_code,
                        'fund1_name': fund_names.get(fund1_code, fund1_code),
                        'fund2_code': fund2_code,
                        'fund2_name': fund_names.get(fund2_code, fund2_code),
                        'correlation': round(correlation, 4),
                        'strength': self._get_correlation_strength(correlation),
                        'direction': '正相关' if correlation > 0 else '负相关'
                    })
        
        # 按相关性强度排序
        high_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
        return high_pairs[:10]  # 只返回前10个最高相关性组合
    
    def _get_correlation_strength(self, corr: float) -> str:
        """
        获取相关性强度描述
        
        参数:
        corr: 相关系数值
        
        返回:
        str: 相关性强度描述
        """
        abs_corr = abs(corr)
        if abs_corr >= 0.8:
            return "极强相关"
        elif abs_corr >= 0.6:
            return "强相关"
        elif abs_corr >= 0.4:
            return "中等相关"
        elif abs_corr >= 0.2:
            return "弱相关"
        else:
            return "极弱相关"
    
    def _interpret_correlation_results(self, basic_corr: Dict, enhanced_corr: Dict) -> str:
        """
        解读相关性分析结果
        
        参数:
        basic_corr: 基础相关性结果
        enhanced_corr: 增强相关性结果
        
        返回:
        str: 相关性分析解读
        """
        fund_codes = basic_corr['fund_codes']
        if len(fund_codes) < 2:
            return "数据不足，无法进行相关性分析"
        
        # 获取第一对基金的相关系数作为代表
        first_pair_key = f"{fund_codes[0]}_{fund_codes[1]}"
        if first_pair_key in enhanced_corr:
            pearson_corr = enhanced_corr[first_pair_key]['pearson']['corr']
            strength = self._get_correlation_strength(pearson_corr)
            direction = "正相关" if pearson_corr > 0 else "负相关"
            return f"基金间呈{strength}（{direction}），相关系数为{pearson_corr:.4f}"
        else:
            return "相关性分析完成"

    def generate_interactive_correlation_data(self, fund_data_dict: Dict[str, pd.DataFrame], 
                                            fund_names: Dict[str, str],
                                            lazy_load: bool = True) -> Dict:
        """
        生成用于交互式图表的详细相关性数据（优化版，支持懒加载和时间统计）
        
        参数:
        fund_data_dict: 基金代码到历史数据DataFrame的映射
        fund_names: 基金代码到基金名称的映射
        lazy_load: 是否启用懒加载模式，默认True
        
        返回:
        dict: 包含散点图、净值对比、滚动相关性、分布图等详细数据（含性能数据）
        """
        # 初始化性能监控
        monitor = CorrelationPerformanceMonitor()
        monitor.start("total")
        
        try:
            logger.info(f"[Performance] 开始生成交互式相关性数据，基金数量: {len(fund_data_dict)}")
            
            # 数据对齐
            with StageTimer("数据对齐", monitor):
                aligned_data = self._align_fund_data(fund_data_dict)
            
            if len(aligned_data.columns) < 3:  # 至少需要两列基金数据加日期列
                logger.warning(f"对齐后数据列不足: {len(aligned_data.columns)} 列")
                return {}
            
            if len(aligned_data) < 2:  # 至少需要2个数据点
                logger.warning(f"对齐后数据点不足: {len(aligned_data)} 行")
                return {}
                
            fund_columns = [col for col in aligned_data.columns if col != 'date']
            
            # 分析所有基金组合（如果有多只基金）
            if len(fund_columns) >= 2:
                
                # 找到相关性最高的组合作为主组合显示
                with StageTimer("主组合查找", monitor):
                    primary_pair = self._find_primary_pair(aligned_data, fund_columns, fund_names)
                    fund1_col, fund2_col = primary_pair['fund1_col'], primary_pair['fund2_col']
                    fund1_name, fund2_name = primary_pair['fund1_name'], primary_pair['fund2_name']
                
                # 只生成主组合的完整图表数据
                returns1 = aligned_data[fund1_col]
                returns2 = aligned_data[fund2_col]
                
                with StageTimer("主组合图表数据生成", monitor):
                    primary_data = {
                        'fund1_code': fund1_col,
                        'fund2_code': fund2_col,
                        'fund1_name': fund1_name,
                        'fund2_name': fund2_name,
                        'correlation_results': self._calculate_single_pair_correlation(returns1, returns2),
                        'scatter_data': self._generate_scatter_data(returns1, returns2),
                        'nav_comparison_data': self._generate_nav_comparison_data(returns1, returns2, aligned_data['date'], fund1_name, fund2_name),
                        'rolling_correlation_data': self._generate_rolling_correlation_data(returns1, returns2, aligned_data['date'], fund1_name, fund2_name),
                        'distribution_data': self._generate_distribution_data(returns1, returns2, fund1_name, fund2_name)
                    }
                
                # 生成所有基金的净值对比和分布数据（这些是必需的，且计算量不大）
                with StageTimer("净值对比和分布数据生成", monitor):
                    all_funds_nav_data = self._generate_all_funds_nav_comparison(
                        aligned_data, fund_columns, fund_names
                    )
                    all_funds_distribution = self._generate_all_funds_distribution(
                        aligned_data, fund_columns, fund_names
                    )
                
                # 生成所有组合的精简信息（只包含基本信息，不包含详细图表数据）
                with StageTimer("组合摘要生成", monitor):
                    all_combinations_summary = []
                    for i in range(len(fund_columns)):
                        for j in range(i + 1, len(fund_columns)):
                            f1_col, f2_col = fund_columns[i], fund_columns[j]
                            f1_name = fund_names.get(f1_col, f1_col)
                            f2_name = fund_names.get(f2_col, f2_col)
                            
                            # 只计算相关系数，不生成图表数据
                            corr = aligned_data[f1_col].corr(aligned_data[f2_col])
                            
                            all_combinations_summary.append({
                                'fund1_code': f1_col,
                                'fund2_code': f2_col,
                                'fund1_name': f1_name,
                                'fund2_name': f2_name,
                                'correlation': float(corr) if not pd.isna(corr) else 0.0,
                                'has_detail': (f1_col == fund1_col and f2_col == fund2_col) or 
                                             (f1_col == fund2_col and f2_col == fund1_col)
                            })
                    
                    # 按相关性绝对值排序
                    all_combinations_summary.sort(key=lambda x: abs(x['correlation']), reverse=True)
                
                # 记录总耗时
                total_time = monitor.end("total")
                
                result = {
                    'primary_combination': primary_data,
                    'all_combinations_summary': all_combinations_summary,  # 精简版组合列表
                    'all_funds_nav_comparison': all_funds_nav_data,
                    'all_funds_distribution': all_funds_distribution,
                    'lazy_load_enabled': lazy_load,
                    'metadata': {
                        'data_points': len(aligned_data),
                        'fund_count': len(fund_columns),
                        'combination_count': len(all_combinations_summary),
                        'date_range': {
                            'start': aligned_data['date'].min().strftime('%Y-%m-%d'),
                            'end': aligned_data['date'].max().strftime('%Y-%m-%d')
                        }
                    },
                    '_performance': {
                        'total_time_ms': total_time,
                        'stage_timings': monitor.timings,
                        'optimization_status': monitor.check_optimizations(),
                        'timestamp': datetime.now().isoformat()
                    }
                }
                
                # 输出性能报告
                logger.info(f"[Performance] 交互式数据生成完成，基金数量: {len(fund_columns)}, 总耗时: {total_time:.2f} ms")
                monitor.log_report()
                
                return result
                
            return {}
            
        except Exception as e:
            elapsed = monitor.end("total")
            logger.error(f"[Performance] 生成交互式相关性数据失败，耗时: {elapsed:.2f} ms, 错误: {e}")
            return {}
    
    def _find_primary_pair(self, aligned_data: pd.DataFrame, fund_columns: List[str], 
                           fund_names: Dict[str, str]) -> Dict:
        """
        找出相关性最高（或最具代表性）的基金对作为主显示
        
        参数:
        aligned_data: 对齐后的数据
        fund_columns: 基金代码列表
        fund_names: 基金名称映射
        
        返回:
        dict: 主基金对信息
        """
        # 默认使用第一对
        fund1_col, fund2_col = fund_columns[0], fund_columns[1]
        max_correlation = 0
        
        # 遍历找到绝对相关性最高的对（关注高相关性组合）
        for i in range(len(fund_columns)):
            for j in range(i + 1, len(fund_columns)):
                corr = aligned_data[fund_columns[i]].corr(aligned_data[fund_columns[j]])
                if not pd.isna(corr) and abs(corr) > abs(max_correlation):
                    max_correlation = corr
                    fund1_col, fund2_col = fund_columns[i], fund_columns[j]
        
        return {
            'fund1_col': fund1_col,
            'fund2_col': fund2_col,
            'fund1_name': fund_names.get(fund1_col, fund1_col),
            'fund2_name': fund_names.get(fund2_col, fund2_col),
            'correlation': max_correlation
        }
    
    def generate_pair_detail_data(self, fund_data_dict: Dict[str, pd.DataFrame],
                                  fund_names: Dict[str, str],
                                  fund1_code: str, 
                                  fund2_code: str) -> Dict:
        """
        按需生成单个基金对的详细分析数据（懒加载API使用）
        
        参数:
        fund_data_dict: 基金数据字典
        fund_names: 基金名称映射
        fund1_code: 基金1代码
        fund2_code: 基金2代码
        
        返回:
        dict: 该基金对的完整分析数据
        """
        try:
            if fund1_code not in fund_data_dict or fund2_code not in fund_data_dict:
                return {}
            
            # 数据对齐（复用已有方法）
            aligned_data = self._align_fund_data(fund_data_dict)
            
            if fund1_code not in aligned_data.columns or fund2_code not in aligned_data.columns:
                return {}
            
            returns1 = aligned_data[fund1_code]
            returns2 = aligned_data[fund2_code]
            fund1_name = fund_names.get(fund1_code, fund1_code)
            fund2_name = fund_names.get(fund2_code, fund2_code)
            
            return {
                'fund1_code': fund1_code,
                'fund2_code': fund2_code,
                'fund1_name': fund1_name,
                'fund2_name': fund2_name,
                'correlation_results': self._calculate_single_pair_correlation(returns1, returns2),
                'scatter_data': self._generate_scatter_data(returns1, returns2),
                'nav_comparison_data': self._generate_nav_comparison_data(returns1, returns2, aligned_data['date'], fund1_name, fund2_name),
                'rolling_correlation_data': self._generate_rolling_correlation_data(returns1, returns2, aligned_data['date'], fund1_name, fund2_name),
                'distribution_data': self._generate_distribution_data(returns1, returns2, fund1_name, fund2_name)
            }
            
        except Exception as e:
            logger.error(f"生成基金对详细数据失败: {e}")
            return {}

    def _generate_all_funds_nav_comparison(self, aligned_data: pd.DataFrame, 
                                           fund_columns: List[str], 
                                           fund_names: Dict[str, str]) -> Dict:
        """
        生成所有基金的净值对比数据（支持多只基金同时显示）
        
        参数:
        aligned_data: 对齐后的基金数据
        fund_columns: 基金代码列表
        fund_names: 基金代码到基金名称的映射
        
        返回:
        dict: 包含所有基金的净值数据
        """
        try:
            # 格式化日期
            formatted_dates = [date.strftime('%Y-%m-%d') for date in aligned_data['date']]
            
            # 为每只基金计算净值
            funds_data = []
            for fund_col in fund_columns:
                returns = aligned_data[fund_col]
                
                # 将收益率转换为净值
                nav = self._returns_to_nav_for_plot(returns)
                
                # 归一化处理（起始值设为100）
                normalized_nav = (nav / nav.iloc[0]) * 100
                
                funds_data.append({
                    'fund_code': fund_col,
                    'fund_name': fund_names.get(fund_col, fund_col),
                    'values': normalized_nav.tolist()
                })
            
            return {
                'dates': formatted_dates,
                'funds': funds_data,
                'fund_count': len(funds_data)
            }
            
        except Exception as e:
            logger.error(f"生成所有基金净值对比数据失败: {e}")
            return {}

    def _generate_all_funds_distribution(self, aligned_data: pd.DataFrame,
                                         fund_columns: List[str],
                                         fund_names: Dict[str, str]) -> Dict:
        """
        生成所有基金的收益率分布数据（支持多只基金同时显示）
        
        参数:
        aligned_data: 对齐后的基金数据
        fund_columns: 基金代码列表
        fund_names: 基金代码到基金名称的映射
        
        返回:
        dict: 包含所有基金的收益率分布数据
        """
        try:
            # 定义收益率区间
            bins = [-np.inf, -5, -3, -1, 1, 3, 5, np.inf]
            labels = ['<-5%', '-5~-3%', '-3~-1%', '-1~1%', '1~3%', '3~5%', '>5%']
            
            # 为每只基金计算收益率分布
            funds_distribution = []
            for fund_col in fund_columns:
                returns = aligned_data[fund_col]
                
                # 计算分布
                hist, _ = np.histogram(returns, bins=bins)
                
                fund_display_name = fund_names.get(fund_col, fund_col)
                # 如果基金名称为空或与代码相同，使用代码作为显示名称
                if not fund_display_name or fund_display_name == fund_col:
                    fund_display_name = fund_col
                
                funds_distribution.append({
                    'fund_code': fund_col,
                    'fund_name': fund_display_name,
                    'counts': hist.tolist()
                })
            
            return {
                'bins': labels,
                'funds': funds_distribution,
                'fund_count': len(funds_distribution)
            }
            
        except Exception as e:
            logger.error(f"生成所有基金收益率分布数据失败: {e}")
            return {}

    def _generate_scatter_data(self, returns1: pd.Series, returns2: pd.Series) -> Dict:
        """生成散点图数据"""
        # 检查数据点数量
        if len(returns1) < 2 or len(returns2) < 2:
            logger.warning(f"[Performance] 散点图数据点不足: fund1={len(returns1)}, fund2={len(returns2)}")
            return {
                'points': [],
                'correlation': 0.0,
                'trend_line': {'slope': 0, 'intercept': 0, 'equation': 'y = 0'}
            }
        
        # 限制数据点数量以提高性能
        max_points = 500
        if len(returns1) > max_points:
            # 采样数据点
            indices = np.linspace(0, len(returns1)-1, max_points).astype(int)
            returns1_sampled = returns1.iloc[indices]
            returns2_sampled = returns2.iloc[indices]
        else:
            returns1_sampled = returns1
            returns2_sampled = returns2
            
        # 构造Chart.js格式的数据
        scatter_points = []
        for i in range(len(returns1_sampled)):
            scatter_points.append({
                'x': float(returns2_sampled.iloc[i]),
                'y': float(returns1_sampled.iloc[i])
            })
            
        # 计算相关系数时也要检查数据点数量
        try:
            if len(returns1_sampled) >= 2 and len(returns2_sampled) >= 2:
                correlation = returns1_sampled.corr(returns2_sampled)
            else:
                correlation = 0.0
                logger.warning(f"[Performance] 相关系数计算数据点不足: {len(returns1_sampled)} vs {len(returns2_sampled)}")
        except Exception as e:
            logger.warning(f"[Performance] 相关系数计算失败: {e}")
            correlation = 0.0
            
        return {
            'points': scatter_points,
            'correlation': float(correlation),
            'trend_line': self._calculate_trend_line(returns2_sampled, returns1_sampled)
        }

    def _calculate_trend_line(self, x_data: pd.Series, y_data: pd.Series) -> Dict:
        """计算趋势线参数"""
        try:
            # 检查数据点数量，至少需要2个点才能计算趋势线
            if len(x_data) < 2 or len(y_data) < 2:
                logger.warning(f"[Performance] 数据点不足，无法计算趋势线: x={len(x_data)}, y={len(y_data)}")
                return {'slope': 0, 'intercept': 0, 'equation': 'y = 0'}
            
            slope, intercept = np.polyfit(x_data, y_data, 1)
            return {
                'slope': float(slope),
                'intercept': float(intercept),
                'equation': f'y = {slope:.3f}x + {intercept:.3f}'
            }
        except Exception as e:
            logger.warning(f"[Performance] 计算趋势线失败: {e}")
            return {'slope': 0, 'intercept': 0, 'equation': 'y = 0'}

    def _generate_nav_comparison_data(self, returns1: pd.Series, returns2: pd.Series, 
                                    dates: pd.Series, fund1_name: str, fund2_name: str) -> Dict:
        """生成净值对比数据"""
        # 将收益率转换为净值
        nav1 = self._returns_to_nav_for_plot(returns1)
        nav2 = self._returns_to_nav_for_plot(returns2)
        
        # 归一化处理（起始值设为100）
        normalized_nav1 = (nav1 / nav1.iloc[0]) * 100
        normalized_nav2 = (nav2 / nav2.iloc[0]) * 100
        
        # 格式化日期
        formatted_dates = [date.strftime('%Y-%m-%d') for date in dates]
        
        return {
            'dates': formatted_dates,
            'fund1_values': normalized_nav1.tolist(),
            'fund2_values': normalized_nav2.tolist(),
            'fund1_name': fund1_name,
            'fund2_name': fund2_name
        }

    def _generate_rolling_correlation_data(self, returns1: pd.Series, returns2: pd.Series,
                                         dates: pd.Series, fund1_name: str, fund2_name: str) -> Dict:
        """生成滚动相关性数据"""
        # 计算滚动相关系数
        rolling_corr = returns1.rolling(window=self.rolling_window).corr(returns2)
        
        # 获取整体相关系数
        overall_corr = returns1.corr(returns2)
        
        # 清理NaN值并限制数据点
        clean_data = rolling_corr.dropna()
        if len(clean_data) > 200:
            # 采样保持趋势
            indices = np.linspace(0, len(clean_data)-1, 200).astype(int)
            sampled_corr = clean_data.iloc[indices]
            sampled_dates = dates.iloc[indices]
        else:
            sampled_corr = clean_data
            sampled_dates = dates.loc[clean_data.index]
        
        formatted_dates = [date.strftime('%Y-%m-%d') for date in sampled_dates]
        
        return {
            'dates': formatted_dates,
            'correlations': sampled_corr.tolist(),
            'overall_corr': float(overall_corr),
            'window': self.rolling_window,
            'fund1_name': fund1_name,
            'fund2_name': fund2_name
        }

    def _generate_distribution_data(self, returns1: pd.Series, returns2: pd.Series, 
                                    fund1_name: str, fund2_name: str) -> Dict:
        """生成收益率分布数据"""
        # 定义收益率区间
        bins = [-np.inf, -5, -3, -1, 1, 3, 5, np.inf]
        labels = ['<-5%', '-5~-3%', '-3~-1%', '-1~1%', '1~3%', '3~5%', '>5%']
        
        # 计算分布
        hist1, _ = np.histogram(returns1, bins=bins)
        hist2, _ = np.histogram(returns2, bins=bins)
        
        return {
            'bins': labels,
            'fund1_counts': hist1.tolist(),
            'fund2_counts': hist2.tolist(),
            'fund1_name': fund1_name,
            'fund2_name': fund2_name
        }

    def generate_correlation_charts(self, fund_data_dict: Dict[str, pd.DataFrame], 
                                  fund_names: Dict[str, str]) -> Dict[str, str]:
        """
            生成相关性分析图表
            fund_data_dict: 基金代码到历史数据DataFrame的映射
            fund_names: 基金代码到基金名称的映射
                
            返回:
            dict: 包含各个图表的base64编码字符串
        """
        try:
            # 数据对齐
            aligned_data = self._align_fund_data(fund_data_dict)
                
            if len(aligned_data.columns) < 3:  # 至少需要两列基金数据加日期列
                return {}
                
            fund_columns = [col for col in aligned_data.columns if col != 'date']
                
            # 只分析前两只基金（如果有多只）
            if len(fund_columns) >= 2:
                fund1_col, fund2_col = fund_columns[0], fund_columns[1]
                fund1_name = fund_names.get(fund1_col, fund1_col)
                fund2_name = fund_names.get(fund2_col, fund2_col)
                    
                # 计算相关系数
                returns1 = aligned_data[fund1_col]
                returns2 = aligned_data[fund2_col]
                corr_results = self._calculate_single_pair_correlation(returns1, returns2)
                    
                # 生成图表
                chart_base64 = self._create_correlation_chart(
                    aligned_data, fund1_col, fund2_col, fund1_name, fund2_name, corr_results
                )
                    
                return {
                    'correlation_chart': chart_base64,
                    'fund1_name': fund1_name,
                    'fund2_name': fund2_name
                }
                
            return {}
                
        except Exception as e:
            logger.error(f"生成相关性图表失败: {e}")
            return {}

    def _calculate_single_pair_correlation(self, returns1: pd.Series, returns2: pd.Series) -> Dict:
        """计算单对基金的相关系数"""
        # 皮尔逊相关系数
        pearson_corr, pearson_p = stats.pearsonr(returns1, returns2)
            
        # 斯皮尔曼相关系数
        spearman_corr, spearman_p = stats.spearmanr(returns1, returns2)
            
        # 肯德尔相关系数
        kendall_corr, kendall_p = stats.kendalltau(returns1, returns2)
                
        return {
            'pearson': {'corr': float(pearson_corr), 'p_value': float(pearson_p)},
            'spearman': {'corr': float(spearman_corr), 'p_value': float(spearman_p)},
            'kendall': {'corr': float(kendall_corr), 'p_value': float(kendall_p)}
        }

    def _create_correlation_chart(self, aligned_data: pd.DataFrame, 
                                fund1_col: str, fund2_col: str,
                                fund1_name: str, fund2_name: str,
                                corr_results: Dict) -> str:
            """
            创建四合一相关性分析图表
                
            参数:
            aligned_data: 对齐的数据
            fund1_col, fund2_col: 基金列名
            fund1_name, fund2_name: 基金名称
            corr_results: 相关性结果
                
            返回:
            str: base64编码的PNG图片
            """
            try:
                pearson_corr = corr_results['pearson']['corr']
                returns1 = aligned_data[fund1_col]
                returns2 = aligned_data[fund2_col]
                
                # 设置美观的图表样式
                plt.style.use('seaborn-v0_8-whitegrid')
                
                # 定义配色方案
                color1 = '#3498db'  # 蓝色
                color2 = '#e74c3c'  # 红色
                color_trend = '#2ecc71'  # 绿色
                color_rolling = '#9b59b6'  # 紫色
                    
                # 创建图表，增大尺寸
                fig, axes = plt.subplots(2, 2, figsize=(16, 12))
                fig.patch.set_facecolor('#fafafa')
                
                # 设置主标题
                fig.suptitle(f'基金相关性分析\n{fund1_name} vs {fund2_name}', 
                            fontsize=16, fontweight='bold', color='#2c3e50', y=0.98)
                    
                # 1. 散点图 - 日收益率相关性
                ax1 = axes[0, 0]
                ax1.set_facecolor('#ffffff')
                scatter = ax1.scatter(returns2, returns1, alpha=0.6, s=30, c=color1, 
                                     edgecolors='white', linewidth=0.5)
                    
                # 添加趋势线
                z = np.polyfit(returns2, returns1, 1)
                p = np.poly1d(z)
                x_line = np.linspace(returns2.min(), returns2.max(), 100)
                ax1.plot(x_line, p(x_line), color=color2, linestyle='--', linewidth=2.5, 
                        label=f'趋势线: y={z[0]:.3f}x+{z[1]:.3f}')
                    
                ax1.set_xlabel(f'{fund2_name[:10]}... 日收益率 (%)' if len(fund2_name) > 10 else f'{fund2_name} 日收益率 (%)', 
                              fontsize=11, color='#34495e')
                ax1.set_ylabel(f'{fund1_name[:10]}... 日收益率 (%)' if len(fund1_name) > 10 else f'{fund1_name} 日收益率 (%)', 
                              fontsize=11, color='#34495e')
                ax1.set_title(f'日收益率散点图\nPearson r = {pearson_corr:.4f}', 
                             fontsize=12, fontweight='bold', color='#2c3e50', pad=10)
                ax1.legend(loc='upper left', fontsize=9, framealpha=0.9)
                ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
                ax1.axhline(y=0, color='#7f8c8d', linestyle='-', linewidth=0.8, alpha=0.5)
                ax1.axvline(x=0, color='#7f8c8d', linestyle='-', linewidth=0.8, alpha=0.5)
                ax1.tick_params(axis='both', labelsize=9, colors='#34495e')
                    
                # 2. 净值走势对比
                ax2 = axes[0, 1]
                ax2.set_facecolor('#ffffff')
                # 将收益率转换为净值进行对比
                nav1 = self._returns_to_nav_for_plot(returns1)
                nav2 = self._returns_to_nav_for_plot(returns2)
                    
                # 归一化处理
                norm_nav1 = nav1 / nav1.iloc[0] * 100
                norm_nav2 = nav2 / nav2.iloc[0] * 100
                    
                dates = aligned_data['date']
                ax2.plot(dates, norm_nav1, label=fund1_name[:12] + '...' if len(fund1_name) > 12 else fund1_name, 
                        linewidth=2, color=color1, alpha=0.9)
                ax2.plot(dates, norm_nav2, label=fund2_name[:12] + '...' if len(fund2_name) > 12 else fund2_name, 
                        linewidth=2, color=color2, alpha=0.9)
                ax2.fill_between(dates, norm_nav1, alpha=0.1, color=color1)
                ax2.fill_between(dates, norm_nav2, alpha=0.1, color=color2)
                ax2.set_xlabel('日期', fontsize=11, color='#34495e')
                ax2.set_ylabel('归一化净值 (起始=100)', fontsize=11, color='#34495e')
                ax2.set_title('净值走势对比 (归一化)', fontsize=12, fontweight='bold', color='#2c3e50', pad=10)
                ax2.legend(loc='upper left', fontsize=9, framealpha=0.9)
                ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)
                ax2.tick_params(axis='both', labelsize=9, colors='#34495e')
                    
                # 3. 滚动相关性
                ax3 = axes[1, 0]
                ax3.set_facecolor('#ffffff')
                rolling_corr = returns1.rolling(window=self.rolling_window).corr(returns2)
                    
                ax3.plot(dates, rolling_corr, linewidth=2, color=color_rolling, alpha=0.9)
                ax3.fill_between(dates, rolling_corr, alpha=0.2, color=color_rolling)
                ax3.axhline(y=pearson_corr, color=color2, linestyle='--', linewidth=2, 
                           label=f'整体相关性: {pearson_corr:.4f}')
                ax3.axhline(y=0, color='#7f8c8d', linestyle='-', linewidth=0.8, alpha=0.5)
                ax3.set_xlabel('日期', fontsize=11, color='#34495e')
                ax3.set_ylabel(f'滚动相关系数 ({self.rolling_window}日)', fontsize=11, color='#34495e')
                ax3.set_title(f'滚动相关性变化 ({self.rolling_window}日窗口)', 
                             fontsize=12, fontweight='bold', color='#2c3e50', pad=10)
                ax3.legend(loc='lower right', fontsize=9, framealpha=0.9)
                ax3.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
                ax3.set_ylim(-1.1, 1.1)
                ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)
                ax3.tick_params(axis='both', labelsize=9, colors='#34495e')
                    
                # 4. 收益率分布
                ax4 = axes[1, 1]
                ax4.set_facecolor('#ffffff')
                # 动态计算bins范围
                all_returns = pd.concat([returns1, returns2])
                bin_min = max(-10, all_returns.min() - 1)
                bin_max = min(10, all_returns.max() + 1)
                bins = np.linspace(bin_min, bin_max, 40)
                
                ax4.hist(returns1, bins=bins, alpha=0.7, label=fund1_name[:12] + '...' if len(fund1_name) > 12 else fund1_name, 
                        color=color1, density=True, edgecolor='white', linewidth=0.5)
                ax4.hist(returns2, bins=bins, alpha=0.7, label=fund2_name[:12] + '...' if len(fund2_name) > 12 else fund2_name, 
                        color=color2, density=True, edgecolor='white', linewidth=0.5)
                ax4.set_xlabel('日收益率 (%)', fontsize=11, color='#34495e')
                ax4.set_ylabel('概率密度', fontsize=11, color='#34495e')
                ax4.set_title('日收益率分布对比', fontsize=12, fontweight='bold', color='#2c3e50', pad=10)
                ax4.legend(loc='upper right', fontsize=9, framealpha=0.9)
                ax4.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
                ax4.axvline(x=0, color='#7f8c8d', linestyle='-', linewidth=0.8, alpha=0.5)
                ax4.tick_params(axis='both', labelsize=9, colors='#34495e')
                    
                # 调整子图间距
                plt.tight_layout(rect=[0, 0.02, 1, 0.95])
                plt.subplots_adjust(hspace=0.35, wspace=0.25)
                    
                # 转换为base64，使用更高DPI
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight', 
                           facecolor='#fafafa', edgecolor='none')
                buffer.seek(0)
                image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
                buffer.close()
                plt.close(fig)  # 释放内存
                    
                return image_base64
                    
            except Exception as e:
                logger.error(f"创建相关性图表失败: {str(e)}")
                import traceback
                logger.error(f"详细错误信息: {traceback.format_exc()}")
                return ""
        
    def _returns_to_nav_for_plot(self, returns: pd.Series) -> pd.Series:
        """
        将收益率序列转换为净值序列（用于图表绘制）
                
            参数:
            returns: 日收益率序列
                
            返回:
            pd.Series: 净值序列
        """
        # 从收益率重建净值序列
        nav = [100]  # 假设初始净值为100
        for ret in returns:
            new_nav = nav[-1] * (1 + ret / 100)
            nav.append(new_nav)
        return pd.Series(nav[:-1], index=returns.index)