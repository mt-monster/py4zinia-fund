#!/usr/bin/env python
# coding: utf-8
"""
公共基金辅助函数
将分散在各路由文件中的重复辅助函数集中到此处，统一维护。

提供：
  - get_fund_name_from_db(fund_code) -> Optional[str]
  - get_fund_type_for_allocation(fund_code, db_manager) -> str
  - classify_fund(fund_name, fund_code, official_type) -> str  （依赖各文件已有实现时直接复用）
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# get_fund_name_from_db — 最完整版（查 fund_basic_info > user_holdings >
#                          fund_analysis_results > akshare）
# ---------------------------------------------------------------------------

def get_fund_name_from_db(fund_code: str, db_manager=None) -> Optional[str]:
    """
    从数据库获取基金名称，支持多个数据源回退。

    查询优先级：
      1. fund_basic_info.fund_name
      2. user_holdings.fund_name
      3. fund_analysis_results.fund_name
      4. akshare 实时查询（网络兜底）

    Args:
        fund_code: 基金代码
        db_manager: 数据库管理器，可选；若不传则尝试从全局 components 获取

    Returns:
        基金名称字符串，获取失败返回 None
    """
    if db_manager is None:
        db_manager = _get_db_manager()

    if db_manager is None:
        return None

    try:
        # 1. fund_basic_info
        try:
            sql = "SELECT fund_name FROM fund_basic_info WHERE fund_code = :fund_code LIMIT 1"
            result = db_manager.execute_query(sql, {'fund_code': fund_code})
            if result is not None and not result.empty:
                name = result.iloc[0]['fund_name']
                if name and str(name) != fund_code:
                    return str(name)
        except Exception as e:
            logger.debug(f"fund_basic_info 获取基金名称失败: {e}")

        # 2. user_holdings
        try:
            sql = "SELECT fund_name FROM user_holdings WHERE fund_code = :fund_code LIMIT 1"
            result = db_manager.execute_query(sql, {'fund_code': fund_code})
            if result is not None and not result.empty:
                name = result.iloc[0]['fund_name']
                if name and str(name) != fund_code:
                    return str(name)
        except Exception as e:
            logger.debug(f"user_holdings 获取基金名称失败: {e}")

        # 3. fund_analysis_results
        try:
            sql = ("SELECT fund_name FROM fund_analysis_results "
                   "WHERE fund_code = :fund_code ORDER BY analysis_date DESC LIMIT 1")
            result = db_manager.execute_query(sql, {'fund_code': fund_code})
            if result is not None and not result.empty:
                name = result.iloc[0]['fund_name']
                if name and str(name) != fund_code:
                    return str(name)
        except Exception as e:
            logger.debug(f"fund_analysis_results 获取基金名称失败: {e}")

        # 4. akshare 兜底
        try:
            import akshare as ak
            try:
                fund_list = ak.fund_name_em()
                if '基金代码' in fund_list.columns and '基金简称' in fund_list.columns:
                    row = fund_list[fund_list['基金代码'] == fund_code]
                    if not row.empty:
                        return row.iloc[0]['基金简称']
            except Exception:
                pass

            try:
                fund_daily = ak.fund_open_fund_daily_em()
                if '基金代码' in fund_daily.columns and '基金简称' in fund_daily.columns:
                    row = fund_daily[fund_daily['基金代码'] == fund_code]
                    if not row.empty:
                        return row.iloc[0]['基金简称']
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"akshare 获取基金名称失败: {e}")

        return None
    except Exception as e:
        logger.warning(f"获取基金名称失败 [{fund_code}]: {e}")
        return None


# ---------------------------------------------------------------------------
# get_fund_type_for_allocation — 合并 dashboard.py 和 holdings.py 两个版本
#   dashboard 版本优先使用预加载器缓存，holdings 版本没有，这里合并两者
# ---------------------------------------------------------------------------

def get_fund_type_for_allocation(fund_code: str, db_manager=None) -> str:
    """
    获取基金的资产配置分类（证监会标准分类）。

    查询优先级：
      1. fund_data_preloader 预加载缓存（dashboard 版本的优化）
      2. fund_basic_info 表
      3. fund_analysis_results 表

    Args:
        fund_code: 基金代码
        db_manager: 数据库管理器，可选

    Returns:
        基金类型字符串，如 '股票型'/'债券型'/'混合型'/'货币型'/'其他'，
        无法识别时返回 'unknown'
    """
    if db_manager is None:
        db_manager = _get_db_manager()

    # 1. 预加载器缓存（最快）
    try:
        from services.fund_data_preloader import get_preloader
        preloader = get_preloader()
        basic_info = preloader.get_fund_basic_info(fund_code)
        if basic_info:
            fund_name = basic_info.get('fund_name', '')
            official_type = basic_info.get('fund_type', '')
            if fund_name or official_type:
                return _classify_fund(fund_name, fund_code, official_type)
    except Exception:
        pass

    if db_manager is None:
        return 'unknown'

    # 2. fund_basic_info
    try:
        sql = ("SELECT fund_name, fund_type FROM fund_basic_info "
               "WHERE fund_code = :fund_code LIMIT 1")
        df = db_manager.execute_query(sql, {'fund_code': fund_code})
        if not df.empty:
            fund_name = df.iloc[0]['fund_name'] if _notna(df.iloc[0]['fund_name']) else ''
            official_type = df.iloc[0]['fund_type'] if _notna(df.iloc[0]['fund_type']) else ''
            return _classify_fund(fund_name, fund_code, official_type)
    except Exception:
        pass

    # 3. fund_analysis_results
    try:
        sql = ("SELECT fund_name FROM fund_analysis_results "
               "WHERE fund_code = :fund_code ORDER BY analysis_date DESC LIMIT 1")
        df = db_manager.execute_query(sql, {'fund_code': fund_code})
        if not df.empty and _notna(df.iloc[0]['fund_name']):
            return _classify_fund(df.iloc[0]['fund_name'], fund_code)
    except Exception:
        pass

    return 'unknown'


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _get_db_manager():
    """尝试从 Flask app context 获取 db_manager"""
    try:
        from flask import current_app
        return current_app.config.get('db_manager') or current_app.extensions.get('db_manager')
    except Exception:
        return None


def _notna(val) -> bool:
    """判断值非空非 NaN"""
    if val is None:
        return False
    try:
        import math
        return not math.isnan(float(val))
    except (TypeError, ValueError):
        return bool(val)


def _classify_fund(fund_name: str, fund_code: str = '', official_type: str = '') -> str:
    """
    根据基金名称和官方类型推断标准分类。
    这是各路由文件中 classify_fund 函数的统一版本。
    """
    # 优先使用官方类型
    if official_type:
        ot = str(official_type)
        if '股票' in ot:
            return '股票型'
        if '混合' in ot:
            return '混合型'
        if '债券' in ot or '债' in ot:
            return '债券型'
        if '货币' in ot:
            return '货币型'
        if '指数' in ot or 'ETF' in ot.upper():
            return '指数型'
        if 'QDII' in ot.upper():
            return 'QDII'

    # 从基金名称推断
    if fund_name:
        name = str(fund_name).upper()
        if any(k in name for k in ['货币', '现金', '理财']):
            return '货币型'
        if 'QDII' in name or '全球' in name or '海外' in name:
            return 'QDII'
        if any(k in name for k in ['债券', '纯债', '信用债', '固收']):
            return '债券型'
        if any(k in name for k in ['指数', 'ETF', '沪深300', '中证', 'CSI', 'HS300']):
            return '指数型'
        if any(k in name for k in ['股票', '成长', '价值', 'EQUITY']):
            return '股票型'
        if any(k in name for k in ['混合', '平衡', '配置', '灵活']):
            return '混合型'

    # 按基金代码规律兜底（6位数字以519开头多为货币，其余难以判断）
    if fund_code and str(fund_code).startswith('519'):
        return '货币型'

    return 'unknown'
