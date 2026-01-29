# Gitee CI/CD 配置指南

## 配置文件

项目使用 `.gitee-ci.yml` 文件配置 Gitee 流水线。

## 流水线阶段

### 1. Test 阶段

#### unit_test 任务
- **镜像**: python:3.10-slim
- **功能**: 运行单元测试
- **特点**: 
  - 跳过数据库相关测试（使用 `-k "not database"`）
  - 生成测试报告和覆盖率报告
  - 使用 SQLite 避免 MySQL 依赖

#### api_test 任务
- **镜像**: python:3.10-slim
- **功能**: 运行 API 集成测试
- **测试范围**: `tests/integration/test_api.py`

#### lint 任务
- **镜像**: python:3.10-slim
- **功能**: 代码风格检查
- **工具**: flake8, pylint
- **特性**: `allow_failure: true`（允许失败，不阻塞流水线）

### 2. Build 阶段

#### build 任务
- **镜像**: python:3.10-slim
- **功能**: 构建应用
- **触发条件**: 仅在 master 和 develop 分支

## 常见问题及解决方案

### 问题1: 依赖安装失败

**症状**: pip 安装依赖时超时或失败

**解决方案**:
1. 使用国内镜像源
2. 减少重型依赖（如 paddlepaddle, torch）
3. 分阶段安装依赖

### 问题2: 数据库连接失败

**症状**: 数据库测试无法连接到 MySQL

**解决方案**:
1. 单元测试跳过数据库测试（使用 `-k "not database"`）
2. 使用 SQLite 替代 MySQL 进行单元测试
3. API 测试使用 Flask 测试客户端，不依赖真实数据库

### 问题3: 内存不足

**症状**: 构建过程中内存溢出

**解决方案**:
1. 移除重型依赖（paddlepaddle, torch, easyocr）
2. 使用轻量级基础镜像
3. 分步骤安装依赖

### 问题4: 测试超时

**症状**: 测试运行时间过长导致超时

**解决方案**:
1. 减少测试数据量
2. 跳过耗时较长的测试
3. 优化测试用例

## 本地测试 Gitee CI 配置

### 使用 Docker 模拟环境

```bash
# 拉取 Gitee CI 使用的镜像
docker pull python:3.10-slim

# 运行容器
docker run -it --rm -v $(pwd):/app -w /app python:3.10-slim bash

# 在容器中执行 CI 步骤
apt-get update && apt-get install -y gcc pkg-config
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install pandas requests PyYAML sqlalchemy flask flask-cors matplotlib seaborn numpy scikit-learn xgboost
pip install pytest pytest-cov pytest-html pytest-mock
pytest tests/unit -v -k "not database"
```

## 优化建议

### 1. 缓存优化
- 使用 `cache` 配置缓存 pip 包
- 缓存虚拟环境

### 2. 并行化
- 单元测试和 API 测试可以并行运行
- 使用 `parallel` 配置

### 3. 条件执行
- 只在特定分支运行部署任务
- 使用 `only` 和 `except` 控制任务执行

### 4. 制品管理
- 配置 `artifacts` 保存测试报告
- 设置合理的过期时间

## 调试技巧

### 查看日志
在 Gitee 仓库页面：
1. 进入"流水线"菜单
2. 点击失败的构建
3. 查看详细的日志输出

### 本地复现
1. 使用相同的 Docker 镜像
2. 按照 CI 配置的顺序执行命令
3. 检查环境变量和依赖

### 常见错误排查

| 错误 | 可能原因 | 解决方案 |
|------|----------|----------|
| ModuleNotFoundError | 依赖未安装 | 检查 requirements.txt |
| Connection refused | 服务未启动 | 检查 services 配置 |
| Timeout | 网络或性能问题 | 增加超时时间或优化代码 |
| Memory error | 内存不足 | 减少依赖或使用更大内存的 runner |

## 联系支持

如遇到无法解决的问题：
1. 查看 Gitee 官方文档: https://gitee.com/help/articles/4113
2. 检查 Gitee 状态页面
3. 联系 Gitee 技术支持
