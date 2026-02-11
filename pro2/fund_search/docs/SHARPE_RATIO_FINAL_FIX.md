# 夏普比率显示修复最终版

## 问题总结

根据用户反馈和截图分析，发现以下问题：

1. **同时显示4个夏普比率列**："夏普比率"、"夏普(近一年)"、"夏普(今年以来)"、"夏普(成立以来)"
2. **值显示异常**：大部分显示"--"，有些显示相同值（如3.00）
3. **默认值问题**：默认显示成立以来，但用户希望默认显示"当前周期"（近一年）
4. **计算逻辑问题**：不同时期的夏普比率没有独立计算

## 修复内容

### 1. 前端配置修复 (config.js)

**修改前：**
```javascript
{ key: 'sharpe_ratio_all', label: '夏普(成立以来)', visible: true, sortable: true, type: 'number' },
{ key: 'sharpe_ratio_1y', label: '夏普(近一年)', visible: true, sortable: true, type: 'number' },
{ key: 'sharpe_ratio_ytd', label: '夏普(今年以来)', visible: true, sortable: true, type: 'number' },
```

**修改后：**
```javascript
// 默认夏普比率：当前周期（近1年），可通过表头设置切换显示其他周期
{ key: 'sharpe_ratio', label: '夏普比率', visible: true, sortable: true, type: 'number' },
// 可选的夏普比率周期（通过表头设置显示/隐藏）
{ key: 'sharpe_ratio_1y', label: '夏普(近一年)', visible: false, sortable: true, type: 'number' },
{ key: 'sharpe_ratio_ytd', label: '夏普(今年以来)', visible: false, sortable: true, type: 'number' },
{ key: 'sharpe_ratio_all', label: '夏普(成立以来)', visible: false, sortable: true, type: 'number' },
```

**变更说明：**
- 默认只显示"夏普比率"列（对应近一年数据）
- 其他周期（近一年、今年以来、成立以来）作为可选列，默认隐藏
- 用户可通过"表头管理"按钮自定义显示哪些列

### 2. 后端计算修复 (multi_source_adapter.py)

已存在的正确计算逻辑：
```python
# 计算夏普比率（成立以来）- 使用全部数据
sharpe_ratio_all = (annualized_return - risk_free_rate) / volatility if volatility != 0 else 0.0

# 计算不同时期的夏普比率
sharpe_ratio_1y = sharpe_ratio_all  # 默认使用全部数据
sharpe_ratio_ytd = sharpe_ratio_all  # 默认使用全部数据

# 根据日期范围分别计算近一年和今年以来的夏普比率
if date_col in hist_data.columns:
    # 近一年数据筛选和计算
    one_year_ago = now - pd.DateOffset(years=1)
    last_year_data = hist_data_copy[hist_data_copy[date_col] >= one_year_ago]
    if len(last_year_data) >= 30:
        # 计算近一年夏普比率...
        sharpe_ratio_1y = ...
    
    # 今年以来数据筛选和计算
    ytd_start = pd.Timestamp(year=now.year, month=1, day=1)
    ytd_data = hist_data_copy[hist_data_copy[date_col] >= ytd_start]
    if len(ytd_data) >= 10:
        # 计算今年以来夏普比率...
        sharpe_ratio_ytd = ...
```

### 3. 缓存管理器修复 (fund_nav_cache_manager.py)

**问题：** `_calculate_performance_metrics` 方法中，所有时期的夏普比率都使用了相同的值

**修复：** 添加不同时期夏普比率的独立计算逻辑

```python
# 夏普比率（成立以来）- 使用全部数据
sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility != 0 else 0

# 计算不同时期的夏普比率
sharpe_ratio_1y = sharpe_ratio  # 默认使用全部数据
sharpe_ratio_ytd = sharpe_ratio  # 默认使用全部数据
sharpe_ratio_all = sharpe_ratio  # 成立以来

# 根据日期范围分别计算近一年和今年以来的夏普比率
if 'date' in df.columns:
    df_copy = df.copy()
    df_copy['date'] = pd.to_datetime(df_copy['date'])
    now = pd.Timestamp.now()
    
    # 计算近一年夏普比率
    one_year_ago = now - pd.DateOffset(years=1)
    last_year_data = df_copy[df_copy['date'] >= one_year_ago]
    if len(last_year_data) >= 30:
        # ... 计算逻辑
        sharpe_ratio_1y = ...
    
    # 计算今年以来夏普比率
    ytd_start = pd.Timestamp(year=now.year, month=1, day=1)
    ytd_data = df_copy[df_copy['date'] >= ytd_start]
    if len(ytd_data) >= 10:
        # ... 计算逻辑
        sharpe_ratio_ytd = ...
```

**同时更新了：**
- 数据库存储逻辑：添加 `sharpe_ratio_all` 字段的存储
- 数据库查询逻辑：添加 `sharpe_ratio_all` 字段的查询
- 空绩效指标方法：添加 `sharpe_ratio_all` 字段

### 4. API数据返回修复

#### holdings.py
- 修复了夏普比率的 fallback 逻辑，不再自动复制其他周期的值
- 默认 `sharpe_ratio` 优先使用近一年数据
- 各个周期的夏普比率独立返回

#### holding_realtime_service.py
- 修复了 `_get_performance_batch` 方法中的 fallback 逻辑
- 移除自动复制 `sharpe_ratio_all` 到其他字段的逻辑
- 确保每个周期的夏普比率独立处理

## 数据计算逻辑

| 周期 | 数据范围 | 最小数据要求 |
|------|----------|--------------|
| 成立以来 (all) | 全部历史数据 | 30个交易日 |
| 近一年 (1y) | 最近365天 | 30个交易日 |
| 今年以来 (ytd) | 当年1月1日至今 | 10个交易日 |

## 用户操作

### 清除浏览器缓存

由于前端配置已更改，用户需要清除浏览器缓存：

**方法1：清除 localStorage**
```javascript
localStorage.removeItem('fund_columns_config')
location.reload()
```

**方法2：强制刷新页面**
按 `Ctrl + Shift + R` (Windows) 或 `Cmd + Shift + R` (Mac)

### 表头设置

清除缓存后，用户可以：
1. 点击"表头管理"按钮
2. 自定义显示/隐藏夏普比率列
3. 可选的列包括：
   - 夏普比率（默认显示，对应近一年）
   - 夏普(近一年)（可选）
   - 夏普(今年以来)（可选）
   - 夏普(成立以来)（可选）

## 修复文件清单

| 文件 | 修改内容 |
|------|----------|
| `web/static/js/my-holdings/config.js` | 调整列配置，默认只显示"夏普比率"（近一年），其他周期可选 |
| `data_retrieval/multi_source_adapter.py` | 确认计算逻辑正确（已存在） |
| `services/fund_nav_cache_manager.py` | 添加不同时期夏普比率的独立计算、存储和查询 |
| `web/routes/holdings.py` | 修复 fallback 逻辑，确保各周期值独立 |
| `services/holding_realtime_service.py` | 修复 fallback 逻辑，确保各周期值独立 |

## 验证步骤

1. 清除浏览器缓存
2. 刷新基金列表页面
3. 检查默认只显示"夏普比率"列
4. 点击"表头管理"，验证可以添加/移除其他周期的夏普比率列
5. 检查不同周期的值是否不同（如果数据足够）
6. 验证排序功能是否正常
