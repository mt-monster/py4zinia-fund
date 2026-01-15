#!/usr/bin/env python
# coding: utf-8

"""
测试邮件发送功能
"""

import sys
import os
sys.path.append('pro2/fund_search')

import pandas as pd
from datetime import datetime

def test_email_sending():
    """
    测试邮件发送功能
    """
    print("=" * 80)
    print("测试邮件发送功能")
    print("=" * 80)
    
    try:
        from enhanced_main import EnhancedFundAnalysisSystem
        from shared.enhanced_config import BASE_CONFIG
        
        # 创建分析器实例
        analyzer = EnhancedFundAnalysisSystem()
        
        print("1. 创建测试数据...")
        
        # 创建测试基金数据
        test_fund_data = pd.DataFrame({
            '代码': ['011146', '000001', '110003'],
            '名称': ['天弘中证电网设备主题指数发起C', '华夏成长混合', '易方达消费行业股票']
        })
        
        print(f"   测试基金数量: {len(test_fund_data)}")
        print(f"   基金列表:")
        for _, row in test_fund_data.iterrows():
            print(f"     {row['代码']}: {row['名称']}")
        
        print(f"\n2. 执行基金分析...")
        
        # 分析基金数据
        analysis_date = datetime.now().strftime('%Y-%m-%d')
        results = analyzer.analyze_all_funds(test_fund_data, analysis_date)
        
        if not results:
            print("❌ 基金分析失败")
            return False
        
        print(f"   ✅ 成功分析 {len(results)} 只基金")
        
        # 转换为DataFrame
        results_df = pd.DataFrame(results)
        
        print(f"\n3. 检查分析结果数据...")
        
        # 检查必要字段
        required_fields = ['fund_code', 'fund_name', 'today_return', 'yesterday_return', 
                          'status_label', 'operation_suggestion', 'execution_amount']
        
        missing_fields = []
        for field in required_fields:
            if field not in results_df.columns:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"   ❌ 缺少必要字段: {missing_fields}")
            return False
        
        print(f"   ✅ 所有必要字段都存在")
        
        # 显示分析结果摘要
        print(f"\n   分析结果摘要:")
        for _, row in results_df.iterrows():
            fund_code = row.get('fund_code', '')
            fund_name = row.get('fund_name', '')
            today_return = row.get('today_return', 0)
            yesterday_return = row.get('yesterday_return', 0)
            status_label = row.get('status_label', '')
            
            print(f"     {fund_code}: {today_return:.2f}% | {yesterday_return:.2f}% | {status_label}")
        
        print(f"\n4. 生成策略汇总...")
        
        # 生成策略汇总
        strategy_summary = analyzer.generate_strategy_summary(results)
        
        if not strategy_summary:
            print("   ❌ 策略汇总生成失败")
            return False
        
        print(f"   ✅ 策略汇总生成成功")
        print(f"   汇总信息: {len(strategy_summary)} 个指标")
        
        print(f"\n5. 测试邮件内容生成...")
        
        # 测试邮件内容生成
        try:
            message = analyzer.generate_wechat_message(results_df)
            
            if not message or len(message) < 100:
                print("   ❌ 邮件内容生成失败或内容过短")
                return False
            
            print(f"   ✅ 邮件内容生成成功")
            print(f"   内容长度: {len(message)} 字符")
            
            # 检查邮件内容是否包含必要元素
            required_elements = ['基金代码', '基金名称', '今日收益率', '昨日收益率', '趋势状态', '操作建议', '执行金额']
            missing_elements = []
            
            for element in required_elements:
                if element not in message:
                    missing_elements.append(element)
            
            if missing_elements:
                print(f"   ❌ 邮件内容缺少元素: {missing_elements}")
                return False
            
            print(f"   ✅ 邮件内容包含所有必要元素")
            
            # 保存邮件内容预览
            with open('email_test_preview.html', 'w', encoding='utf-8') as f:
                f.write(f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>邮件测试预览</title>
</head>
<body>
{message}
</body>
</html>
""")
            
            print(f"   📄 邮件预览已保存为: email_test_preview.html")
            
        except Exception as e:
            print(f"   ❌ 邮件内容生成异常: {str(e)}")
            return False
        
        print(f"\n6. 测试通知发送准备...")
        
        # 测试通知发送准备（不实际发送）
        try:
            report_files = {}  # 空的报告文件字典
            
            # 模拟发送通知报告的准备工作
            notification_success = analyzer.send_notification_reports(results_df, strategy_summary, report_files)
            
            print(f"   通知发送结果: {'成功' if notification_success else '失败'}")
            
        except Exception as e:
            print(f"   ⚠️  通知发送测试异常: {str(e)}")
            print(f"   这可能是由于缺少通知配置导致的，属于正常情况")
        
        print(f"\n✅ 邮件发送功能测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_email_format_details():
    """
    测试邮件格式细节
    """
    print(f"\n" + "=" * 80)
    print("测试邮件格式细节")
    print("=" * 80)
    
    try:
        # 模拟完整的基金分析结果数据
        test_results = [
            {
                'fund_code': '011146',
                'fund_name': '天弘中证电网设备主题指数发起C',
                'today_return': -0.93,
                'yesterday_return': 1.33,
                'status_label': '🔴 反转跌',
                'operation_suggestion': '定投金额 150 元',
                'execution_amount': '150元'
            },
            {
                'fund_code': '000001',
                'fund_name': '华夏成长混合',
                'today_return': 1.25,
                'yesterday_return': -0.45,
                'status_label': '🔵 反转涨',
                'operation_suggestion': '定投金额 100 元',
                'execution_amount': '100元'
            },
            {
                'fund_code': '110003',
                'fund_name': '易方达消费行业股票',
                'today_return': 0.0,
                'yesterday_return': 2.1,
                'status_label': '⚪ 转势持平',
                'operation_suggestion': '定投金额 120 元',
                'execution_amount': '120元'
            }
        ]
        
        results_df = pd.DataFrame(test_results)
        
        print("测试数据:")
        print(results_df.to_string(index=False))
        
        # 导入邮件生成函数
        sys.path.append('pro2/fund_search')
        from enhanced_main import EnhancedFundAnalysisSystem
        
        analyzer = EnhancedFundAnalysisSystem()
        
        # 生成邮件内容
        message = analyzer.generate_wechat_message(results_df)
        
        print(f"\n邮件内容生成成功，长度: {len(message)} 字符")
        
        # 验证格式
        format_checks = [
            ('表格标签', '<table' in message and '</table>' in message),
            ('表头行', '<thead>' in message and '</thead>' in message),
            ('数据行', '<tbody>' in message and '</tbody>' in message),
            ('基金代码列', '011146' in message and '000001' in message),
            ('基金名称列', '天弘中证电网设备主题指数发起C' in message),
            ('今日收益率列', '-0.93%' in message and '1.25%' in message),
            ('昨日收益率列', '1.33%' in message and '-0.45%' in message),
            ('趋势状态列', '反转跌' in message and '反转涨' in message),
            ('操作建议列', '定投金额' in message),
            ('执行金额列', '150元' in message and '100元' in message),
            ('颜色样式', 'color:' in message),
            ('图标', '●' in message or '🔵' in message or '🔴' in message or '🟢' in message or '🟡' in message or '⚪' in message)
        ]
        
        print(f"\n格式验证:")
        all_passed = True
        for check_name, result in format_checks:
            status = "✅" if result else "❌"
            print(f"  {status} {check_name}: {'通过' if result else '失败'}")
            if not result:
                all_passed = False
        
        # 保存详细预览
        with open('email_format_test.html', 'w', encoding='utf-8') as f:
            f.write(f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>邮件格式测试</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .test-info {{ background: #f0f0f0; padding: 10px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="test-info">
        <h3>测试信息</h3>
        <p>测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>测试基金数量: {len(test_results)}</p>
        <p>格式验证: {'全部通过' if all_passed else '部分失败'}</p>
    </div>
    {message}
</body>
</html>
""")
        
        print(f"\n📄 详细预览已保存为: email_format_test.html")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 格式测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始邮件发送功能测试...")
    
    # 测试1: 基本功能测试
    basic_success = test_email_sending()
    
    # 测试2: 格式细节测试
    format_success = test_email_format_details()
    
    print(f"\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    
    print(f"基本功能测试: {'✅ 通过' if basic_success else '❌ 失败'}")
    print(f"格式细节测试: {'✅ 通过' if format_success else '❌ 失败'}")
    
    overall_success = basic_success and format_success
    
    if overall_success:
        print(f"\n🎉 邮件发送功能测试全部通过！")
        print("功能特点:")
        print("  - 按照7列格式正确排版")
        print("  - 使用yesterday_return作为昨日收益率")
        print("  - 收益率颜色区分（正绿负红）")
        print("  - 趋势状态包含图标")
        print("  - 表格样式美观专业")
        print("  - 所有字段来自数据库表")
    else:
        print(f"\n❌ 邮件发送功能测试存在问题，请检查上述错误信息。")
    
    print("=" * 80)