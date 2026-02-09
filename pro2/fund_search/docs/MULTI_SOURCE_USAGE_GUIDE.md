# 多数据源基金数据获取模块使用指南

## 快速开始

### 1. 基本使用

```python
from fund_search.data_retrieval.multi_source_fund_data import MultiSourceFundData

# 初始化（推荐添加Tushare token作为备用）
fetcher = MultiSourceFundData(tushare_token="your_token")

# 获取基金历史净值
df = fetcher.get_fund_nav_history("021539")
print(df.head())

# 获取最新净值
latest = fetcher.get_fund_latest_nav("021539")
print(f"最新净值: {latest['nav']}")
```

### 2. QDII基金处理

```python
# 判断是否为QDII
is_qdii = fetcher.is_qdii_fund("021539", "华安法国CAC40ETF发起式联接(QDII)A")

# 获取QDII基金数据（自动特殊处理）
qdii_data = fetcher.get_qdii_fund_data("021539")
print(f"净值: {qdii_data['current_nav']}")
print(f"更新延迟: {qdii_data['update_delay']}")  # T+2
```

### 3. 数据源选择

```python
# 强制使用akshare
df = fetcher.get_fund_nav_history("021539", source="akshare")

# 强制使用tushare
df = fetcher.get_fund_nav_history("021539", source="tushare")

# 自动选择(根据健康状态)
df = fetcher.get_fund_nav_history("021539", source="auto")
```

## 高级功能

### 健康监控

```python
# 获取数据源健康状态
health = fetcher.get_health_status()
print(health)

# 输出:
# {
#     'akshare': {
#         'success_rate': '95.2%',
#         'avg_response_time': '1.234s',
#         'total_requests': 100,
#         'last_error': None
#     },
#     'tushare': {...},
#     'recommend_source': 'akshare'
# }
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

fetcher = MultiSourceFundData()
nav = fetcher.get_fund_nav_history("021539")
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
            # 从配置读取token
            token = get_config().get('TUSHARE_TOKEN')
            cls._multi_source_fetcher = MultiSourceFundData(tushare_token=token)
        return cls._multi_source_fetcher
    
    @staticmethod
    def get_fund_realtime_data(fund_code: str) -> Dict:
        fetcher = EnhancedFundData.get_fetcher()
        
        # 自动判断QDII
        if fetcher.is_qdii_fund(fund_code):
            return fetcher.get_qdii_fund_data(fund_code)
        
        return fetcher.get_fund_latest_nav(fund_code)
```

## 配置建议

### 1. 环境变量配置

```bash
# .env 文件
TUSHARE_TOKEN=5ff19facae0e5b26a407d491d33707a9884a39a714a0d76b6495725b
DATA_TIMEOUT=10
```

### 2. 日志配置

```python
import logging

# 启用调试日志
logging.getLogger('fund_search.data_retrieval.multi_source_fund_data').setLevel(logging.DEBUG)
```

## 常见问题

### Q1: Tushare token无效怎么办？
```python
# 不传入token，只使用akshare
fetcher = MultiSourceFundData()
```

### Q2: 如何强制使用特定数据源？
```python
# 强制使用akshare
df = fetcher._get_nav_from_akshare("021539")

# 强制使用tushare
df = fetcher._get_nav_from_tushare("021539")
```

### Q3: 如何处理网络超时？
```python
# 增加超时时间
fetcher = MultiSourceFundData(timeout=30)

# 或使用重试装饰器
from fund_search.data_retrieval.multi_source_fund_data import retry_on_failure

@retry_on_failure(max_retries=5, delay=2)
def get_data():
    return fetcher.get_fund_nav_history("021539")
```

## 性能对比

| 操作 | Akshare | Tushare | 推荐 |
|------|---------|---------|------|
| 获取历史净值 | 1-3s | 0.5-2s | Tushare |
| 获取最新净值 | 1-2s | 0.5-1s | Tushare |
| 获取基本信息 | 2-4s | 1-2s | Tushare |
| QDII基金 | 支持 | 支持 | Akshare |

## 更新日志

### v1.0 (2026-02-09)
- 初始版本发布
- 支持 akshare + tushare 双数据源
- QDII基金特殊处理
- 健康状态监控
