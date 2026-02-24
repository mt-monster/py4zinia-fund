#!/usr/bin/env python
# coding: utf-8

"""
投资策略模块

提供基于收益率的投资策略判断逻辑。
"""

from .rules import InvestmentStrategyRules, StrategyResult, ActionType

__all__ = ['InvestmentStrategyRules', 'StrategyResult', 'ActionType']
