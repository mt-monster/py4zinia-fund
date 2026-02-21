#!/usr/bin/env python
# coding: utf-8

"""
用户策略管理 API 路由
提供用户策略的增删改查等操作
"""

import os
import sys
import json
from flask import jsonify, request
import pandas as pd
from datetime import datetime
import logging

# 添加父目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 初始化日志
logger = logging.getLogger(__name__)

# 导入策略模型
from backtesting.strategy_models import (
    StrategyConfig, FilterCondition, StrategyValidator, 
    calculate_equal_weights, validate_weights_sum
)
from backtesting.builtin_strategies import get_builtin_strategies_manager

# 数据库管理器将在 register_routes 中设置
db_manager = None


# ==================== 用户策略管理 API ====================


def get_user_strategies():
    """获取用户策略列表"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        sql = """
        SELECT id, user_id, name, description, config, created_at, updated_at
        FROM user_strategies
        WHERE user_id = :user_id
        ORDER BY updated_at DESC
        """
        
        df = db_manager.execute_query(sql, {'user_id': user_id})
        
        if df.empty:
            return jsonify({'success': True, 'data': [], 'total': 0})
        
        strategies = []
        for _, row in df.iterrows():
            strategy = {
                'id': int(row['id']),
                'user_id': row['user_id'],
                'name': row['name'],
                'description': row['description'] if pd.notna(row['description']) else '',
                'config': json.loads(row['config']) if isinstance(row['config'], str) else row['config'],
                'created_at': str(row['created_at']),
                'updated_at': str(row['updated_at'])
            }
            strategies.append(strategy)
        
        return jsonify({'success': True, 'data': strategies, 'total': len(strategies)})
        
    except Exception as e:
        logger.error(f"获取用户策略列表失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def create_user_strategy():
    """创建新策略"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default_user')
        name = data.get('name', '').strip()
        description = data.get('description', '')
        config_data = data.get('config', {})
        
        # 验证策略名称
        if not name:
            return jsonify({'success': False, 'error': '策略名称不能为空'}), 400
        
        # 构建策略配置对象并验证
        try:
            strategy_config = StrategyConfig.from_dict(config_data)
            strategy_config.name = name
            strategy_config.description = description
            
            is_valid, errors = StrategyValidator.validate_strategy_config(strategy_config)
            if not is_valid:
                error_messages = [err.to_dict() for err in errors]
                return jsonify({
                    'success': False, 
                    'error': '策略配置验证失败',
                    'validation_errors': error_messages
                }), 400
        except Exception as e:
            return jsonify({'success': False, 'error': f'策略配置解析失败: {str(e)}'}), 400
        
        # 序列化配置为JSON
        config_json = json.dumps(strategy_config.to_dict(), ensure_ascii=False)
        
        sql = """
        INSERT INTO user_strategies (user_id, name, description, config)
        VALUES (:user_id, :name, :description, :config)
        """
        
        success = db_manager.execute_sql(sql, {
            'user_id': user_id,
            'name': name,
            'description': description,
            'config': config_json
        })
        
        if success:
            # 获取新创建的策略ID
            id_sql = "SELECT LAST_INSERT_ID() as id"
            id_df = db_manager.execute_query(id_sql)
            new_id = int(id_df.iloc[0]['id']) if not id_df.empty else None
            
            return jsonify({
                'success': True, 
                'message': '策略创建成功',
                'data': {'id': new_id, 'name': name}
            })
        else:
            return jsonify({'success': False, 'error': '策略创建失败'}), 500
            
    except Exception as e:
        logger.error(f"创建策略失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def get_user_strategy(strategy_id):
    """获取策略详情"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        sql = """
        SELECT id, user_id, name, description, config, created_at, updated_at
        FROM user_strategies
        WHERE id = :strategy_id AND user_id = :user_id
        """
        
        df = db_manager.execute_query(sql, {'strategy_id': strategy_id, 'user_id': user_id})
        
        if df.empty:
            return jsonify({'success': False, 'error': '策略不存在'}), 404
        
        row = df.iloc[0]
        strategy = {
            'id': int(row['id']),
            'user_id': row['user_id'],
            'name': row['name'],
            'description': row['description'] if pd.notna(row['description']) else '',
            'config': json.loads(row['config']) if isinstance(row['config'], str) else row['config'],
            'created_at': str(row['created_at']),
            'updated_at': str(row['updated_at'])
        }
        
        return jsonify({'success': True, 'data': strategy})
        
    except Exception as e:
        logger.error(f"获取策略详情失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def update_user_strategy(strategy_id):
    """更新策略"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default_user')
        
        # 检查策略是否存在
        check_sql = "SELECT id FROM user_strategies WHERE id = :strategy_id AND user_id = :user_id"
        check_df = db_manager.execute_query(check_sql, {'strategy_id': strategy_id, 'user_id': user_id})
        
        if check_df.empty:
            return jsonify({'success': False, 'error': '策略不存在'}), 404
        
        # 构建更新字段
        update_fields = []
        params = {'strategy_id': strategy_id, 'user_id': user_id}
        
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({'success': False, 'error': '策略名称不能为空'}), 400
            update_fields.append('name = :name')
            params['name'] = name
        
        if 'description' in data:
            update_fields.append('description = :description')
            params['description'] = data['description']
        
        if 'config' in data:
            config_data = data['config']
            try:
                strategy_config = StrategyConfig.from_dict(config_data)
                
                # 如果更新了名称，同步到config
                if 'name' in data:
                    strategy_config.name = data['name'].strip()
                if 'description' in data:
                    strategy_config.description = data['description']
                
                is_valid, errors = StrategyValidator.validate_strategy_config(strategy_config)
                if not is_valid:
                    error_messages = [err.to_dict() for err in errors]
                    return jsonify({
                        'success': False,
                        'error': '策略配置验证失败',
                        'validation_errors': error_messages
                    }), 400
                
                config_json = json.dumps(strategy_config.to_dict(), ensure_ascii=False)
                update_fields.append('config = :config')
                params['config'] = config_json
            except Exception as e:
                return jsonify({'success': False, 'error': f'策略配置解析失败: {str(e)}'}), 400
        
        if not update_fields:
            return jsonify({'success': False, 'error': '没有要更新的字段'}), 400
        
        sql = f"""
        UPDATE user_strategies 
        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
        WHERE id = :strategy_id AND user_id = :user_id
        """
        
        success = db_manager.execute_sql(sql, params)
        
        if success:
            return jsonify({'success': True, 'message': '策略更新成功'})
        else:
            return jsonify({'success': False, 'error': '策略更新失败'}), 500
            
    except Exception as e:
        logger.error(f"更新策略失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def delete_user_strategy(strategy_id):
    """删除策略"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # 检查策略是否存在
        check_sql = "SELECT id FROM user_strategies WHERE id = :strategy_id AND user_id = :user_id"
        check_df = db_manager.execute_query(check_sql, {'strategy_id': strategy_id, 'user_id': user_id})
        
        if check_df.empty:
            return jsonify({'success': False, 'error': '策略不存在'}), 404
        
        sql = "DELETE FROM user_strategies WHERE id = :strategy_id AND user_id = :user_id"
        success = db_manager.execute_sql(sql, {'strategy_id': strategy_id, 'user_id': user_id})
        
        if success:
            return jsonify({'success': True, 'message': '策略删除成功'})
        else:
            return jsonify({'success': False, 'error': '策略删除失败'}), 500
            
    except Exception as e:
        logger.error(f"删除策略失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def copy_user_strategy(strategy_id):
    """复制策略"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        new_name = data.get('name', '').strip()
        
        # 获取原策略
        sql = """
        SELECT name, description, config
        FROM user_strategies
        WHERE id = :strategy_id AND user_id = :user_id
        """
        
        df = db_manager.execute_query(sql, {'strategy_id': strategy_id, 'user_id': user_id})
        
        if df.empty:
            return jsonify({'success': False, 'error': '原策略不存在'}), 404
        
        row = df.iloc[0]
        original_name = row['name']
        description = row['description'] if pd.notna(row['description']) else ''
        config = row['config']
        
        # 生成新名称
        if not new_name:
            new_name = f"{original_name} (副本)"
        
        # 更新config中的名称
        config_dict = json.loads(config) if isinstance(config, str) else config
        config_dict['name'] = new_name
        config_json = json.dumps(config_dict, ensure_ascii=False)
        
        # 插入新策略
        insert_sql = """
        INSERT INTO user_strategies (user_id, name, description, config)
        VALUES (:user_id, :name, :description, :config)
        """
        
        success = db_manager.execute_sql(insert_sql, {
            'user_id': user_id,
            'name': new_name,
            'description': description,
            'config': config_json
        })
        
        if success:
            # 获取新创建的策略ID
            id_sql = "SELECT LAST_INSERT_ID() as id"
            id_df = db_manager.execute_query(id_sql)
            new_id = int(id_df.iloc[0]['id']) if not id_df.empty else None
            
            return jsonify({
                'success': True,
                'message': '策略复制成功',
                'data': {'id': new_id, 'name': new_name}
            })
        else:
            return jsonify({'success': False, 'error': '策略复制失败'}), 500
            
    except Exception as e:
        logger.error(f"复制策略失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def validate_strategy_config():
    """验证策略配置（不保存）"""
    try:
        data = request.get_json()
        config_data = data.get('config', {})
        
        try:
            strategy_config = StrategyConfig.from_dict(config_data)
            is_valid, errors = StrategyValidator.validate_strategy_config(strategy_config)
            
            if is_valid:
                return jsonify({
                    'success': True,
                    'valid': True,
                    'message': '策略配置验证通过'
                })
            else:
                error_messages = [err.to_dict() for err in errors]
                return jsonify({
                    'success': True,
                    'valid': False,
                    'validation_errors': error_messages
                })
        except Exception as e:
            return jsonify({
                'success': True,
                'valid': False,
                'error': f'策略配置解析失败: {str(e)}'
            })
            
    except Exception as e:
        logger.error(f"验证策略配置失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def get_filter_fields():
    """获取支持的筛选字段列表"""
    try:
        from backtesting.strategy_models import SUPPORTED_FILTER_FIELDS, SUPPORTED_SORT_FIELDS
        
        filter_fields = []
        for field_name, field_info in SUPPORTED_FILTER_FIELDS.items():
            filter_fields.append({
                'name': field_name,
                'type': field_info['type'],
                'description': field_info['description']
            })
        
        return jsonify({
            'success': True,
            'data': {
                'filter_fields': filter_fields,
                'sort_fields': SUPPORTED_SORT_FIELDS,
                'operators': ['>', '<', '>=', '<=', '==', '!='],
                'filter_logic': ['AND', 'OR'],
                'sort_orders': ['ASC', 'DESC'],
                'weight_modes': ['equal', 'custom']
            }
        })
        
    except Exception as e:
        logger.error(f"获取筛选字段失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def register_routes(app, **kwargs):
    """
    注册用户策略管理相关的 API 路由
    
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
    
    # 用户策略管理路由
    app.route('/api/user-strategies', methods=['GET'])(get_user_strategies)
    app.route('/api/user-strategies', methods=['POST'])(create_user_strategy)
    app.route('/api/user-strategies/<int:strategy_id>', methods=['GET'])(get_user_strategy)
    app.route('/api/user-strategies/<int:strategy_id>', methods=['PUT'])(update_user_strategy)
    app.route('/api/user-strategies/<int:strategy_id>', methods=['DELETE'])(delete_user_strategy)
    app.route('/api/user-strategies/<int:strategy_id>/copy', methods=['POST'])(copy_user_strategy)
    app.route('/api/user-strategies/validate', methods=['POST'])(validate_strategy_config)
    app.route('/api/user-strategies/filter-fields', methods=['GET'])(get_filter_fields)
    
    logger.info("用户策略管理 API 路由已注册")
