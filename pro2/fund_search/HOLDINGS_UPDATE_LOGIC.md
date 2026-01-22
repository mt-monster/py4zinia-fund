# 持仓信息更新逻辑

## 概述

截图识别导入功能会自动保存持仓信息到 `user_holdings` 表，并通过 JOIN 查询自动计算和显示持仓盈亏信息。

---

## 数据库表结构

### 1. user_holdings 表（持仓表）

存储用户的基金持仓信息：

```sql
CREATE TABLE user_holdings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    fund_code VARCHAR(10) NOT NULL,
    fund_name VARCHAR(200),
    holding_shares DECIMAL(15, 2),      -- 持有份额
    cost_price DECIMAL(10, 4),          -- 成本价
    holding_amount DECIMAL(15, 2),      -- 持仓金额
    buy_date DATE,                      -- 买入日期
    notes TEXT,                         -- 备注
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_fund (user_id, fund_code)
);
```

### 2. fund_analysis_results 表（分析结果表）

存储基金的分析数据和净值信息：

```sql
CREATE TABLE fund_analysis_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_code VARCHAR(10) NOT NULL,
    fund_name VARCHAR(200),
    current_estimate DECIMAL(10, 4),    -- 当前净值
    yesterday_nav DECIMAL(10, 4),       -- 昨日净值
    today_return DECIMAL(10, 4),        -- 今日涨跌幅
    annualized_return DECIMAL(10, 4),   -- 年化收益率
    sharpe_ratio DECIMAL(10, 4),        -- 夏普比率
    max_drawdown DECIMAL(10, 4),        -- 最大回撤
    composite_score DECIMAL(10, 4),     -- 综合评分
    analysis_date DATE,
    -- ... 其他字段
);
```

---

## 数据流程

### 1. 截图识别导入

```
OCR识别 → 数据转换 → 保存到 user_holdings → 计算盈亏 → 显示结果
```

#### 步骤详解：

**Step 1: OCR识别**
```javascript
{
    fund_code: '013048',
    fund_name: '富国中证新能源汽车指数(LOF)C',
    holding_amount: 276.65,      // 持仓金额
    profit_amount: 13.45,        // 盈亏金额
    current_value: 290.10,       // 当前市值
    nav_value: 1.234             // 净值（可能为null）
}
```

**Step 2: 数据转换**
```javascript
// 计算持有份额和成本价
holding_shares = current_value / nav_value  // 235.09
cost_price = holding_amount / holding_shares // 1.1768
```

**Step 3: 保存到数据库**
```sql
INSERT INTO user_holdings 
(user_id, fund_code, fund_name, holding_shares, cost_price, holding_amount, buy_date, notes)
VALUES ('default_user', '013048', '富国中证新能源汽车指数(LOF)C', 235.09, 1.1768, 276.65, '2026-01-22', '通过截图识别导入 - 置信度: 95.00%')
ON DUPLICATE KEY UPDATE
    holding_shares = holding_shares + 235.09,
    holding_amount = holding_amount + 276.65,
    cost_price = (holding_amount + 276.65) / (holding_shares + 235.09),
    notes = CONCAT(notes, '; ', '通过截图识别导入 - 置信度: 95.00%'),
    updated_at = NOW()
```

**Step 4: 获取最新净值**
```sql
SELECT current_estimate, yesterday_nav 
FROM fund_analysis_results 
WHERE fund_code = '013048' 
ORDER BY analysis_date DESC 
LIMIT 1
```

**Step 5: 计算盈亏信息**
```python
current_nav = 1.234           # 当前净值
previous_nav = 1.200          # 昨日净值
holding_shares = 235.09       # 持有份额
holding_amount = 276.65       # 持仓金额

# 当前市值
current_value = holding_shares * current_nav  # 290.10

# 持有盈亏
holding_profit = current_value - holding_amount  # 13.45
holding_profit_rate = (holding_profit / holding_amount) * 100  # 4.86%

# 当日盈亏
previous_value = holding_shares * previous_nav  # 282.11
today_profit = current_value - previous_value  # 7.99
today_profit_rate = (today_profit / previous_value) * 100  # 2.83%
```

### 2. 查询持仓列表

```sql
SELECT 
    far.fund_code, 
    far.fund_name, 
    far.today_return, 
    far.current_estimate as current_nav, 
    far.yesterday_nav as previous_nav,
    h.holding_shares, 
    h.cost_price, 
    h.holding_amount, 
    h.buy_date
FROM fund_analysis_results far
LEFT JOIN user_holdings h ON far.fund_code = h.fund_code AND h.user_id = 'default_user'
WHERE far.analysis_date = '2026-01-22'
```

**查询结果：**
```
fund_code: 013048
fund_name: 富国中证新能源汽车指数(LOF)C
current_nav: 1.234
previous_nav: 1.200
holding_shares: 235.09
cost_price: 1.1768
holding_amount: 276.65
```

**前端计算盈亏：**
```javascript
// 当前市值
current_value = holding_shares * current_nav  // 290.10

// 持有盈亏
holding_profit = current_value - holding_amount  // 13.45
holding_profit_rate = (holding_profit / holding_amount) * 100  // 4.86%

// 当日盈亏
previous_value = holding_shares * previous_nav  // 282.11
today_profit = current_value - previous_value  // 7.99
today_profit_rate = (today_profit / previous_value) * 100  // 2.83%
```

---

## API端点更新

### `/api/holdings/import/confirm`

**功能增强：**

1. ✅ 保存到 `user_holdings` 表
2. ✅ 获取最新净值信息
3. ✅ 计算持仓盈亏
4. ✅ 记录详细日志
5. ✅ 更新成本价（重复导入时）

**重复导入处理：**

如果同一个基金重复导入，会：
- 累加持有份额
- 累加持仓金额
- 重新计算平均成本价：`cost_price = total_holding_amount / total_holding_shares`
- 追加备注信息

**示例：**

第一次导入：
```
holding_shares: 100
cost_price: 1.20
holding_amount: 120
```

第二次导入：
```
holding_shares: 50
cost_price: 1.30
holding_amount: 65
```

合并后：
```
holding_shares: 150
holding_amount: 185
cost_price: 185 / 150 = 1.2333
```

---

## 前端显示逻辑

### `/api/funds` 端点

返回的数据包含持仓盈亏信息：

```javascript
{
    fund_code: '013048',
    fund_name: '富国中证新能源汽车指数(LOF)C',
    current_nav: 1.234,
    previous_nav: 1.200,
    holding_shares: 235.09,
    cost_price: 1.1768,
    holding_amount: 276.65,
    // 计算后的字段
    today_profit: 7.99,
    today_profit_rate: 2.83,
    holding_profit: 13.45,
    holding_profit_rate: 4.86,
    total_profit: 13.45,
    total_profit_rate: 4.86,
    current_value: 290.10
}
```

### 持仓列表显示

| 基金代码 | 基金名称 | 持仓金额 | 当日盈亏 | 持有盈亏 | 当前市值 |
|---------|---------|---------|---------|---------|---------|
| 013048 | 富国中证新能源... | ¥276.65 | +¥7.99 (+2.83%) | +¥13.45 (+4.86%) | ¥290.10 |

---

## 数据一致性保证

### 1. 事务处理

虽然当前实现没有显式使用事务，但 `ON DUPLICATE KEY UPDATE` 确保了原子性操作。

### 2. 数据验证

- ✅ 基金代码不能为空
- ✅ 持有份额必须大于0
- ✅ 成本价必须大于0
- ✅ 持仓金额 = 持有份额 × 成本价

### 3. 错误处理

- ✅ 数据库插入失败会记录到 `failed` 列表
- ✅ 详细的错误日志
- ✅ 返回成功和失败的统计信息

---

## 性能优化

### 1. 批量查询

虽然当前是逐个处理基金，但可以优化为批量查询净值信息：

```python
# 优化前：逐个查询
for fund in funds:
    nav_df = db_manager.execute_query(sql_nav, {'fund_code': fund_code})

# 优化后：批量查询
fund_codes = [f['fund_code'] for f in funds]
sql_nav_batch = """
SELECT fund_code, current_estimate, yesterday_nav 
FROM fund_analysis_results 
WHERE fund_code IN :fund_codes 
ORDER BY analysis_date DESC
"""
nav_df = db_manager.execute_query(sql_nav_batch, {'fund_codes': tuple(fund_codes)})
```

### 2. 缓存净值信息

对于同一天的多次导入，可以缓存净值信息避免重复查询。

---

## 测试场景

### 场景1: 首次导入

```
输入: 3个基金
结果: 
- user_holdings 表新增3条记录
- 持仓列表显示3个基金及盈亏信息
```

### 场景2: 重复导入

```
输入: 已存在的基金
结果:
- 持有份额累加
- 持仓金额累加
- 成本价重新计算
- 备注追加
```

### 场景3: 部分失败

```
输入: 5个基金，其中2个代码为空
结果:
- 3个成功导入
- 2个失败（记录在failed列表）
- 返回详细的成功/失败信息
```

---

## 日志示例

```
INFO - 导入基金 013048: 持仓金额=276.65, 当前市值=290.10, 持有盈亏=13.45 (4.86%)
INFO - 导入基金 013277: 持仓金额=274.58, 当前市值=279.78, 持有盈亏=5.20 (1.89%)
INFO - 导入基金 006106: 持仓金额=262.57, 当前市值=266.65, 持有盈亏=4.08 (1.55%)
INFO - 成功导入 3 个基金，0 个失败
```

---

## 总结

持仓信息更新逻辑的关键点：

1. ✅ **单一数据源** - 持仓数据只存储在 `user_holdings` 表
2. ✅ **JOIN查询** - 通过 LEFT JOIN 关联获取持仓和净值信息
3. ✅ **前端计算** - 盈亏信息在前端实时计算
4. ✅ **重复导入处理** - 自动累加和重新计算成本价
5. ✅ **详细日志** - 记录每个基金的导入和计算过程

这种设计的优势：
- 数据不冗余
- 实时计算盈亏
- 易于维护和扩展
- 性能良好

---

## 完成时间
2026-01-22

## 相关文档
- [用户确认流程](./USER_CONFIRM_FLOW.md)
- [完整集成总结](./COMPLETE_INTEGRATION_SUMMARY.md)
