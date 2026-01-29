# 基金分析系统 - Makefile
# 提供便捷的命令来运行测试、构建和部署

.PHONY: help install test test-unit test-integration test-api test-db coverage build deploy clean lint format

# 默认目标
help:
	@echo "基金分析系统 - 可用命令"
	@echo "========================"
	@echo "  make install          - 安装依赖"
	@echo "  make test             - 运行所有测试"
	@echo "  make test-unit        - 运行单元测试"
	@echo "  make test-integration - 运行集成测试"
	@echo "  make test-api         - 运行API测试"
	@echo "  make test-db          - 运行数据库测试"
	@echo "  make coverage         - 生成覆盖率报告"
	@echo "  make build            - 构建项目"
	@echo "  make deploy           - 部署项目"
	@echo "  make deploy-local     - 本地部署"
	@echo "  make lint             - 代码检查"
	@echo "  make format           - 代码格式化"
	@echo "  make clean            - 清理临时文件"
	@echo "  make ci               - 运行完整CI流程"

# 安装依赖
install:
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-html pytest-mock

# 运行所有测试
test:
	pytest tests/ -v --html=tests/reports/test_report.html --self-contained-html

# 运行单元测试
test-unit:
	pytest tests/unit -v --html=tests/reports/unit_test_report.html --self-contained-html

# 运行集成测试
test-integration:
	pytest tests/integration -v --html=tests/reports/integration_test_report.html --self-contained-html

# 运行API测试
test-api:
	pytest tests/integration/test_api.py -v -m api

# 运行数据库测试
test-db:
	pytest tests/integration/test_database.py -v -m database

# 生成覆盖率报告
coverage:
	pytest tests/ -v --cov=fund_search --cov-report=html:tests/reports/coverage --cov-report=xml --cov-report=term-missing --html=tests/reports/test_report.html --self-contained-html

# 代码检查
lint:
	flake8 fund_search --max-line-length=120 --exclude=.venv,venv,__pycache__,build,dist
	pylint fund_search --disable=C,R --ignore=.venv,venv,__pycache__,build,dist

# 代码格式化
format:
	black fund_search --line-length=120 --exclude='/(\.venv|venv|__pycache__|build|dist)/'
	isort fund_search --profile black --skip .venv --skip venv

# 构建项目
build:
	python -m build

# 部署到生产环境
deploy:
	powershell -ExecutionPolicy Bypass -File ci-cd/deploy.ps1 -Environment production

# 本地部署
deploy-local:
	powershell -ExecutionPolicy Bypass -File ci-cd/deploy.ps1 -Environment local

# 清理临时文件
clean:
	rm -rf build/ dist/ *.egg-info/
	rm -rf tests/reports/* tests/logs/*
	rm -rf htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# 运行完整CI流程
ci:
	powershell -ExecutionPolicy Bypass -File ci-cd/local-ci.ps1

# 快速CI (跳过集成测试)
ci-quick:
	powershell -ExecutionPolicy Bypass -File ci-cd/local-ci.ps1 -Quick

# 本地CI (带部署)
ci-deploy:
	powershell -ExecutionPolicy Bypass -File ci-cd/local-ci.ps1 -Deploy

# 生成文档
docs:
	@echo "生成项目文档..."
	python -m pydoc -w fund_search

# 启动开发服务器
serve:
	cd fund_search/web && python app.py

# 数据库迁移
migrate:
	@echo "执行数据库迁移..."
	python fund_search/data_retrieval/enhanced_database.py

# 备份数据库
backup:
	@echo "备份数据库..."
	mysqldump -u root -p fund_analysis > backup_$(shell date +%Y%m%d_%H%M%S).sql
