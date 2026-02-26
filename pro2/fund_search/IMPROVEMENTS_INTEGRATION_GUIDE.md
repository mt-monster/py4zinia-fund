# 架构改进集成指南

本指南说明如何将架构改进集成到现有系统中。

## 快速集成

### 步骤1：安装依赖

```bash
cd pro2
pip install -r requirements.txt
```

### 步骤2：配置Redis

确保Redis服务器运行：

```bash
# Windows
redis-server.exe

# Linux/Mac
redis-server
```

### 步骤3：启动增强版应用

```bash
cd pro2/fund_search
python web/app_enhanced.py
```

### 步骤4：启动Celery Worker（推荐）

```bash
# 新终端窗口
cd pro2/fund_search
python -m celery_tasks.runner worker
```

### 步骤5：启动回测微服务（可选）

```bash
# 新终端窗口
cd pro2/fund_search
python -m microservices.backtest_service.api
```

## 功能验证

### 1. 验证Celery

```python
from celery_tasks import update_fund_data_task

# 触发异步任务
result = update_fund_data_task.delay(fund_code='000001', data_type='basic')
print(f"任务ID: {result.id}")
print(f"状态: {result.status}")
```

### 2. 验证消息队列

```python
from messaging import EventBus

event_bus = EventBus()

@event_bus.on('test.event')
def handle_test(event):
    print(f"收到事件: {event.data}")

event_bus.emit('test.event', {'message': 'Hello'})
```

### 3. 验证GraphQL

访问：`http://localhost:5000/graphql`

执行查询：
```graphql
{
  fundTypes
  marketOverview {
    totalFunds
    avgReturn
  }
}
```

### 4. 验证微服务

```bash
# 检查健康状态
curl http://localhost:5001/health

# 创建回测任务
curl -X POST http://localhost:5001/api/backtest/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "test_strategy",
    "user_id": "test_user",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  }'
```

## 与现有代码集成

### 在现有路由中使用Celery

```python
# web/routes/backtest.py
from celery_tasks import run_backtest_task

def run_strategy_backtest():
    data = request.get_json()
    
    # 改为异步执行
    task = run_backtest_task.delay(
        strategy_id=data.get('strategy_id'),
        user_id=data.get('user_id', 'default'),
        start_date=data.get('start_date'),
        end_date=data.get('end_date')
    )
    
    return jsonify({
        'success': True,
        'task_id': task.id,
        'message': '回测任务已提交'
    })
```

### 在现有服务中使用事件总线

```python
# services/fund_data_service.py
from messaging import EventBus

class FundDataService:
    def update_fund(self, fund_code):
        # 更新逻辑...
        
        # 发布事件
        event_bus = EventBus()
        event_bus.emit('fund.data_updated', {
            'fund_code': fund_code,
            'timestamp': datetime.now().isoformat()
        })
```

## 配置选项

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `REDIS_URL` | redis://localhost:6379/0 | Redis连接 |
| `USE_CELERY_BG` | true | 使用Celery后台任务 |
| `ENABLE_SYNC_SERVICE` | true | 启用数据同步 |
| `ENABLE_BACKGROUND_UPDATE` | true | 启用后台更新 |
| `BACKTEST_SERVICE_PORT` | 5001 | 回测服务端口 |
| `BACKTEST_GRPC_PORT` | 50051 | gRPC端口 |

### 选择性启用

可以只启用部分改进：

```python
# web/app.py 中添加

# 只启用GraphQL
from graphql_api import init_graphql
init_graphql(app)

# 只启用消息队列（不启用Celery）
from messaging import EventBus, register_event_handlers
event_bus = EventBus()
register_event_handlers(event_bus)
```

## 故障排除

### Redis连接失败

```
Error: Connection refused
```
解决方案：启动Redis服务器

### Celery任务不执行

```
检查Worker是否启动：
python -m celery_tasks.runner worker --loglevel=debug
```

### GraphQL不可用

```
安装依赖：pip install graphene>=3.3.0
```

## 性能对比

| 指标 | 改进前 | 改进后 | 提升 |
|------|--------|--------|------|
| 回测执行 | 同步阻塞 | 异步非阻塞 | 用户响应快 |
| 数据更新 | 定时任务 | 分布式任务 | 可扩展 |
| API查询 | REST多接口 | GraphQL单接口 | 减少请求 |
| 服务耦合 | 单体 | 微服务 | 独立扩展 |
