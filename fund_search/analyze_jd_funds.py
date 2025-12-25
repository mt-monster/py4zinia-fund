# analyze_jd_funds.py
"""分析京东金融Excel文件中的基金组合相似度"""

import pandas as pd
from pathlib import Path
from fund_portfolio_analyzer import FundPortfolioAnalyzer, AnalysisConfig
import sys

def analyze_jd_fund_portfolio():
    """分析京东金融Excel文件中的基金组合"""
    
    # Excel文件路径
    excel_path = Path("京东金融.xlsx")
    
    if not excel_path.exists():
        print(f"❌ 文件不存在: {excel_path.absolute()}")
        return
    
    print("="*60)
    print("京东金融基金组合相似度分析")
    print("="*60)
    
    # 读取Excel文件
    try:
        print(f"\n📖 读取Excel文件: {excel_path}")
        持仓数据 = pd.read_excel(excel_path, sheet_name='持仓数据')
        
        print(f"✅ 成功读取数据")
        print(f"数据形状: {持仓数据.shape[0]} 行 x {持仓数据.shape[1]} 列")
        print(f"列名: {list(持仓数据.columns)}")
        
        # 提取基金代码和名称
        # 检查可能的列名
        code_col = None
        name_col = None
        
        for col in 持仓数据.columns:
            col_lower = str(col).lower()
            if '代码' in col_lower or 'code' in col_lower:
                code_col = col
            if '名称' in col_lower or 'name' in col_lower or '基金名称' in col_lower:
                name_col = col
        
        if code_col is None:
            print("\n❌ 未找到基金代码列，请检查Excel文件格式")
            print("可用的列:", list(持仓数据.columns))
            return
        
        # 提取基金代码
        fund_codes = 持仓数据[code_col].astype(str).tolist()
        fund_codes = [code.strip().zfill(6) for code in fund_codes if pd.notna(code)]  # 确保6位数字
        
        # 提取基金名称（如果有）
        fund_names = {}
        if name_col:
            for idx, row in 持仓数据.iterrows():
                code = str(row[code_col]).strip().zfill(6)
                if pd.notna(row[name_col]):
                    fund_names[code] = str(row[name_col]).strip()
        
        print(f"\n📊 找到 {len(fund_codes)} 只基金")
        print(f"基金代码列表: {fund_codes[:10]}{'...' if len(fund_codes) > 10 else ''}")
        
        if len(fund_codes) == 0:
            print("❌ 未找到有效的基金代码")
            return
        
        # 创建分析器
        print("\n🔧 初始化分析器...")
        config = AnalysisConfig(
            top_n_holdings=50,
            similarity_threshold=0.5  # 50%相似度阈值
        )
        analyzer = FundPortfolioAnalyzer(config)
        
        # 添加基金到分析池
        print("\n📝 添加基金到分析池...")
        for code in fund_codes:
            name = fund_names.get(code, code)
            analyzer.add_fund(code, name)
        
        # 加载持仓数据
        print("\n📥 加载基金持仓数据（这可能需要一些时间）...")
        analyzer.load_holdings()
        
        # 检查是否有有效数据
        valid_funds = [code for code, df in analyzer.holdings_dict.items() if not df.empty]
        if len(valid_funds) == 0:
            print("\n❌ 未能获取到任何基金的有效持仓数据")
            print("可能的原因：")
            print("  1. 基金代码不正确")
            print("  2. 网络连接问题")
            print("  3. AKShare接口暂时不可用")
            return
        
        print(f"\n✅ 成功获取 {len(valid_funds)}/{len(fund_codes)} 只基金的有效数据")
        
        if len(valid_funds) < len(fund_codes):
            missing = [code for code in fund_codes if code not in valid_funds]
            print(f"⚠️  以下基金数据缺失: {missing}")
        
        # 执行分析
        print("\n🔍 执行相似度分析...")
        methods = ['holdings', 'industry', 'composite']
        results = analyzer.run_analysis(methods=methods)
        
        if not results:
            print("❌ 分析失败，没有生成结果")
            return
        
        # 生成可视化
        print("\n📈 生成可视化图表...")
        output_dir = Path("output/jd_fund_analysis")
        output_dir.mkdir(parents=True, exist_ok=True)
        analyzer.visualize(save_path=str(output_dir))
        
        # 生成报告
        print("\n📝 生成分析报告...")
        report = analyzer.generate_report()
        print(report)
        
        # 保存结果
        print("\n💾 保存分析结果...")
        analyzer.save_results(str(output_dir))
        
        print(f"\n✅ 分析完成！结果已保存至: {output_dir.absolute()}")
        
        # 生成简要总结
        print("\n" + "="*60)
        print("简要总结")
        print("="*60)
        
        if 'composite' in results:
            matrix = results['composite']
            funds = matrix.index.tolist()
            
            # 找出高相似度基金对
            high_sim_pairs = []
            for i in range(len(funds)):
                for j in range(i+1, len(funds)):
                    sim = matrix.iloc[i, j]
                    if sim > 0.5:
                        high_sim_pairs.append((funds[i], funds[j], sim))
            
            high_sim_pairs.sort(key=lambda x: x[2], reverse=True)
            
            if high_sim_pairs:
                print("\n⚠️  高相似度基金对（建议优化组合）:")
                for fund1, fund2, sim in high_sim_pairs[:10]:  # 只显示前10个
                    name1 = analyzer.fund_names.get(fund1, fund1)
                    name2 = analyzer.fund_names.get(fund2, fund2)
                    print(f"  {fund1}({name1}) ↔ {fund2}({name2}): {sim:.2%}")
            else:
                print("\n✅ 未发现相似度 > 50% 的基金对，组合分散性良好")
        
    except FileNotFoundError:
        print(f"❌ 文件不存在: {excel_path.absolute()}")
    except ValueError as e:
        if "Worksheet named" in str(e):
            print(f"❌ Excel文件中未找到'持仓数据'工作表")
            print("请检查Excel文件，确保存在名为'持仓数据'的工作表")
        else:
            print(f"❌ 读取Excel文件时出错: {e}")
    except Exception as e:
        print(f"❌ 分析过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_jd_fund_portfolio()

