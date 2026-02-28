# 单元测试业务功能文档

本文档详细说明基金分析系统单元测试覆盖的业务功能。

---

## 测试目录结构

```
tests/
├── unit/                           # 单元测试
│   ├── test_backtesting.py        # 回测引擎测试
│   ├── test_metrics_system.py     # 指标系统测试
│   ├── test_data_retrieval.py    # 数据检索测试
│   ├── test_data_retrieval/      # 数据检索子模块
│   │   └── test_multi_source_adapter.py
│   └── test_services/            # 服务层测试
│       └── test_cache.py
├── integration/                   # 集成测试
│   ├── test_api/
│   └── test_database.py
└── performance/                  # 性能测试
```

---

## 一、回测引擎测试 (test_backtesting.py)

### 1.1 TestBacktestEngine - 回测引擎

| 测试用例 | 测试功能 | 业务说明 |
|---------|---------|---------|
| `test_calculate_cumulative_returns` | 计算累计收益 | 将每日收益率序列转换为累计收益率曲线 |
| `test_calculate_max_drawdown` | 计算最大回撤 | 识别投资组合从峰值到谷底的最大跌幅 |
| `test_calculate_sharpe_ratio` | 计算夏普比率 | 衡量风险调整后的收益表现 |
| `test_calculate_volatility` | 计算波动率 | 衡量收益的不确定性和风险 |

### 1.2 TestStrategyModels - 策略模型

| 测试用例 | 测试功能 | 业务说明 |
|---------|---------|---------|
| `test_strategy_config_validation` | 策略配置验证 | 验证策略参数配置的合法性 |
| `test_backtest_result_structure` | 回测结果结构 | 验证回测结果数据模型的完整性 |

### 1.3 TestEnhancedStrategy - 增强策略

| 测试用例 | 测试功能 | 业务说明 |
|---------|---------|---------|
| `test_momentum_strategy_signals` | 动量策略信号 | 基于历史涨跌生成买入/卖出/持有信号 |
| `test_mean_reversion_strategy` | 均值回归策略 | 基于价格偏离均值程度生成交易信号 |
| `test_strategy_performance_metrics` | 策略性能指标 | 计算策略的总收益、波动率、夏普比率、最大回撤 |

### 1.4 TestRiskMetrics - 风险指标

| 测试用例 | 测试功能 | 业务说明 |
|---------|---------|---------|
| `test_value_at_risk` | VaR 风险价值 | 衡量给定置信度下的最大可能损失 |
| `test_conditional_var` | CVaR 条件风险价值 | 衡量超过 VaR 的平均损失 |
| `test_beta_calculation` | Beta 系数 | 衡量相对于市场的系统性风险 |

### 1.5 TestUnifiedStrategyEngine - 统一策略引擎

| 测试用例 | 测试功能 | 业务说明 |
|---------|---------|---------|
| `test_strategy_registry` | 策略注册表 | 动态注册和管理多种策略 |
| `test_strategy_execution_context` | 策略执行上下文 | 管理回测的初始资金、时间范围等 |
| `test_portfolio_allocation` | 投资组合配置 | 根据信号计算各基金的资金分配 |

---

## 二、指标系统测试 (test_metrics_system.py)

### 2.1 关键绩效指标引擎

| 测试用例 | 测试功能 | 业务说明 |
|---------|---------|---------|
| `test_metric_engine_summary_format` | 指标报告格式 | 验证指标报告的结构和内容完整性 |
| `test_metric_engine_rule_filtering` | 指标规则过滤 | 支持按需启用/禁用特定指标 |
| `test_metric_engine_dimensions` | 多维度指标 | 支持分组计算指标（如按部门） |
| `test_metric_engine_rule_override_annualization` | 年化参数覆盖 | 支持自定义年化交易日参数 |

---

## 三、数据检索测试 (test_data_retrieval.py)

### 3.1 TestFundDataParser - 基金数据解析

| 测试用例 | 测试功能 | 业务说明 |
|---------|---------|---------|
| `test_parse_fund_code_valid` | 解析有效基金代码 | 支持 6 位数字、含空格、带后缀(.OF) 等格式 |
| `test_parse_fund_code_invalid` | 解析无效基金代码 | 拒绝空字符串、长度不足/过长、非数字等 |
| `test_validate_fund_data_complete` | 验证完整数据 | 验证必填字段（基金代码、名称、净值、日期） |
| `test_validate_fund_data_incomplete` | 验证不完整数据 | 识别并报告缺失字段 |

### 3.2 TestFieldMapping - 字段映射

| 测试用例 | 测试功能 | 业务说明 |
|---------|---------|---------|
| `test_standardize_field_names` | 标准化字段名 | 将中文/英文原始字段转换为统一命名 |
| `test_calculate_derived_fields` | 计算派生字段 | 根据基础字段计算日收益率、持仓市值等 |

### 3.3 TestEnhancedDatabase - 增强数据库

| 测试用例 | 测试功能 | 业务说明 |
|---------|---------|---------|
| `test_build_connection_string` | 构建连接字符串 | 生成 MySQL 连接 URL |
| `test_sanitize_fund_code` | 清理基金代码 | 去除空格、统一格式、防止 SQL 注入 |

### 3.4 TestDateUtils - 日期工具

| 测试用例 | 测试功能 | 业务说明 |
|---------|---------|---------|
| `test_date_parsing` | 日期解析 | 支持多种日期格式（YYYY-MM-DD、YYYY/MM/DD） |
| `test_trading_days_logic` | 交易日判断 | 排除周末，筛选有效交易日 |

### 3.5 TestPortfolioImporter - 持仓导入

| 测试用例 | 测试功能 | 业务说明 |
|---------|---------|---------|
| `test_parse_excel_file` | 解析 Excel 文件 | 读取并解析基金持仓 Excel 文件 |
| `test_validate_holding_data` | 验证持仓数据 | 验证必填字段、数值有效性（金额>0） |

---

## 四、多数据源适配器测试 (test_multi_source_adapter.py)

### 4.1 TestMultiSourceDataAdapter

| 测试用例 | 测试功能 | 业务说明 |
|---------|---------|---------|
| `test_init_with_config` | 初始化配置 | 验证适配器初始化和缓存配置 |
| `test_calculate_today_return_realtime_fallback` | 今日收益计算（缓存 fallback） | 当无实时估值时，使用昨日净值计算 |
| `test_calculate_today_return_realtime_with_estimate` | 今日收益计算（实时估值） | 使用实时估值数据计算今日收益 |
| `test_calculate_today_return_realtime_zero_previous` | 边界情况处理 | 前一日净值为 0 时返回 0，避免除零错误 |

### 4.2 TestFundCodeValidation

| 测试用例 | 测试功能 | 业务说明 |
|---------|---------|---------|
| `test_valid_fund_codes` | 有效代码验证 | 验证 6 位数字格式 |
| `test_invalid_fund_codes` | 无效代码验证 | 拒绝空、过短/过长、非数字 |

### 4.3 TestPerformanceMetrics

| 测试用例 | 测试功能 | 业务说明 |
|---------|---------|---------|
| `test_sharpe_ratio_calculation` | 夏普比率计算 | 标准年化夏普比率 |
| `test_sharpe_ratio_insufficient_data` | 数据不足处理 | 数据少于 2 天时返回 0 |
| `test_volatility_calculation` | 波动率计算 | 日收益率标准差年化 |

---

## 五、缓存系统测试 (test_cache.py)

### 5.1 TestMemoryCache

| 测试用例 | 测试功能 | 业务说明 |
|---------|---------|---------|
| `test_set_and_get` | 基本存取 | 验证缓存的设置和获取功能 |
| `test_get_nonexistent` | 获取不存在键 | 键不存在时返回 None |
| `test_ttl_expiration` | TTL 过期 | 设置生存时间，到期自动删除 |
| `test_lru_eviction` | LRU 淘汰 | 超过最大容量时淘汰最少使用的项 |
| `test_delete` | 删除操作 | 删除指定键 |
| `test_delete_nonexistent` | 删除不存在键 | 返回 False |
| `test_clear` | 清空缓存 | 清空所有缓存数据 |
| `test_stats` | 缓存统计 | 统计命中/未命中次数、命中率 |
| `test_exists` | 键存在检查 | 检查键是否存在（考虑过期） |

### 5.2 TestPerformanceCalculator

| 测试用例 | 测试功能 | 业务说明 |
|---------|---------|---------|
| `test_sharpe_ratio_calculation` | 夏普比率 | 标准风险调整收益计算 |
| `test_sharpe_ratio_insufficient_data` | 数据不足处理 | 数据不足时返回 0 |
| `test_volatility_calculation` | 波动率 | 收益标准差计算 |
| `test_max_drawdown_calculation` | 最大回撤 | 净值曲线最大跌幅计算 |

---

## 测试覆盖率统计

| 模块 | 测试文件 | 测试用例数 |
|-----|---------|-----------|
| 回测引擎 | test_backtesting.py | 17 |
| 指标系统 | test_metrics_system.py | 4 |
| 数据检索 | test_data_retrieval.py | 14 |
| 多数据源 | test_multi_source_adapter.py | 9 |
| 缓存系统 | test_cache.py | 14 |
| **总计** | | **58** |

---

## 运行测试

```bash
# 运行所有单元测试
make test-unit

# 运行特定模块测试
pytest tests/unit/test_backtesting.py -v
pytest tests/unit/test_cache.py -v

# 运行测试并生成覆盖率报告
make coverage
```

---

*本文档由 CI/CD 系统自动生成，最后更新于 2026-02-28*
