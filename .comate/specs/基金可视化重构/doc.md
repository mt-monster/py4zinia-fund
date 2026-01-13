# 基金可视化重构需求文档

## 需求背景
项目中的基金绩效对比图表在布局和图例设计方面存在可读性和美观性不足的问题，用户需要对这些图表进行重构优化。

## 当前问题分析
基于代码分析，目前的图表存在以下问题：
1. **布局拥挤**：多图表的对比显示混乱
2. **图例不清晰**：基金名称显示不完整，缺乏有效的标识
3. **颜色方案不统一**：不同业绩代表颜色缺乏一致的视觉编码
3. **信息密度过大**：大量数据点挤在有限空间内
4. **缺乏交互性**：静态图片无法提供详细信息

## 架构技术方案
### 重构策略
1. **统一可视化风格**：采用一致的配色方案和字体设置
2. **优化布局结构**：重新设计图表排列和间距
3. **改进图例设计**：使用更清晰的标识和位置安排
4. **增强可读性**：调整标签大小、位置和旋转角度
5. **交互功能增强**：添加悬停提示和数据筛选

### 影响文件
- `pro2/fund_search/search_01.py`：主要可视化代码文件（约1373行）
- 关键修改区域：`plot_performance_comparison` 函数族（日收益率、年化收益率、最大回撤、夏普比率、波动率对比）

### 实现细节
#### 1. 布局优化
```python
# 原设计：拥挤的2x1布局
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [2, 1]})
# 新设计：清晰的分列布局
fig = plt.figure(figsize=(16, 12))  # 增加整体尺寸
gs = fig.add_gridspec(2, 2, height_ratios=[2, 1], width_ratios=[3, 1]})
```

#### 2. 图例重构
```python
# 原设计：右侧拥挤的文本注释
ax.text(1.02, 0.45 - i*0.05, f'{code}: {name}', transform=ax.transAxes)

# 新设计：智能位置排列
max_name_len = max(len(name) for name in fund_names)
optimized_y_pos = calculate_optimized_positions(n_funds, max_name_len))
```

#### 3. 颜色方案标准化
```python
# 统一配色方案
COLOR_POLETTE = {
    'positive': '#2E8B57',  # 绿色系
    'negative': '#CD5C5C',  # 红色系
    'neutral': '#2D97F2',  # 蓝色系
    'performance_good': '#2CA02C',
    'performace_poor': '#D62728',
    'volatility_low': '#9467BD',
    'volatility_high': '#8C56A1'
}
```

#### 4. 交互功能
```python
# 悬停提示功能
def add_tooltip(axis, fund_code, fund_name, value):
    """添加鼠标悬停显示详细信息的工具提示"""
    pass
```

## 边界条件与异常处理
- **空数据处理**：当基金数据为空时提供友好的提示信息
- **过长名称处理**：智能截断和完整显示策略
- **异常值过滤**：自动识别并处理极端异常值

## 数据流动路径
1. 数据库查询 → 性能指标计算 → 数据格式化 → 图表生成 → 文件保存

## 预期成果
- 美观统一的基金绩效对比图表
- 清晰易读的图例和标签
- 更好的数据可视化效果
```