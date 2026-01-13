# Agent 架构说明

## 概述

本项目已升级为基于 AI Agent 架构的客户流失预警系统。Agent 具备自主决策、任务规划、记忆管理等核心能力。

## 核心组件

### 1. Agent 核心 (`agent.py`)

`ChurnPredictionAgent` 类是系统的核心，负责：

- **意图理解**：解析用户自然语言指令
- **任务规划**：将复杂任务分解为多个步骤
- **工具调用**：根据规划调用相应的工具
- **记忆管理**：记录历史操作和结果
- **响应生成**：生成自然语言响应

#### 关键方法

- `plan(user_intent)`: 根据用户意图制定执行计划
- `execute_plan(plan, context)`: 执行计划中的各个步骤
- `chat(user_message, context)`: 对话接口，处理用户消息
- `add_memory(action, result, context)`: 添加记忆
- `get_memory_summary(limit)`: 获取记忆摘要

### 2. 工具系统 (`tools.py`)

`ChurnPredictionTools` 类提供所有可用的工具：

- `generate_data()`: 生成客户数据
- `feature_engineering()`: 进行特征工程
- `train_model()`: 训练流失预测模型
- `predict_risk()`: 预测客户流失风险
- `shap_analysis()`: 进行模型可解释性分析
- `generate_retention_plan()`: 生成挽留计划
- `generate_report()`: 生成分析报告
- `get_customer_info()`: 获取客户信息

### 3. 配置系统 (`config.py`)

集中管理所有配置项：

- LLM 配置（API 密钥、模型等）
- 数据生成配置
- 模型训练配置
- 预测配置
- 文件路径配置
- Agent 配置

### 4. API 服务 (`app.py`)

Flask 应用提供以下接口：

#### Agent 相关接口

- `POST /api/agent/chat`: Agent 对话接口
- `GET /api/agent/status`: 查询 Agent 状态
- `GET /api/agent/memory`: 查询 Agent 记忆
- `POST /api/agent/memory/clear`: 清空 Agent 记忆

#### 兼容接口（保持向后兼容）

- `POST /api/train`: 训练模型
- `POST /api/predict`: 预测风险
- `GET /api/customer/<customer_id>`: 获取客户信息
- `GET /api/plans/download`: 下载挽留计划

## 工作流程

### 典型对话流程

```
用户: "请帮我训练一个流失预测模型"
  ↓
Agent.plan() 解析意图
  ↓
生成执行计划:
  1. 生成客户数据
  2. 进行特征工程
  3. 训练流失预测模型
  4. 进行模型可解释性分析
  ↓
Agent.execute_plan() 执行计划
  ↓
调用工具:
  - tools.generate_data()
  - tools.feature_engineering()
  - tools.train_model()
  - tools.shap_analysis()
  ↓
记录记忆
  ↓
生成响应返回用户
```

## 扩展指南

### 添加新工具

1. 在 `tools.py` 中添加新方法：

```python
def your_new_tool(self, param1: str) -> Dict[str, Any]:
    """新工具描述"""
    try:
        # 实现逻辑
        result = do_something(param1)
        return {
            'status': 'success',
            'message': '执行成功',
            'result': result
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'执行失败: {str(e)}'
        }
```

2. 在 `app.py` 中注册：

```python
agent.register_tool('your_new_tool', tools.your_new_tool, '新工具描述')
```

3. 在 `agent.py` 的 `plan()` 方法中添加意图识别：

```python
elif 'your_keyword' in intent_lower:
    plan.append({
        'step': 1,
        'action': 'your_action',
        'description': '执行描述',
        'tool': 'your_new_tool'
    })
```

### 自定义规划逻辑

修改 `agent.py` 中的 `plan()` 方法，添加新的意图识别规则。

### 自定义响应生成

修改 `agent.py` 中的 `_generate_response()` 方法，自定义响应格式。

## 记忆系统

Agent 的记忆系统记录所有操作历史：

- **时间戳**：操作时间
- **动作**：执行的操作名称
- **结果**：操作结果
- **上下文**：操作上下文信息

记忆可以：
- 查询（`get_memory_summary()`）
- 保存到文件（`save_memory()`）
- 从文件加载（`load_memory()`）
- 清空（`clear_memory()`）

## 优势

1. **自然语言交互**：用户无需记忆复杂命令
2. **自主决策**：Agent 自动选择执行工具
3. **任务规划**：自动分解复杂任务
4. **记忆管理**：记录历史操作，支持上下文理解
5. **易于扩展**：模块化设计，易于添加新功能
6. **向后兼容**：保留原有 API 接口

## 未来改进方向

1. **LLM 增强**：使用 LLM 进行更智能的意图理解
2. **多轮对话**：支持上下文相关的多轮对话
3. **错误恢复**：自动处理错误并重试
4. **并行执行**：支持并行执行多个工具
5. **可视化**：添加 Agent 决策过程的可视化

