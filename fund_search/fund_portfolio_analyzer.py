# fund_portfolio_analyzer.py
"""
基金投资组合相似度分析工具
基于AKShare数据源，提供多维度持仓相似度分析和组合优化建议
"""

import akshare as ak
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
import logging
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

# =========================================
# 配置与日志
# =========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fund_analysis.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

@dataclass
class AnalysisConfig:
    """分析配置参数"""
    base_amount: float = 1000.0
    top_n_holdings: int = 50  # 重仓股数量
    similarity_threshold: float = 0.6  # 相似度预警阈值
    min_samples: int = 30  # 最小样本数
    correlation_methods: List[str] = None
    
    def __post_init__(self):
        if self.correlation_methods is None:
            self.correlation_methods = ['pearson', 'spearman']

# =========================================
# 数据获取模块
# =========================================
class FundDataFetcher:
    """基金数据获取器"""
    
    def __init__(self):
        self.holdings_cache: Dict[str, pd.DataFrame] = {}
        self.stock_info_cache: Dict[str, Dict] = {}
        
    def get_fund_holdings(self, fund_code: str, date: Optional[str] = None) -> pd.DataFrame:
        """
        获取基金持仓数据（带缓存）
        
        Args:
            fund_code: 基金代码，如'005827'
            date: 报告期，如'2024-12-31'，None则自动获取最新
            
        Returns:
            DataFrame: 持仓数据，包含股票代码、名称、占比等
        """
        cache_key = f"{fund_code}_{date}"
        if cache_key in self.holdings_cache:
            logging.info(f"从缓存读取 {fund_code} 持仓数据")
            return self.holdings_cache[cache_key]
        
        try:
            df = ak.fund_portfolio_hold_em(symbol=fund_code)
            
            if df.empty:
                logging.warning(f"基金 {fund_code} 无持仓数据")
                return pd.DataFrame()
            
            # 数据清洗
            df['占净值比例'] = pd.to_numeric(df['占净值比例'], errors='coerce')
            df['持股数'] = pd.to_numeric(df['持股数'], errors='coerce')
            df['持仓市值'] = pd.to_numeric(df['持仓市值'], errors='coerce')
            df['季度'] = pd.to_datetime(df['报告期'])
            
            # 按日期筛选
            if date:
                df = df[df['报告期'] == date]
            
            # 获取最新报告期
            latest_date = df['报告期'].max()
            holdings = df[df['报告期'] == latest_date].copy()
            
            # 缓存数据
            self.holdings_cache[cache_key] = holdings
            logging.info(f"✅ 成功获取 {fund_code} 数据：{len(holdings)} 只重仓股，报告期 {latest_date}")
            
            return holdings
            
        except Exception as e:
            logging.error(f"❌ 获取 {fund_code} 数据失败: {e}")
            return pd.DataFrame()
    
    def get_stock_industry(self, stock_code: str) -> str:
        """
        获取股票所属行业（带缓存）
        
        Args:
            stock_code: 股票代码，如'000858'
            
        Returns:
            str: 行业名称
        """
        if stock_code in self.stock_info_cache:
            return self.stock_info_cache[stock_code].get('industry', '未知行业')
        
        try:
            info = ak.stock_individual_info_em(symbol=stock_code)
            industry = info[info['item'] == '行业']['value'].iloc[0] if not info.empty else '未知行业'
            
            self.stock_info_cache[stock_code] = {'industry': industry}
            return industry
        except:
            self.stock_info_cache[stock_code] = {'industry': '未知行业'}
            return '未知行业'
    
    def get_stock_factors(self, stock_code: str) -> Dict[str, float]:
        """
        获取股票风险因子数据（示例：市值、估值）
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Dict: 因子字典
        """
        try:
            # 实际项目中需要调用更多接口获取真实数据
            # 这里使用占位符逻辑
            info = ak.stock_individual_info_em(symbol=stock_code)
            
            # 从返回信息中提取所需因子（实际需扩展）
            market_cap = 1000  # 需要调用 ak.stock_individual_fund_flow() 等接口
            pe_ratio = 15.0
            
            return {
                'market_cap': market_cap,
                'pe_ratio': pe_ratio,
                'pb_ratio': 2.0,
                'roe': 0.15
            }
        except:
            logging.warning(f"无法获取 {stock_code} 因子数据")
            return {'market_cap': 0, 'pe_ratio': 0, 'pb_ratio': 0, 'roe': 0}

# =========================================
# 相似度计算模块
# =========================================
class SimilarityCalculator:
    """相似度计算器"""
    
    @staticmethod
    def holdings_overlap_similarity(holdings_dict: Dict[str, pd.DataFrame], 
                                   top_n: int = 50) -> pd.DataFrame:
        """
        重仓股重合度相似度（Jaccard系数）
        
        Args:
            holdings_dict: 基金持仓字典
            top_n: 取前N大重仓股
            
        Returns:
            DataFrame: 相似度矩阵
        """
        # 提取前N大重仓股
        top_holdings = {}
        for fund, df in holdings_dict.items():
            if not df.empty:
                top_holdings[fund] = set(df.head(top_n)['股票代码'].tolist())
            else:
                top_holdings[fund] = set()
        
        # 计算相似度矩阵
        funds = list(holdings_dict.keys())
        matrix = pd.DataFrame(index=funds, columns=funds, dtype=float)
        
        for i, fund1 in enumerate(funds):
            for j, fund2 in enumerate(funds):
                if i == j:
                    matrix.loc[fund1, fund2] = 1.0
                else:
                    set1, set2 = top_holdings[fund1], top_holdings[fund2]
                    if not set1 or not set2:
                        matrix.loc[fund1, fund2] = 0.0
                    else:
                        intersection = len(set1 & set2)
                        union = len(set1 | set2)
                        matrix.loc[fund1, fund2] = intersection / union
        
        return matrix
    
    @staticmethod
    def industry_similarity(holdings_dict: Dict[str, pd.DataFrame],
                           data_fetcher: FundDataFetcher) -> pd.DataFrame:
        """
        行业配置相似度（基于持仓权重）
        
        Args:
            holdings_dict: 基金持仓字典
            data_fetcher: 数据获取器实例
            
        Returns:
            DataFrame: 相似度矩阵
        """
        # 为每个持仓添加行业信息
        industry_weights = {}
        
        for fund, df in holdings_dict.items():
            if df.empty:
                industry_weights[fund] = pd.Series(dtype=float)
                continue
            
            # 添加行业信息
            df = df.copy()
            df['行业分类'] = df['股票代码'].apply(data_fetcher.get_stock_industry)
            
            # 按行业汇总权重（占净值比例）
            industry_weight = df.groupby('行业分类')['占净值比例'].sum()
            industry_weights[fund] = industry_weight
        
        # 统一索引
        all_industries = set()
        for weights in industry_weights.values():
            all_industries.update(weights.index)
        all_industries = sorted(list(all_industries))
        
        # 构建DataFrame
        industry_df = pd.DataFrame(index=all_industries)
        for fund, weights in industry_weights.items():
            industry_df[fund] = weights.reindex(all_industries).fillna(0)
        
        # 计算余弦相似度
        from sklearn.metrics.pairwise import cosine_similarity
        similarity_matrix = cosine_similarity(industry_df.T)
        
        return pd.DataFrame(similarity_matrix, index=industry_df.columns, columns=industry_df.columns)
    
    @staticmethod
    def composite_similarity(holdings_dict: Dict[str, pd.DataFrame],
                            weights: Dict[str, float],
                            data_fetcher: FundDataFetcher) -> pd.DataFrame:
        """
        综合相似度（多维度加权）
        
        Args:
            holdings_dict: 基金持仓字典
            weights: 各维度权重，如{'holdings':0.6, 'industry':0.3, 'factor':0.2}
            data_fetcher: 数据获取器实例
            
        Returns:
            DataFrame: 加权综合相似度矩阵
        """
        calculators = {
            'holdings': SimilarityCalculator.holdings_overlap_similarity,
            'industry': SimilarityCalculator.industry_similarity,
        }
        
        # 计算各维度相似度
        similarities = {}
        for name, weight in weights.items():
            if weight > 0:
                if name == 'holdings':
                    similarities[name] = calculators[name](holdings_dict)
                else:
                    similarities[name] = calculators[name](holdings_dict, data_fetcher)
        
        # 加权融合
        funds = list(holdings_dict.keys())
        composite_matrix = pd.DataFrame(0.0, index=funds, columns=funds)
        
        for name, matrix in similarities.items():
            composite_matrix += weights[name] * matrix
        
        return composite_matrix

# =========================================
# 主分析器类
# =========================================
class FundPortfolioAnalyzer:
    """基金投资组合相似度分析器"""
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        self.config = config or AnalysisConfig()
        self.fetcher = FundDataFetcher()
        self.holdings_dict: Dict[str, pd.DataFrame] = {}
        self.similarity_results: Dict[str, pd.DataFrame] = {}
        self.fund_names: Dict[str, str] = {}
        
    def add_fund(self, fund_code: str, fund_name: Optional[str] = None):
        """添加基金到分析池"""
        logging.info(f"添加基金 {fund_code} 到分析池")
        self.fund_names[fund_code] = fund_name or fund_code
        
    def load_holdings(self, target_date: Optional[str] = None):
        """加载所有基金的持仓数据"""
        logging.info(f"开始加载 {len(self.fund_names)} 只基金的持仓数据...")
        
        for fund_code in self.fund_names.keys():
            holdings = self.fetcher.get_fund_holdings(fund_code, target_date)
            self.holdings_dict[fund_code] = holdings
        
        valid_funds = len([h for h in self.holdings_dict.values() if not h.empty])
        logging.info(f"成功加载 {valid_funds} 只基金的有效数据")
        
        if valid_funds < len(self.fund_names):
            missing = [code for code, df in self.holdings_dict.items() if df.empty]
            logging.warning(f"以下基金数据缺失: {missing}")
    
    def run_analysis(self, methods: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        执行相似度分析
        
        Args:
            methods: 分析方法列表，可选['holdings', 'industry', 'composite']
            
        Returns:
            Dict: 分析结果字典
        """
        if methods is None:
            methods = ['holdings', 'industry']
        
        logging.info(f"开始执行相似度分析，方法: {methods}")
        
        calculator = SimilarityCalculator()
        valid_methods = []
        
        for method in methods:
            try:
                if method == 'holdings':
                    result = calculator.holdings_overlap_similarity(
                        self.holdings_dict, 
                        top_n=self.config.top_n_holdings
                    )
                elif method == 'industry':
                    result = calculator.industry_similarity(self.holdings_dict, self.fetcher)
                elif method == 'composite':
                    weights = {'holdings': 0.6, 'industry': 0.4}
                    result = calculator.composite_similarity(self.holdings_dict, weights, self.fetcher)
                else:
                    logging.warning(f"不支持的相似度方法: {method}")
                    continue
                
                self.similarity_results[method] = result
                valid_methods.append(method)
                logging.info(f"✅ {method} 相似度计算完成")
                
            except Exception as e:
                logging.error(f"❌ {method} 相似度计算失败: {e}")
        
        return {k: v for k, v in self.similarity_results.items() if k in valid_methods}
    
    def visualize(self, method: str = 'all', save_path: Optional[str] = None):
        """
        可视化相似度矩阵
        
        Args:
            method: 'all'表示显示所有，或指定特定方法名
            save_path: 保存路径，None则直接显示
        """
        if method == 'all':
            methods_to_plot = list(self.similarity_results.keys())
        else:
            methods_to_plot = [method] if method in self.similarity_results else []
        
        if not methods_to_plot:
            logging.warning("没有可用的相似度结果进行可视化")
            return
        
        for method_name in methods_to_plot:
            matrix = self.similarity_results[method_name]
            
            plt.figure(figsize=(12, 10))
            mask = np.triu(np.ones_like(matrix, dtype=bool))
            
            # 生成带基金名称的标签
            labels = [f"{code}\n{self.fund_names.get(code, '')}" for code in matrix.columns]
            
            sns.heatmap(
                matrix,
                mask=mask,
                annot=True,
                cmap='RdYlBu_r',
                center=0.5,
                linewidths=0.5,
                cbar_kws={"shrink": 0.8},
                fmt='.3f',
                xticklabels=labels,
                yticklabels=labels,
                square=True
            )
            
            plt.title(f'基金持仓相似度分析 ({method_name})', fontsize=16, fontweight='bold', pad=20)
            plt.tight_layout()
            
            if save_path:
                output_path = Path(save_path) / f"similarity_{method_name}.png"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                logging.info(f"图表已保存至 {output_path}")
            else:
                plt.show()
            
            plt.close()
    
    def generate_report(self, threshold: Optional[float] = None) -> str:
        """
        生成分析报告
        
        Args:
            threshold: 相似度阈值，None则使用配置值
            
        Returns:
            str: 分析报告文本
        """
        if threshold is None:
            threshold = self.config.similarity_threshold
        
        if not self.similarity_results:
            return "尚未运行相似度分析"
        
        report = []
        report.append("="*60)
        report.append("基金投资组合相似度分析报告")
        report.append("="*60)
        report.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"基金数量: {len(self.fund_names)}")
        report.append(f"相似度阈值: {threshold:.1%}")
        report.append("-"*60)
        
        # 统计持仓数据质量
        valid_funds = [code for code, df in self.holdings_dict.items() if not df.empty]
        report.append(f"有效数据基金: {len(valid_funds)}/{len(self.fund_names)}")
        
        if len(valid_funds) < len(self.fund_names):
            missing = [code for code, df in self.holdings_dict.items() if df.empty]
            report.append(f"数据缺失基金: {missing}")
        report.append("-"*60)
        
        # 使用composite或第一个可用结果
        primary_method = 'composite' if 'composite' in self.similarity_results else list(self.similarity_results.keys())[0]
        similarity_matrix = self.similarity_results[primary_method]
        
        # 统计相似度分布
        sim_values = []
        funds = similarity_matrix.index.tolist()
        
        for i in range(len(funds)):
            for j in range(i+1, len(funds)):
                sim_values.append(similarity_matrix.iloc[i, j])
        
        if sim_values:
            report.append(f"\n相似度统计:")
            report.append(f"  平均值: {np.mean(sim_values):.2%}")
            report.append(f"  中位数: {np.median(sim_values):.2%}")
            report.append(f"  最大值: {np.max(sim_values):.2%}")
            report.append(f"  最小值: {np.min(sim_values):.2%}")
        
        # 找出高相似度基金对
        high_similarity_pairs = []
        for i in range(len(funds)):
            for j in range(i+1, len(funds)):
                sim_value = similarity_matrix.iloc[i, j]
                if sim_value > threshold:
                    high_similarity_pairs.append((funds[i], funds[j], sim_value))
        
        # 按相似度排序
        high_similarity_pairs.sort(key=lambda x: x[2], reverse=True)
        
        if high_similarity_pairs:
            report.append(f"\n⚠️ 高相似度基金对（建议优化）：")
            for fund1, fund2, sim in high_similarity_pairs:
                name1 = self.fund_names.get(fund1, fund1)
                name2 = self.fund_names.get(fund2, fund2)
                report.append(f"  {fund1}({name1}) - {fund2}({name2}): {sim:.2%}")
        else:
            report.append(f"\n✅ 未发现相似度 > {threshold:.1%} 的基金对，组合分散性良好")
        
        # 方法说明
        report.append("\n" + "-"*60)
        report.append("方法说明:")
        for method in self.similarity_results.keys():
            if method == 'holdings':
                report.append("  - holdings: 基于前50大重仓股的重合度（Jaccard相似度）")
            elif method == 'industry':
                report.append("  - industry: 基于行业配置权重的余弦相似度")
            elif method == 'composite':
                report.append("  - composite: 重仓股(60%) + 行业(40%)的综合相似度")
        
        report.append("="*60)
        
        return "\n".join(report)
    
    def save_results(self, output_dir: str = "./output"):
        """保存所有分析结果"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 保存相似度矩阵
        for method, matrix in self.similarity_results.items():
            csv_path = output_path / f"similarity_matrix_{method}.csv"
            matrix.to_csv(csv_path, encoding='utf-8-sig', float_format='%.4f')
            logging.info(f"相似度矩阵已保存至 {csv_path}")
        
        # 保存持仓数据
        for fund, holdings in self.holdings_dict.items():
            if not holdings.empty:
                csv_path = output_path / f"holdings_{fund}.csv"
                holdings.to_csv(csv_path, encoding='utf-8-sig', index=False)
                logging.info(f"持仓数据已保存至 {csv_path}")
        
        # 保存分析报告
        report_path = output_path / "analysis_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_report())
        logging.info(f"分析报告已保存至 {report_path}")
        
        print(f"\n📁 所有结果已保存至: {output_path.absolute()}")

# =========================================
# 示例与测试
# =========================================
def run_demo():
    """运行演示示例"""
    print("🚀 基金投资组合相似度分析工具")
    print("="*60)
    
    # 配置
    config = AnalysisConfig(
        top_n_holdings=50,
        similarity_threshold=0.5
    )
    
    # 创建分析器
    analyzer = FundPortfolioAnalyzer(config)
    
    # 添加基金（热门主动管理型基金示例）
    funds = {
        '005827': '易方达蓝筹精选',
        '161725': '招商中证白酒指数',
        '003095': '中欧医疗健康混合A',
        '110022': '易方达消费行业',
        '000001': '华夏成长混合',
        '000011': '华夏大盘精选',
    }
    
    for code, name in funds.items():
        analyzer.add_fund(code, name)
    
    # 加载数据
    print("\n📊 步骤1: 加载基金持仓数据...")
    analyzer.load_holdings()
    
    # 执行分析
    print("\n🔍 步骤2: 执行多维度相似度分析...")
    methods = ['holdings', 'industry', 'composite']
    results = analyzer.run_analysis(methods=methods)
    
    if not results:
        print("❌ 没有成功获取到任何基金的有效持仓数据，请检查基金代码或网络连接")
        return
    
    # 可视化
    print("\n📈 步骤3: 生成可视化图表...")
    analyzer.visualize(save_path="./output")
    
    # 生成报告
    print("\n📝 步骤4: 生成分析报告...")
    report = analyzer.generate_report()
    print(report)
    
    # 保存结果
    print("\n💾 步骤5: 保存分析结果...")
    analyzer.save_results("./output")
    
    print("\n✅ 分析完成！请查看 output 目录下的结果文件。")

if __name__ == "__main__":
    run_demo()
