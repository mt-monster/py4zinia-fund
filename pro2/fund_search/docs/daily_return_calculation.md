# 基金日涨跌幅计算说明

## 概述

本文档详细说明系统中日涨跌幅（daily return）的计算方式。

## 核心概念

系统中有两个关键的涨跌幅指标：

| 字段 | 含义 | 数据来源 |
|------|------|----------|
| `today_return` | **今日涨跌幅** | 实时计算 |
| `prev_day_return` | **昨日涨跌幅** | 从数据库历史记录获取 |

## 计算公式

```
今日涨跌幅(today_return) = (当前净值 - 昨日净值) / 昨日净值 × 100%
```

**示例：**
- 昨日净值：1.2345
- 当前净值：1.3560
- 今日涨跌幅 = (1.3560 - 1.2345) / 1.2345 × 100% = +9.84%

---

## 详细流程

### 1. 今日涨跌幅 (today_return) 计算

#### 1.1 数据源获取

系统按优先级尝试以下数据源：

1. **天天基金API** (fund_zhuli_em) - 最常用
2. **Tushare Pro API** (ts_pro.fund_nav)
3. **AKShare** (fund_open_fund_info_em)
4. **新浪财经** (从适配器获取)

#### 1.2 计算逻辑

文件：`services/holding_realtime_service.py`

```python
# 方式1：从天天基金API获取（推荐）
def _from_fund_zhuli_em(self, fund_code: str):
    df = ak.fund_zhuli_em(symbol=fund_code)
    # 获取最新两条数据
    latest = df.iloc[0]
    prev = df.iloc[1]
    
    # 计算今日涨跌幅
    current_nav = float(latest.get('单位净值', 0))
    prev_nav = float(prev.get('单位净值', 0))
    
    today_return = 0.0
    if current_nav and prev_nav and prev_nav > 0:
        today_return = round((current_nav - prev_nav) / prev_nav * 100, 2)
    
    return {
        'current_nav': current_nav,
        'estimate_nav': current_nav,
        'today_return': today_return,
        'source': 'fund_zhuli_em'
    }

# 方式2：从AKShare获取
def _from_akshare(self, fund_code: str):
    df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
    if df is not None and not df.empty and len(df) >= 2:
        latest = df.iloc[0]
        prev = df.iloc[1]
        
        current_nav = float(latest.get('单位净值', 0))
        prev_nav = float(prev.get('单位净值', 0))
        
        today_return = 0.0
        if current_nav and prev_nav and prev_nav > 0:
            today_return = round((current_nav - prev_nav) / prev_nav * 100, 2)
        
        return {
            'current_nav': current_nav,
            'estimate_nav': current_nav,
            'today_return': today_return,
            'source': 'akshare'
        }
```

#### 1.3 QDII基金特殊处理

QDII基金（如投资港股、美股的基金）存在时差问题：
- 港股收盘时间：16:00（北京时间）
- 美股收盘时间：04:00（北京时间，次日）

系统会标记QDII基金的数据延迟情况：

```python
# 判断是否为QDII基金
if fund_code.startswith('15') or fund_code.startswith('16'):
    is_qdii = True  # 港股通基金
```

---

### 2. 昨日涨跌幅 (prev_day_return) 获取

#### 2.1 数据来源

昨日涨跌幅从数据库 `fund_analysis_results` 表中获取：

```python
# 从数据库获取昨日收益率
sql = """
    SELECT 
        fund_code,
        prev_day_return
    FROM fund_analysis_results
    WHERE (fund_code, analysis_date) IN (
        SELECT fund_code, MAX(analysis_date) as max_date
        FROM fund_analysis_results
        WHERE fund_code IN (:fund_codes)
        GROUP BY fund_code
    )
"""

# 执行查询
df = self.db.execute_query(sql, params)

for _, row in df.iterrows():
    code = row['fund_code']
    prev_return = float(row['prev_day_return'])
    results[code] = {
        'yesterday_return': prev_return,
        'yesterday_return_date': datetime.now().strftime('%Y-%m-%d'),
        'yesterday_return_days_diff': 1
    }
```

#### 2.2 备用获取方式

如果数据库中没有记录，从历史净值计算：

```python
# 从 MultiSourceDataAdapter 批量获取
batch_nav_data = adapter.batch_get_fund_nav(fund_codes)

for code, df in batch_nav_data.items():
    if not df.empty and len(df) >= 2:
        # 计算昨日收益率
        latest_nav = float(df.iloc[-1]['nav'])      # 最新净值
        yesterday_nav = float(df.iloc[-2]['nav'])   # 昨日净值
        
        if yesterday_nav > 0:
            yesterday_return = (latest_nav - yesterday_nav) / yesterday_nav * 100
            yesterday_return = round(yesterday_return, 2)
```

---

## 数据流向图

```
┌─────────────────────────────────────────────────────────────────┐
│                        今日涨跌幅 (today_return)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   用户请求 ──▶ HoldingRealtimeService.get_fund_realtime()      │
│                          │                                       │
│                          ▼                                       │
│              ┌─────────────────────────┐                         │
│              │   数据源获取优先级        │                         │
│              │  1. 天天基金API          │                         │
│              │  2. Tushare Pro         │                         │
│              │  3. AKShare            │                         │
│              │  4. 新浪财经            │                         │
│              └─────────────────────────┘                         │
│                          │                                       │
│                          ▼                                       │
│         ┌────────────────────────────────────┐                   │
│         │  获取最近两天净值数据                │                   │
│         │  - latest: 今日净值                 │                   │
│         │  - prev: 昨日净值                   │                   │
│         └────────────────────────────────────┘                   │
│                          │                                       │
│                          ▼                                       │
│              计算: today_return =                               │
│              (current_nav - prev_nav) / prev_nav × 100%         │
│                          │                                       │
│                          ▼                                       │
│              返回: { today_return: +9.84% }                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      昨日涨跌幅 (prev_day_return)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   用户请求 ──▶ HoldingRealtimeService.get_fund_realtime()      │
│                          │                                       │
│                          ▼                                       │
│              ┌─────────────────────────┐                         │
│              │  查询内存缓存            │                         │
│              │  (Cache: yesterday:*)   │                         │
│              └─────────────────────────┘                         │
│                     │ 不命中                                     │
│                     ▼                                           │
│              ┌─────────────────────────┐                         │
│              │  查询数据库              │                         │
│              │  fund_analysis_results  │                         │
│              │  (按fund_code分组取最新) │                        │
│              └─────────────────────────┘                         │
│                     │ 不命中                                     │
│                     ▼                                           │
│              ┌─────────────────────────┐                         │
│              │  MultiSourceAdapter     │                         │
│              │  计算历史净值收益率       │                         │
│              └─────────────────────────┘                         │
│                          │                                       │
│                          ▼                                       │
│              返回: { prev_day_return: -1.23% }                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 数据库表结构

### fund_analysis_results 表关键字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| fund_code | VARCHAR | 基金代码 |
| fund_name | VARCHAR | 基金名称 |
| yesterday_nav | DECIMAL | 昨日单位净值 |
| current_estimate | DECIMAL | 当前估算净值 |
| today_return | DECIMAL | 今日涨跌幅(%) |
| prev_day_return | DECIMAL | 昨日涨跌幅(%) |
| analysis_date | DATE | 分析日期 |

---

## 缓存策略

| 数据类型 | 缓存时间 | 说明 |
|----------|----------|------|
| 今日涨跌幅 | **不缓存** | 实时获取 |
| 昨日涨跌幅 | 15分钟 | 内存缓存 |
| 基金基本信息 | 1天 | Redis缓存 |

---

## 常见问题

### Q1: 今日涨跌幅显示为0%
可能原因：
1. 基金未更新（节假日后首个交易日可能无数据）
2. 数据源获取失败
3. 净值数据异常

### Q2: 昨日涨跌幅显示为0%
可能原因：
1. 数据库中无历史记录
2. 历史净值计算结果为0

### Q3: QDII基金涨跌幅为何不同步？
QDII基金投资海外市场，存在时差：
- 港股通基金：T+1显示
- 美股基金：T+2显示
系统会根据基金类型自动标记延迟。

---

## 相关文件

- `services/holding_realtime_service.py` - 实时数据服务
- `services/fund_nav_cache_manager.py` - 净值缓存管理
- `data_retrieval/adapters/multi_source_adapter.py` - 多源数据适配器
- `web/routes/holdings.py` - 持仓路由处理
