# -*- coding: utf-8 -*-
"""
配置文件
"""

import os
from typing import Dict, Any

# LLM 配置
LLM_CONFIG = {
    'api_key': os.getenv('LLM_API_KEY', '7301bcd7-0207-4bc1-8bd7-8f64182fa1bb'),
    'base_url': os.getenv('LLM_BASE_URL', 'https://ark.cn-beijing.volces.com/api/v3'),
    'model': os.getenv('LLM_MODEL', 'kimi-k2-thinking-251104')
}

# 数据生成配置
DATA_CONFIG = {
    'n_customers': int(os.getenv('N_CUSTOMERS', 3000)),
    'n_weeks': int(os.getenv('N_WEEKS', 12))
}

# 模型配置
MODEL_CONFIG = {
    'n_estimators': 300,
    'max_depth': 5,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'scale_pos_weight': 3.5,
    'random_state': 42
}

# 预测配置
PREDICTION_CONFIG = {
    'risk_threshold': 0.6,
    'top_k': 30
}

# 文件路径配置
FILE_CONFIG = {
    'save_path': os.getenv('SAVE_PATH', './'),
    'memory_file': 'agent_memory.json',
    'retention_plan_file': 'securities_retention_plan.xlsx',
    'data_dir': 'data',
    'reports_dir': 'reports'
}

# Agent 配置
AGENT_CONFIG = {
    'max_memory': 1000,
    'enable_llm': bool(os.getenv('ENABLE_LLM', 'true').lower() == 'true')
}

def get_config() -> Dict[str, Any]:
    """获取完整配置"""
    return {
        'llm': LLM_CONFIG,
        'data': DATA_CONFIG,
        'model': MODEL_CONFIG,
        'prediction': PREDICTION_CONFIG,
        'file': FILE_CONFIG,
        'agent': AGENT_CONFIG
    }

