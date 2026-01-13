# API 文档

## 基础信息

- **Base URL**: `http://localhost:8000/api`
- **Content-Type**: `application/json`

## Agent 相关接口

### 1. Agent 对话

**POST** `/api/agent/chat`

与 Agent 进行自然语言对话。

**请求体**:
```json
{
  "message": "请帮我训练一个流失预测模型",
  "context": {}
}
```

**响应**:
```json
{
  "status": "success",
  "response": "我已经为您制定了执行计划...",
  "plan": [...],
  "results": {...}
}
```

### 2. Agent 状态查询

**GET** `/api/agent/status`

获取 Agent 当前状态。

**响应**:
```json
{
  "status": "success",
  "agent_status": {
    "capabilities": {...},
    "tools_count": 8,
    "memory_count": 15,
    "has_llm": true
  }
}
```

### 3. Agent 记忆查询

**GET** `/api/agent/memory?limit=10`

获取 Agent 历史记忆。

**参数**:
- `limit` (可选): 返回最近 N 条记忆，默认 10

**响应**:
```json
{
  "status": "success",
  "memory": "[2025-01-01T10:00:00] train_model: 执行成功...",
  "memory_count": 15
}
```

### 4. 清空 Agent 记忆

**POST** `/api/agent/memory/clear`

清空 Agent 的所有记忆。

**响应**:
```json
{
  "status": "success",
  "message": "记忆已清空"
}
```

## 传统接口（兼容）

### 1. 健康检查

**GET** `/api/health`

检查 API 服务器运行状态。

**响应**:
```json
{
  "status": "ok",
  "message": "API服务器运行正常"
}
```

### 2. 训练模型

**POST** `/api/train`

生成模拟数据并训练流失预测模型。

**请求体**:
```json
{
  "n_customers": 3000,
  "n_weeks": 12
}
```

**响应**:
```json
{
  "status": "success",
  "message": "模型训练完成",
  "customer_count": 3000,
  "feature_count": 29
}
```

### 3. 预测风险

**POST** `/api/predict`

预测客户流失风险并生成挽留计划。

**请求体**:
```json
{
  "top_k": 30
}
```

**响应**:
```json
{
  "status": "success",
  "high_risk_count": 30,
  "plans_count": 30,
  "retention_plans": [...]
}
```

### 4. 客户信息查询

**GET** `/api/customer/<customer_id>`

获取单个客户的详细信息。

**响应**:
```json
{
  "status": "success",
  "customer_info": {...}
}
```

### 5. 挽留计划下载

**GET** `/api/plans/download`

下载挽留计划 Excel 文件。

**响应**:
```json
{
  "status": "success",
  "plans": [...]
}
```

## 错误响应

所有接口在出错时都会返回以下格式：

```json
{
  "status": "error",
  "message": "错误描述"
}
```

HTTP 状态码：
- `200`: 成功
- `400`: 请求错误
- `404`: 资源不存在
- `500`: 服务器错误

