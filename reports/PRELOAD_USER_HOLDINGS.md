# 用户持仓基金预加载指南

## 概述

预加载系统现在只加载**用户持仓中的基金**，而不是市场上全部基金。这样可以：
- 大幅减少预加载时间和内存占用
- 更加个性化，只关注用户关心的基金
- 启动速度更快（持仓10只基金只需几秒钟）

## 预加载逻辑

```
1. 首先尝试从数据库获取用户持仓基金
   ├── 查询 holdings 表
   └── 查询 user_holdings 表

2. 如果数据库没有，尝试从本地文件读取
   └── user_holdings.json

3. 如果都没有持仓基金
   └── 跳过预加载（不加载其他基金）
```

## 使用方法

### 方式1：自动获取持仓基金（推荐）

```bash
# 系统会自动从数据库获取用户的持仓基金进行预加载
python startup.py
```

输出示例：
```
从数据库获取到 5 只用户持仓基金
将预加载用户持仓的 5 只基金
...
预加载完成！共 5 只基金，耗时 8.5 秒
```

### 方式2：指定基金预加载

```bash
# 手动指定要预加载的基金
python startup.py --fund-codes 000001,000002,021539
```

### 方式3：跳过预加载

```bash
# 如果暂时没有持仓，可以跳过预加载
python startup.py --skip-preload
```

## 数据库表结构

确保 holdings 表或 user_holdings 表存在：

```sql
-- holdings 表
CREATE TABLE IF NOT EXISTS holdings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) DEFAULT 'default_user',
    fund_code VARCHAR(20) NOT NULL,
    fund_name VARCHAR(100),
    shares DECIMAL(20, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_fund (user_id, fund_code)
);

-- 或 user_holdings 表
CREATE TABLE IF NOT EXISTS user_holdings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) DEFAULT 'default_user',
    fund_code VARCHAR(20) NOT NULL,
    fund_name VARCHAR(100),
    amount DECIMAL(20, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_fund (user_id, fund_code)
);
```

## 本地文件方式

如果没有数据库，可以使用本地 JSON 文件：

```bash
# 创建 user_holdings.json
cat > user_holdings.json << 'EOF'
[
    {"fund_code": "000001", "fund_name": "华夏成长混合"},
    {"fund_code": "000002", "fund_name": "华夏大盘精选"},
    {"fund_code": "021539", "fund_name": "华安法国CAC40"}
]
EOF

# 启动系统
python startup.py
```

## 性能参考

| 持仓数量 | 预加载时间 | 内存占用 |
|---------|-----------|---------|
| 5只 | ~5秒 | ~20MB |
| 10只 | ~10秒 | ~40MB |
| 20只 | ~20秒 | ~80MB |
| 50只 | ~60秒 | ~200MB |

## 代码示例

### 在代码中使用

```python
from services.fund_data_preloader import FundDataPreloader

preloader = FundDataPreloader()

# 预加载（自动获取用户持仓）
preloader.preload_all()

# 查看预加载状态
status = preloader.get_preload_status()
print(f"预加载完成: {status['completed']}")
print(f"基金数量: {len(preloader._get_user_holdings_fund_codes())}")
```

### 查询持仓基金数据

```python
from services.fast_fund_service import get_fast_fund_service

service = get_fast_fund_service()

# 获取用户持仓基金代码
from services.fund_data_preloader import get_preloader
preloader = get_preloader()
holding_codes = preloader._get_user_holdings_fund_codes()

# 批量查询（极速）
for code in holding_codes:
    data = service.get_fund_complete_data(code)
    print(f"{data.fund_code}: {data.fund_name}, NAV: {data.latest_nav}")
```

## 故障排查

### 问题1：预加载显示 "用户暂无持仓基金"

**原因**：数据库中没有持仓数据

**解决**：
```sql
-- 添加持仓数据
INSERT INTO holdings (fund_code, fund_name) VALUES
('000001', '华夏成长混合'),
('000002', '华夏大盘精选');
```

### 问题2：数据库连接失败

**原因**：数据库配置不正确

**解决**：
```python
# 检查配置文件
from shared.config_manager import config_manager
db_config = config_manager.get_database_config()
print(db_config.host, db_config.database)
```

### 问题3：想预加载更多基金

**解决**：
```bash
# 手动指定基金
python startup.py --fund-codes 000001,000002,000003,000004,000005
```

## 总结

- 预加载系统现在**只关注用户持仓基金**
- 自动从数据库或本地文件获取持仓列表
- 如无持仓，跳过预加载（不浪费资源）
- 可以通过 `--fund-codes` 手动指定要预加载的基金
