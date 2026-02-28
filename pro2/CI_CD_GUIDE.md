# 基金分析系统 - CI/CD 操作指南

本文档详细介绍基金分析系统的本地 CI/CD 流程和操作方法。

## 目录

- [快速开始](#快速开始)
- [目录结构](#目录结构)
- [环境配置](#环境配置)
- [Make 命令参考](#make-命令参考)
- [Git Hooks 配置](#git-hooks-配置)
- [CI/CD 脚本说明](#cicd-脚本说明)
- [常见问题](#常见问题)

---

## 快速开始

```bash
# 1. 进入项目目录
cd pro2

# 2. 安装依赖
make install

# 3. 运行完整 CI
make ci

# 4. 提交代码（自动触发 pre-commit 检查）
git add .
git commit -m "feat: 添加新功能"
```

---

## 目录结构

```
pro2/
├── .github/workflows/          # GitHub Actions CI 配置
├── ci-cd/                     # 本地 CI/CD 脚本
│   ├── local-ci.ps1          # 主 CI 流程脚本
│   ├── run-tests.ps1         # 测试运行脚本
│   └── deploy.ps1            # 部署脚本
├── .git/hooks/                # Git Hooks
│   └── pre-commit            # 提交前检查钩子
├── tests/                     # 测试目录
│   ├── unit/                 # 单元测试
│   ├── integration/          # 集成测试
│   ├── performance/         # 性能测试
│   └── reports/             # 测试报告
├── Makefile                  # Make 命令入口
├── pyproject.toml           # 项目配置
├── pytest.ini               # pytest 配置
├── .flake8                  # flake8 配置
└── .pre-commit-config.yaml  # pre-commit 配置
```

---

## 环境配置

### 安装 Python 依赖

```bash
# 使用 Make
make install

# 或手动安装
pip install -r requirements.txt
pip install pytest pytest-cov pytest-html pytest-mock
pip install black isort flake8 mypy pylint
pip install pre-commit
```

### 安装 Pre-commit Hooks

```bash
# 方式 1: 使用 Make
make pre-commit

# 方式 2: 手动安装
pre-commit install
```

---

## Make 命令参考

### 开发环境

| 命令 | 说明 |
|------|------|
| `make help` | 显示所有可用命令 |
| `make install` | 安装项目依赖 |

### 测试

| 命令 | 说明 |
|------|------|
| `make test` | 运行所有测试 |
| `make test-unit` | 运行单元测试 |
| `make test-integration` | 运行集成测试 |
| `make test-api` | 运行 API 测试 |
| `make test-db` | 运行数据库测试 |
| `make coverage` | 生成覆盖率报告 |

### 代码质量

| 命令 | 说明 |
|------|------|
| `make lint` | 运行 flake8 和 pylint 检查 |
| `make format` | 运行 black 和 isort 格式化 |
| `make type-check` | 运行 mypy 类型检查 |
| `make pre-commit` | 安装并运行 pre-commit 检查 |

### 构建与部署

| 命令 | 说明 |
|------|------|
| `make build` | 构建 Python 包 |
| `make deploy` | 部署到生产环境 |
| `make deploy-local` | 本地部署 |

### CI/CD

| 命令 | 说明 |
|------|------|
| `make ci` | 运行完整 CI 流程 |
| `make ci-quick` | 快速 CI（跳过集成测试） |
| `make ci-deploy` | CI + 本地部署 |

### 清理

| 命令 | 说明 |
|------|------|
| `make clean` | 清理临时文件和缓存 |

---

## Git Hooks 配置

### Pre-commit Hook

提交前自动运行以下检查：

1. **flake8** - 代码语法和风格检查
2. **black** - 代码格式化检查
3. **isort** - import 排序检查
4. **pytest** - 单元测试

### 手动运行 Pre-commit

```bash
# 运行所有文件的检查
pre-commit run --all-files

# 运行特定文件的检查
pre-commit run --files fund_search/example.py

# 跳过 pre-commit 检查（不推荐）
git commit --no-verify -m "commit message"
```

### 更新 Pre-commit 配置

```bash
# 更新 hook 版本
pre-commit autoupdate
```

---

## CI/CD 脚本说明

### PowerShell 脚本

```powershell
# 运行完整 CI
powershell -ExecutionPolicy Bypass -File ci-cd/local-ci.ps1

# 快速 CI（跳过集成测试）
powershell -ExecutionPolicy Bypass -File ci-cd/local-ci.ps1 -Quick

# CI + 部署
powershell -ExecutionPolicy Bypass -File ci-cd/local-ci.ps1 -Deploy

# 运行测试
powershell -ExecutionPolicy Bypass -File ci-cd/run-tests.ps1

# 部署
powershell -ExecutionPolicy Bypass -File ci-cd/deploy.ps1 -Environment production
powershell -ExecutionPolicy Bypass -File ci-cd/deploy.ps1 -Environment local
```

---

## 常见问题

### Q: 如何跳过 pre-commit 检查？

```bash
git commit --no-verify -m "快速提交"
```

### Q: 如何只运行部分检查？

```bash
# 只运行 flake8
flake8 fund_search --max-line-length=120

# 只运行 black
black fund_search --check

# 只运行单元测试
pytest tests/unit -v
```

### Q: 覆盖率报告在哪里？

覆盖率报告生成在以下位置：
- HTML 报告: `tests/reports/coverage/index.html`
- XML 报告: `coverage.xml`

### Q: 如何配置 CI 工具？

#### Black
编辑 `pyproject.toml`:
```toml
[tool.black]
line-length = 120
target-version = ["py310"]
```

#### Flake8
编辑 `.flake8`:
```ini
[flake8]
max-line-length = 120
exclude = .git,__pycache__,venv
```

#### MyPy
编辑 `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
```

---

## 工作流程示例

### 开发流程

```bash
# 1. 创建分支
git checkout -b feature/new-feature

# 2. 开发代码...

# 3. 运行格式化
make format

# 4. 运行代码检查
make lint
make type-check

# 5. 运行测试
make test
make coverage

# 6. 提交（自动触发 pre-commit）
git add .
git commit -m "feat: 添加新功能"

# 7. 推送
git push origin feature/new-feature
```

### 修复 Bug 流程

```bash
# 1. 创建分支
git checkout -b fix/bug-description

# 2. 编写测试复现问题
# 3. 修复代码
# 4. 运行测试确认修复
make test

# 5. 提交
git add .
git commit -m "fix: 修复 XXX 问题"

# 6. 推送并创建 PR
git push origin fix/bug-description
```

---

## 配置文件说明

| 文件 | 作用 |
|------|------|
| `Makefile` | 定义所有 Make 命令 |
| `pyproject.toml` | 项目元数据和工具配置 |
| `pytest.ini` | pytest 测试框架配置 |
| `.flake8` | flake8 代码检查配置 |
| `.pre-commit-config.yaml` | pre-commit hook 配置 |

---

## 持续集成

### GitHub Actions

项目已配置 GitHub Actions，push 到主分支自动运行 CI：

```yaml
# .github/workflows/ci.yml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run tests
        run: make ci
```

---

## 附录

### 依赖版本要求

- Python >= 3.10
- pytest >= 7.0.0
- black >= 23.0.0
- isort >= 5.12.0
- flake8 >= 6.0.0
- mypy >= 1.0.0
- pre-commit >= 3.0.0

### 相关链接

- [Black 文档](https://black.readthedocs.io/)
- [isort 文档](https://pycqa.github.io/isort/)
- [Flake8 文档](https://flake8.pycqa.org/)
- [MyPy 文档](https://mypy.readthedocs.io/)
- [Pre-commit 文档](https://pre-commit.com/)
- [Pytest 文档](https://docs.pytest.org/)

---

*本文档由 CI/CD 系统自动生成，最后更新于 2026-02-28*
