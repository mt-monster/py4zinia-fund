"""
基金分析服务模块

提供各类业务逻辑服务，包括：
- 基金类型分类服务（fund_type_service）：基于证监会标准的基金分类
"""

from .fund_type_service import (
    FundType,
    FundTypeService,
    classify_fund,
    get_fund_type_display,
    get_fund_type_css_class,
    FUND_TYPE_CN,
    FUND_TYPE_CSS_CLASS,
    FUND_TYPE_COLORS
)

__all__ = [
    'FundType',
    'FundTypeService',
    'classify_fund',
    'get_fund_type_display',
    'get_fund_type_css_class',
    'FUND_TYPE_CN',
    'FUND_TYPE_CSS_CLASS',
    'FUND_TYPE_COLORS'
]
