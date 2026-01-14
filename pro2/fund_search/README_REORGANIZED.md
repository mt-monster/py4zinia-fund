# 基金分析系统 - 重构后目录结构

## 概述

本项目已重新组织，将数据获取和回测功能分离到不同的模块中，提高了代码的可维护性和模块化程度。

## 目录结构

```
pro2/fund_search/
├── data_retrieval/              # 数据获取模块
│   ├── __init__.py
│   ├── enhanced_fund_data.py    # 增强版基金数据获取
│   ├── fund_realtime.py         # 实时基金数据
│   ├── enhanced_database.py     # 数据库管理
│   ├── enhanced_notification.py # 通知服务
│   ├── field_mapping.py         # 字段映射
│   └── check_table_structure.py # 表结构检查
├── backtesting/                 # 回测分析模块
│   ├── __init__.py
│   ├── backtest_engine.py       # 回测引擎
│   ├── strategy_backtest.py     # 策略回测
│   ├── backtest_search_01.py    # 搜索策略回测
│   ├── enhanced_strategy.py     # 增强版投资策略
│   ├── enhanced_analytics.py    # 绩效分析
│   └── fund_similarity.py       # 基金相似性分析
├── shared/                      # 共享配置模块
│   ├── __init__.py
│   ├── enhanced_config.py       # 增强版配置
│   └── config.py               # 基础配置
├── web/                        # Web 界面模块
│   ├── app.py                  # Flask 应用
│   ├── static/                 # 静态资源
│   ├── templates/              # HTML 模板
│   └── [测试文件...]
├── reports/                    # 报告输出目录
├── enhanced_main.py            # 主程序入口
├── main.py                     # 原始主程序
├── search_01.ipynb            # Jupyter 笔记本
├── test_*.py                   # 测试文件
└── README.md                   # 原始说明文档
```

## 模块说明

### 1. 数据获取模块 (data_retrieval/)

负责所有与数据获取相关的功能：

- **enhanced_fund_data.py**: 从 akshare 获取基金数据的核心类
- **fund_realtime.py**: 实时基金数据获取
- **enhanced_database.py**: 数据库连接和操作管理
- **enhanced_notification.py**: 邮件和推送通知服务
- **field_mapping.py**: 数据字段映射和转换
- **check_table_structure.py**: 数据库表结构验证

### 2. 回测分析模块 (backtesting/)

负责所有与回测和策略分析相关的功能：

- **backtest_engine.py**: 核心回测引擎，支持单基金和组合回测
- **strategy_backtest.py**: 使用投资策略进行回测
- **enhanced_strategy.py**: 增强版投资策略算法
- **enhanced_analytics.py**: 绩效指标计算和可视化
- **fund_similarity.py**: 基金相似性和聚类分析

### 3. 共享配置模块 (shared/)

包含系统的共享配置：

- **enhanced_config.py**: 数据库、通知、图表等配置
- **config.py**: 基础系统配置

### 4. Web 界面模块 (web/)

提供 Web 界面和 API：

- **app.py**: Flask 应用主文件
- **templates/**: HTML 模板文件
- **static/**: CSS、JavaScript 等静态资源
- 各种测试和验证文件

## 使用方法

### 1. 数据获取

```python
from data_retrieval import EnhancedFundData, FundRealTime

# 获取基金数据
fund_data = EnhancedFundData()
basic_info = fund_data.get_fund_basic_info('000001')

# 获取实时数据
realtime = FundRealTime()
nav_data = realtime.get_realtime_nav('000001')
```

### 2. 回测分析

```python
from backtesting import FundBacktest, EnhancedInvestmentStrategy

# 创建回测引擎
backtest = FundBacktest(base_amount=100, start_date='2020-01-01')

# 执行单基金回测
result = backtest.backtest_single_fund('000001')

# 使用投资策略
strategy = EnhancedInvestmentStrategy()
advice = strategy.analyze_strategy(today_return=0.02, prev_day_return=0.01)
```

### 3. Web 应用

```bash
cd web/
python app.py
```

然后访问 http://localhost:5000

## 配置

所有配置文件位于 `shared/` 目录中：

- 数据库配置：`DATABASE_CONFIG`
- 通知配置：`NOTIFICATION_CONFIG`
- 图表配置：`CHART_CONFIG`

## 依赖关系

- **data_retrieval** 模块相对独立，主要依赖 akshare 和数据库
- **backtesting** 模块依赖 data_retrieval 模块获取数据
- **web** 模块使用两个模块的功能提供界面
- **shared** 模块被所有其他模块使用

## 迁移说明

如果你有使用旧结构的代码，需要更新导入语句：

```python
# 旧的导入方式
from enhanced_fund_data import EnhancedFundData
from enhanced_strategy import EnhancedInvestmentStrategy

# 新的导入方式
from data_retrieval.enhanced_fund_data import EnhancedFundData
from backtesting.enhanced_strategy import EnhancedInvestmentStrategy
```

## 优势

1. **模块化**: 清晰的功能分离，便于维护和扩展
2. **可重用性**: 各模块可独立使用
3. **可测试性**: 每个模块可单独测试
4. **可扩展性**: 新功能可以轻松添加到相应模块
5. **依赖管理**: 清晰的依赖关系，避免循环依赖

## 注意事项

- 确保 Python 路径包含项目根目录
- 数据库配置需要在 `shared/enhanced_config.py` 中正确设置
- Web 应用需要安装 Flask 相关依赖
- 回测功能需要足够的历史数据支持