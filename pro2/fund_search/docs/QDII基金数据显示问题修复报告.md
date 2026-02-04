# QDII基金数据显示问题修复报告

## 问题描述

在"我的持仓"页面（http://localhost:5000/my-holdings-new）中，QDII基金的日涨跌幅等数据未正常加载或显示。

## 问题排查过程

### 1. 前端检查
- ✅ 前端代码正常，QDII标签显示功能已实现
- ✅ 数据渲染逻辑正确，`today_return`、`yesterday_return`等字段都有正确的格式化处理
- ✅ API调用正常，使用`/api/holdings`接口获取数据

### 2. 后端API检查
- ✅ `/api/holdings` GET接口正常返回数据
- ✅ 数据库查询逻辑正确，联表查询`user_holdings`和`fund_analysis_results`

### 3. 数据获取逻辑检查
- ⚠️ **发现问题**：在`enhanced_fund_data.py`中，`get_realtime_data()`方法需要`fund_name`参数来正确识别QDII基金
- ⚠️ **发现问题**：多处调用`get_realtime_data()`时未传入`fund_name`参数

## 根本原因

QDII基金的数据获取策略与普通基金不同：
- **普通基金**：使用新浪财经实时估算接口（分钟级更新）
- **QDII基金**：使用AKShare历史净值接口（日级更新）

`EnhancedFundData.is_qdii_fund()`方法通过两种方式识别QDII基金：
1. 检查基金代码是否在预定义的`QDII_FUND_CODES`列表中
2. 检查基金名称是否包含"QDII"关键词

**问题所在**：在以下位置调用`get_realtime_data()`时，未传入`fund_name`参数：
1. `app.py` - `/api/holdings/<fund_code>` PUT接口（更新持仓时）
2. `app.py` - `/api/holdings/import/confirm` POST接口（导入持仓时）
3. `enhanced_main.py` - 批量分析基金时

这导致不在预定义列表中的QDII基金无法被正确识别，从而使用了错误的数据获取策略。

## 修复方案

### 修复内容

#### 1. `pro2/fund_search/web/app.py` - 第2482行
```python
# 修复前
realtime_data = fund_data_manager.get_realtime_data(fund_code)

# 修复后
realtime_data = fund_data_manager.get_realtime_data(fund_code, fund_name)
```

#### 2. `pro2/fund_search/web/app.py` - 第3291行
```python
# 修复前
realtime_data = EnhancedFundData.get_realtime_data(fund_code)

# 修复后
realtime_data = EnhancedFundData.get_realtime_data(fund_code, fund_name)
```

#### 3. `pro2/fund_search/enhanced_main.py` - 第1218行
```python
# 修复前
fund_info = self.fund_data_manager.get_realtime_data(fund_code)

# 修复后
fund_info = self.fund_data_manager.get_realtime_data(fund_code, fund_name)
```

### 修复效果

修复后，系统能够正确识别所有QDII基金（包括不在预定义列表中的），并使用正确的数据获取策略：
- QDII基金将使用AKShare接口获取历史净值数据
- 日涨跌幅、昨日涨跌幅等数据将正常显示
- 持仓盈亏计算将基于正确的净值数据

## 验证步骤

1. 重启Flask应用：
   ```bash
   cd pro2/fund_search/web
   python app.py
   ```

2. 访问"我的持仓"页面：http://localhost:5000/my-holdings-new

3. 检查QDII基金的数据显示：
   - 日涨跌幅（今日收益率）
   - 昨日涨跌幅
   - 当日盈亏
   - 持有盈亏
   - 累计盈亏

4. 测试更新持仓功能：
   - 编辑QDII基金持仓
   - 保存后检查数据是否正确刷新

5. 测试导入持仓功能：
   - 导入包含QDII基金的持仓数据
   - 检查导入后的数据是否正确显示

## 相关文件

- `pro2/fund_search/data_retrieval/enhanced_fund_data.py` - QDII基金数据获取逻辑
- `pro2/fund_search/web/app.py` - API接口
- `pro2/fund_search/enhanced_main.py` - 批量分析逻辑
- `pro2/fund_search/web/templates/my_holdings.html` - 前端页面

## 注意事项

1. **QDII基金列表维护**：
   - 预定义的`QDII_FUND_CODES`列表位于`enhanced_fund_data.py`第28-44行
   - 如需添加新的QDII基金代码，请更新该列表

2. **数据更新频率**：
   - QDII基金数据来自AKShare，更新频率为每日一次
   - 不会有实时估算数据，显示的是最新一日的净值数据

3. **错误处理**：
   - 如果AKShare接口失败，系统会尝试从数据库获取历史数据
   - 如果所有数据源都失败，会返回默认值（0.0）

## 修复日期

2026-02-04

## 修复人员

Kiro AI Assistant
