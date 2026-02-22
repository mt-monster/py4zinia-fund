#!/usr/bin/env python
# coding: utf-8

"""
内置策略 API 路由
提供内置策略的查询、详情获取和应用功能
"""

import os
import sys
import json
from flask import jsonify, request
from datetime import datetime, timedelta
import logging

# 添加父目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting import get_builtin_strategies_manager

# 设置日志
logger = logging.getLogger(__name__)

# 数据库管理器引用（将在注册时设置）
db_manager = None


def register_routes(app, **kwargs):
    """注册内置策略相关路由
    
    Args:
        app: Flask 应用实例
        **kwargs: 包含以下可选参数:
            - db_manager 或 database_manager: 数据库管理器实例
    """
    global db_manager
    db_manager = kwargs.get('db_manager') or kwargs.get('database_manager')
    
    # 如果 kwargs 中没有，尝试从 app 属性获取
    if db_manager is None:
        db_manager = app.db_manager if hasattr(app, 'db_manager') else None
    
    # 注册所有路由
    app.route('/api/builtin-strategies', methods=['GET'])(get_builtin_strategies)
    app.route('/api/builtin-strategies/<strategy_key>', methods=['GET'])(get_builtin_strategy_detail)
    app.route('/api/builtin-strategies/<strategy_key>/apply', methods=['POST'])(apply_builtin_strategy)


# ==================== 内置策略 API ====================


def get_builtin_strategies():
    """获取内置策略列表
    
    Returns:
        所有内置策略的 key, name, description
    """
    try:
        manager = get_builtin_strategies_manager()
        strategies = manager.get_all()
        
        return jsonify({
            'success': True,
            'data': strategies,
            'total': len(strategies)
        })
        
    except Exception as e:
        logger.error(f"获取内置策略列表失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def get_builtin_strategy_detail(strategy_key):
    """获取内置策略详情
    
    Args:
        strategy_key: 策略唯一标识
        
    Returns:
        完整的策略配置（key, name, description, config）
    """
    try:
        manager = get_builtin_strategies_manager()
        strategy = manager.get_by_key(strategy_key)
        
        if strategy is None:
            return jsonify({
                'success': False,
                'error': f'内置策略不存在: {strategy_key}'
            }), 404
        
        return jsonify({
            'success': True,
            'data': strategy.to_dict()
        })
        
    except Exception as e:
        logger.error(f"获取内置策略详情失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def apply_builtin_strategy(strategy_key):
    """应用内置策略创建新的用户策略
    
    Args:
        strategy_key: 策略唯一标识
        
    Request Body:
        custom_name (optional): 自定义策略名称
        user_id (optional): 用户ID，默认为 'default_user'
        
    Returns:
        新创建的策略 ID 和详情
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        custom_name = data.get('custom_name', '').strip()
        
        # 获取内置策略
        manager = get_builtin_strategies_manager()
        builtin_strategy = manager.get_by_key(strategy_key)
        
        if builtin_strategy is None:
            return jsonify({
                'success': False,
                'error': f'内置策略不存在: {strategy_key}'
            }), 404
        
        # 确定策略名称
        if custom_name:
            strategy_name = custom_name
        else:
            # 使用内置策略名称加时间戳后缀
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            strategy_name = f"{builtin_strategy.name}_{timestamp}"
        
        # 复制策略配置
        config_dict = builtin_strategy.config.to_dict()
        config_dict['name'] = strategy_name
        
        # 序列化配置为JSON
        config_json = json.dumps(config_dict, ensure_ascii=False)
        
        # 保存到数据库
        sql = """
        INSERT INTO user_strategies (user_id, name, description, config)
        VALUES (:user_id, :name, :description, :config)
        """
        
        success = db_manager.execute_sql(sql, {
            'user_id': user_id,
            'name': strategy_name,
            'description': builtin_strategy.description,
            'config': config_json
        })
        
        if success:
            # 获取新创建的策略ID
            id_sql = "SELECT LAST_INSERT_ID() as id"
            id_df = db_manager.execute_query(id_sql)
            new_id = int(id_df.iloc[0]['id']) if not id_df.empty else None
            
            return jsonify({
                'success': True,
                'message': '策略应用成功',
                'data': {
                    'id': new_id,
                    'name': strategy_name,
                    'description': builtin_strategy.description,
                    'config': config_dict,
                    'source_builtin_key': strategy_key
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '创建策略失败'
            }), 500
            
    except Exception as e:
        logger.error(f"应用内置策略失败: {str(e)}")
        return jsonify({'success': False, 'error': f'创建策略失败: {str(e)}'}), 500
