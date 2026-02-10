# CODEBUDDY.md This file provides guidance to CodeBuddy when working with code in this repository.

## 项目概述

这是一个综合性的**基金投资分析平台**，整合了多种分析工具和策略。项目实现了基金数据获取、策略回测、实时分析和Web可视化等功能。

## 常用命令

### 启动应用
```bash
# 启动Web应用（Flask服务器）
python d:/codes/py4zinia/pro2/fund_search/web/app.py
# Web界面访问地址: http://localhost:5000

# 运行主分析程序
python d:/codes/py4zinia/pro2/fund_search/enhanced_main.py --analyze

# 运行策略对比分析
python d:/codes/py4zinia/pro2/fund_search/enhanced_main.py --strategy-analysis
```

### 测试

```bash
# 使用Makefile运行测试（在pro2目录下）
cd pro2
make test              # 运行所有测试
make test-unit         # 运行单元测试
make test-integration  # 运行集成测试
make coverage          # 生成覆盖率报告

# 直接使用pytest
pytest tests/ -v                                    # 运行所有测试
pytest tests/unit -v                                # 单元测试
pytest tests/integration -v                         # 集成测试
pytest tests/ -v --cov=fund_search --cov-report=html  # 覆盖率测试
```

### CI/CD

```bash
# 本地CI流程（在pro2目录下）
powershell -ExecutionPolicy Bypass -File ci-cd/local-ci.ps1        # 完整CI流程
powershell -ExecutionPolicy Bypass -File ci-cd/local-ci.ps1 -Quick # 快速模式（仅单元测试）
make ci                                                             # 使用Makefile运行CI

# 部署
powershell -ExecutionPolicy Bypass -File ci-cd/deploy.ps1 -Environment local      # 本地部署
powershell -ExecutionPolicy Bypass -File ci-cd/deploy.ps1 -Environment production # 生产部署
make deploy-local                                                                  # Makefile本地部署
```

### 依赖管理

```bash
# 安装依赖
pip install -r requirements.txt                           # 项目依赖
pip install -r pro2/requirements.txt                      # pro2模块依赖
pip install pytest pytest-cov pytest-html pytest-mock    # 测试依赖

# 升级核心包（如遇到setuptools问题）
python -m pip install --upgrade pip
python -m pip install --upgrade setuptools
```

### 代码质量

```bash
cd pro2
make lint          # 代码检查（flake8 + pylint）
make format        # 代码格式化（black + isort）
make clean         # 清理临时文件
```

## 代码架构

### 顶层结构

项目采用双层目录结构：
- **根目录 (`d:/codes/py4zinia/`)**: 包含CI/CD配置、Docker配置、顶层依赖文件
- **pro2 目录**: 实际的项目代码库，包含所有功能模块

### 核心模块 (`pro2/fund_search/`)

#### 1. **Web应用层** (`web/`)
- **`app.py`**: Flask应用主入口，初始化所有服务组件，注册路由
- **`routes/`**: 按功能拆分的路由模块
  - `funds.py`: 基金基础数据API
  - `holdings.py`: 持仓管理
  - `analysis.py`: 分析功能
  - `backtest.py`: 回测接口
  - `strategies.py`: 策略管理
  - `dashboard.py`: 仪表板数据
  - `etf.py`: ETF相关功能
- **`templates/`**: HTML模板（Jinja2）
- **`static/`**: 静态资源（JS/CSS）

#### 2. **数据获取层** (`data_retrieval/`)
- **`multi_source_adapter.py`**: 多数据源适配器，统一数据接口
- **`enhanced_database.py`**: 数据库管理（MySQL），处理持久化
- **`enhanced_fund_parser.py`**: 基金数据解析
- **`heavyweight_stocks_fetcher.py`**: 重仓股数据获取
- **`fund_screenshot_ocr.py`**: OCR识别基金截图
- **数据源优先级**: Tushare (主) → Akshare (备1) → Sina/Eastmoney (备2)

#### 3. **回测引擎层** (`backtesting/`)
- **策略实现** (`advanced_strategies.py`):
  - `DualMAStrategy`: 双均线动量策略
  - `MeanReversionStrategy`: 均值回归策略
  - `TargetValueStrategy`: 目标市值策略
  - `GridTradingStrategy`: 网格交易策略
- **`unified_strategy_engine.py`**: 统一策略引擎，整合所有策略逻辑
- **`backtest_engine.py`**: 回测执行引擎
- **`strategy_evaluator.py`**: 策略评估器
- **`enhanced_analytics.py`**: 增强的分析功能（风险指标、绩效归因）
- **`enhanced_engine/`**: 高级回测引擎子模块

#### 4. **业务服务层** (`services/`)
- **`fund_type_service.py`**: 基金分类服务
- **缓存服务** (如已启用):
  - `FundNavCacheManager`: 净值缓存管理
  - `HoldingRealtimeService`: 持仓实时服务
  - `FundDataSyncService`: 数据同步服务

#### 5. **配置层** (`shared/`)
- **`enhanced_config.py`**: 统一配置管理
  - `BASE_CONFIG`: 基础配置（文件路径、列映射）
  - `DATABASE_CONFIG`: 数据库连接配置
  - `DATA_SOURCE_CONFIG`: 数据源配置和优先级
  - `NOTIFICATION_CONFIG`: 通知配置

### 策略对比模块 (`pro2/fund_backtest/`)

独立的策略对比分析系统：
- **`complete_strategy_analyzer.py`**: 完整策略分析器
- **`strategy_comparison_engine.py`**: 策略对比引擎
- **`strategy_ranking_system.py`**: 策略排名系统
- **`strategy_advice_report_generator.py`**: 报告生成器

### 主程序入口

- **`pro2/fund_search/enhanced_main.py`**: 命令行分析工具主入口
  - 初始化 `EnhancedFundAnalysisSystem` 类
  - 支持多种命令行参数（`--analyze`, `--strategy-analysis`, `--all`）
  - 整合所有分析引擎和数据源

### 数据流程

1. **数据获取**: `MultiSourceDataAdapter` → 多数据源（Tushare/Akshare等）
2. **数据存储**: `EnhancedDatabaseManager` → MySQL数据库
3. **策略分析**: `UnifiedStrategyEngine` + `EnhancedInvestmentStrategy` → 策略信号
4. **回测执行**: `BacktestEngine` → 历史数据模拟
5. **结果展示**: `Web API` → 前端界面 / `enhanced_main.py` → 报告文件

### 测试结构 (`pro2/tests/`)

- **`unit/`**: 单元测试（不依赖外部服务）
- **`integration/`**: 集成测试（测试组件交互、数据库、API）
- **`conftest.py`**: pytest共享配置和fixture
- **`pytest.ini`**: pytest配置文件，定义测试标记和选项

### CI/CD配置

#### Jenkins (`Jenkinsfile`)
- 使用 Docker (Python 3.9-slim)
- 阶段: Install → Unit Tests → Integration Tests → All Tests → Build
- 自动发布测试报告和覆盖率

#### 本地CI (`pro2/ci-cd/`)
- **`local-ci.ps1`**: PowerShell CI脚本
- **`deploy.ps1`**: 部署脚本（支持 local/staging/production）
- **`run-tests.ps1`**: 测试执行脚本

### 数据库设计

使用 MySQL 8.0，主要表包括：
- 基金基础信息表
- 净值历史表
- 持仓记录表
- 策略配置表
- 回测结果表

数据库连接通过 `DATABASE_CONFIG` 配置，支持环境变量覆盖。

### 关键设计模式

1. **适配器模式**: `MultiSourceDataAdapter` 统一多数据源接口
2. **策略模式**: `BaseStrategy` 抽象基类，各策略独立实现
3. **工厂模式**: `StrategyRegistry` 管理策略实例
4. **单例模式**: 数据库管理器、缓存管理器
5. **模板方法**: 回测引擎的执行流程

### 配置管理

- 所有配置集中在 `shared/enhanced_config.py`
- 支持环境变量覆盖（`DB_HOST`, `DB_USER`, `TUSHARE_TOKEN` 等）
- 敏感信息（如 Tushare Token）应通过环境变量注入

### 日志系统

- 使用 Python `logging` 模块
- 主日志文件: `fund_analysis.log`
- pytest日志: `tests/logs/pytest.log`
- CI日志: `tests/logs/ci-cd-{timestamp}.log`

### 报告输出

所有分析报告统一输出到 `pro2/reports/` 目录：
- **图表**: PNG格式可视化分析图
- **数据**: CSV格式详细数据导出
- **报告**: Markdown格式操作建议

### 前端技术栈

- **Flask**: 后端框架
- **Flask-CORS**: 跨域支持
- **Jinja2**: 模板引擎
- **原生JavaScript**: 前端交互
- **Chart.js/Matplotlib**: 数据可视化

### 关键依赖

- **数据处理**: pandas, numpy
- **数据库**: SQLAlchemy
- **Web框架**: Flask, flask-cors
- **数据可视化**: matplotlib, seaborn
- **机器学习**: scikit-learn
- **数据源**: tushare, akshare (需安装)
- **测试**: pytest, pytest-cov, pytest-html, pytest-mock

### 开发注意事项

1. **Python路径**: 代码中多处使用 `sys.path.append()` 添加模块路径，IDE可能无法正确识别导入
2. **数据库依赖**: 集成测试需要MySQL数据库运行
3. **数据源Token**: Tushare需要有效token才能获取数据
4. **文件路径**: 配置文件路径使用相对路径，注意工作目录
5. **端口占用**: Web应用默认使用5000端口
6. **中文显示**: 已配置中文字体支持（Windows: SimHei, Linux: WenQuanYi）

### 扩展开发

#### 添加新策略
1. 在 `backtesting/advanced_strategies.py` 继承 `BaseStrategy`
2. 实现 `generate_signal()` 方法
3. 在 `get_all_advanced_strategies()` 注册
4. 在 `unified_strategy_engine.py` 集成

#### 添加新数据源
1. 在 `data_retrieval/` 创建新的fetcher模块
2. 在 `multi_source_adapter.py` 注册数据源
3. 更新 `DATA_SOURCE_CONFIG` 配置

#### 添加新API路由
1. 在 `web/routes/` 创建新路由模块
2. 在 `web/app.py` 导入并注册Blueprint
3. 在 `templates/` 添加对应页面模板

### 故障排查

- **ModuleNotFoundError**: 检查 `sys.path` 和工作目录
- **数据库连接失败**: 验证 `DATABASE_CONFIG` 和MySQL服务
- **数据获取失败**: 检查网络和数据源Token配置
- **测试失败**: 查看 `tests/reports/` 和 `tests/logs/` 的详细报告
- **setuptools错误**: 升级 pip 和 setuptools

### 部署流程

1. 安装依赖: `pip install -r requirements.txt`
2. 配置数据库: 创建数据库和用户
3. 配置环境变量: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `TUSHARE_TOKEN`
4. 初始化数据库: 运行数据库迁移脚本
5. 启动应用: `python pro2/fund_search/web/app.py`
6. （可选）使用 Docker: `docker-compose up`
