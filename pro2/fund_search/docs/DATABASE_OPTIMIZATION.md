# 数据库结构优化说明

## 优化时间
2026-02-11

## 优化内容

### 1. 添加表注释 (Table Comments)

为以下表添加了中文注释，便于理解表用途：

| 表名 | 注释 |
|------|------|
| fund_analysis_results | 基金分析结果表 - 存储基金实时分析数据、策略信号、绩效指标 |
| fund_basic_info | 基金基本信息表 - 存储基金基础档案信息 |
| fund_performance | 基金绩效数据表 - 存储历史净值和绩效指标（按日期汇总） |
| user_holdings | 用户持仓表 - 存储用户基金持仓信息 |
| analysis_summary | 分析汇总表 - 存储每日分析汇总统计 |
| user_strategies | 用户策略表 - 存储用户自定义投资策略 |
| strategy_backtest_results | 策略回测结果表 - 存储策略回测执行结果 |
| fund_heavyweight_stocks | 基金重仓股表 - 存储基金重仓持股信息 |
| fund_nav_cache | 基金净值缓存表 - 缓存基金历史净值数据 |
| fund_cache_metadata | 缓存元数据表 - 记录基金数据缓存状态 |

### 2. 添加字段注释 (Column Comments)

为主要表的核心字段添加了详细注释，包括：
- 字段用途说明
- 数据格式示例
- 特殊值含义
- 单位标注（如：%、元）

#### fund_analysis_results 表关键字段注释示例：
- `fund_code`: 基金代码，如：000001
- `today_return`: 当日收益率(%)
- `prev_day_return`: 昨日收益率(%) - 主要使用的昨日盈亏字段
- `status_label`: 策略状态标签，如：强烈买入、观望等
- `sharpe_ratio_ytd`: 夏普比率-今年以来
- `max_drawdown`: 最大回撤(%)

### 3. 清理冗余字段 (Redundant Columns)

#### 已删除的冗余字段：

| 表名 | 删除字段 | 原因 |
|------|----------|------|
| fund_analysis_results | yesterday_return | 与 prev_day_return 重复，从未被代码使用 |

#### 字段说明：
- `yesterday_return`: 历史遗留字段，与 `prev_day_return` 含义相同
- 代码中只使用 `prev_day_return` 存储昨日收益率
- 删除后可避免数据冗余和混淆

## 优化脚本

### 使用方法

```bash
# 进入项目目录
cd pro2/fund_search

# 运行优化脚本
python scripts/db_schema_optimizer.py
```

### 脚本功能

1. **自动连接数据库** - 读取配置文件中的数据库连接信息
2. **添加表注释** - 为所有核心表添加中文注释
3. **添加字段注释** - 为关键字段添加详细说明
4. **清理冗余字段** - 删除未使用的重复字段
5. **生成结构文档** - 自动生成 DATABASE_SCHEMA.md 文档

### 注意事项

- 脚本会检查字段/注释是否已存在，避免重复添加
- 删除字段前会自动检查字段是否存在
- 所有操作都有日志记录，便于追踪
- 建议在测试环境先验证再应用到生产环境

## 数据库结构文档

优化完成后，会自动生成 `docs/DATABASE_SCHEMA.md` 文件，包含：
- 所有表的完整字段列表
- 字段数据类型和可空性
- 默认值信息
- 中文注释说明

## 后续维护建议

1. **新增表时**: 及时在 `TABLE_COMMENTS` 中添加表注释
2. **新增字段时**: 及时在 `COLUMN_COMMENTS` 中添加字段注释
3. **定期审查**: 定期检查是否存在新的冗余字段
4. **文档同步**: 运行优化脚本更新 DATABASE_SCHEMA.md 文档
