# API 文档

## 基础信息

- **Base URL**: `http://localhost:5000/api`
- **Content-Type**: `application/json`

## 健康检查

### GET /api/health

检查 API 服务器运行状态。

**响应示例**:
```json
{
  "status": "ok",
  "message": "API服务器运行正常"
}
```

## Agent 接口

### GET /api/agent/status

获取 Agent 状态信息。

**响应示例**:
```json
{
  "status": "success",
  "agent_status": {
    "capabilities": {
      "data_generation": "生成模拟客户数据",
      "model_training": "训练流失预测模型",
      "risk_prediction": "预测客户流失风险",
      "shap_analysis": "进行模型可解释性分析",
      "retention_planning": "生成个性化挽留计划",
      "report_generation": "生成分析报告"
    },
    "tools_count": 8,
    "memory_count": 15,
    "has_llm": true,
    "recent_memories": "..."
  }
}
```

### POST /api/agent/chat

与 Agent 进行对话。

**请求体**:
```json
{
  "message": "请帮我训练一个流失预测模型",
  "context": {}
}
```

**响应示例**:
```json
{
  "status": "success",
  "response": "我已经为您制定了执行计划...",
  "plan": [
    {
      "step": 1,
      "action": "data_generation",
      "description": "生成客户数据",
      "tool": "generate_data"
    }
  ],
  "results": {
    "data_generation": {
      "status": "success",
      "message": "成功生成 3000 个客户的 12 周数据"
    }
  }
}
```

### GET /api/agent/memory

获取 Agent 记忆。

**查询参数**:
- `limit` (可选): 返回最近 N 条记忆，默认 10

**响应示例**:
```json
{
  "status": "success",
  "memory": "[2025-01-01T10:00:00] train_model: 执行成功...",
  "memory_count": 15
}
```

### POST /api/agent/memory/clear

清空 Agent 记忆。

**响应示例**:
```json
{
  "status": "success",
  "message": "记忆已清空"
}
```

## 模型训练

### POST /api/train

训练流失预测模型。

**请求体** (可选):
```json
{
  "n_customers": 3000,
  "n_weeks": 12
}
```

**响应示例**:
```json
{
  "status": "success",
  "message": "模型训练完成",
  "customer_count": 3000,
  "feature_count": 29
}
```

## 风险预测

### POST /api/predict

预测客户流失风险并生成挽留计划。

**请求体** (可选):
```json
{
  "top_k": 30
}
```

**响应示例**:
```json
{
  "status": "success",
  "high_risk_count": 30,
  "plans_count": 30,
  "retention_plans": [
    {
      "客户ID": "CUST_000001",
      "风险等级": "高",
      "流失概率": "85.3%",
      "关键预警信号": "资产波动率: 0.45, 资金净流出周数: 3",
      "挽留策略": ["客户经理电话回访", "提供个性化投资建议"],
      "预期效果": "降低客户流失风险",
      "执行优先级": 1,
      "执行期限": "3个工作日"
    }
  ]
}
```

## 客户信息

### GET /api/customer/<customer_id>

获取单个客户的详细信息。

**路径参数**:
- `customer_id`: 客户ID

**响应示例**:
```json
{
  "status": "success",
  "customer_info": {
    "customer_id": "CUST_000001",
    "customer_type": 0,
    "risk_tolerance": 1,
    "base_assets": 50000.0,
    ...
  }
}
```

## 挽留计划

### GET /api/plans/download

下载挽留计划 Excel 文件内容。

**响应示例**:
```json
{
  "status": "success",
  "plans": [
    {
      "客户ID": "CUST_000001",
      "风险等级": "高",
      ...
    }
  ]
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
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

