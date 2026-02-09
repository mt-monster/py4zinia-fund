# 多数据源基金数据获取模块使用指南

## 快速开始

### 1. 基本使用

```python
from fund_search.data_retrieval.multi_source_fund_data import MultiSourceFundData

# 初始化（使用新的数据源优先级）
# Tushare作为主数据源，Akshare作为第一备用
fetcher = MultiSourceFundData(tushare_token="your_token")

# 获取基金历史净值（自动使用最优数据源）
df = fetcher.get_fund_nav_history("021539")
print(df.head())

# 获取最新净值（自动降级）
latest = fetcher.get_fund_latest_nav("021539")
print(f"最新净值: {latest['nav']}")
print(f"数据来源: {latest['source']}")  # tushare / akshare / sina / eastmoney
```

### 2. 数据源优先级

**当前配置** (v2.0):

```
获取数据流程:
┌─────────────┐    失败    ┌─────────────┐    失败    ┌─────────────┐
│  Tushare    │ ─────────► │   Akshare   │ ─────────► │ Sina/EM     │
│  (PRIMARY)  │            │ (BACKUP_1)  │            │ (BACKUP_2)  │
└─────────────┘            └─────────────┘            └─────────────┘
     │                          │                          │
     ▼                          ▼                          ▼
  返回数据                   返回数据                   返回数据
```

**降级条件**:
- Tushare 成功率 < 70%
- Akshare 成功率比 Tushare 高 20% 以上

### 3. QDII基金处理

```python
# 判断是否为QDII
is_qdii = fetcher.is_qdii_fund("021539", "华安法国CAC40ETF发起式联接(QDII)A")

# 获取QDII基金数据（自动特殊处理，同样遵循Tushare优先）
qdii_data = fetcher.get_qdii_fund_data("021539")
print(f"净值: {qdii_data['current_nav']}")
print(f"数据来源: {qdii_data['data_source']}")  # 可能是 tushare 或 akshare
print(f"更新延迟: {qdii_data['update_delay']}")  # T+2
```

### 4. 数据源选择

```python
# 强制使用akshare（忽略优先级）
df = fetcher.get_fund_nav_history("021539", source="akshare")

# 强制使用tushare
df = fetcher.get_fund_nav_history("021539", source="tushare")

# 自动选择(根据健康状态和优先级)
df = fetcher.get_fund_nav_history("021539", source="auto")
```

---

## 高级功能

### 健康监控

```python
# 获取数据源健康状态
health = fetcher.get_health_status()
print(health)

# 输出:
# {
#     'tushare': {
#         'success_rate': '98.2%',      # Tushare成功率更高
#         'avg_response_time': '0.823s', # 响应更快
#         'total_requests': 100,
#         'last_error': None
#     },
#     'akshare': {
#         'success_rate': '95.1%',
#         'avg_response_time': '1.456s',
#         'total_requests': 100,
#         'last_error': None
#     },
#     'recommend_source': 'tushare'  # 推荐主数据源
# }
```

### 代码格式自动转换

```python
# Tushare 需要 .OF 后缀，系统自动处理

# 传入原始代码
result = fetcher.get_fund_latest_nav("021539")

# 系统内部自动转换为 021539.OF 调用 Tushare
# 返回结果使用原始代码格式
print(result['fund_code'])  # "021539" (不是 "021539.OF")
```

### 日期范围筛选

```python
# 获取近30天数据
from datetime import datetime, timedelta

end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

df = fetcher.get_fund_nav_history(
    "021539",
    start_date=start_date,
    end_date=end_date
)
```

---

## 与现有代码集成

### 替换现有akshare调用

**原代码**:
```python
import akshare as ak

nav = ak.fund_open_fund_daily_em(symbol="021539")
```

**新代码**:
```python
from fund_search.data_retrieval.multi_source_fund_data import MultiSourceFundData

fetcher = MultiSourceFundData(tushare_token="your_token")
nav = fetcher.get_fund_nav_history("021539")  # 优先使用Tushare
```

### 在项目中的使用

```python
# 在 enhanced_fund_data.py 中使用

class EnhancedFundData:
    # 添加多数据源支持
    _multi_source_fetcher = None
    
    @classmethod
    def get_fetcher(cls):
        if cls._multi_source_fetcher is None:
            from fund_search.shared.enhanced_config import DATA_SOURCE_CONFIG
            token = DATA_SOURCE_CONFIG['tushare']['token']
            cls._multi_source_fetcher = MultiSourceFundData(tushare_token=token)
        return cls._multi_source_fetcher
    
    @staticmethod
    def get_fund_realtime_data(fund_code: str) -> Dict:
        fetcher = EnhancedFundData.get_fetcher()
        
        # 自动判断QDII
        if fetcher.is_qdii_fund(fund_code):
            return fetcher.get_qdii_fund_data(fund_code)
        
        # 使用新的优先级获取数据 (Tushare > Akshare > Sina > EM)
        return fetcher.get_fund_latest_nav(fund_code)
```

---

## 配置建议

### 1. 环境变量配置

```bash
# .env 文件

# Tushare 配置 (PRIMARY) - 必须配置
TUSHARE_TOKEN=5ff19facae0e5b26a407d491d33707a9884a39a714a0d76b6495725b
TUSHARE_TIMEOUT=30
TUSHARE_RETRIES=3

# Akshare 配置 (BACKUP_1)
AKSHARE_TIMEOUT=30
AKSHARE_RETRIES=3
AKSHARE_DELAY=1.0

# Fallback 配置 (BACKUP_2)
SINA_ENABLED=true
EASTMONEY_ENABLED=true
FALLBACK_TIMEOUT=10
```

### 2. 配置文件导入

```python
from fund_search.shared.enhanced_config import DATA_SOURCE_CONFIG

# 获取配置
tushare_config = DATA_SOURCE_CONFIG['tushare']
akshare_config = DATA_SOURCE_CONFIG['akshare']
priority_config = DATA_SOURCE_CONFIG['priority']

print(f"主数据源: {priority_config['primary']}")  # tushare
print(f"第一备用: {priority_config['backup_1']}")  # akshare
print(f"第二备用: {priority_config['backup_2']}")  # ['sina', 'eastmoney']
```

### 3. 日志配置

```python
import logging

# 启用调试日志
logging.getLogger('fund_search.data_retrieval.multi_source_fund_data').setLevel(logging.DEBUG)

# 日志输出示例:
# INFO - 使用 PRIMARY 数据源 Tushare 获取 021539
# INFO - 从 Tushare 成功获取 021539 最新净值
#
# 降级时:
# WARNING - Tushare获取 021539 失败: Connection timeout
# INFO - 使用 BACKUP_1 数据源 Akshare 获取 021539
# INFO - 从 Akshare 成功获取 021539 最新净值 (BACKUP_1)
```

---

## 常见问题

### Q1: Tushare token无效怎么办？

```python
# 方式1: 不传入token，系统会使用环境变量或默认值
fetcher = MultiSourceFundData()

# 方式2: 如果Tushare完全不可用，强制使用Akshare
df = fetcher.get_fund_nav_history("021539", source="akshare")
```

### Q2: 如何强制使用特定数据源？

```python
# 强制使用Tushare (PRIMARY)
df = fetcher.get_fund_nav_history("021539", source="tushare")

# 强制使用Akshare (BACKUP_1)
df = fetcher.get_fund_nav_history("021539", source="akshare")

# 使用内部方法 (不推荐，除非有特殊需求)
df = fetcher._get_nav_from_tushare("021539.OF")  # 注意: 需要.OF后缀
df = fetcher._get_nav_from_akshare("021539")
df = fetcher._get_nav_from_fallback("021539")  # Sina/EM
```

### Q3: 如何处理网络超时？

```python
# 方式1: 增加超时时间
fetcher = MultiSourceFundData(timeout=30)

# 方式2: 使用重试装饰器
from fund_search.data_retrieval.multi_source_fund_data import retry_on_failure

@retry_on_failure(max_retries=5, delay=2)
def get_data():
    return fetcher.get_fund_nav_history("021539")

# 方式3: 多数据源自动降级，无需额外处理
# 系统会自动尝试下一个数据源
```

### Q4: 为什么返回的数据代码格式不对？

```python
# Tushare返回的代码是 021539.OF，但系统已自动转换
result = fetcher.get_fund_latest_nav("021539")
print(result['fund_code'])  # "021539" (已去除.OF后缀)

# 如果需要原始格式，可以查看source字段
print(result['source'])  # "tushare" 或 "akshare" 等
```

### Q5: QDII基金数据为什么会有延迟？

QDII基金T+2更新是正常现象：

```python
qdii_data = fetcher.get_qdii_fund_data("021539")
print(qdii_data['update_delay'])  # "T+2"
print(qdii_data['note'])  # "QDII基金净值T+2更新，受汇率影响"

# 系统会自动向前追溯获取最新数据
# 不需要手动处理
```

---

## 性能对比

### 响应时间对比

| 操作 | Tushare | Akshare | Sina | Eastmoney | 推荐 |
|------|---------|---------|------|-----------|------|
| 获取历史净值 | 0.5-2s | 1-3s | N/A | 1-2s | **Tushare** |
| 获取最新净值 | 0.5-1s | 1-2s | 0.2-1s | 1-2s | **Tushare** |
| 获取基本信息 | 1-2s | 2-4s | N/A | N/A | **Tushare** |
| QDII基金 | ✓ | ✓ | ✗ | ✓ | **Tushare/Akshare** |
| 实时数据 | ✗ | ✗ | ✓ | ✗ | **Sina** |

### 成功率对比

| 数据源 | 成功率 | 稳定性 | 适用场景 |
|-------|-------|-------|---------|
| **Tushare** | 98% | ⭐⭐⭐⭐⭐ | 生产环境主数据源 |
| **Akshare** | 95% | ⭐⭐⭐⭐ | 备用数据源，QDII支持好 |
| **Sina** | 90% | ⭐⭐⭐ | 实时数据获取 |
| **Eastmoney** | 92% | ⭐⭐⭐⭐ | 备用数据源 |

---

## 更新日志

### v2.0 (2026-02-09)
- **重大变更**: 调整数据源优先级
  - Tushare: 备用 → **主数据源 (PRIMARY)**
  - Akshare: 主数据源 → **第一备用 (BACKUP_1)**
  - Sina/EM: 新增为 **第二备用 (BACKUP_2)**
- **新增**: 自动代码格式转换（处理.OF后缀）
- **优化**: QDII处理逻辑适配新优先级
- **改进**: 更详细的降级日志

### v1.0 (2026-02-08)
- 初始版本发布
- 支持 akshare + tushare 双数据源
- QDII基金特殊处理
- 健康状态监控

---

## 相关文档

- [数据源优先级配置说明](./DATA_SOURCE_PRIORITY_CONFIG.md)
- [数据源对比分析](./DATA_SOURCE_COMPARISON.md)
- [Tushare 集成指南](./TUSHARE_INTEGRATION_GUIDE.md)
- [QDII 基金特殊处理说明](./QDII基金特殊处理说明.md)
