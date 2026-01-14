#!/usr/bin/env python
# coding: utf-8

"""
测试绩效分析邮件发送功能
"""

import sys
import os
import logging
import pandas as pd
from datetime import datetime

# 添加项目根目录到sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_config import DATABASE_CONFIG, NOTIFICATION_CONFIG
from enhanced_database import EnhancedDatabaseManager
from enhanced_notification import EnhancedNotificationManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_performance_email():
    """
    测试绩效分析邮件发送功能
    """
    try:
        logger.info("开始测试绩效分析邮件发送功能")
        
        # 1. 初始化数据库管理器
        logger.info("初始化数据库管理器...")
        db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        
        # 2. 获取最新的绩效分析结果
        logger.info("获取最新的绩效分析结果...")
        performance_data = db_manager.get_latest_performance_analysis(limit=5)
        
        if performance_data.empty:
            logger.warning("没有获取到绩效分析数据，无法测试邮件发送")
            logger.warning("请先运行基金分析程序生成数据")
            return False
        
        logger.info(f"成功获取 {len(performance_data)} 条绩效分析数据")
        logger.info(f"数据包含字段: {', '.join(performance_data.columns.tolist())}")
        
        # 3. 初始化通知管理器
        logger.info("初始化通知管理器...")
        notification_manager = EnhancedNotificationManager(NOTIFICATION_CONFIG)
        
        # 4. 发送绩效分析邮件
        logger.info("发送绩效分析邮件...")
        email_title = f"[测试] 📊 基金绩效分析报告 - {datetime.now().strftime('%Y-%m-%d')}"
        success = notification_manager.send_performance_analysis_email(performance_data, title=email_title)
        
        if success:
            logger.info("绩效分析邮件发送测试成功！")
            return True
        else:
            logger.error("绩效分析邮件发送测试失败！")
            return False
            
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    logger.info("========================================")
    logger.info("📧 绩效分析邮件发送功能测试")
    logger.info("========================================")
    
    success = test_performance_email()
    
    if success:
        logger.info("✅ 测试成功！")
        sys.exit(0)
    else:
        logger.error("❌ 测试失败！")
        sys.exit(1)
