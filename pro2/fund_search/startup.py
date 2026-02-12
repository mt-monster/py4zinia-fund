#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金分析系统启动脚本

在启动Web服务前预加载所有必要数据，确保用户访问时几秒内响应。

启动流程：
1. 预加载所有基金基本信息
2. 预加载所有基金历史净值
3. 预计算所有绩效指标
4. 启动后台更新服务
5. 启动Web服务

使用示例:
    # 完整启动（推荐）
    python startup.py
    
    # 仅预加载数据
    python startup.py --preload-only
    
    # 指定基金预加载
    python startup.py --fund-codes 000001,000002,021539
    
    # 跳过预加载
    python startup.py --skip-preload
"""

import os
import sys
import time
import signal
import logging
import argparse
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('startup.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class FundAnalysisSystem:
    """基金分析系统主类"""
    
    def __init__(self):
        self.preloader = None
        self.updater = None
        self.app = None
        self._shutdown_event = False
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        logger.info(f"收到信号 {signum}，开始关闭系统...")
        self._shutdown_event = True
        self.shutdown()
        sys.exit(0)
    
    def preload_data(self, fund_codes: list = None, timeout: int = 300) -> bool:
        """
        预加载数据
        
        Args:
            fund_codes: 要预加载的基金代码列表
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否成功
        """
        logger.info("=" * 60)
        logger.info("开始预加载基金数据")
        logger.info("=" * 60)
        
        try:
            from services.fund_data_preloader import get_preloader
            
            self.preloader = get_preloader()
            
            # 设置配置
            if fund_codes:
                self.preloader.config.fund_codes = fund_codes
                logger.info(f"将预加载 {len(fund_codes)} 只指定基金")
            else:
                logger.info("将自动获取用户持仓基金进行预加载")
            
            # 开始预加载
            start_time = time.time()
            success = self.preloader.preload_all(async_mode=False)
            elapsed = time.time() - start_time
            
            if success:
                logger.info("=" * 60)
                logger.info(f"✓ 数据预加载完成！耗时: {elapsed:.1f} 秒")
                logger.info(f"  缓存统计: {self.preloader.get_cache_stats()}")
                logger.info("=" * 60)
                return True
            else:
                logger.error("✗ 数据预加载失败")
                return False
                
        except Exception as e:
            logger.error(f"预加载过程出错: {e}", exc_info=True)
            return False
    
    def start_background_updater(self):
        """启动后台更新服务"""
        try:
            from services.background_updater import get_background_updater
            
            self.updater = get_background_updater()
            self.updater.start()
            
            logger.info("✓ 后台数据更新服务已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动后台更新服务失败: {e}")
            return False
    
    def start_web_server(self, host: str = '0.0.0.0', port: int = 5000, 
                        debug: bool = False):
        """
        启动Web服务
        
        Args:
            host: 监听地址
            port: 监听端口
            debug: 是否调试模式
        """
        logger.info("=" * 60)
        logger.info("启动Web服务")
        logger.info("=" * 60)
        
        try:
            from web.app import app
            
            logger.info(f"监听地址: {host}:{port}")
            logger.info(f"调试模式: {debug}")
            logger.info("=" * 60)
            
            # 启动Flask应用
            app.run(host=host, port=port, debug=debug, threaded=True)
            
        except Exception as e:
            logger.error(f"启动Web服务失败: {e}", exc_info=True)
    
    def shutdown(self):
        """关闭系统"""
        logger.info("正在关闭系统...")
        
        # 停止后台更新服务
        if self.updater:
            try:
                self.updater.stop()
                logger.info("✓ 后台更新服务已停止")
            except Exception as e:
                logger.error(f"停止后台更新服务失败: {e}")
        
        logger.info("系统已关闭")
    
    def run(self, args):
        """
        运行系统
        
        Args:
            args: 命令行参数
        """
        print("\n" + "=" * 60)
        print("基金分析系统 v2.0")
        print("=" * 60 + "\n")
        
        # 1. 预加载数据（除非跳过）
        if not args.skip_preload:
            fund_codes = None
            if args.fund_codes:
                fund_codes = [c.strip() for c in args.fund_codes.split(',')]
            
            # 预加载前初始化 preloader 并设置最大基金数量
            from services.fund_data_preloader import get_preloader
            self.preloader = get_preloader()
            if args.max_funds > 0:
                self.preloader.config.max_funds = args.max_funds
                logger.info(f"设置最大预加载基金数量: {args.max_funds}")
            
            success = self.preload_data(fund_codes, args.preload_timeout)
            
            if not success and args.preload_required:
                logger.error("预加载失败且设置为必须，系统退出")
                return 1
            
            if args.preload_only:
                logger.info("仅预加载模式，退出")
                return 0
        else:
            logger.info("跳过预加载步骤")
        
        # 2. 启动后台更新服务
        if not args.skip_background_update:
            self.start_background_updater()
        
        # 3. 启动Web服务
        self.start_web_server(args.host, args.port, args.debug)
        
        return 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='基金分析系统启动脚本')
    
    # 预加载选项
    parser.add_argument('--fund-codes', type=str, 
                       help='指定预加载的基金代码，逗号分隔')
    parser.add_argument('--skip-preload', action='store_true',
                       help='跳过预加载步骤')
    parser.add_argument('--preload-only', action='store_true',
                       help='仅执行预加载，不启动Web服务')
    parser.add_argument('--preload-required', action='store_true',
                       help='预加载失败时退出系统')
    parser.add_argument('--preload-timeout', type=int, default=300,
                       help='预加载超时时间（秒，默认300）')
    parser.add_argument('--max-funds', type=int, default=0,
                       help='最大预加载基金数量，0表示无限制（默认0）')
    
    # 后台更新选项
    parser.add_argument('--skip-background-update', action='store_true',
                       help='跳过启动后台更新服务')
    
    # Web服务选项
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='监听地址（默认0.0.0.0）')
    parser.add_argument('--port', type=int, default=5000,
                       help='监听端口（默认5000）')
    parser.add_argument('--debug', action='store_true',
                       help='启用调试模式')
    
    args = parser.parse_args()
    
    # 创建并运行系统
    system = FundAnalysisSystem()
    
    try:
        return system.run(args)
    except KeyboardInterrupt:
        logger.info("收到键盘中断")
        system.shutdown()
        return 0
    except Exception as e:
        logger.error(f"系统运行出错: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
