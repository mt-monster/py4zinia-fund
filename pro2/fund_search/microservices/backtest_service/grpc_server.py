#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
回测服务gRPC接口

基于gRPC的高性能接口实现。
"""

import os
import sys
import logging
from concurrent import futures

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# gRPC导入（如果已安装）
try:
    import grpc
    from grpc import ServicerContext
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    logger.warning("gRPC未安装，gRPC服务不可用")

from .service import get_service, TaskStatus


if GRPC_AVAILABLE:
    # 定义gRPC服务（需要.proto文件生成）
    # 这里是服务实现示例
    
    class BacktestServicer:
        """回测服务gRPC实现"""
        
        def __init__(self):
            self.service = get_service()
        
        def CreateTask(self, request, context):
            """创建任务"""
            try:
                task = self.service.create_task(
                    strategy_id=request.strategy_id,
                    user_id=request.user_id,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    initial_capital=request.initial_capital,
                    rebalance_freq=request.rebalance_freq
                )
                
                return {
                    'task_id': task.task_id,
                    'status': task.status.value,
                    'created_at': task.created_at
                }
            except Exception as e:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
                return {}
        
        def RunTask(self, request, context):
            """运行任务"""
            try:
                success = self.service.run_task(request.task_id)
                return {'success': success}
            except Exception as e:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
                return {'success': False}
        
        def GetTaskStatus(self, request, context):
            """获取任务状态"""
            try:
                status = self.service.get_task_status(request.task_id)
                if status:
                    return status
                else:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details('Task not found')
                    return {}
            except Exception as e:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
                return {}
        
        def GetTaskResult(self, request, context):
            """获取任务结果"""
            try:
                result = self.service.get_task_result(request.task_id)
                if result:
                    return result
                else:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details('Task not found')
                    return {}
            except Exception as e:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
                return {}
        
        def CancelTask(self, request, context):
            """取消任务"""
            try:
                success = self.service.cancel_task(request.task_id)
                return {'success': success}
            except Exception as e:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
                return {'success': False}
        
        def ListTasks(self, request, context):
            """列出任务"""
            try:
                tasks = self.service.list_tasks(
                    user_id=request.user_id if request.user_id else None,
                    status=request.status if request.status else None
                )
                return {'tasks': tasks}
            except Exception as e:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
                return {}
        
        def GetStats(self, request, context):
            """获取统计信息"""
            try:
                stats = self.service.get_stats()
                return stats
            except Exception as e:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
                return {}


def serve(port: int = 50051, max_workers: int = 10):
    """
    启动gRPC服务
    
    Args:
        port: 服务端口
        max_workers: 最大工作线程数
    """
    if not GRPC_AVAILABLE:
        logger.error("gRPC未安装，无法启动gRPC服务")
        return None
    
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
        
        # 注册服务（需要.proto文件生成）
        # add_BacktestServiceServicer_to_server(BacktestServicer(), server)
        
        server.add_insecure_port(f'[::]:{port}')
        server.start()
        
        logger.info(f"gRPC服务已启动，端口: {port}")
        
        return server
        
    except Exception as e:
        logger.error(f"启动gRPC服务失败: {e}")
        return None


def serve_blocking(port: int = 50051, max_workers: int = 10):
    """
    启动gRPC服务并阻塞
    
    Args:
        port: 服务端口
        max_workers: 最大工作线程数
    """
    server = serve(port, max_workers)
    if server:
        server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    serve_blocking()
