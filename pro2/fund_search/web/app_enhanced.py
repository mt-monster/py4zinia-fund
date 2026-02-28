#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基金分析系统 Web 应用 - 增强版

集成架构改进：
1. Celery异步任务
2. Redis消息队列
3. 微服务支持
4. GraphQL API
"""

import os
import sys
import logging
from flask import Flask, jsonify
from flask_cors import CORS

# 设置 Tushare 缓存目录到项目目录（避免权限问题）
# 必须在导入 tushare 之前设置
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tushare_cache_dir = os.path.join(project_root, '.cache', 'tushare')
os.makedirs(tushare_cache_dir, exist_ok=True)
os.environ['TUSHARE_CACHE_DIR'] = tushare_cache_dir

sys.path.append(project_root)

# 配置日志 - 只打印错误日志
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fund_analysis.log', encoding='utf-8')
    ]
)
# 设置 werkzeug 日志级别为 ERROR，只显示错误请求
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# ============ 尝试导入各个模块 ============

# 1. 配置管理
try:
    from shared.config_manager import config_manager
    from shared.json_utils import SafeJSONEncoder
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"配置管理不可用: {e}")
    CONFIG_AVAILABLE = False
    
    # 创建默认配置
    class MockConfig:
        secret_key = 'dev-secret-key'
        host = '0.0.0.0'
        port = 5000
        debug = True
    
    class MockConfigManager:
        @staticmethod
        def get_app_config():
            return MockConfig()
    
    config_manager = MockConfigManager()
    SafeJSONEncoder = None

# 2. 数据库
try:
    from data_access.enhanced_database import EnhancedDatabaseManager
    DB_AVAILABLE = True
except ImportError as e:
    print(f"数据库模块不可用: {e}")
    DB_AVAILABLE = False

# 3. 回测引擎（处理plotly等依赖）
try:
    from backtesting.core.unified_strategy_engine import UnifiedStrategyEngine
    from backtesting.analysis.strategy_evaluator import StrategyEvaluator
    BACKTEST_AVAILABLE = True
except ImportError as e:
    print(f"回测引擎不可用: {e}")
    BACKTEST_AVAILABLE = False

# 4. 数据适配器
try:
    from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
    ADAPTER_AVAILABLE = True
except ImportError as e:
    print(f"数据适配器不可用: {e}")
    ADAPTER_AVAILABLE = False

# 5. Celery
try:
    from celery_tasks import init_celery
    CELERY_AVAILABLE = True
except ImportError as e:
    print(f"Celery不可用: {e}")
    CELERY_AVAILABLE = False

# 6. Redis消息队列
try:
    from messaging import EventBus, register_event_handlers
    MESSAGING_AVAILABLE = True
except ImportError as e:
    print(f"消息队列不可用: {e}")
    MESSAGING_AVAILABLE = False

# 7. GraphQL
try:
    from graphql_api.blueprint import init_graphql
    GRAPHQL_AVAILABLE = True
except ImportError as e:
    print(f"GraphQL不可用: {e}")
    GRAPHQL_AVAILABLE = False

# 8. 原有服务
try:
    from services import FundNavCacheManager, HoldingRealtimeService, FundDataSyncService
    from services.cache_api_routes import init_cache_routes
    CACHE_SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"缓存服务不可用: {e}")
    CACHE_SERVICES_AVAILABLE = False

try:
    from services.fund_data_preloader import get_preloader
    from services.background_updater import get_background_updater
    PRELOAD_SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"预加载服务不可用: {e}")
    PRELOAD_SERVICES_AVAILABLE = False

# ============ 创建Flask应用 ============

app_config = config_manager.get_app_config()
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = app_config.secret_key
if SafeJSONEncoder:
    app.json_encoder = SafeJSONEncoder

CORS(app)

components = {}

# ============ 初始化函数 ============

def init_components():
    """初始化系统组件"""
    global components
    
    logger.info("开始初始化系统组件...")
    
    # 1. 初始化数据库
    if DB_AVAILABLE and CONFIG_AVAILABLE:
        try:
            from shared.config_manager import config_manager
            db_config = config_manager.get_database_config()
            components['db_manager'] = EnhancedDatabaseManager({
                'host': db_config.host,
                'user': db_config.user,
                'password': db_config.password,
                'database': db_config.database,
                'port': db_config.port,
                'charset': db_config.charset
            })
            logger.info("数据库管理器已初始化")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
    
    # 2. 初始化回测引擎
    if BACKTEST_AVAILABLE:
        try:
            components['strategy_engine'] = UnifiedStrategyEngine()
            components['strategy_evaluator'] = StrategyEvaluator()
            logger.info("回测引擎已初始化")
        except Exception as e:
            logger.error(f"回测引擎初始化失败: {e}")
    
    # 3. 初始化数据适配器
    if ADAPTER_AVAILABLE and CONFIG_AVAILABLE:
        try:
            from shared.config_manager import config_manager
            system_config = config_manager.get_system_config()
            components['fund_data_manager'] = MultiSourceDataAdapter(
                timeout=system_config.request_timeout
            )
            logger.info("数据适配器已初始化")
        except Exception as e:
            logger.error(f"数据适配器初始化失败: {e}")
    
    # 4. 初始化缓存服务
    if CACHE_SERVICES_AVAILABLE and 'db_manager' in components:
        try:
            from shared.config_manager import config_manager
            cache_config = config_manager.get_cache_config()
            components['cache_manager'] = FundNavCacheManager(
                components['db_manager'],
                default_ttl_minutes=cache_config.default_ttl // 60
            )
            components['holding_service'] = HoldingRealtimeService(
                components['db_manager'],
                components['cache_manager']
            )
            components['sync_service'] = FundDataSyncService(
                components['cache_manager'],
                components['db_manager']
            )
            
            if os.environ.get('ENABLE_SYNC_SERVICE', 'true').lower() == 'true':
                components['sync_service'].start()
                logger.info("数据同步服务已启动")
            
            init_cache_routes(
                app,
                components['cache_manager'],
                components['holding_service'],
                components['sync_service']
            )
            logger.info("缓存服务已初始化")
        except Exception as e:
            logger.error(f"缓存服务初始化失败: {e}")
    
    # 5. 初始化预加载服务
    if PRELOAD_SERVICES_AVAILABLE:
        try:
            preloader = get_preloader()
            components['preloader'] = preloader
            logger.info("预加载服务已初始化")

            # 启动时预加载数据（后台线程，不阻塞启动）
            import threading
            def background_preload():
                try:
                    logger.info("开始后台预加载基金数据...")
                    preloader.preload_all(async_mode=False)
                    logger.info("预加载完成，数据已缓存")
                except Exception as preload_err:
                    logger.warning(f"预加载失败: {preload_err}")

            preload_thread = threading.Thread(target=background_preload, daemon=True)
            preload_thread.start()
            logger.info("预加载任务已启动（后台运行）")

        except Exception as e:
            logger.error(f"预加载服务初始化失败: {e}")

    # 6. 初始化Celery（内存模式，无需 Redis，始终可用）
    if CELERY_AVAILABLE:
        try:
            celery = init_celery(app)
            components['celery'] = celery
            logger.info("Celery 已初始化（内存模式）")

            # 启动时触发一次净值更新（task_always_eager=True，同步执行）
            if os.environ.get('CELERY_TRIGGER_ON_START', 'false').lower() == 'true':
                try:
                    from celery_tasks import update_fund_nav_task
                    update_fund_nav_task.delay()
                    logger.info("已触发启动时净值更新任务")
                except Exception as e:
                    logger.warning(f"触发启动任务失败: {e}")
        except Exception as e:
            logger.error(f"Celery 初始化失败，降级为线程后台更新: {e}")
            if PRELOAD_SERVICES_AVAILABLE and os.environ.get('ENABLE_BACKGROUND_UPDATE', 'true').lower() == 'true':
                try:
                    updater = get_background_updater()
                    updater.start()
                    components['background_updater'] = updater
                    logger.info("降级：线程后台更新服务已启动")
                except Exception as e2:
                    logger.error(f"线程后台更新服务启动失败: {e2}")
    else:
        # Celery 不可用时使用线程后台更新
        if PRELOAD_SERVICES_AVAILABLE and os.environ.get('ENABLE_BACKGROUND_UPDATE', 'true').lower() == 'true':
            try:
                updater = get_background_updater()
                updater.start()
                components['background_updater'] = updater
                logger.info("线程后台数据更新服务已启动")
            except Exception as e:
                logger.error(f"线程后台更新服务启动失败: {e}")
    
    # 7. 初始化消息队列
    if MESSAGING_AVAILABLE:
        try:
            event_bus = EventBus()
            register_event_handlers(event_bus)
            event_bus.start_listener()
            components['event_bus'] = event_bus
            logger.info("事件总线已初始化")
        except Exception as e:
            logger.error(f"事件总线初始化失败: {e}")
    
    # 8. 初始化GraphQL
    if GRAPHQL_AVAILABLE:
        try:
            init_graphql(app)
            logger.info("GraphQL已初始化")
        except Exception as e:
            logger.error(f"GraphQL初始化失败: {e}")
    
    logger.info("系统组件初始化完成")


def register_routes():
    """注册路由"""
    try:
        from web.utils.auto_router import register_routes_automatically
        routes_dir = os.path.join(os.path.dirname(__file__), 'routes')
        results = register_routes_automatically(app, routes_dir, components)
        
        failed = [name for name, success in results.items() if not success]
        if failed:
            logger.warning(f"以下路由注册失败: {', '.join(failed)}")
    except Exception as e:
        logger.error(f"路由注册失败: {e}")


# ============ 初始化应用 ============

with app.app_context():
    init_components()
    register_routes()

# ============ 路由定义 ============




@app.route('/api/health')
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'components': {k: 'available' for k in components.keys()},
        'timestamp': '2026-02-26'
    })


@app.route('/api/enhancements')
def get_enhancements():
    """获取架构改进状态"""
    enhancements = {
        'celery': {
            'available': CELERY_AVAILABLE,
            'enabled': 'celery' in components,
            'description': '异步任务处理系统'
        },
        'messaging': {
            'available': MESSAGING_AVAILABLE,
            'enabled': 'event_bus' in components,
            'description': 'Redis消息队列和事件驱动架构'
        },
        'graphql': {
            'available': GRAPHQL_AVAILABLE,
            'enabled': GRAPHQL_AVAILABLE,
            'description': 'GraphQL API优化查询'
        },
        'microservices': {
            'available': True,
            'enabled': True,
            'description': '回测引擎微服务'
        }
    }
    
    return jsonify({
        'success': True,
        'data': enhancements,
        'version': '2.0-enhanced'
    })


@app.route('/api/modules')
def get_modules():
    """获取模块状态"""
    return jsonify({
        'success': True,
        'data': {
            'config': CONFIG_AVAILABLE,
            'database': DB_AVAILABLE,
            'backtest': BACKTEST_AVAILABLE,
            'adapter': ADAPTER_AVAILABLE,
            'celery': CELERY_AVAILABLE,
            'messaging': MESSAGING_AVAILABLE,
            'graphql': GRAPHQL_AVAILABLE,
            'cache': CACHE_SERVICES_AVAILABLE,
            'preload': PRELOAD_SERVICES_AVAILABLE
        }
    })


# ============ 启动应用 ============

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  基金分析系统 v2.0 (增强版)")
    print("="*60)
    print("\n  架构改进:")
    print(f"    [1] Celery异步任务:   {'OK' if CELERY_AVAILABLE else 'NO'}")
    print(f"    [2] Redis消息队列:    {'OK' if MESSAGING_AVAILABLE else 'NO'}")
    print(f"    [3] 微服务拆分:       OK")
    print(f"    [4] GraphQL API:      {'OK' if GRAPHQL_AVAILABLE else 'NO'}")
    print("\n  访问地址:")
    print(f"    http://{app_config.host}:{app_config.port}")
    print("="*60 + "\n")
    
    app.run(
        host=app_config.host,
        port=app_config.port,
        debug=app_config.debug
    )
