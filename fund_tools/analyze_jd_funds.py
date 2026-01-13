# analyze_jd_funds.py
"""分析京东金融Excel文件中的基金组合相似度，基于净值收益率计算相关系数矩阵"""

import pandas as pd
from pathlib import Path
import xlsxwriter
from datetime import datetime, timedelta
from fund_correlation import FundCorrelation


def analyze_jd_fund_portfolio():
    """分析京东金融Excel文件中的基金组合，基于净值收益率计算相关系数矩阵"""
    
    # Excel文件路径
    excel_path = Path("京东金融.xlsx")
    
    if not excel_path.exists():
        print(f"❌ 文件不存在: {excel_path.absolute()}")
        return
    
    print("="*60)
    print("京东金融基金组合相关性分析")
    print("="*60)
    
    # 读取Excel文件
    try:
        print(f"\n📖 读取Excel文件: {excel_path}")
        持仓数据 = pd.read_excel(excel_path, sheet_name='持仓数据')
        
        print(f"✅ 成功读取数据")
        
        # 提取基金代码和名称
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
        
        # 设置时间范围（过去1年）
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        print(f"\n📅 时间范围: {start_date} 至 {end_date}")
        
        # 创建相关性分析器
        print("\n🔧 初始化相关性分析器...")
        correlation_analyzer = FundCorrelation(start_date=start_date, end_date=end_date)
        
        # 获取基金历史数据
        print("\n� 获取基金历史净值数据（这可能需要一些时间）...")
        if not correlation_analyzer.get_multiple_funds(fund_codes):
            return
        
        # 执行相关性分析 - 基于净值收益率
        print("\n🔍 执行基于净值收益率的相关性分析...")
        correlation_matrix = correlation_analyzer.calculate_correlation(method='pearson', based_on='returns')
        
        if correlation_matrix is None:
            print("❌ 分析失败，没有生成结果")
            return
        
        # 检查共同日期数量是否满足要求（至少4条）
        valid_fund_codes = list(correlation_matrix.columns)
        if not valid_fund_codes:
            print("❌ 没有有效的基金数据")
            return
        
        # 构建合并后的数据框来检查共同日期数量
        merged_df = None
        for code in valid_fund_codes:
            fund_data = correlation_analyzer.fund_data[code]
            if merged_df is None:
                merged_df = fund_data[['净值日期', '日收益率']].rename(columns={'日收益率': code})
            else:
                merged_df = merged_df.merge(fund_data[['净值日期', '日收益率']].rename(columns={'日收益率': code}), on='净值日期', how='inner')
        
        common_dates_count = len(merged_df)
        print(f"\n📊 共同日期数量: {common_dates_count} 条")
        
        if common_dates_count < 4:
            print(f"⚠️  共同日期数量不足4条，可能影响相关性分析结果")
        
        # 获取相关性矩阵
        holdings_matrix = correlation_matrix
        
        # 将列名和索引名替换为中文基金名称
        holdings_matrix.columns = [fund_names.get(code, code) for code in holdings_matrix.columns]
        holdings_matrix.index = [fund_names.get(code, code) for code in holdings_matrix.index]
        
        print("\n" + "="*60)
        print("相关性系数矩阵 (基于净值收益率)")
        print("="*60)
        print(holdings_matrix.round(4))
        
        # 将相关性系数矩阵保存到Excel文件
        print("\n💾 保存相关性系数矩阵到Excel文件...")
        output_dir = Path("output/jd_fund_analysis")
        output_dir.mkdir(parents=True, exist_ok=True)
        excel_file = output_dir / "相关性系数矩阵.xlsx"
        
        # 使用xlsxwriter创建Excel文件
        writer = pd.ExcelWriter(excel_file, engine='xlsxwriter')
        
        # 将数据写入Excel
        holdings_matrix.round(4).to_excel(writer, sheet_name='相似系数矩阵', index=True)
        
        # 获取工作簿和工作表对象
        workbook = writer.book
        worksheet = writer.sheets['相似系数矩阵']
        
        # 定义红色渐变色格式
        for row_idx in range(1, holdings_matrix.shape[0] + 2):
            for col_idx in range(1, holdings_matrix.shape[1] + 2):
                if row_idx == 1 or col_idx == 1:
                    # 表头和索引列使用默认格式
                    continue
                    
                # 获取单元格值
                value = holdings_matrix.iloc[row_idx - 2, col_idx - 2] if row_idx > 1 and col_idx > 1 else 0
                
                # 计算红色深浅，值越大红色越深
                intensity = int(value * 255)
                intensity = max(50, min(255, intensity))  # 确保最小值为50，避免黑色背景
                
                # 创建填充格式
                format_dict = {
                    'bg_color': f'#{intensity:02X}0000',  # 红色渐变
                    'font_color': '#FFFFFF' if intensity > 128 else '#000000',  # 根据背景色选择字体颜色
                    'align': 'center',
                    'valign': 'vcenter'
                }
                cell_format = workbook.add_format(format_dict)
                
                # 应用格式到单元格
                worksheet.write(row_idx - 1, col_idx - 1, round(value, 4), cell_format)
        
        # 设置列宽
        for col_idx in range(holdings_matrix.shape[1] + 1):
            worksheet.set_column(col_idx, col_idx, 12)
        
        # 设置行高
        for row_idx in range(holdings_matrix.shape[0] + 1):
            worksheet.set_row(row_idx, 30)
        
        # 关闭并保存文件
        writer.close()
        
        print(f"✅ 相关性系数矩阵已保存至: {excel_file.absolute()}")
        print(f"\n✅ 分析完成！")
        
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

