# 基金列表夏普指标计算审查报告

## 审查时间
2026-02-11

## 审查对象
- `multi_source_adapter.py` - 夏普比率计算核心逻辑
- `holding_realtime_service.py` - 基金列表数据获取

---

## 发现的问题

### 问题1: 日收益率格式处理错误 ⚠️ 严重

**位置**: `multi_source_adapter.py` 第869-870行

**代码**:
```python
# 如果数值很小，可能是小数格式，需要转换为百分比
if abs(daily_returns).mean() < 1:
    daily_returns = daily_returns * 100
```

**问题**:
- 数据源返回的日增长率已经是百分比格式（如0.65表示0.65%）
- 但代码错误地将其乘以100，变成了0.65% → 65%
- 这导致年化波动率计算结果异常放大100倍

**影响**:
- 以001270为例，正确的年化波动率应该是20.41%
- 但乘以100后，波动率变成2041%，夏普比率趋近于0

**修复方案**:
应该将百分比转换为小数（除以100），而不是乘以100：
```python
# 如果数值较大，是百分比格式，需要转换为小数
if abs(daily_returns).mean() >= 0.01:
    daily_returns = daily_returns / 100
```

---

### 问题2: 净值数据未按日期排序 ⚠️ 严重

**位置**: `multi_source_adapter.py` 第919-920行

**代码**:
```python
start_nav = float(hist_data[nav_col].iloc[0])
end_nav = float(hist_data[nav_col].iloc[-1])
```

**问题**:
- `get_historical_data()` 返回的数据按日期**降序**排列（最新在前）
- 但代码假设第一条是最早的数据（起始净值）
- 这导致起始净值和最新净值颠倒，总收益率计算错误

**影响**:
- 以001270为例，修复前总收益率为-33.21%（错误）
- 修复后总收益率为+49.73%（正确）

**修复方案**:
在计算前确保数据按日期升序排列：
```python
# 确保数据按日期升序排列
if date_col in hist_data.columns:
    hist_data = hist_data.sort_values(date_col, ascending=True).reset_index(drop=True)

start_nav = float(hist_data[nav_col].iloc[0])
end_nav = float(hist_data[nav_col].iloc[-1])
```

---

### 问题3: 风险利率配置不一致 ⚠️ 轻微

**位置**: `multi_source_adapter.py` 第905行

**代码**:
```python
INVESTMENT_STRATEGY_CONFIG = {
    'risk_free_rate': 0.02  # fallback值
}
```

**问题**:
- fallback值是0.02，但配置文件中是0.03
- 虽然实际运行时会从配置读取，但默认值不一致可能导致混淆

**修复方案**:
保持与配置文件一致：
```python
'risk_free_rate': 0.03
```

---

## 修复影响对比

### 以001270为例

| 指标 | 修复前 | 修复后 | 变化 |
|------|--------|--------|------|
| 日收益率处理 | ×100 (错误) | ÷100 (正确) | 格式修正 |
| 净值排序 | 降序(错误) | 升序(正确) | 排序修正 |
| 总收益率 | -33.21% | +49.73% | 方向反转 |
| 年化收益率 | -3.75% | +3.89% | 符号反转 |
| 年化波动率 | 2041% | 20.41% | 缩小100倍 |
| 夏普(全期) | -0.0033 | +0.0436 | 由负转正 |

---

## 修复代码

### multi_source_adapter.py 修复

#### 修复1: _get_performance_metrics_from_cache 方法

找到第869-870行：
```python
# 如果数值很小，可能是小数格式，需要转换为百分比
if abs(daily_returns).mean() < 1:
    daily_returns = daily_returns * 100
```

修改为：
```python
# 如果数值较大，是百分比格式，需要转换为小数
if abs(daily_returns).mean() >= 0.01:
    daily_returns = daily_returns / 100
```

#### 修复2: _calculate_metrics 方法

找到第919-920行：
```python
# 计算总收益率（成立以来）
if nav_col in hist_data.columns:
    start_nav = float(hist_data[nav_col].iloc[0])
    end_nav = float(hist_data[nav_col].iloc[-1])
```

修改为：
```python
# 确保数据按日期升序排列（最早的在前）
if date_col in hist_data.columns:
    hist_data = hist_data.sort_values(date_col, ascending=True).reset_index(drop=True)

# 计算总收益率（成立以来）
if nav_col in hist_data.columns:
    start_nav = float(hist_data[nav_col].iloc[0])
    end_nav = float(hist_data[nav_col].iloc[-1])
```

同时需要确保date_col变量在方法开头就定义：
在第914行后添加：
```python
date_col = '日期' if '日期' in hist_data.columns else 'date'
```

---

## 验证方法

修复后，可以通过以下方式验证：

1. **检查001270的计算结果**:
   ```python
   adapter = MultiSourceDataAdapter()
   metrics = adapter.get_performance_metrics('001270')
   print(f"夏普(全期): {metrics['sharpe_ratio_all']}")  # 应为约0.04
   print(f"年化波动: {metrics['volatility']}")  # 应为约0.20 (20%)
   ```

2. **对比手动计算**:
   - 起始净值: 1.0000
   - 最新净值: 1.4973
   - 总收益率: 49.73%
   - 年化收益率: 3.89%
   - 年化波动率: 20.41%
   - 夏普比率: (3.89% - 3%) / 20.41% = 0.0436

---

## 建议

1. **立即修复**问题1和问题2，这是计算错误的主要原因
2. **重新计算**所有基金的夏普比率并更新数据库
3. **添加单元测试**验证夏普比率计算逻辑
4. **统一配置**确保所有地方使用相同的风险利率
