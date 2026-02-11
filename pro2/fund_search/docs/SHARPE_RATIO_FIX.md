# 夏普比率显示修复说明

## 问题描述

基金列表页面中的夏普比率列存在以下问题：
1. 默认显示的"夏普比率"列数据未正确计算，显示为 0.00
2. 多余的夏普比率选项（默认周期、近一年、今年以来、成立以来）
3. 不同时期的夏普比率值相同，未根据实际时间段计算
4. 排序功能可能异常

## 修复内容

### 1. 前端配置修复 (config.js)

**修改前：**
```javascript
{ key: 'sharpe_ratio', label: '夏普比率', visible: true, sortable: true, type: 'number' },
{ key: 'sharpe_ratio_ytd', label: '夏普(今年以来)', visible: false, sortable: true, type: 'number' },
{ key: 'sharpe_ratio_1y', label: '夏普(近一年)', visible: false, sortable: true, type: 'number' },
{ key: 'sharpe_ratio_all', label: '夏普(成立以来)', visible: false, sortable: true, type: 'number' },
```

**修改后：**
```javascript
{ key: 'sharpe_ratio_all', label: '夏普(成立以来)', visible: true, sortable: true, type: 'number' },
{ key: 'sharpe_ratio_1y', label: '夏普(近一年)', visible: true, sortable: true, type: 'number' },
{ key: 'sharpe_ratio_ytd', label: '夏普(今年以来)', visible: true, sortable: true, type: 'number' },
```

**变更说明：**
- 移除默认的 `sharpe_ratio` 列（未明确时间周期的列）
- 默认显示"成立以来"（`sharpe_ratio_all`）
- 同时显示"近一年"和"今年以来"
- 所有列都支持排序

### 2. 后端计算修复 (multi_source_adapter.py)

**核心修改：**
在 `_calculate_metrics` 方法中，分别计算不同时期的夏普比率：

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

**计算逻辑：**
1. **成立以来** - 使用全部历史数据计算
2. **近一年** - 使用最近365天的数据计算（需至少30个交易日）
3. **今年以来** - 使用当年1月1日至今的数据计算（需至少10个交易日）

### 3. 数据返回修复

#### holdings.py
- 更新主逻辑中的夏普比率字段提取和映射
- 更新降级逻辑中的字段处理
- 确保返回 `sharpe_ratio_all`, `sharpe_ratio_1y`, `sharpe_ratio_ytd` 三个字段

#### holding_realtime_service.py
- 更新 `HoldingDataDTO` 类，添加新的夏普比率字段
- 更新 `_get_performance_batch` 方法，查询并返回各个时期的夏普比率
- 更新 `get_holdings_data` 方法，正确填充各个时期的夏普比率到DTO

## 数据验证

测试结果显示修复成功：

```
基金 008811:
  默认夏普比率 (sharpe_ratio):      -0.0058
  今年以来 (sharpe_ratio_ytd):      -0.0328
  近一年   (sharpe_ratio_1y):       -0.0125
  成立以来 (sharpe_ratio_all):      -0.0058
  数据天数: 1460
```

不同时期的夏普比率有不同的值，说明计算逻辑正确。

## 用户操作

### 清除浏览器缓存

由于前端配置已更改，用户需要清除浏览器缓存以加载新的列配置：

**方法1：清除 localStorage**
1. 打开基金列表页面
2. 按 F12 打开开发者工具
3. 在 Console 中执行：
   ```javascript
   localStorage.removeItem('fund_columns_config')
   location.reload()
   ```

**方法2：强制刷新页面**
1. 在基金列表页面
2. 按 `Ctrl + Shift + R` (Windows) 或 `Cmd + Shift + R` (Mac)

**方法3：清除浏览器缓存**
1. 打开浏览器设置
2. 清除浏览数据（选择"缓存的图像和文件"）
3. 重新访问基金列表页面

### 表头设置

清除缓存后，用户可以：
1. 点击"表头管理"按钮
2. 自定义显示/隐藏夏普比率列
3. 可选的列包括：
   - 夏普(成立以来) - 默认显示
   - 夏普(近一年) - 默认显示
   - 夏普(今年以来) - 默认显示

## 排序功能

所有夏普比率列都支持排序：
1. 点击列头按升序排列
2. 再次点击按降序排列
3. 排序基于实际数值，正确处理 null 值

## 后续维护

如需添加更多时间周期的夏普比率：
1. 在 `multi_source_adapter.py` 的 `_calculate_metrics` 中添加计算逻辑
2. 在 `config.js` 中添加新的列配置
3. 更新相关 DTO 和数据返回逻辑
4. 更新数据库表结构（如需要）
