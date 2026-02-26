#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
回测引擎微服务

将回测引擎拆分为独立的微服务，支持：
- RESTful API接口
- gRPC接口（高性能）
- 消息队列异步处理
- 独立部署和扩展

服务端口:
- HTTP API: 5001
- gRPC: 50051
"""

from .service import BacktestService
from .api import create_app
from .grpc_server import serve as serve_grpc

__all__ = ['BacktestService', 'create_app', 'serve_grpc']
