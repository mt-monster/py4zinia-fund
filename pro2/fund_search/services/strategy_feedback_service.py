#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略反馈服务层

提供用户反馈管理、策略表现记录和学习机制的核心服务。

主要功能：
    1. 用户反馈管理：提交、查询、统计用户反馈
    2. 策略表现记录：记录预测与实际表现的对比
    3. 学习机制：根据反馈和表现动态调整策略权重
    4. 有效性分析：计算策略的综合有效性得分

使用示例：
    >>> from services.strategy_feedback_service import StrategyFeedbackService
    >>> service = StrategyFeedbackService()
    >>> 
    >>> # 提交用户反馈
    >>> service.submit_feedback(
    ...     fund_code='000001',
    ...     strategy_type='enhanced_rule_based',
    ...     rating=5,
    ...     comment='策略推荐很准确'
    ... )
    >>> 
    >>> # 获取策略统计
    >>> stats = service.get_feedback_stats('enhanced_rule_based')
    >>> 
    >>> # 记录策略表现
    >>> service.record_performance(
    ...     fund_code='000001',
    ...     strategy_type='enhanced_rule_based',
    ...     predicted_action='buy',
    ...     actual_return=5.2
    ... )
    >>> 
    >>> # 获取策略有效性分析
    >>> effectiveness = service.get_strategy_effectiveness()

作者：AI Assistant
创建日期：2026-02-12
"""

from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
import logging
import json
import math

import pandas as pd
import numpy as np

# 尝试导入数据库管理器
try:
    from data_access.enhanced_database import EnhancedDatabaseManager
except ImportError:
    EnhancedDatabaseManager = None

# 设置日志
logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """反馈类型枚举"""
    ACCURACY = 'accuracy'      # 准确性
    USEFULNESS = 'usefulness'  # 有用性
    OVERALL = 'overall'        # 综合评价


class PredictionAction(Enum):
    """预测操作类型枚举"""
    BUY = 'buy'
    SELL = 'sell'
    HOLD = 'hold'


class PerformanceStatus(Enum):
    """表现记录状态枚举"""
    PENDING = 'pending'
    COMPLETED = 'completed'
    EXPIRED = 'expired'


@dataclass
class StrategyFeedbackDTO:
    """策略反馈数据传输对象"""
    id: Optional[int] = None
    fund_code: str = ''
    fund_name: Optional[str] = None
    strategy_type: str = ''
    strategy_name: Optional[str] = None
    match_score: Optional[float] = None
    user_id: str = 'default_user'
    user_rating: Optional[int] = None
    user_comment: Optional[str] = None
    feedback_type: str = 'overall'
    is_helpful: Optional[bool] = None
    would_recommend: Optional[bool] = None
    feedback_date: date = field(default_factory=date.today)
    created_at: Optional[datetime] = None


@dataclass
class StrategyPerformanceDTO:
    """策略表现数据传输对象"""
    id: Optional[int] = None
    fund_code: str = ''
    strategy_type: str = ''
    predicted_action: str = ''
    predicted_confidence: Optional[float] = None
    actual_return: Optional[float] = None
    benchmark_return: Optional[float] = None
    excess_return: Optional[float] = None
    prediction_accuracy: Optional[float] = None
    profit_loss: Optional[float] = None
    prediction_date: date = field(default_factory=date.today)
    evaluation_date: Optional[date] = None
    status: str = 'pending'
    market_condition: Optional[str] = None


@dataclass
class StrategyWeightDTO:
    """策略权重数据传输对象"""
    strategy_type: str = ''
    strategy_name: str = ''
    base_weight: float = 1.0
    dynamic_weight: float = 1.0
    effectiveness_score: float = 50.0
    feedback_count: int = 0
    avg_user_rating: float = 0.0
    success_rate: float = 0.0
    learning_rate: float = 0.1


@dataclass
class FeedbackStatsDTO:
    """反馈统计数据传输对象"""
    strategy_type: str = ''
    total_feedback: int = 0
    avg_rating: float = 0.0
    rating_distribution: Dict[int, int] = field(default_factory=dict)
    helpful_rate: float = 0.0
    recent_trend: str = 'stable'  # improving/declining/stable
    period_days: int = 30


class StrategyFeedbackService:
    """
    策略反馈服务类
    
    提供完整的策略反馈管理功能，包括：
    - 用户反馈的提交和查询
    - 策略表现的记录和评估
    - 基于反馈的权重学习调整
    - 策略有效性分析
    
    Attributes:
        db_manager: 数据库管理器实例
        _initialized: 是否已初始化
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls, db_manager=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db_manager=None):
        """
        初始化策略反馈服务
        
        Args:
            db_manager: 数据库管理器实例，如果为None则尝试从全局获取
        """
        if self._initialized:
            return
            
        self.logger = logging.getLogger(__name__)
        
        # 获取数据库管理器
        if db_manager is None:
            db_manager = self._get_db_manager_from_global()
        
        self.db_manager = db_manager
        
        # 学习参数配置
        self.learning_config = {
            'feedback_weight': 0.4,      # 反馈在权重调整中的占比
            'performance_weight': 0.4,   # 表现在权重调整中的占比
            'momentum_weight': 0.2,      # 历史动量占比
            'min_feedback_count': 5,     # 最小反馈数才开始调整
            'weight_bounds': (0.1, 3.0), # 权重调整范围
            'learning_rate_decay': 0.99  # 学习率衰减
        }
        
        self._initialized = True
        self.logger.info("策略反馈服务初始化完成")
    
    def _get_db_manager_from_global(self) -> Optional[Any]:
        """
        从全局获取数据库管理器
        
        Returns:
            Optional[Any]: 数据库管理器实例或None
        """
        try:
            from web.app import components
            return components.get('db_manager')
        except ImportError:
            self.logger.warning("无法从全局获取数据库管理器")
            return None
    
    def _ensure_db_manager(self) -> bool:
        """
        确保数据库管理器可用
        
        Returns:
            bool: 是否可用
        """
        if self.db_manager is None:
            self.logger.error("数据库管理器未初始化")
            return False
        return True
    
    # ==================== 用户反馈管理 ====================
    
    def submit_feedback(
        self,
        fund_code: str,
        strategy_type: str,
        rating: int,
        comment: Optional[str] = None,
        user_id: str = 'default_user',
        fund_name: Optional[str] = None,
        strategy_name: Optional[str] = None,
        match_score: Optional[float] = None,
        is_helpful: Optional[bool] = None,
        feedback_type: str = 'overall'
    ) -> Dict[str, Any]:
        """
        提交用户反馈
        
        记录用户对特定基金策略匹配的评分和评论。
        
        Args:
            fund_code: 基金代码
            strategy_type: 策略类型标识
            rating: 用户评分(1-5星)
            comment: 用户评论（可选）
            user_id: 用户ID（默认'default_user'）
            fund_name: 基金名称（可选，用于冗余存储）
            strategy_name: 策略名称（可选，用于冗余存储）
            match_score: 系统匹配得分（可选）
            is_helpful: 是否有帮助（可选）
            feedback_type: 反馈类型，默认为'overall'
            
        Returns:
            Dict: 包含操作结果的字典
            {
                'success': bool,
                'feedback_id': int,
                'message': str,
                'weight_updated': bool
            }
            
        Raises:
            ValueError: 参数验证失败时
            
        Example:
            >>> result = service.submit_feedback(
            ...     fund_code='000001',
            ...     strategy_type='enhanced_rule_based',
            ...     rating=5,
            ...     comment='非常准确的策略推荐'
            ... )
        """
        # 参数验证
        if not fund_code or not strategy_type:
            raise ValueError("基金代码和策略类型不能为空")
        
        if not 1 <= rating <= 5:
            raise ValueError("评分必须在1-5之间")
        
        if not self._ensure_db_manager():
            return {'success': False, 'error': '数据库未初始化'}
        
        try:
            today = date.today()
            
            # 检查是否已有今日反馈
            check_sql = """
                SELECT id FROM strategy_feedback 
                WHERE fund_code = %s AND strategy_type = %s 
                AND user_id = %s AND feedback_date = %s
            """
            existing = self.db_manager.execute_query(
                check_sql, (fund_code, strategy_type, user_id, today)
            )
            
            if not existing.empty:
                # 更新现有反馈
                feedback_id = existing.iloc[0]['id']
                update_sql = """
                    UPDATE strategy_feedback 
                    SET user_rating = %s, user_comment = %s, is_helpful = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """
                self.db_manager.execute_update(
                    update_sql, (rating, comment, is_helpful, feedback_id)
                )
                message = "反馈更新成功"
            else:
                # 插入新反馈
                insert_sql = """
                    INSERT INTO strategy_feedback 
                    (fund_code, fund_name, strategy_type, strategy_name, match_score,
                     user_id, user_rating, user_comment, feedback_type, is_helpful,
                     feedback_date, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """
                feedback_id = self.db_manager.execute_insert(
                    insert_sql,
                    (fund_code, fund_name, strategy_type, strategy_name, match_score,
                     user_id, rating, comment, feedback_type, is_helpful, today)
                )
                message = "反馈提交成功"
            
            # 触发权重更新
            weight_updated = self._update_strategy_weight_from_feedback(
                strategy_type, rating, feedback_id
            )
            
            return {
                'success': True,
                'feedback_id': feedback_id,
                'message': message,
                'weight_updated': weight_updated
            }
            
        except Exception as e:
            self.logger.error(f"提交反馈失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_feedback_by_fund(
        self,
        fund_code: str,
        strategy_type: Optional[str] = None,
        days: int = 30
    ) -> List[StrategyFeedbackDTO]:
        """
        获取特定基金的反馈列表
        
        Args:
            fund_code: 基金代码
            strategy_type: 策略类型过滤（可选）
            days: 最近多少天的反馈，默认30天
            
        Returns:
            List[StrategyFeedbackDTO]: 反馈列表
        """
        if not self._ensure_db_manager():
            return []
        
        try:
            since_date = date.today() - timedelta(days=days)
            
            if strategy_type:
                sql = """
                    SELECT * FROM strategy_feedback 
                    WHERE fund_code = %s AND strategy_type = %s 
                    AND feedback_date >= %s
                    ORDER BY feedback_date DESC
                """
                params = (fund_code, strategy_type, since_date)
            else:
                sql = """
                    SELECT * FROM strategy_feedback 
                    WHERE fund_code = %s AND feedback_date >= %s
                    ORDER BY feedback_date DESC
                """
                params = (fund_code, since_date)
            
            df = self.db_manager.execute_query(sql, params)
            
            if df.empty:
                return []
            
            return [self._row_to_feedback_dto(row) for _, row in df.iterrows()]
            
        except Exception as e:
            self.logger.error(f"获取反馈列表失败: {str(e)}")
            return []
    
    def get_feedback_stats(
        self,
        strategy_type: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取策略反馈统计信息
        
        计算指定策略或全局的反馈统计数据，包括平均分、分布、趋势等。
        
        Args:
            strategy_type: 策略类型，为None则返回全局统计
            days: 统计时间范围（天），默认30天
            
        Returns:
            Dict: 统计信息字典
            {
                'strategy_type': str,
                'period_days': int,
                'total_feedback': int,
                'avg_rating': float,
                'rating_distribution': {1: n1, 2: n2, ...},
                'helpful_rate': float,
                'recent_trend': str,  # improving/declining/stable
                'daily_stats': [...]
            }
            
        Example:
            >>> stats = service.get_feedback_stats('enhanced_rule_based', days=30)
            >>> print(f"平均评分: {stats['avg_rating']:.2f}")
        """
        if not self._ensure_db_manager():
            return {'error': '数据库未初始化'}
        
        try:
            since_date = date.today() - timedelta(days=days)
            
            # 基础统计查询
            where_clause = "feedback_date >= %s"
            params = [since_date]
            
            if strategy_type:
                where_clause += " AND strategy_type = %s"
                params.append(strategy_type)
            
            # 总体统计
            stats_sql = f"""
                SELECT 
                    COUNT(*) as total_feedback,
                    AVG(user_rating) as avg_rating,
                    COUNT(CASE WHEN is_helpful = TRUE THEN 1 END) as helpful_count,
                    COUNT(CASE WHEN is_helpful IS NOT NULL THEN 1 END) as total_helpful_responses
                FROM strategy_feedback
                WHERE {where_clause}
            """
            stats_df = self.db_manager.execute_query(stats_sql, tuple(params))
            
            # 评分分布
            dist_sql = f"""
                SELECT user_rating, COUNT(*) as count
                FROM strategy_feedback
                WHERE {where_clause} AND user_rating IS NOT NULL
                GROUP BY user_rating
                ORDER BY user_rating
            """
            dist_df = self.db_manager.execute_query(dist_sql, tuple(params))
            
            # 每日趋势
            daily_sql = f"""
                SELECT 
                    feedback_date,
                    COUNT(*) as count,
                    AVG(user_rating) as avg_rating
                FROM strategy_feedback
                WHERE {where_clause}
                GROUP BY feedback_date
                ORDER BY feedback_date
            """
            daily_df = self.db_manager.execute_query(daily_sql, tuple(params))
            
            # 组装结果
            total_feedback = int(stats_df.iloc[0]['total_feedback']) if not stats_df.empty else 0
            avg_rating = float(stats_df.iloc[0]['avg_rating']) if not stats_df.empty else 0.0
            
            helpful_count = int(stats_df.iloc[0]['helpful_count']) if not stats_df.empty else 0
            total_helpful = int(stats_df.iloc[0]['total_helpful_responses']) if not stats_df.empty else 0
            helpful_rate = (helpful_count / total_helpful * 100) if total_helpful > 0 else 0.0
            
            # 评分分布
            rating_distribution = {i: 0 for i in range(1, 6)}
            for _, row in dist_df.iterrows():
                rating = int(row['user_rating'])
                rating_distribution[rating] = int(row['count'])
            
            # 趋势判断（简单线性回归）
            trend = 'stable'
            if len(daily_df) >= 7:
                ratings = daily_df['avg_rating'].values
                x = np.arange(len(ratings))
                slope = np.polyfit(x, ratings, 1)[0] if len(x) > 1 else 0
                
                if slope > 0.05:
                    trend = 'improving'
                elif slope < -0.05:
                    trend = 'declining'
            
            return {
                'strategy_type': strategy_type or 'all',
                'period_days': days,
                'total_feedback': total_feedback,
                'avg_rating': round(avg_rating, 2),
                'rating_distribution': rating_distribution,
                'helpful_rate': round(helpful_rate, 2),
                'recent_trend': trend,
                'daily_stats': [
                    {
                        'date': str(row['feedback_date']),
                        'count': int(row['count']),
                        'avg_rating': round(float(row['avg_rating']), 2)
                    }
                    for _, row in daily_df.iterrows()
                ]
            }
            
        except Exception as e:
            self.logger.error(f"获取反馈统计失败: {str(e)}")
            return {'error': str(e)}
    
    # ==================== 策略表现记录 ====================
    
    def record_performance(
        self,
        fund_code: str,
        strategy_type: str,
        predicted_action: str,
        actual_return: Optional[float] = None,
        predicted_confidence: Optional[float] = None,
        suggested_amount: Optional[float] = None,
        benchmark_return: Optional[float] = None,
        prediction_date: Optional[date] = None,
        market_condition: Optional[str] = None,
        evaluation_date: Optional[date] = None,
        holding_days: int = 1
    ) -> Dict[str, Any]:
        """
        记录策略表现
        
        记录策略预测与实际表现的对比数据，用于后续分析和权重调整。
        
        Args:
            fund_code: 基金代码
            strategy_type: 策略类型标识
            predicted_action: 预测操作（buy/sell/hold）
            actual_return: 实际收益率(%)，可选
            predicted_confidence: 预测置信度(0-100)，可选
            suggested_amount: 建议金额，可选
            benchmark_return: 基准收益率(%)，可选
            prediction_date: 预测日期，默认为今天
            market_condition: 市场环境（bull/bear/sideways），可选
            evaluation_date: 评估日期，可选
            holding_days: 持仓天数，默认1天
            
        Returns:
            Dict: 操作结果
            {
                'success': bool,
                'performance_id': int,
                'excess_return': float,
                'prediction_accuracy': float,
                'message': str
            }
            
        Example:
            >>> result = service.record_performance(
            ...     fund_code='000001',
            ...     strategy_type='enhanced_rule_based',
            ...     predicted_action='buy',
            ...     actual_return=5.2,
            ...     benchmark_return=3.0
            ... )
        """
        if not self._ensure_db_manager():
            return {'success': False, 'error': '数据库未初始化'}
        
        try:
            pred_date = prediction_date or date.today()
            
            # 计算超额收益
            excess_return = None
            if actual_return is not None and benchmark_return is not None:
                excess_return = actual_return - benchmark_return
            
            # 计算预测准确度
            accuracy = self._calculate_prediction_accuracy(
                predicted_action, actual_return, predicted_confidence
            )
            
            # 检查是否已存在
            check_sql = """
                SELECT id FROM strategy_performance 
                WHERE fund_code = %s AND strategy_type = %s AND prediction_date = %s
            """
            existing = self.db_manager.execute_query(
                check_sql, (fund_code, strategy_type, pred_date)
            )
            
            if not existing.empty:
                # 更新
                perf_id = existing.iloc[0]['id']
                update_sql = """
                    UPDATE strategy_performance 
                    SET predicted_action = %s, actual_return = %s,
                        benchmark_return = %s, excess_return = %s,
                        prediction_accuracy = %s, evaluation_date = %s,
                        status = %s, updated_at = NOW()
                    WHERE id = %s
                """
                status = 'completed' if actual_return is not None else 'pending'
                self.db_manager.execute_update(
                    update_sql,
                    (predicted_action, actual_return, benchmark_return,
                     excess_return, accuracy, evaluation_date, status, perf_id)
                )
                message = "表现记录更新成功"
            else:
                # 插入
                status = 'completed' if actual_return is not None else 'pending'
                insert_sql = """
                    INSERT INTO strategy_performance 
                    (fund_code, strategy_type, predicted_action, predicted_confidence,
                     suggested_amount, actual_return, benchmark_return, excess_return,
                     prediction_accuracy, prediction_date, evaluation_date, 
                     holding_days, status, market_condition, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """
                perf_id = self.db_manager.execute_insert(
                    insert_sql,
                    (fund_code, strategy_type, predicted_action, predicted_confidence,
                     suggested_amount, actual_return, benchmark_return, excess_return,
                     accuracy, pred_date, evaluation_date, holding_days, 
                     status, market_condition)
                )
                message = "表现记录创建成功"
            
            # 触发权重更新
            if actual_return is not None:
                self._update_strategy_weight_from_performance(strategy_type, accuracy, perf_id)
            
            return {
                'success': True,
                'performance_id': perf_id,
                'excess_return': excess_return,
                'prediction_accuracy': accuracy,
                'message': message
            }
            
        except Exception as e:
            self.logger.error(f"记录策略表现失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def update_performance_result(
        self,
        performance_id: int,
        actual_return: float,
        benchmark_return: Optional[float] = None,
        evaluation_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        更新策略表现的实际结果
        
        用于在预测后一段时间补充实际收益数据。
        
        Args:
            performance_id: 表现记录ID
            actual_return: 实际收益率(%)
            benchmark_return: 基准收益率(%)，可选
            evaluation_date: 评估日期，可选
            
        Returns:
            Dict: 更新结果
        """
        if not self._ensure_db_manager():
            return {'success': False, 'error': '数据库未初始化'}
        
        try:
            # 获取原记录
            select_sql = """
                SELECT predicted_action, strategy_type, predicted_confidence
                FROM strategy_performance WHERE id = %s
            """
            df = self.db_manager.execute_query(select_sql, (performance_id,))
            
            if df.empty:
                return {'success': False, 'error': '记录不存在'}
            
            predicted_action = df.iloc[0]['predicted_action']
            strategy_type = df.iloc[0]['strategy_type']
            confidence = df.iloc[0]['predicted_confidence']
            
            # 计算指标
            excess_return = None
            if benchmark_return is not None:
                excess_return = actual_return - benchmark_return
            
            accuracy = self._calculate_prediction_accuracy(
                predicted_action, actual_return, confidence
            )
            
            eval_date = evaluation_date or date.today()
            
            # 更新
            update_sql = """
                UPDATE strategy_performance 
                SET actual_return = %s, benchmark_return = %s, 
                    excess_return = %s, prediction_accuracy = %s,
                    evaluation_date = %s, status = 'completed',
                    updated_at = NOW()
                WHERE id = %s
            """
            self.db_manager.execute_update(
                update_sql,
                (actual_return, benchmark_return, excess_return, 
                 accuracy, eval_date, performance_id)
            )
            
            # 触发权重更新
            self._update_strategy_weight_from_performance(strategy_type, accuracy, performance_id)
            
            return {
                'success': True,
                'excess_return': excess_return,
                'prediction_accuracy': accuracy,
                'message': '表现结果更新成功'
            }
            
        except Exception as e:
            self.logger.error(f"更新表现结果失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_pending_evaluations(self, days: int = 7) -> List[StrategyPerformanceDTO]:
        """
        获取待评估的表现记录
        
        获取预测后经过一段时间需要补充实际数据的记录。
        
        Args:
            days: 预测后多少天的记录，默认7天
            
        Returns:
            List[StrategyPerformanceDTO]: 待评估记录列表
        """
        if not self._ensure_db_manager():
            return []
        
        try:
            target_date = date.today() - timedelta(days=days)
            
            sql = """
                SELECT * FROM strategy_performance 
                WHERE status = 'pending' 
                AND prediction_date <= %s
                ORDER BY prediction_date
            """
            df = self.db_manager.execute_query(sql, (target_date,))
            
            return [self._row_to_performance_dto(row) for _, row in df.iterrows()]
            
        except Exception as e:
            self.logger.error(f"获取待评估记录失败: {str(e)}")
            return []
    
    # ==================== 学习机制 ====================
    
    def _update_strategy_weight_from_feedback(
        self, 
        strategy_type: str, 
        rating: int,
        feedback_id: int
    ) -> bool:
        """
        根据用户反馈更新策略权重
        
        内部方法，由submit_feedback触发。
        
        Args:
            strategy_type: 策略类型
            rating: 用户评分
            feedback_id: 反馈ID
            
        Returns:
            bool: 是否成功更新
        """
        try:
            # 获取当前权重
            weight_sql = """
                SELECT dynamic_weight, feedback_count, avg_user_rating, learning_rate
                FROM strategy_weights WHERE strategy_type = %s
            """
            df = self.db_manager.execute_query(weight_sql, (strategy_type,))
            
            if df.empty:
                self.logger.warning(f"策略 {strategy_type} 不存在于权重表")
                return False
            
            current_weight = float(df.iloc[0]['dynamic_weight'])
            feedback_count = int(df.iloc[0]['feedback_count'])
            avg_rating = float(df.iloc[0]['avg_user_rating'] or 0)
            learning_rate = float(df.iloc[0]['learning_rate'])
            
            # 计算调整量
            # 评分映射到调整：3分=0，5分=+0.2，1分=-0.2
            rating_adjustment = (rating - 3) * 0.1
            
            # 新权重 = 旧权重 + 学习率 * 调整量
            new_weight = current_weight + learning_rate * rating_adjustment
            
            # 边界限制
            min_w, max_w = self.learning_config['weight_bounds']
            new_weight = max(min_w, min(max_w, new_weight))
            
            # 更新平均评分
            new_avg_rating = (avg_rating * feedback_count + rating) / (feedback_count + 1)
            
            # 更新权重表
            update_sql = """
                UPDATE strategy_weights 
                SET dynamic_weight = %s, 
                    weight_adjustment = %s - base_weight,
                    feedback_count = feedback_count + 1,
                    avg_user_rating = %s,
                    last_updated = %s
                WHERE strategy_type = %s
            """
            self.db_manager.execute_update(
                update_sql, (new_weight, new_weight, new_avg_rating, date.today(), strategy_type)
            )
            
            # 记录学习日志
            self._log_weight_adjustment(
                strategy_type, 'feedback', current_weight, new_weight,
                feedback_id=feedback_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"更新权重失败: {str(e)}")
            return False
    
    def _update_strategy_weight_from_performance(
        self,
        strategy_type: str,
        accuracy: Optional[float],
        performance_id: int
    ) -> bool:
        """
        根据策略表现更新权重
        
        内部方法，由record_performance触发。
        
        Args:
            strategy_type: 策略类型
            accuracy: 预测准确度
            performance_id: 表现记录ID
            
        Returns:
            bool: 是否成功更新
        """
        if accuracy is None:
            return False
        
        try:
            # 获取当前权重
            weight_sql = """
                SELECT dynamic_weight, total_predictions, accurate_predictions, learning_rate
                FROM strategy_weights WHERE strategy_type = %s
            """
            df = self.db_manager.execute_query(weight_sql, (strategy_type,))
            
            if df.empty:
                return False
            
            current_weight = float(df.iloc[0]['dynamic_weight'])
            total_pred = int(df.iloc[0]['total_predictions'])
            accurate_pred = int(df.iloc[0]['accurate_predictions'])
            learning_rate = float(df.iloc[0]['learning_rate'])
            
            # 根据准确度调整
            # 准确度>70%增加权重，<50%减少权重
            if accuracy >= 70:
                adjustment = 0.05
            elif accuracy >= 50:
                adjustment = 0
            else:
                adjustment = -0.05
            
            new_weight = current_weight + learning_rate * adjustment
            
            # 边界限制
            min_w, max_w = self.learning_config['weight_bounds']
            new_weight = max(min_w, min(max_w, new_weight))
            
            # 更新成功率
            new_total = total_pred + 1
            new_accurate = accurate_pred + (1 if accuracy >= 70 else 0)
            new_success_rate = (new_accurate / new_total * 100) if new_total > 0 else 0
            
            # 更新权重表
            update_sql = """
                UPDATE strategy_weights 
                SET dynamic_weight = %s,
                    weight_adjustment = %s - base_weight,
                    total_predictions = %s,
                    accurate_predictions = %s,
                    success_rate = %s,
                    last_updated = %s
                WHERE strategy_type = %s
            """
            self.db_manager.execute_update(
                update_sql,
                (new_weight, new_weight, new_total, new_accurate, 
                 new_success_rate, date.today(), strategy_type)
            )
            
            # 记录学习日志
            self._log_weight_adjustment(
                strategy_type, 'performance', current_weight, new_weight,
                performance_id=performance_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"更新权重失败: {str(e)}")
            return False
    
    def _log_weight_adjustment(
        self,
        strategy_type: str,
        adjustment_type: str,
        old_weight: float,
        new_weight: float,
        feedback_id: Optional[int] = None,
        performance_id: Optional[int] = None,
        triggered_by: str = 'system'
    ) -> None:
        """
        记录权重调整日志
        
        Args:
            strategy_type: 策略类型
            adjustment_type: 调整类型
            old_weight: 调整前权重
            new_weight: 调整后权重
            feedback_id: 关联的反馈ID
            performance_id: 关联的表现记录ID
            triggered_by: 触发者
        """
        try:
            sql = """
                INSERT INTO strategy_learning_log 
                (strategy_type, adjustment_type, old_weight, new_weight, 
                 change_amount, feedback_id, performance_id, triggered_by, change_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            change = new_weight - old_weight
            reason = f"{adjustment_type} triggered weight adjustment"
            
            self.db_manager.execute_insert(
                sql,
                (strategy_type, adjustment_type, old_weight, new_weight,
                 change, feedback_id, performance_id, triggered_by, reason)
            )
        except Exception as e:
            self.logger.warning(f"记录学习日志失败: {str(e)}")
    
    def recalculate_all_weights(self) -> Dict[str, Any]:
        """
        重新计算所有策略权重
        
        基于所有历史反馈和表现数据重新计算策略权重。
        
        Returns:
            Dict: 包含各策略新旧权重的字典
        """
        if not self._ensure_db_manager():
            return {'error': '数据库未初始化'}
        
        try:
            # 获取所有策略
            strategies_sql = "SELECT strategy_type, base_weight FROM strategy_weights"
            strategies_df = self.db_manager.execute_query(strategies_sql)
            
            results = []
            
            for _, row in strategies_df.iterrows():
                strategy_type = row['strategy_type']
                base_weight = float(row['base_weight'])
                
                # 计算反馈得分
                feedback_sql = """
                    SELECT AVG(user_rating) as avg_rating, COUNT(*) as count
                    FROM strategy_feedback
                    WHERE strategy_type = %s
                """
                feedback_df = self.db_manager.execute_query(feedback_sql, (strategy_type,))
                
                avg_rating = float(feedback_df.iloc[0]['avg_rating'] or 3.0)
                feedback_count = int(feedback_df.iloc[0]['count'])
                
                # 计算表现得分
                perf_sql = """
                    SELECT AVG(prediction_accuracy) as avg_accuracy, COUNT(*) as count
                    FROM strategy_performance
                    WHERE strategy_type = %s AND status = 'completed'
                """
                perf_df = self.db_manager.execute_query(perf_sql, (strategy_type,))
                
                avg_accuracy = float(perf_df.iloc[0]['avg_accuracy'] or 50.0)
                perf_count = int(perf_df.iloc[0]['count'])
                
                # 综合计算新权重
                # 评分转换为得分：1-5分映射到0.5-1.5倍权重
                rating_factor = 0.5 + (avg_rating - 1) * 0.25
                
                # 准确度转换为得分：0-100%映射到0.5-1.5倍权重
                accuracy_factor = 0.5 + (avg_accuracy / 100)
                
                # 综合权重
                new_weight = base_weight * (rating_factor * 0.4 + accuracy_factor * 0.6)
                
                # 边界限制
                min_w, max_w = self.learning_config['weight_bounds']
                new_weight = max(min_w, min(max_w, new_weight))
                
                # 获取旧权重
                old_weight_sql = """
                    SELECT dynamic_weight FROM strategy_weights WHERE strategy_type = %s
                """
                old_weight_df = self.db_manager.execute_query(old_weight_sql, (strategy_type,))
                old_weight = float(old_weight_df.iloc[0]['dynamic_weight'])
                
                # 更新权重
                update_sql = """
                    UPDATE strategy_weights 
                    SET dynamic_weight = %s, 
                        weight_adjustment = %s - base_weight,
                        effectiveness_score = %s,
                        avg_user_rating = %s,
                        success_rate = %s,
                        feedback_count = %s,
                        total_predictions = %s,
                        last_updated = %s
                    WHERE strategy_type = %s
                """
                effectiveness = (avg_rating * 20 + avg_accuracy) / 2
                self.db_manager.execute_update(
                    update_sql,
                    (new_weight, new_weight, effectiveness, avg_rating,
                     avg_accuracy, feedback_count, perf_count, date.today(), strategy_type)
                )
                
                results.append({
                    'strategy_type': strategy_type,
                    'old_weight': round(old_weight, 2),
                    'new_weight': round(new_weight, 2),
                    'feedback_count': feedback_count,
                    'avg_rating': round(avg_rating, 2),
                    'avg_accuracy': round(avg_accuracy, 2)
                })
            
            return {
                'success': True,
                'updated_count': len(results),
                'strategies': results
            }
            
        except Exception as e:
            self.logger.error(f"重新计算权重失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # ==================== 策略有效性分析 ====================
    
    def get_strategy_effectiveness(
        self,
        strategy_type: Optional[str] = None,
        days: int = 90
    ) -> Dict[str, Any]:
        """
        获取策略有效性分析
        
        综合分析策略的反馈评分、预测准确度、成功率等指标，
        计算策略的综合有效性得分。
        
        Args:
            strategy_type: 策略类型，为None则返回所有策略
            days: 分析时间范围（天），默认90天
            
        Returns:
            Dict: 策略有效性分析结果
            {
                'strategy_type': str,
                'effectiveness_score': float,  # 综合得分(0-100)
                'components': {
                    'feedback_score': float,      # 反馈得分(0-100)
                    'accuracy_score': float,      # 准确度得分(0-100)
                    'success_rate': float,        # 成功率(%)
                    'consistency_score': float    # 稳定性得分(0-100)
                },
                'statistics': {
                    'total_feedback': int,
                    'avg_rating': float,
                    'total_predictions': int,
                    'completed_evaluations': int
                },
                'ranking': int,  # 在所有策略中的排名
                'recommendation': str  # 推荐等级：high/medium/low
            }
            
        Example:
            >>> effectiveness = service.get_strategy_effectiveness('enhanced_rule_based')
            >>> print(f"有效性得分: {effectiveness['effectiveness_score']:.1f}")
        """
        if not self._ensure_db_manager():
            return {'error': '数据库未初始化'}
        
        try:
            since_date = date.today() - timedelta(days=days)
            
            if strategy_type:
                # 查询特定策略
                sql = """
                    SELECT * FROM v_strategy_effectiveness 
                    WHERE strategy_type = %s
                """
                df = self.db_manager.execute_query(sql, (strategy_type,))
                
                if df.empty:
                    return {'error': f'策略 {strategy_type} 不存在'}
                
                return self._calculate_effectiveness_detail(df.iloc[0], since_date)
            else:
                # 查询所有策略并排序
                sql = "SELECT * FROM v_strategy_effectiveness ORDER BY composite_score DESC"
                df = self.db_manager.execute_query(sql)
                
                results = []
                for idx, row in df.iterrows():
                    detail = self._calculate_effectiveness_detail(row, since_date)
                    detail['ranking'] = idx + 1
                    results.append(detail)
                
                return {
                    'strategies': results,
                    'total_count': len(results),
                    'top_strategy': results[0] if results else None,
                    'analysis_period_days': days
                }
                
        except Exception as e:
            self.logger.error(f"获取策略有效性失败: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_effectiveness_detail(
        self, 
        row: pd.Series,
        since_date: date
    ) -> Dict[str, Any]:
        """
        计算策略有效性详情
        
        Args:
            row: 策略数据行
            since_date: 统计起始日期
            
        Returns:
            Dict: 有效性详情
        """
        strategy_type = row['strategy_type']
        
        # 获取近期详细统计
        feedback_sql = """
            SELECT 
                COUNT(*) as count,
                AVG(user_rating) as avg_rating,
                STDDEV(user_rating) as std_rating
            FROM strategy_feedback
            WHERE strategy_type = %s AND feedback_date >= %s
        """
        feedback_df = self.db_manager.execute_query(
            feedback_sql, (strategy_type, since_date)
        )
        
        perf_sql = """
            SELECT 
                COUNT(*) as total,
                AVG(prediction_accuracy) as avg_accuracy,
                STDDEV(prediction_accuracy) as std_accuracy,
                COUNT(CASE WHEN prediction_accuracy >= 70 THEN 1 END) as accurate_count
            FROM strategy_performance
            WHERE strategy_type = %s AND prediction_date >= %s AND status = 'completed'
        """
        perf_df = self.db_manager.execute_query(perf_sql, (strategy_type, since_date))
        
        # 计算各维度得分
        avg_rating = float(feedback_df.iloc[0]['avg_rating'] or 0)
        rating_std = float(feedback_df.iloc[0]['std_rating'] or 0)
        feedback_count = int(feedback_df.iloc[0]['count'] or 0)
        
        avg_accuracy = float(perf_df.iloc[0]['avg_accuracy'] or 0)
        accuracy_std = float(perf_df.iloc[0]['std_accuracy'] or 0)
        total_pred = int(perf_df.iloc[0]['total'] or 0)
        accurate_count = int(perf_df.iloc[0]['accurate_count'] or 0)
        
        # 反馈得分：5星制转为百分制
        feedback_score = avg_rating * 20 if avg_rating > 0 else 0
        
        # 准确度得分
        accuracy_score = avg_accuracy
        
        # 成功率
        success_rate = (accurate_count / total_pred * 100) if total_pred > 0 else 0
        
        # 稳定性得分：基于标准差的反向得分
        consistency_score = 0
        if rating_std > 0 and accuracy_std > 0:
            consistency_score = 100 - (rating_std * 10 + accuracy_std * 0.5) / 2
            consistency_score = max(0, min(100, consistency_score))
        
        # 综合得分
        composite = (
            feedback_score * 0.3 +
            accuracy_score * 0.3 +
            success_rate * 0.25 +
            consistency_score * 0.15
        )
        
        # 推荐等级
        if composite >= 80:
            recommendation = 'high'
        elif composite >= 60:
            recommendation = 'medium'
        else:
            recommendation = 'low'
        
        return {
            'strategy_type': strategy_type,
            'strategy_name': row['strategy_name'],
            'effectiveness_score': round(composite, 2),
            'current_weight': round(float(row['dynamic_weight']), 2),
            'components': {
                'feedback_score': round(feedback_score, 2),
                'accuracy_score': round(accuracy_score, 2),
                'success_rate': round(success_rate, 2),
                'consistency_score': round(consistency_score, 2)
            },
            'statistics': {
                'total_feedback': feedback_count,
                'avg_rating': round(avg_rating, 2),
                'total_predictions': total_pred,
                'completed_evaluations': total_pred
            },
            'recommendation': recommendation,
            'analysis_period_days': (date.today() - since_date).days
        }
    
    def get_strategy_comparison(
        self,
        strategy_types: Optional[List[str]] = None,
        days: int = 90
    ) -> Dict[str, Any]:
        """
        获取多策略对比分析
        
        对比多个策略的有效性和表现指标。
        
        Args:
            strategy_types: 策略类型列表，为None则对比所有策略
            days: 分析时间范围（天）
            
        Returns:
            Dict: 对比分析结果
        """
        if not self._ensure_db_manager():
            return {'error': '数据库未初始化'}
        
        try:
            since_date = date.today() - timedelta(days=days)
            
            if strategy_types:
                placeholders = ', '.join(['%s'] * len(strategy_types))
                sql = f"""
                    SELECT * FROM v_strategy_effectiveness 
                    WHERE strategy_type IN ({placeholders})
                    ORDER BY composite_score DESC
                """
                df = self.db_manager.execute_query(sql, tuple(strategy_types))
            else:
                sql = "SELECT * FROM v_strategy_effectiveness ORDER BY composite_score DESC"
                df = self.db_manager.execute_query(sql)
            
            strategies = []
            for idx, row in df.iterrows():
                detail = self._calculate_effectiveness_detail(row, since_date)
                detail['ranking'] = idx + 1
                strategies.append(detail)
            
            # 计算对比指标
            if len(strategies) >= 2:
                scores = [s['effectiveness_score'] for s in strategies]
                avg_score = sum(scores) / len(scores)
                best_strategy = strategies[0]
                worst_strategy = strategies[-1]
                score_gap = best_strategy['effectiveness_score'] - worst_strategy['effectiveness_score']
            else:
                avg_score = strategies[0]['effectiveness_score'] if strategies else 0
                best_strategy = strategies[0] if strategies else None
                worst_strategy = None
                score_gap = 0
            
            return {
                'strategies': strategies,
                'comparison': {
                    'average_score': round(avg_score, 2),
                    'best_strategy': best_strategy,
                    'worst_strategy': worst_strategy,
                    'score_gap': round(score_gap, 2),
                    'analysis_period_days': days
                }
            }
            
        except Exception as e:
            self.logger.error(f"获取策略对比失败: {str(e)}")
            return {'error': str(e)}
    
    # ==================== 辅助方法 ====================
    
    def _calculate_prediction_accuracy(
        self,
        predicted_action: str,
        actual_return: Optional[float],
        confidence: Optional[float]
    ) -> Optional[float]:
        """
        计算预测准确度
        
        Args:
            predicted_action: 预测操作
            actual_return: 实际收益率
            confidence: 预测置信度
            
        Returns:
            Optional[float]: 准确度得分(0-100)或None
        """
        if actual_return is None:
            return None
        
        # 基础准确度：预测方向是否正确
        direction_correct = False
        if predicted_action == 'buy' and actual_return > 0:
            direction_correct = True
        elif predicted_action == 'sell' and actual_return < 0:
            direction_correct = True
        elif predicted_action == 'hold' and abs(actual_return) < 2:
            direction_correct = True
        
        # 基础分：方向正确60分，错误40分
        base_score = 60 if direction_correct else 40
        
        # 幅度加分：预测越准确分越高
        magnitude_bonus = 0
        if direction_correct:
            # 收益绝对值越大，加分越多（但不超过20分）
            magnitude_bonus = min(abs(actual_return) * 2, 20)
        
        # 置信度调整：如果置信度高但预测错误，扣分
        confidence_adjustment = 0
        if confidence is not None:
            if not direction_correct and confidence > 70:
                confidence_adjustment = -10
            elif direction_correct and confidence > 70:
                confidence_adjustment = 5
        
        accuracy = base_score + magnitude_bonus + confidence_adjustment
        return max(0, min(100, accuracy))
    
    def _row_to_feedback_dto(self, row: pd.Series) -> StrategyFeedbackDTO:
        """将数据行转换为反馈DTO"""
        return StrategyFeedbackDTO(
            id=row.get('id'),
            fund_code=row.get('fund_code', ''),
            fund_name=row.get('fund_name'),
            strategy_type=row.get('strategy_type', ''),
            strategy_name=row.get('strategy_name'),
            match_score=float(row['match_score']) if pd.notna(row.get('match_score')) else None,
            user_id=row.get('user_id', 'default_user'),
            user_rating=int(row['user_rating']) if pd.notna(row.get('user_rating')) else None,
            user_comment=row.get('user_comment'),
            feedback_type=row.get('feedback_type', 'overall'),
            is_helpful=bool(row['is_helpful']) if pd.notna(row.get('is_helpful')) else None,
            would_recommend=bool(row['would_recommend']) if pd.notna(row.get('would_recommend')) else None,
            feedback_date=row.get('feedback_date'),
            created_at=row.get('created_at')
        )
    
    def _row_to_performance_dto(self, row: pd.Series) -> StrategyPerformanceDTO:
        """将数据行转换为表现DTO"""
        return StrategyPerformanceDTO(
            id=row.get('id'),
            fund_code=row.get('fund_code', ''),
            strategy_type=row.get('strategy_type', ''),
            predicted_action=row.get('predicted_action', ''),
            predicted_confidence=float(row['predicted_confidence']) if pd.notna(row.get('predicted_confidence')) else None,
            actual_return=float(row['actual_return']) if pd.notna(row.get('actual_return')) else None,
            benchmark_return=float(row['benchmark_return']) if pd.notna(row.get('benchmark_return')) else None,
            excess_return=float(row['excess_return']) if pd.notna(row.get('excess_return')) else None,
            prediction_accuracy=float(row['prediction_accuracy']) if pd.notna(row.get('prediction_accuracy')) else None,
            profit_loss=float(row['profit_loss']) if pd.notna(row.get('profit_loss')) else None,
            prediction_date=row.get('prediction_date'),
            evaluation_date=row.get('evaluation_date'),
            status=row.get('status', 'pending'),
            market_condition=row.get('market_condition')
        )
    
    def get_learning_logs(
        self,
        strategy_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取策略学习日志
        
        Args:
            strategy_type: 策略类型过滤
            limit: 返回条数限制
            
        Returns:
            List[Dict]: 学习日志列表
        """
        if not self._ensure_db_manager():
            return []
        
        try:
            if strategy_type:
                sql = """
                    SELECT * FROM strategy_learning_log 
                    WHERE strategy_type = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                params = (strategy_type, limit)
            else:
                sql = """
                    SELECT * FROM strategy_learning_log 
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                params = (limit,)
            
            df = self.db_manager.execute_query(sql, params)
            
            return [
                {
                    'id': row['id'],
                    'strategy_type': row['strategy_type'],
                    'adjustment_type': row['adjustment_type'],
                    'old_weight': float(row['old_weight']),
                    'new_weight': float(row['new_weight']),
                    'change_amount': float(row['change_amount']),
                    'triggered_by': row['triggered_by'],
                    'change_reason': row['change_reason'],
                    'created_at': str(row['created_at'])
                }
                for _, row in df.iterrows()
            ]
            
        except Exception as e:
            self.logger.error(f"获取学习日志失败: {str(e)}")
            return []


# 全局服务实例
strategy_feedback_service = StrategyFeedbackService()
