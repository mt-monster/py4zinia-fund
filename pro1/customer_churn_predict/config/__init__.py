# -*- coding: utf-8 -*-
"""
配置模块
"""

from .settings import get_config, LLM_CONFIG, DATA_CONFIG, MODEL_CONFIG, PREDICTION_CONFIG, FILE_CONFIG, AGENT_CONFIG

__all__ = [
    'get_config',
    'LLM_CONFIG',
    'DATA_CONFIG',
    'MODEL_CONFIG',
    'PREDICTION_CONFIG',
    'FILE_CONFIG',
    'AGENT_CONFIG'
]

