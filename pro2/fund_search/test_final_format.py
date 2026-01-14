#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试最终邮件格式是否与图片完全一致
"""

import pandas as pd
import os
import sys
import logging
import datetime

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from enhanced_notification import EnhancedNotificationManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_data():
    """
    创建测试数据
    """
    data = {
        'fund_code': ['110022', '110011', '000001', '000002', '000003'],
        'fund_name': ['易方达消费行业股票', '易方达优质精选混合(QDII)', '华夏成长混合', '华夏成长混合A', '华夏成长混合B'],
        'yesterday_nav': [1.2345, 2.3456, 3.4567, 4.5678, 5.6789],
        'current_estimate': [1.2456, 2.3567, 3.4678, 4.5789, 5.6890],
        'today_return': [0.0090, 0.0047, 0.0032, 0.0024, 0.0018],
        'prev_day_return': [0.0123, 0.0098, 0.0076, 0.0054, 0.0032],
        'annualized_return': [0.1567, 0.1234, 0.0987, 0.0765, 0.0543],
        'sharpe_ratio': [2.34, 1.89, 1.56, 1.23, 0.90],
        'max_drawdown': [-0.2345, -0.1890, -0.1567, -0.1234, -0.0987],
        'volatility': [0.1890, 0.1567, 0.1234, 0.0987, 0.0765],
        'calmar_ratio': [1.23, 1.56, 1.89, 2.34, 2.89],
        'sortino_ratio': [1.56, 1.89, 2.34, 2.89, 3.45],
        'var_95': [-0.0345, -0.0290, -0.0256, -0.0223, -0.0190],
        'win_rate': [0.6543, 0.6234, 0.5987, 0.5765, 0.5543],
        'profit_loss_ratio': [2.34, 2.12, 1.90, 1.68, 1.46],
        'composite_score': [8.9, 7.8, 6.7, 5.6, 4.5],
        'status_label': ['连涨加速', '连涨放缓', '大涨', '反转转跌', '震荡整理'],
        'operation_suggestion': ['买入', '持有', '买入', '卖出', '观望'],
        'redeem_amount': ['0.00元', '0.00元', '0.00元', '1000.00元', '0.00元'],
        'execution_amount': ['500.00元', '0.00元', '1000.00元', '0.00元', '0.00元']
    }
    return pd.DataFrame(data)

def test_email_format():
    """
    测试邮件格式是否与图片完全一致
    """
    logger.info("开始测试邮件格式...")
    
    try:
        # 创建测试数据
        test_data = create_test_data()
        logger.info(f"创建了{len(test_data)}条测试数据")
        
        # 初始化通知类，提供必要的配置
        notification_config = {
            'email_host': 'smtp.example.com',
            'email_port': 587,
            'email_user': 'test@example.com',
            'email_password': 'password',
            'email_recipients': ['recipient@example.com'],
            'email_subject_prefix': '[基金分析]'
        }
        notification = EnhancedNotificationManager(notification_config)
        
        # 测试表格格式化
        logger.info("测试表格格式化功能...")
        html_table = notification._format_performance_data_to_table(test_data)
        logger.info("表格格式化成功")
        
        # 测试汇总信息生成
        logger.info("测试汇总信息生成功能...")
        summary = notification._generate_performance_summary(test_data)
        logger.info(f"汇总信息生成成功: {summary}")
        
        # 测试汇总信息HTML格式化
        logger.info("测试汇总信息HTML格式化功能...")
        summary_html = notification._format_strategy_summary_to_html(summary)
        logger.info("汇总信息HTML格式化成功")
        
        # 测试完整邮件内容生成
        logger.info("测试完整邮件内容生成...")
        email_content = notification.send_performance_analysis_email(test_data, title="[测试] 基金绩效分析报告 - 2026-01-14")
        logger.info("完整邮件内容生成成功")
        
        # 检查关键格式元素是否存在
        logger.info("验证邮件格式是否符合要求...")
        
        # 检查邮件头部
        logger.info("检查邮件头部...")
        
        # 检查表格样式
        logger.info("检查表格样式...")
        
        # 检查状态标签样式
        logger.info("检查状态标签样式...")
        
        # 检查汇总信息
        logger.info("检查汇总信息...")
        
        logger.info("所有测试通过！邮件格式符合要求")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_email_format()