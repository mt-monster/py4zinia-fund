# py4zinia 基金投资分析平台

基于 Python Flask 的综合性基金投资分析 Web 应用。

## 项目简介

py4zinia 是一个功能完整的基金投资分析平台，提供基金搜索、持仓管理、投资策略、回测分析等功能。

## 核心功能

| 功能 | 说明 |
|------|------|
| 📊 首页仪表盘 | 持仓概览、收益趋势、基金类型分布 |
| 🔍 基金搜索 | 基金净值、持仓明细、历史走势 |
| 💼 持仓管理 | 持仓导入、编辑、DIP定投收益计算 |
| 📈 策略回测 | 双均线、均值回归、目标市值、网格交易 |
| 💡 投资建议 | 个性化调仓建议、估值分析 |

## 系统架构

```
py4zinia/
├── pro2/                              # 主项目目录
│   ├── fund_search/                   # 核心业务模块
│   │   ├── web/                       # Web层
│   │   │   ├── routes/               # API路由 (15个模块)
│   │   │   ├── templates/            # 前端模板
│   │   │   ├── static/               # 静态资源
│   │   │   └── app_enhanced.py       # Flask应用入口
│   │   ├── services/                 # 业务服务层
│   │   ├── data_retrieval/           # 数据获取层
│   │   ├── backtesting/              # 回测引擎
│   │   ├── celery_tasks/             # 异步任务
│   │   ├── messaging/                # 消息总线
│   │   ├── graphql_api/              # GraphQL接口
│   │   └── shared/                   # 共享工具
│   ├── services/                     # 独立服务
│   │   └── backtest_service/         # 回测微服务
│   └── reports/                      # 报告输出目录
└── README.md
```

## Web前端功能模块

### 3.1 首页仪表盘 (Dashboard)

**入口路由**：`/`

- 持仓总资产统计与今日收益展示
- 近90天收益趋势图表（支持与基准对比）
- 基金类型分布可视化（股票型、债券型、混合型等）
- 持仓Top10股票展示
- 恐慌/贪婪指数实时监控
- 系统负载与API响应时间监控

**API接口**：
| API路径 | 功能说明 |
|---------|----------|
| `/api/dashboard/stats` | 获取仪表盘统计数据 |
| `/api/dashboard/profit-trend` | 获取收益趋势数据 |
| `/api/dashboard/allocation` | 获取基金类型分布 |
| `/api/dashboard/holding-stocks` | 获取持仓股票 |
| `/api/market/fear-greed` | 获取恐慌贪婪指数 |

### 3.2 基金搜索与分析

**入口路由**：`/funds`

- 基金代码/名称搜索
- 基金详细信息查询（净值、规模、评级等）
- 基金历史净值查询
- 基金持仓明细查询
- 分阶段收益展示（近1周、1月、3月、6月、1年等）
- 基金资产配置分析

**API接口**：
| API路径 | 功能说明 |
|---------|----------|
| `/api/funds` | 基金列表搜索 |
| `/api/fund/<fund_code>` | 基金详细信息 |
| `/api/fund/<fund_code>/history` | 历史净值 |
| `/api/fund/<fund_code>/holdings` | 基金持仓明细 |
| `/api/fund/<fund_code>/allocation` | 资产配置 |
| `/api/fund/<fund_code>/latest` | 最新净值数据 |

### 3.3 持仓管理

**入口路由**：`/holdings`

- 用户持仓基金列表展示
- 持仓导入（支持截图OCR识别）
- 持仓编辑、删除、清空
- 持仓成本修改
- 定投收益计算（DIP策略）
- 持仓相关性分析
- 综合分析报告

**API接口**：
| API路径 | 功能说明 |
|---------|----------|
| `/api/holdings` | 持仓列表/添加/修改 |
| `/api/holdings/list` | 持仓列表查询 |
| `/api/holdings/import/screenshot` | 截图导入 |
| `/api/holdings/analyze/correlation` | 相关性分析 |
| `/api/holdings/analyze/comprehensive` | 综合分析 |
| `/api/dip/returns` | 定投收益计算 |

### 3.4 ETF分析

**入口路由**：`/etf`

- ETF列表展示
- ETF详细信息查询
- ETF对比分析

### 3.5 回测分析

**入口路由**：`/backtest`

- 投资策略回测
- 策略绩效评估
- 风险指标分析
- 收益归因分析
- 蒙特卡洛模拟

### 3.6 策略管理

**入口路由**：`/strategies`

- 内置策略查看
- 自定义策略创建与管理
- 策略元数据管理
- 策略反馈收集

### 3.7 投资建议

**入口路由**：`/investment-advice`

- 基于持仓的个性化投资建议
- 策略模拟与回测
- 基金估值分析
- 调仓建议生成

## 后端核心服务

### 4.1 数据获取服务

**模块路径**：`data_retrieval/`

| 模块 | 功能说明 |
|------|----------|
| `fetchers/` | 多源数据获取器（AkShare、新浪等） |
| `adapters/` | 数据适配器，统一数据格式 |
| `parsers/` | 数据解析器（含OCR截图识别） |

### 4.2 缓存服务

**模块路径**：`services/cache/`

| 模块 | 功能说明 |
|------|----------|
| `memory_cache.py` | 内存缓存 |
| `persistent_cache.py` | 持久化缓存 |
| `fund_cache.py` | 基金数据缓存 |

### 4.3 基金分析服务

| 服务 | 功能说明 |
|------|----------|
| `fund_analyzer.py` | 基金综合分析 |
| `fund_data_service.py` | 基金数据服务 |
| `fund_realtime.py` | 实时行情 |
| `fund_type_service.py` | 基金类型分类 |
| `dip_return_calculator.py` | 定投收益计算 |
| `portfolio_importer.py` | 持仓导入 |

### 4.4 异步任务服务

使用 Celery 实现后台异步任务：
- 基金数据定时同步
- 缓存预热
- 报告生成

## 回测引擎

### 内置策略

1. **双均线动量策略 (Dual MA)**
   - 适用场景：趋势明显的市场环境
   - 优势：捕捉中长期趋势，避免假突破

2. **均值回归策略 (Mean Reversion)**
   - 适用场景：震荡整理的市场
   - 优势：低买高卖，逆向投资

3. **目标市值策略 (Target Value)**
   - 适用场景：长期定投和稳健投资
   - 优势：成本平均，平滑波动

4. **网格交易策略 (Grid Trading)**
   - 适用场景：波动率适中的震荡市
   - 优势：分批建仓，降低平均成本

### 分析模块

| 模块 | 功能说明 |
|------|----------|
| `performance_metrics.py` | 绩效指标计算 |
| `risk_metrics.py` | 风险指标分析 |
| `visualization.py` | 可视化图表 |
| `monte_carlo.py` | 蒙特卡洛模拟 |
| `attribution.py` | 收益归因 |

## 技术栈

- **Web框架**: Flask
- **前端**: Bootstrap 5 + Chart.js
- **数据获取**: AkShare、新浪财经
- **缓存**: Redis、Memory Cache
- **异步任务**: Celery

## 快速开始

### 安装依赖

```bash
cd pro2
pip install -r requirements.txt
```

### 启动服务

```bash
cd pro2/fund_search
python enhanced_main.py
```

访问 http://localhost:5000 打开首页。

## 主要页面路由

| 路由 | 说明 |
|------|------|
| `/` | 首页仪表盘 |
| `/funds` | 基金搜索 |
| `/holdings` | 持仓管理 |
| `/etf` | ETF分析 |
| `/backtest` | 回测分析 |
| `/strategies` | 策略管理 |
| `/investment-advice` | 投资建议 |

## 注意事项

1. 投资有风险，请谨慎决策
2. 回测结果不代表未来表现
3. 数据获取依赖网络连接

---

*最后更新：2026年2月*
