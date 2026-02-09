#!/usr/bin/env python
# coding: utf-8

"""
增强版基金分析工具配置文件
"""

import os

# 基础配置
BASE_CONFIG = {
    # 基金持仓数据文件路径 - 使用相对路径
    'fund_position_file': os.environ.get(
        'FUND_POSITION_FILE_PATH', 
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '京东金融.xlsx')
    ),
    
    # 工作表名称
    'sheet_name': '持仓数据',
    
    # 数据列配置
    'columns': {
        'fund_code': '代码',
        'fund_name': '名称',
        'holding_amount': '持有金额',
        'daily_profit': '当日盈亏',
        'daily_return_rate': '当日盈亏率',
        'holding_profit': '持有盈亏',
        'holding_return_rate': '持有盈亏率',
        'total_profit': '累计盈亏',
        'total_return_rate': '累计盈亏率'
    }
}

# 数据库配置
DATABASE_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'root'),
    'database': os.environ.get('DB_NAME', 'fund_analysis'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'charset': os.environ.get('DB_CHARSET', 'utf8mb4')
}

# 数据源配置
DATA_SOURCE_CONFIG = {
    # Tushare 配置
    'tushare': {
        'token': os.environ.get('TUSHARE_TOKEN', '5ff19facae0e5b26a407d491d33707a9884a39a714a0d76b6495725b'),
        'timeout': int(os.environ.get('TUSHARE_TIMEOUT', 30)),
        'max_retries': int(os.environ.get('TUSHARE_RETRIES', 3))
    },
    
    # Akshare 配置
    'akshare': {
        'timeout': int(os.environ.get('AKSHARE_TIMEOUT', 30)),
        'max_retries': int(os.environ.get('AKSHARE_RETRIES', 3)),
        'delay_between_requests': float(os.environ.get('AKSHARE_DELAY', 1.0))
    },
    
    # 备用数据源配置
    'fallback': {
        'sina_enabled': os.environ.get('SINA_ENABLED', 'True').lower() == 'true',
        'eastmoney_enabled': os.environ.get('EASTMONEY_ENABLED', 'True').lower() == 'true',
        'request_timeout': int(os.environ.get('FALLBACK_TIMEOUT', 10))
    }
}

# 通知配置
NOTIFICATION_CONFIG = {
    'wechat': {
        'enabled': os.environ.get('WECHAT_ENABLED', 'True').lower() == 'true',
        'token': os.environ.get('WECHAT_TOKEN', 'fb0dfd5592ed4eb19cd886d737b6cc6a'),
        'template': 'html'
    },
    'email': {
        'enabled': os.environ.get('EMAIL_ENABLED', 'True').lower() == 'true',
        'token': os.environ.get('EMAIL_TOKEN', 'fb0dfd5592ed4eb19cd886d737b6cc6a'),  # PushPlus token
        'channel': os.environ.get('EMAIL_CHANNEL', 'mail'), # 'mail' for PushPlus, 'smtp' for standard SMTP
        # SMTP配置 (仅当 channel='smtp' 时需要)
        'smtp_host': os.environ.get('SMTP_HOST', 'smtp.qq.com'),
        'smtp_port': int(os.environ.get('SMTP_PORT', 465)),
        'smtp_user': os.environ.get('SMTP_USER', ''),
        'smtp_password': os.environ.get('SMTP_PASSWORD', ''),
        'smtp_receivers': os.environ.get('SMTP_RECEIVERS', '').split(',') if os.environ.get('SMTP_RECEIVERS') else []
    }
}

# 投资策略配置
INVESTMENT_STRATEGY_CONFIG = {
    # 无风险收益率（用于夏普比率计算）
    'risk_free_rate': float(os.environ.get('RISK_FREE_RATE', 0.03)),
    
    # 投资倍数配置
    'buy_multipliers': {
        'strong_buy': 3.0,      # 强烈买入
        'buy': 1.5,             # 正常买入
        'weak_buy': 1.0,        # 谨慎买入
        'hold': 0.0,            # 持有
        'sell': 0.0             # 卖出
    },
    
    # 赎回金额配置
    'redeem_amounts': {
        'small': 15,            # 小额赎回
        'medium': 30,           # 中等赎回
        'large': 50,            # 大额赎回
        'none': 0               # 不赎回
    }
}

# 绩效分析配置
PERFORMANCE_CONFIG = {
    # 历史数据天数
    'historical_days': int(os.environ.get('HISTORICAL_DAYS', 365)),
    
    # 年化计算基准
    'trading_days_per_year': int(os.environ.get('TRADING_DAYS_PER_YEAR', 252)),
    
    # 置信区间（用于VaR计算）
    'var_confidence': float(os.environ.get('VAR_CONFIDENCE', 0.05)),
    
    # 绩效指标权重（用于综合评分）
    'weights': {
        'annualized_return': 0.3,
        'sharpe_ratio': 0.25,
        'max_drawdown': 0.2,
        'volatility': 0.15,
        'win_rate': 0.1
    }
}

# 图表配置
CHART_CONFIG = {
    'dpi': int(os.environ.get('CHART_DPI', 350)),
    'figsize': (16, 10),
    'style': 'seaborn-v0_8',
    'color_palette': {
        'positive': ['#2E8B57', '#3CB371', '#219C55'],
        'neutral': ['#E7C628', '#F39C12', '#E67E22'],
        'negative': ['#CD5C5C', '#C0392B', '#922B21']
    }
}

# 日志配置
LOGGING_CONFIG = {
    'level': os.environ.get('LOG_LEVEL', 'INFO'),
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': os.environ.get('LOG_FILE', 'fund_analysis.log')
}