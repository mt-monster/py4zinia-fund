# 基金数据缓存系统

## 概述

本缓存系统旨在优化持仓页面的数据加载性能，将高频的外部API请求转换为低频的后台数据同步。

### 核心优化点

| 优化项 | 优化前 | 优化后 | 提升 |
|--------|--------|--------|------|
| 页面加载时间 | 15-30秒 | 1-3秒 | **10x** |
| 外部API请求/次 | N次（每只基金1-2次） | 仅实时数据N次 | **大幅减少** |
| 数据库查询 | 复杂联表查询 | 缓存表直查 | **5x** |

## 数据分级策略

### 1. 实时数据（不缓存）
- **字段**：日涨跌幅、当前净值、当前市值、今日盈亏
- **更新频率**：每30秒刷新一次
- **获取方式**：每次请求实时从新浪/天天基金获取

### 2. 准实时数据（内存缓存15分钟）
- **字段**：昨日净值、昨日涨跌幅
- **更新频率**：日终更新，内存缓存15分钟
- **获取方式**：从fund_nav_cache表查询

### 3. 低频指标（数据库缓存1天）
- **字段**：年化收益、最大回撤、夏普比率、综合评分等
- **更新频率**：每日计算一次，缓存1天
- **获取方式**：从fund_performance_cache表查询

### 4. 静态数据（长期缓存）
- **字段**：持仓份额、成本价、持有金额
- **更新频率**：持仓变更时更新
- **获取方式**：直接从user_holdings表读取

## 目录结构

```
pro2/fund_search/
├── services/
│   ├── __init__.py                    # 服务模块导出
│   ├── fund_nav_cache_manager.py      # 缓存管理器（核心）
│   ├── holding_realtime_service.py    # 实时持仓服务
│   ├── fund_data_sync_service.py      # 后台数据同步服务
│   └── cache_api_routes.py            # 缓存相关API路由
├── sql/
│   └── 001_create_cache_tables.sql    # 数据库表结构
├── scripts/
│   └── init_cache_system.py           # 初始化脚本
├── web/
│   ├── app.py                         # Web应用（已修改）
│   └── static/js/
│       └── holdings-realtime-cache.js # 前端缓存管理器
└── docs/
    └── CACHE_SYSTEM_README.md         # 本文档
```

## 快速开始

### 1. 安装依赖

```bash
# 确保已安装所有依赖
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
# 进入项目目录
cd pro2/fund_search

# 执行初始化脚本
python scripts/init_cache_system.py --full
```

参数说明：
- `--full`: 执行完整初始化，包括历史数据同步
- `--days N`: 同步N天的历史数据（默认365天）

### 3. 启动服务

```bash
# 设置环境变量启动定时同步服务
export ENABLE_SYNC_SERVICE=true

# 启动Web应用
python web/app.py
```

Windows环境：
```powershell
$env:ENABLE_SYNC_SERVICE="true"
python web/app.py
```

## API接口

### 获取持仓数据（新接口）

```http
GET /api/my-holdings/combined?user_id=default_user
```

响应示例：
```json
{
  "success": true,
  "data": [
    {
      "fund_code": "007153",
      "fund_name": "汇添富中证银行ETF联接A",
      "fund_type": "index",
      "holding_shares": 100,
      "cost_price": 1.2345,
      "holding_amount": 123.45,
      "today_return": 0.50,
      "current_nav": 1.2420,
      "current_market_value": 124.20,
      "yesterday_return": 0.34,
      "annualized_return": -5.19,
      "max_drawdown": -45.75,
      "sharpe_ratio": 0.00,
      "composite_score": 0.32
    }
  ],
  "meta": {
    "fetch_time": "10:30:15",
    "count": 42,
    "data_freshness": {
      "realtime": "实时获取",
      "yesterday_data": "内存缓存15分钟",
      "performance": "数据库缓存1天"
    }
  }
}
```

### 仅获取实时数据（用于定时刷新）

```http
GET /api/my-holdings/realtime?user_id=default_user&codes=007153,006105
```

### 缓存管理接口

```http
# 获取缓存统计
GET /api/cache/stats

# 清除缓存
POST /api/cache/invalidate
Content-Type: application/json

{
  "fund_code": "007153",  // 可选，不传则清除全部
  "type": "memory"        // memory, performance, all
}

# 手动同步单只基金
POST /api/cache/fund/007153/sync

# 获取同步任务状态
GET /api/cache/sync/status

# 健康检查
GET /api/cache/health-check
```

## 前端使用示例

```html
<!-- 在持仓页面引入 -->
<script src="/static/js/holdings-realtime-cache.js"></script>

<script>
// 初始化缓存管理器
const cacheManager = new HoldingsCacheManager({
    userId: 'default_user',
    realtimeRefreshInterval: 30000  // 30秒
});

// 初始化表格渲染器
const tableRenderer = new HoldingsTableRenderer('holdings-table-body', cacheManager);

// 监听数据更新事件
cacheManager.on('dataUpdated', (event) => {
    if (event.type === 'full') {
        console.log('完整数据已更新');
    } else if (event.type === 'realtime') {
        console.log('实时数据已更新:', event.timestamp);
    }
});

// 加载数据
cacheManager.init();

// 手动刷新按钮
document.getElementById('refresh-btn').addEventListener('click', () => {
    cacheManager.manualRefresh();
});

// 页面卸载时清理
window.addEventListener('beforeunload', () => {
    cacheManager.destroy();
});
</script>
```

## 定时任务配置

系统默认配置以下定时任务：

| 时间 | 任务 | 说明 |
|------|------|------|
| 16:00 | 净值数据同步 | 同步所有持仓基金的净值数据 |
| 16:10 | 绩效指标计算 | 计算所有基金的绩效指标 |
| 16:20 | 持仓快照生成 | 生成用户持仓快照 |
| 每小时 | 失败重试 | 重试失败的同步任务 |

> 注：任务安排在下午4点左右错开执行（每10分钟一个任务），避免同时执行造成系统压力。

### 手动执行数据同步

```python
from services import FundNavCacheManager, FundDataSyncService
from data_retrieval.enhanced_database import EnhancedDatabaseManager
from shared.enhanced_config import DATABASE_CONFIG

# 初始化
db = EnhancedDatabaseManager(DATABASE_CONFIG)
cache = FundNavCacheManager(db)
sync = FundDataSyncService(cache, db)

# 手动同步单只基金
sync.manual_sync_fund('007153')
```

## 故障排查

### 1. 缓存未命中

检查缓存元数据：
```sql
SELECT fund_code, latest_date, sync_status, sync_fail_count
FROM fund_cache_metadata
WHERE fund_code = '007153';
```

### 2. 数据过期

手动触发同步：
```bash
curl -X POST http://localhost:5000/api/cache/fund/007153/sync
```

### 3. 查看同步日志

```sql
SELECT * FROM fund_sync_job_log
WHERE start_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
ORDER BY start_time DESC;
```

### 4. 健康检查

```bash
curl http://localhost:5000/api/cache/health-check
```

## 性能监控

### 查看缓存命中率

```bash
curl http://localhost:5000/api/cache/stats
```

响应示例：
```json
{
  "success": true,
  "data": {
    "memory_cache": {
      "total_entries": 42,
      "total_access": 156
    },
    "database_cache": {
      "total_funds": 42,
      "total_records": 15330,
      "perf_records": 42
    },
    "timestamp": "2024-01-15 10:30:15"
  }
}
```

## 注意事项

1. **首次部署**：建议执行完整初始化（带--full参数）以同步历史数据
2. **QDII基金**：由于净值更新延迟（T+2），缓存有效期会自动延长
3. **内存使用**：内存缓存限制为200条，采用LRU淘汰策略
4. **数据库空间**：历史净值数据会持续增长，建议定期清理（保留最近2年）

## 回滚方案

如需回滚到旧版本：

1. 设置环境变量禁用缓存服务：
```bash
export ENABLE_SYNC_SERVICE=false
```

2. 前端继续使用原有API：
- `/api/holdings` （旧接口仍然可用）

3. 删除缓存表（可选）：
```sql
DROP TABLE IF EXISTS fund_nav_cache;
DROP TABLE IF EXISTS fund_cache_metadata;
DROP TABLE IF EXISTS fund_performance_cache;
DROP TABLE IF EXISTS fund_sync_job_log;
```
