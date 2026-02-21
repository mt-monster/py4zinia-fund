---
name: refactor-strategy-analysis-realdata
overview: 重构全站策略/组合分析界面，移除模拟数据，改为基于真实交易数据计算与展示，统一两位小数，并补充数据来源说明与关键指标模块。
design:
  architecture:
    framework: html
  styleKeywords:
    - 简洁
    - 数据驱动
    - 卡片布局
    - 高对比
  fontSystem:
    fontFamily: Noto Sans
    heading:
      size: 28px
      weight: 600
    subheading:
      size: 18px
      weight: 500
    body:
      size: 14px
      weight: 400
  colorSystem:
    primary:
      - "#3A5BFF"
      - "#2F3B52"
    background:
      - "#F6F8FB"
      - "#FFFFFF"
    text:
      - "#1F2A37"
      - "#6B7280"
    functional:
      - "#10B981"
      - "#EF4444"
      - "#F59E0B"
todos:
  - id: audit-mock-removal
    content: 清点并移除策略/组合分析页面与脚本的模拟数据展示
    status: completed
  - id: backend-real-data-api
    content: 在 app.py 与 real_data_fetcher.py 中补齐真实数据与来源字段接口
    status: completed
    dependencies:
      - audit-mock-removal
  - id: frontend-real-data-render
    content: 更新 strategy/portfolio 页面脚本，接入真实数据与两位小数格式化
    status: completed
    dependencies:
      - backend-real-data-api
  - id: market-index-api
    content: 替换 my-holdings/api.js 的指数接口为真实 API 调用
    status: completed
    dependencies:
      - backend-real-data-api
  - id: ui-source-precision-check
    content: 校验各页面数据来源说明与全量两位小数展示一致性
    status: completed
    dependencies:
      - frontend-real-data-render
---

## User Requirements

- 重构全站策略/组合分析相关界面，移除所有模拟数据展示
- 所有数值计算基于真实交易数据与历史数据，结果统一保留两位小数
- 增加清晰的数据来源说明，避免误导性数据展示

## Product Overview

- 面向策略分析与组合分析的多页面展示体系
- 页面风格简洁直观，信息密度高但层级清晰
- 强调实时数据、历史分析图表、关键指标模块的可读性与准确性

## Core Features

- 实时数据展示：组合净值/收益率、基准指数、持仓市值与盈亏
- 历史数据分析图表：组合净值与基准对比曲线
- 关键指标精确计算模块：收益率、波动、回撤、夏普等指标
- 数据来源说明：明确真实数据来源与基准说明

## Tech Stack Selection

- 后端：Python + Flask（现有 `app.py`）
- 前端：Jinja2 模板 + 原生 JavaScript
- 图表与样式：现有 Bootstrap + Canvas/Chart 脚本
- 数据：AKShare + 现有真实数据获取器 `real_data_fetcher.py`

## Implementation Approach

- 以现有真实数据 API 为核心，统一前端取数入口，彻底移除模拟/静态数据路径
- 前端新增统一数值格式化与数据来源展示逻辑，确保所有展示与计算一致
- 后端补齐“实时指数/持仓实时数据”与“数据来源说明”字段，前后端统一协议
- 性能上避免重复拉取：复用现有 API、限制请求频率，前端缓存页面内一次渲染数据

## Implementation Notes

- 移除所有 JS 中的随机/静态数据生成函数与 fallback 模拟路径
- 真实数据不足时返回明确错误并提示“数据不足”，不再回退模拟数据
- 所有金额/收益率/比例统一 `toFixed(2)` 展示，计算保留原始精度
- 日志使用现有 logger，避免输出大规模原始数据

## Architecture Design

- 页面层：`templates/*.html` 负责结构与区块布局
- 交互层：`static/js/*` 负责真实数据获取与渲染
- API 层：`app.py` 负责真实数据聚合与精确指标计算
- 数据层：`real_data_fetcher.py` 提供真实指数与净值历史数据

## Directory Structure Summary

本次改造集中在策略/组合分析相关页面与其数据脚本、API 端点，统一真实数据来源与格式化展示。
project-root/
├── pro2/fund_search/web/templates/strategy.html  # [MODIFY] 策略分析主界面，添加实时数据/历史图表/关键指标模块与数据来源说明，移除模拟展示
├── pro2/fund_search/web/templates/strategy_editor.html  # [MODIFY] 策略编辑/回测页，保证分析展示使用真实数据与两位小数格式
├── pro2/fund_search/web/templates/portfolio_analysis.html  # [MODIFY] 组合分析报告页，移除内置静态数据，改为真实 API 渲染
├── pro2/fund_search/web/templates/strategy_test.html  # [MODIFY] 测试页清理模拟提示，展示真实数据来源说明
├── pro2/fund_search/web/static/js/portfolio-analysis-integrated.js  # [MODIFY] 移除 fallback 模拟数据路径，统一真实 API 取数与格式化
├── pro2/fund_search/web/static/js/portfolio-analysis.js  # [MODIFY] 废弃模拟生成逻辑，改为真实数据驱动或停止引用
├── pro2/fund_search/web/static/js/my-holdings/api.js  # [MODIFY] getMarketIndex 改为真实 API 调用
├── pro2/fund_search/web/app.py  # [MODIFY] 增加/完善真实数据接口、数据来源字段、实时指数数据输出
├── pro2/fund_search/web/real_data_fetcher.py  # [MODIFY] 增加获取最新指数数据与日涨跌的真实数据方法

## Design Style

- 简洁直观、卡片式信息布局、层级清晰
- 以数据为核心的展示方式，减少装饰性元素
- 统一浅色背景与高对比文本，提升可读性

## Page Planning

- 策略分析页：核心入口，包含实时区块、历史图表、指标模块与来源说明
- 策略编辑/回测页：强调回测结果与指标展示一致性
- 组合分析报告页：聚焦指标、图表、基金明细与来源说明

## Block Design (示例：策略分析页)

1. 顶部导航：主导航 + 页面标题，固定在顶部
2. 实时数据区：净值、收益率、基准指数、持仓盈亏的并列卡片
3. 历史图表区：净值曲线与基准对比图，支持日期范围说明
4. 关键指标区：核心绩效指标卡片，统一两位小数格式
5. 数据来源说明区：数据来源、时间范围、基准说明
6. 底部导航：全站一致的页脚导航