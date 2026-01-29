"""
测试报告生成器
生成详细的测试报告和统计信息
"""

import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class TestReportGenerator:
    """测试报告生成器"""
    
    def __init__(self, report_dir: str = "reports"):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def generate_html_report(self, test_results: Dict[str, Any]) -> str:
        """生成HTML测试报告"""
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>基金分析系统 - 测试报告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}
        
        .header .meta {{
            opacity: 0.9;
            font-size: 0.9rem;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .summary-card {{
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .summary-card .number {{
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }}
        
        .summary-card .label {{
            color: #666;
            font-size: 0.9rem;
        }}
        
        .summary-card.passed .number {{ color: #52c41a; }}
        .summary-card.failed .number {{ color: #f5222d; }}
        .summary-card.warning .number {{ color: #faad14; }}
        .summary-card.info .number {{ color: #1890ff; }}
        
        .details {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem 2rem;
        }}
        
        .section {{
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .section h2 {{
            color: #333;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #f0f0f0;
        }}
        
        .test-list {{
            list-style: none;
        }}
        
        .test-item {{
            padding: 0.75rem 1rem;
            border-radius: 6px;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .test-item.passed {{
            background: #f6ffed;
            border: 1px solid #b7eb8f;
        }}
        
        .test-item.failed {{
            background: #fff1f0;
            border: 1px solid #ffa39e;
        }}
        
        .test-item.skipped {{
            background: #fffbe6;
            border: 1px solid #ffe58f;
        }}
        
        .test-name {{
            font-weight: 500;
        }}
        
        .test-status {{
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
        }}
        
        .test-status.passed {{
            background: #52c41a;
            color: white;
        }}
        
        .test-status.failed {{
            background: #f5222d;
            color: white;
        }}
        
        .test-status.skipped {{
            background: #faad14;
            color: white;
        }}
        
        .duration {{
            color: #666;
            font-size: 0.85rem;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #f0f0f0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 1rem;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #52c41a, #73d13d);
            border-radius: 4px;
            transition: width 0.3s ease;
        }}
        
        .coverage-section {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
        }}
        
        .coverage-item {{
            text-align: center;
            padding: 1rem;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        
        .coverage-value {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #1890ff;
        }}
        
        .coverage-label {{
            font-size: 0.85rem;
            color: #666;
            margin-top: 0.25rem;
        }}
        
        .error-details {{
            background: #fff1f0;
            border: 1px solid #ffa39e;
            border-radius: 6px;
            padding: 1rem;
            margin-top: 0.5rem;
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
            white-space: pre-wrap;
            overflow-x: auto;
        }}
        
        .footer {{
            text-align: center;
            padding: 2rem;
            color: #666;
            font-size: 0.85rem;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>基金分析系统 - 测试报告</h1>
        <div class="meta">
            生成时间: {test_results.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))} | 
            版本: {test_results.get('version', '1.0.0')}
        </div>
    </div>
    
    <div class="summary">
        <div class="summary-card passed">
            <div class="number">{test_results.get('passed', 0)}</div>
            <div class="label">通过</div>
        </div>
        <div class="summary-card failed">
            <div class="number">{test_results.get('failed', 0)}</div>
            <div class="label">失败</div>
        </div>
        <div class="summary-card warning">
            <div class="number">{test_results.get('skipped', 0)}</div>
            <div class="label">跳过</div>
        </div>
        <div class="summary-card info">
            <div class="number">{test_results.get('total', 0)}</div>
            <div class="label">总计</div>
        </div>
    </div>
    
    <div class="details">
        <div class="section">
            <h2>执行摘要</h2>
            <p><strong>总耗时:</strong> {test_results.get('duration', 'N/A')}</p>
            <p><strong>成功率:</strong> {test_results.get('pass_rate', '0')}%</p>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {test_results.get('pass_rate', 0)}%"></div>
            </div>
        </div>
"""
        
        # 添加覆盖率信息
        if 'coverage' in test_results:
            html_content += """
        <div class="section">
            <h2>代码覆盖率</h2>
            <div class="coverage-section">
"""
            for key, value in test_results['coverage'].items():
                html_content += f"""
                <div class="coverage-item">
                    <div class="coverage-value">{value}%</div>
                    <div class="coverage-label">{key}</div>
                </div>
"""
            html_content += """
            </div>
        </div>
"""
        
        # 添加测试详情
        if 'tests' in test_results:
            html_content += """
        <div class="section">
            <h2>测试详情</h2>
            <ul class="test-list">
"""
            for test in test_results['tests']:
                status = test.get('status', 'unknown')
                html_content += f"""
                <li class="test-item {status}">
                    <div>
                        <div class="test-name">{test.get('name', 'Unknown')}</div>
                        <div class="duration">{test.get('duration', 'N/A')}</div>
                    </div>
                    <span class="test-status {status}">{status.upper()}</span>
                </li>
"""
                if status == 'failed' and 'error' in test:
                    html_content += f"""
                <div class="error-details">{test['error']}</div>
"""
            html_content += """
            </ul>
        </div>
"""
        
        html_content += """
    </div>
    
    <div class="footer">
        <p>基金分析系统测试报告 &copy; 2024</p>
        <p>自动生成 by CI/CD Pipeline</p>
    </div>
</body>
</html>
"""
        
        # 保存报告
        report_path = self.report_dir / f"test_report_{self.timestamp}.html"
        report_path.write_text(html_content, encoding='utf-8')
        
        return str(report_path)
    
    def parse_junit_xml(self, xml_path: str) -> Dict[str, Any]:
        """解析JUnit XML报告"""
        
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        results = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'duration': '0s',
            'tests': []
        }
        
        # 解析testsuites或testsuite
        if root.tag == 'testsuites':
            for testsuite in root.findall('testsuite'):
                self._parse_testsuite(testsuite, results)
        elif root.tag == 'testsuite':
            self._parse_testsuite(root, results)
        
        # 计算成功率
        if results['total'] > 0:
            results['pass_rate'] = round(results['passed'] / results['total'] * 100, 2)
        else:
            results['pass_rate'] = 0
        
        return results
    
    def _parse_testsuite(self, testsuite: ET.Element, results: Dict[str, Any]):
        """解析单个测试套件"""
        
        results['total'] += int(testsuite.get('tests', 0))
        results['failed'] += int(testsuite.get('failures', 0))
        results['skipped'] += int(testsuite.get('skipped', 0))
        results['passed'] += int(testsuite.get('tests', 0)) - int(testsuite.get('failures', 0)) - int(testsuite.get('skipped', 0))
        
        for testcase in testsuite.findall('testcase'):
            test_info = {
                'name': testcase.get('name', 'Unknown'),
                'classname': testcase.get('classname', ''),
                'duration': f"{float(testcase.get('time', 0)):.3f}s",
                'status': 'passed'
            }
            
            # 检查失败
            failure = testcase.find('failure')
            if failure is not None:
                test_info['status'] = 'failed'
                test_info['error'] = failure.text or failure.get('message', 'Unknown error')
            
            # 检查跳过
            skipped = testcase.find('skipped')
            if skipped is not None:
                test_info['status'] = 'skipped'
            
            results['tests'].append(test_info)
    
    def parse_coverage_xml(self, xml_path: str) -> Dict[str, float]:
        """解析覆盖率XML报告"""
        
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        coverage = {}
        
        # 解析覆盖率数据
        for package in root.findall('.//package'):
            package_name = package.get('name', 'unknown')
            
            for classs in package.findall('class'):
                class_name = classs.get('name', 'unknown')
                
                # 计算行覆盖率
                lines = classs.find('lines')
                if lines is not None:
                    total_lines = len(lines.findall('line'))
                    hit_lines = len([l for l in lines.findall('line') if int(l.get('hits', 0)) > 0])
                    
                    if total_lines > 0:
                        coverage[f"{package_name}.{class_name}"] = round(hit_lines / total_lines * 100, 2)
        
        return coverage
    
    def generate_summary_json(self, test_results: Dict[str, Any]) -> str:
        """生成JSON格式的摘要报告"""
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': test_results.get('total', 0),
                'passed': test_results.get('passed', 0),
                'failed': test_results.get('failed', 0),
                'skipped': test_results.get('skipped', 0),
                'pass_rate': test_results.get('pass_rate', 0),
                'duration': test_results.get('duration', 'N/A')
            }
        }
        
        if 'coverage' in test_results:
            summary['coverage'] = test_results['coverage']
        
        # 保存JSON
        json_path = self.report_dir / f"test_summary_{self.timestamp}.json"
        json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
        
        return str(json_path)


def main():
    """主函数 - 用于命令行调用"""
    import argparse
    
    parser = argparse.ArgumentParser(description='测试报告生成器')
    parser.add_argument('--junit-xml', help='JUnit XML报告路径')
    parser.add_argument('--coverage-xml', help='覆盖率XML报告路径')
    parser.add_argument('--output-dir', default='reports', help='输出目录')
    
    args = parser.parse_args()
    
    generator = TestReportGenerator(args.output_dir)
    
    # 解析测试结果
    if args.junit_xml and os.path.exists(args.junit_xml):
        results = generator.parse_junit_xml(args.junit_xml)
        
        # 解析覆盖率
        if args.coverage_xml and os.path.exists(args.coverage_xml):
            results['coverage'] = generator.parse_coverage_xml(args.coverage_xml)
        
        # 生成报告
        html_path = generator.generate_html_report(results)
        json_path = generator.generate_summary_json(results)
        
        print(f"HTML报告已生成: {html_path}")
        print(f"JSON摘要已生成: {json_path}")
    else:
        print("错误: 未找到JUnit XML报告文件")
        exit(1)


if __name__ == '__main__':
    main()
