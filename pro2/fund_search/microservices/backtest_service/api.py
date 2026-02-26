#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
回测服务REST API

基于Flask实现的RESTful API接口。
"""

import os
import sys
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .service import get_service

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """创建Flask应用"""
    app = Flask(__name__)
    CORS(app)
    
    # 初始化服务
    service = get_service()
    service.init_components()
    
    # ============ 健康检查 ============
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """健康检查"""
        return jsonify({
            'status': 'healthy',
            'service': 'backtest',
            'stats': service.get_stats()
        })
    
    # ============ 任务管理 API ============
    
    @app.route('/api/backtest/tasks', methods=['POST'])
    def create_task():
        """创建回测任务"""
        try:
            data = request.get_json()
            
            strategy_id = data.get('strategy_id')
            user_id = data.get('user_id', 'default')
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            initial_capital = data.get('initial_capital', 100000.0)
            rebalance_freq = data.get('rebalance_freq', 'monthly')
            
            if not strategy_id:
                return jsonify({'success': False, 'error': '策略ID不能为空'}), 400
            
            task = service.create_task(
                strategy_id=strategy_id,
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                rebalance_freq=rebalance_freq
            )
            
            return jsonify({
                'success': True,
                'data': task.to_dict()
            })
            
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/backtest/tasks/<task_id>/run', methods=['POST'])
    def run_task(task_id):
        """执行回测任务"""
        try:
            success = service.run_task(task_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': '任务开始执行'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '任务执行失败'
                }), 400
                
        except Exception as e:
            logger.error(f"执行任务失败: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/backtest/tasks/<task_id>', methods=['GET'])
    def get_task(task_id):
        """获取任务详情"""
        try:
            task = service.get_task(task_id)
            
            if not task:
                return jsonify({
                    'success': False,
                    'error': '任务不存在'
                }), 404
            
            return jsonify({
                'success': True,
                'data': task.to_dict()
            })
            
        except Exception as e:
            logger.error(f"获取任务失败: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/backtest/tasks/<task_id>/status', methods=['GET'])
    def get_task_status(task_id):
        """获取任务状态"""
        try:
            status = service.get_task_status(task_id)
            
            if not status:
                return jsonify({
                    'success': False,
                    'error': '任务不存在'
                }), 404
            
            return jsonify({
                'success': True,
                'data': status
            })
            
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/backtest/tasks/<task_id>/result', methods=['GET'])
    def get_task_result(task_id):
        """获取任务结果"""
        try:
            result = service.get_task_result(task_id)
            
            if not result:
                return jsonify({
                    'success': False,
                    'error': '任务不存在'
                }), 404
            
            return jsonify({
                'success': True,
                'data': result
            })
            
        except Exception as e:
            logger.error(f"获取任务结果失败: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/backtest/tasks/<task_id>/cancel', methods=['POST'])
    def cancel_task(task_id):
        """取消任务"""
        try:
            success = service.cancel_task(task_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': '任务已取消'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '无法取消任务'
                }), 400
                
        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/backtest/tasks', methods=['GET'])
    def list_tasks():
        """列出所有任务"""
        try:
            user_id = request.args.get('user_id')
            status = request.args.get('status')
            
            tasks = service.list_tasks(user_id=user_id, status=status)
            
            return jsonify({
                'success': True,
                'data': tasks,
                'total': len(tasks)
            })
            
        except Exception as e:
            logger.error(f"列出任务失败: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ============ 统计信息 API ============
    
    @app.route('/api/backtest/stats', methods=['GET'])
    def get_stats():
        """获取服务统计信息"""
        try:
            stats = service.get_stats()
            
            return jsonify({
                'success': True,
                'data': stats
            })
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    logger.info("回测服务API已创建")
    return app


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=False)
