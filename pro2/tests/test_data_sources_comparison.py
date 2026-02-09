#!/usr/bin/env python
# coding: utf-8
"""
数据源对比测试脚本
对比 akshare 和 tushare 获取基金数据的能力
测试基金: 华安法国CAC40ETF发起式联接(QDII)A (021539)
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


class DataSourceTester:
    """数据源测试器"""
    
    def __init__(self):
        self.results = {
            'akshare': {},
            'tushare': {}
        }
        # 初始化tushare
        try:
            ts.set_token(TUSHARE_TOKEN)
            self.pro = ts.pro_api()
            logger.info("Tushare 初始化成功")
        except Exception as e:
            logger.error(f"Tushare 初始化失败: {e}")
            self.pro = None
    
    def test_akshare_basic_info(self) -> Dict:
        """测试 akshare 获取基金基本信息"""
        logger.info("=" * 60)
        logger.info("测试 Akshare - 基金基本信息")
        logger.info("=" * 60)
        
        result = {
            'success': False,
            'data': None,
            'error': None,
            'response_time': 0,
            'fields': []
        }
        
        try:
            start_time = time.time()
            
            # 使用 akshare 获取基金基本信息
            fund_info = ak.fund_open_fund_info_em(symbol=TEST_FUND_CODE, indicator="基本信息")
            
            result['response_time'] = round(time.time() - start_time, 3)
            
            if fund_info.empty:
                result['error'] = "返回空数据"
                logger.warning("Akshare 返回空数据")
            else:
                result['success'] = True
                result['data'] = fund_info
                result['fields'] = fund_info.columns.tolist()
                
                logger.info(f"✓ 成功获取数据，字段: {result['fields']}")
                logger.info(f"✓ 响应时间: {result['response_time']}s")
                logger.info(f"数据预览:\n{fund_info.head()}")
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"✗ 获取失败: {e}")
        
        self.results['akshare']['basic_info'] = result
        return result
    
    def test_tushare_basic_info(self) -> Dict:
        """测试 tushare 获取基金基本信息"""
        logger.info("\n" + "=" * 60)
        logger.info("测试 Tushare - 基金基本信息")
        logger.info("=" * 60)
        
        result = {
            'success': False,
            'data': None,
            'error': None,
            'response_time': 0,
            'fields': []
        }
        
        if not self.pro:
            result['error'] = "Tushare 未初始化"
            logger.error("✗ Tushare 未初始化")
            self.results['tushare']['basic_info'] = result
            return result
        
        try:
            start_time = time.time()
            
            # 使用 tushare 获取基金基本信息
            fund_info = self.pro.fund_basic(ts_code=TEST_FUND_CODE)
            
            result['response_time'] = round(time.time() - start_time, 3)
            
            if fund_info.empty:
                result['error'] = "返回空数据"
                logger.warning("Tushare 返回空数据")
            else:
                result['success'] = True
                result['data'] = fund_info
                result['fields'] = fund_info.columns.tolist()
                
                logger.info(f"✓ 成功获取数据，字段: {result['fields']}")
                logger.info(f"✓ 响应时间: {result['response_time']}s")
                logger.info(f"数据预览:\n{fund_info.head()}")
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"✗ 获取失败: {e}")
        
        self.results['tushare']['basic_info'] = result
        return result
    
    def test_akshare_nav_history(self) -> Dict:
        """测试 akshare 获取历史净值"""
        logger.info("\n" + "=" * 60)
        logger.info("测试 Akshare - 历史净值数据")
        logger.info("=" * 60)
        
        result = {
            'success': False,
            'data': None,
            'error': None,
            'response_time': 0,
            'fields': [],
            'data_count': 0,
            'date_range': None
        }
        
        try:
            start_time = time.time()
            
            # 使用 akshare 获取基金历史净值
            nav_history = ak.fund_open_fund_daily_em(symbol=TEST_FUND_CODE)
            
            result['response_time'] = round(time.time() - start_time, 3)
            
            if nav_history.empty:
                result['error'] = "返回空数据"
                logger.warning("Akshare 返回空数据")
            else:
                result['success'] = True
                result['data'] = nav_history
                result['fields'] = nav_history.columns.tolist()
                result['data_count'] = len(nav_history)
                
                # 获取日期范围
                if '净值日期' in nav_history.columns:
                    date_range = f"{nav_history['净值日期'].min()} ~ {nav_history['净值日期'].max()}"
                else:
                    date_range = "未知"
                result['date_range'] = date_range
                
                logger.info(f"✓ 成功获取数据")
                logger.info(f"✓ 响应时间: {result['response_time']}s")
                logger.info(f"✓ 数据条数: {result['data_count']}")
                logger.info(f"✓ 日期范围: {date_range}")
                logger.info(f"✓ 字段: {result['fields']}")
                logger.info(f"数据预览:\n{nav_history.head(3)}")
                logger.info(f"...\n{nav_history.tail(3)}")
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"✗ 获取失败: {e}")
        
        self.results['akshare']['nav_history'] = result
        return result
    
    def test_tushare_nav_history(self) -> Dict:
        """测试 tushare 获取历史净值"""
        logger.info("\n" + "=" * 60)
        logger.info("测试 Tushare - 历史净值数据")
        logger.info("=" * 60)
        
        result = {
            'success': False,
            'data': None,
            'error': None,
            'response_time': 0,
            'fields': [],
            'data_count': 0,
            'date_range': None
        }
        
        if not self.pro:
            result['error'] = "Tushare 未初始化"
            logger.error("✗ Tushare 未初始化")
            self.results['tushare']['nav_history'] = result
            return result
        
        try:
            start_time = time.time()
            
            # 使用 tushare 获取基金净值
            # 注意：tushare的基金净值接口可能需要不同的代码格式
            nav_history = self.pro.fund_nav(ts_code=TEST_FUND_CODE)
            
            result['response_time'] = round(time.time() - start_time, 3)
            
            if nav_history.empty:
                result['error'] = "返回空数据"
                logger.warning("Tushare 返回空数据")
            else:
                result['success'] = True
                result['data'] = nav_history
                result['fields'] = nav_history.columns.tolist()
                result['data_count'] = len(nav_history)
                
                # 获取日期范围
                if 'nav_date' in nav_history.columns:
                    date_range = f"{nav_history['nav_date'].min()} ~ {nav_history['nav_date'].max()}"
                else:
                    date_range = "未知"
                result['date_range'] = date_range
                
                logger.info(f"✓ 成功获取数据")
                logger.info(f"✓ 响应时间: {result['response_time']}s")
                logger.info(f"✓ 数据条数: {result['data_count']}")
                logger.info(f"✓ 日期范围: {date_range}")
                logger.info(f"✓ 字段: {result['fields']}")
                logger.info(f"数据预览:\n{nav_history.head(3)}")
                logger.info(f"...\n{nav_history.tail(3)}")
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"✗ 获取失败: {e}")
        
        self.results['tushare']['nav_history'] = result
        return result
    
    def test_akshare_realtime(self) -> Dict:
        """测试 akshare 获取实时/最新数据"""
        logger.info("\n" + "=" * 60)
        logger.info("测试 Akshare - 实时/最新数据")
        logger.info("=" * 60)
        
        result = {
            'success': False,
            'data': None,
            'error': None,
            'response_time': 0,
            'fields': []
        }
        
        try:
            start_time = time.time()
            
            # 使用 akshare 获取基金实时数据
            # 对于 QDII 基金，使用开放式基金历史数据获取最新值
            realtime_data = ak.fund_open_fund_daily_em(symbol=TEST_FUND_CODE)
            
            result['response_time'] = round(time.time() - start_time, 3)
            
            if realtime_data.empty:
                result['error'] = "返回空数据"
                logger.warning("Akshare 返回空数据")
            else:
                # 取最新一条数据
                latest = realtime_data.iloc[-1]
                result['success'] = True
                result['data'] = latest
                result['fields'] = realtime_data.columns.tolist()
                
                logger.info(f"✓ 成功获取数据")
                logger.info(f"✓ 响应时间: {result['response_time']}s")
                logger.info(f"✓ 字段: {result['fields']}")
                logger.info(f"最新数据:\n{latest}")
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"✗ 获取失败: {e}")
        
        self.results['akshare']['realtime'] = result
        return result
    
    def test_tushare_realtime(self) -> Dict:
        """测试 tushare 获取实时/最新数据"""
        logger.info("\n" + "=" * 60)
        logger.info("测试 Tushare - 实时/最新数据")
        logger.info("=" * 60)
        
        result = {
            'success': False,
            'data': None,
            'error': None,
            'response_time': 0,
            'fields': []
        }
        
        if not self.pro:
            result['error'] = "Tushare 未初始化"
            logger.error("✗ Tushare 未初始化")
            self.results['tushare']['realtime'] = result
            return result
        
        try:
            start_time = time.time()
            
            # 使用 tushare 获取最新基金净值
            realtime_data = self.pro.fund_nav(ts_code=TEST_FUND_CODE, limit=1)
            
            result['response_time'] = round(time.time() - start_time, 3)
            
            if realtime_data.empty:
                result['error'] = "返回空数据"
                logger.warning("Tushare 返回空数据")
            else:
                latest = realtime_data.iloc[-1]
                result['success'] = True
                result['data'] = latest
                result['fields'] = realtime_data.columns.tolist()
                
                logger.info(f"✓ 成功获取数据")
                logger.info(f"✓ 响应时间: {result['response_time']}s")
                logger.info(f"✓ 字段: {result['fields']}")
                logger.info(f"最新数据:\n{latest}")
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"✗ 获取失败: {e}")
        
        self.results['tushare']['realtime'] = result
        return result
    
    def test_akshare_company_info(self) -> Dict:
        """测试 akshare 获取基金公司信息"""
        logger.info("\n" + "=" * 60)
        logger.info("测试 Akshare - 基金公司信息")
        logger.info("=" * 60)
        
        result = {
            'success': False,
            'data': None,
            'error': None,
            'response_time': 0,
            'fields': []
        }
        
        try:
            start_time = time.time()
            
            # 使用 akshare 获取基金公司列表
            company_info = ak.fund_manager_em()
            
            result['response_time'] = round(time.time() - start_time, 3)
            
            if company_info.empty:
                result['error'] = "返回空数据"
                logger.warning("Akshare 返回空数据")
            else:
                result['success'] = True
                result['data'] = company_info
                result['fields'] = company_info.columns.tolist()
                
                logger.info(f"✓ 成功获取数据")
                logger.info(f"✓ 响应时间: {result['response_time']}s")
                logger.info(f"✓ 字段: {result['fields']}")
                logger.info(f"数据条数: {len(company_info)}")
                logger.info(f"数据预览:\n{company_info.head(3)}")
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"✗ 获取失败: {e}")
        
        self.results['akshare']['company_info'] = result
        return result
    
    def test_stability(self, iterations: int = 5) -> Dict:
        """测试接口稳定性"""
        logger.info("\n" + "=" * 60)
        logger.info(f"测试稳定性 - 连续请求 {iterations} 次")
        logger.info("=" * 60)
        
        stability_result = {
            'akshare': {'success_count': 0, 'fail_count': 0, 'avg_time': 0, 'errors': []},
            'tushare': {'success_count': 0, 'fail_count': 0, 'avg_time': 0, 'errors': []}
        }
        
        # 测试 akshare
        logger.info("\n测试 Akshare 稳定性...")
        akshare_times = []
        for i in range(iterations):
            try:
                start = time.time()
                nav = ak.fund_open_fund_daily_em(symbol=TEST_FUND_CODE)
                elapsed = time.time() - start
                akshare_times.append(elapsed)
                stability_result['akshare']['success_count'] += 1
                logger.info(f"  第{i+1}次: {elapsed:.3f}s ✓")
                time.sleep(0.5)  # 避免请求过快
            except Exception as e:
                stability_result['akshare']['fail_count'] += 1
                stability_result['akshare']['errors'].append(str(e))
                logger.error(f"  第{i+1}次: ✗ {e}")
        
        if akshare_times:
            stability_result['akshare']['avg_time'] = round(sum(akshare_times) / len(akshare_times), 3)
        
        # 测试 tushare
        if self.pro:
            logger.info("\n测试 Tushare 稳定性...")
            tushare_times = []
            for i in range(iterations):
                try:
                    start = time.time()
                    nav = self.pro.fund_nav(ts_code=TEST_FUND_CODE, limit=10)
                    elapsed = time.time() - start
                    tushare_times.append(elapsed)
                    stability_result['tushare']['success_count'] += 1
                    logger.info(f"  第{i+1}次: {elapsed:.3f}s ✓")
                    time.sleep(0.5)
                except Exception as e:
                    stability_result['tushare']['fail_count'] += 1
                    stability_result['tushare']['errors'].append(str(e))
                    logger.error(f"  第{i+1}次: ✗ {e}")
            
            if tushare_times:
                stability_result['tushare']['avg_time'] = round(sum(tushare_times) / len(tushare_times), 3)
        
        # 输出稳定性报告
        logger.info("\n" + "=" * 60)
        logger.info("稳定性测试报告")
        logger.info("=" * 60)
        for source, data in stability_result.items():
            total = data['success_count'] + data['fail_count']
            success_rate = (data['success_count'] / total * 100) if total > 0 else 0
            logger.info(f"\n{source.upper()}:")
            logger.info(f"  成功率: {success_rate:.1f}% ({data['success_count']}/{total})")
            logger.info(f"  平均响应: {data['avg_time']}s")
            if data['errors']:
                logger.info(f"  错误类型: {set(data['errors'])}")
        
        self.results['stability'] = stability_result
        return stability_result
    
    def generate_report(self) -> str:
        """生成对比报告"""
        report = []
        report.append("=" * 80)
        report.append("数据源对比测试报告")
        report.append(f"测试基金: {TEST_FUND_NAME} ({TEST_FUND_CODE})")
        report.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        
        # 基本信息对比
        report.append("\n【1. 基金基本信息获取】")
        ak_basic = self.results.get('akshare', {}).get('basic_info', {})
        ts_basic = self.results.get('tushare', {}).get('basic_info', {})
        
        report.append(f"Akshare: {'✓ 成功' if ak_basic.get('success') else '✗ 失败'}")
        if ak_basic.get('success'):
            report.append(f"  - 响应时间: {ak_basic.get('response_time')}s")
            report.append(f"  - 字段数: {len(ak_basic.get('fields', []))}")
        if ak_basic.get('error'):
            report.append(f"  - 错误: {ak_basic.get('error')}")
        
        report.append(f"Tushare: {'✓ 成功' if ts_basic.get('success') else '✗ 失败'}")
        if ts_basic.get('success'):
            report.append(f"  - 响应时间: {ts_basic.get('response_time')}s")
            report.append(f"  - 字段数: {len(ts_basic.get('fields', []))}")
        if ts_basic.get('error'):
            report.append(f"  - 错误: {ts_basic.get('error')}")
        
        # 历史净值对比
        report.append("\n【2. 历史净值数据获取】")
        ak_nav = self.results.get('akshare', {}).get('nav_history', {})
        ts_nav = self.results.get('tushare', {}).get('nav_history', {})
        
        report.append(f"Akshare: {'✓ 成功' if ak_nav.get('success') else '✗ 失败'}")
        if ak_nav.get('success'):
            report.append(f"  - 响应时间: {ak_nav.get('response_time')}s")
            report.append(f"  - 数据条数: {ak_nav.get('data_count')}")
            report.append(f"  - 日期范围: {ak_nav.get('date_range')}")
        if ak_nav.get('error'):
            report.append(f"  - 错误: {ak_nav.get('error')}")
        
        report.append(f"Tushare: {'✓ 成功' if ts_nav.get('success') else '✗ 失败'}")
        if ts_nav.get('success'):
            report.append(f"  - 响应时间: {ts_nav.get('response_time')}s")
            report.append(f"  - 数据条数: {ts_nav.get('data_count')}")
            report.append(f"  - 日期范围: {ts_nav.get('date_range')}")
        if ts_nav.get('error'):
            report.append(f"  - 错误: {ts_nav.get('error')}")
        
        # 稳定性对比
        report.append("\n【3. 接口稳定性测试】")
        stability = self.results.get('stability', {})
        for source, data in stability.items():
            total = data['success_count'] + data['fail_count']
            success_rate = (data['success_count'] / total * 100) if total > 0 else 0
            report.append(f"{source.upper()}:")
            report.append(f"  - 成功率: {success_rate:.1f}%")
            report.append(f"  - 平均响应: {data['avg_time']}s")
        
        report.append("\n" + "=" * 80)
        return "\n".join(report)


def main():
    """主函数"""
    tester = DataSourceTester()
    
    # 运行各项测试
    tester.test_akshare_basic_info()
    tester.test_tushare_basic_info()
    
    tester.test_akshare_nav_history()
    tester.test_tushare_nav_history()
    
    tester.test_akshare_realtime()
    tester.test_tushare_realtime()
    
    tester.test_akshare_company_info()
    
    tester.test_stability(iterations=5)
    
    # 生成报告
    report = tester.generate_report()
    
    # 保存报告
    report_path = os.path.join(os.path.dirname(__file__), 'data_source_comparison_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"\n报告已保存至: {report_path}")
    logger.info("\n" + report)


if __name__ == '__main__':
    main()
