#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据访问层
提供 Repository 模式和数据库访问对象
"""

from .repositories.base import BaseRepository
from .repositories.fund_repository import FundRepository
from .repositories.holdings_repository import HoldingsRepository
from .repositories.analysis_repository import AnalysisRepository

__all__ = [
    'BaseRepository',
    'FundRepository',
    'HoldingsRepository',
    'AnalysisRepository'
]
