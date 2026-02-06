# 基金相关性分析多基金显示修复

## 问题描述

用户在持仓页面选择3只基金进行相关性分析时，发现以下问题：

### 问题1：图表中只显示2只基金
- **净值走势对比图** 只显示2只基金的数据，缺失第3只基金
- **收益率分布对比图** 只显示2只基金的数据，缺失第3只基金

### 问题2：图表中显示基金代码而非基金名称
- 如图中所示，`006614` 显示为基金代码而不是基金名称（如"东方主题精选混合"）

## 根本原因

### 问题1原因
1. **后端数据结构设计问题**：后端 `generate_interactive_correlation_data` 方法虽然支持多基金分析，但返回的净值对比和收益率分布数据只包含第一对基金（基金1和基金2）的数据
2. **前端图表限制**：前端 `initLineChart` 和 `initDistributionChart` 函数只为两只基金的对比设计，没有处理多只基金的情况

### 问题2原因
`db_manager.get_fund_detail(code)` 方法从 `fund_basic_info` 表获取基金信息，如果该表中没有对应基金数据，就会返回 `None`，导致使用基金代码作为名称显示在图表中。

## 修复方案

### 1. 修复图表显示多只基金的问题

#### 1.1 后端修复 (`pro2/fund_search/backtesting/enhanced_correlation.py`)

**新增 `_generate_all_funds_nav_comparison` 方法**：
生成所有选中基金的净值对比数据。

**新增 `_generate_all_funds_distribution` 方法**：
生成所有选中基金的收益率分布数据。

**修改 `generate_interactive_correlation_data` 方法**：
在返回结果中添加 `all_funds_nav_comparison` 和 `all_funds_distribution` 字段。

#### 1.2 前端修复 (`pro2/fund_search/web/static/js/fund-correlation-charts.js`)

**修改 `initCorrelationCharts` 函数**：
优先使用多基金数据结构。

**修改 `initLineChart` 函数**：
支持多只基金的净值曲线显示，使用8种颜色方案。

**修改 `initDistributionChart` 函数**：
支持多只基金的收益率分布柱状图显示。

### 2. 修复基金名称显示问题

#### 2.1 后端修复 (`pro2/fund_search/web/app.py`)

**修改 `/api/holdings/analyze/correlation-interactive` 端点中的基金名称获取逻辑**：

```python
# 获取基金名称映射
fund_names = {}
for code in fund_codes:
    fund_name = None
    
    # 首先尝试从 fund_basic_info 表获取
    try:
        fund_info = db_manager.get_fund_detail(code)
        if fund_info and 'fund_name' in fund_info:
            fund_name = fund_info['fund_name']
    except Exception as e:
        logger.warning(f"从fund_basic_info获取基金 {code} 信息失败: {e}")
    
    # 如果fund_basic_info中没有，尝试从fund_analysis_results表获取
    if not fund_name:
        try:
            sql = """
            SELECT fund_name FROM fund_analysis_results 
            WHERE fund_code = %(fund_code)s 
            LIMIT 1
            """
            df = pd.read_sql(sql, db_manager.engine, params={'fund_code': code})
            if not df.empty and pd.notna(df.iloc[0]['fund_name']):
                fund_name = df.iloc[0]['fund_name']
        except Exception as e:
            logger.warning(f"从fund_analysis_results获取基金 {code} 名称失败: {e}")
    
    # 如果都没有找到，使用基金代码作为名称
    fund_names[code] = fund_name if fund_name else code
    
    logger.info(f"基金 {code} 的名称: {fund_names[code]}")
```

**改进点**：
1. 增加从 `fund_analysis_results` 表获取基金名称的备用方案
2. 添加异常处理，防止数据库查询失败导致整个流程中断
3. 添加日志记录，便于排查问题

## 测试结果

### 基金数量测试
使用3只基金进行测试：
- `all_funds_nav_comparison`: OK (3只基金)
- `all_funds_distribution`: OK (3只基金，7个区间)
- 每只基金364个数据点

### 基金名称测试
- ✅ 能够从 `fund_basic_info` 表获取基金名称
- ✅ 当 `fund_basic_info` 表中没有数据时，能够从 `fund_analysis_results` 表获取
- ✅ 图表中显示基金名称而非基金代码

测试结果: **通过** ✓

## 颜色方案

净值走势对比图和收益率分布对比图使用一致的颜色方案：
1. 🔵 蓝色
2. 🟢 绿色  
3. 🔴 红色
4. 🟠 橙色
5. 🟣 紫色
6. 🩷 粉色
7. 🩵 青色
8. 🔷 靛蓝

## 兼容性

- **向后兼容**：当后端返回旧数据结构时，前端会自动回退到双基金显示模式
- **向前兼容**：旧版本前端可以正常处理新数据结构（忽略额外字段）

## 修改的文件列表

1. `pro2/fund_search/backtesting/enhanced_correlation.py` - 后端数据生成（支持多基金显示）
2. `pro2/fund_search/web/static/js/fund-correlation-charts.js` - 前端图表渲染（支持多基金显示）
3. `pro2/fund_search/web/app.py` - API端点（修复基金名称获取逻辑）

## 验证步骤

1. 在持仓页面选择3只或更多基金
2. 点击"相关性分析"按钮
3. 在相关性分析页面验证以下图表：
   - **净值走势对比图**：确认所有选中的基金都显示为独立的曲线，且图例显示基金名称而非代码
   - **收益率分布对比图**：确认所有选中的基金都显示为独立的柱状图，且图例显示基金名称而非代码
4. 检查图例中显示的是基金名称（如"东方主题精选混合"）而不是基金代码（如"006614"）
