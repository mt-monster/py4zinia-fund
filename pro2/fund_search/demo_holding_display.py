#!/usr/bin/env python
# coding: utf-8

"""
演示如何在界面中显示持仓信息
"""

def format_holding_display_data():
    """格式化持仓显示数据"""
    
    # 模拟从API获取的持仓识别结果
    api_response = {
        "success": True,
        "data": [
            {
                "fund_code": "007721",
                "fund_name": "天弘标普500发起(QDII-FOF)A",
                "confidence": 0.8,
                "source": "name_match",
                "original_text": "天弘标普500发起(QDIIFOF)A",
                "holding_amount": 681.30,
                "profit_amount": 21.11,
                "profit_rate": 3.20,
                "nav_value": None,
                "current_value": 702.41
            },
            {
                "fund_code": "016667",
                "fund_name": "景顺长城全球半导体芯片股票A(QDII-LOF)(美元现汇)",
                "confidence": 0.8,
                "source": "name_match",
                "original_text": "景顺长城全球半导体芯片股票A(.",
                "holding_amount": 664.00,
                "profit_amount": 83.08,
                "profit_rate": 15.08,
                "nav_value": None,
                "current_value": 747.08
            },
            {
                "fund_code": "017512",
                "fund_name": "广发北证50成份指数A",
                "confidence": 0.8,
                "source": "name_match",
                "original_text": "广发北证50成份指数A",
                "holding_amount": 568.11,
                "profit_amount": 15.10,
                "profit_rate": 2.83,
                "nav_value": None,
                "current_value": 583.21
            },
            {
                "fund_code": "000157",
                "fund_name": "富国全球科技互联网股票(QDII)A(后端)",
                "confidence": 0.8,
                "source": "name_match",
                "original_text": "富国全球科技互联网股票(QDII)A",
                "holding_amount": 438.25,
                "profit_amount": 28.42,
                "profit_rate": 7.29,
                "nav_value": None,
                "current_value": 466.67
            },
            {
                "fund_code": "010391",
                "fund_name": "易方达战略新兴产业股票A",
                "confidence": 0.8,
                "source": "name_match",
                "original_text": "易方达战略新兴产业股票A",
                "holding_amount": 429.02,
                "profit_amount": 21.21,
                "profit_rate": 5.33,
                "nav_value": None,
                "current_value": 450.23
            }
        ],
        "portfolio_summary": {
            "total_funds": 5,
            "total_holding_amount": 2780.68,
            "total_profit_amount": 168.92,
            "total_current_value": 2949.60,
            "total_profit_rate": 6.07,
            "best_fund": {
                "fund_name": "景顺长城全球半导体芯片股票A...",
                "profit_rate": 15.08
            },
            "worst_fund": {
                "fund_name": "广发北证50成份指数A...",
                "profit_rate": 2.83
            }
        },
        "message": "成功识别 5 个基金，请确认信息后导入"
    }
    
    return api_response

def generate_html_table(data):
    """生成HTML表格"""
    
    html = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>基金持仓识别结果</title>
        <style>
            body {
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .success-banner {
                background: linear-gradient(135deg, #28a745, #20c997);
                color: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                text-align: center;
                font-size: 16px;
                font-weight: bold;
            }
            .summary-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            .summary-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }
            .summary-item {
                text-align: center;
            }
            .summary-value {
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            .summary-label {
                font-size: 14px;
                opacity: 0.9;
            }
            .fund-table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
                font-size: 14px;
            }
            .fund-table th, .fund-table td {
                border: 1px solid #ddd;
                padding: 12px;
                text-align: left;
            }
            .fund-table th {
                background-color: #f8f9fa;
                font-weight: bold;
                position: sticky;
                top: 0;
            }
            .fund-table tr:nth-child(even) {
                background-color: #f9f9f9;
            }
            .fund-table tr:hover {
                background-color: #e3f2fd;
            }
            .positive {
                color: #28a745;
                font-weight: bold;
            }
            .negative {
                color: #dc3545;
                font-weight: bold;
            }
            .fund-code {
                font-family: 'Courier New', monospace;
                font-weight: bold;
                color: #007bff;
            }
            .fund-name {
                max-width: 300px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .confidence-badge {
                background-color: #17a2b8;
                color: white;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 12px;
            }
            .source-badge {
                background-color: #6c757d;
                color: white;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 12px;
            }
            .performance-highlight {
                display: flex;
                justify-content: space-between;
                margin-top: 15px;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 6px;
            }
            .best-performer {
                color: #28a745;
                font-weight: bold;
            }
            .worst-performer {
                color: #dc3545;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 基金持仓识别结果</h1>
            
            <div class="success-banner">
                ✅ {message}
            </div>
            
            <!-- 投资组合汇总 -->
            <div class="summary-card">
                <h3>📈 投资组合汇总</h3>
                <div class="summary-grid">
                    <div class="summary-item">
                        <div class="summary-value">{total_funds}</div>
                        <div class="summary-label">基金数量</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value">¥{total_holding_amount:,.2f}</div>
                        <div class="summary-label">持仓成本</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value {profit_class}">¥{total_profit_amount:+,.2f}</div>
                        <div class="summary-label">盈亏金额</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value">¥{total_current_value:,.2f}</div>
                        <div class="summary-label">当前市值</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value {profit_class}">{total_profit_rate:+.2f}%</div>
                        <div class="summary-label">总盈亏率</div>
                    </div>
                </div>
                
                <div class="performance-highlight">
                    <div class="best-performer">
                        🏆 表现最佳: {best_fund_name} ({best_fund_rate:+.2f}%)
                    </div>
                    <div class="worst-performer">
                        📉 表现最差: {worst_fund_name} ({worst_fund_rate:+.2f}%)
                    </div>
                </div>
            </div>
            
            <!-- 基金详细列表 -->
            <h3>🎯 基金详细信息</h3>
            <table class="fund-table">
                <thead>
                    <tr>
                        <th>基金代码</th>
                        <th>基金名称</th>
                        <th>持仓金额</th>
                        <th>盈亏金额</th>
                        <th>盈亏率</th>
                        <th>当前市值</th>
                        <th>置信度</th>
                        <th>识别来源</th>
                        <th>原始文本</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    # 添加基金数据行
    for fund in data['data']:
        profit_class = 'positive' if fund['profit_amount'] >= 0 else 'negative'
        rate_class = 'positive' if fund['profit_rate'] >= 0 else 'negative'
        
        html += f"""
                    <tr>
                        <td class="fund-code">{fund['fund_code']}</td>
                        <td class="fund-name" title="{fund['fund_name']}">{fund['fund_name']}</td>
                        <td>¥{fund['holding_amount']:,.2f}</td>
                        <td class="{profit_class}">¥{fund['profit_amount']:+,.2f}</td>
                        <td class="{rate_class}">{fund['profit_rate']:+.2f}%</td>
                        <td>¥{fund['current_value']:,.2f}</td>
                        <td><span class="confidence-badge">{fund['confidence']*100:.1f}%</span></td>
                        <td><span class="source-badge">{fund['source']}</span></td>
                        <td title="{fund['original_text']}">{fund['original_text'][:20]}...</td>
                    </tr>
        """
    
    html += """
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    
    # 格式化HTML模板
    summary = data['portfolio_summary']
    profit_class = 'positive' if summary['total_profit_amount'] >= 0 else 'negative'
    
    # 使用字符串替换而不是format方法
    formatted_html = html.replace('{message}', data['message'])
    formatted_html = formatted_html.replace('{total_funds}', str(summary['total_funds']))
    formatted_html = formatted_html.replace('{total_holding_amount:,.2f}', f"{summary['total_holding_amount']:,.2f}")
    formatted_html = formatted_html.replace('{total_profit_amount:+,.2f}', f"{summary['total_profit_amount']:+,.2f}")
    formatted_html = formatted_html.replace('{total_current_value:,.2f}', f"{summary['total_current_value']:,.2f}")
    formatted_html = formatted_html.replace('{total_profit_rate:+.2f}', f"{summary['total_profit_rate']:+.2f}")
    formatted_html = formatted_html.replace('{profit_class}', profit_class)
    formatted_html = formatted_html.replace('{best_fund_name}', summary['best_fund']['fund_name'])
    formatted_html = formatted_html.replace('{best_fund_rate:+.2f}', f"{summary['best_fund']['profit_rate']:+.2f}")
    formatted_html = formatted_html.replace('{worst_fund_name}', summary['worst_fund']['fund_name'])
    formatted_html = formatted_html.replace('{worst_fund_rate:+.2f}', f"{summary['worst_fund']['profit_rate']:+.2f}")
    
    return formatted_html

def main():
    """主函数"""
    print("🎨 生成基金持仓识别结果展示页面...")
    
    # 获取模拟数据
    data = format_holding_display_data()
    
    # 生成HTML
    html_content = generate_html_table(data)
    
    # 保存HTML文件
    output_file = "web/templates/demo_holding_result.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ HTML文件已生成: {output_file}")
    print("💡 您可以在浏览器中打开此文件查看效果")
    
    # 显示数据摘要
    summary = data['portfolio_summary']
    print(f"\n📊 数据摘要:")
    print(f"  基金数量: {summary['total_funds']}")
    print(f"  持仓成本: ¥{summary['total_holding_amount']:,.2f}")
    print(f"  盈亏金额: ¥{summary['total_profit_amount']:+,.2f}")
    print(f"  当前市值: ¥{summary['total_current_value']:,.2f}")
    print(f"  总盈亏率: {summary['total_profit_rate']:+.2f}%")
    print(f"  表现最佳: {summary['best_fund']['fund_name']} ({summary['best_fund']['profit_rate']:+.2f}%)")
    print(f"  表现最差: {summary['worst_fund']['fund_name']} ({summary['worst_fund']['profit_rate']:+.2f}%)")

if __name__ == "__main__":
    main()