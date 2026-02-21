# 基金数据同步 - 快速开始

## 🎯 目标

预先从akshare获取基金历史数据并存入数据库，让相关性分析从30秒缩短到2秒。

## 📋 前置条件

- Python环境已配置
- 数据库连接正常
- 用户持仓表有数据

## 🚀 三步搞定

### 第一步：打开命令行

```bash
cd pro2/fund_search
```

### 第二步：执行数据同步

```bash
# 同步所有持仓基金（推荐）
python sync_fund_nav_data.py --sync-holdings
```

**预期输出**：
```
开始同步 14 只基金的历史数据
...
同步完成！总耗时: 28.5 秒
  - 成功: 14
  - 插入记录: 3500
```

### 第三步：测试相关性分析

1. 打开前端页面
2. 选择基金点击"相关性分析"
3. 观察加载速度（应该<2秒）

## 🔄 设置自动同步（可选）

### Windows用户

双击运行 `setup_windows_task.ps1`（以管理员身份）

或手动创建定时任务：
1. 打开"任务计划程序"
2. 创建基本任务 → 名称：`FundSync`
3. 触发器：每天 16:30
4. 操作：启动程序
   - 程序：`python`
   - 参数：`sync_fund_nav_data.py --sync-holdings`
   - 起始于：`pro2/fund_search`

### 手动运行批处理

```bash
# Windows
RUN_SYNC.bat holdings
```

## 📊 效果对比

| 指标 | 同步前 | 同步后 |
|-----|-------|-------|
| 首次分析 | 30-60秒 | 30-60秒 |
| 后续分析 | 30-60秒 | **<2秒** |
| 数据来源 | akshare实时 | 数据库缓存 |

## 🐛 故障排除

### 问题1：同步失败

```bash
# 检查akshare连接
python -c "import akshare as ak; print(ak.fund_open_fund_info_em('000001', '单位净值走势').head())"

# 检查数据库
python -c "from data_retrieval.enhanced_database import EnhancedDatabaseManager; from shared.enhanced_config import DATABASE_CONFIG; db = EnhancedDatabaseManager(DATABASE_CONFIG); print('OK')"
```

### 问题2：同步后仍然慢

检查日志确认从数据库读取：
```bash
# 查看后端日志
python app.py 2>&1 | grep "API Performance"
```

应该看到：
```
[API Performance] 步骤3-akshare获取数据: 0 ms  <-- 应该是0或很小
```

## 📁 文件说明

| 文件 | 用途 |
|-----|------|
| `sync_fund_nav_data.py` | 数据同步脚本 |
| `setup_windows_task.ps1` | Windows定时任务配置 |
| `RUN_SYNC.bat` | Windows批处理快捷方式 |
| `FUND_NAV_SYNC_GUIDE.md` | 详细文档 |

## ✅ 验证成功

数据同步成功后：
1. 日志显示 `成功: 14`（或你的基金数量）
2. 相关性分析页面秒开
3. 后端日志显示 `步骤3-akshare获取数据: 0 ms`

---

**提示**：只需执行一次全量同步，之后每日自动增量更新即可。
