# 架构改进实施文档

本文档记录了根据`ARCHITECTURE_ANALYSIS.md`第9.2节建议实施的所有架构改进。

## 实施概览

| 编号 | 改进建议 | 状态 | 实现模块 |
|------|----------|------|----------|
| 1 | 引入Celery处理耗时的后台任务 | ✅ 已完成 | `celery_tasks/` |
| 2 | 使用Redis/RabbitMQ实现事件驱动架构 | ✅ 已完成 | `messaging/` |
| 3 | 将回测引擎拆分为独立服务 | ✅ 已完成 | `microservices/backtest_service/` |
| 4 | 引入GraphQL优化API查询 | ✅ 已完成 | `graphql_api/` |

---

## 1. Celery异步任务处理

### 1.1 实施内容

- 创建了`celery_tasks/`模块，实现异步任务系统
- 支持的任务类型：
  - 基金数据更新任务
  - 回测计算任务
  - 数据同步任务
  - 缓存清理任务
- 配置定时任务调度（使用Celery Beat）
- 支持任务重试和错误处理

### 1.2 主要文件

- `celery_tasks/__init__.py` - 模块入口
- `celery_tasks/celery_app.py` - Celery应用配置
- `celery_tasks/tasks.py` - 任务定义
- `celery_tasks/runner.py` - 启动脚本

### 1.3 使用方法

```python
from celery_tasks import update_fund_data_task

# 异步执行
task = update_fund_data_task.delay(fund_code='000001')

# 检查状态
print(task.status)
```

### 1.4 启动命令

```bash
# 启动Worker
cd pro2/fund_search
python -m celery_tasks.runner worker

# 启动Beat调度器
python -m celery_tasks.runner beat

# 启动监控界面
python -m celery_tasks.runner flower
```

---

## 2. Redis消息队列和事件驱动架构

### 2.1 实施内容

- 创建了`messaging/`模块，实现基于Redis的事件驱动架构
- 核心组件：
  - `EventBus`: 事件总线，支持发布/订阅模式
  - `MessageQueue`: 可靠消息队列
  - `EventStore`: 事件持久化存储
- 实现事件处理器：
  - 基金数据更新处理器
  - 回测完成处理器
  - 缓存失效处理器

### 2.2 主要文件

- `messaging/__init__.py` - 模块入口
- `messaging/event_bus.py` - 事件总线
- `messaging/message_queue.py` - 消息队列
- `messaging/handlers.py` - 事件处理器

### 2.3 使用方法

```python
from messaging import EventBus, EventPriority

# 获取事件总线
event_bus = EventBus()

# 订阅事件
@event_bus.on('fund.data_updated')
def handle_update(event):
    print(f"基金 {event.data['fund_code']} 已更新")

# 发布事件
event_bus.emit('fund.data_updated', {'fund_code': '000001'})
```

---

## 3. 回测引擎微服务拆分

### 3.1 实施内容

- 创建了`microservices/backtest_service/`模块
- 将回测引擎从主应用解耦，作为独立服务运行
- 提供服务接口：
  - RESTful API (端口5001)
  - gRPC接口 (端口50051)
  - 任务管理机制
- 支持独立部署和水平扩展

### 3.2 主要文件

- `microservices/backtest_service/__init__.py` - 模块入口
- `microservices/backtest_service/service.py` - 服务核心
- `microservices/backtest_service/api.py` - REST API
- `microservices/backtest_service/grpc_server.py` - gRPC服务

### 3.3 API端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/backtest/tasks` | POST | 创建任务 |
| `/api/backtest/tasks/<id>/run` | POST | 执行任务 |
| `/api/backtest/tasks/<id>` | GET | 获取任务 |
| `/api/backtest/tasks/<id>/status` | GET | 获取状态 |
| `/api/backtest/tasks/<id>/result` | GET | 获取结果 |
| `/api/backtest/tasks/<id>/cancel` | POST | 取消任务 |

### 3.4 使用方法

```python
from microservices.backtest_service import BacktestService

service = BacktestService()
service.init_components()

# 创建任务
task = service.create_task(
    strategy_id='strategy_001',
    user_id='user_001',
    start_date='2023-01-01',
    end_date='2023-12-31'
)

# 执行任务
service.run_task(task.task_id)
```

---

## 4. GraphQL API优化查询

### 4.1 实施内容

- 创建了`graphql_api/`模块，实现GraphQL API
- 定义完整的Schema：
  - 查询（Query）：基金、策略、回测、持仓等
  - 变更（Mutation）：创建、更新、删除操作
  - 订阅（Subscription）：实时数据推送
- 支持精确数据获取，避免过度获取
- 提供GraphQL Playground交互界面

### 4.2 主要文件

- `graphql_api/__init__.py` - 模块入口
- `graphql_api/types.py` - 类型定义
- `graphql_api/queries.py` - 查询定义
- `graphql_api/mutations.py` - 变更定义
- `graphql_api/schema.py` - Schema组合
- `graphql_api/blueprint.py` - Flask蓝图

### 4.3 使用示例

```graphql
# 查询基金基本信息和净值
query {
  fund(code: "000001") {
    code
    name
    type
    navHistory(days: 30) {
      date
      nav
      dailyReturn
    }
    performance {
      sharpeRatio
      maxDrawdown
    }
  }
}

# 查询投资组合
query {
  portfolio(userId: "user_001", realtime: true) {
    totalValue
    totalReturn
    dailyProfit
    holdings {
      fundCode
      fundName
      currentValue
      profitLoss
    }
  }
}

# 运行回测
mutation {
  runBacktest(input: {
    strategyId: "strategy_001"
    userId: "user_001"
    startDate: "2023-01-01"
    endDate: "2023-12-31"
    initialCapital: 100000
  }) {
    success
    taskId
  }
}
```

### 4.4 访问Playground

启动应用后访问：`http://localhost:5000/graphql`

---

## 环境配置

### 依赖安装

```bash
pip install -r requirements.txt
```

### 必要的环境变量

```bash
# Redis连接
export REDIS_URL=redis://localhost:6379/0

# Celery配置
export CELERY_RESULT_BACKEND=redis://localhost:6379/0

# 功能开关
export USE_CELERY_BG=true        # 使用Celery替代本地后台任务
export ENABLE_SYNC_SERVICE=true  # 启用数据同步服务
export ENABLE_BACKGROUND_UPDATE=true  # 启用后台更新
```

### 服务启动

```bash
# 1. 启动Redis
redis-server

# 2. 启动主应用
cd pro2/fund_search
python web/app_enhanced.py

# 3. 启动Celery Worker（可选）
python -m celery_tasks.runner worker

# 4. 启动回测微服务（可选）
python -m microservices.backtest_service.api
```

---

## 架构改进验证

启动应用后，可以通过以下端点验证改进是否正确应用：

```bash
# 查看架构改进状态
curl http://localhost:5000/api/system/enhancements

# 健康检查
curl http://localhost:5000/api/system/health
```

---

## 回滚说明

如需回滚到原始版本：

1. 使用原始`web/app.py`代替`web/app_enhanced.py`
2. 停止使用Celery Worker
3. 关闭Redis服务

原始功能不受影响，新模块为可选组件。

---

*文档生成时间: 2026-02-26*
