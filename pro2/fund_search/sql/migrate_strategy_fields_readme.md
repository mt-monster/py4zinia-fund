# 策略建议字段整合说明

## 概述
将 `fund_analysis_results` 表中的三个字段：
- `status_label` (策略状态标签)
- `operation_suggestion` (操作建议描述)  
- `execution_amount` (执行金额建议)

合并为一个 JSON 字段 `strategy_advice`。

## 数据结构对比

### 整合前
```sql
status_label VARCHAR(50),
operation_suggestion VARCHAR(100),
execution_amount VARCHAR(20)
```

### 整合后
```sql
strategy_advice JSON,
advice_status VARCHAR(50) GENERATED,  -- 虚拟列
advice_action VARCHAR(100) GENERATED   -- 虚拟列
```

JSON 格式示例：
```json
{
    "status_label": "🔴 反转下跌",
    "operation_suggestion": "建议止盈（赎回8%仓位）",
    "execution_amount": "建议赎回：赎回8%持仓"
}
```

## 优缺点分析

### 优点
1. **表结构更简洁** - 减少字段数量
2. **扩展性好** - 后续添加新的建议字段无需修改表结构
3. **逻辑内聚** - 三个相关字段放在一起

### 缺点
1. **查询复杂度增加** - 需要使用 JSON 函数提取字段
2. **索引效率降低** - JSON 字段索引不如普通字段高效
3. **需要修改代码** - 所有读写这三个字段的地方都需要修改

## 需要修改的代码文件

### 1. 数据库操作
- `data_retrieval/enhanced_database.py` - 创建表语句

### 2. 数据写入
- `web/routes/holdings.py` - 多处 INSERT/UPDATE
- `web/routes/analysis.py` - 数据保存

### 3. 数据读取
- `web/routes/funds.py` - 查询语句
- `web/routes/strategies.py` - 查询语句

### 4. 前端展示
- 已完成（三列合并为一列）

## 建议

**如果当前系统运行稳定，建议暂不整合数据库字段**，原因：
1. 改动涉及面广，需要修改多个文件
2. 收益有限（只是减少2个字段）
3. 引入 JSON 查询复杂度

**如果确实需要整合**，建议：
1. 先在测试环境验证迁移脚本
2. 保留原字段一段时间作为备份
3. 逐步修改代码，确保兼容性
