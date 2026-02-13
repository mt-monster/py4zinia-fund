# 数据库统一改造说明

## 改造概述

本项目已完成数据库统一改造，从 SQLite + MySQL 双数据库架构统一为 **纯 MySQL 架构**。

## 改造内容

### 1. 删除的文件

- `web/sqlite_adapter.py` - SQLite 适配器（已删除）

### 2. 修改的文件

#### `data_retrieval/portfolio_importer.py`
- 移除 `import sqlite3`
- 修改 `__init__` 方法：从 `db_path` 参数改为 `db_manager` 参数
- 修改 `import_to_database` 方法：使用 MySQL 语法 (`%s` 占位符)
- 修改 `get_user_portfolio` 方法：使用 MySQL 查询
- 修改 `_ensure_portfolio_table` 方法：创建 MySQL 版本的 `user_portfolio` 表
- 新增 `delete_portfolio` 方法
- 新增 `clear_user_portfolio` 方法

#### `setup_local_dev.py`
- 完全重写，移除所有 SQLite 相关逻辑
- 改为 MySQL 本地开发环境配置助手
- 添加 MySQL 连接检查功能
- 添加 Docker MySQL 启动命令

### 3. 删除的数据库文件

- `fund_analysis.db` - SQLite 数据库文件
- `fund_data.db` - SQLite 数据库文件

## 数据库表结构

### user_portfolio 表（新增）

用于存储从截图导入的持仓信息：

```sql
CREATE TABLE user_portfolio (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    user_id VARCHAR(50) NOT NULL DEFAULT 'default' COMMENT '用户ID',
    fund_code VARCHAR(10) NOT NULL COMMENT '基金代码',
    fund_name VARCHAR(200) COMMENT '基金名称',
    nav_value DECIMAL(10,4) COMMENT '单位净值',
    change_amount DECIMAL(10,2) COMMENT '涨跌金额',
    change_percent DECIMAL(6,2) COMMENT '涨跌百分比',
    position_value DECIMAL(15,2) COMMENT '持仓金额',
    shares DECIMAL(15,4) COMMENT '持有份额',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    UNIQUE KEY uk_user_fund (user_id, fund_code),
    INDEX idx_user_id (user_id),
    INDEX idx_fund_code (fund_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

## 快速开始

### 1. 确保 MySQL 已安装并运行

```bash
# Windows
net start mysql

# Linux
sudo systemctl start mysql

# Mac
brew services start mysql
```

### 2. 配置数据库连接

编辑 `shared/enhanced_config.py` 中的 `DATABASE_CONFIG`：

```python
DATABASE_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'your_password',
    'database': 'fund_analysis',
    'port': 3306,
    'charset': 'utf8mb4'
}
```

或使用环境变量：

```bash
set DB_HOST=localhost
set DB_USER=root
set DB_PASSWORD=your_password
set DB_NAME=fund_analysis
set DB_PORT=3306
```

### 3. 运行环境检查

```bash
python setup_local_dev.py
```

### 4. 启动应用

```bash
python -m web.app
```

## 使用 Docker 启动 MySQL

```bash
docker run -d \
  --name fund-mysql \
  -e MYSQL_ROOT_PASSWORD=123456 \
  -e MYSQL_DATABASE=fund_analysis \
  -p 3306:3306 \
  --restart unless-stopped \
  mysql:8.0 \
  --character-set-server=utf8mb4 \
  --collation-server=utf8mb4_unicode_ci
```

## 架构对比

### 改造前

```
┌──────────────────────────────────────────────────────┐
│                    应用层                             │
├──────────────────────────────────────────────────────┤
│  SQLite (本地开发)        │  MySQL (生产环境)        │
│  - fund_analysis.db       │  - fund_analysis DB      │
│  - user_portfolio         │  - user_holdings         │
└──────────────────────────────────────────────────────┘
```

问题：
- 开发和生产环境不一致
- 需要维护两套 SQL 语法
- 数据分散，一致性风险

### 改造后

```
┌──────────────────────────────────────────────────────┐
│                    应用层                             │
├──────────────────────────────────────────────────────┤
│              MySQL (统一数据库)                       │
│              - fund_analysis DB                       │
│              - user_holdings                          │
│              - user_portfolio                         │
│              - fund_analysis_results                  │
│              - 其他所有表...                          │
└──────────────────────────────────────────────────────┘
```

优势：
- 开发和生产环境完全一致
- 只需维护一套 SQL 语法（MySQL）
- 数据集中，便于管理
- 支持复杂查询、事务、并发

## 注意事项

1. **首次启动会自动创建表结构**
   - `EnhancedDatabaseManager` 会在首次连接时自动创建所有必需的表

2. **数据迁移**
   - 如果之前 SQLite 中有重要数据，需要手动迁移到 MySQL
   - 可使用 `INSERT INTO ... SELECT ...` 语句迁移

3. **依赖包**
   - 确保已安装 `pymysql`：`pip install pymysql`

## 故障排查

### 连接失败

检查 MySQL 服务是否运行：
```bash
# Windows
net start | findstr MySQL

# Linux/Mac
ps aux | grep mysql
```

### 权限问题

确保数据库用户有足够权限：
```sql
GRANT ALL PRIVILEGES ON fund_analysis.* TO 'your_user'@'localhost';
FLUSH PRIVILEGES;
```

### 字符集问题

确保数据库使用 utf8mb4：
```sql
ALTER DATABASE fund_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
