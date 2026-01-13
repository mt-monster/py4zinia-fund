#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试PushPlus邮件通知功能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from enhanced_notification import EnhancedNotificationManager
from enhanced_config import NOTIFICATION_CONFIG
import pandas as pd


def test_email_notification():
    """测试邮件通知功能"""
    print("开始测试PushPlus邮件通知功能...")
    
    # 创建通知管理器实例
    notification_manager = EnhancedNotificationManager(NOTIFICATION_CONFIG)
    
    # 准备测试数据 - 您提到的基金分析报告示例
    fund_analysis_content = """📊 基金分析报告 - 2026年01月13日
持仓基金收益率变化分析
基金代码\t基金名称\t今日收益率\t昨日收益率\t趋势状态\t操作建议\t执行金额
002611\t博时黄金ETF联接C\t0.34%\t1.95%\t🟠 **连涨回落**\t不买入，不赎回\t持有不动
096001\t大成标普500等权重指数(QDII)A人民币\t0.14%\t0.46%\t🟠 **连涨放缓**\t不买入，不赎回\t持有不动
001614\t东方区域发展混合\t0.33%\t2.39%\t🟠 **连涨回落**\t不买入，不赎回\t持有不动
006373\t国富全球科技互联混合(QDII)人民币A\t0.11%\t2.61%\t🟠 **连涨回落**\t不买入，不赎回\t持有不动
012728\t国泰中证动漫游戏ETF联接A\t2.72%\t6.35%\t🟠 **连涨回落**\t不买入，不赎回\t持有不动
013048\t富国中证新能源汽车指数(LOF)C\t1.25%\t0.33%\t🟡 **连涨加速**\t不买入，赎回15元\t赎回¥15
010034\t安信成长精选混合C\t-0.01%\t0.60%\t🔴 **反转跌**\t不买入，赎回30元\t赎回¥30
017963\t融通产业趋势臻选股票C\t-0.96%\t-1.16%\t💜 **阴跌筑底**\t定投买入，不赎回\t买入1.0×定额
006680\t广发道琼斯石油指数美元现汇C\t0.13%\t-0.95%\t🔵 **反转涨**\t定投买入，不赎回\t买入1.5×定额

提示：以上分析基于实时估值数据，仅供参考。最终投资决策请结合市场情况谨慎考虑。"""
    
    # 测试发送邮件通知
    print("\n正在发送邮件通知...")
    success = notification_manager.send_email_notification(
        title="📊 基金分析报告 - 2026年01月13日",
        content=fund_analysis_content,
        channel='mail',
        option='163'
    )
    
    if success:
        print("✅ 邮件通知发送成功！")
    else:
        print("❌ 邮件通知发送失败！")
    
    print("\n测试完成。")


if __name__ == "__main__":
    test_email_notification()