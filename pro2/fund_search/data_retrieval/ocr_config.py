#!/usr/bin/env python
# coding: utf-8

"""
OCR配置文件
用于配置OCR引擎的选择和参数
"""

import os

# OCR引擎配置
OCR_CONFIG = {
    # 默认OCR引擎: 'paddleocr' 或 'easyocr'
    'default_engine': 'easyocr',  # 由于PaddleOCR在某些系统上有兼容性问题，默认使用EasyOCR
    
    # 是否启用GPU加速
    'use_gpu': False,
    
    # 置信度阈值
    'confidence_threshold': 0.5,
    
    # 支持的语言
    'languages': {
        'paddleocr': 'ch',
        'easyocr': ['ch_sim', 'en']
    }
}

def get_ocr_engine():
    """获取当前配置的OCR引擎"""
    # 检查环境变量
    force_easyocr = os.getenv('FORCE_EASYOCR', 'false').lower() == 'true'
    if force_easyocr:
        return 'easyocr'
    
    force_paddleocr = os.getenv('FORCE_PADDLEOCR', 'false').lower() == 'true'
    if force_paddleocr:
        return 'paddleocr'
    
    # 返回默认配置
    return OCR_CONFIG['default_engine']

def should_use_gpu():
    """是否使用GPU加速"""
    gpu_env = os.getenv('OCR_USE_GPU', str(OCR_CONFIG['use_gpu'])).lower()
    return gpu_env in ['true', '1', 'yes']

def get_confidence_threshold():
    """获取置信度阈值"""
    threshold_env = os.getenv('OCR_CONFIDENCE_THRESHOLD')
    if threshold_env:
        try:
            return float(threshold_env)
        except ValueError:
            pass
    return OCR_CONFIG['confidence_threshold']