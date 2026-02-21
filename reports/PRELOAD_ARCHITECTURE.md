# 基金数据预加载架构设计

## 架构目标

**核心目标**: 系统启动前预加载所有数据，用户打开系统后几秒内看到所有内容。

```
传统方式:
用户访问 → 查询数据库/API → 计算 → 返回 (几秒~几十秒)

预加载方式:
系统启动 → 预加载所有数据到内存 → 用户访问 → 直接返回 (< 10ms)
```

## 架构设计

### 1. 数据分层策略

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: 实时数据（需要实时计算）                          │
│  - 今日收益率（today_return）                               │
│  - 实时估值                                                 │
│  响应时间: 实时计算，< 100ms                                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: 动态数据（每天更新）                              │
│  - 最新净值（latest_nav）                                   │
│  - 日涨跌幅（daily_return）                                 │
│  缓存TTL: 30分钟                                            │
│  响应时间: 内存读取，< 1ms                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: 准静态数据（定期更新）                            │
│  - 历史净值（nav_history）                                  │
│  - 绩效指标（performance）                                  │
│  缓存TTL: 1天                                               │
│  响应时间: 内存读取，< 1ms                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: 静态数据（极少更新）                              │
│  - 基金基本信息（basic_info）                               │
│  - QDII标识（qdii_flag）                                    │
│  缓存TTL: 7天                                               │
│  响应时间: 内存读取，< 1ms                                  │
└─────────────────────────────────────────────────────────────┘
```

### 2. 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户层                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Web界面   │  │   API接口   │  │   移动App   │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
└─────────┼────────────────┼────────────────┼────────────────────┘
          │                │                │
          └────────────────┴────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     极速查询服务层                               │
│              FastFundService (< 10ms响应)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  - get_fund_complete_data()                             │   │
│  │  - batch_get_fund_data()                                │   │
│  │  - get_fund_nav_history()                               │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   内存缓存   │  │   实时计算   │  │  降级到API   │
│  (L1 Cache)  │  │  (Layer 1)   │  │  (Fallback)  │
└──────────────┘  └──────────────┘  └──────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     数据预加载服务层                             │
│              FundDataPreloader (系统启动时运行)                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. 加载所有基金基本信息                                 │   │
│  │  2. 加载所有QDII标识                                     │   │
│  │  3. 批量加载最新净值                                     │   │
│  │  4. 分批加载历史净值                                     │   │
│  │  5. 预计算绩效指标                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
           ▼                               ▼
┌──────────────────────┐      ┌──────────────────────┐
│     数据源层         │      │    后台更新服务      │
│  ┌────────────────┐  │      │  BackgroundUpdater   │
│  │   Tushare API  │  │      │                      │
│  │   Akshare API  │  │      │  - 每30分钟更新净值  │
│  │   新浪API      │  │      │  - 每天更新历史数据  │
│  └────────────────┘  │      │  - 自动重算绩效指标  │
└──────────────────────┘      └──────────────────────┘
```

### 3. 启动流程

```
系统启动流程:

1. 初始化基础组件
   ├── 初始化配置管理器
   ├── 初始化数据库连接
   └── 初始化日志系统
   
2. 数据预加载阶段 (FundDataPreloader)
   ├── 获取所有基金代码列表
   │   └── 从Akshare获取（约1000+只基金）
   │
   ├── 批量加载基本信息 (10%)
   │   └── 缓存到内存，TTL=7天
   │
   ├── 加载QDII标识 (20%)
   │   └── 缓存到内存，TTL=7天
   │
   ├── 批量加载最新净值 (30%)
   │   └── 使用Tushare批量接口
   │   └── 缓存到内存，TTL=30分钟
   │
   ├── 分批加载历史净值 (50-80%)
   │   └── 每批50只基金
   │   └── 最近2年历史数据
   │   └── 缓存到内存，TTL=1天
   │
   └── 预计算绩效指标 (90-100%)
       └── 基于历史净值计算
       └── 缓存到内存，TTL=1天

3. 启动后台更新服务 (BackgroundUpdater)
   ├── 注册更新任务
   │   ├── 最新净值更新（每30分钟）
   │   ├── 历史净值更新（每天收盘后）
   │   ├── 绩效指标重算（净值更新后）
   │   └── 缓存健康检查（每5分钟）
   │
   └── 启动后台线程

4. 启动Web服务
   ├── 注册路由
   ├── 初始化极速查询服务
   └── 开始接受用户请求

总耗时: 约 1-5 分钟（取决于基金数量）
```

### 4. 查询响应流程

```
用户查询基金数据:

1. 极速查询服务接收请求
   └── FastFundService.get_fund_complete_data(code)

2. 并行从内存缓存获取数据
   ├── 基本信息 (get_fund_basic_info) ───────┐
   ├── 最新净值 (get_fund_latest_nav) ───────┤
   ├── 绩效指标 (get_fund_performance) ──────┤─── 全部 < 1ms
   └── QDII标识 (is_qdii_fund) ──────────────┘

3. 实时计算今日收益率
   └── 基于昨日净值和实时估值计算
   └── 耗时: < 50ms

4. 组装返回数据
   └── FundCompleteData 对象

总响应时间: < 10ms（99%的查询）
```

## 核心组件

### 1. FundDataPreloader（数据预加载服务）

**职责**: 系统启动时预加载所有数据到内存缓存

**关键方法**:
- `preload_all()` - 预加载所有数据
- `get_fund_basic_info()` - 从缓存获取基本信息
- `get_fund_nav_history()` - 从缓存获取历史净值
- `get_fund_latest_nav()` - 从缓存获取最新净值
- `get_fund_performance()` - 从缓存获取绩效指标

**配置参数**:
```python
PreloadConfig(
    fund_codes=None,          # 预加载的基金代码，None表示全部
    history_days=730,         # 历史数据天数（2年）
    max_workers=3,            # 并行线程数
    enable_full_preload=True, # 是否启用全量预加载
    max_cache_size=10000,     # 最大缓存条目数
    preload_timeout=300       # 预加载超时时间（秒）
)
```

### 2. MemoryCacheManager（内存缓存管理器）

**职责**: 高性能内存缓存，支持TTL和LRU淘汰

**特性**:
- O(1) 读写性能
- 支持TTL过期
- LRU自动淘汰
- 线程安全

**使用示例**:
```python
cache = MemoryCacheManager(max_size=10000)

# 设置缓存（TTL=1小时）
cache.set('key', value, ttl_seconds=3600)

# 获取缓存
value = cache.get('key')

# 批量操作
cache.mset({'k1': v1, 'k2': v2}, ttl_seconds=3600)
values = cache.mget(['k1', 'k2'])
```

### 3. BackgroundUpdater（后台更新服务）

**职责**: 系统运行期间自动更新数据

**默认任务**:
1. **latest_nav_update** - 每30分钟更新最新净值
2. **nav_history_update** - 每天收盘后更新历史净值
3. **performance_recalc** - 净值更新后重算绩效指标
4. **cache_health_check** - 每5分钟检查缓存健康

**使用示例**:
```python
updater = BackgroundUpdater()

# 启动服务
updater.start()

# 查看状态
status = updater.get_status()

# 停止服务
updater.stop()
```

### 4. FastFundService（极速查询服务）

**职责**: 基于内存缓存提供极速数据查询

**特性**:
- 所有查询 < 10ms
- 自动检测预加载状态
- 实时计算今日收益率
- 批量查询优化

**使用示例**:
```python
service = FastFundService()

# 等待预加载完成
service.wait_for_ready(timeout=60)

# 单只查询（< 10ms）
data = service.get_fund_complete_data('000001')

# 批量查询（100只 < 100ms）
batch = service.batch_get_fund_data(['000001', '000002'])

# 获取历史净值
df = service.get_fund_nav_history('000001')
```

## 性能指标

### 预加载性能

| 数据类型 | 数量 | 预加载时间 | 内存占用 |
|---------|------|-----------|---------|
| 基本信息 | 1000只基金 | ~10秒 | ~50MB |
| 最新净值 | 1000只基金 | ~5秒 | ~20MB |
| 历史净值 | 1000只基金x2年 | ~60秒 | ~200MB |
| 绩效指标 | 1000只基金 | ~10秒 | ~10MB |
| **总计** | **1000只基金** | **~85秒** | **~280MB** |

### 查询性能

| 查询类型 | 响应时间 | 说明 |
|---------|---------|------|
| 单只基金完整数据 | < 10ms | 99%的查询 |
| 批量查询（10只） | < 20ms | 并行读取 |
| 批量查询（100只） | < 100ms | 并行读取 |
| 历史净值（2年） | < 5ms | 内存缓存 |
| 实时计算（今日收益） | < 50ms | 需要实时数据 |

### 对比传统方式

| 指标 | 传统方式 | 预加载方式 | 提升 |
|-----|---------|-----------|------|
| 首次查询响应 | 1-5秒 | < 10ms | **500x** |
| 批量查询100只 | 10-30秒 | < 100ms | **300x** |
| API调用次数 | 每次查询 | 启动时一次 | **1000x** |
| 用户体验 | 等待加载 | 秒开 | **秒开** |

## 使用指南

### 1. 完整启动（推荐）

```bash
# 进入项目目录
cd pro2/fund_search

# 完整启动（预加载 + Web服务）
python startup.py

# 或指定参数
python startup.py --host 0.0.0.0 --port 8080 --debug
```

### 2. 仅预加载数据

```bash
# 仅预加载，不启动Web服务
python startup.py --preload-only

# 指定基金预加载
python startup.py --preload-only --fund-codes 000001,000002,021539
```

### 3. 在代码中使用

```python
# 获取极速查询服务
from services.fast_fund_service import get_fast_fund_service

service = get_fast_fund_service()

# 等待预加载完成（可选）
if not service.is_ready():
    service.wait_for_ready(timeout=60)

# 查询基金数据（< 10ms）
data = service.get_fund_complete_data('000001')
print(f"基金: {data.fund_name}")
print(f"最新净值: {data.latest_nav}")
print(f"日涨跌幅: {data.daily_return}%")
print(f"夏普比率: {data.sharpe_ratio}")

# 批量查询（< 100ms）
batch_data = service.batch_get_fund_data(['000001', '000002', '000003'])
```

### 4. 在Flask路由中使用

```python
from flask import Flask, jsonify
from services.fast_fund_service import get_fast_fund_service

app = Flask(__name__)
service = get_fast_fund_service()

@app.route('/api/fund/<code>')
def get_fund(code):
    """获取基金数据 - 极速版"""
    data = service.get_fund_complete_data(code)
    if data:
        return jsonify({
            'code': data.fund_code,
            'name': data.fund_name,
            'nav': data.latest_nav,
            'daily_return': data.daily_return,
            'sharpe_ratio': data.sharpe_ratio
        })
    return jsonify({'error': 'Not found'}), 404
```

## 运维监控

### 1. 查看预加载状态

```python
from services.fund_data_preloader import get_preloader

preloader = get_preloader()
status = preloader.get_preload_status()

print(f"已启动: {status['started']}")
print(f"已完成: {status['completed']}")
print(f"进度: {status['progress'] * 100}%")
print(f"最后预加载: {status['last_preload']}")
```

### 2. 查看缓存统计

```python
from services.fund_data_preloader import get_preloader

preloader = get_preloader()
stats = preloader.get_cache_stats()

print(f"缓存大小: {stats['size']} / {stats['max_size']}")
print(f"命中率: {stats['hit_rate']}")
print(f"访问次数: {stats['access_count']}")
```

### 3. 查看后台更新状态

```python
from services.background_updater import get_background_updater

updater = get_background_updater()
status = updater.get_status()

for task in status['tasks']:
    print(f"任务: {task['name']}")
    print(f"  运行次数: {task['run_count']}")
    print(f"  错误次数: {task['error_count']}")
    print(f"  下次运行: {task['next_run']}")
```

## 故障处理

### 场景1: 预加载失败

```python
# 检查预加载状态
status = preloader.get_preload_status()
if status['error']:
    logger.error(f"预加载失败: {status['error']}")
    # 可以降级到实时查询模式
```

### 场景2: 缓存命中率低

```python
stats = preloader.get_cache_stats()
hit_rate = float(stats['hit_rate'].replace('%', ''))

if hit_rate < 50:
    logger.warning("缓存命中率低，可能需要重新预加载")
    # 重新预加载
    preloader.preload_all()
```

### 场景3: 内存不足

```python
stats = preloader.get_cache_stats()
if stats['size'] >= stats['max_size'] * 0.9:
    logger.warning("缓存接近上限，执行清理")
    # LRU清理
    preloader.cache._cleanup_lru(500)
```

## 总结

这个预加载架构的核心优势：

1. **极速响应**: 99%的查询 < 10ms
2. **零等待**: 用户打开系统立即看到数据
3. **低API消耗**: 启动时一次性加载，运行期无API调用
4. **自动维护**: 后台服务自动更新数据
5. **内存优化**: LRU淘汰策略，内存占用可控

**适用场景**:
- 基金数据展示页面
- 投资组合分析
- 实时行情监控
- 批量数据分析

**不适用场景**:
- 低频查询（预加载成本不划算）
- 内存受限环境
- 数据实时性要求极高（秒级更新）
