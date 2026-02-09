#!/usr/bin/env python
# coding: utf-8
"""
改进的数据源测试脚本
针对当前遇到的akshare和tushare问题进行优化测试
"""

import pandas as pd
import akshare as ak
import tushare as ts
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os
import requests
from functools import wraps

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Tushare Token (用户提供的)
TUSHARE_TOKEN = "5ff19facae0e5b26a407d491d33707a9884a39a714a0d76b6495725b"

# 测试基金代码
TEST_FUND_CODE = "021539"
TEST_FUND_NAME = "华安法国CAC40ETF发起式联接(QDII)A"

def retry_on_failure(max_retries=3, delay=1):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"尝试 {attempt + 1}/{max_retries} 失败: {e}，{delay}秒后重试...")
                        time.sleep(delay)
                    else:
                        logger.error(f"所有 {max_retries} 次尝试都失败了")
            raise last_exception
        return wrapper
    return decorator

class ImprovedDataSourceTester:
    """改进的数据源测试器"""
    
    def __init__(self):
        self.results = {
            'akshare': {},
            'tushare': {},
            'fallback': {}
        }
        # 初始化tushare
        try:
            ts.set_token(TUSHARE_TOKEN)
            self.pro = ts.pro_api()
            logger.info("Tushare 初始化成功")
        except Exception as e:
            logger.error(f"Tushare 初始化失败: {e}")
            self.pro = None
    
    @retry_on_failure(max_retries=3, delay=2)
    def test_akshare_basic_info_v2(self) -> Dict:
        """测试 akshare 获取基金基本信息 - 改进版本"""
        logger.info("=" * 60)
        logger.info("测试 Akshare - 基金基本信息 (改进版)")
        logger.info("=" * 60)
        
        result = {
            'success': False,
            'data': None,
            'error': None,
            'response_time': 0,
            'fields': [],
            'alternative_methods': []
        }
        
        start_time = time.time()
        
        # 方法1: 使用 fund_open_fund_info_em
        try:
            logger.info("尝试方法1: fund_open_fund_info_em")
            fund_info = ak.fund_open_fund_info_em(symbol=TEST_FUND_CODE, indicator="基本信息")
            
            if not fund_info.empty:
                result['success'] = True
                result['data'] = fund_info
                result['fields'] = fund_info.columns.tolist()
                result['response_time'] = round(time.time() - start_time, 3)
                
                logger.info(f"✓ 方法1成功: {len(fund_info)} 行数据")
                logger.info(f"✓ 字段: {result['fields']}")
                return result
        except Exception as e:
            logger.warning(f"方法1失败: {e}")
            result['alternative_methods'].append(f"方法1失败: {e}")
        
        # 方法2: 使用 fund_individual_basic_info_xq
        try:
            logger.info("尝试方法2: fund_individual_basic_info_xq")
            fund_info = ak.fund_individual_basic_info_xq(symbol=TEST_FUND_CODE)
            
            if not fund_info.empty:
                result['success'] = True
                result['data'] = fund_info
                result['fields'] = fund_info.columns.tolist()
                result['response_time'] = round(time.time() - start_time, 3)
                
                logger.info(f"✓ 方法2成功: {len(fund_info)} 行数据")
                logger.info(f"✓ 字段: {result['fields']}")
                return result
        except Exception as e:
            logger.warning(f"方法2失败: {e}")
            result['alternative_methods'].append(f"方法2失败: {e}")
        
        # 方法3: 使用 fund_name_em
        try:
            logger.info("尝试方法3: fund_name_em")
            fund_list = ak.fund_name_em()
            
            if not fund_list.empty:
                # 查找目标基金
                target_fund = fund_list[fund_list['基金代码'] == TEST_FUND_CODE]
                if not target_fund.empty:
                    result['success'] = True
                    result['data'] = target_fund
                    result['fields'] = target_fund.columns.tolist()
                    result['response_time'] = round(time.time() - start_time, 3)
                    
                    logger.info(f"✓ 方法3成功: 找到基金信息")
                    logger.info(f"✓ 字段: {result['fields']}")
                    return result
        except Exception as e:
            logger.warning(f"方法3失败: {e}")
            result['alternative_methods'].append(f"方法3失败: {e}")
        
        # 所有方法都失败
        result['error'] = "所有方法都失败"
        result['response_time'] = round(time.time() - start_time, 3)
        logger.error("✗ 所有akshare方法都失败")
        
        self.results['akshare']['basic_info'] = result
        return result
    
    @retry_on_failure(max_retries=3, delay=2)
    def test_akshare_nav_history_v2(self) -> Dict:
        """测试 akshare 获取历史净值 - 改进版本"""
        logger.info("\n" + "=" * 60)
        logger.info("测试 Akshare - 历史净值数据 (改进版)")
        logger.info("=" * 60)
        
        result = {
            'success': False,
            'data': None,
            'error': None,
            'response_time': 0,
            'fields': [],
            'data_count': 0,
            'date_range': None,
            'alternative_methods': []
        }
        
        start_time = time.time()
        
        # 方法1: 使用 fund_open_fund_info_em (单位净值走势)
        try:
            logger.info("尝试方法1: fund_open_fund_info_em (单位净值走势)")
            nav_history = ak.fund_open_fund_info_em(symbol=TEST_FUND_CODE, indicator="单位净值走势")
            
            if not nav_history.empty:
                result['success'] = True
                result['data'] = nav_history
                result['fields'] = nav_history.columns.tolist()
                result['data_count'] = len(nav_history)
                result['response_time'] = round(time.time() - start_time, 3)
                
                # 获取日期范围
                if '净值日期' in nav_history.columns:
                    nav_history['净值日期'] = pd.to_datetime(nav_history['净值日期'])
                    date_range = f"{nav_history['净值日期'].min().strftime('%Y-%m-%d')} ~ {nav_history['净值日期'].max().strftime('%Y-%m-%d')}"
                    result['date_range'] = date_range
                
                logger.info(f"✓ 方法1成功: {result['data_count']} 条数据")
                logger.info(f"✓ 日期范围: {result['date_range']}")
                logger.info(f"✓ 字段: {result['fields']}")
                return result
        except Exception as e:
            logger.warning(f"方法1失败: {e}")
            result['alternative_methods'].append(f"方法1失败: {e}")
        
        # 方法2: 使用 fund_open_fund_info_em (累计净值走势)
        try:
            logger.info("尝试方法2: fund_open_fund_info_em (累计净值走势)")
            nav_history = ak.fund_open_fund_info_em(symbol=TEST_FUND_CODE, indicator="累计净值走势")
            
            if not nav_history.empty:
                result['success'] = True
                result['data'] = nav_history
                result['fields'] = nav_history.columns.tolist()
                result['data_count'] = len(nav_history)
                result['response_time'] = round(time.time() - start_time, 3)
                
                # 获取日期范围
                if '净值日期' in nav_history.columns:
                    nav_history['净值日期'] = pd.to_datetime(nav_history['净值日期'])
                    date_range = f"{nav_history['净值日期'].min().strftime('%Y-%m-%d')} ~ {nav_history['净值日期'].max().strftime('%Y-%m-%d')}"
                    result['date_range'] = date_range
                
                logger.info(f"✓ 方法2成功: {result['data_count']} 条数据")
                logger.info(f"✓ 日期范围: {result['date_range']}")
                logger.info(f"✓ 字段: {result['fields']}")
                return result
        except Exception as e:
            logger.warning(f"方法2失败: {e}")
            result['alternative_methods'].append(f"方法2失败: {e}")
        
        # 方法3: 使用 fund_open_fund_daily_em (如果存在)
        try:
            logger.info("尝试方法3: fund_open_fund_daily_em")
            # 注意：这个函数可能不存在或参数不同
            nav_history = ak.fund_open_fund_daily_em(symbol=TEST_FUND_CODE)
            
            if not nav_history.empty:
                result['success'] = True
                result['data'] = nav_history
                result['fields'] = nav_history.columns.tolist()
                result['data_count'] = len(nav_history)
                result['response_time'] = round(time.time() - start_time, 3)
                
                logger.info(f"✓ 方法3成功: {result['data_count']} 条数据")
                return result
        except Exception as e:
            logger.warning(f"方法3失败: {e}")
            result['alternative_methods'].append(f"方法3失败: {e}")
        
        # 所有方法都失败
        result['error'] = "所有方法都失败"
        result['response_time'] = round(time.time() - start_time, 3)
        logger.error("✗ 所有akshare方法都失败")
        
        self.results['akshare']['nav_history'] = result
        return result
    
    def test_fallback_sources(self) -> Dict:
        """测试备用数据源"""
        logger.info("\n" + "=" * 60)
        logger.info("测试备用数据源")
        logger.info("=" * 60)
        
        result = {
            'success': False,
            'sources_tested': [],
            'working_sources': [],
            'failed_sources': [],
            'detailed_results': {}
        }
        
        # 测试新浪财经
        sina_result = self._test_sina_finance(TEST_FUND_CODE)
        result['sources_tested'].append('sina')
        result['detailed_results']['sina'] = sina_result
        if sina_result['success']:
            result['working_sources'].append('sina')
        else:
            result['failed_sources'].append(f"sina: {sina_result.get('error', 'Unknown error')}")
        
        # 测试天天基金网
        eastmoney_result = self._test_eastmoney(TEST_FUND_CODE)
        result['sources_tested'].append('eastmoney')
        result['detailed_results']['eastmoney'] = eastmoney_result
        if eastmoney_result['success']:
            result['working_sources'].append('eastmoney')
        else:
            result['failed_sources'].append(f"eastmoney: {eastmoney_result.get('error', 'Unknown error')}")
        
        # 判断是否有可用的备用源
        if result['working_sources']:
            result['success'] = True
            logger.info(f"✓ 找到 {len(result['working_sources'])} 个可用的备用数据源")
        else:
            logger.warning("✗ 没有可用的备用数据源")
        
        self.results['fallback'] = result
        return result
    
    def _test_sina_finance(self, fund_code: str) -> Dict:
        """测试新浪财经接口"""
        logger.info("测试新浪财经接口...")
        result = {
            'success': False,
            'error': None,
            'response_time': 0,
            'status_code': None,
            'can_parse_data': False,
            'sample_data': None
        }
        
        try:
            start_time = time.time()
            
            # 测试基础页面访问
            sina_url = f"http://finance.sina.com.cn/fund/quotes/{fund_code}/bc.shtml"
            response = requests.get(sina_url, timeout=10)
            result['response_time'] = round(time.time() - start_time, 3)
            result['status_code'] = response.status_code
            
            if response.status_code == 200:
                logger.info(f"✓ 新浪财经页面访问成功 (响应时间: {result['response_time']}s)")
                
                # 尝试解析基金实时数据
                try:
                    # 测试实时数据接口
                    sina_js_url = f"http://hq.sinajs.cn/list=f_{fund_code}"
                    js_response = requests.get(sina_js_url, timeout=10)
                    if js_response.status_code == 200 and js_response.text.strip():
                        result['can_parse_data'] = True
                        # 简单解析示例数据
                        content = js_response.text.strip()
                        if content and not content.endswith('"";'):
                            result['sample_data'] = content[:100] + "..." if len(content) > 100 else content
                        logger.info("✓ 新浪财经实时数据接口可用")
                    else:
                        logger.warning("⚠ 新浪财经实时数据接口无有效数据")
                except Exception as parse_e:
                    logger.warning(f"⚠ 新浪财经数据解析失败: {parse_e}")
                    result['error'] = f"数据解析失败: {parse_e}"
            else:
                logger.warning(f"✗ 新浪财经页面访问失败 (状态码: {response.status_code})")
                result['error'] = f"HTTP {response.status_code}"
                
        except Exception as e:
            result['error'] = str(e)
            result['response_time'] = round(time.time() - start_time, 3) if 'start_time' in locals() else 0
            logger.warning(f"✗ 新浪财经测试失败: {e}")
        
        result['success'] = result['can_parse_data'] or (result['status_code'] == 200 and not result['error'])
        return result
    
    def _test_eastmoney(self, fund_code: str) -> Dict:
        """测试天天基金网接口"""
        logger.info("测试天天基金网接口...")
        result = {
            'success': False,
            'error': None,
            'response_time': 0,
            'status_code': None,
            'can_parse_data': False,
            'sample_data': None
        }
        
        try:
            start_time = time.time()
            
            # 测试基础页面访问
            eastmoney_url = f"http://fund.eastmoney.com/{fund_code}.html"
            response = requests.get(eastmoney_url, timeout=10)
            result['response_time'] = round(time.time() - start_time, 3)
            result['status_code'] = response.status_code
            
            if response.status_code == 200:
                logger.info(f"✓ 天天基金网页面访问成功 (响应时间: {result['response_time']}s)")
                
                # 检查页面内容是否包含基金信息
                content = response.text
                if fund_code in content and ('基金' in content or 'NAV' in content):
                    result['can_parse_data'] = True
                    # 提取部分页面内容作为样本
                    result['sample_data'] = content[:200] + "..." if len(content) > 200 else content
                    logger.info("✓ 天天基金网页面包含有效基金数据")
                else:
                    logger.warning("⚠ 天天基金网页面内容异常或不包含基金信息")
            else:
                logger.warning(f"✗ 天天基金网页面访问失败 (状态码: {response.status_code})")
                result['error'] = f"HTTP {response.status_code}"
                
        except Exception as e:
            result['error'] = str(e)
            result['response_time'] = round(time.time() - start_time, 3) if 'start_time' in locals() else 0
            logger.warning(f"✗ 天天基金网测试失败: {e}")
        
        result['success'] = result['can_parse_data'] or (result['status_code'] == 200 and not result['error'])
        return result
    
    def generate_detailed_report(self) -> str:
        """生成详细报告"""
        report = []
        report.append("=" * 80)
        report.append("改进版数据源测试报告")
        report.append(f"测试基金: {TEST_FUND_NAME} ({TEST_FUND_CODE})")
        report.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        
        # Akshare 测试结果
        report.append("\n【1. Akshare 测试结果】")
        
        # 基本信息
        ak_basic = self.results.get('akshare', {}).get('basic_info', {})
        report.append(f"基本信息获取:")
        report.append(f"  状态: {'✓ 成功' if ak_basic.get('success') else '✗ 失败'}")
        if ak_basic.get('success'):
            report.append(f"    - 响应时间: {ak_basic.get('response_time')}s")
            report.append(f"    - 字段数: {len(ak_basic.get('fields', []))}")
            report.append(f"    - 数据预览: {ak_basic.get('data').head(1) if hasattr(ak_basic.get('data'), 'head') else 'N/A'}")
        else:
            report.append(f"    - 错误: {ak_basic.get('error')}")
            if ak_basic.get('alternative_methods'):
                report.append(f"    - 尝试的方法:")
                for method in ak_basic.get('alternative_methods', []):
                    report.append(f"      * {method}")
        
        # 历史净值
        ak_nav = self.results.get('akshare', {}).get('nav_history', {})
        report.append(f"历史净值获取:")
        report.append(f"  状态: {'✓ 成功' if ak_nav.get('success') else '✗ 失败'}")
        if ak_nav.get('success'):
            report.append(f"    - 响应时间: {ak_nav.get('response_time')}s")
            report.append(f"    - 数据条数: {ak_nav.get('data_count')}")
            report.append(f"    - 日期范围: {ak_nav.get('date_range')}")
        else:
            report.append(f"    - 错误: {ak_nav.get('error')}")
            if ak_nav.get('alternative_methods'):
                report.append(f"    - 尝试的方法:")
                for method in ak_nav.get('alternative_methods', []):
                    report.append(f"      * {method}")
        
        # Tushare 测试结果
        report.append("\n【2. Tushare 测试结果】")
        if self.pro:
            report.append("  状态: ✓ 初始化成功")
            report.append("  注意: 权限问题需要升级账户")
        else:
            report.append("  状态: ✗ 初始化失败")
            report.append("  原因: 可能是Token无效或网络问题")
        
        # 备用数据源
        fallback = self.results.get('fallback', {})
        report.append("\n【3. 备用数据源详细测试】")
        report.append(f"  测试源数量: {len(fallback.get('sources_tested', []))}")
        report.append(f"  可用源数量: {len(fallback.get('working_sources', []))}")
        report.append(f"  失败源数量: {len(fallback.get('failed_sources', []))}")
        
        # 详细结果
        detailed_results = fallback.get('detailed_results', {})
        
        # 新浪财经详细结果
        if 'sina' in detailed_results:
            sina_res = detailed_results['sina']
            report.append(f"\n  新浪财经 (sina):")
            report.append(f"    状态: {'✓ 可用' if sina_res.get('success') else '✗ 不可用'}")
            report.append(f"    响应时间: {sina_res.get('response_time', 0)}s")
            report.append(f"    HTTP状态码: {sina_res.get('status_code', 'N/A')}")
            report.append(f"    数据解析: {'✓ 可解析' if sina_res.get('can_parse_data') else '✗ 无法解析'}")
            if sina_res.get('sample_data'):
                report.append(f"    数据示例: {sina_res['sample_data']}")
            if sina_res.get('error'):
                report.append(f"    错误信息: {sina_res['error']}")
        
        # 天天基金网详细结果
        if 'eastmoney' in detailed_results:
            east_res = detailed_results['eastmoney']
            report.append(f"\n  天天基金网 (eastmoney):")
            report.append(f"    状态: {'✓ 可用' if east_res.get('success') else '✗ 不可用'}")
            report.append(f"    响应时间: {east_res.get('response_time', 0)}s")
            report.append(f"    HTTP状态码: {east_res.get('status_code', 'N/A')}")
            report.append(f"    数据解析: {'✓ 可解析' if east_res.get('can_parse_data') else '✗ 无法解析'}")
            if east_res.get('sample_data'):
                report.append(f"    数据示例: {east_res['sample_data']}")
            if east_res.get('error'):
                report.append(f"    错误信息: {east_res['error']}")
        
        # 总结
        if fallback.get('working_sources'):
            report.append(f"\n  ✓ 可用备用源: {', '.join(fallback.get('working_sources', []))}")
        if fallback.get('failed_sources'):
            report.append(f"  ✗ 失败备用源: {', '.join([fs.split(':')[0] for fs in fallback.get('failed_sources', [])])}")
        
        # 建议和解决方案
        report.append("\n【4. 建议和解决方案】")
        
        ak_success = ak_basic.get('success') or ak_nav.get('success')
        ts_available = self.pro is not None
        
        if ak_success:
            report.append("✓ Akshare 部分功能可用，建议继续使用")
        else:
            report.append("✗ Akshare 功能受限，需要考虑替代方案")
        
        if ts_available:
            report.append("⚠ Tushare 可用但权限受限，建议申请更高权限")
        else:
            report.append("✗ Tushare 不可用")
        
        if fallback.get('working_sources'):
            report.append("✓ 发现可用的备用数据源，可作为应急方案")
        else:
            report.append("✗ 没有可用的备用数据源")
        
        # 推荐的数据获取策略
        report.append("\n【5. 推荐数据获取策略】")
        if ak_success:
            report.append("1. 优先使用 Akshare 作为主要数据源")
            report.append("2. 实现重试机制和错误处理")
            report.append("3. 准备备用数据源作为兜底方案")
        elif fallback.get('working_sources'):
            report.append("1. 使用备用数据源作为主要方案")
            report.append("2. 同时申请 Tushare 更高权限")
            report.append("3. 开发网页爬虫获取公开数据")
        else:
            report.append("1. 立即申请 Tushare 更高权限")
            report.append("2. 开发自定义网页爬虫")
            report.append("3. 考虑购买专业数据服务")
        
        report.append("\n" + "=" * 80)
        return "\n".join(report)

def main():
    """主函数"""
    tester = ImprovedDataSourceTester()
    
    # 运行测试
    tester.test_akshare_basic_info_v2()
    tester.test_akshare_nav_history_v2()
    tester.test_fallback_sources()
    
    # 生成报告
    report = tester.generate_detailed_report()
    
    # 保存报告
    report_path = os.path.join(os.path.dirname(__file__), 'improved_data_source_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"\n详细报告已保存至: {report_path}")
    logger.info("\n" + report)

if __name__ == '__main__':
    main()