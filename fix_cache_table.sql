-- 修复 fund_data_cache 表缺失问题
-- 运行此SQL脚本创建缓存表

CREATE TABLE IF NOT EXISTS fund_data_cache (
    fund_code VARCHAR(20) NOT NULL,
    cache_date DATE NOT NULL,
    current_nav FLOAT,
    previous_nav FLOAT,
    prev_day_return FLOAT,
    nav_date VARCHAR(10),
    data_source VARCHAR(50),
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (fund_code, cache_date),
    INDEX idx_cached_at (cached_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 验证表是否创建成功
SELECT COUNT(*) as total_records FROM fund_data_cache;
