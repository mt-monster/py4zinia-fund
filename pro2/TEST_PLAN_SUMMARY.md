# Pro2 Fund Search - 测试方案总结

## 📋 测试方案概览

本文档总结了为 pro2/fund_search 项目设计的完整业务功能测试方案。

---

## 📁 生成的测试文件

### 1. 测试方案文档
| 文件 | 说明 |
|------|------|
| `TEST_PLAN.md` | 完整测试方案主文档 |
| `TEST_PLAN_SUMMARY.md` | 本文档 - 测试方案总结 |
| `tests/README.md` | 测试套件使用指南 |

### 2. 测试配置文件
| 文件 | 说明 |
|------|------|
| `pytest.ini` | Pytest 主配置文件 |
| `requirements-test.txt` | 测试依赖列表 |
| `.github/workflows/test.yml` | CI/CD 测试工作流 |

### 3. 测试代码文件
| 文件 | 类型 | 说明 |
|------|------|------|
| `tests/conftest.py` | 配置 | Pytest fixtures 和配置 |
| `tests/unit/test_data_retrieval/test_multi_source_adapter.py` | 单元测试 | 数据获取模块测试 |
| `tests/integration/test_api/test_dashboard_api.py` | 集成测试 | Dashboard API 测试 |
| `tests/performance/locustfile.py` | 性能测试 | Locust 性能测试脚本 |
| `tests/fixtures/fund_data.json` | 测试数据 | 示例基金数据 |
| `scripts/init_test_db.py` | 工具脚本 | 测试数据库初始化 |

---

## 🎯 测试策略金字塔

```
        /\
       /  \     E2E 测试 (10%) - Selenium/Playwright
      /----\    
     /      \   集成测试 (30%) - API/Database/Cache
    /--------\  
   /          \ 单元测试 (60%) - pytest
  /------------\
```

---

## 📊 测试覆盖范围

### P0 优先级（核心功能）
- ✅ 基金数据获取（实时/历史）
- ✅ 绩效指标计算（夏普比率、波动率等）
- ✅ 持仓管理（CRUD）
- ✅ Dashboard 统计数据
- ✅ Web API 接口

### P1 优先级（重要功能）
- ✅ 缓存系统（命中/过期/淘汰）
- ✅ 回测引擎
- ✅ 收益趋势分析
- ✅ 风险分析

### P2 优先级（辅助功能）
- ⏳ 基金类型分类
- ⏳ 截图OCR识别
- ⏳ 策略推荐

---

## 🚀 快速开始指南

### 1. 安装测试依赖

```bash
cd pro2
pip install -r requirements-test.txt
```

### 2. 运行单元测试

```bash
# 运行所有单元测试
pytest tests/unit -v

# 运行特定模块
pytest tests/unit/test_data_retrieval -v

# 生成覆盖率报告
pytest tests/unit --cov=fund_search --cov-report=html
```

### 3. 运行集成测试

```bash
# 需要测试数据库
pytest tests/integration -v
```

### 4. 运行性能测试

```bash
# 启动应用后
locust -f tests/performance/locustfile.py --host=http://localhost:5001
```

---

## 🧪 测试类型详解

### 1. 单元测试

**目标**: 测试单个函数/方法

**示例**:
```python
def test_calculate_sharpe_ratio():
    calculator = PerformanceCalculator()
    returns = np.array([0.001, -0.0005, 0.0008])
    sharpe = calculator.calculate_sharpe_ratio(returns)
    assert isinstance(sharpe, float)
    assert not np.isnan(sharpe)
```

**覆盖模块**:
- 数据获取模块 (`data_retrieval/`)
- 绩效计算 (`backtesting/performance_metrics.py`)
- 缓存系统 (`services/cache/`)

### 2. 集成测试

**目标**: 测试模块间交互

**示例**:
```python
def test_get_dashboard_stats(client):
    response = client.get('/api/dashboard/stats')
    assert response.status_code == 200
    data = response.get_json()
    assert 'totalAssets' in data['data']
```

**覆盖场景**:
- API 接口集成
- 数据库操作
- 缓存集成

### 3. 性能测试

**目标**: 验证系统性能

**指标**:
| 指标 | 目标值 | 警告阈值 |
|------|--------|----------|
| API响应时间 | < 200ms | 500ms |
| Dashboard加载 | < 3s | 5s |
| 并发用户数 | 100 | 50 |

**Locust 场景**:
- Dashboard 查看 (权重: 10)
- 基金详情查看 (权重: 5)
- 持仓管理 (权重: 3)

---

## 📈 持续集成配置

### GitHub Actions 工作流

已配置 `.github/workflows/test.yml`，包含：

1. **单元测试** - Python 3.9/3.10/3.11
2. **集成测试** - MySQL 服务容器
3. **代码质量** - flake8, black, mypy
4. **性能测试** - Locust (仅 main 分支)

### 触发条件

```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
```

---

## 🔧 测试工具链

| 工具 | 用途 | 版本 |
|------|------|------|
| pytest | 测试框架 | >=7.0.0 |
| pytest-cov | 覆盖率 | >=4.0.0 |
| pytest-xdist | 并行测试 | >=3.0.0 |
| Locust | 性能测试 | >=2.15.0 |
| flake8 | 代码检查 | >=6.0.0 |
| black | 代码格式化 | >=23.0.0 |

---

## 📝 测试标记 (Markers)

| 标记 | 用途 | 示例 |
|------|------|------|
| `@pytest.mark.slow` | 慢测试 | `pytest -m "not slow"` |
| `@pytest.mark.integration` | 集成测试 | `pytest -m integration` |
| `@pytest.mark.e2e` | E2E测试 | `pytest -m e2e` |
| `@pytest.mark.database` | 数据库测试 | `pytest -m database` |
| `@pytest.mark.performance` | 性能测试 | `pytest -m performance` |

---

## 🎭 测试 Fixtures

### 基础 Fixtures
- `sample_fund_code` - 示例基金代码
- `sample_historical_data` - 历史净值数据
- `sample_holding_data` - 持仓数据
- `mock_db_manager` - 模拟数据库
- `mock_cache_manager` - 模拟缓存
- `client` - Flask 测试客户端

### 使用示例
```python
def test_get_fund_detail(client, sample_fund_code):
    response = client.get(f'/api/fund/{sample_fund_code}')
    assert response.status_code == 200
```

---

## 📋 测试数据

### fixtures/fund_data.json
包含：
- 5只示例基金的基础信息
- 3条用户持仓记录
- 收益趋势数据（30天/90天）
- 基金类型分布

---

## ✅ 验收标准

### 功能测试
- [ ] 所有API接口返回正确数据结构
- [ ] 基金数据计算准确性验证
- [ ] 缓存策略按预期工作
- [ ] 数据库CRUD操作正常

### 性能测试
- [ ] API平均响应时间 < 200ms
- [ ] Dashboard 加载时间 < 3s
- [ ] 支持100并发用户
- [ ] 缓存命中率 > 80%

### 兼容性测试
- [ ] Python 3.9/3.10/3.11
- [ ] Chrome/Firefox/Edge 浏览器

---

## 🚀 后续优化建议

### 短期
1. 补充更多边界条件测试
2. 增加异常处理测试
3. 完善测试数据 fixtures

### 中期
1. 引入契约测试（Pact）
2. 增加可视化回归测试
3. 建立测试数据工厂

### 长期
1. 引入混沌工程测试
2. 建立自动化测试平台
3. 性能基线监控

---

## 📞 问题反馈

如遇到测试相关问题：
1. 查看 `tests/README.md` 故障排除章节
2. 检查测试日志输出
3. 确认环境配置正确

---

*文档版本: 1.0*
*生成日期: 2026-02-12*
