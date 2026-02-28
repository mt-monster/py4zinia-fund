# 统一配置管理系统

## 概述

本项目已将分散在多个目录的配置文件整合为统一的配置管理系统，解决了配置分散在 `shared/`、`backtesting/`、`data_retrieval/`、`services/` 等多个目录的问题。

## 新架构

```
fund_search/config/
├── __init__.py           # 统一入口和向后兼容
├── base.py               # 基础配置类和工具
├── settings.py           # 配置数据类和管理器
├── database.yaml         # 数据库配置
├── cache.yaml            # 缓存配置
├── notification.yaml     # 通知配置
├── datasource.yaml       # 数据源配置
├── strategy.yaml         # 策略配置
├── celery.yaml           # Celery配置
├── ocr.yaml              # OCR配置
├── web.yaml              # Web应用配置
├── system.yaml           # 系统配置
├── logging.yaml          # 日志配置
├── MIGRATION_GUIDE.md    # 迁移指南
├── example_usage.py      # 使用示例
└── test_config.py        # 测试脚本
```

## 核心特性

### 1. 集中管理
所有配置统一在 `config/` 目录，易于查找和维护。

### 2. 环境覆盖
支持通过环境变量覆盖任何配置，格式为 `FUND_<SECTION>_<KEY>`。

### 3. 类型安全
使用 Python dataclass 定义配置结构，提供类型检查和自动补全。

### 4. 配置验证
自动验证配置有效性，在启动时发现配置错误。

### 5. 向后兼容
原有代码无需修改，旧导入语句继续有效。

## 快速开始

### 方式1: 使用统一入口（推荐）

```python
from fund_search.config import settings

# 访问配置
db_host = settings.database.host
cache_ttl = settings.cache.default_ttl
strategy_multiplier = settings.strategy.buy_multipliers['buy']

# 支持嵌套路径访问
warning_threshold = settings.get('strategy.stop_loss.warning_threshold')
```

### 方式2: 使用便捷函数

```python
from fund_search.config import get_db_config, get_strategy_config

db_config = get_db_config()
strategy_config = get_strategy_config()
```

### 方式3: 向后兼容

```python
# 原有代码无需修改
from fund_search.config import DATABASE_CONFIG, CACHE_CONFIG
```

## 环境变量

所有配置都支持通过环境变量覆盖：

```bash
# 数据库配置
export FUND_DB_HOST=localhost
export FUND_DB_PORT=3306
export FUND_DB_PASSWORD=your_password

# 数据源配置
export TUSHARE_TOKEN=your_token

# Web配置
export FUND_WEB_PORT=5001
```

## 配置优先级

1. **环境变量** - 最高优先级
2. **配置文件** - YAML 文件中的值
3. **默认值** - 代码中定义的默认值

## 运行测试

```bash
cd pro2/fund_search
python config/test_config.py
```

## 运行示例

```bash
cd pro2/fund_search
python config/example_usage.py
```

## 迁移旧配置

详见 [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)

## 目录对比

### 改进前

```
配置分散在多个目录：
- shared/config.py              # 基础配置
- shared/enhanced_config.py     # 增强配置
- shared/config_manager.py      # 配置管理器
- shared/fund_data_config.py    # 数据配置
- backtesting/core/strategy_config.py  # 策略配置
- data_retrieval/utils/ocr_config.py   # OCR配置
- services/celery_config.py     # Celery配置
```

### 改进后

```
配置统一在config目录：
- config/
  ├── __init__.py       # 统一入口
  ├── base.py           # 基础工具
  ├── settings.py       # 配置管理器
  └── *.yaml            # 各模块配置
```

## 优势总结

| 方面 | 改进前 | 改进后 |
|------|--------|--------|
| 配置位置 | 分散在6+个目录 | 集中在1个目录 |
| 配置格式 | Python字典/类混合 | YAML + dataclass |
| 环境覆盖 | 部分支持 | 全面支持 |
| 配置验证 | 无 | 自动验证 |
| 类型安全 | 无 | 完整类型提示 |
| 向后兼容 | N/A | 完全兼容 |

## 许可证

与项目主许可证一致。
