#!/usr/bin/env python
# coding: utf-8

"""
基金分析工具配置文件
"""

import os

# 基金持仓数据文件路径配置
FUND_POSITION_FILE_PATH = os.environ.get('FUND_POSITION_FILE_PATH', 'd:/codes/py4zinia/pro2/fund_search/京东金融.xlsx')

# 报告输出目录配置
REPORT_DIR = os.environ.get('REPORT_DIR', 'd:/codes/py4zinia/pro2/fund_search/reports')

# 数据库配置
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'root'),
    'database': os.environ.get('DB_NAME', 'fund_analysis'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'charset': os.environ.get('DB_CHARSET', 'utf8mb4')
}

# 微信通知配置
WECHAT_CONFIG = {
    'enabled': os.environ.get('WECHAT_ENABLED', 'True').lower() == 'true',
    'token': os.environ.get('WECHAT_TOKEN', 'fb0dfd5592ed4eb19cd886d737b6cc6a')
}