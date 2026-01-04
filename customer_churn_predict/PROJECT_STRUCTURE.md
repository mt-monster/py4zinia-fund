# 项目结构说明

## 目录结构

```
customer_churn_predict/
├── agent/                      # Agent 模块
│   ├── __init__.py            # 模块导出
│   ├── core.py                # Agent 核心逻辑
│   ├── report_generator.py    # 报告生成器
│   └── prompts.py             # Prompt 模板管理
├── config/                     # 配置模块
│   ├── __init__.py            # 模块导出
│   ├── settings.py            # 配置项
│   └── prompts.yaml           # Prompt 配置
├── static/                     # 静态资源
│   └── css/
│       └── style.css          # 样式文件
├── templates/                  # 模板文件
│   ├── index.html             # 主页
│   └── agent.html             # Agent 对话页面
├── data/                       # 数据目录
│   ├── raw/                    # 原始数据
│   ├── processed/              # 处理后的数据
│   └── models/                 # 模型文件
├── reports/                    # 报告目录
├── app.py                      # Flask 主应用
├── churn_predict.py           # 预测核心逻辑
├── tools.py                   # 工具系统
├── Dockerfile                  # Docker 配置
├── docker-compose.yml          # Docker Compose
├── requirements.txt            # 依赖列表
├── README.md                   # 项目文档
├── API.md                      # API 文档
└── PROJECT_STRUCTURE.md        # 本文件
```

## 模块说明

### Agent 模块 (`agent/`)

- **core.py**: Agent 核心类，包含决策、规划、记忆等功能
- **report_generator.py**: 报告生成器，支持 JSON 和 HTML 格式
- **prompts.py**: Prompt 管理器，支持从 YAML 加载或使用默认 Prompt

### 配置模块 (`config/`)

- **settings.py**: 集中管理所有配置项
- **prompts.yaml**: Prompt 模板配置文件

### 静态资源 (`static/`)

- **css/style.css**: 全局样式文件

### 模板文件 (`templates/`)

- **index.html**: 主页面，提供传统功能界面
- **agent.html**: Agent 对话界面，支持自然语言交互

### 数据目录 (`data/`)

- **raw/**: 存储原始数据
- **processed/**: 存储处理后的数据
- **models/**: 存储训练好的模型和 Agent 记忆

### 报告目录 (`reports/`)

存储生成的分析报告（JSON 和 HTML 格式）

## 主要文件说明

### app.py

Flask 应用主文件，包含：
- Agent 相关路由
- 传统 API 路由（向后兼容）
- 模板渲染路由

### churn_predict.py

核心预测逻辑，包含：
- 数据生成
- 特征工程
- 模型训练
- SHAP 分析
- 挽留计划生成

### tools.py

工具系统，封装所有可调用的工具函数

## 使用方式

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python app.py
```

### Docker 运行

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 访问地址

- 主页: http://localhost:8000/
- Agent 界面: http://localhost:8000/agent
- API 文档: 参见 API.md

## 环境变量

可以通过环境变量配置：

- `LLM_API_KEY`: LLM API 密钥
- `LLM_BASE_URL`: LLM API 地址
- `LLM_MODEL`: LLM 模型名称
- `N_CUSTOMERS`: 客户数量（默认 3000）
- `N_WEEKS`: 周数（默认 12）
- `ENABLE_LLM`: 是否启用 LLM（默认 true）

