#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略反馈系统 API 路由

提供策略反馈相关的 RESTful API 端点：
- 用户反馈提交和查询
- 策略表现记录
- 策略有效性分析
- 学习机制监控

API 端点列表：
    POST   /api/strategy/feedback              提交用户反馈
    GET    /api/strategy/feedback              获取反馈列表
    GET    /api/strategy/feedback/stats        获取反馈统计
    POST   /api/strategy/performance           记录策略表现
    GET    /api/strategy/performance/pending   获取待评估记录
    GET    /api/strategy/effectiveness         获取策略有效性分析
    GET    /api/strategy/comparison            策略对比分析
    POST   /api/strategy/recalculate           重新计算策略权重
    GET    /api/strategy/learning-logs         获取学习日志

作者：AI Assistant
创建日期：2026-02-12
"""

import os
import sys
import math
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List

from flask import Blueprint, jsonify, request, g

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.strategy_feedback_service import (
    StrategyFeedbackService, 
    strategy_feedback_service
)

# 设置日志
logger = logging.getLogger(__name__)

# 创建蓝图
strategy_feedback_bp = Blueprint('strategy_feedback', __name__, url_prefix='/api/strategy')


def register_routes(app, **kwargs):
    """
    注册策略反馈相关路由
    
    Args:
        app: Flask 应用实例
        kwargs: 可选的关键字参数
    """
    # 从 kwargs 获取全局组件
    db_manager = kwargs.get('db_manager') or getattr(app, 'db_manager', None)
    
    # 初始化服务
    if db_manager:
        global strategy_feedback_service
        strategy_feedback_service = StrategyFeedbackService(db_manager)
        logger.info("策略反馈服务已初始化")
    
    # 注册蓝图
    app.register_blueprint(strategy_feedback_bp)
    logger.info("策略反馈路由注册完成")


# ============================================================
# 用户反馈相关 API
# ============================================================

@strategy_feedback_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    """
    提交用户反馈
    
    记录用户对特定基金策略匹配的评分和评论。
    
    Request Body:
        {
            "fund_code": "000001",           // 必填：基金代码
            "strategy_type": "enhanced_rule_based",  // 必填：策略类型
            "rating": 5,                      // 必填：评分(1-5)
            "comment": "策略很准确",          // 可选：评论
            "user_id": "user123",            // 可选：用户ID，默认'default_user'
            "fund_name": "华夏成长混合",      // 可选：基金名称
            "strategy_name": "增强规则策略",  // 可选：策略名称
            "match_score": 85.5,             // 可选：系统匹配得分
            "is_helpful": true,              // 可选：是否有帮助
            "feedback_type": "overall"       // 可选：反馈类型
        }
    
    Returns:
        {
            "success": true,
            "data": {
                "feedback_id": 123,
                "message": "反馈提交成功",
                "weight_updated": true
            }
        }
    
    Error Response:
        {
            "success": false,
            "error": "错误信息"
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400
        
        # 必填参数验证
        required = ['fund_code', 'strategy_type', 'rating']
        for field in required:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必填参数: {field}'}), 400
        
        # 评分范围验证
        rating = data.get('rating')
        if not isinstance(rating, int) or not 1 <= rating <= 5:
            return jsonify({'success': False, 'error': '评分必须在1-5之间'}), 400
        
        # 提交反馈
        result = strategy_feedback_service.submit_feedback(
            fund_code=data['fund_code'],
            strategy_type=data['strategy_type'],
            rating=rating,
            comment=data.get('comment'),
            user_id=data.get('user_id', 'default_user'),
            fund_name=data.get('fund_name'),
            strategy_name=data.get('strategy_name'),
            match_score=data.get('match_score'),
            is_helpful=data.get('is_helpful'),
            feedback_type=data.get('feedback_type', 'overall')
        )
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result})
        else:
            return jsonify({'success': False, 'error': result.get('error', '提交失败')}), 500
            
    except Exception as e:
        logger.error(f"提交反馈失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@strategy_feedback_bp.route('/feedback', methods=['GET'])
def get_feedback_list():
    """
    获取反馈列表
    
    查询特定基金或策略的用户反馈列表。
    
    Query Parameters:
        fund_code (str): 基金代码，必填
        strategy_type (str): 策略类型，可选
        days (int): 最近多少天，默认30
        
    Returns:
        {
            "success": true,
            "data": {
                "fund_code": "000001",
                "total": 10,
                "feedbacks": [
                    {
                        "id": 1,
                        "strategy_type": "enhanced_rule_based",
                        "user_rating": 5,
                        "user_comment": "很准确",
                        "feedback_date": "2026-02-12",
                        "created_at": "2026-02-12 10:30:00"
                    }
                ]
            }
        }
    """
    try:
        fund_code = request.args.get('fund_code')
        if not fund_code:
            return jsonify({'success': False, 'error': '缺少参数: fund_code'}), 400
        
        strategy_type = request.args.get('strategy_type')
        days = request.args.get('days', 30, type=int)
        
        feedbacks = strategy_feedback_service.get_feedback_by_fund(
            fund_code=fund_code,
            strategy_type=strategy_type,
            days=days
        )
        
        return jsonify({
            'success': True,
            'data': {
                'fund_code': fund_code,
                'strategy_type': strategy_type,
                'total': len(feedbacks),
                'feedbacks': [
                    {
                        'id': f.id,
                        'strategy_type': f.strategy_type,
                        'user_rating': f.user_rating,
                        'user_comment': f.user_comment,
                        'is_helpful': f.is_helpful,
                        'feedback_date': str(f.feedback_date) if f.feedback_date else None,
                        'created_at': str(f.created_at) if f.created_at else None
                    }
                    for f in feedbacks
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"获取反馈列表失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@strategy_feedback_bp.route('/feedback/stats', methods=['GET'])
def get_feedback_stats():
    """
    获取反馈统计
    
    获取策略或全局的反馈统计数据。
    
    Query Parameters:
        strategy_type (str): 策略类型，为空则返回全局统计
        days (int): 统计天数，默认30
        
    Returns:
        {
            "success": true,
            "data": {
                "strategy_type": "enhanced_rule_based",
                "period_days": 30,
                "total_feedback": 100,
                "avg_rating": 4.2,
                "rating_distribution": {
                    "1": 5, "2": 10, "3": 20, "4": 30, "5": 35
                },
                "helpful_rate": 85.5,
                "recent_trend": "improving",
                "daily_stats": [...]
            }
        }
    """
    try:
        strategy_type = request.args.get('strategy_type')
        days = request.args.get('days', 30, type=int)
        
        stats = strategy_feedback_service.get_feedback_stats(
            strategy_type=strategy_type,
            days=days
        )
        
        if 'error' in stats:
            return jsonify({'success': False, 'error': stats['error']}), 500
        
        return jsonify({'success': True, 'data': stats})
        
    except Exception as e:
        logger.error(f"获取反馈统计失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# 策略表现相关 API
# ============================================================

@strategy_feedback_bp.route('/performance', methods=['POST'])
def record_performance():
    """
    记录策略表现
    
    记录策略预测与实际表现的对比数据。
    
    Request Body:
        {
            "fund_code": "000001",           // 必填：基金代码
            "strategy_type": "enhanced_rule_based",  // 必填：策略类型
            "predicted_action": "buy",       // 必填：预测操作
            "actual_return": 5.2,            // 可选：实际收益率(%)
            "predicted_confidence": 85,      // 可选：预测置信度
            "benchmark_return": 3.0,         // 可选：基准收益率(%)
            "prediction_date": "2026-02-01", // 可选：预测日期，默认今天
            "market_condition": "bull"       // 可选：市场环境
        }
    
    Returns:
        {
            "success": true,
            "data": {
                "performance_id": 456,
                "excess_return": 2.2,
                "prediction_accuracy": 75.5,
                "message": "表现记录创建成功"
            }
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400
        
        # 必填参数
        required = ['fund_code', 'strategy_type', 'predicted_action']
        for field in required:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必填参数: {field}'}), 400
        
        # 解析日期
        pred_date = None
        if 'prediction_date' in data:
            try:
                pred_date = datetime.strptime(data['prediction_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'error': '日期格式错误，应为YYYY-MM-DD'}), 400
        
        # 记录表现
        result = strategy_feedback_service.record_performance(
            fund_code=data['fund_code'],
            strategy_type=data['strategy_type'],
            predicted_action=data['predicted_action'],
            actual_return=data.get('actual_return'),
            predicted_confidence=data.get('predicted_confidence'),
            benchmark_return=data.get('benchmark_return'),
            prediction_date=pred_date,
            market_condition=data.get('market_condition')
        )
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result})
        else:
            return jsonify({'success': False, 'error': result.get('error', '记录失败')}), 500
            
    except Exception as e:
        logger.error(f"记录策略表现失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@strategy_feedback_bp.route('/performance/pending', methods=['GET'])
def get_pending_evaluations():
    """
    获取待评估的策略表现记录
    
    获取预测后经过一段时间需要补充实际数据的记录。
    
    Query Parameters:
        days (int): 预测后多少天，默认7
        
    Returns:
        {
            "success": true,
            "data": {
                "total": 5,
                "records": [
                    {
                        "id": 1,
                        "fund_code": "000001",
                        "strategy_type": "enhanced_rule_based",
                        "predicted_action": "buy",
                        "prediction_date": "2026-02-05",
                        "status": "pending"
                    }
                ]
            }
        }
    """
    try:
        days = request.args.get('days', 7, type=int)
        
        records = strategy_feedback_service.get_pending_evaluations(days=days)
        
        return jsonify({
            'success': True,
            'data': {
                'total': len(records),
                'records': [
                    {
                        'id': r.id,
                        'fund_code': r.fund_code,
                        'strategy_type': r.strategy_type,
                        'predicted_action': r.predicted_action,
                        'predicted_confidence': r.predicted_confidence,
                        'prediction_date': str(r.prediction_date) if r.prediction_date else None,
                        'status': r.status
                    }
                    for r in records
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"获取待评估记录失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@strategy_feedback_bp.route('/performance/<int:performance_id>', methods=['PUT'])
def update_performance(performance_id: int):
    """
    更新策略表现结果
    
    补充预测的实际收益数据。
    
    Request Body:
        {
            "actual_return": 5.2,            // 必填：实际收益率(%)
            "benchmark_return": 3.0,         // 可选：基准收益率(%)
            "evaluation_date": "2026-02-10"  // 可选：评估日期
        }
    
    Returns:
        {
            "success": true,
            "data": {
                "excess_return": 2.2,
                "prediction_accuracy": 75.5,
                "message": "表现结果更新成功"
            }
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'actual_return' not in data:
            return jsonify({'success': False, 'error': '缺少参数: actual_return'}), 400
        
        # 解析评估日期
        eval_date = None
        if 'evaluation_date' in data:
            try:
                eval_date = datetime.strptime(data['evaluation_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'error': '日期格式错误，应为YYYY-MM-DD'}), 400
        
        result = strategy_feedback_service.update_performance_result(
            performance_id=performance_id,
            actual_return=data['actual_return'],
            benchmark_return=data.get('benchmark_return'),
            evaluation_date=eval_date
        )
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result})
        else:
            return jsonify({'success': False, 'error': result.get('error', '更新失败')}), 400
            
    except Exception as e:
        logger.error(f"更新表现结果失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# 策略有效性分析 API
# ============================================================

@strategy_feedback_bp.route('/effectiveness', methods=['GET'])
def get_strategy_effectiveness():
    """
    获取策略有效性分析
    
    综合分析策略的反馈评分、预测准确度等指标。
    
    Query Parameters:
        strategy_type (str): 策略类型，为空则返回所有策略
        days (int): 分析天数，默认90
        
    Returns:
        {
            "success": true,
            "data": {
                "strategies": [
                    {
                        "strategy_type": "enhanced_rule_based",
                        "strategy_name": "增强规则策略",
                        "effectiveness_score": 78.5,
                        "current_weight": 1.2,
                        "components": {
                            "feedback_score": 80,
                            "accuracy_score": 75,
                            "success_rate": 70,
                            "consistency_score": 85
                        },
                        "statistics": {...},
                        "recommendation": "high",
                        "ranking": 1
                    }
                ]
            }
        }
    """
    try:
        strategy_type = request.args.get('strategy_type')
        days = request.args.get('days', 90, type=int)
        
        result = strategy_feedback_service.get_strategy_effectiveness(
            strategy_type=strategy_type,
            days=days
        )
        
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 500
        
        # 清理可能的NaN值
        def clean_nan(obj):
            if isinstance(obj, dict):
                return {k: clean_nan(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_nan(item) for item in obj]
            elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
                return None
            return obj
        
        result = clean_nan(result)
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        logger.error(f"获取策略有效性失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@strategy_feedback_bp.route('/comparison', methods=['GET'])
def get_strategy_comparison():
    """
    策略对比分析
    
    对比多个策略的有效性和表现。
    
    Query Parameters:
        strategy_types (str): 策略类型列表，逗号分隔，如 "type1,type2"
        days (int): 分析天数，默认90
        
    Returns:
        {
            "success": true,
            "data": {
                "strategies": [...],
                "comparison": {
                    "average_score": 65.5,
                    "best_strategy": {...},
                    "worst_strategy": {...},
                    "score_gap": 20.0
                }
            }
        }
    """
    try:
        strategy_types_str = request.args.get('strategy_types')
        days = request.args.get('days', 90, type=int)
        
        strategy_types = None
        if strategy_types_str:
            strategy_types = [s.strip() for s in strategy_types_str.split(',')]
        
        result = strategy_feedback_service.get_strategy_comparison(
            strategy_types=strategy_types,
            days=days
        )
        
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 500
        
        # 清理NaN值
        def clean_nan(obj):
            if isinstance(obj, dict):
                return {k: clean_nan(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_nan(item) for item in obj]
            elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
                return None
            return obj
        
        result = clean_nan(result)
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        logger.error(f"获取策略对比失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# 学习机制 API
# ============================================================

@strategy_feedback_bp.route('/recalculate', methods=['POST'])
def recalculate_weights():
    """
    重新计算所有策略权重
    
    基于所有历史数据重新计算策略权重。
    
    Returns:
        {
            "success": true,
            "data": {
                "updated_count": 7,
                "strategies": [
                    {
                        "strategy_type": "enhanced_rule_based",
                        "old_weight": 1.0,
                        "new_weight": 1.25,
                        "feedback_count": 50,
                        "avg_rating": 4.2,
                        "avg_accuracy": 72.5
                    }
                ]
            }
        }
    """
    try:
        result = strategy_feedback_service.recalculate_all_weights()
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result})
        else:
            return jsonify({'success': False, 'error': result.get('error', '计算失败')}), 500
            
    except Exception as e:
        logger.error(f"重新计算权重失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@strategy_feedback_bp.route('/learning-logs', methods=['GET'])
def get_learning_logs():
    """
    获取策略学习日志
    
    获取策略权重的调整历史。
    
    Query Parameters:
        strategy_type (str): 策略类型过滤
        limit (int): 返回条数，默认50
        
    Returns:
        {
            "success": true,
            "data": {
                "total": 50,
                "logs": [
                    {
                        "id": 1,
                        "strategy_type": "enhanced_rule_based",
                        "adjustment_type": "feedback",
                        "old_weight": 1.0,
                        "new_weight": 1.05,
                        "change_amount": 0.05,
                        "triggered_by": "system",
                        "created_at": "2026-02-12 10:30:00"
                    }
                ]
            }
        }
    """
    try:
        strategy_type = request.args.get('strategy_type')
        limit = request.args.get('limit', 50, type=int)
        
        logs = strategy_feedback_service.get_learning_logs(
            strategy_type=strategy_type,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'data': {
                'total': len(logs),
                'logs': logs
            }
        })
        
    except Exception as e:
        logger.error(f"获取学习日志失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@strategy_feedback_bp.route('/weights', methods=['GET'])
def get_strategy_weights():
    """
    获取策略权重
    
    获取各策略的当前权重配置。
    
    Query Parameters:
        strategy_type (str): 策略类型，为空返回所有
        
    Returns:
        {
            "success": true,
            "data": {
                "strategies": [
                    {
                        "strategy_type": "enhanced_rule_based",
                        "strategy_name": "增强规则策略",
                        "base_weight": 1.0,
                        "dynamic_weight": 1.25,
                        "effectiveness_score": 78.5,
                        "feedback_count": 50,
                        "avg_user_rating": 4.2,
                        "success_rate": 72.5
                    }
                ]
            }
        }
    """
    try:
        strategy_type = request.args.get('strategy_type')
        
        # 这里使用直接查询，因为服务类没有提供专门的方法
        from services.strategy_feedback_service import strategy_feedback_service as sfs
        
        if not sfs._ensure_db_manager():
            return jsonify({'success': False, 'error': '数据库未初始化'}), 500
        
        if strategy_type:
            sql = "SELECT * FROM strategy_weights WHERE strategy_type = %s"
            df = sfs.db_manager.execute_query(sql, (strategy_type,))
        else:
            sql = "SELECT * FROM strategy_weights ORDER BY dynamic_weight DESC"
            df = sfs.db_manager.execute_query(sql)
        
        strategies = []
        for _, row in df.iterrows():
            strategies.append({
                'strategy_type': row['strategy_type'],
                'strategy_name': row['strategy_name'],
                'base_weight': float(row['base_weight']),
                'dynamic_weight': float(row['dynamic_weight']),
                'effectiveness_score': float(row['effectiveness_score']),
                'feedback_count': int(row['feedback_count']),
                'avg_user_rating': float(row['avg_user_rating']),
                'success_rate': float(row['success_rate']),
                'last_updated': str(row['last_updated']) if row['last_updated'] else None
            })
        
        return jsonify({
            'success': True,
            'data': {
                'strategies': strategies,
                'total': len(strategies)
            }
        })
        
    except Exception as e:
        logger.error(f"获取策略权重失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# 健康检查
# ============================================================

@strategy_feedback_bp.route('/health', methods=['GET'])
def health_check():
    """
    健康检查
    
    检查反馈系统状态。
    
    Returns:
        {
            "success": true,
            "data": {
                "status": "healthy",
                "service": "strategy_feedback",
                "timestamp": "2026-02-12T10:30:00"
            }
        }
    """
    return jsonify({
        'success': True,
        'data': {
            'status': 'healthy',
            'service': 'strategy_feedback',
            'timestamp': datetime.now().isoformat()
        }
    })
