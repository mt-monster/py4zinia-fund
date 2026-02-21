# Pro2 Fund Search - 测试套件

## 目录结构

```
tests/
├── README.md                   # 本文档
├── conftest.py                 # Pytest 配置和共享 fixtures
├── pytest.ini                  # Pytest 配置文件
├── unit/                       # 单元测试
│   ├── test_data_retrieval/    # 数据获取模块测试
│   ├── test_services/          # 服务模块测试
│   └── test_backtesting/       # 回测模块测试
├── integration/                # 集成测试
│   ├── test_api/               # API 接口测试
│   └── test_cache/             # 缓存集成测试
├── e2e/                        # 端到端测试
├── performance/                # 性能测试
│   └── locustfile.py           # Locust 性能测试脚本
└── fixtures/                   # 测试数据
    └── fund_data.json          # 示例基金数据
```

## 快速开始

### 安装测试依赖

```bash
# 在项目根目录执行
pip install -r requirements-test.txt
```

`requirements-test.txt` 内容：
```
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-xdist>=3.0.0
locust>=2.15.0
requests>=2.28.0
```

### 运行测试

```bash
# 运行所有单元测试
cd pro2
pytest tests/unit -v

# 运行特定模块的测试
pytest tests/unit/test_data_retrieval -v

# 运行集成测试
pytest tests/integration -v

# 生成覆盖率报告
pytest tests/unit --cov=fund_search --cov-report=html

# 运行标记为 slow 的测试
pytest -m "slow" -v

# 排除 slow 测试
pytest -m "not slow" -v

# 并行运行测试（需要 pytest-xdist）
pytest -n auto tests/unit
```

## 测试类型说明

### 1. 单元测试 (Unit Tests)

测试单个函数或类的功能，不依赖外部服务。

```python
# 示例
def test_calculate_sharpe_ratio():
    from fund_search.backtesting.performance_metrics import PerformanceCalculator
    
    calculator = PerformanceCalculator()
    daily_returns = np.array([0.001, -0.0005, 0.0008])
    
    sharpe = calculator.calculate_sharpe_ratio(daily_returns)
    
    assert isinstance(sharpe, float)
    assert not np.isnan(sharpe)
```

### 2. 集成测试 (Integration Tests)

测试模块间的交互，可能需要数据库或缓存服务。

```bash
# 运行集成测试前确保测试数据库已启动
pytest tests/integration -v
```

### 3. 端到端测试 (E2E Tests)

测试完整业务流程，需要完整的应用环境。

```bash
# 启动应用后运行
pytest tests/e2e -v
```

### 4. 性能测试 (Performance Tests)

使用 Locust 进行负载测试。

```bash
# 启动 Locust Web 界面
locust -f tests/performance/locustfile.py --host=http://localhost:5001

# 命令行模式运行
locust -f tests/performance/locustfile.py \
    --headless \
    -u 50 \
    -r 5 \
    --run-time 5m \
    --host=http://localhost:5001
```

## 测试标记 (Markers)

| 标记 | 说明 | 使用示例 |
|------|------|----------|
| `@pytest.mark.slow` | 慢测试 | `pytest -m "not slow"` |
| `@pytest.mark.integration` | 集成测试 | `pytest -m integration` |
| `@pytest.mark.e2e` | E2E测试 | `pytest -m e2e` |
| `@pytest.mark.database` | 需要数据库 | `pytest -m database` |
| `@pytest.mark.api` | API测试 | `pytest -m api` |

## Fixtures 使用

### 基础 Fixtures

```python
# sample_fund_code - 示例基金代码
# sample_historical_data - 示例历史数据
# mock_db_manager - 模拟数据库管理器
# mock_cache_manager - 模拟缓存管理器
# client - Flask 测试客户端

def test_get_fund_detail(client, sample_fund_code):
    response = client.get(f'/api/fund/{sample_fund_code}')
    assert response.status_code == 200
```

### 自定义 Fixtures

在 `conftest.py` 中添加项目级 fixtures，或在测试文件中添加模块级 fixtures。

## 测试数据

测试数据存放在 `tests/fixtures/` 目录：

- `fund_data.json` - 基金基础数据
- `holdings.json` - 持仓数据
- `historical_nav.csv` - 历史净值数据

## 最佳实践

### 1. 测试命名

```python
# 良好的命名
def test_calculate_sharpe_ratio_with_normal_data():
    pass

def test_calculate_sharpe_ratio_returns_zero_for_insufficient_data():
    pass

# 避免的命名
def test_sharpe():
    pass
```

### 2. 测试结构 (Arrange-Act-Assert)

```python
def test_example():
    # Arrange - 准备数据
    calculator = PerformanceCalculator()
    returns = np.array([0.01, 0.02, -0.005])
    
    # Act - 执行操作
    result = calculator.calculate_sharpe_ratio(returns)
    
    # Assert - 验证结果
    assert result > 0
```

### 3. 使用 Mock

```python
from unittest.mock import Mock, patch

def test_with_mock():
    with patch('module.function') as mock_func:
        mock_func.return_value = 42
        
        result = function_under_test()
        
        assert result == 42
        mock_func.assert_called_once()
```

### 4. 参数化测试

```python
import pytest

@pytest.mark.parametrize("fund_code,expected_type", [
    ("000001", "混合型"),
    ("000002", "股票型"),
    ("016667", "QDII"),
])
def test_fund_type_classification(fund_code, expected_type):
    result = classify_fund(fund_code)
    assert result == expected_type
```

## 持续集成

在 `.github/workflows/test.yml` 中配置自动化测试：

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
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
      - name: Run tests
        run: pytest tests/unit -v --cov=. --cov-report=xml
```

## 故障排除

### 问题：模块导入错误

```bash
# 确保项目根目录在 Python 路径中
export PYTHONPATH="${PYTHONPATH}:/path/to/pro2"
```

### 问题：数据库连接失败

```bash
# 检查数据库配置
# 或跳过数据库测试
pytest -m "not database"
```

### 问题：Locust 无法连接

```bash
# 确保应用已启动
# 检查 host 和端口
locust --host=http://localhost:5001
```

## 贡献指南

1. 为新功能添加对应的单元测试
2. 修复 bug 时添加回归测试
3. 保持测试代码简单明了
4. 使用 fixtures 减少重复代码
5. 及时更新测试文档

## 参考

- [Pytest 官方文档](https://docs.pytest.org/)
- [Locust 官方文档](https://docs.locust.io/)
- [Flask 测试文档](https://flask.palletsprojects.com/en/2.0.x/testing/)
