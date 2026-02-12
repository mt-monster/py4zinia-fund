# 基金数据预加载 - 快速开始

## 1分钟启动

```bash
# 进入项目目录
cd pro2/fund_search

# 启动系统（自动预加载所有数据）
python startup.py
```

等待看到以下输出即表示系统就绪：
```
============================================================
✓ 数据预加载完成！耗时: 85.2 秒
  缓存统计: {'size': 5000, 'hit_rate': '0.0%'}
============================================================
启动Web服务
============================================================
监听地址: 0.0.0.0:5000
```

## 快速验证

### 1. 检查预加载状态

```python
# 在另一个终端执行 Python
python

from services.fund_data_preloader import get_preloader
p = get_preloader()

# 查看状态
p.get_preload_status()
# {'started': True, 'completed': True, 'progress': 1.0}

# 查看缓存统计
p.get_cache_stats()
# {'size': 5000, 'max_size': 10000, 'hit_rate': '95.5%'}
```

### 2. 测试查询速度

```python
from services.fast_fund_service import get_fast_fund_service
import time

service = get_fast_fund_service()

# 测试单只基金（应该 < 10ms）
start = time.time()
data = service.get_fund_complete_data('000001')
elapsed = (time.time() - start) * 1000
print(f"查询耗时: {elapsed:.2f}ms")
# 输出: 查询耗时: 2.35ms

# 测试批量查询（100只应该 < 100ms）
codes = ['000001', '000002', ...]  # 100只基金
start = time.time()
batch = service.batch_get_fund_data(codes)
elapsed = (time.time() - start) * 1000
print(f"批量查询耗时: {elapsed:.2f}ms")
# 输出: 批量查询耗时: 45.23ms
```

## 常用命令

### 仅预加载数据（不启动Web）

```bash
python startup.py --preload-only
```

### 指定基金预加载

```bash
python startup.py --fund-codes 000001,000002,021539,100055
```

### 跳过预加载（使用现有缓存）

```bash
python startup.py --skip-preload
```

### 开发模式（调试）

```bash
python startup.py --debug --port 8080
```

## 在代码中使用

### 基础用法

```python
from services.fast_fund_service import get_fast_fund_service

# 获取服务实例
service = get_fast_fund_service()

# 查询单只基金（< 10ms）
data = service.get_fund_complete_data('000001')
print(data.fund_name)
print(data.latest_nav)
print(data.sharpe_ratio)

# 批量查询（< 100ms）
batch = service.batch_get_fund_data(['000001', '000002'])
```

### Flask路由中使用

```python
from flask import Flask, jsonify
from services.fast_fund_service import get_fast_fund_service

app = Flask(__name__)
service = get_fast_fund_service()

@app.route('/api/fund/<code>')
def get_fund(code):
    data = service.get_fund_complete_data(code)
    if data:
        return jsonify({
            'name': data.fund_name,
            'nav': data.latest_nav,
            'return': data.daily_return
        })
    return jsonify({'error': 'Not found'}), 404
```

## 性能对比

| 操作 | 传统方式 | 预加载方式 | 提升 |
|-----|---------|-----------|------|
| 打开基金页面 | 3-5秒 | < 0.1秒 | **50x** |
| 切换基金 | 1-2秒 | < 0.01秒 | **200x** |
| 批量分析100只 | 20-30秒 | < 0.1秒 | **300x** |

## 故障排查

### 预加载卡住

```bash
# 查看详细日志
tail -f startup.log

# 限制基金数量测试
python startup.py --fund-codes 000001,000002 --preload-only
```

### 内存不足

```python
# 减少预加载的基金数量
from services.fund_data_preloader import get_preloader, PreloadConfig

p = get_preloader()
p.config.max_cache_size = 5000  # 减少缓存大小
p.preload_all(fund_codes=['000001', '000002'])  # 只加载指定基金
```

### 缓存未命中

```python
# 强制重新预加载
from services.fund_data_preloader import get_preloader

p = get_preloader()
p.cache.clear()  # 清空缓存
p.preload_all()  # 重新加载
```

## 监控指标

```python
# 查看后台更新状态
from services.background_updater import get_background_updater

u = get_background_updater()
print(u.get_status())

# 查看速率限制状态
from data_retrieval.rate_limiter import get_tushare_limiter

l = get_tushare_limiter('fund_nav')
print(l.get_stats())
```

---

**开始使用**: `python startup.py`

**详细文档**: 查看 `PRELOAD_ARCHITECTURE.md`
