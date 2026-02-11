-- =====================================================
-- 基金数据缓存系统 - 数据库表结构
-- 缓存策略：
--   1. 实时数据（日涨跌幅、当前市值）：不缓存
--   2. 准实时数据（昨日数据）：内存缓存15分钟，数据库缓存1天
--   3. 低频指标（年化收益、夏普等）：存储在 fund_analysis_results 表
--
-- 注：基金绩效指标现在直接存储在 fund_analysis_results 表中
--     不再单独创建 fund_performance_cache 表，避免数据冗余
-- =====================================================

-- 1. 基金净值缓存表（按日存储每只基金的历史净值）
CREATE TABLE IF NOT EXISTS fund_nav_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_code VARCHAR(10) NOT NULL COMMENT '基金代码',
    nav_date DATE NOT NULL COMMENT '净值日期',
    nav_value DECIMAL(10,4) NOT NULL COMMENT '单位净值',
    accum_nav DECIMAL(10,4) COMMENT '累计净值',
    daily_return DECIMAL(8,4) COMMENT '日涨跌幅(%)',
    data_source VARCHAR(20) COMMENT '数据来源：tushare/akshare/eastmoney',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_fund_date (fund_code, nav_date),
    INDEX idx_fund_code (fund_code),
    INDEX idx_nav_date (nav_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='基金净值缓存表';

-- 2. 缓存元数据表（记录每只基金的最后更新时间和数据范围）
CREATE TABLE IF NOT EXISTS fund_cache_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_code VARCHAR(10) NOT NULL UNIQUE COMMENT '基金代码',
    earliest_date DATE COMMENT '最早有数据的日期',
    latest_date DATE COMMENT '最新有数据的日期',
    total_records INT DEFAULT 0 COMMENT '总记录数',
    last_sync_at TIMESTAMP COMMENT '最后同步时间',
    next_sync_at TIMESTAMP COMMENT '下次预定同步时间',
    sync_status ENUM('pending', 'syncing', 'completed', 'failed') DEFAULT 'pending' COMMENT '同步状态',
    sync_fail_count INT DEFAULT 0 COMMENT '连续失败次数',
    data_source VARCHAR(20) COMMENT '主要数据来源',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_sync_status (sync_status),
    INDEX idx_next_sync (next_sync_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='基金缓存元数据表';

-- 3. 用户持仓日终数据表（准实时数据，日终更新）
CREATE TABLE IF NOT EXISTS user_holding_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL COMMENT '用户ID',
    fund_code VARCHAR(10) NOT NULL COMMENT '基金代码',
    
    -- 静态数据
    holding_shares DECIMAL(15,4) COMMENT '持仓份额',
    cost_price DECIMAL(10,4) COMMENT '成本价',
    holding_amount DECIMAL(15,4) COMMENT '持有金额',
    
    -- 准实时数据（日终更新）
    yesterday_nav DECIMAL(10,4) COMMENT '昨日净值',
    yesterday_return DECIMAL(8,4) COMMENT '昨日涨跌幅(%)',
    yesterday_profit DECIMAL(15,4) COMMENT '昨日收益金额',
    yesterday_market_value DECIMAL(15,4) COMMENT '昨日市值',
    
    -- 累计数据
    total_buy_amount DECIMAL(15,4) COMMENT '累计买入金额',
    total_sell_amount DECIMAL(15,4) COMMENT '累计卖出金额',
    
    record_date DATE NOT NULL COMMENT '记录日期',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_user_fund_date (user_id, fund_code, record_date),
    INDEX idx_user_id (user_id),
    INDEX idx_record_date (record_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户持仓日终数据表';

-- 4. 用户持仓快照表（每日收盘后生成，用于快速展示）
CREATE TABLE IF NOT EXISTS user_portfolio_snapshot (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL COMMENT '用户ID',
    snapshot_date DATE NOT NULL COMMENT '快照日期',
    fund_code VARCHAR(10) NOT NULL COMMENT '基金代码',
    
    holding_shares DECIMAL(15,4) COMMENT '持仓份额',
    nav_value DECIMAL(10,4) COMMENT '当日净值',
    market_value DECIMAL(15,4) COMMENT '当日市值',
    daily_return DECIMAL(8,4) COMMENT '日涨跌幅(%)',
    holding_profit DECIMAL(15,4) COMMENT '持仓盈亏',
    total_profit DECIMAL(15,4) COMMENT '累计盈亏',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_user_fund_date (user_id, fund_code, snapshot_date),
    INDEX idx_user_date (user_id, snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户持仓快照表';

-- 5. 后台任务执行记录表
CREATE TABLE IF NOT EXISTS fund_sync_job_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_name VARCHAR(50) NOT NULL COMMENT '任务名称',
    job_type ENUM('daily', 'full', 'realtime') COMMENT '任务类型',
    start_time TIMESTAMP COMMENT '开始时间',
    end_time TIMESTAMP COMMENT '结束时间',
    status ENUM('running', 'success', 'failed') COMMENT '执行状态',
    total_count INT DEFAULT 0 COMMENT '处理总数',
    success_count INT DEFAULT 0 COMMENT '成功数',
    fail_count INT DEFAULT 0 COMMENT '失败数',
    error_message TEXT COMMENT '错误信息',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_job_name (job_name),
    INDEX idx_start_time (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据同步任务日志表';
