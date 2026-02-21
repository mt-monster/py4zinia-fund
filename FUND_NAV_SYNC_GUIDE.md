# 基金历史净值数据同步方案

## 方案概述

通过预先从akshare获取基金历史净值数据并存入数据库，使相关性分析无需等待实时网络请求，实现秒开体验。

## 文件说明

| 文件 | 说明 |
|-----|------|
| `sync_fund_nav_data.py` | 数据同步脚本（核心） |
| `setup_windows_task.ps1` | Windows定时任务配置脚本 |
| `sync_fund_nav.log` | 同步日志文件 |

## 快速开始

### 第一步：立即同步当前持仓基金数据

```bash
cd pro2/fund_search

# 同步用户持仓的所有基金
python sync_fund_nav_data.py --sync-holdings
```

运行后，脚本会：
1. 从 `user_holdings` 表获取所有持仓基金代码
2. 从akshare获取每只基金的历史净值（最近一年）
3. 将数据存入 `fund_analysis_results` 表

**预期耗时**：
- 14只基金 × 每只2秒 ≈ 30秒（一次性）
- 之后相关性分析将秒开（<1秒）

### 第二步：验证数据同步成功

```bash
python sync_fund_nav_data.py --sync-holdings
```

如果输出显示：
```
同步完成！
  - 成功: 14
  - 插入记录: 3000+
  - 更新记录: 0
```

说明数据已存入数据库。

### 第三步：测试相关性分析速度

1. 打开前端页面
2. 选择基金进行相关性分析
3. 观察页面加载速度（应该<2秒）

查看后端日志确认从数据库读取：
```
[API Performance] 步骤2-数据库获取数据: XX ms
[API Performance] 步骤3-akshare获取数据: 0 ms  <-- 应该是0或很小
```

## 定时自动同步（推荐）

### 方式1：Windows 定时任务

以管理员身份运行 PowerShell：

```powershell
cd pro2/fund_search
.\setup_windows_task.ps1
```

这将创建每日 16:30 自动执行的任务。

### 方式2：手动创建定时任务

1. 打开"任务计划程序"
2. 创建基本任务
3. 名称：`FundNavDataSync`
4. 触发器：每天 16:30
5. 操作：启动程序
   - 程序：`pro2/fund_search/sync_fund_nav_data.py`
   - 参数：`--sync-holdings`

### 方式3：Linux/Mac 定时任务 (crontab)

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每日16:30执行）
30 16 * * * cd /path/to/pro2/fund_search && /path/to/python sync_fund_nav_data.py --sync-holdings >> sync.log 2>&1
```

## 高级用法

### 同步指定基金

```bash
# 同步指定基金（逗号分隔）
python sync_fund_nav_data.py --codes 006614,017962,006718
```

### 全量更新（重新获取所有历史数据）

```bash
# 删除现有数据，重新获取全部历史
python sync_fund_nav_data.py --sync-holdings --full
```

### 查看同步日志

```bash
# 实时查看日志
tail -f sync_fund_nav.log

# 或查看完整日志
cat sync_fund_nav.log
```

## 数据更新策略

### 增量更新（默认）
- 只获取数据库中缺失的日期数据
- 速度快，适合日常更新

### 全量更新
- 重新获取所有历史数据
- 用于数据修复或首次同步

## 常见问题

### Q1: 同步失败怎么办？

**检查网络连接**：
```bash
# 测试akshare连接
python -c "import akshare as ak; print(ak.fund_open_fund_info_em('000001', '单位净值走势').head())"
```

**检查数据库连接**：
```bash
python -c "from data_retrieval.enhanced_database import EnhancedDatabaseManager; from shared.enhanced_config import DATABASE_CONFIG; db = EnhancedDatabaseManager(DATABASE_CONFIG); print('OK')"
```

### Q2: 数据同步后分析仍然慢？

检查是否所有基金都有数据：
```sql
SELECT fund_code, COUNT(*) as count 
FROM fund_analysis_results 
WHERE analysis_date >= DATE_SUB(NOW(), INTERVAL 1 YEAR)
GROUP BY fund_code;
```

如果某些基金 `count < 10`，说明数据不足，需要重新同步。

### Q3: 如何清理重复数据？

```sql
-- 查找重复数据
SELECT fund_code, analysis_date, COUNT(*) as cnt
FROM fund_analysis_results
GROUP BY fund_code, analysis_date
HAVING cnt > 1;

-- 删除重复数据（保留最新）
DELETE t1 FROM fund_analysis_results t1
INNER JOIN fund_analysis_results t2 
WHERE t1.id < t2.id 
AND t1.fund_code = t2.fund_code 
AND t1.analysis_date = t2.analysis_date;
```

## 性能对比

| 场景 | 同步前 | 同步后 | 提升 |
|-----|-------|-------|-----|
| 14只基金分析 | 30-60秒 | <2秒 | **95%+** |
| 数据来源 | akshare实时 | 数据库缓存 | **本地读取** |
| 用户体验 | 长时间loading | 秒开 | **即时响应** |

## 维护建议

1. **每日自动同步**：设置定时任务，收盘后自动更新
2. **监控同步日志**：定期检查 `sync_fund_nav.log`
3. **数据完整性检查**：每月检查一次数据完整性
4. **新增基金自动同步**：添加新持仓后手动执行一次同步

## 技术细节

### 数据表结构

数据存入 `fund_analysis_results` 表：
- `fund_code`: 基金代码
- `fund_name`: 基金名称
- `analysis_date`: 净值日期
- `current_estimate`: 单位净值
- `today_return`: 日收益率

### 同步流程

```
1. 读取 user_holdings 获取基金列表
2. 检查 fund_analysis_results 现有数据
3. 计算缺失的日期范围
4. 从akshare获取缺失数据
5. 批量插入/更新数据库
6. 输出同步统计报告
```

### 容错机制

- 单只基金失败不影响其他基金
- 自动重试失败的记录
- 详细的错误日志记录

---

*方案版本: 1.0*  
*创建时间: 2026-02-13*
