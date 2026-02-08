# 基金净值曲线可视化增强

## 🎯 优化目标

在投资组合净值图表中同时显示：
1. ✅ 组合净值曲线（蓝色粗线）
2. ✅ 沪深300基准（红色粗线）
3. ✅ **每个基金的单独净值曲线**（彩色实线）
4. ✅ 统一横纵坐标，确保所有曲线清晰可见

## 📊 优化内容

### 1. 增强基金曲线可见度

**文件**：`portfolio-analysis-integrated.js` → `drawFundCurve()` 方法

#### 优化前
```javascript
ctx.globalAlpha = 0.7;      // 透明度偏低
ctx.lineWidth = 2;          // 线条较细
ctx.setLineDash([6, 3]);    // 虚线不清晰
```

#### 优化后
```javascript
ctx.globalAlpha = 0.85;     // 提高透明度 ✅
ctx.lineWidth = 2.5;        // 加粗线条 ✅
ctx.setLineDash([]);        // 改为实线 ✅
ctx.shadowBlur = 3;         // 增强阴影 ✅
```

**改进效果**：
- ✅ 更高的透明度（0.7 → 0.85）
- ✅ 更粗的线条（2px → 2.5px）
- ✅ 实线替代虚线（更清晰）
- ✅ 更强的阴影效果

### 2. 优化配色方案

**文件**：`portfolio-analysis-integrated.js` → `drawNavChart()` 方法（第1581行）

#### 优化前
```javascript
const fundColors = [
    '#9D84B7',  // 紫罗兰（偏淡）
    '#F4A582',  // 橙粉色（偏淡）
    '#92C5DE',  // 浅蓝色（偏淡）
    '#F9D423',  // 黄色
    '#66C7F4'   // 浅蓝色（偏淡）
];
```

#### 优化后
```javascript
const fundColors = [
    '#9C27B0',  // 紫色 - 鲜明醒目 ✅
    '#FF6B6B',  // 橙红色 - 温暖明亮 ✅
    '#4ECDC4',  // 青绿色 - 清新活泼 ✅
    '#FFD93D',  // 金黄色 - 显眼明快 ✅
    '#6BCF7F',  // 翠绿色 - 生机盎然 ✅
    '#FF8C42',  // 橙色 - 活力四射 ✅
    '#95E1D3',  // 薄荷绿 - 柔和清晰 ✅
    '#F38181'   // 粉红色 - 柔美醒目 ✅
];
```

**改进效果**：
- ✅ 8种颜色（原5种）→ 支持更多基金
- ✅ 对比度更高，视觉区分度强
- ✅ 饱和度提升，更鲜艳醒目

### 3. 增强图例显示

**文件**：`portfolio-analysis-integrated.js` → `drawLegendWithFunds()` 方法

#### 优化前
```javascript
// 简单图例，透明度低
ctx.globalAlpha = 0.4;
ctx.fillRect(legendX, legendY, 20, 3);  // 细线
ctx.fillStyle = '#666';  // 灰色文字
```

#### 优化后
```javascript
// 带半透明背景的图例框
ctx.fillStyle = 'rgba(255, 255, 255, 0.92)';
ctx.fillRect(legendX - 5, legendY - 8, 150, legendHeight);

// 绘制实线样本
ctx.lineWidth = 2.5;
ctx.globalAlpha = 0.85;
ctx.moveTo(legendX, legendY);
ctx.lineTo(legendX + 25, legendY);

// 分隔线区分不同类型
ctx.strokeStyle = '#e0e0e0';
ctx.beginPath();
ctx.moveTo(legendX, legendY);
ctx.lineTo(legendX + 135, legendY);
ctx.stroke();
```

**改进效果**：
- ✅ 白色半透明背景，提高可读性
- ✅ 边框分隔，结构更清晰
- ✅ 实线样本（粗2.5px），与曲线一致
- ✅ 分隔线区分主曲线和基金曲线
- ✅ 显示基金代码和名称（截取6字符）

### 4. 增加调试日志

**优化后的日志输出**：
```javascript
console.log(`📊 准备绘制 ${fundsWithDetails.length} 个基金的净值曲线`);
fundsWithDetails.forEach((fund, index) => {
    console.log(`  - 基金 ${fund.fund_code}: ${color}, 数据点: ${fund.equity_curve.length}`);
});
console.log(`📈 绘制基金曲线: ${fund.fund_code}, 颜色: ${color}, 数据点: ${matchedPoints.length}`);
```

**用途**：
- 验证基金数据是否正确加载
- 检查每个基金的数据点数量
- 确认颜色分配

## 📐 统一坐标系统

### Y轴范围计算（自动适配）

```javascript
// 收集所有曲线的值
let allValues = [
    ...data.map(d => d.portfolio),    // 组合净值
    ...data.map(d => d.benchmark)      // 基准线
];

// 添加各基金净值
fundsWithDetails.forEach(fund => {
    if (fund.equity_curve && fund.equity_curve.length > 0) {
        allValues = allValues.concat(fund.equity_curve.map(p => p.value));
    }
});

// 计算最小值和最大值
const minValue = Math.min(...allValues);
const maxValue = Math.max(...allValues);
const padding = (maxValue - minValue) * 0.1;  // 10%边距

// 应用到所有曲线
const yMin = minValue - padding;
const yMax = maxValue + padding;
```

**关键点**：
- ✅ 包含所有曲线的数据点
- ✅ 自动计算最优Y轴范围
- ✅ 10%边距确保不贴边
- ✅ 所有曲线使用相同坐标系

### X轴时间对齐

```javascript
// 创建日期映射
const dateMap = {};
this.chartState.data.forEach((point, index) => {
    dateMap[point.date] = index;
});

// 匹配基金曲线的时间点
fund.equity_curve.forEach((point) => {
    const mappedIndex = dateMap[point.date];
    if (mappedIndex !== undefined) {
        matchedPoints.push({ dataIndex: mappedIndex, value: point.value });
    }
});
```

**关键点**：
- ✅ 基于日期对齐，不是简单的索引映射
- ✅ 支持不同长度的数据序列
- ✅ 确保时间轴一致

## 🎨 视觉层次

### 绘制顺序（从底层到顶层）

```
1. 背景和网格线（最底层）
   ├─ 灰色背景
   └─ 坐标轴和刻度

2. 基金净值曲线（中层）
   ├─ 基金1: 紫色实线 (2.5px)
   ├─ 基金2: 橙红实线 (2.5px)
   ├─ 基金3: 青绿实线 (2.5px)
   └─ ...

3. 买卖点标记（中上层）
   ├─ 买入: 绿色上三角
   └─ 卖出: 红色下三角

4. 主曲线（顶层，最醒目）
   ├─ 组合净值: 蓝色粗线 (3.5px)
   └─ 沪深300: 红色粗线 (3.5px)

5. 图例（覆盖层）
   └─ 半透明白色背景 + 边框
```

**设计原则**：
- ✅ 主曲线最粗（3.5px），最显眼
- ✅ 基金曲线适中（2.5px），清晰可见
- ✅ 实线区分优先级（实线 > 虚线）
- ✅ 颜色差异大，避免混淆

## 📋 使用示例

### 控制台输出示例

执行回测后，查看控制台：

```
📊 准备绘制 3 个基金的净值曲线
  - 基金 000001: #9C27B0, 数据点: 730
  - 基金 000002: #FF6B6B, 数据点: 730
  - 基金 000003: #4ECDC4, 数据点: 730
📈 绘制基金曲线: 000001, 颜色: #9C27B0, 数据点: 728
📈 绘制基金曲线: 000002, 颜色: #FF6B6B, 数据点: 730
📈 绘制基金曲线: 000003, 颜色: #4ECDC4, 数据点: 729
✅ 净值曲线绘制完成（含基金曲线和买卖点）
```

### 图表效果

```
图例框（左上角，白色半透明背景）：
┌─────────────────────┐
│ ━━━ 组合净值        │ (蓝色粗线 3.5px)
│ ━━━ 沪深300         │ (红色粗线 3.5px)
│ ────────────────    │ (分隔线)
│ ━━━ 000001 华夏成长 │ (紫色 2.5px)
│ ━━━ 000002 南方稳健 │ (橙红 2.5px)
│ ━━━ 000003 易方达   │ (青绿 2.5px)
│ ────────────────    │ (分隔线)
│  ▲  买入点          │ (绿色三角)
│  ▼  卖出点          │ (红色三角)
└─────────────────────┘
```

## ✅ 验证检查

### 1. 视觉检查
- [ ] 能看到所有基金曲线（不同颜色）
- [ ] 曲线粗细适中，清晰可辨
- [ ] 颜色对比度高，不会混淆
- [ ] 图例完整显示所有曲线

### 2. 数据检查
- [ ] 控制台显示基金数量和数据点
- [ ] 每个基金都有对应的绘制日志
- [ ] 无"equity_curve为空"的警告

### 3. 坐标检查
- [ ] Y轴范围包含所有曲线
- [ ] 曲线不会超出边界
- [ ] 时间轴对齐，无错位

## 🐛 常见问题

### Q1: 看不到基金曲线
**原因**：回测结果中没有 `equity_curve` 数据  
**检查**：
```javascript
console.log(window.lastBacktestResult.funds);
// 应该看到类似：
// [{fund_code: "000001", equity_curve: [{date: "2024-01-01", value: 10000}, ...]}]
```

### Q2: 曲线颜色太淡
**解决**：已优化透明度从0.7→0.85，并增强阴影

### Q3: 曲线重叠看不清
**解决**：
- 8种高对比度颜色
- 不同粗细（主曲线3.5px，基金2.5px）
- 图例明确标注

## 📄 相关文件

- 主文件：`portfolio-analysis-integrated.js`
  - `drawNavChart()` - 主绘图方法（第1472行）
  - `drawFundCurve()` - 基金曲线绘制（第2127行）
  - `drawLegendWithFunds()` - 图例绘制（第2285行）

- 数据源：`window.lastBacktestResult.funds`
  - 需要包含 `equity_curve` 字段
  - 格式：`[{date: "YYYY-MM-DD", value: 10000}, ...]`

---

**优化完成时间**: 2026-02-08  
**优化目标**: 提高基金曲线可见度，统一坐标系统，优化配色和图例
