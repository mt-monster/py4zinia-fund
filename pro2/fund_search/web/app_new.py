#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金分析系统 - 架构改进演示版

展示四个架构改进功能：
1. Celery异步任务
2. Redis消息队列
3. 回测引擎微服务
4. GraphQL API
"""

import os
import sys
import logging
from flask import Flask, jsonify
from flask_cors import CORS

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 检查各模块可用性
def check_modules():
    """检查架构改进模块"""
    modules = {
        'celery': {'status': False, 'error': None},
        'messaging': {'status': False, 'error': None},
        'microservices': {'status': False, 'error': None},
        'graphql': {'status': False, 'error': None}
    }
    
    # 1. Check Celery
    try:
        from celery_tasks import init_celery
        modules['celery']['status'] = True
        modules['celery']['version'] = '5.3.0+'
    except Exception as e:
        modules['celery']['error'] = str(e)
    
    # 2. Check Messaging
    try:
        from messaging import EventBus
        modules['messaging']['status'] = True
    except Exception as e:
        modules['messaging']['error'] = str(e)
    
    # 3. Check Microservices
    try:
        from microservices.backtest_service import BacktestService
        modules['microservices']['status'] = True
    except Exception as e:
        modules['microservices']['error'] = str(e)
    
    # 4. Check GraphQL
    try:
        from graphql_api import schema
        modules['graphql']['status'] = True
    except Exception as e:
        modules['graphql']['error'] = str(e)
    
    return modules

# ============ 路由定义 ============

@app.route('/')
def index():
    """首页"""
    return jsonify({
        'message': '基金分析系统 - 架构改进版',
        'version': '2.0-enhanced',
        'endpoints': {
            'health': '/api/health',
            'modules': '/api/modules',
            'enhancements': '/api/enhancements',
            'graphql': '/graphql'
        }
    })


@app.route('/api/health')
def health():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': '2026-02-26T15:50:00'
    })


@app.route('/api/modules')
def get_modules():
    """获取模块状态"""
    modules = check_modules()
    return jsonify({
        'success': True,
        'data': modules
    })


@app.route('/api/enhancements')
def get_enhancements():
    """获取架构改进详情"""
    enhancements = {
        'celery': {
            'name': 'Celery异步任务',
            'description': '处理耗时的后台任务',
            'files': [
                'celery_tasks/__init__.py',
                'celery_tasks/celery_app.py',
                'celery_tasks/tasks.py',
                'celery_tasks/runner.py'
            ],
            'features': [
                '基金数据异步更新',
                '回测任务异步执行',
                '定时任务调度',
                '任务重试机制'
            ]
        },
        'messaging': {
            'name': 'Redis消息队列',
            'description': '事件驱动架构',
            'files': [
                'messaging/__init__.py',
                'messaging/event_bus.py',
                'messaging/message_queue.py',
                'messaging/handlers.py'
            ],
            'features': [
                '发布/订阅模式',
                '可靠消息队列',
                '事件处理器',
                '分布式事件广播'
            ]
        },
        'microservices': {
            'name': '回测引擎微服务',
            'description': '独立服务拆分',
            'files': [
                'microservices/backtest_service/__init__.py',
                'microservices/backtest_service/service.py',
                'microservices/backtest_service/api.py',
                'microservices/backtest_service/grpc_server.py'
            ],
            'features': [
                'RESTful API',
                'gRPC接口',
                '任务管理',
                '独立部署'
            ]
        },
        'graphql': {
            'name': 'GraphQL API',
            'description': '优化API查询',
            'files': [
                'graphql_api/__init__.py',
                'graphql_api/types.py',
                'graphql_api/queries.py',
                'graphql_api/mutations.py',
                'graphql_api/schema.py',
                'graphql_api/blueprint.py'
            ],
            'features': [
                '精确数据获取',
                '单一端点',
                '类型安全',
                'Playground界面'
            ]
        }
    }
    
    return jsonify({
        'success': True,
        'data': enhancements
    })


@app.route('/api/test/celery')
def test_celery():
    """测试Celery任务"""
    try:
        from celery_tasks.tasks import update_fund_data_task
        
        # 注意：这里只是演示，不会真正执行（需要Celery Worker）
        result = {
            'available': True,
            'tasks': [
                'update_fund_data_task',
                'run_backtest_task',
                'sync_fund_data_task',
                'clear_expired_cache_task',
                'update_fund_nav_task',
                'recalc_performance_task',
                'batch_update_task'
            ],
            'note': '启动Worker后使用: python -m celery_tasks.runner worker'
        }
    except ImportError as e:
        result = {
            'available': False,
            'error': str(e),
            'install': 'pip install celery>=5.3.0 redis>=5.0.0'
        }
    
    return jsonify(result)


@app.route('/api/test/messaging')
def test_messaging():
    """测试消息队列"""
    try:
        from messaging import EventBus
        from messaging.message_queue import MessageQueue
        
        event_bus = EventBus()
        
        result = {
            'available': True,
            'event_bus_connected': event_bus.is_connected,
            'handlers_registered': len(event_bus._handlers),
            'features': [
                'EventBus: 发布/订阅',
                'MessageQueue: 可靠队列',
                'EventStore: 事件存储'
            ]
        }
    except ImportError as e:
        result = {
            'available': False,
            'error': str(e),
            'install': 'pip install redis>=5.0.0'
        }
    
    return jsonify(result)


@app.route('/api/test/microservices')
def test_microservices():
    """测试微服务"""
    try:
        from microservices.backtest_service.service import BacktestService, TaskStatus
        
        service = BacktestService()
        
        # 创建一个测试任务
        task = service.create_task(
            strategy_id='demo_strategy',
            user_id='demo_user',
            start_date='2023-01-01',
            end_date='2023-12-31'
        )
        
        result = {
            'available': True,
            'task_created': {
                'task_id': task.task_id,
                'strategy_id': task.strategy_id,
                'status': task.status.value
            },
            'endpoints': [
                'POST /api/backtest/tasks',
                'GET /api/backtest/tasks/<id>',
                'POST /api/backtest/tasks/<id>/run',
                'GET /api/backtest/tasks/<id>/status'
            ],
            'note': '启动服务: python -m microservices.backtest_service.api'
        }
    except ImportError as e:
        result = {
            'available': False,
            'error': str(e)
        }
    
    return jsonify(result)


@app.route('/api/test/graphql')
def test_graphql():
    """测试GraphQL"""
    try:
        from graphql_api import schema
        
        result = {
            'available': True,
            'types': [
                'FundType',
                'FundPerformanceType',
                'StrategyType',
                'BacktestResultType',
                'HoldingType',
                'PortfolioType'
            ],
            'queries': [
                'fund(code)',
                'funds(search, fundType)',
                'portfolio(userId)',
                'strategy(id)',
                'backtests'
            ],
            'mutations': [
                'createStrategy',
                'runBacktest',
                'addHolding'
            ],
            'playground': '/graphql'
        }
    except ImportError as e:
        result = {
            'available': False,
            'error': str(e),
            'install': 'pip install graphene>=3.3.0'
        }
    
    return jsonify(result)


# 注册GraphQL蓝图
try:
    from graphql_api.blueprint import graphql_blueprint
    app.register_blueprint(graphql_blueprint, url_prefix='')
    logger.info("GraphQL API已注册")
except ImportError:
    logger.warning("GraphQL不可用")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  基金分析系统 - 架构改进版")
    print("="*60)
    print("\n  正在检查模块...\n")
    
    modules = check_modules()
    for name, info in modules.items():
        status = "OK" if info['status'] else "NO"
        print(f"  [{status}] {name}")
    
    print("\n" + "="*60)
    print("  访问地址:")
    print("  - 主页:       http://localhost:5000/")
    print("  - 健康检查:   http://localhost:5000/api/health")
    print("  - 模块状态:   http://localhost:5000/api/modules")
    print("  - 改进详情:   http://localhost:5000/api/enhancements")
    print("  - GraphQL:    http://localhost:5000/graphql")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
