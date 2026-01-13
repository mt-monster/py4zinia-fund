# -*- coding: utf-8 -*-
"""
报告生成器
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: str = "reports"):
        """
        初始化报告生成器
        
        Args:
            output_dir: 报告输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_text_report(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        生成文本报告
        
        Args:
            data: 报告数据
            filename: 文件名（可选）
            
        Returns:
            报告文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"churn_report_{timestamp}.txt"
        
        filepath = self.output_dir / filename
        
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("客户流失预警分析报告")
        report_lines.append("=" * 60)
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # 数据概览
        if 'data_overview' in data:
            report_lines.append("一、数据概览")
            report_lines.append("-" * 60)
            for key, value in data['data_overview'].items():
                report_lines.append(f"  {key}: {value}")
            report_lines.append("")
        
        # 模型性能
        if 'model_performance' in data:
            report_lines.append("二、模型性能")
            report_lines.append("-" * 60)
            for key, value in data['model_performance'].items():
                report_lines.append(f"  {key}: {value}")
            report_lines.append("")
        
        # 关键发现
        if 'key_findings' in data:
            report_lines.append("三、关键发现")
            report_lines.append("-" * 60)
            for finding in data['key_findings']:
                report_lines.append(f"  • {finding}")
            report_lines.append("")
        
        # 风险客户统计
        if 'risk_statistics' in data:
            report_lines.append("四、风险客户统计")
            report_lines.append("-" * 60)
            for key, value in data['risk_statistics'].items():
                report_lines.append(f"  {key}: {value}")
            report_lines.append("")
        
        # 建议措施
        if 'recommendations' in data:
            report_lines.append("五、建议措施")
            report_lines.append("-" * 60)
            for i, rec in enumerate(data['recommendations'], 1):
                report_lines.append(f"  {i}. {rec}")
            report_lines.append("")
        
        report_lines.append("=" * 60)
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        return str(filepath)
    
    def generate_html_report(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        生成 HTML 报告
        
        Args:
            data: 报告数据
            filename: 文件名（可选）
            
        Returns:
            报告文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"churn_report_{timestamp}.html"
        
        filepath = self.output_dir / filename
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>客户流失预警分析报告</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .section {{
            margin: 20px 0;
            padding: 15px;
            background: #f9f9f9;
            border-left: 4px solid #667eea;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px 10px 0;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border-radius: 5px;
        }}
        ul {{
            list-style-type: none;
            padding-left: 0;
        }}
        li {{
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }}
        .timestamp {{
            color: #999;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>客户流失预警分析报告</h1>
        <p class="timestamp">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
"""
        
        # 数据概览
        if 'data_overview' in data:
            html_content += """
        <div class="section">
            <h2>一、数据概览</h2>
"""
            for key, value in data['data_overview'].items():
                html_content += f'            <div class="metric">{key}: {value}</div>\n'
            html_content += "        </div>\n"
        
        # 模型性能
        if 'model_performance' in data:
            html_content += """
        <div class="section">
            <h2>二、模型性能</h2>
"""
            for key, value in data['model_performance'].items():
                html_content += f'            <div class="metric">{key}: {value}</div>\n'
            html_content += "        </div>\n"
        
        # 关键发现
        if 'key_findings' in data:
            html_content += """
        <div class="section">
            <h2>三、关键发现</h2>
            <ul>
"""
            for finding in data['key_findings']:
                html_content += f'                <li>• {finding}</li>\n'
            html_content += "            </ul>\n        </div>\n"
        
        # 风险客户统计
        if 'risk_statistics' in data:
            html_content += """
        <div class="section">
            <h2>四、风险客户统计</h2>
"""
            for key, value in data['risk_statistics'].items():
                html_content += f'            <div class="metric">{key}: {value}</div>\n'
            html_content += "        </div>\n"
        
        # 建议措施
        if 'recommendations' in data:
            html_content += """
        <div class="section">
            <h2>五、建议措施</h2>
            <ol>
"""
            for rec in data['recommendations']:
                html_content += f'                <li>{rec}</li>\n'
            html_content += "            </ol>\n        </div>\n"
        
        html_content += """
    </div>
</body>
</html>
"""
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(filepath)

