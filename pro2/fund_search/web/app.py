#!/usr/bin/env python
# coding: utf-8

"""
基金分析系统 Web 应用
提供前端界面和 API 接口

重构版本：使用自动化路由注册和统一配置管理
"""

import os
import sys
import logging
from flask import Flask
from flask_cors import CORS

# 添加父目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 使用新的配置管理系统
from shared.config_manager import config_manager
from shared.exceptions import with_error_handling

# 核心组件导入
from data_retrieval.enhanced_database import EnhancedDatabaseManager
from backtesting.unified_strategy_engine import UnifiedStrategyEngine
from backtesting.strategy_evaluator import StrategyEvaluator
from data_retrieval.multi_source_adapter import MultiSourceDataAdapter

# 缓存服务导入
try:
    from services import FundNavCacheManager, HoldingRealtimeService, FundDataSyncService
    from services.cache_api_routes import init_cache_routes
    CACHE_SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"缓存服务不可用: {e}")
    CACHE_SERVICES_AVAILABLE = False

# 预加载服务导入
try:
    from services.fund_data_preloader import FundDataPreloader, get_preloader
    from services.background_updater import BackgroundUpdater, get_background_updater
    PRELOAD_SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"预加载服务不可用: {e}")
    PRELOAD_SERVICES_AVAILABLE = False

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fund_analysis.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app_config = config_manager.get_app_config()
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = app_config.secret_key

# 配置 JSON 编码器以处理 NaN 和 Infinity
from shared.json_utils import SafeJSONEncoder
app.json_encoder = SafeJSONEncoder

CORS(app)

# 初始化组件
components = {}


def init_components():
    """初始化系统组件"""
    global components
    
    try:
        # 获取配置
        db_config = config_manager.get_database_config()
        system_config = config_manager.get_system_config()
        
        # 初始化数据库管理器
        components['db_manager'] = EnhancedDatabaseManager({
            'host': db_config.host,
            'user': db_config.user,
            'password': db_config.password,
            'database': db_config.database,
            'port': db_config.port,
            'charset': db_config.charset
        })
        
        # 初始化策略引擎
        components['strategy_engine'] = UnifiedStrategyEngine()
        components['strategy_evaluator'] = StrategyEvaluator()
        
        # 初始化数据管理器
        components['fund_data_manager'] = MultiSourceDataAdapter(
            timeout=system_config.request_timeout
        )
        
        # 初始化重仓股数据获取器
        from data_retrieval.heavyweight_stocks_fetcher import init_fetcher
        init_fetcher(components['db_manager'])
        
        # 初始化缓存服务（如果可用）
        if CACHE_SERVICES_AVAILABLE:
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
            
            # 启动定时同步服务
            if os.environ.get('ENABLE_SYNC_SERVICE', 'true').lower() == 'true':
                components['sync_service'].start()
                logger.info("数据同步服务已启动")
            
            # 注册缓存相关API路由
            init_cache_routes(
                app, 
                components['cache_manager'], 
                components['holding_service'], 
                components['sync_service']
            )
        
        # 初始化预加载服务（如果可用）
        if PRELOAD_SERVICES_AVAILABLE:
            logger.info("初始化数据预加载服务...")
            try:
                # 初始化预加载器
                preloader = get_preloader()
                components['preloader'] = preloader
                
                # 同步启动预加载（阻塞直到完成）
                # 确保系统启动时数据已准备就绪
                logger.info("开始预加载基金数据...")
                preloader.preload_all(async_mode=False)
                logger.info("数据预加载完成，系统已准备就绪")
                
                # 启动后台更新服务
                if os.environ.get('ENABLE_BACKGROUND_UPDATE', 'true').lower() == 'true':
                    updater = get_background_updater()
                    updater.start()
                    components['background_updater'] = updater
                    logger.info("后台数据更新服务已启动")
                
            except Exception as e:
                logger.error(f"预加载服务初始化失败: {e}")
        
        logger.info("系统组件初始化完成")
        
    except Exception as e:
        logger.error(f"系统组件初始化失败: {str(e)}", exc_info=True)
        raise


def register_routes_automatically():
    """自动注册所有路由"""
    try:
        from web.utils.auto_router import register_routes_automatically as auto_register
        
        # 获取路由目录
        routes_dir = os.path.join(os.path.dirname(__file__), 'routes')
        
        # 注册路由
        results = auto_register(app, routes_dir, components)
        
        # 检查注册结果
        failed_modules = [name for name, success in results.items() if not success]
        if failed_modules:
            logger.warning(f"以下路由模块注册失败: {', '.join(failed_modules)}")
        
        return results
        
    except Exception as e:
        logger.error(f"路由注册失败: {str(e)}", exc_info=True)
        raise

# 应用初始化
@with_error_handling
def initialize_application():
    """初始化应用"""
    logger.info("开始初始化基金分析系统...")
    
    # 初始化组件
    init_components()
    
    # 自动注册路由
    register_routes_automatically()
    
    logger.info("应用初始化完成")


# 初始化应用
initialize_application()


if __name__ == '__main__':
    # 获取应用配置
    app_config = config_manager.get_app_config()
    
    logger.info(f"启动基金分析系统 v2.0")
    logger.info(f"监听地址: {app_config.host}:{app_config.port}")
    logger.info(f"调试模式: {app_config.debug}")
    
    app.run(
        debug=app_config.debug,
        host=app_config.host,
        port=app_config.port,
        use_reloader=False  # 禁用重载器，避免日志重复打印
    )
