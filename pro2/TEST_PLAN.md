# Pro2 Fund Search 项目 - 业务功能测试方案

## 1. 测试概述

### 1.1 项目背景
Pro2 Fund Search 是一个基于 Flask 的基金分析系统，提供基金数据获取、持仓管理、回测分析、绩效计算等功能。

### 1.2 测试目标
- 确保核心功能正确性和稳定性
- 验证数据准确性（基金净值、收益率、夏普比率等）
- 保证系统性能和响应速度
- 确保 API 接口稳定可靠

### 1.3 测试范围
| 模块 | 功能 | 优先级 |
|------|------|--------|
| 数据获取 | 基金净值、历史数据、实时数据 | P0 |
| 持仓管理 | CRUD 操作、收益计算 | P0 |
| 分析计算 | 夏普比率、波动率、回撤等 | P0 |
| 回测引擎 | 策略回测、绩效评估 | P1 |
| Dashboard | 统计数据、图表展示 | P1 |
| Web API | 所有 RESTful 接口 | P0 |
| 缓存系统 | 缓存命中、过期策略 | P1 |

---

## 2. 测试策略

### 2.1 测试金字塔
```
        /\
       /  \     端到端测试 (10%)
      /----\    
     /      \   集成测试 (30%)
    /--------\  
   /          \ 单元测试 (60%)
  /------------\
```

### 2.2 测试类型

#### 2.2.1 单元测试 (Unit Testing)
- **目标**：单个函数/方法级别的测试
- **工具**：pytest
- **覆盖率目标**：≥ 80%
- **执行频率**：每次代码提交

#### 2.2.2 集成测试 (Integration Testing)
- **目标**：模块间交互测试
- **工具**：pytest + 测试数据库
- **覆盖范围**：数据库操作、API 调用、缓存交互
- **执行频率**：每日构建

#### 2.2.3 端到端测试 (E2E Testing)
- **目标**：完整业务流程测试
- **工具**：Selenium / Playwright
- **覆盖范围**：用户操作全流程
- **执行频率**：版本发布前

#### 2.2.4 性能测试 (Performance Testing)
- **目标**：系统性能和稳定性
- **工具**：Locust / JMeter
- **指标**：响应时间、吞吐量、并发能力
- **执行频率**：每周

### 2.3 测试环境

| 环境 | 用途 | 数据 |
|------|------|------|
| 本地开发 | 开发调试 | 模拟数据 |
| 测试环境 | 自动化测试 | 脱敏生产数据 |
| 预发布 | 验收测试 | 生产数据副本 |
| 生产 | 监控验证 | 真实数据 |

---

## 3. 单元测试方案

### 3.1 测试目录结构
```
tests/
├── __init__.py
├── conftest.py                 # pytest 配置和 fixtures
├── unit/                       # 单元测试
│   ├── __init__.py
│   ├── test_data_retrieval/    # 数据获取模块
│   ├── test_services/          # 服务模块
│   ├── test_backtesting/       # 回测模块
│   └── test_utils/             # 工具函数
├── integration/                # 集成测试
│   ├── __init__.py
│   ├── test_api/               # API 测试
│   ├── test_database/          # 数据库测试
│   └── test_cache/             # 缓存测试
├── e2e/                        # 端到端测试
│   ├── __init__.py
│   ├── test_dashboard/         # Dashboard 测试
│   └── test_holdings/          # 持仓管理测试
└── fixtures/                   # 测试数据
    ├── fund_data.json
    ├── holdings.json
    └── historical_nav.csv
```

### 3.2 核心模块测试计划

#### 3.2.1 数据获取模块 (data_retrieval)

```python
# tests/unit/test_data_retrieval/test_multi_source_adapter.py

class TestMultiSourceDataAdapter:
    """多数据源适配器测试"""
    
    def test_get_realtime_data_success(self):
        """测试获取基金实时数据成功"""
        pass
    
    def test_get_realtime_data_invalid_code(self):
        """测试无效基金代码处理"""
        pass
    
    def test_get_historical_data(self):
        """测试获取历史数据"""
        pass
    
    def test_get_performance_metrics(self):
        """测试获取绩效指标"""
        pass
    
    def test_cache_strategy(self):
        """测试缓存策略"""
        pass
    
    def test_qdii_fund_handling(self):
        """测试QDII基金特殊处理"""
        pass
```

**测试要点：**
- 基金代码格式验证（6位数字）
- 空值/异常值处理
- 缓存命中和过期逻辑
- QDII基金前向追溯逻辑
- 多数据源降级策略

#### 3.2.2 绩效计算模块 (performance_metrics)

```python
# tests/unit/test_backtesting/test_performance_metrics.py

class TestPerformanceCalculator:
    """绩效计算器测试"""
    
    def test_calculate_sharpe_ratio_normal(self):
        """测试正常情况下的夏普比率计算"""
        pass
    
    def test_calculate_sharpe_ratio_zero_volatility(self):
        """测试零波动率情况"""
        pass
    
    def test_calculate_sharpe_ratio_insufficient_data(self):
        """测试数据不足情况"""
        pass
    
    def test_calculate_volatility(self):
        """测试波动率计算"""
        pass
    
    def test_calculate_max_drawdown(self):
        """测试最大回撤计算"""
        pass
    
    def test_calculate_annualized_return(self):
        """测试年化收益率计算"""
        pass
```

**测试要点：**
- 夏普比率计算准确性（使用已知结果验证）
- 边界条件（空数组、单元素、零值）
- 年化系数（252个交易日）
- 无风险利率处理
- 数据格式转换（百分比vs小数）

#### 3.2.3 缓存模块 (cache)

```python
# tests/unit/test_services/test_cache.py

class TestMemoryCache:
    """内存缓存测试"""
    
    def test_set_and_get(self):
        """测试设置和获取缓存"""
        pass
    
    def test_ttl_expiration(self):
        """测试TTL过期"""
        pass
    
    def test_lru_eviction(self):
        """测试LRU淘汰"""
        pass
    
    def test_clear(self):
        """测试清空缓存"""
        pass
    
    def test_thread_safety(self):
        """测试线程安全"""
        pass
```

### 3.3 测试 Fixtures

```python
# tests/conftest.py

import pytest
import pandas as pd
import numpy as np

@pytest.fixture
def sample_fund_code():
    """示例基金代码"""
    return "000001"  # 华夏成长混合

@pytest.fixture
def sample_qdii_fund_code():
    """示例QDII基金代码"""
    return "016667"  # 景顺长城全球半导体

@pytest.fixture
def sample_historical_data():
    """示例历史净值数据"""
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='B')
    np.random.seed(42)
    nav_values = 1.0 + np.cumsum(np.random.randn(len(dates)) * 0.01)
    
    return pd.DataFrame({
        'date': dates,
        'nav': nav_values,
        'accum_nav': nav_values * 1.05,
        'daily_return': np.random.randn(len(dates)) * 0.01
    })

@pytest.fixture
def mock_db_manager():
    """模拟数据库管理器"""
    class MockDBManager:
        def execute_query(self, sql, params=None):
            return pd.DataFrame()
        
        def execute_sql(self, sql, params=None):
            return True
    
    return MockDBManager()
```

---

## 4. 集成测试方案

### 4.1 API 集成测试

```python
# tests/integration/test_api/test_dashboard.py

class TestDashboardAPI:
    """Dashboard API 集成测试"""
    
    def test_get_dashboard_stats(self, client):
        """测试获取仪表盘统计"""
        response = client.get('/api/dashboard/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'totalAssets' in data['data']
    
    def test_get_profit_trend(self, client):
        """测试获取收益趋势"""
        response = client.get('/api/dashboard/profit-trend?days=90')
        assert response.status_code == 200
        data = response.get_json()
        assert 'labels' in data['data']
        assert 'profit' in data['data']
    
    def test_get_fund_type_allocation(self, client):
        """测试获取基金类型分布"""
        response = client.get('/api/dashboard/fund-type-allocation')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data['data'], list)
```

### 4.2 数据库集成测试

```python
# tests/integration/test_database/test_holdings.py

class TestHoldingsDatabaseOperations:
    """持仓数据库操作测试"""
    
    def test_add_holding(self, db_manager):
        """测试添加持仓"""
        holding_data = {
            'user_id': 'test_user',
            'fund_code': '000001',
            'fund_name': '测试基金',
            'holding_shares': 1000,
            'cost_price': 1.5
        }
        result = db_manager.add_holding(holding_data)
        assert result is True
        
        # 验证数据已写入
        holdings = db_manager.get_user_holdings('test_user')
        assert len(holdings) == 1
        assert holdings[0]['fund_code'] == '000001'
    
    def test_update_holding(self, db_manager):
        """测试更新持仓"""
        pass
    
    def test_delete_holding(self, db_manager):
        """测试删除持仓"""
        pass
```

### 4.3 缓存集成测试

```python
# tests/integration/test_cache/test_cache_integration.py

class TestCacheIntegration:
    """缓存集成测试"""
    
    def test_preloader_cache_interaction(self):
        """测试预加载器与缓存交互"""
        pass
    
    def test_adapter_cache_strategy(self):
        """测试适配器缓存策略"""
        pass
```

---

## 5. 端到端测试方案

### 5.1 用户场景测试

#### 场景1：首次使用系统
```gherkin
Feature: 首次使用系统
  Scenario: 用户首次访问系统
    Given 用户打开系统首页
    Then 页面显示基金列表
    And 显示总资产为0
    And 显示"暂无持仓"提示
  
  Scenario: 用户添加第一只基金
    Given 用户在基金列表页面
    When 点击"添加持仓"按钮
    And 输入基金代码"000001"
    And 输入持仓份额1000
    And 点击"保存"
    Then 提示"添加成功"
    And 持仓列表显示该基金
    And Dashboard总资产更新
```

#### 场景2：查看收益分析
```gherkin
Feature: 查看收益分析
  Scenario: 用户查看收益趋势
    Given 用户已持有基金
    When 访问 Dashboard 页面
    Then 显示收益趋势图表
    And 图表包含近90天数据
    And 显示沪深300对比曲线
  
  Scenario: 用户查看基金详情
    Given 用户在持仓列表页面
    When 点击某只基金名称
    Then 显示基金详情页
    And 显示实时净值和涨跌幅
    And 显示历史净值曲线
    And 显示绩效指标（夏普比率等）
```

### 5.2 E2E 测试代码示例

```python
# tests/e2e/test_dashboard/test_dashboard_flow.py

class TestDashboardFlow:
    """Dashboard 端到端测试"""
    
    def test_dashboard_loads_successfully(self, browser):
        """测试 Dashboard 成功加载"""
        browser.goto('http://localhost:5001/dashboard')
        
        # 验证关键元素存在
        assert browser.is_visible('text=总资产')
        assert browser.is_visible('text=今日收益')
        assert browser.is_visible('text=持仓基金')
    
    def test_fund_list_display(self, browser):
        """测试基金列表显示"""
        browser.goto('http://localhost:5001/dashboard')
        
        # 等待基金列表加载
        browser.wait_for_selector('.fund-item', timeout=10000)
        
        # 验证至少有一只基金显示
        fund_items = browser.query_selector_all('.fund-item')
        assert len(fund_items) > 0
    
    def test_profit_chart_rendering(self, browser):
        """测试收益图表渲染"""
        browser.goto('http://localhost:5001/dashboard')
        
        # 等待图表加载
        browser.wait_for_selector('#profitTrendChart', timeout=10000)
        
        # 验证图表canvas存在
        chart = browser.query_selector('#profitTrendChart')
        assert chart is not None
```

---

## 6. 性能测试方案

### 6.1 测试指标

| 指标 | 目标值 | 警告阈值 | 错误阈值 |
|------|--------|----------|----------|
| API响应时间 | < 200ms | 500ms | 1s |
| Dashboard加载 | < 3s | 5s | 10s |
| 数据库查询 | < 100ms | 300ms | 500ms |
| 并发用户数 | 100 | 50 | - |
| 缓存命中率 | > 80% | 60% | 50% |

### 6.2 Locust 性能测试脚本

```python
# tests/performance/locustfile.py

from locust import HttpUser, task, between
import random

class FundSearchUser(HttpUser):
    """基金搜索系统性能测试用户"""
    wait_time = between(1, 3)
    
    fund_codes = ['000001', '000002', '000003', '006373', '016667']
    
    @task(5)
    def get_dashboard_stats(self):
        """获取Dashboard统计"""
        self.client.get('/api/dashboard/stats')
    
    @task(3)
    def get_fund_list(self):
        """获取基金列表"""
        self.client.get('/api/holdings/list?user_id=default_user')
    
    @task(3)
    def get_fund_detail(self):
        """获取基金详情"""
        fund_code = random.choice(self.fund_codes)
        self.client.get(f'/api/fund/{fund_code}')
    
    @task(2)
    def get_profit_trend(self):
        """获取收益趋势"""
        self.client.get('/api/dashboard/profit-trend?days=90')
    
    @task(1)
    def get_realtime_data(self):
        """获取实时数据"""
        fund_code = random.choice(self.fund_codes)
        self.client.get(f'/api/fund/{fund_code}/realtime')
```

### 6.3 性能测试执行

```bash
# 启动 Locust
locust -f tests/performance/locustfile.py \
    --host=http://localhost:5001 \
    --users=100 \
    --spawn-rate=10 \
    --run-time=5m
```

---

## 7. 数据准确性测试

### 7.1 基金数据验证

```python
# tests/data_validation/test_fund_data_accuracy.py

class TestFundDataAccuracy:
    """基金数据准确性测试"""
    
    def test_nav_calculation_accuracy(self):
        """测试净值计算准确性"""
        # 使用已知结果的数据进行验证
        fund_code = '000001'
        adapter = MultiSourceDataAdapter()
        
        data = adapter.get_realtime_data(fund_code)
        
        # 验证今日涨跌幅计算
        # today_return = (current_nav - previous_nav) / previous_nav * 100
        expected_return = (data['current_nav'] - data['previous_nav']) / data['previous_nav'] * 100
        assert abs(data['today_return'] - expected_return) < 0.01
    
    def test_sharpe_ratio_accuracy(self):
        """测试夏普比率计算准确性"""
        # 使用已知夏普比率的基金进行验证
        calculator = PerformanceCalculator()
        
        # 模拟已知收益率数据
        daily_returns = np.array([0.01, -0.005, 0.008, 0.002, -0.001])
        
        sharpe = calculator.calculate_sharpe_ratio(daily_returns)
        
        # 手动计算验证
        excess_returns = daily_returns - calculator.daily_risk_free
        expected_sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        
        assert abs(sharpe - expected_sharpe) < 0.0001
```

### 7.2 第三方数据对比

```python
# 从多个数据源获取同一基金数据，验证一致性
def test_cross_source_consistency():
    """测试跨数据源一致性"""
    fund_code = '000001'
    
    # 从 Tushare 获取
    tushare_data = adapter.get_from_tushare(fund_code)
    
    # 从 Akshare 获取
    akshare_data = adapter.get_from_akshare(fund_code)
    
    # 验证净值差异在可接受范围
    assert abs(tushare_data['nav'] - akshare_data['nav']) < 0.001
```

---

## 8. 测试执行计划

### 8.1 持续集成流程

```yaml
# .github/workflows/test.yml

name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run unit tests
        run: pytest tests/unit -v --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v1

  integration-tests:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: test
          MYSQL_DATABASE: fund_test
    steps:
      - uses: actions/checkout@v2
      - name: Run integration tests
        run: pytest tests/integration -v

  performance-tests:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v2
      - name: Run performance tests
        run: |
          locust -f tests/performance/locustfile.py \
            --headless -u 50 -r 5 --run-time 2m \
            --host=http://localhost:5001
```

### 8.2 测试执行频率

| 测试类型 | 触发条件 | 执行时间 |
|----------|----------|----------|
| 单元测试 | 每次提交 | < 5分钟 |
| 集成测试 | 每次PR | < 15分钟 |
| 端到端测试 | 每日夜间 | < 30分钟 |
| 性能测试 | 每周/发布前 | < 1小时 |

---

## 9. 测试报告模板

### 9.1 测试报告结构

```markdown
# 测试报告 - YYYY-MM-DD

## 执行概要
- 测试日期: 
- 执行人: 
- 版本号: 
- 环境: 

## 测试结果统计
| 类型 | 总数 | 通过 | 失败 | 跳过 | 成功率 |
|------|------|------|------|------|--------|
| 单元测试 | | | | | |
| 集成测试 | | | | | |
| E2E测试 | | | | | |

## 覆盖率报告
- 代码覆盖率: XX%
- 主要模块覆盖情况: 

## 发现的缺陷
| 编号 | 描述 | 严重程度 | 状态 |
|------|------|----------|------|

## 性能指标
| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| API响应时间 | < 200ms | | |
| Dashboard加载 | < 3s | | |

## 结论与建议
```

---

## 10. 附录

### 10.1 测试数据准备

```bash
# 初始化测试数据库
python scripts/init_test_db.py

# 导入测试数据
python scripts/import_test_data.py --fixtures tests/fixtures/
```

### 10.2 常用命令

```bash
# 运行所有单元测试
pytest tests/unit -v

# 运行特定模块测试
pytest tests/unit/test_data_retrieval -v

# 生成覆盖率报告
pytest --cov=fund_search --cov-report=html

# 运行性能测试
locust -f tests/performance/locustfile.py --host=http://localhost:5001

# 运行特定标记的测试
pytest -m "slow" -v
```

### 10.3 测试标记 (Markers)

```python
# pytest.ini
[pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
    performance: marks tests as performance tests
    database: marks tests that require database
```

---

*文档版本: 1.0*
*最后更新: 2026-02-12*
