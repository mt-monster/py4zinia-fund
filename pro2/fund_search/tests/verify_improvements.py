#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
架构改进验证脚本

验证四个架构改进是否正确实施，无需pytest。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_header(title):
    """打印标题"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def print_result(test_name, success, details=""):
    """打印测试结果"""
    status = "[PASS]" if success else "[FAIL]"
    print(f"  {status} - {test_name}")
    if details:
        print(f"         {details}")


def test_celery_integration():
    """测试1: Celery异步任务"""
    print_header("测试 1/4: Celery异步任务处理")
    
    tests_passed = 0
    tests_total = 4
    
    # 测试1.1: 模块导入
    try:
        from celery_tasks import init_celery
        print_result("Celery模块可导入", True)
        tests_passed += 1
    except ImportError as e:
        print_result("Celery模块可导入", False, "依赖未安装: pip install celery>=5.3.0")
    
    # 测试1.2: 任务定义
    try:
        from celery_tasks.tasks import update_fund_data_task
        print_result("任务定义可导入", True)
        tests_passed += 1
    except ImportError as e:
        print_result("任务定义可导入", False, str(e)[:50])
    
    # 测试1.3: 配置文件
    try:
        from celery_tasks.celery_app import DEFAULT_CELERY_CONFIG
        assert 'broker_url' in DEFAULT_CELERY_CONFIG
        assert 'result_backend' in DEFAULT_CELERY_CONFIG
        print_result("Celery配置正确", True)
        tests_passed += 1
    except (ImportError, AssertionError) as e:
        print_result("Celery配置正确", False, str(e)[:50])
    
    # 测试1.4: 定时任务配置
    try:
        from celery_tasks.celery_app import create_celery_app
        celery = create_celery_app()
        assert celery.conf.beat_schedule is not None
        print_result("定时任务配置正确", True)
        tests_passed += 1
    except Exception as e:
        print_result("定时任务配置正确", False, str(e)[:50])
    
    print(f"\n  结果: {tests_passed}/{tests_total} 测试通过")
    return tests_passed == tests_total


def test_messaging_integration():
    """测试2: Redis消息队列"""
    print_header("测试 2/4: Redis消息队列和事件驱动架构")
    
    tests_passed = 0
    tests_total = 4
    
    # 测试2.1: 事件总线
    try:
        from messaging import EventBus
        print_result("EventBus可导入", True)
        tests_passed += 1
    except ImportError as e:
        print_result("EventBus可导入", False, "依赖未安装: pip install redis>=5.0.0")
    
    # 测试2.2: 消息队列
    try:
        from messaging import MessageQueue
        print_result("MessageQueue可导入", True)
        tests_passed += 1
    except ImportError as e:
        print_result("MessageQueue可导入", False, str(e)[:50])
    
    # 测试2.3: 事件处理器
    try:
        from messaging.handlers import FundDataUpdatedHandler
        print_result("事件处理器可导入", True)
        tests_passed += 1
    except ImportError as e:
        print_result("事件处理器可导入", False, str(e)[:50])
    
    # 测试2.4: 事件类型定义
    try:
        from messaging.event_bus import Event, EventPriority
        assert EventPriority.CRITICAL.value == 0
        assert EventPriority.NORMAL.value == 2
        print_result("事件类型定义正确", True)
        tests_passed += 1
    except (ImportError, AssertionError) as e:
        print_result("事件类型定义正确", False, str(e)[:50])
    
    print(f"\n  结果: {tests_passed}/{tests_total} 测试通过")
    return tests_passed == tests_total


def test_microservices_integration():
    """测试3: 微服务拆分"""
    print_header("测试 3/4: 回测引擎微服务拆分")
    
    tests_passed = 0
    tests_total = 4
    
    # 测试3.1: 服务核心
    try:
        from microservices.backtest_service import BacktestService
        print_result("BacktestService可导入", True)
        tests_passed += 1
    except ImportError as e:
        print_result("BacktestService可导入", False, str(e)[:50])
    
    # 测试3.2: 任务状态枚举
    try:
        from microservices.backtest_service.service import TaskStatus
        assert TaskStatus.PENDING.value == 'pending'
        assert TaskStatus.COMPLETED.value == 'completed'
        print_result("任务状态枚举定义正确", True)
        tests_passed += 1
    except (ImportError, AssertionError) as e:
        print_result("任务状态枚举定义正确", False, str(e)[:50])
    
    # 测试3.3: REST API
    try:
        from microservices.backtest_service.api import create_app
        assert callable(create_app)
        print_result("REST API可创建", True)
        tests_passed += 1
    except ImportError as e:
        print_result("REST API可创建", False, str(e)[:50])
    
    # 测试3.4: 任务创建
    try:
        from microservices.backtest_service.service import BacktestService, TaskStatus
        service = BacktestService()
        task = service.create_task(
            strategy_id='test_strategy',
            user_id='test_user',
            start_date='2023-01-01',
            end_date='2023-12-31'
        )
        assert task.strategy_id == 'test_strategy'
        assert task.status == TaskStatus.PENDING
        print_result("任务创建功能正常", True)
        tests_passed += 1
    except Exception as e:
        print_result("任务创建功能正常", False, str(e)[:50])
    
    print(f"\n  结果: {tests_passed}/{tests_total} 测试通过")
    return tests_passed == tests_total


def test_graphql_integration():
    """测试4: GraphQL API"""
    print_header("测试 4/4: GraphQL API优化查询")
    
    tests_passed = 0
    tests_total = 4
    
    # 测试4.1: Schema导入
    try:
        from graphql_api import schema
        print_result("GraphQL Schema可导入", True)
        tests_passed += 1
    except ImportError as e:
        print_result("GraphQL Schema可导入", False, "依赖未安装: pip install graphene>=3.3.0")
    
    # 测试4.2: 类型定义
    try:
        from graphql_api.types import FundType, FundPerformanceType
        print_result("GraphQL类型可导入", True)
        tests_passed += 1
    except ImportError as e:
        print_result("GraphQL类型可导入", False, str(e)[:50])
    
    # 测试4.3: 查询定义
    try:
        from graphql_api.queries import Query
        print_result("GraphQL查询可导入", True)
        tests_passed += 1
    except ImportError as e:
        print_result("GraphQL查询可导入", False, str(e)[:50])
    
    # 测试4.4: 变更定义
    try:
        from graphql_api.mutations import Mutation
        print_result("GraphQL变更可导入", True)
        tests_passed += 1
    except ImportError as e:
        print_result("GraphQL变更可导入", False, str(e)[:50])
    
    print(f"\n  结果: {tests_passed}/{tests_total} 测试通过")
    return tests_passed == tests_total


def test_file_structure():
    """测试文件结构完整性"""
    print_header("测试: 文件结构完整性")
    
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    required_files = [
        ('Celery模块', 'celery_tasks/__init__.py'),
        ('Celery应用', 'celery_tasks/celery_app.py'),
        ('Celery任务', 'celery_tasks/tasks.py'),
        ('消息队列模块', 'messaging/__init__.py'),
        ('事件总线', 'messaging/event_bus.py'),
        ('消息队列', 'messaging/message_queue.py'),
        ('事件处理器', 'messaging/handlers.py'),
        ('微服务模块', 'microservices/backtest_service/__init__.py'),
        ('回测服务', 'microservices/backtest_service/service.py'),
        ('服务API', 'microservices/backtest_service/api.py'),
        ('GraphQL模块', 'graphql_api/__init__.py'),
        ('GraphQL类型', 'graphql_api/types.py'),
        ('GraphQL查询', 'graphql_api/queries.py'),
        ('GraphQL变更', 'graphql_api/mutations.py'),
        ('GraphQL Schema', 'graphql_api/schema.py'),
        ('增强版应用', 'web/app_enhanced.py'),
        ('改进文档', 'ARCHITECTURE_IMPROVEMENTS.md'),
        ('集成指南', 'IMPROVEMENTS_INTEGRATION_GUIDE.md'),
    ]
    
    tests_passed = 0
    
    for name, path in required_files:
        full_path = os.path.join(base_path, path)
        exists = os.path.exists(full_path)
        print_result(name, exists, path if not exists else "")
        if exists:
            tests_passed += 1
    
    print(f"\n  结果: {tests_passed}/{len(required_files)} 文件存在")
    return tests_passed == len(required_files)


def main():
    """主函数"""
    print("\n" + "="*60)
    print("  架构改进实施验证")
    print("  验证ARCHITECTURE_ANALYSIS.md第9.2节的4项改进")
    print("="*60)
    
    results = []
    
    # 运行所有测试
    results.append(("Celery异步任务", test_celery_integration()))
    results.append(("Redis消息队列", test_messaging_integration()))
    results.append(("微服务拆分", test_microservices_integration()))
    results.append(("GraphQL API", test_graphql_integration()))
    results.append(("文件结构", test_file_structure()))
    
    # 打印总结
    print_header("验证总结")
    
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} - {name}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("  SUCCESS: 所有架构改进已成功实施!")
    else:
        print("  WARNING: 部分测试未通过，请检查实现")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
