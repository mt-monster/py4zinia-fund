# 相关性分析页面基金名称显示问题修复

## 问题描述

用户报告 `http://localhost:5000/correlation-analysis` 页面显示的是"基金013048"这样的格式，而不是真实的基金名称（如"富国中证新能源汽车指数(LOF)C"）。

## 问题分析

经过测试，发现：

1. **后端代码工作正常**：
   - `FundAnalyzer._get_fund_name()` 方法能够正确从数据库获取基金名称
   - `FundAnalyzer.analyze_correlation()` 方法返回的数据包含正确的基金名称
   - 测试结果显示基金名称正确：
     ```
     013048: 富国中证新能源汽车指数(LOF)C
     006106: 景顺长城量化港股通股票A
     013277: 富国创业板ETF联接C
     ```

2. **数据库中有完整数据**：
   - `user_holdings` 表中有所有基金的名称
   - `fund_analysis_results` 表中也有所有基金的名称
   - `fund_basic_info` 表中没有这些基金（但不影响，因为会从其他表获取）

3. **可能的原因**：
   - **缓存问题**：`FundAnalyzer` 有24小时的缓存机制，可能缓存了旧数据
   - **浏览器缓存**：浏览器可能缓存了旧的分析结果

## 解决方案

### 方案1：清除缓存（推荐）

1. **清除服务器缓存**：
   - 重启Flask应用（`python pro2/fund_search/web/app.py`）
   - 或者在代码中调用 `analyzer.analyze_correlation(fund_codes, use_cache=False)`

2. **清除浏览器缓存**：
   - 在浏览器中按 `Ctrl + Shift + Delete` 清除缓存
   - 或者使用无痕模式/隐私模式重新测试

### 方案2：强制刷新（临时）

在相关性分析API中添加 `use_cache=False` 参数：

```python
# pro2/fund_search/web/app.py
@app.route('/api/holdings/analyze/correlation', methods=['POST'])
def analyze_fund_correlation():
    """分析基金相关性"""
    try:
        data = request.get_json()
        if not data or 'fund_codes' not in data:
            return jsonify({'success': False, 'error': '缺少基金代码'})
        
        fund_codes = data['fund_codes']
        if len(fund_codes) < 2:
            return jsonify({'success': False, 'error': '至少需要2只基金进行相关性分析'})
        
        from data_retrieval.fund_analyzer import FundAnalyzer
        
        analyzer = FundAnalyzer()
        # 添加 use_cache=False 强制刷新
        result = analyzer.analyze_correlation(fund_codes, use_cache=False)
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"分析基金相关性失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
```

### 方案3：修改缓存时间（长期）

如果需要更频繁地更新数据，可以修改缓存时间：

```python
# pro2/fund_search/data_retrieval/fund_analyzer.py
def analyze_correlation(self, fund_codes: List[str], use_cache: bool = True, 
                      min_data_points: int = 30) -> Dict:
    # ...
    if use_cache and self.enable_cache:
        cache_key = tuple(sorted(fund_codes))
        if cache_key in self._cache:
            cache_time = self._cache_time.get(cache_key)
            # 将缓存时间从86400秒(24小时)改为3600秒(1小时)
            if cache_time and (datetime.now() - cache_time).total_seconds() < 3600:
                logger.info(f"使用缓存结果: {cache_key}")
                return self._cache[cache_key]
    # ...
```

## 测试步骤

1. **重启Flask应用**：
   ```bash
   # 停止当前运行的应用
   # 重新启动
   python pro2/fund_search/web/app.py
   ```

2. **清除浏览器缓存**：
   - Chrome/Edge: `Ctrl + Shift + Delete` → 选择"缓存的图片和文件" → 清除数据
   - Firefox: `Ctrl + Shift + Delete` → 选择"缓存" → 立即清除

3. **重新测试**：
   - 访问 `http://localhost:5000/my_holdings`
   - 选择2只或更多基金
   - 点击"相关性分析"按钮
   - 检查新窗口中的基金名称是否正确显示

## 验证结果

测试后应该看到：

| 基金013048 | 基金006106 | 基金013277 |
|-----------|-----------|-----------|
| **之前（错误）** | **之前（错误）** | **之前（错误）** |

变为：

| 富国中证新能源汽车指数(LOF)C | 景顺长城量化港股通股票A | 富国创业板ETF联接C |
|--------------------------|---------------------|------------------|
| **正确显示** | **正确显示** | **正确显示** |

## 相关文件

- `pro2/fund_search/data_retrieval/fund_analyzer.py` - 相关性分析核心逻辑
- `pro2/fund_search/web/app.py` - API端点
- `pro2/fund_search/web/templates/correlation_analysis.html` - 前端页面
- `pro2/fund_search/web/templates/my_holdings.html` - 持仓页面（触发分析）

## 注意事项

1. Task 4中已经修复了`_get_fund_name()`方法，使其能够从多个表中查询基金名称
2. 后端代码工作正常，问题主要是缓存导致的
3. 如果清除缓存后仍有问题，请检查浏览器控制台的网络请求，查看API返回的实际数据

## 修复日期

2026-01-26
