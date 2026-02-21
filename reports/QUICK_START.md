# Tushare API 优化 - 快速开始

## 验证迁移

```bash
cd pro2/fund_search
python verify_migration.py
```

## 基础使用

### 1. 获取单只基金数据

```python
from data_retrieval import OptimizedFundData

fetcher = OptimizedFundData()
df = fetcher.get_fund_nav_history('000001')
print(df.head())
```

### 2. 批量获取（推荐）

```python
from data_retrieval import OptimizedFundData

fetcher = OptimizedFundData()
results = fetcher.batch_get_fund_nav(['000001', '000002', '000003'])

for code, df in results.items():
    print(f"{code}: {len(df)} 条数据")
```

### 3. 预加载数据

```python
# 预加载关注的基金
fetcher.preload_fund_data(['000001', '000002', '021539'])

# 后续获取会使用缓存，不触发API调用
df = fetcher.get_fund_nav_history('000001')
```

## 高级用法

### 性能测试

```python
python data_retrieval/migration_helper.py --benchmark \
  --fund-codes 000001,000002,000003,021539,100055
```

### 查看统计

```python
fetcher = OptimizedFundData()
stats = fetcher.get_optimized_stats()
print(stats)
```

### 速率限制监控

```python
from data_retrieval import get_tushare_limiter

limiter = get_tushare_limiter('fund_nav')
print(limiter.get_stats())
```

## 配置

### 环境变量

```bash
export TUSHARE_TOKEN=your_token
export FUND_DATA_ENABLE_BATCH=true
export FUND_DATA_ENABLE_RATE_LIMIT=true
```

### 代码配置

```python
from shared.fund_data_config import FundDataConfig

config = FundDataConfig(
    enable_batch=True,
    enable_rate_limit=True,
    enable_cache=True
)
```

## 向后兼容

```python
# 旧代码（仍然有效）
from data_retrieval.multi_source_fund_data import MultiSourceFundData
fetcher = MultiSourceFundData()

# 等价于新代码
from data_retrieval import OptimizedFundData
fetcher = OptimizedFundData()
```

## 优化效果

| 场景 | 迁移前 | 迁移后 |
|------|--------|--------|
| 100只基金首次获取 | 100次API调用, ~60s | 1次API调用, ~3s |
| 100只基金后续获取 | 100次API调用 | 0次(缓存) |
| 频率限制 | 触发 | 不触发 |

---

**开始使用优化后的代码吧！** 🚀
