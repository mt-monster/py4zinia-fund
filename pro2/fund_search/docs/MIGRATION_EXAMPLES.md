# 代码迁移示例

本文档展示如何将现有代码迁移到新的架构。

## 1. 获取基金净值历史

### 迁移前
```python
# multi_source_fund_data.py (重复实现)
import akshare as ak
import pandas as pd

def get_fund_nav_history(fund_code, days=365):
    df = ak.fund_open_fund_info_em(
        symbol=fund_code, 
        indicator='单位净值走势',
        period='最大值'
    )
    # 重复的标准化处理
    column_mapping = {
        '净值日期': 'date',
        '单位净值': 'nav',
        '累计净值': 'accum_nav',
        '日增长率': 'daily_return'
    }
    df = df.rename(columns=column_mapping)
    return df.tail(days)
```

### 迁移后
```python
# 使用统一数据服务
from services import fund_data_service

def get_fund_nav_history(fund_code, days=365):
    # 一行代码，自动处理降级和重试
    return fund_data_service.get_fund_nav_history(fund_code, days)
```

---

## 2. 获取实时数据

### 迁移前
```python
# multi_source_adapter.py (重复实现)
import requests

def get_realtime_data(fund_code):
    url = f"https://hq.sinajs.cn/list=f_{fund_code}"
    headers = {'Referer': 'https://finance.sina.com.cn'}
    response = requests.get(url, headers=headers, timeout=10)
    # 解析逻辑...
    return parse_response(response.text)
```

### 迁移后
```python
from services import fund_data_service

def get_realtime_data(fund_code):
    realtime = fund_data_service.get_realtime_data(fund_code)
    return {
        'fund_name': realtime.fund_name,
        'current_nav': realtime.current_nav,
        'daily_return': realtime.daily_return
    }
```

---

## 3. Web 路由层

### 迁移前
```python
# web/routes/funds.py
@app.route('/api/fund/<fund_code>/nav')
def get_fund_nav(fund_code):
    try:
        import akshare as ak
        df = ak.fund_open_fund_info_em(...)
        # 大量数据处理逻辑
        data = df.to_dict('records')
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
```

### 迁移后
```python
from services import fund_data_service
from web.decorators import api_response

@app.route('/api/fund/<fund_code>/nav')
@api_response
def get_fund_nav(fund_code):
    days = request.args.get('days', 365, type=int)
    df = fund_data_service.get_fund_nav_history(fund_code, days)
    return df.to_dict('records') if not df.empty else []
```

---

## 4. 错误处理

### 迁移前
```python
try:
    df = get_fund_data(fund_code)
except Exception as e:
    logger.error(f"获取数据失败: {e}")
    return None
```

### 迁移后
```python
# 使用新的日志配置
from shared.logging_config import get_logger

logger = get_logger(__name__)

# 适配器内部已处理错误和重试
df = fund_data_service.get_fund_nav_history(fund_code)
if df.empty:
    logger.warning(f"基金 {fund_code} 数据为空")
```

---

## 5. 列名映射

### 迁移前
```python
# 在每个文件中重复定义
column_mapping = {
    '净值日期': 'date',
    '单位净值': 'nav',
    '累计净值': 'accum_nav',
    '日增长率': 'daily_return'
}
```

### 迁移后
```python
from data_retrieval.constants import FUND_NAV_COLUMN_MAPPING

# 使用统一常量
df = df.rename(columns=FUND_NAV_COLUMN_MAPPING)
```

---

## 完整迁移示例

假设要迁移 `enhanced_main.py` 中的数据获取逻辑：

### 迁移前
```python
# enhanced_main.py
class FundAnalysisService:
    def analyze_fund(self, fund_code):
        # 获取实时数据（直接调用akshare）
        import akshare as ak
        df = ak.fund_open_fund_info_em(symbol=fund_code, indicator='单位净值走势')
        
        # 处理数据
        df = df.rename(columns={
            '净值日期': 'date',
            '单位净值': 'nav',
            '日增长率': 'daily_return'
        })
        
        return df
```

### 迁移后
```python
# enhanced_main.py
from services import fund_data_service

class FundAnalysisService:
    def analyze_fund(self, fund_code):
        # 使用统一服务，自动处理重试和降级
        df = fund_data_service.get_fund_nav_history(fund_code, days=30)
        
        # 数据已经标准化，无需再次处理列名
        return df
```

---

## 迁移检查清单

- [ ] 替换所有 `ak.fund_open_fund_info_em` 调用
- [ ] 替换所有新浪实时数据获取代码
- [ ] 删除重复的列名映射定义
- [ ] 使用新的日志配置替换 `logging.basicConfig`
- [ ] 测试所有迁移后的功能
- [ ] 删除废弃的文件

## 常见问题

### Q: 原有代码还能继续使用吗？
**A:** 可以。新架构完全向后兼容，可以逐步迁移。

### Q: 如何处理适配器不支持的API？
**A:** 可以直接使用适配器实例访问底层akshare：
```python
from data_retrieval.adapters import AkshareAdapter

adapter = AkshareAdapter()
ak = adapter._get_akshare()
# 使用akshare的特殊API
```

### Q: 如何添加新的数据源？
**A:** 继承 `BaseDataSourceAdapter` 基类：
```python
from data_retrieval.adapters import BaseDataSourceAdapter

class NewAdapter(BaseDataSourceAdapter):
    def get_fund_nav_history(self, fund_code, days=365):
        # 实现数据获取逻辑
        pass
```

---

*文档版本: 1.0*
