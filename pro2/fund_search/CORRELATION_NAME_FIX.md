# 相关性分析页面基金名称显示修复

## 问题描述
在 `http://localhost:5000/correlation-analysis` 页面中，基金相关性矩阵显示的是基金代码而不是基金名称，导致用户无法直观地识别基金。

### 问题截图
相关性矩阵表头和行标签显示为：
- `基金013048`
- `基金006106`
- `基金013277`

而不是实际的基金名称。

## 根本原因
`FundAnalyzer` 类的 `_get_fund_name` 方法只从 `fund_basic_info` 表查询基金名称。如果该表中没有对应的基金数据，就会返回 `None`，导致后续使用基金代码作为显示名称。

### 原始代码
```python
def _get_fund_name(self, fund_code: str) -> Optional[str]:
    """从数据库获取基金名称"""
    try:
        sql = "SELECT fund_name FROM fund_basic_info WHERE fund_code = :fund_code"
        result = self.db_manager.execute_query_raw(sql, {'fund_code': fund_code})
        if result and len(result) > 0:
            return result[0][0]
        return None
    except Exception as e:
        logger.error(f"获取基金名称失败: {e}")
        return None
```

## 解决方案
增强 `_get_fund_name` 方法，使其按优先级从多个表中查询基金名称：

1. **fund_basic_info** 表（优先级最高）
2. **user_holdings** 表（用户持仓表）
3. **fund_analysis_results** 表（分析结果表）

### 修复后的代码
```python
def _get_fund_name(self, fund_code: str) -> Optional[str]:
    """
    从数据库获取基金名称
    
    参数：
    fund_code: 基金代码
    
    返回：
    str: 基金名称，如果不存在则返回None
    """
    try:
        # 首先尝试从 fund_basic_info 表获取
        sql = "SELECT fund_name FROM fund_basic_info WHERE fund_code = :fund_code"
        result = self.db_manager.execute_query_raw(sql, {'fund_code': fund_code})
        if result and len(result) > 0 and result[0][0]:
            return result[0][0]
        
        # 如果 fund_basic_info 表中没有，尝试从 user_holdings 表获取
        sql = "SELECT fund_name FROM user_holdings WHERE fund_code = :fund_code LIMIT 1"
        result = self.db_manager.execute_query_raw(sql, {'fund_code': fund_code})
        if result and len(result) > 0 and result[0][0]:
            return result[0][0]
        
        # 如果 user_holdings 表中也没有，尝试从 fund_analysis_results 表获取
        sql = "SELECT fund_name FROM fund_analysis_results WHERE fund_code = :fund_code ORDER BY analysis_date DESC LIMIT 1"
        result = self.db_manager.execute_query_raw(sql, {'fund_code': fund_code})
        if result and len(result) > 0 and result[0][0]:
            return result[0][0]
        
        return None
    except Exception as e:
        logger.error(f"获取基金名称失败: {e}")
        return None
```

## 修改的文件
- **pro2/fund_search/data_retrieval/fund_analyzer.py**
  - 方法: `_get_fund_name()`
  - 行数: 约 210-240

## 测试结果

### 测试数据
```
测试基金代码: ['013048', '013277', '006106']
```

### 测试输出
```
✅ 分析成功！

分析结果:
  - 基金代码: ['013277', '006106', '013048']
  - 基金名称: ['富国创业板ETF联接C', '景顺长城量化港股通股票A', '富国中证新能源汽车指数(LOF)C']
  - 数据点数: 240
  - 分析时间: 2026-01-26 10:51:55

基金名称检查:
  ✅ 013277: 富国创业板ETF联接C
  ✅ 006106: 景顺长城量化港股通股票A
  ✅ 013048: 富国中证新能源汽车指数(LOF)C
```

### 相关性矩阵显示
```
相关性矩阵:
    富国创业板ETF联接  景顺长城量化港股通股  富国中证新能源汽车指
  富国创业板ETF联接      1.0000      0.6936      0.8172
  景顺长城量化港股通股      0.6936      1.0000      0.6510
  富国中证新能源汽车指      0.8172      0.6510      1.0000
```

## 功能特性

### 1. 多数据源查询
- 按优先级从三个表中查询基金名称
- 确保即使某个表缺失数据，也能从其他表获取

### 2. 数据验证
- 检查查询结果是否为空
- 检查基金名称是否为 None
- 确保返回有效的基金名称

### 3. 错误处理
- 捕获数据库查询异常
- 记录错误日志
- 返回 None 而不是抛出异常

### 4. 向后兼容
- 保持原有的 API 接口不变
- 不影响其他使用该方法的代码
- 如果所有表都没有数据，仍然返回 None

## 影响范围

### 直接影响
- ✅ `/correlation-analysis` 页面现在正确显示基金名称
- ✅ 相关性矩阵的表头和行标签显示真实基金名称
- ✅ 用户可以直观识别基金

### 间接影响
- ✅ 所有调用 `FundAnalyzer.analyze_correlation()` 的代码都会受益
- ✅ 提高了系统的数据容错能力
- ✅ 减少了因单一数据源缺失导致的显示问题

## 注意事项

### 1. 数据库表依赖
修复依赖以下数据库表：
- `fund_basic_info` - 基金基本信息表
- `user_holdings` - 用户持仓表
- `fund_analysis_results` - 基金分析结果表

### 2. 性能考虑
- 查询按优先级进行，找到数据后立即返回
- 最坏情况下会执行3次数据库查询
- 建议在 `fund_basic_info` 表中维护完整的基金名称数据

### 3. 数据一致性
- 不同表中的基金名称可能略有差异
- 优先使用 `fund_basic_info` 表的数据（最权威）
- 建议定期同步各表的基金名称数据

## 后续优化建议

### 1. 添加缓存机制
```python
# 在 FundAnalyzer 类中添加名称缓存
self._name_cache = {}

def _get_fund_name(self, fund_code: str) -> Optional[str]:
    # 先检查缓存
    if fund_code in self._name_cache:
        return self._name_cache[fund_code]
    
    # 查询数据库...
    fund_name = ...
    
    # 保存到缓存
    if fund_name:
        self._name_cache[fund_code] = fund_name
    
    return fund_name
```

### 2. 批量查询优化
对于多个基金代码，可以使用 `IN` 查询一次性获取所有名称：
```python
def _get_fund_names_batch(self, fund_codes: List[str]) -> Dict[str, str]:
    """批量获取基金名称"""
    sql = "SELECT fund_code, fund_name FROM fund_basic_info WHERE fund_code IN :codes"
    # ...
```

### 3. 数据同步任务
创建定时任务，确保 `fund_basic_info` 表包含所有基金的最新名称。

## 验证步骤

1. 启动 Flask 应用：
   ```bash
   python pro2/fund_search/web/app.py
   ```

2. 访问持仓页面：
   ```
   http://localhost:5000/my_holdings
   ```

3. 选择至少2只基金

4. 点击"相关性分析"按钮

5. 在新打开的页面中验证：
   - ✅ 相关性矩阵表头显示基金名称而不是代码
   - ✅ 相关性矩阵行标签显示基金名称而不是代码
   - ✅ 基金名称完整且正确

## 总结
通过增强 `_get_fund_name` 方法，使其能够从多个数据源查询基金名称，成功解决了相关性分析页面基金名称显示问题。修复后的代码更加健壮，能够处理数据缺失的情况，提升了用户体验。
