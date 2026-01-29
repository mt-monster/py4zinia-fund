"""
基金分析系统测试套件
===================

本测试套件覆盖项目核心功能，包括：
- API接口测试
- 数据检索测试
- 回测引擎测试
- 策略分析测试
- 数据库操作测试
"""

import os
import sys

# 添加项目根目录到Python路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# 测试配置
TEST_CONFIG = {
    'TEST_DB_NAME': 'fund_test_db',
    'TEST_DATA_DIR': os.path.join(os.path.dirname(__file__), 'test_data'),
    'REPORT_DIR': os.path.join(os.path.dirname(__file__), 'reports'),
    'LOG_DIR': os.path.join(os.path.dirname(__file__), 'logs'),
}

# 确保目录存在
for dir_path in [TEST_CONFIG['TEST_DATA_DIR'], TEST_CONFIG['REPORT_DIR'], TEST_CONFIG['LOG_DIR']]:
    os.makedirs(dir_path, exist_ok=True)
