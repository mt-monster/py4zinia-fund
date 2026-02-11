# 基金分析系统 - 数据库表结构文档

生成时间: 2026-02-11 15:33:53

============================================================


## fund_analysis_results
基金分析结果表 - 存储基金实时分析数据、策略信号、绩效指标

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| fund_code | VARCHAR(20) | 是 | - | 基金代码，如：000001 |
| fund_name | VARCHAR(100) | 是 | - | 基金名称 |
| yesterday_nav | FLOAT | 是 | - | 昨日净值 |
| current_estimate | FLOAT | 是 | - | 当前估算净值/最新净值 |
| today_return | FLOAT | 是 | - | 当日收益率(%) |
| prev_day_return | FLOAT | 是 | - | 昨日收益率(%) - 主要使用的昨日盈亏字段 |
| status_label | VARCHAR(50) | 是 | - | 策略状态标签，如：强烈买入、观望等 |
| is_buy | TINYINT | 是 | - | 是否为买入信号：1=买入，0=非买入 |
| redeem_amount | DECIMAL(10,2) | 是 | - | 赎回金额建议 |
| comparison_value | FLOAT | 是 | - | 对比值（今日-昨日收益率差值） |
| operation_suggestion | VARCHAR(100) | 是 | - | 操作建议描述 |
| execution_amount | VARCHAR(20) | 是 | - | 执行金额建议 |
| analysis_date | DATE | 是 | - | 分析日期 |
| buy_multiplier | FLOAT | 是 | - | 买入倍率，建议加仓倍数 |
| annualized_return | FLOAT | 是 | - | 年化收益率(%) |
| sharpe_ratio | FLOAT | 是 | - | 夏普比率-默认周期 |
| sharpe_ratio_ytd | FLOAT | 是 | - | 夏普比率-今年以来 |
| sharpe_ratio_1y | FLOAT | 是 | - | 夏普比率-近一年 |
| sharpe_ratio_all | FLOAT | 是 | - | 夏普比率-成立以来 |
| max_drawdown | FLOAT | 是 | - | 最大回撤(%) |
| volatility | FLOAT | 是 | - | 波动率(%) |
| calmar_ratio | FLOAT | 是 | - | 卡玛比率 |
| sortino_ratio | FLOAT | 是 | - | 索提诺比率 |
| var_95 | FLOAT | 是 | - | VaR风险价值(95%置信度) |
| win_rate | FLOAT | 是 | - | 胜率(%) |
| profit_loss_ratio | FLOAT | 是 | - | 盈亏比 |
| total_return | FLOAT | 是 | - | 累计收益率(%) |
| composite_score | FLOAT | 是 | - | 综合评分 |
| created_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |
| updated_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |


## fund_basic_info
基金基本信息表 - 存储基金基础档案信息

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | INT | 否 | - | - [自增] |
| fund_code | VARCHAR(10) | 否 | - | 基金代码，唯一标识 |
| fund_name | VARCHAR(100) | 否 | - | 基金全称 |
| fund_type | VARCHAR(50) | 是 | - | 基金类型：股票型/债券型/混合型/指数型等 |
| fund_company | VARCHAR(100) | 是 | - | 基金公司/管理人 |
| fund_manager | VARCHAR(100) | 是 | - | 基金经理 |
| establish_date | DATE | 是 | - | 基金成立日期 |
| management_fee | DECIMAL(5,4) | 是 | - | 管理费率(%) |
| custody_fee | DECIMAL(5,4) | 是 | - | 托管费率(%) |
| created_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |
| updated_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |


## fund_performance
基金绩效数据表 - 存储历史净值和绩效指标（按日期汇总）

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | INT | 否 | - | - [自增] |
| fund_code | VARCHAR(10) | 否 | - | 基金代码 |
| analysis_date | DATE | 否 | - | 分析日期 |
| current_nav | DECIMAL(10,4) | 是 | - | 当日单位净值 |
| previous_nav | DECIMAL(10,4) | 是 | - | 前一日单位净值 |
| nav_date | DATE | 是 | - | 净值日期 |
| annualized_return | DECIMAL(8,4) | 是 | - | 年化收益率(%) |
| sharpe_ratio | DECIMAL(8,4) | 是 | - | 夏普比率 |
| max_drawdown | DECIMAL(8,4) | 是 | - | 最大回撤(%) |
| volatility | DECIMAL(8,4) | 是 | - | 波动率(%) |
| calmar_ratio | DECIMAL(8,4) | 是 | - | 卡玛比率 |
| sortino_ratio | DECIMAL(8,4) | 是 | - | 索提诺比率 |
| var_95 | DECIMAL(8,4) | 是 | - | VaR风险价值(95%置信度) |
| win_rate | DECIMAL(5,4) | 是 | - | 胜率(%) |
| profit_loss_ratio | DECIMAL(8,4) | 是 | - | 盈亏比 |
| composite_score | DECIMAL(5,4) | 是 | - | 综合评分 |
| total_return | DECIMAL(8,4) | 是 | - | 累计收益率(%) |
| data_days | INT | 是 | - | 数据天数/样本量 |
| created_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |
| updated_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |


## user_holdings
用户持仓表 - 存储用户基金持仓信息

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | INT | 否 | - | 自增主键ID [自增] |
| user_id | VARCHAR(50) | 否 | default_user | 用户ID，默认default_user |
| fund_code | VARCHAR(20) | 否 | - | 基金代码 |
| fund_name | VARCHAR(100) | 否 | - | 基金名称 |
| holding_shares | FLOAT | 是 | 0 | 持仓份额 |
| cost_price | FLOAT | 是 | 0 | 成本价 |
| holding_amount | FLOAT | 是 | 0 | 持有金额（份额×成本价） |
| buy_date | DATE | 是 | - | 买入日期 |
| created_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |
| updated_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |
| notes | TEXT | 是 | - | 备注信息 |


## analysis_summary
分析汇总表 - 存储每日分析汇总统计

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | INT | 否 | - | - [自增] |
| analysis_date | DATE | 否 | - | 分析日期 |
| total_funds | INT | 是 | - | 分析基金总数 |
| buy_signals | INT | 是 | - | 买入信号数量 |
| sell_signals | INT | 是 | - | 卖出信号数量 |
| hold_signals | INT | 是 | - | 持有信号数量 |
| avg_buy_multiplier | DECIMAL(5,2) | 是 | - | 平均买入倍率 |
| total_redeem_amount | INT | 是 | - | 总建议赎回金额 |
| best_performing_fund | VARCHAR(10) | 是 | - | 表现最佳基金代码 |
| worst_performing_fund | VARCHAR(10) | 是 | - | 表现最差基金代码 |
| highest_sharpe_fund | VARCHAR(10) | 是 | - | 夏普比率最高基金 |
| lowest_volatility_fund | VARCHAR(10) | 是 | - | 波动率最低基金 |
| report_files | JSON | 是 | - | 报告文件路径（JSON格式） |
| created_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |
| updated_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |


## user_strategies
用户策略表 - 存储用户自定义投资策略

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | INT | 否 | - | 策略ID，自增主键 [自增] |
| user_id | VARCHAR(50) | 否 | default_user | 用户ID |
| name | VARCHAR(100) | 否 | - | 策略名称 |
| description | TEXT | 是 | - | 策略描述 |
| config | JSON | 否 | - | 策略配置（JSON格式） |
| created_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |
| updated_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |


## strategy_backtest_results
策略回测结果表 - 存储策略回测执行结果

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | INT | 否 | - | 回测记录ID [自增] |
| strategy_id | INT | 否 | - | 关联的策略ID |
| task_id | VARCHAR(50) | 否 | - | 任务唯一标识 |
| status | VARCHAR(20) | 是 | pending | 回测状态：pending/running/success/failed |
| result | JSON | 是 | - | 回测结果数据（JSON格式） |
| created_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |
| completed_at | TIMESTAMP | 是 | - | 完成时间 |


## fund_heavyweight_stocks
基金重仓股表 - 存储基金重仓持股信息

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | INT | 否 | - | 记录ID [自增] |
| fund_code | VARCHAR(10) | 否 | - | 基金代码 |
| stock_code | VARCHAR(10) | 否 | - | 股票代码 |
| stock_name | VARCHAR(100) | 否 | - | 股票名称 |
| holding_ratio | DECIMAL(8,4) | 是 | - | 持仓比例(%) |
| market_value | DECIMAL(15,2) | 是 | - | 持仓市值 |
| change_percent | DECIMAL(8,4) | 是 | - | 持仓变动比例(%) |
| report_period | VARCHAR(20) | 是 | - | 报告期，如：2024Q1 |
| ranking | INT | 是 | 0 | 重仓排名 |
| created_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |
| updated_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |


## fund_nav_cache
基金净值缓存表

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | INT | 否 | - | - [自增] |
| fund_code | VARCHAR(10) | 否 | - | - |
| nav_date | DATE | 否 | - | - |
| nav_value | DECIMAL(10,4) | 否 | - | - |
| accum_nav | DECIMAL(10,4) | 是 | - | - |
| daily_return | DECIMAL(8,4) | 是 | - | - |
| data_source | VARCHAR(20) | 是 | - | - |
| created_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |
| updated_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |


## fund_cache_metadata
基金缓存元数据表

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | INT | 否 | - | - [自增] |
| fund_code | VARCHAR(10) | 否 | - | - |
| earliest_date | DATE | 是 | - | - |
| latest_date | DATE | 是 | - | - |
| total_records | INT | 是 | 0 | - |
| last_sync_at | TIMESTAMP | 是 | - | - |
| next_sync_at | TIMESTAMP | 是 | - | - |
| sync_status | ENUM | 是 | pending | - |
| sync_fail_count | INT | 是 | 0 | - |
| data_source | VARCHAR(20) | 是 | - | - |
| created_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |
| updated_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | - |
