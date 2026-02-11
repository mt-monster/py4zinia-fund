# 昨日盈亏率数据时效性标记功能

## 功能概述

为基金列表中的"昨日盈亏率"列增加了数据时效性验证和标记功能。当计算昨日盈亏率使用的净值数据不是T-1日（前一个交易日）的数据时，系统会在界面上进行明确的标记。

## 实现逻辑

### 后端实现

1. **multi_source_adapter.py**
   - 修改 `_get_yesterday_return` 方法，返回包含日期信息的字典：
     ```python
     {
         'value': 昨日收益率,
         'date': 使用的净值日期,
         'days_diff': 与最新净值的日期差（T-1=1, T-2=2）,
         'is_stale': 是否为延迟数据（days_diff > 1）
     }
     ```
   - 新增 `_get_previous_nonzero_return_with_date` 方法，支持带日期的前向追溯

2. **holding_realtime_service.py**
   - 更新 `HoldingDataDTO`，添加新字段：
     - `yesterday_return_date`: 使用的净值日期
     - `yesterday_return_days_diff`: 日期差
     - `yesterday_return_is_stale`: 是否为延迟数据
   - 更新 `_get_yesterday_data_batch` 方法，处理新的返回格式
   - 更新 `get_holdings_data` 方法，填充新的 DTO 字段

3. **holdings.py (API)**
   - 在 API 返回中添加新字段：
     - `yesterday_return_date`
     - `yesterday_return_days_diff`
     - `yesterday_return_is_stale`

### 前端实现

1. **table.js**
   - 修改 `renderRow` 方法中的 `prev_day_return` 列渲染逻辑
   - 当 `is_stale` 为 true 且 `days_diff > 1` 时：
     - 添加 `stale-data` CSS 类
     - 显示数值和 T-N 标记徽章
     - 添加工具提示显示具体日期信息

2. **my-holdings-enhanced.css**
   - 添加延迟数据单元格的背景色（淡黄色）
   - 添加 T-N 徽章样式（不同延迟天数不同颜色）
   - 添加深色主题适配
   - 添加工具提示样式

## 显示效果

### 正常数据（T-1）
```
+2.50%
```
鼠标悬停显示：数据日期: 2026-02-10

### 延迟数据（T-2及以上）
```
+2.50% [T-2]
```
- 单元格背景变为淡黄色
- 数值后显示 T-N 徽章
- 鼠标悬停显示：昨日盈亏率数据来自 2026-02-09，比最新净值延迟 2 天

### 颜色编码
- **T-2**（延迟1天）：黄色背景 `#ffc107`
- **T-3**（延迟2天）：橙色背景 `#fd7e14`
- **T-4及以上**（延迟3天及以上）：红色背景 `#dc3545`

## 使用场景

### QDII 基金
QDII 基金由于时差和交易时间差异，经常会出现数据延迟的情况。此功能可以：
- 明确告知用户数据的实际日期
- 避免因数据延迟造成的误判

### 新成立基金
新成立的基金可能历史数据不足，系统会使用最早可用的数据进行计算，此功能可以：
- 标记数据的新旧程度
- 提醒用户数据的局限性

### 数据缺失情况
当数据源出现异常或延迟时，此功能可以：
- 显示实际使用的数据日期
- 帮助用户理解数据的时效性

## 测试验证

1. 查看 QDII 基金的昨日盈亏率列
2. 鼠标悬停查看工具提示
3. 观察 T-N 徽章的颜色变化
4. 验证延迟数据的单元格背景色

## 相关文件

| 文件 | 修改内容 |
|------|----------|
| `data_retrieval/multi_source_adapter.py` | 修改 `_get_yesterday_return`，新增 `_get_previous_nonzero_return_with_date` |
| `services/holding_realtime_service.py` | 更新 DTO 和昨日数据获取逻辑 |
| `web/routes/holdings.py` | API 返回新增字段 |
| `web/static/js/my-holdings/table.js` | 渲染逻辑添加时效性标记 |
| `web/static/css/my-holdings-enhanced.css` | 添加延迟数据样式 |
