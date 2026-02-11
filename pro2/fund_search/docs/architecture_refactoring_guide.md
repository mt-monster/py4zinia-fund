# pro2/fund_search 架构重构实施指南

## 快速开始

本文档提供具体的重构实施步骤，可在不影响现有功能的前提下逐步改进架构。

---

## 第一阶段：代码清理（立即执行）

### 1.1 统一列名映射

**创建文件**: `data_retrieval/constants.py`

```python
"""数据检索层常量定义"""

# 基金净值数据列名映射（统一使用）
FUND_NAV_COLUMN_MAPPING = {
    '净值日期': 'date',
    '单位净值': 'nav',
    '累计净值': 'accum_nav',
    '日增长率': 'daily_return'
}

# ETF 数据列名映射
ETF_COLUMN_MAPPING = {
    '代码': 'etf_code',
    '名称': 'etf_name',
    '最新价': 'current_price',
    '涨跌额': 'change',
    '涨跌幅': 'change_percent',
    '成交量': 'volume',
    '成交额': 'turnover',
    '市盈率': 'pe',
    '市净率': 'pb'
}
```

### 1.2 修复日志配置

**创建文件**: `shared/logging_config.py`

```python
"""统一日志配置"""
import logging
import sys

_configured = False

def configure_logging(level=logging.INFO, log_file='fund_analysis.log'):
    """配置日志（只允许执行一次）"""
    global _configured
    if _configured:
        return
    
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    _configured = True
```

---

## 第二阶段：提取数据源适配器（1周）

### 2.1 创建适配器基类

**创建目录**: `data_retrieval/adapters/`

**文件**: `base.py`
```python
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict

class BaseDataSourceAdapter(ABC):
    def __init__(self, name: str, timeout: int = 10):
        self.name = name
        self.timeout = timeout
    
    @abstractmethod
    def get_fund_nav_history(self, fund_code: str, days: int = 365) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def get_fund_basic_info(self, fund_code: str) -> Dict:
        pass
```

### 2.2 创建具体适配器

**文件**: `akshare_adapter.py`, `sina_adapter.py`, `tushare_adapter.py`

---

## 第三阶段：创建门面类（1周）

**创建文件**: `services/fund_data_facade.py`

```python
class FundDataFacade:
    """统一数据获取门面"""
    
    def __init__(self):
        self.adapters = {
            'akshare': AkshareAdapter(),
            'sina': SinaAdapter()
        }
    
    def get_fund_nav_history(self, fund_code: str, days: int = 365):
        # 自动降级逻辑
        pass
```

---

## 第四阶段：重构路由层（2周）

### 4.1 创建统一响应装饰器

**文件**: `web/decorators.py`
```python
def api_response(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        try:
            result = handler(*args, **kwargs)
            return jsonify({'success': True, 'data': result})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return wrapper
```

### 4.2 逐步替换路由实现

使用门面类替换直接的数据获取调用。

---

## 第五阶段：拆分 God Class（3周）

### 5.1 创建 Repository 层

**目录**: `data_access/repositories/`

**文件**: `fund_repository.py`, `holdings_repository.py`

### 5.2 迁移数据库操作

将 `EnhancedDatabaseManager` 的方法逐步迁移到 Repository。

---

## 关键改进清单

### 立即执行
- [ ] 统一列名映射常量
- [ ] 修复日志重复配置

### 第一阶段（1周）
- [ ] 创建数据源适配器
- [ ] 提取重复的数据获取逻辑

### 第二阶段（1-2周）
- [ ] 创建 FundDataFacade
- [ ] 删除废弃的 FundRealTime

### 第三阶段（2-3周）
- [ ] 重构路由层
- [ ] 创建 Service 层

### 第四阶段（3-4周）
- [ ] 拆分 EnhancedDatabaseManager
- [ ] 创建 Repository 层

### 第五阶段（持续）
- [ ] 添加缓存层
- [ ] 性能优化

---

*指南版本: 1.0*
