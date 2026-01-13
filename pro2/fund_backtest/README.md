# 基金组合回测系统

## 系统功能

1. **基金筛选**：从 akshare 数据接口获取每日加仓前二十的基金
2. **相似性分析**：分析基金间的相似性，选择低相关性基金构建组合
3. **回测分析**：应用投资策略进行回测，分析绩效表现

## 文件结构

```
new_fund_backtest_system/
├── fund_top_picker.py      # 基金筛选模块
├── fund_similarity.py       # 相似性分析模块
├── backtest_engine.py       # 回测引擎模块
├── top_funds_backtest.py    # 整合回测流程
├── main.py                  # 主程序入口
└── README.md                # 系统说明
```

## 核心功能模块

### 1. 基金筛选模块 (fund_top_picker.py)
- 从 akshare 获取基金排名数据
- 按日增长率筛选前20名基金
- 支持不同基金类型的筛选

### 2. 相似性分析模块 (fund_similarity.py)
- 计算基金间的相关性矩阵
- 使用 K-means 聚类分析基金相似性
- 构建低相关性基金组合

### 3. 回测引擎模块 (backtest_engine.py)
- 实现基金组合回测功能
- 计算多种绩效指标：总收益率、年化收益率、最大回撤、夏普比率等
- 生成可视化分析结果

### 4. 整合回测流程 (top_funds_backtest.py)
- 整合基金筛选、相似性分析和回测功能
- 支持不同的组合构建方法
- 提供完整的回测流程

### 5. 主程序入口 (main.py)
- 命令行参数配置
- 执行完整回测流程
- 输出回测结果和分析报告

## 使用方法

### 基本使用

```bash
# 在 new_fund_backtest_system 目录下执行
python main.py --top-n 20 --rank-type daily --portfolio-method diversified
```

### 参数说明

- `--top-n`：筛选的基金数量，默认20
- `--rank-type`：排名类型，可选值为 daily、weekly、monthly，默认 daily
- `--portfolio-method`：组合构建方法，可选值为 diversified、low_corr，默认 diversified
- `--start-date`：回测开始日期，默认 2023-01-01
- `--end-date`：回测结束日期，默认当前日期
- `--investment-amount`：每期投资金额，默认 1000
- `--investment-frequency`：投资频率，可选值为 daily、weekly、monthly，默认 monthly

## 依赖包

- akshare：获取基金数据
- pandas：数据处理
- numpy：数值计算
- matplotlib：数据可视化
- scikit-learn：聚类分析
- tqdm：进度条显示

## 回测结果

回测完成后，系统会生成以下结果：

1. **回测结果文件**：top_funds_backtest_result.csv
2. **绩效指标文件**：top_funds_performance_metrics.csv
3. **可视化图表**：资产趋势图、日收益率对比图、绩效指标柱状图

## 注意事项

1. 系统使用 akshare 接口获取基金数据，需要确保网络连接正常
2. 首次运行时，数据获取可能较慢，请耐心等待
3. 回测结果仅供参考，不构成投资建议
4. 系统支持的基金类型和筛选条件可能会根据 akshare 接口的更新而变化
