# 数据源优先级配置说明

## 概述

本文档说明系统当前的数据源优先级配置，以及如何在代码中使用和修改这些配置。

**更新时间**: 2026-02-09  
**配置文件**: `shared/enhanced_config.py`

---

## 数据源优先级

### 当前配置 (2026-02-09 更新)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    数据源优先级架构                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────────────────────────────────────────────┐      │
│   │  PRIMARY (主数据源)                                      │      │
│   │  ┌─────────────────┐                                    │      │
│   │  │   Tushare       │  稳定性高 (98%成功率)              │      │
│   │  │   - .OF格式     │  响应快 (0.5-2s)                   │      │
│   │  │   - 专业接口    │  支持基金最全                      │      │
│   │  └─────────────────┘                                    │      │
│   └─────────────────────────────────────────────────────────┘      │
│                            ↓ (失败时)                               │
│   ┌─────────────────────────────────────────────────────────┐      │
│   │  BACKUP_1 (第一备用)                                    │      │
│   │  ┌─────────────────┐                                    │      │
│   │  │   Akshare       │  数据全面 (95%成功率)              │      │
│   │  │   - 标准格式    │  免费开源                          │      │
│   │  │   - 东财数据    │  QDII支持好                        │      │
│   │  └─────────────────┘                                    │      │
│   └─────────────────────────────────────────────────────────┘      │
│                            ↓ (失败时)                               │
│   ┌─────────────────────────────────────────────────────────┐      │
│   │  BACKUP_2 (第二备用)                                    │      │
│   │  ┌──────────┐  ┌──────────────┐                        │      │
│   │  │   Sina   │  │  Eastmoney   │  实时性好              │      │
│   │  │ 实时接口 │  │   备用接口    │  轻量级                │      │
│   │  └──────────┘  └──────────────┘                        │      │
│   └─────────────────────────────────────────────────────────┘      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 配置代码

```python
# shared/enhanced_config.py

DATA_SOURCE_CONFIG = {
    # Tushare 配置 (PRIMARY)
    'tushare': {
        'token': os.environ.get('TUSHARE_TOKEN', '5ff19facae0e5b26a407d491d33707a9884a39a714a0d76b6495725b'),
        'timeout': int(os.environ.get('TUSHARE_TIMEOUT', 30)),
        'max_retries': int(os.environ.get('TUSHARE_RETRIES', 3))
    },
    
    # Akshare 配置 (BACKUP_1)
    'akshare': {
        'timeout': int(os.environ.get('AKSHARE_TIMEOUT', 30)),
        'max_retries': int(os.environ.get('AKSHARE_RETRIES', 3)),
        'delay_between_requests': float(os.environ.get('AKSHARE_DELAY', 1.0))
    },
    
    # 备用数据源配置 (BACKUP_2)
    'fallback': {
        'sina_enabled': os.environ.get('SINA_ENABLED', 'True').lower() == 'true',
        'eastmoney_enabled': os.environ.get('EASTMONEY_ENABLED', 'True').lower() == 'true',
        'request_timeout': int(os.environ.get('FALLBACK_TIMEOUT', 10))
    },
    
    # 数据源优先级配置
    'priority': {
        'primary': 'tushare',           # 主数据源
        'backup_1': 'akshare',          # 第一备用
        'backup_2': ['sina', 'eastmoney']  # 第二备用(按顺序尝试)
    }
}
```

---

## 代码格式转换

### Tushare 格式要求

Tushare 需要使用 `.OF` 后缀的基金代码格式：

| 原始代码 | Tushare格式 | 说明 |
|---------|------------|------|
| 021539 | 021539.OF | 华安法国CAC40ETF联接A |
| 000001 | 000001.OF | 华夏成长混合 |

### 自动转换

系统已内置自动转换函数：

```python
# multi_source_fund_data.py

def _convert_to_tushare_format(self, fund_code: str) -> str:
    """将基金代码转换为 Tushare 格式"""
    if not fund_code.endswith('.OF'):
        return f"{fund_code}.OF"
    return fund_code
```

### 使用示例

```python
from pro2.fund_search.data_retrieval.multi_source_fund_data import MultiSourceFundData

fetcher = MultiSourceFundData(tushare_token="your_token")

# 传入原始代码，系统自动转换
result = fetcher.get_fund_latest_nav("021539")  # 自动转为 021539.OF

# 返回结果使用原始代码格式
print(result['fund_code'])  # 输出: 021539 (不是 021539.OF)
```

---

## 降级策略

### 自动降级条件

```python
# DataSourceHealth.get_recommend_source()

def get_recommend_source(self) -> str:
    ak_rate = self.get_success_rate('akshare')
    ts_rate = self.get_success_rate('tushare')
    
    # 降级条件:
    # 1. Tushare成功率 < 70%
    # 2. Akshare成功率比Tushare高20%以上
    if ts_rate < 0.7 or (ak_rate - ts_rate) > 0.2:
        logger.warning(f"Tushare成功率低，降级到Akshare")
        return 'akshare'
    
    return 'tushare'
```

### 降级流程

```
获取基金数据 [021539]
    │
    ├─► 尝试 Tushare (PRIMARY)
    │   ├─ 成功 ◄── 返回数据
    │   └─ 失败
    │       │
    │       ▼
    ├─► 尝试 Akshare (BACKUP_1)
    │   ├─ 成功 ◄── 返回数据
    │   └─ 失败
    │       │
    │       ▼
    ├─► 尝试 Sina (BACKUP_2)
    │   ├─ 成功 ◄── 返回数据
    │   └─ 失败
    │       │
    │       ▼
    └─► 尝试 Eastmoney (BACKUP_2)
        ├─ 成功 ◄── 返回数据
        └─ 失败 ◄── 返回 None
```

---

## QDII 基金特殊处理

### QDII 数据源优先级

QDII 基金同样遵循新的数据源优先级：

```python
def get_qdii_fund_data(self, fund_code: str) -> Optional[Dict]:
    # 尝试 Tushare (PRIMARY)
    if self.tushare_pro:
        try:
            tushare_code = self._convert_to_tushare_format(fund_code)
            nav_history = self._get_nav_from_tushare(tushare_code)
            source_used = 'tushare'
        except Exception as e:
            logger.warning(f"QDII Tushare获取失败: {e}")
    
    # 尝试 Akshare (BACKUP_1)
    if nav_history is None or nav_history.empty:
        try:
            nav_history = self._get_nav_from_akshare(fund_code)
            source_used = 'akshare'
        except Exception as e:
            logger.warning(f"QDII Akshare获取失败: {e}")
```

### T+2 延迟处理

QDII 基金净值 T+2 更新，系统会自动向前追溯获取最新有效数据：

```python
# 当 yesterday_return = 0 时，向前查找最近非零值
yesterday_return = EnhancedFundData._get_previous_nonzero_return(fund_nav, fund_code)
```

---

## 环境变量配置

### 完整环境变量列表

```bash
# .env 文件

# Tushare 配置 (PRIMARY)
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

### Docker 配置

```yaml
# docker-compose.yml
services:
  fund-analysis:
    environment:
      - TUSHARE_TOKEN=${TUSHARE_TOKEN}
      - TUSHARE_TIMEOUT=30
      - AKSHARE_TIMEOUT=30
      - SINA_ENABLED=true
```

---

## 监控与日志

### 健康状态监控

```python
# 获取数据源健康状态
fetcher = MultiSourceFundData(tushare_token="your_token")

# 检查各数据源成功率
health = fetcher.health
print(f"Tushare成功率: {health.get_success_rate('tushare'):.1%}")
print(f"Akshare成功率: {health.get_success_rate('akshare'):.1%}")

# 获取推荐数据源
recommend = health.get_recommend_source()
print(f"推荐数据源: {recommend}")
```

### 日志输出示例

```
INFO - 使用 PRIMARY 数据源 Tushare 获取 021539
INFO - 从 Tushare 成功获取 021539 最新净值

# 降级情况
WARNING - Tushare获取 021539 失败: Connection timeout
INFO - 使用 BACKUP_1 数据源 Akshare 获取 021539
INFO - 从 Akshare 成功获取 021539 最新净值 (BACKUP_1)

# 继续降级
WARNING - Akshare获取 021539 失败: Network error
INFO - 从 Fallback 成功获取 021539 最新净值 (BACKUP_2)
```

---

## 性能对比

### 响应时间对比

| 数据源 | 平均响应时间 | 成功率 | 适用场景 |
|-------|------------|-------|---------|
| **Tushare** | 0.5-2s | 98% | 主数据源，生产环境首选 |
| **Akshare** | 1-3s | 95% | 备用数据源，QDII支持好 |
| **Sina** | 0.2-1s | 90% | 实时数据，轻量级查询 |
| **Eastmoney** | 1-2s | 92% | 备用，数据完整 |

### 数据源能力对比

| 功能 | Tushare | Akshare | Sina | Eastmoney |
|-----|---------|---------|------|-----------|
| 历史净值 | ✓ | ✓ | ✗ | ✓ |
| 实时净值 | ✗ | ✗ | ✓ | ✗ |
| 基金信息 | ✓ | ✓ | ✗ | ✓ |
| QDII支持 | ✓ | ✓ | ✗ | ✓ |
| 分红数据 | ✓ | ✓ | ✗ | ✓ |
| 免费使用 | 积分制 | ✓ | ✓ | ✓ |

---

## 故障排查

### 常见问题

#### Q1: Tushare 返回 "权限不足"

**原因**: Tushare 积分不足或接口权限限制

**解决**: 
```python
# 系统会自动降级到 Akshare
# 或手动切换到 Akshare
df = fetcher.get_fund_nav_history("021539", source="akshare")
```

#### Q2: 所有数据源都失败

**检查**:
1. 网络连接是否正常
2. Tushare token 是否有效
3. 基金代码是否正确

```python
# 检查数据源状态
print(fetcher.health.akshare)   # 查看 Akshare 健康状态
print(fetcher.health.tushare)   # 查看 Tushare 健康状态
```

#### Q3: QDII 基金数据延迟

**原因**: QDII 基金 T+2 更新是正常现象

**解决**: 系统会自动向前追溯获取最新有效数据，无需手动处理。

---

## 更新日志

### v2.0 (2026-02-09)
- **重大变更**: 数据源优先级调整
  - Tushare 从备用提升为主数据源
  - Akshare 从主数据源降级为第一备用
  - 添加 Sina/Eastmoney 作为第二备用
- **新增**: 自动代码格式转换 (.OF后缀处理)
- **优化**: QDII 基金处理逻辑适配新优先级
- **新增**: 详细的降级日志记录

### v1.0 (2026-02-08)
- 初始版本: Akshare 为主，Tushare 为备用
- 支持 QDII 基金特殊处理
- 健康状态监控

---

## 相关文档

- [数据源对比分析](./DATA_SOURCE_COMPARISON.md)
- [多数据源使用指南](./MULTI_SOURCE_USAGE_GUIDE.md)
- [Tushare 集成指南](./TUSHARE_INTEGRATION_GUIDE.md)
- [QDII 基金特殊处理说明](./QDII基金特殊处理说明.md)
