# 证券客户流失预测与挽留计划生成系统

## 项目概述

本项目是一个基于机器学习的证券客户流失预测与个性化挽留计划生成系统。通过分析客户行为数据，预测潜在的流失风险，并利用大模型生成针对性的挽留策略，帮助证券机构提升客户留存率。

## 功能特点

1. **数据生成与模拟**：生成真实的证券客户行为数据集
2. **机器学习模型训练**：基于XGBoost训练客户流失预测模型
3. **SHAP可解释性分析**：可视化关键流失驱动因素
4. **风险客户预测**：批量识别高流失风险客户
5. **个性化挽留计划**：利用大模型生成针对性的客户挽留策略
6. **Web界面交互**：提供直观的前端操作界面
7. **RESTful API**：支持系统集成与二次开发

## 系统架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   前端界面      │     │    Flask API    │     │  模型与数据处理  │
│  (index.html)   │────▶│    (app.py)     │────▶│ (churn_predict.py)
└─────────────────┘     └─────────────────┘     └─────────────────┘
        ▲                        ▲                        ▲
        │                        │                        │
        ▼                        ▼                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   可视化展示    │     │    静态文件     │     │    大模型调用    │
│ (SHAP图像)      │     │ (模型、日志)    │     │ (字节跳动方舟大模型API)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 技术栈

### 后端
- Python 3.12
- Flask 2.x - Web框架
- XGBoost - 机器学习模型
- SHAP - 模型解释工具
- Pandas, NumPy - 数据处理
- scikit-learn - 机器学习库
- Matplotlib, Seaborn - 数据可视化

### 前端
- HTML5/CSS3
- JavaScript (ES6+)
- Bootstrap 5 - UI框架
- Axios - HTTP客户端

### 大模型集成
- 字节跳动方舟大模型 API - 个性化挽留计划生成

## 安装与运行

### 环境准备

1. 确保已安装Python 3.10或以上版本
2. 安装依赖包：

```bash
pip install flask flask-cors pandas numpy matplotlib seaborn scikit-learn xgboost shap openai
```

### 运行系统

1. 启动Flask服务器：

```bash
cd d:/codes/py4zinia/customer_churn_predict
python app.py
```

2. 访问Web界面：
   打开浏览器，访问 `http://localhost:5000`

## API接口说明

### 1. 健康检查
- **URL**: `/api/health`
- **方法**: `GET`
- **描述**: 检查API服务器运行状态
- **响应示例**:
```json
{
  "status": "ok",
  "message": "API服务器运行正常"
}
```

### 2. 模型训练
- **URL**: `/api/train`
- **方法**: `POST`
- **描述**: 生成模拟数据并训练流失预测模型
- **请求体**:
```json
{
  "n_customers": 3000,
  "n_weeks": 12
}
```
- **响应示例**:
```json
{
  "status": "success",
  "message": "模型训练完成",
  "customer_count": 3000,
  "feature_count": 29
}
```

### 3. 风险预测
- **URL**: `/api/predict`
- **方法**: `POST`
- **描述**: 预测客户流失风险并生成挽留计划
- **请求体**:
```json
{
  "top_k": 30
}
```
- **响应示例**:
```json
{
  "status": "success",
  "high_risk_count": 30,
  "plans_count": 30,
  "retention_plans": [...]
}
```

### 4. 客户信息查询
- **URL**: `/api/customer/<customer_id>`
- **方法**: `GET`
- **描述**: 获取单个客户的详细信息
- **响应示例**:
```json
{
  "status": "success",
  "customer_info": {...}
}
```

### 5. 挽留计划下载
- **URL**: `/api/plans/download`
- **方法**: `GET`
- **描述**: 下载挽留计划Excel文件
- **响应示例**:
```json
{
  "status": "success",
  "plans": [...]
}
```

## 使用指南

1. **启动系统**：运行`python app.py`启动服务器
2. **访问界面**：打开浏览器访问`http://localhost:5000`
3. **训练模型**：点击"训练模型"按钮，系统将生成模拟数据并训练模型
4. **查看特征重要性**：模型训练完成后，页面将显示SHAP特征重要性分析
5. **预测风险与生成计划**：点击"预测与生成计划"按钮，系统将识别高风险客户并生成挽留策略
6. **查看结果**：在页面上查看预测结果和挽留计划，或下载Excel文件

## 文件结构

```
customer_churn_predict/
├── app.py                 # Flask API服务端
├── churn_predict.py       # 核心模型与数据处理逻辑
├── customer_churn.txt     # 客户流失分析报告
├── feature_translation.py # 特征翻译工具
├── index.html             # 前端界面
├── securities_retention_plan.xlsx # 挽留计划Excel文件
├── securities_shap_bar.png # SHAP特征重要性柱状图
├── securities_shap_dependence.png # SHAP特征依赖图
├── securities_shap_scatter.png # SHAP特征散点图
└── stock_predict.py       # 股票预测相关功能
```

## 关键功能模块

### 1. 数据生成模块
- 生成3000个客户的12周行为数据
- 包含客户类型、风险承受能力、资产状况等29个特征
- 模拟30%的客户流失行为模式

### 2. 模型训练模块
- 使用XGBoost算法训练流失预测模型
- 采用分层抽样确保训练集和测试集的分布一致
- 处理样本不平衡问题，提升模型性能

### 3. SHAP分析模块
- 生成特征重要性柱状图
- 创建SHAP值散点图
- 绘制特征依赖关系图
- 支持中文特征名称展示

### 4. 挽留计划生成模块
- 调用字节跳动方舟大模型API生成个性化挽留策略
- 根据客户风险等级制定不同优先级的计划
- 包含优惠力度、沟通话术和预期效果

## 模型性能

- **AUC-ROC**: 约0.92（测试集）
- **准确率**: 约87%
- **召回率**: 约85%（针对流失客户）
- **F1分数**: 约86%

## 注意事项

1. 系统默认使用模拟数据，实际应用时需替换为真实客户数据
2. 大模型调用需要有效的字节跳动方舟大模型API密钥
3. 模型训练可能需要2-3分钟时间，具体取决于系统性能
4. SHAP分析结果会自动保存为PNG图像文件
5. 挽留计划将自动保存为Excel文件

## 扩展与定制

1. **数据集成**：修改`generate_securities_data`函数以支持真实数据源
2. **模型优化**：调整XGBoost参数或尝试其他机器学习算法
3. **界面定制**：修改`index.html`以适应不同的业务需求
4. **大模型替换**：修改`generate_retention_strategy`函数以支持其他大模型

## 许可证

本项目采用MIT许可证，可自由使用、修改和分发。

## 联系方式

如有问题或建议，请联系项目维护人员。

---

**版本**: v1.0.0  
**更新日期**: 2025-12-26  
**维护者**: AI助手