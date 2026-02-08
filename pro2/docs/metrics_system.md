# 关键绩效指标系统（KPI Metrics System）

## 目标
- **模块化与可扩展**：指标定义与计算逻辑统一注册管理。
- **规则与计算解耦**：业务部门规则通过配置注入，不侵入核心计算。
- **标准化数据格式**：统一输入/输出结构，便于对接前后端与多业务线。
- **多维度分析**：支持按业务维度（如部门、产品线、策略类型）并行计算。

## 接口定义
### MetricsInput（标准化输入）
- `equity_curve`: 组合净值序列
- `benchmark_curve`: 基准净值序列（可选）
- `trades`: 交易记录（可选）
- `risk_free_rate`: 年化无风险利率
- `trading_days`: 年交易日数
- `metadata`: 附加元数据（可选）
- `dimensions`: 多维度输入（可选，key 为维度名）

### MetricRuleSet（业务规则）
- `enabled_metrics`: 启用指标列表（白名单）
- `risk_free_rate`: 全局无风险利率覆盖
- `trading_days`: 全局交易日数覆盖
- `annualization_days`: 年化折算天数覆盖
- `overrides`: 指标级覆盖（按 `metric_id` 定义）

### MetricReport（标准化输出）
- `summary`: 主维度指标集合
- `dimensions`: 多维度指标集合（可选）
- `metadata`: 报告元数据（可选）

## 标准化输出格式示例
```json
{
  "summary": {
    "metrics": {
      "total_return": {
        "id": "total_return",
        "name": "总收益率",
        "value": 0.1234,
        "category": "收益",
        "unit": "ratio",
        "description": "期间总收益率",
        "meta": {
          "risk_free_rate": 0.02,
          "trading_days": 252,
          "annualization_days": 365
        }
      }
    }
  },
  "dimensions": {
    "dept_a": {
      "metrics": {
        "total_return": {"id": "total_return", "value": 0.05, "unit": "ratio"}
      }
    }
  },
  "metadata": {
    "source": "performance_metrics"
  }
}
```

## 业务规则配置示例
```python
from backtesting.performance_metrics import MetricRuleSet

rule_set = MetricRuleSet(
    enabled_metrics=["total_return", "annual_return", "max_drawdown"],
    risk_free_rate=0.03,
    annualization_days=252,
    overrides={
        "sharpe_ratio": {"risk_free_rate": 0.025}
    }
)
```

## 多维度分析示例
```python
from backtesting.performance_metrics import MetricsInput, calculate_metrics_report

dimension_inputs = {
    "dept_a": MetricsInput(equity_curve=[1.0, 1.02, 1.05]),
    "dept_b": MetricsInput(equity_curve=[1.0, 0.98, 1.01])
}

report = calculate_metrics_report(
    equity_curve=[1.0, 1.01, 1.03],
    dimensions=dimension_inputs
)
```

## 扩展新指标
1. 在 `MetricEngine.register_defaults` 中新增 `MetricDefinition`。
2. 实现对应的 `_compute_xxx` 计算函数。
3. 如需业务规则调整，通过 `MetricRuleSet` 设置覆盖项。

## 设计说明
- **核心计算逻辑**：集中在 `MetricEngine` 内部的计算函数。
- **业务规则**：通过 `MetricRuleSet` 进行开关与参数覆盖。
- **兼容性**：原有 `PerformanceCalculator.calculate_all_metrics` 仍返回 `PerformanceMetrics`，内部通过新引擎计算。