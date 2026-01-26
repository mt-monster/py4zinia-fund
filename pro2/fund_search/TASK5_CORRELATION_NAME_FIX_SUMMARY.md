# Task 5: 修复相关性分析页面基金名称显示问题

## 问题描述

用户报告 `http://localhost:5000/correlation-analysis` 页面显示的是"基金013048"这样的格式，而不是真实的基金名称。

## 根本原因

经过详细测试发现：

1. **后端代码工作正常**：
   - `FundAnalyzer._get_fund_name()` 方法能够正确从数据库获取基金名称（Task 4已修复）
   - 测试显示所有基金名称都能正确获取

2. **缓存导致的问题**：
   - `FundAnalyzer.analyze_correlation()` 有24小时的缓存机制
   - 缓存中可能保存了旧数据（当时基金名称还未正确获取）
   - 每次调用都返回缓存的旧数据，导致显示"基金代码"而不是"基金名称"

## 解决方案

### 修改内容

**文件**: `pro2/fund_search/web/app.py`

在 `/api/holdings/analyze/correlation` API端点中添加 `use_cache=False` 参数：

```python
@app.route('/api/holdings/analyze/correlation', methods=['POST'])
def analyze_fund_correlation():
    """分析基金相关性"""
    try:
        # ... 省略验证代码 ...
        
        analyzer = FundAnalyzer()
        # 使用 use_cache=False 确保获取最新的基金名称
        result = analyzer.analyze_correlation(fund_codes, use_cache=False)
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"分析基金相关性失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
```

### 为什么这样修改

1. **绕过缓存**：`use_cache=False` 强制每次都重新计算相关性，确保使用最新的基金名称
2. **性能影响小**：相关性分析通常只涉及少量基金（2-6只），计算速度很快
3. **数据准确性优先**：对于用户主动触发的分析，实时性比性能更重要

## 测试验证

### 测试步骤

1. **重启Flask应用**（清除内存缓存）：
   ```bash
   python pro2/fund_search/web/app.py
   ```

2. **访问持仓页面**：
   - 打开 `http://localhost:5000/my_holdings`
   - 选择2只或更多基金
   - 点击"相关性分析"按钮

3. **验证结果**：
   - 新窗口应该显示真实的基金名称
   - 例如："富国中证新能源汽车指数(LOF)C" 而不是 "基金013048"

### 测试结果

```
=== 测试相关性分析 ===
基金代码: ['013048', '006106', '013277']
基金名称: ['富国中证新能源汽车指数(LOF)C', '景顺长城量化港股通股票A', '富国创业板ETF联接C']

相关性矩阵:
['1.0000', '0.6510', '0.8172']
['0.6510', '1.0000', '0.6936']
['0.8172', '0.6936', '1.0000']
```

✅ 基金名称正确显示

## 相关任务

- **Task 4**: 修复了 `_get_fund_name()` 方法，使其能够从多个数据库表中查询基金名称
- **Task 5**: 修复了缓存导致的基金名称显示问题

## 修改文件列表

1. `pro2/fund_search/web/app.py` - 添加 `use_cache=False` 参数
2. `pro2/fund_search/CORRELATION_NAME_DISPLAY_FIX.md` - 问题分析和解决方案文档
3. `pro2/fund_search/TASK5_CORRELATION_NAME_FIX_SUMMARY.md` - 本文档

## 注意事项

1. 如果未来需要恢复缓存功能（提高性能），可以：
   - 缩短缓存时间（从24小时改为1小时）
   - 在基金名称更新时清除相关缓存
   - 使用更智能的缓存失效策略

2. 当前方案优先保证数据准确性，性能影响可以忽略不计

## 完成日期

2026-01-26
