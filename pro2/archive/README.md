# 归档文件说明

> 归档时间: 2026-02-23

## 说明

此目录包含从项目中移除的文件。这些文件被归档以便在需要时恢复。

## 归档内容

### 1. Repository 层 (repositories/)
完整的数据访问 Repository 模式实现，包括：
- `base.py` - Repository 基类
- `fund_repository.py` - 基金数据 Repository
- `holdings_repository.py` - 持仓数据 Repository
- `analysis_repository.py` - 分析数据 Repository
- `__init__.py` - 模块导出

**移除原因:** 当前项目直接使用 `enhanced_database.py` 进行数据库操作，Repository 层未被使用。

**恢复方法:**
```bash
cp -r repositories/ ../fund_search/data_access/
# 然后更新 data_access/__init__.py 恢复导出
```

### 2. 业务服务 (fund_business_service.py)
基于 Repository 层的高级业务服务。

**移除原因:** 依赖 Repository 层，当前未使用。

### 3. 其他服务
- `fast_fund_service.py` - 快速基金数据服务
- `parallel_fetcher.py` - 并行数据获取器
- `cache/base.py` - 缓存基类
- `cache_warmup.py` - 缓存预热服务

**移除原因:** 这些服务当前未被任何代码引用。

## 清理前文件总数
- Python 文件: ~170 个

## 清理后文件总数
- Python 文件: ~163 个
- 归档文件: 10 个
- 直接删除: 6 个（备份文件、空 __init__.py）

## 如需恢复

1. 复制所需文件回原位置
2. 更新相关 `__init__.py` 恢复模块导出
3. 检查并安装可能缺失的依赖

## 注意事项

归档文件保留 3 个月，如无问题可彻底删除。
