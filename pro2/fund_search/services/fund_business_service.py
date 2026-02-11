#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金业务服务
整合 Repository 和数据服务，提供高层次的业务接口
供 Web 路由层调用
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import logging

from data_access.repositories import FundRepository, HoldingsRepository, AnalysisRepository
from services import fund_data_service

logger = logging.getLogger(__name__)


@dataclass
class FundDetailDTO:
    """基金详情 DTO"""
    fund_code: str
    fund_name: Optional[str] = None
    basic_info: Optional[Dict] = None
    realtime_data: Optional[Dict] = None
    analysis_data: Optional[Dict] = None
    performance_metrics: Optional[Dict] = None
    nav_history: Optional[pd.DataFrame] = None


@dataclass
class HoldingDetailDTO:
    """持仓详情 DTO"""
    holding_id: int
    fund_code: str
    fund_name: str
    holding_shares: float
    cost_price: float
    holding_amount: float
    current_nav: Optional[float] = None
    current_value: Optional[float] = None
    today_return: Optional[float] = None
    holding_profit: Optional[float] = None
    holding_profit_rate: Optional[float] = None


class FundBusinessService:
    """
    基金业务服务
    
    整合数据获取、缓存、数据库访问，提供完整的业务功能
    """
    
    _instance = None
    
    def __new__(cls, db_manager=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_manager=None):
        if self._initialized:
            return
        
        if db_manager is None:
            # 尝试从全局获取
            from web.app import components
            db_manager = components.get('db_manager')
        
        self.db_manager = db_manager
        
        # 初始化 Repository
        if db_manager:
            self.fund_repo = FundRepository(db_manager)
            self.holdings_repo = HoldingsRepository(db_manager)
            self.analysis_repo = AnalysisRepository(db_manager)
        else:
            self.fund_repo = None
            self.holdings_repo = None
            self.analysis_repo = None
        
        self.logger = logging.getLogger(__name__)
        self._initialized = True
        
        self.logger.info("基金业务服务初始化完成")
    
    def get_fund_detail(
        self,
        fund_code: str,
        include_history: bool = False,
        days: int = 30
    ) -> FundDetailDTO:
        """
        获取基金完整详情
        
        Args:
            fund_code: 基金代码
            include_history: 是否包含净值历史
            days: 历史数据天数
            
        Returns:
            FundDetailDTO: 基金详情
        """
        dto = FundDetailDTO(fund_code=fund_code)
        
        # 1. 获取基本信息（从数据库或API）
        if self.fund_repo:
            dto.basic_info = self.fund_repo.get_by_code(fund_code)
        
        if not dto.basic_info:
            # 从 API 获取
            dto.basic_info = fund_data_service.get_fund_basic_info(fund_code)
        
        dto.fund_name = dto.basic_info.get('fund_name') if dto.basic_info else None
        
        # 2. 获取实时数据
        realtime = fund_data_service.get_realtime_data(fund_code)
        dto.realtime_data = {
            'current_nav': realtime.current_nav,
            'daily_return': realtime.daily_return,
            'estimate_nav': realtime.estimate_nav,
            'data_source': realtime.data_source
        }
        
        # 3. 获取分析数据（从数据库）
        if self.analysis_repo:
            dto.analysis_data = self.fund_repo.get_latest_analysis(fund_code)
        
        # 4. 获取绩效指标
        if self.fund_repo:
            dto.performance_metrics = self.fund_repo.get_performance_metrics(fund_code)
        
        # 5. 获取净值历史（如果需要）
        if include_history:
            dto.nav_history = fund_data_service.get_fund_nav_history(fund_code, days)
        
        return dto
    
    def get_user_holdings_detail(
        self,
        user_id: str = 'default_user'
    ) -> List[HoldingDetailDTO]:
        """
        获取用户持仓详情（包含实时计算）
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[HoldingDetailDTO]: 持仓详情列表
        """
        if not self.holdings_repo:
            self.logger.error("持仓 Repository 未初始化")
            return []
        
        # 获取持仓数据
        holdings_df = self.holdings_repo.get_user_holdings(user_id)
        
        if holdings_df.empty:
            return []
        
        result = []
        
        for _, row in holdings_df.iterrows():
            holding = HoldingDetailDTO(
                holding_id=row.get('id', 0),
                fund_code=row['fund_code'],
                fund_name=row['fund_name'],
                holding_shares=float(row['holding_shares']),
                cost_price=float(row['cost_price']),
                holding_amount=float(row['holding_amount'])
            )
            
            # 获取实时数据
            realtime = fund_data_service.get_realtime_data(holding.fund_code)
            holding.current_nav = realtime.current_nav
            
            # 计算当前市值
            if holding.current_nav:
                holding.current_value = holding.holding_shares * holding.current_nav
                
                # 计算持仓盈亏
                holding.holding_profit = holding.current_value - holding.holding_amount
                holding.holding_profit_rate = (
                    (holding.holding_profit / holding.holding_amount * 100)
                    if holding.holding_amount > 0 else 0
                )
            
            # 当日收益
            holding.today_return = realtime.daily_return
            
            result.append(holding)
        
        return result
    
    def search_funds(self, keyword: str, limit: int = 20) -> pd.DataFrame:
        """
        搜索基金
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            DataFrame: 搜索结果
        """
        if self.fund_repo:
            return self.fund_repo.search_by_name(keyword, limit)
        
        # 如果没有 Repository，返回空
        return pd.DataFrame()
    
    def get_portfolio_summary(self, user_id: str = 'default_user') -> Dict[str, Any]:
        """
        获取投资组合汇总
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 汇总信息
        """
        if not self.holdings_repo:
            return {}
        
        # 获取持仓汇总
        summary = self.holdings_repo.get_holding_summary(user_id)
        
        # 获取持仓详情并计算总市值
        holdings = self.get_user_holdings_detail(user_id)
        
        total_current_value = sum(
            h.current_value for h in holdings if h.current_value
        )
        
        total_holding_profit = sum(
            h.holding_profit for h in holdings if h.holding_profit
        )
        
        total_today_profit = sum(
            (h.current_value * h.today_return / 100)
            for h in holdings if h.current_value and h.today_return
        )
        
        return {
            'fund_count': summary.get('fund_count', 0),
            'total_cost': summary.get('total_amount', 0),
            'total_current_value': total_current_value,
            'total_holding_profit': total_holding_profit,
            'total_holding_profit_rate': (
                (total_holding_profit / summary['total_amount'] * 100)
                if summary.get('total_amount', 0) > 0 else 0
            ),
            'total_today_profit': total_today_profit,
            'holdings': holdings
        }
    
    def refresh_analysis_data(
        self,
        fund_codes: List[str],
        user_id: str = 'default_user'
    ) -> Dict[str, Any]:
        """
        刷新基金分析数据
        
        Args:
            fund_codes: 基金代码列表
            user_id: 用户ID
            
        Returns:
            Dict: 刷新结果统计
        """
        if not self.fund_repo:
            return {'success': 0, 'failed': 0}
        
        success_count = 0
        failed_count = 0
        
        for fund_code in fund_codes:
            try:
                # 获取最新数据
                detail = self.get_fund_detail(fund_code)
                
                # 保存到数据库
                if detail.analysis_data:
                    self.fund_repo.save_analysis_result(
                        fund_code,
                        detail.fund_name or fund_code,
                        detail.analysis_data,
                        user_id
                    )
                    success_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                self.logger.error(f"刷新 {fund_code} 数据失败: {e}")
                failed_count += 1
        
        return {
            'success': success_count,
            'failed': failed_count,
            'total': len(fund_codes)
        }


# 全局业务服务实例
fund_business_service = FundBusinessService()
