#!/usr/bin/env python
# coding: utf-8

"""
基金路由模块
"""

from .funds_list import register_funds_list_routes
from .funds_detail import register_funds_detail_routes
from .funds_history import register_funds_history_routes
from .funds_search import register_funds_search_routes

__all__ = [
    'register_funds_list_routes',
    'register_funds_detail_routes',
    'register_funds_history_routes',
    'register_funds_search_routes'
]
