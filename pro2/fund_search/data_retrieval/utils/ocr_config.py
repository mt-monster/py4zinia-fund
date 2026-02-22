#!/usr/bin/env python
# coding: utf-8

"""
OCR配置文件
用于配置OCR引擎的选择和参数
支持百度OCR、EasyOCR、PaddleOCR
"""

import os

# 百度OCR硬编码配置（从截图获取）
BAIDU_OCR_CONFIG = {
    'api_key': 'iJLqdFrPaRxJQSbzuBH047cB',
    'secret_key': 'bMQ50psuEfkS4KiVSfTwJXNaAG65krnK'
}

# OCR引擎配置
OCR_CONFIG = {
    # 默认OCR引擎: 'baidu', 'easyocr', 'paddleocr'
    'default_engine': 'baidu',  # 默认使用百度OCR

    # 是否启用GPU加速
    'use_gpu': False,

    # 置信度阈值
    'confidence_threshold': 0.5,

    # 支持的语言
    'languages': {
        'paddleocr': 'ch',
        'easyocr': ['ch_sim', 'en'],
        'baidu': 'CHN_ENG'
    },

    # 百度OCR配置 - 优先使用环境变量，否则使用硬编码配置
    'baidu': {
        'api_key': os.getenv('BAIDU_OCR_API_KEY') or BAIDU_OCR_CONFIG['api_key'],
        'secret_key': os.getenv('BAIDU_OCR_SECRET_KEY') or BAIDU_OCR_CONFIG['secret_key'],
        'use_accurate': True,  # 使用高精度识别
        'timeout': 30,  # 请求超时时间
    },

    # EasyOCR配置
    'easyocr': {
        'gpu': False,
        'languages': ['ch_sim', 'en']
    },

    # PaddleOCR配置
    'paddleocr': {
        'use_angle_cls': True,
        'lang': 'ch',
        'show_log': False
    }
}


def get_ocr_engine():
    """获取当前配置的OCR引擎"""
    # 检查环境变量
    engine_env = os.getenv('OCR_ENGINE')
    if engine_env and engine_env in ['baidu', 'easyocr', 'paddleocr']:
        return engine_env

    force_easyocr = os.getenv('FORCE_EASYOCR', 'false').lower() == 'true'
    if force_easyocr:
        return 'easyocr'

    force_paddleocr = os.getenv('FORCE_PADDLEOCR', 'false').lower() == 'true'
    if force_paddleocr:
        return 'paddleocr'

    # 返回默认配置
    return OCR_CONFIG['default_engine']


def set_ocr_engine(engine: str):
    """设置OCR引擎"""
    if engine in ['baidu', 'easyocr', 'paddleocr']:
        OCR_CONFIG['default_engine'] = engine
        os.environ['OCR_ENGINE'] = engine
        return True
    return False


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


def get_baidu_api_key():
    """获取百度OCR API Key"""
    return os.getenv('BAIDU_OCR_API_KEY', OCR_CONFIG['baidu']['api_key'])


def get_baidu_secret_key():
    """获取百度OCR Secret Key"""
    return os.getenv('BAIDU_OCR_SECRET_KEY', OCR_CONFIG['baidu']['secret_key'])


def get_baidu_config():
    """获取百度OCR完整配置"""
    return {
        'api_key': get_baidu_api_key(),
        'secret_key': get_baidu_secret_key(),
        'use_accurate': OCR_CONFIG['baidu']['use_accurate'],
        'timeout': OCR_CONFIG['baidu']['timeout']
    }


def get_available_engines():
    """获取可用的OCR引擎列表"""
    engines = []

    # 检查百度OCR是否可用
    baidu_config = get_baidu_config()
    if baidu_config['api_key'] and baidu_config['secret_key']:
        engines.append({
            'name': 'baidu',
            'display_name': '百度OCR',
            'description': '百度智能云OCR，高精度识别，需要网络连接',
            'available': True
        })
    else:
        engines.append({
            'name': 'baidu',
            'display_name': '百度OCR',
            'description': '百度智能云OCR（未配置API Key）',
            'available': False
        })

    # 检查EasyOCR是否可用
    try:
        import easyocr
        engines.append({
            'name': 'easyocr',
            'display_name': 'EasyOCR',
            'description': '本地OCR引擎，无需网络，首次加载较慢',
            'available': True
        })
    except ImportError:
        engines.append({
            'name': 'easyocr',
            'display_name': 'EasyOCR',
            'description': '本地OCR引擎（未安装）',
            'available': False
        })

    # 检查PaddleOCR是否可用
    try:
        from paddleocr import PaddleOCR
        engines.append({
            'name': 'paddleocr',
            'display_name': 'PaddleOCR',
            'description': '百度开源OCR，本地识别',
            'available': True
        })
    except ImportError:
        engines.append({
            'name': 'paddleocr',
            'display_name': 'PaddleOCR',
            'description': '百度开源OCR（未安装）',
            'available': False
        })

    return engines


def validate_engine_config(engine: str) -> tuple:
    """
    验证OCR引擎配置

    Returns:
        (是否可用, 错误信息)
    """
    if engine == 'baidu':
        api_key = get_baidu_api_key()
        secret_key = get_baidu_secret_key()
        if not api_key or not secret_key:
            return False, "百度OCR需要配置API Key和Secret Key"
        return True, "配置有效"

    elif engine == 'easyocr':
        try:
            import easyocr
            return True, "EasyOCR已安装"
        except ImportError:
            return False, "EasyOCR未安装，请运行: pip install easyocr"

    elif engine == 'paddleocr':
        try:
            from paddleocr import PaddleOCR
            return True, "PaddleOCR已安装"
        except ImportError:
            return False, "PaddleOCR未安装，请运行: pip install paddleocr"

    else:
        return False, f"未知的OCR引擎: {engine}"
