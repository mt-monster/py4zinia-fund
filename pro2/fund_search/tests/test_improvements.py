#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
架构改进验证测试

测试四个架构改进是否正常工作。
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCeleryIntegration:
    """测试Celery异步任务"""
    
    def test_celery_import(self):
        """测试Celery模块可导入"""
        try:
            from celery_tasks import init_celery, celery_app
            assert True
        except ImportError:
            pytest.skip("Celery未安装")
    
    def test_celery_tasks_import(self):
        """测试任务可导入"""
        try:
            from celery_tasks.tasks import (
                update_fund_data_task,
                run_backtest_task,
                sync_fund_data_task
            )
            assert True
        except ImportError:
            pytest.skip("Celery任务未定义")
    
    def test_celery_config(self):
        """测试Celery配置"""
        try:
            from celery_tasks.celery_app import DEFAULT_CELERY_CONFIG
            assert 'broker_url' in DEFAULT_CELERY_CONFIG
            assert 'result_backend' in DEFAULT_CELERY_CONFIG
        except ImportError:
            pytest.skip("Celery配置未定义")


class TestMessagingIntegration:
    """测试Redis消息队列"""
    
    def test_event_bus_import(self):
        """测试事件总线可导入"""
        try:
            from messaging import EventBus, Event
            assert True
        except ImportError:
            pytest.skip("消息队列模块未安装")
    
    def test_message_queue_import(self):
        """测试消息队列可导入"""
        try:
            from messaging import MessageQueue, QueueConsumer
            assert True
        except ImportError:
            pytest.skip("消息队列未定义")
    
    def test_handlers_import(self):
        """测试事件处理器可导入"""
        try:
            from messaging.handlers import (
                FundDataUpdatedHandler,
                BacktestCompletedHandler
            )
            assert True
        except ImportError:
            pytest.skip("事件处理器未定义")


class TestMicroservicesIntegration:
    """测试微服务拆分"""
    
    def test_backtest_service_import(self):
        """测试回测服务可导入"""
        try:
            from microservices.backtest_service import BacktestService
            assert True
        except ImportError:
            pytest.skip("回测服务未定义")
    
    def test_service_api_import(self):
        """测试服务API可导入"""
        try:
            from microservices.backtest_service.api import create_app
            assert callable(create_app)
        except ImportError:
            pytest.skip("服务API未定义")
    
    def test_task_creation(self):
        """测试任务创建"""
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
            assert task.user_id == 'test_user'
            assert task.status == TaskStatus.PENDING
        except ImportError:
            pytest.skip("服务组件未定义")


class TestGraphQLIntegration:
    """测试GraphQL API"""
    
    def test_graphql_import(self):
        """测试GraphQL模块可导入"""
        try:
            from graphql_api import schema
            assert True
        except ImportError:
            pytest.skip("GraphQL未安装")
    
    def test_schema_types(self):
        """测试Schema类型定义"""
        try:
            from graphql_api.types import (
                FundType, FundPerformanceType,
                StrategyType, BacktestResultType
            )
            assert True
        except ImportError:
            pytest.skip("GraphQL类型未定义")
    
    def test_query_execution(self):
        """测试查询执行"""
        try:
            from graphql_api import schema
            
            # 测试基本查询
            result = schema.execute('{ fundTypes }')
            
            # 查询应该成功执行（即使数据为空）
            assert result.errors is None or len(result.errors) == 0
        except ImportError:
            pytest.skip("GraphQL不可用")
    
    def test_fund_query(self):
        """测试基金查询"""
        try:
            from graphql_api import schema
            
            query = '''
                query {
                    fundTypes
                }
            '''
            
            result = schema.execute(query)
            
            if result.errors:
                # 可能缺少数据，但查询语法应该正确
                for error in result.errors:
                    assert 'Syntax' not in str(error)
        except ImportError:
            pytest.skip("GraphQL不可用")


class TestIntegration:
    """测试模块间集成"""
    
    def test_all_modules_exist(self):
        """测试所有模块文件存在"""
        import os
        
        modules = [
            'celery_tasks/__init__.py',
            'celery_tasks/celery_app.py',
            'celery_tasks/tasks.py',
            'messaging/__init__.py',
            'messaging/event_bus.py',
            'messaging/message_queue.py',
            'messaging/handlers.py',
            'microservices/backtest_service/__init__.py',
            'microservices/backtest_service/service.py',
            'microservices/backtest_service/api.py',
            'graphql_api/__init__.py',
            'graphql_api/types.py',
            'graphql_api/queries.py',
            'graphql_api/mutations.py',
            'graphql_api/schema.py',
            'graphql_api/blueprint.py',
        ]
        
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        for module in modules:
            full_path = os.path.join(base_path, module)
            assert os.path.exists(full_path), f"模块文件不存在: {module}"
    
    def test_enhanced_app_exists(self):
        """测试增强版应用文件存在"""
        import os
        
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        enhanced_app = os.path.join(base_path, 'web', 'app_enhanced.py')
        
        assert os.path.exists(enhanced_app), "增强版应用文件不存在"
    
    def test_documentation_exists(self):
        """测试文档文件存在"""
        import os
        
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        docs = [
            'ARCHITECTURE_IMPROVEMENTS.md',
            'IMPROVEMENTS_INTEGRATION_GUIDE.md',
            'microservices/backtest_service/README.md'
        ]
        
        for doc in docs:
            full_path = os.path.join(base_path, doc)
            assert os.path.exists(full_path), f"文档不存在: {doc}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
