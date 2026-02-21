-- =====================================================
-- 策略反馈系统 - 数据库表结构
-- 
-- 功能说明：
--   1. 存储用户对策略匹配的反馈
--   2. 记录策略实际表现数据
--   3. 支持策略有效性分析和学习机制
--
-- 表清单：
--   - strategy_feedback: 用户反馈表
--   - strategy_performance: 策略表现记录表
--   - strategy_weights: 策略动态权重表
--   - strategy_learning_log: 策略学习日志表
-- =====================================================

-- -----------------------------------------------------
-- 1. 用户策略反馈表
-- 记录用户对策略匹配的评分和评论
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS strategy_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    
    -- 基金和策略关联信息
    fund_code VARCHAR(10) NOT NULL COMMENT '基金代码',
    fund_name VARCHAR(100) COMMENT '基金名称（冗余存储，方便查询）',
    strategy_type VARCHAR(50) NOT NULL COMMENT '策略类型标识',
    strategy_name VARCHAR(100) COMMENT '策略名称（冗余存储）',
    
    -- 匹配信息
    match_score DECIMAL(5,2) COMMENT '系统匹配得分(0-100)',
    match_reason TEXT COMMENT '匹配理由/策略推荐理由',
    
    -- 用户反馈信息
    user_id VARCHAR(50) DEFAULT 'default_user' COMMENT '用户ID',
    user_rating TINYINT COMMENT '用户评分(1-5星)',
    user_comment TEXT COMMENT '用户评论/反馈内容',
    feedback_type ENUM('accuracy', 'usefulness', 'overall') DEFAULT 'overall' 
        COMMENT '反馈类型：准确性/有用性/综合评价',
    
    -- 反馈状态
    is_helpful BOOLEAN DEFAULT NULL COMMENT '是否有帮助（布尔值）',
    would_recommend BOOLEAN DEFAULT NULL COMMENT '是否愿意推荐此策略',
    
    -- 时间戳
    feedback_date DATE NOT NULL COMMENT '反馈日期',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX idx_fund_code (fund_code),
    INDEX idx_strategy_type (strategy_type),
    INDEX idx_user_id (user_id),
    INDEX idx_feedback_date (feedback_date),
    INDEX idx_rating (user_rating),
    UNIQUE KEY uk_fund_strategy_user_date (fund_code, strategy_type, user_id, feedback_date) 
        COMMENT '同一用户同一天对同一基金策略只能有一条反馈'
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户策略反馈表';


-- -----------------------------------------------------
-- 2. 策略表现记录表
-- 记录策略预测与实际表现的对比
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS strategy_performance (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    
    -- 基金和策略关联信息
    fund_code VARCHAR(10) NOT NULL COMMENT '基金代码',
    strategy_type VARCHAR(50) NOT NULL COMMENT '策略类型标识',
    
    -- 预测信息
    predicted_action VARCHAR(20) COMMENT '预测操作：buy/sell/hold',
    predicted_confidence DECIMAL(5,2) COMMENT '预测置信度(0-100)',
    suggested_amount DECIMAL(12,2) COMMENT '建议金额',
    
    -- 实际表现数据
    actual_return DECIMAL(8,4) COMMENT '实际收益率(%)',
    actual_return_period INT DEFAULT 1 COMMENT '收益计算周期（天）',
    benchmark_return DECIMAL(8,4) COMMENT '基准收益率(%)，如沪深300',
    excess_return DECIMAL(8,4) COMMENT '超额收益率(%) = 实际收益 - 基准收益',
    
    -- 表现评估
    prediction_accuracy DECIMAL(5,2) COMMENT '预测准确度得分(0-100)',
    profit_loss DECIMAL(15,2) COMMENT '实际盈亏金额',
    max_drawdown DECIMAL(8,4) COMMENT '期间最大回撤(%)',
    volatility DECIMAL(8,4) COMMENT '期间波动率(%)',
    
    -- 时间信息
    prediction_date DATE NOT NULL COMMENT '预测日期',
    evaluation_date DATE COMMENT '评估日期（实际表现计算日期）',
    holding_days INT COMMENT '持仓天数',
    
    -- 状态
    status ENUM('pending', 'completed', 'expired') DEFAULT 'pending' 
        COMMENT '状态：等待评估/已完成/已过期',
    
    -- 元数据
    market_condition VARCHAR(20) COMMENT '市场环境：bull/bear/sideways',
    notes TEXT COMMENT '备注信息',
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_fund_code (fund_code),
    INDEX idx_strategy_type (strategy_type),
    INDEX idx_prediction_date (prediction_date),
    INDEX idx_status (status),
    INDEX idx_evaluation_date (evaluation_date),
    UNIQUE KEY uk_fund_strategy_pred_date (fund_code, strategy_type, prediction_date) 
        COMMENT '同一基金同一天同一策略只能有一条预测记录'
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='策略表现记录表';


-- -----------------------------------------------------
-- 3. 策略动态权重表
-- 根据反馈和表现动态调整各策略权重
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS strategy_weights (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    
    strategy_type VARCHAR(50) NOT NULL UNIQUE COMMENT '策略类型标识',
    strategy_name VARCHAR(100) NOT NULL COMMENT '策略名称',
    
    -- 权重配置
    base_weight DECIMAL(5,2) DEFAULT 1.00 COMMENT '基础权重',
    dynamic_weight DECIMAL(5,2) DEFAULT 1.00 COMMENT '动态调整后的权重',
    weight_adjustment DECIMAL(5,2) DEFAULT 0.00 COMMENT '权重调整量',
    
    -- 有效性指标
    effectiveness_score DECIMAL(5,2) DEFAULT 50.00 COMMENT '有效性得分(0-100)',
    feedback_count INT DEFAULT 0 COMMENT '反馈数量',
    avg_user_rating DECIMAL(3,2) DEFAULT 0.00 COMMENT '平均用户评分',
    success_rate DECIMAL(5,2) DEFAULT 0.00 COMMENT '成功率(%)',
    
    -- 统计指标
    total_predictions INT DEFAULT 0 COMMENT '总预测次数',
    accurate_predictions INT DEFAULT 0 COMMENT '准确预测次数',
    total_return DECIMAL(10,4) DEFAULT 0.0000 COMMENT '累计收益率(%)',
    sharpe_ratio DECIMAL(8,4) DEFAULT 0.0000 COMMENT '夏普比率',
    
    -- 学习参数
    learning_rate DECIMAL(4,3) DEFAULT 0.100 COMMENT '学习率',
    momentum DECIMAL(4,3) DEFAULT 0.050 COMMENT '动量因子',
    
    -- 时间戳
    last_updated DATE COMMENT '最后更新时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_effectiveness (effectiveness_score),
    INDEX idx_dynamic_weight (dynamic_weight)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='策略动态权重表';


-- -----------------------------------------------------
-- 4. 策略学习日志表
-- 记录策略权重的调整历史
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS strategy_learning_log (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    
    strategy_type VARCHAR(50) NOT NULL COMMENT '策略类型标识',
    
    -- 调整信息
    adjustment_type ENUM('feedback', 'performance', 'manual', 'auto') 
        DEFAULT 'auto' COMMENT '调整类型',
    old_weight DECIMAL(5,2) NOT NULL COMMENT '调整前权重',
    new_weight DECIMAL(5,2) NOT NULL COMMENT '调整后权重',
    change_amount DECIMAL(5,2) NOT NULL COMMENT '变化量',
    change_reason TEXT COMMENT '调整原因',
    
    -- 触发因素
    feedback_id INT COMMENT '关联的反馈ID',
    performance_id INT COMMENT '关联的表现记录ID',
    triggered_by VARCHAR(50) COMMENT '触发者（用户ID或system）',
    
    -- 影响评估
    expected_improvement DECIMAL(5,2) COMMENT '预期改进幅度',
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_strategy_type (strategy_type),
    INDEX idx_adjustment_type (adjustment_type),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (feedback_id) REFERENCES strategy_feedback(id) ON DELETE SET NULL,
    FOREIGN KEY (performance_id) REFERENCES strategy_performance(id) ON DELETE SET NULL
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='策略学习日志表';


-- -----------------------------------------------------
-- 5. 策略匹配历史表
-- 记录策略与基金匹配的历史记录
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS strategy_match_history (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    
    fund_code VARCHAR(10) NOT NULL COMMENT '基金代码',
    fund_name VARCHAR(100) COMMENT '基金名称',
    strategy_type VARCHAR(50) NOT NULL COMMENT '策略类型',
    
    -- 匹配信息
    match_score DECIMAL(5,2) NOT NULL COMMENT '匹配得分',
    match_rank INT COMMENT '匹配排名',
    is_recommended BOOLEAN DEFAULT FALSE COMMENT '是否被推荐',
    
    -- 基金特征快照
    fund_type VARCHAR(50) COMMENT '基金类型',
    risk_level VARCHAR(20) COMMENT '风险等级',
    volatility_snapshot DECIMAL(8,4) COMMENT '波动率快照',
    sharpe_snapshot DECIMAL(8,4) COMMENT '夏普比率快照',
    
    -- 时间戳
    match_date DATE NOT NULL COMMENT '匹配日期',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_fund_code (fund_code),
    INDEX idx_strategy_type (strategy_type),
    INDEX idx_match_date (match_date),
    INDEX idx_match_score (match_score),
    UNIQUE KEY uk_fund_strategy_date (fund_code, strategy_type, match_date)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='策略匹配历史表';


-- -----------------------------------------------------
-- 初始化策略权重数据
-- 插入默认策略配置
-- -----------------------------------------------------
INSERT INTO strategy_weights 
    (strategy_type, strategy_name, base_weight, dynamic_weight, effectiveness_score, learning_rate)
VALUES
    ('enhanced_rule_based', '增强规则策略', 1.00, 1.00, 50.00, 0.10),
    ('dual_ma', '双均线策略', 1.00, 1.00, 50.00, 0.10),
    ('mean_reversion', '均值回归策略', 1.00, 1.00, 50.00, 0.10),
    ('target_value', '目标价值策略', 1.00, 1.00, 50.00, 0.10),
    ('grid', '网格交易策略', 1.00, 1.00, 50.00, 0.10),
    ('trend_following', '趋势跟踪策略', 1.00, 1.00, 50.00, 0.10),
    ('volatility_based', '波动率策略', 1.00, 1.00, 50.00, 0.10)
ON DUPLICATE KEY UPDATE 
    strategy_name = VALUES(strategy_name);


-- -----------------------------------------------------
-- 创建视图：策略有效性综合评估
-- -----------------------------------------------------
CREATE OR REPLACE VIEW v_strategy_effectiveness AS
SELECT 
    sw.strategy_type,
    sw.strategy_name,
    sw.dynamic_weight,
    sw.effectiveness_score,
    sw.avg_user_rating,
    sw.success_rate,
    sw.total_predictions,
    sw.accurate_predictions,
    
    -- 计算综合得分（权重可调整）
    (
        sw.effectiveness_score * 0.4 +
        (sw.avg_user_rating * 20) * 0.3 +  -- 5星制转换为百分制
        sw.success_rate * 0.3
    ) AS composite_score,
    
    -- 反馈统计
    COUNT(DISTINCT sf.id) AS feedback_count,
    AVG(sf.user_rating) AS recent_avg_rating,
    
    -- 最近30天表现
    COUNT(DISTINCT CASE 
        WHEN sp.prediction_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) 
        THEN sp.id 
    END) AS predictions_30d,
    
    AVG(CASE 
        WHEN sp.prediction_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) 
        THEN sp.prediction_accuracy 
    END) AS accuracy_30d

FROM strategy_weights sw
LEFT JOIN strategy_feedback sf ON sw.strategy_type = sf.strategy_type
LEFT JOIN strategy_performance sp ON sw.strategy_type = sp.strategy_type
GROUP BY sw.strategy_type, sw.strategy_name, sw.dynamic_weight, 
         sw.effectiveness_score, sw.avg_user_rating, sw.success_rate,
         sw.total_predictions, sw.accurate_predictions
ORDER BY composite_score DESC;


-- -----------------------------------------------------
-- 创建视图：基金策略反馈汇总
-- -----------------------------------------------------
CREATE OR REPLACE VIEW v_fund_strategy_feedback_summary AS
SELECT 
    fund_code,
    fund_name,
    strategy_type,
    COUNT(*) AS total_feedback,
    AVG(user_rating) AS avg_rating,
    COUNT(CASE WHEN is_helpful = TRUE THEN 1 END) AS helpful_count,
    COUNT(CASE WHEN is_helpful = FALSE THEN 1 END) AS not_helpful_count,
    ROUND(
        COUNT(CASE WHEN is_helpful = TRUE THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 
        2
    ) AS helpful_rate,
    MAX(feedback_date) AS last_feedback_date
FROM strategy_feedback
GROUP BY fund_code, fund_name, strategy_type;
