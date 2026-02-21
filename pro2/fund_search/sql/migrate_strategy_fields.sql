-- 策略建议字段整合迁移脚本
-- 将 status_label, operation_suggestion, execution_amount 合并为 strategy_advice JSON 字段

-- 1. 添加新的 JSON 字段
ALTER TABLE fund_analysis_results 
ADD COLUMN strategy_advice JSON COMMENT '策略建议(JSON格式):包含状态、操作建议、执行金额';

-- 2. 迁移数据：将三个字段合并为 JSON
UPDATE fund_analysis_results 
SET strategy_advice = JSON_OBJECT(
    'status_label', status_label,
    'operation_suggestion', operation_suggestion,
    'execution_amount', execution_amount
)
WHERE status_label IS NOT NULL 
   OR operation_suggestion IS NOT NULL 
   OR execution_amount IS NOT NULL;

-- 3. 删除旧字段（确认数据迁移成功后执行）
-- ALTER TABLE fund_analysis_results 
-- DROP COLUMN status_label,
-- DROP COLUMN operation_suggestion,
-- DROP COLUMN execution_amount;

-- 4. 创建虚拟生成列用于查询（可选）
-- 如果经常需要根据状态筛选，可以创建虚拟列
ALTER TABLE fund_analysis_results 
ADD COLUMN advice_status VARCHAR(50) 
    GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(strategy_advice, '$.status_label'))) 
    STORED COMMENT '策略状态(从JSON生成)';

ALTER TABLE fund_analysis_results 
ADD COLUMN advice_action VARCHAR(100) 
    GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(strategy_advice, '$.operation_suggestion'))) 
    STORED COMMENT '操作建议(从JSON生成)';

-- 5. 为生成列添加索引
CREATE INDEX idx_advice_status ON fund_analysis_results(advice_status);


-- ============================================
-- 回滚脚本（如需恢复）
-- ============================================
/*
-- 1. 重新添加原字段
ALTER TABLE fund_analysis_results 
ADD COLUMN status_label VARCHAR(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
ADD COLUMN operation_suggestion VARCHAR(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
ADD COLUMN execution_amount VARCHAR(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL;

-- 2. 从 JSON 恢复数据
UPDATE fund_analysis_results 
SET status_label = JSON_UNQUOTE(JSON_EXTRACT(strategy_advice, '$.status_label')),
    operation_suggestion = JSON_UNQUOTE(JSON_EXTRACT(strategy_advice, '$.operation_suggestion')),
    execution_amount = JSON_UNQUOTE(JSON_EXTRACT(strategy_advice, '$.execution_amount'))
WHERE strategy_advice IS NOT NULL;

-- 3. 删除 JSON 字段和生成列
ALTER TABLE fund_analysis_results 
DROP COLUMN strategy_advice,
DROP COLUMN advice_status,
DROP COLUMN advice_action;
*/
