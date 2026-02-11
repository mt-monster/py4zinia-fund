#!/usr/bin/env python
# coding: utf-8
"""
自动化路由注册系统
提供基于约定的路由自动发现和注册机制
"""

import os
import importlib
import logging
from typing import Dict, List, Callable, Any, Optional
from flask import Flask
from pathlib import Path


logger = logging.getLogger(__name__)


class RouteRegistry:
    """路由注册器"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.registered_routes = {}
        self.route_modules = {}
    
    def auto_discover_routes(self, routes_dir: str) -> Dict[str, List[str]]:
        """
        自动发现路由模块
        
        Args:
            routes_dir: 路由模块目录路径
            
        Returns:
            Dict: 发现的路由模块映射
        """
        routes_map = {}
        
        if not os.path.exists(routes_dir):
            logger.warning(f"路由目录不存在: {routes_dir}")
            return routes_map
        
        # 遍历路由目录
        for filename in os.listdir(routes_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = filename[:-3]  # 移除.py扩展名
                module_path = os.path.join(routes_dir, filename)
                
                # 检查模块是否包含register_routes函数
                if self._has_register_function(module_path):
                    routes_map[module_name] = [module_path]
                    logger.debug(f"发现路由模块: {module_name}")
        
        return routes_map
    
    def _has_register_function(self, module_path: str) -> bool:
        """检查模块是否包含register_routes函数"""
        try:
            # 简单的文本检查
            with open(module_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return 'register_routes' in content and 'def register_routes' in content
        except Exception as e:
            logger.warning(f"检查模块失败 {module_path}: {e}")
            return False
    
    def register_route_module(self, module_name: str, module_path: str, **dependencies) -> bool:
        """
        注册单个路由模块
        
        Args:
            module_name: 模块名称
            module_path: 模块路径
            **dependencies: 依赖项
            
        Returns:
            bool: 注册是否成功
        """
        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 检查是否有register_routes函数
            if not hasattr(module, 'register_routes'):
                logger.warning(f"模块 {module_name} 缺少 register_routes 函数")
                return False
            
            # 调用注册函数
            register_func = getattr(module, 'register_routes')
            register_func(self.app, **dependencies)
            
            # 记录注册信息
            self.registered_routes[module_name] = {
                'path': module_path,
                'dependencies': list(dependencies.keys()),
                'status': 'registered'
            }
            
            self.route_modules[module_name] = module
            
            logger.info(f"路由模块注册成功: {module_name}")
            return True
            
        except Exception as e:
            logger.error(f"路由模块注册失败 {module_name}: {e}")
            self.registered_routes[module_name] = {
                'path': module_path,
                'error': str(e),
                'status': 'failed'
            }
            return False
    
    def register_all_routes(self, routes_dir: str, dependencies: Dict[str, Any]) -> Dict[str, bool]:
        """
        注册所有路由模块
        
        Args:
            routes_dir: 路由目录
            dependencies: 全局依赖项
            
        Returns:
            Dict: 各模块注册结果
        """
        results = {}
        routes_map = self.auto_discover_routes(routes_dir)
        
        for module_name, module_paths in routes_map.items():
            module_path = module_paths[0]  # 取第一个路径
            results[module_name] = self.register_route_module(
                module_name, module_path, **dependencies
            )
        
        # 输出注册统计
        success_count = sum(1 for result in results.values() if result)
        total_count = len(results)
        logger.info(f"路由注册完成: {success_count}/{total_count} 个模块注册成功")
        
        return results
    
    def get_registered_routes(self) -> Dict[str, Dict[str, Any]]:
        """获取已注册的路由信息"""
        return self.registered_routes.copy()
    
    def get_route_module(self, module_name: str):
        """获取已注册的路由模块"""
        return self.route_modules.get(module_name)


class RouteDecorator:
    """路由装饰器工厂"""
    
    @staticmethod
    def api_route(endpoint: str, methods: List[str] = None, **kwargs):
        """
        API路由装饰器
        
        Args:
            endpoint: 路由端点
            methods: HTTP方法列表
            **kwargs: 其他路由参数
        """
        if methods is None:
            methods = ['GET']
            
        def decorator(func: Callable):
            # 添加路由元数据
            func._route_meta = {
                'endpoint': endpoint,
                'methods': methods,
                'kwargs': kwargs
            }
            return func
        return decorator
    
    @staticmethod
    def page_route(endpoint: str, template: str = None, **kwargs):
        """
        页面路由装饰器
        
        Args:
            endpoint: 路由端点
            template: 模板名称
            **kwargs: 其他路由参数
        """
        def decorator(func: Callable):
            func._page_meta = {
                'endpoint': endpoint,
                'template': template,
                'kwargs': kwargs
            }
            return func
        return decorator


def create_auto_router(app: Flask) -> RouteRegistry:
    """
    创建自动化路由注册器
    
    Args:
        app: Flask应用实例
        
    Returns:
        RouteRegistry: 路由注册器实例
    """
    return RouteRegistry(app)


def register_routes_automatically(
    app: Flask, 
    routes_directory: str, 
    dependencies: Dict[str, Any] = None
) -> Dict[str, bool]:
    """
    自动注册路由的便捷函数
    
    Args:
        app: Flask应用实例
        routes_directory: 路由模块目录
        dependencies: 依赖项字典
        
    Returns:
        Dict: 注册结果映射
    """
    if dependencies is None:
        dependencies = {}
    
    router = create_auto_router(app)
    results = router.register_all_routes(routes_directory, dependencies)
    
    # 打印详细的路由信息
    print_route_summary(router)
    
    return results


def print_route_summary(router: RouteRegistry):
    """打印路由注册摘要"""
    registered_routes = router.get_registered_routes()
    
    print("\n" + "="*60)
    print("路由注册摘要")
    print("="*60)
    
    for module_name, info in registered_routes.items():
        status_icon = "✅" if info['status'] == 'registered' else "❌"
        print(f"{status_icon} {module_name}")
        print(f"   路径: {info.get('path', 'N/A')}")
        if info['status'] == 'failed':
            print(f"   错误: {info.get('error', 'Unknown error')}")
        elif info.get('dependencies'):
            print(f"   依赖: {', '.join(info['dependencies'])}")
        print()
    
    success_count = sum(1 for info in registered_routes.values() if info['status'] == 'registered')
    total_count = len(registered_routes)
    print(f"总计: {success_count}/{total_count} 个模块注册成功")
    print("="*60)