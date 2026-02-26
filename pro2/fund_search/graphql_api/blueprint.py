#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GraphQL Flask蓝图

提供GraphQL API的Flask路由。
"""

import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# 尝试导入Graphene
try:
    from graphene import Schema
    from .schema import schema
    GRAPHENE_AVAILABLE = True
except ImportError:
    GRAPHENE_AVAILABLE = False
    logger.warning("Graphene未安装，GraphQL API不可用")


# 创建蓝图
graphql_blueprint = Blueprint('graphql', __name__)


@graphql_blueprint.route('/graphql', methods=['POST'])
def graphql_endpoint():
    """
    GraphQL API端点
    
    接收GraphQL查询并返回结果
    """
    if not GRAPHENE_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'GraphQL不可用，请安装graphene: pip install graphene>=3.3.0'
        }), 503
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'errors': [{'message': '请求体不能为空'}]
            }), 400
        
        query = data.get('query')
        variables = data.get('variables')
        operation_name = data.get('operationName')
        
        if not query:
            return jsonify({
                'errors': [{'message': '查询不能为空'}]
            }), 400
        
        # 执行查询
        result = schema.execute(
            query,
            variables=variables,
            operation_name=operation_name,
            context={'request': request}
        )
        
        # 构建响应
        response = {}
        
        if result.errors:
            response['errors'] = [
                {'message': str(e)} for e in result.errors
            ]
        
        if result.data:
            response['data'] = result.data
        
        status_code = 200 if not result.errors else 400
        return jsonify(response), status_code
        
    except Exception as e:
        logger.error(f"GraphQL执行失败: {e}")
        return jsonify({
            'errors': [{'message': str(e)}]
        }), 500


@graphql_blueprint.route('/graphql', methods=['GET'])
def graphql_playground():
    """
    GraphQL Playground
    
    提供交互式的GraphQL查询界面
    """
    if not GRAPHENE_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'GraphQL不可用'
        }), 503
    
    # 返回GraphQL Playground HTML
    playground_html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>GraphQL Playground</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/css/index.css">
        <link rel="shortcut icon" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/favicon.png">
        <script src="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/js/middleware.js"></script>
    </head>
    <body>
        <div id="root">
            <style>
                body {
                    background-color: rgb(23, 42, 58);
                    font-family: Open Sans, sans-serif;
                    height: 90vh;
                }
                #root {
                    height: 100%;
                    width: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .loading {
                    font-size: 32px;
                    font-weight: 200;
                    color: rgba(255, 255, 255, .6);
                    margin-left: 20px;
                }
                img {
                    width: 78px;
                    height: 78px;
                }
                .title {
                    font-weight: 400;
                }
            </style>
            <img src='https://cdn.jsdelivr.net/npm/graphql-playground-react/build/logo.png' alt=''>
            <div class="loading">
                Loading <span class="title">GraphQL Playground</span>
            </div>
        </div>
        <script>
            window.addEventListener('load', function (event) {
                GraphQLPlayground.init(document.getElementById('root'), {
                    endpoint: '/graphql'
                })
            })
        </script>
    </body>
    </html>
    '''
    
    from flask import Response
    return Response(playground_html, mimetype='text/html')


@graphql_blueprint.route('/graphql/schema', methods=['GET'])
def graphql_schema():
    """
    获取GraphQL Schema定义
    
    返回Schema的SDL（Schema Definition Language）格式
    """
    if not GRAPHENE_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'GraphQL不可用'
        }), 503
    
    try:
        schema_sdl = schema.execute('''
            query IntrospectionQuery {
                __schema {
                    types {
                        name
                        kind
                        description
                    }
                }
            }
        ''')
        
        return jsonify({
            'success': True,
            'data': schema_sdl.data
        })
        
    except Exception as e:
        logger.error(f"获取Schema失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# 注册到Flask应用的辅助函数
def init_graphql(app):
    """
    初始化GraphQL蓝图
    
    Args:
        app: Flask应用实例
    """
    app.register_blueprint(graphql_blueprint, url_prefix='')
    logger.info("GraphQL API已注册")
