# 图表闪烁问题 - 快速排查清单

## 🔍 立即检查（30秒）

### 打开浏览器控制台（F12），查找以下信息：

#### ✅ 正常情况
```
📊 开始绘制净值曲线，数据点数量: 1095
📊 基金详细数据: 3 个基金
✅ 净值曲线绘制完成
```

#### ❌ 异常情况1：重复绘制
```
⚠️ 图表正在绘制中，跳过重复调用  // 反复出现
```
**原因**：多处同时调用绘制
**已修复**：添加了 `isDrawing` 标记

#### ❌ 异常情况2：无基金数据
```
📊 基金详细数据: 0 个基金
⚠️ window.lastBacktestResult.funds 为空
```
**原因**：后端未返回单个基金详细数据
**影响**：只能看到组合总净值和基准线，看不到单个基金曲线

#### ❌ 异常情况3：Observer频繁触发
```
🔍 MutationObserver: 检测到外部DOM变化  // 反复出现
⚙️ MutationObserver: 开始重新计算分析...  // 反复出现
```
**原因**：DOM变化触发连锁反应
**已修复**：优化了Observer过滤逻辑

## 🎯 快速解决方案

### 方案1：检查后端数据（最可能）

在控制台输入：
```javascript
console.log(window.lastBacktestResult?.funds?.length);
```

- **如果输出 `0` 或 `undefined`** → 后端问题，需要修改后端返回数据
- **如果输出数字（如 `3`）** → 继续检查数据完整性

```javascript
window.lastBacktestResult.funds.forEach(f => {
    console.log(f.fund_code, '净值点数:', f.equity_curve?.length);
});
```

### 方案2：临时禁用Observer（测试用）

如果怀疑是Observer导致闪烁，在控制台输入：
```javascript
// 停止观察
PortfolioAnalysis.observeBacktestResults = () => {};
// 刷新页面后再次回测
```

### 方案3：手动重绘（应急）

如果图表消失，在控制台输入：
```javascript
// 获取最后的净值数据
const navData = PortfolioAnalysis.analysisData?.navData;
if (navData) {
    PortfolioAnalysis.drawNavChart(navData);
}
```

## 📊 预期显示内容

### 完整图表包含：
1. ✅ **组合净值**（蓝色粗线）- 必有
2. ✅ **沪深300基准**（红色粗线）- 必有
3. ⚠️ **单个基金曲线**（半透明细线）- 需要后端数据
4. ⚠️ **买卖点标记**（圆点）- 需要后端trades数据
5. ✅ **坐标轴和图例** - 必有

### 如果只看到1+2
→ **这是正常的降级显示**，说明后端未返回单个基金详细数据

### 如果完全看不到图表
→ 可能是以下原因：
- Canvas未渲染（检查DOM）
- 数据为空（检查 `navData`）
- 持续重绘导致闪烁（检查Observer日志）

## 🛠️ 已修复的问题

1. ✅ 防止重复绘制（`isDrawing` 标记）
2. ✅ 优化MutationObserver过滤
3. ✅ 延长绘制延迟到300ms
4. ✅ 增加详细调试日志
5. ✅ 添加数据完整性检查

## 📝 需要后端支持

如果要显示**单个基金曲线**，后端回测接口需要返回：

```python
{
    "funds": [
        {
            "fund_code": "001234",
            "equity_curve": [  # ← 必需
                {"date": "2024-01-01", "value": 10000},
                {"date": "2024-01-02", "value": 10050},
                ...
            ],
            "trades": [  # ← 可选，用于买卖点标记
                {"type": "buy", "date": "2024-01-01", ...},
                ...
            ]
        }
    ]
}
```

**如果后端不返回 `equity_curve`**：
- 前端会正常显示组合净值和基准线
- 但无法显示单个基金的曲线

## 🔗 相关文档

- 详细调试指南：`CHART_FLASH_DEBUG.md`
- 完整修复文档：`PORTFOLIO_METRICS_FIX.md`
- 快速参考：`QUICK_FIX_SUMMARY.md`
