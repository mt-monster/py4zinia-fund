# 基金数据缓存系统 - 安装指南

## 已完成的工作

### 1. 数据库表结构 (`sql/001_create_cache_tables.sql`)
- `fund_nav_cache` - 基金净值缓存表
- `fund_cache_metadata` - 缓存元数据表
- `fund_analysis_results` - 基金分析结果表（包含绩效指标）
- `user_holding_daily` - 用户持仓日终数据表
- `user_portfolio_snapshot` - 用户持仓快照表
- `fund_sync_job_log` - 同步任务日志表

**注**：绩效指标直接存储在 `fund_analysis_results` 表中，不再单独创建 `fund_performance_cache` 表，避免数据冗余。

### 2. 后端服务模块 (`services/`)
- `fund_nav_cache_manager.py` - 缓存管理器核心（三级缓存策略）
- `holding_realtime_service.py` - 实时持仓服务（数据分级获取）
- `fund_data_sync_service.py` - 后台数据同步服务（定时任务）
- `cache_api_routes.py` - 缓存相关API路由

### 3. Web API集成
- 修改 `web/app.py` - 添加缓存服务初始化
- 新API端点：
  - `GET /api/my-holdings/combined` - 获取分层缓存的持仓数据
  - `GET /api/my-holdings/realtime` - 仅获取实时数据
  - `GET /api/cache/stats` - 缓存统计
  - `POST /api/cache/invalidate` - 清除缓存
  - `POST /api/cache/fund/{code}/sync` - 手动同步
  - `GET /api/cache/sync/status` - 同步状态
  - `GET /api/cache/health-check` - 健康检查

### 4. 前端组件 (`web/static/js/holdings-realtime-cache.js`)
- `HoldingsCacheManager` - 前端缓存管理器
- `HoldingsTableRenderer` - 表格渲染器
- 自动定时刷新机制

### 5. 工具脚本 (`scripts/init_cache_system.py`)
- 数据库表创建
- 元数据初始化
- 历史数据同步
- 绩效指标计算

## 安装步骤

### 步骤1：执行数据库初始化

```bash
cd pro2/fund_search
python scripts/init_cache_system.py --full --days 365
```

### 步骤2：启动服务（启用同步服务）

Linux/Mac:
```bash
export ENABLE_SYNC_SERVICE=true
python web/app.py
```

Windows:
```powershell
$env:ENABLE_SYNC_SERVICE="true"
python web/app.py
```

### 步骤3：前端页面引入缓存管理器

在 `my_holdings.html` 或对应页面添加：

```html
<script src="/static/js/holdings-realtime-cache.js"></script>
<script>
const cacheManager = new HoldingsCacheManager({
    userId: 'default_user',
    realtimeRefreshInterval: 30000
});
const tableRenderer = new HoldingsTableRenderer('holdings-table-body', cacheManager);
cacheManager.init();
</script>
```

## 数据分级详情

| 级别 | 数据类型 | 缓存位置 | 有效期 | 更新方式 |
|------|----------|----------|--------|----------|
| 实时 | 日涨跌幅、当前净值 | 不缓存 | - | 每次请求实时获取 |
| 准实时 | 昨日净值、昨日涨跌幅 | 内存 | 15分钟 | 日终定时更新 |
| 低频 | 年化收益、夏普比率等 | 数据库 | 1天 | 日终定时计算 |
| 静态 | 持仓份额、成本价 | 数据库 | 长期 | 持仓变更时更新 |

## 预期效果

- 页面加载时间：从15-30秒降至1-3秒
- 外部API请求：从42次/页降至仅实时数据请求
- 数据库查询：优化为简单的缓存表查询

## 监控和维护

访问以下接口监控系统状态：
- 缓存统计：`GET /api/cache/stats`
- 健康检查：`GET /api/cache/health-check`
- 同步状态：`GET /api/cache/sync/status`
