# 回测引擎微服务

将回测引擎拆分为独立的微服务，支持独立部署和扩展。

## 架构改进说明

这是根据`ARCHITECTURE_ANALYSIS.md`第9.2节第3项建议实施的微服务拆分。

## 服务特性

- **RESTful API**: 基于Flask的HTTP接口
- **gRPC支持**: 高性能二进制协议（可选）
- **异步处理**: 支持消息队列集成
- **独立部署**: 可单独部署和扩展

## 快速开始

### 启动服务

```bash
# 启动REST API服务
cd pro2/fund_search
python -m microservices.backtest_service.api

# 或使用gRPC服务
python -m microservices.backtest_service.grpc_server
```

### API端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/backtest/tasks` | POST | 创建回测任务 |
| `/api/backtest/tasks/<id>` | GET | 获取任务详情 |
| `/api/backtest/tasks/<id>/run` | POST | 执行任务 |
| `/api/backtest/tasks/<id>/status` | GET | 获取任务状态 |
| `/api/backtest/tasks/<id>/result` | GET | 获取任务结果 |
| `/api/backtest/tasks/<id>/cancel` | POST | 取消任务 |
| `/api/backtest/stats` | GET | 服务统计 |

## 配置

环境变量：
- `BACKTEST_SERVICE_PORT`: REST API端口（默认5001）
- `BACKTEST_GRPC_PORT`: gRPC端口（默认50051）
- `DATABASE_URL`: 数据库连接字符串
