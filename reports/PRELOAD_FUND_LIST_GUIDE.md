# 基金列表获取与验证指南

## 概述

预加载系统会自动从市场获取**真实的场外开放式基金**列表，确保加载的是市场上实际存在的基金，而不是虚构的代码。

## 基金列表来源

### 数据来源

系统使用 **Akshare** 从以下渠道获取基金列表：

1. **fund_open_fund_daily_em** - 场外开放式基金每日行情（推荐）
2. **fund_name_em** - 基金名称列表（备用）

### 过滤规则

获取的基金会经过以下过滤：

1. **格式验证** - 只保留6位数字代码
2. **场内基金过滤** - 排除 ETF、LOF 等场内基金
   - 排除 `51xxxx`（上交所ETF）
   - 排除 `15xxxx`（深交所ETF）
   - 排除 `16xxxx`（LOF基金）
   - 排除 `50xxxx`（上交所其他）
   - 排除 `18xxxx`（深交所其他）

3. **去重** - 确保基金代码唯一

## 使用方法

### 1. 验证基金列表

```bash
cd pro2/fund_search

# 查看市场基金列表
python verify_fund_list.py

# 查看前100只基金
python verify_fund_list.py --limit 100

# 验证数据可获取性
python verify_fund_list.py --verify --verify-count 20

# 保存到文件
python verify_fund_list.py --output fund_list.csv
```

### 2. 预加载全部基金

```bash
# 预加载市场上全部场外基金（约10000+只）
python startup.py

# 可能需要几分钟时间
```

### 3. 限制预加载数量

```bash
# 只预加载前1000只基金
python startup.py --max-funds 1000

# 或预加载前500只
python startup.py --max-funds 500
```

### 4. 指定基金预加载

```bash
# 只预加载指定的基金
python startup.py --fund-codes 000001,000002,021539,100055
```

## 配置选项

### 在代码中配置

```python
from services.fund_data_preloader import get_preloader

preloader = get_preloader()

# 设置最大预加载数量
preloader.config.max_funds = 2000  # 只加载前2000只

# 预加载
preloader.preload_all()
```

### 环境变量配置

```bash
# 设置默认最大预加载数量
export FUND_PRELOAD_MAX_FUNDS=1000
```

## 基金数量参考

| 类型 | 数量 | 说明 |
|-----|------|------|
| 全部场外基金 | 约10000+只 | 市场上所有开放式基金 |
| 常见基金 | 约1000只 | 规模较大、流动性好的基金 |
| 热门基金 | 约100只 | 用户最常关注的基金 |

## 性能参考

| 预加载数量 | 预计时间 | 内存占用 |
|-----------|---------|---------|
| 100只 | ~10秒 | ~30MB |
| 1000只 | ~60秒 | ~200MB |
| 5000只 | ~5分钟 | ~1GB |
| 10000只 | ~10分钟 | ~2GB |

## 常见问题

### Q: 预加载的基金数量太多，内存不够怎么办？

**A:** 使用 `--max-funds` 参数限制数量：

```bash
# 只加载前500只
python startup.py --max-funds 500
```

或在代码中配置：

```python
preloader.config.max_funds = 500
```

### Q: 如何确保加载的是最新的基金列表？

**A:** 每次启动时系统都会重新从市场获取基金列表。后台更新服务也会定期更新。

### Q: 发现某些基金代码不存在怎么办？

**A:** 系统已经有过滤机制。如果仍发现无效代码，可以：

1. 运行验证脚本检查：
```bash
python verify_fund_list.py --verify
```

2. 手动指定有效的基金代码：
```bash
python startup.py --fund-codes 000001,000002,000003
```

### Q: 如何查看当前加载了多少只基金？

**A:** 

```python
from services.fund_data_preloader import get_preloader

preloader = get_preloader()
status = preloader.get_preload_status()
cache_stats = preloader.get_cache_stats()

print(f"预加载完成: {status['completed']}")
print(f"缓存大小: {cache_stats['size']}")
```

## 验证示例

### 查看基金列表分布

```bash
$ python verify_fund_list.py

============================================================
基金列表验证工具
============================================================
2024-01-01 12:00:00,000 - INFO - 正在从市场获取场外开放式基金列表...
2024-01-01 12:00:05,000 - INFO - ✓ 从 fund_open_fund_daily_em 获取到 10523 只场外基金

============================================================
基金列表分析
============================================================

总数量: 10523 只

按代码前缀分布:
  00xxxx: 5234 只
  01xxxx: 2341 只
  02xxxx: 1234 只
  16xxxx: 876 只
  50xxxx: 654 只

✓ 未发现明显的场内基金代码

前20只基金:
  1. 000001 - 华夏成长混合
  2. 000002 - 华夏大盘精选
  3. 000003 - 中海可转债A
  ...
```

### 验证数据可获取性

```bash
$ python verify_fund_list.py --verify --verify-count 10

数据可获取性验证（随机10只）
============================================================
  ✓ 000001 (华夏成长混合...): 2456 条数据
  ✓ 000002 (华夏大盘精选...): 2678 条数据
  ✓ 021539 (华安法国CAC40...): 123 条数据
  ...

验证结果: 10/10 只基金数据可获取
```

## 总结

- 系统自动从市场获取**真实的场外基金**列表
- 支持多种方式控制预加载数量
- 提供验证工具确保数据准确性
- 根据内存和性能需求灵活配置

---

**提示**: 对于生产环境，建议先运行 `verify_fund_list.py` 查看市场上的基金数量和分布，然后根据实际情况设置合适的 `--max-funds` 值。
