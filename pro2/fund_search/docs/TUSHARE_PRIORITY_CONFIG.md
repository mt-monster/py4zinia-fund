# Tushare 优先数据源配置说明

## 概述

系统已统一配置为优先从 **Tushare** 获取数据，当 Tushare 不可用时自动降级到其他数据源。

## 数据源优先级

### 1. 实时数据获取（日涨跌幅等）

**RealtimeDataFetcher 优先级：**

1. **Tushare**（主要数据源）
   - 稳定性高
   - 需要 `.OF` 后缀格式
   - 提供单位净值、累计净值

2. **天天基金**（实时性好）
   - 提供估算净值和估算涨跌幅
   - 最实时但不支持所有基金

3. **新浪**（备用）
   - 实时性好
   - 部分基金可能不支持

4. **AKShare**（降级）
   - 数据全面
   - 作为最后备选

### 2. 历史数据获取（净值历史等）

**MultiSourceFundData 优先级：**

1. **Tushare**（PRIMARY）
   - 成功率监控
   - 失败率过高时自动降级

2. **AKShare**（BACKUP_1）
   - 数据全面
   - 格式兼容性好

## 配置方法

### Tushare Token 配置

**方式1：环境变量**
```bash
export TUSHARE_TOKEN="your_token_here"
```

**方式2：配置文件**（`shared/enhanced_config.py`）
```python
DATA_SOURCE_CONFIG = {
    'tushare': {
        'token': 'your_token_here',
        'timeout': 30,
        'max_retries': 3
    }
}
```

### 数据源降级条件

当以下情况发生时，系统自动降级到备用数据源：

1. Tushare 成功率 < 70%
2. AKShare 成功率 > Tushare 成功率 + 20%
3. Tushare API 返回错误
4. 网络超时

## 验证 Tushare 优先

### 方法1：查看日志

启动应用后查看日志，应包含：
```
INFO - Tushare 初始化成功
INFO - 使用 PRIMARY 数据源 Tushare 获取 {fund_code}
```

### 方法2：运行测试脚本

```bash
cd pro2/fund_search
python test_tushare_priority.py
```

### 方法3：查看数据源字段

API 返回的数据中包含 `source` 或 `data_source` 字段：
```json
{
  "fund_code": "016667",
  "today_return": 1.69,
  "source": "tushare"
}
```

## QDII 基金特殊处理

QDII 基金由于时差原因，数据更新可能延迟。系统已针对 QDII 基金进行特殊处理：

1. **前向追溯**：当昨日收益率为0时，向前查找最近的非零收益率
2. **Tushare 优先**：优先使用 Tushare 的 QDII 数据接口

## 故障排除

### Tushare 初始化失败

**症状：**
```
WARNING - Tushare 初始化失败
```

**解决方案：**
1. 检查 token 是否有效
2. 检查网络连接
3. 查看 Tushare 官网服务状态

### 数据获取失败

**症状：**
```
WARNING - 所有实时数据源都失败
```

**解决方案：**
1. 检查基金代码是否正确
2. 检查网络连接
3. 查看日志中的具体错误信息
4. 系统会自动降级到其他数据源

## 性能优化

### 缓存策略

1. **内存缓存**：2分钟（实时数据）
2. **数据库缓存**：1天（昨日数据）
3. **绩效缓存**：1天（年化收益、夏普比率等）

### 并发控制

- 批量获取数据时使用线程池（默认5个并发）
- 避免短时间内重复请求同一基金

## 相关文件

| 文件 | 说明 |
|------|------|
| `services/holding_realtime_service.py` | RealtimeDataFetcher 类，Tushare 优先获取实时数据 |
| `data_retrieval/multi_source_fund_data.py` | MultiSourceFundData 类，Tushare 优先获取历史数据 |
| `data_retrieval/multi_source_adapter.py` | MultiSourceDataAdapter 类，整合缓存策略 |
| `shared/enhanced_config.py` | 数据源配置 |
| `test_tushare_priority.py` | 测试脚本 |

## 更新日志

### 2026-02-11
- 统一配置为 Tushare 优先
- RealtimeDataFetcher 添加 Tushare 数据源
- 修改数据源优先级：Tushare > 天天基金 > 新浪 > AKShare
