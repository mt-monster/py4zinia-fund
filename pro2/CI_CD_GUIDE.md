# 基金分析系统 - CI/CD 使用指南

本文档介绍如何使用项目中的持续集成和持续部署(CI/CD)功能。

## 📋 目录

- [快速开始](#快速开始)
- [本地CI/CD](#本地cicd)
- [GitHub Actions](#github-actions)
- [测试框架](#测试框架)
- [部署流程](#部署流程)
- [故障排除](#故障排除)

## 🚀 快速开始

### 环境要求

- Python 3.10+
- PowerShell 5.1+ (Windows) 或 Bash (Linux/Mac)
- MySQL 8.0 (用于集成测试)
- Git

### 安装测试依赖

```powershell
# 安装项目依赖
pip install -r requirements.txt

# 安装测试工具
pip install pytest pytest-cov pytest-html pytest-mock
```

## 🖥️ 本地CI/CD

### 方式1: 使用 PowerShell 脚本

```powershell
# 运行完整的CI/CD流程
.\ci-cd\local-ci.ps1

# 快速模式（只运行单元测试）
.\ci-cd\local-ci.ps1 -Quick

# 跳过测试直接构建
.\ci-cd\local-ci.ps1 -SkipTests

# 测试通过后自动部署
.\ci-cd\local-ci.ps1 -Deploy
```

### 方式2: 使用 Makefile

```bash
# 查看所有可用命令
make help

# 运行所有测试
make test

# 运行单元测试
make test-unit

# 运行集成测试
make test-integration

# 生成覆盖率报告
make coverage

# 构建项目
make build

# 本地部署
make deploy-local

# 运行完整CI流程
make ci
```

### 方式3: 直接运行测试

```powershell
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/unit -v

# 运行集成测试
pytest tests/integration -v

# 生成HTML报告
pytest tests/ -v --html=tests/reports/report.html --self-contained-html

# 生成覆盖率报告
pytest tests/ --cov=fund_search --cov-report=html --cov-report=term
```

## 🔄 GitHub Actions

### 自动触发条件

- **Push到master分支**: 运行完整CI/CD并部署到生产环境
- **Push到develop分支**: 运行CI并部署到测试环境
- **Pull Request**: 运行测试和代码检查

### 工作流文件

配置位于 `.github/workflows/ci.yml`

### 查看执行结果

1. 访问 GitHub 仓库
2. 点击 "Actions" 标签
3. 查看工作流执行历史和日志

## 🧪 测试框架

### 测试目录结构

```
tests/
├── __init__.py              # 测试包初始化
├── conftest.py              # Pytest配置和固件
├── unit/                    # 单元测试
│   ├── __init__.py
│   ├── test_data_retrieval.py
│   └── test_backtesting.py
├── integration/             # 集成测试
│   ├── __init__.py
│   ├── test_api.py
│   └── test_database.py
├── utils/                   # 测试工具
│   └── report_generator.py
├── reports/                 # 测试报告
└── logs/                    # 测试日志
```

### 测试标记

使用标记来分类测试：

```python
import pytest

@pytest.mark.unit
def test_something():
    pass

@pytest.mark.integration
@pytest.mark.api
def test_api_endpoint():
    pass

@pytest.mark.database
@pytest.mark.slow
def test_database_operation():
    pass
```

### 运行特定标记的测试

```powershell
# 只运行单元测试
pytest -m unit

# 只运行API测试
pytest -m api

# 排除慢速测试
pytest -m "not slow"

# 运行多个标记
pytest -m "unit or api"
```

### 测试固件

在 `conftest.py` 中定义共享固件：

```python
import pytest

@pytest.fixture
def mock_fund_data():
    return {
        'fund_code': '000001',
        'fund_name': '测试基金'
    }

@pytest.fixture(scope='session')
def db_manager():
    # 创建数据库连接
    manager = EnhancedDatabaseManager(...)
    yield manager
    # 清理
    manager.cleanup()
```

## 📊 测试报告

### 报告位置

- **HTML报告**: `tests/reports/test_report_YYYYMMDD_HHMMSS.html`
- **覆盖率报告**: `tests/reports/coverage_YYYYMMDD/index.html`
- **JSON摘要**: `tests/reports/test_summary_YYYYMMDD_HHMMSS.json`
- **日志文件**: `tests/logs/pytest.log`

### 查看报告

```powershell
# 打开HTML报告
start tests/reports/test_report_*.html

# 打开覆盖率报告
start tests/reports/coverage_*/index.html
```

## 🚀 部署流程

### 本地部署

```powershell
# 使用部署脚本
.\ci-cd\deploy.ps1 -Environment local

# 或使用Makefile
make deploy-local
```

### 测试环境部署

```powershell
.\ci-cd\deploy.ps1 -Environment staging -Backup
```

### 生产环境部署

```powershell
.\ci-cd\deploy.ps1 -Environment production -Backup
```

### 部署配置

部署配置位于脚本开头的 `$DeployConfig` 变量中，可根据需要修改：

```powershell
$DeployConfig = @{
    local = @{
        TargetDir = "D:\\deploy\\local"
        AppPort = 5000
        DbName = "fund_local"
    }
    staging = @{
        TargetDir = "\\\\staging-server\\fund-analysis"
        AppPort = 5000
        DbName = "fund_staging"
    }
    production = @{
        TargetDir = "\\\\prod-server\\fund-analysis"
        AppPort = 80
        DbName = "fund_production"
    }
}
```

## 🔧 故障排除

### 常见问题

#### 1. 测试失败：找不到模块

**问题**: `ModuleNotFoundError: No module named 'fund_search'`

**解决**:
```powershell
# 确保在项目根目录运行
# 添加项目路径到PYTHONPATH
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
```

#### 2. 数据库连接失败

**问题**: 集成测试无法连接数据库

**解决**:
```powershell
# 设置数据库环境变量
$env:DB_HOST = "localhost"
$env:DB_PORT = "3306"
$env:DB_USER = "root"
$env:DB_PASSWORD = "your_password"
$env:TEST_DB_NAME = "fund_test_db"
```

#### 3. PowerShell 执行策略

**问题**: `无法加载文件，因为在此系统上禁止运行脚本`

**解决**:
```powershell
# 以管理员身份运行
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 或临时绕过
powershell -ExecutionPolicy Bypass -File ci-cd\local-ci.ps1
```

#### 4. 虚拟环境激活失败

**问题**: 无法激活虚拟环境

**解决**:
```powershell
# 手动激活
.\.venv\Scripts\Activate.ps1

# 或创建新的虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 调试模式

```powershell
# 启用详细输出
pytest -v --tb=long

# 在第一个失败处停止
pytest -x

# 只运行失败的测试
pytest --lf

# 调试特定测试
pytest tests/unit/test_data_retrieval.py::TestFundDataParser::test_parse_fund_code_valid -v
```

### 日志查看

```powershell
# 查看测试日志
type tests\logs\pytest.log

# 查看CI/CD日志
type tests\logs\ci-cd-*.log
```

## 📈 性能优化

### 并行测试

```powershell
# 安装并行测试插件
pip install pytest-xdist

# 并行运行测试
pytest -n auto

# 指定进程数
pytest -n 4
```

### 测试缓存

```powershell
# 使用缓存加速
pytest --cache-clear  # 清除缓存
pytest --lf           # 只运行上次失败的测试
pytest --ff           # 先运行上次失败的测试
```

## 📝 最佳实践

1. **编写测试**: 每个功能都要有对应的单元测试
2. **命名规范**: 测试函数名要清晰描述测试内容
3. **独立性**: 测试之间不要相互依赖
4. **快速执行**: 单元测试应该快速完成
5. **持续集成**: 每次提交前都要运行测试
6. **代码覆盖**: 保持较高的代码覆盖率（建议>80%）

## 🔗 相关链接

- [Pytest文档](https://docs.pytest.org/)
- [GitHub Actions文档](https://docs.github.com/cn/actions)
- [项目README](./README.md)

## 📞 支持

如有问题，请：
1. 查看本指南的故障排除部分
2. 查看测试日志文件
3. 在GitHub Issues中提交问题
