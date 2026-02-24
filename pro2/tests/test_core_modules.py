#!/usr/bin/env python
# coding: utf-8

"""
单元测试 - 核心模块测试
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fund_search.shared.exceptions import (
    FundAnalysisException, FundNotFoundError, ValidationError,
    DataSourceError, DatabaseError, ErrorCode
)
from fund_search.services.db_optimizer import (
    VectorizedProfitCalculator, BatchDatabaseOperations
)
from fund_search.services.parallel_fetcher import ParallelDataFetcher, BatchFetchResult


class TestExceptions(unittest.TestCase):
    """异常类测试"""
    
    def test_fund_not_found_error(self):
        """测试基金未找到异常"""
        error = FundNotFoundError("000001")
        
        self.assertEqual(error.code, ErrorCode.FUND_NOT_FOUND)
        self.assertEqual(error.http_status, 404)
        self.assertIn("000001", error.message)
        
        result = error.to_dict()
        self.assertFalse(result['success'])
        self.assertEqual(result['error']['code'], 'FUND_NOT_FOUND')
    
    def test_validation_error(self):
        """测试验证异常"""
        error = ValidationError("fund_code", "abc", "必须是6位数字")
        
        self.assertEqual(error.code, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(error.http_status, 400)
        self.assertIn("fund_code", error.message)
    
    def test_data_source_error(self):
        """测试数据源异常"""
        error = DataSourceError("tushare", "连接超时", retry_after=60)
        
        self.assertEqual(error.http_status, 429)
        self.assertIn("retry_after", error.details)
    
    def test_exception_to_dict(self):
        """测试异常转换为字典"""
        error = FundNotFoundError("000001")
        result = error.to_dict()
        
        self.assertIn('success', result)
        self.assertIn('error', result)
        self.assertIn('code', result['error'])
        self.assertIn('message', result['error'])


class TestVectorizedProfitCalculator(unittest.TestCase):
    """向量化盈亏计算器测试"""
    
    def setUp(self):
        """设置测试数据"""
        self.calculator = VectorizedProfitCalculator()
        
        self.test_df = pd.DataFrame({
            'holding_shares': [1000.0, 2000.0, 0.0, np.nan],
            'cost_price': [1.5, 2.0, 1.0, 1.5],
            'holding_amount': [1500.0, 4000.0, np.nan, np.nan],
            'current_nav': [1.6, 1.9, 1.1, 1.5],
            'previous_nav': [1.55, 2.0, 1.0, 1.5]
        })
    
    def test_calculate_profits(self):
        """测试盈亏计算"""
        result = self.calculator.calculate_profits(self.test_df)
        
        self.assertIsInstance(result.holding_amount, pd.Series)
        self.assertIsInstance(result.today_profit, pd.Series)
        self.assertIsInstance(result.holding_profit, pd.Series)
        
        self.assertAlmostEqual(result.today_profit[0], 50.0, places=1)
        self.assertAlmostEqual(result.holding_profit[0], 100.0, places=1)
    
    def test_format_performance_metrics(self):
        """测试绩效指标格式化"""
        df = pd.DataFrame({
            'annualized_return': [0.15, 0.20],
            'max_drawdown': [-0.10, -0.15],
            'sharpe_ratio': [1.5, 2.0],
            'today_return': [1.5, 2.0]
        })
        
        result = self.calculator.format_performance_metrics(df)
        
        self.assertAlmostEqual(result['annualized_return'][0], 15.0, places=1)
        self.assertAlmostEqual(result['max_drawdown'][0], -10.0, places=1)
    
    def test_clean_nan_values(self):
        """测试NaN值清理"""
        df = pd.DataFrame({
            'value': [1.0, np.nan, np.inf, 4.0],
            'name': ['a', 'b', 'c', 'd']
        })
        
        result = self.calculator.clean_nan_values(df)
        
        self.assertEqual(result['value'][0], 1.0)
        self.assertIsNone(result['value'][1])
        self.assertIsNone(result['value'][2])


class TestBatchDatabaseOperations(unittest.TestCase):
    """批量数据库操作测试"""
    
    def setUp(self):
        self.ops = BatchDatabaseOperations()
    
    def test_prepare_batch_insert(self):
        """测试批量插入准备"""
        records = [{'id': i, 'name': f'test_{i}'} for i in range(100)]
        
        chunks = self.ops.prepare_batch_insert(records, 'test_table', chunk_size=30)
        
        self.assertEqual(len(chunks), 4)
        self.assertEqual(len(chunks[0][1]), 30)
    
    def test_generate_upsert_sql(self):
        """测试UPSERT SQL生成"""
        sql = self.ops.generate_upsert_sql(
            table_name='fund_data',
            columns=['fund_code', 'nav', 'date'],
            unique_keys=['fund_code', 'date']
        )
        
        self.assertIn('INSERT INTO fund_data', sql)
        self.assertIn('ON DUPLICATE KEY UPDATE', sql)


class TestParallelDataFetcher(unittest.TestCase):
    """并行数据获取器测试"""
    
    def setUp(self):
        self.fetcher = ParallelDataFetcher(
            max_workers=2,
            rate_limit_per_second=10.0,
            max_retries=2
        )
    
    def test_fetch_single_success(self):
        """测试单次获取成功"""
        def mock_fetch(fund_code):
            return {'fund_code': fund_code, 'nav': 1.5}
        
        result = self.fetcher.fetch_single(mock_fetch, '000001')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['fund_code'], '000001')
    
    def test_fetch_single_failure(self):
        """测试单次获取失败"""
        def mock_fetch(fund_code):
            raise Exception("获取失败")
        
        result = self.fetcher.fetch_single(mock_fetch, '000001')
        
        self.assertIsNone(result)
    
    def test_fetch_batch(self):
        """测试批量获取"""
        def mock_fetch(fund_code):
            return {'fund_code': fund_code, 'nav': 1.5}
        
        fund_codes = ['000001', '000002', '000003']
        result = self.fetcher.fetch_batch(fund_codes, mock_fetch)
        
        self.assertIsInstance(result, BatchFetchResult)
        self.assertEqual(result.success_count, 3)
        self.assertEqual(result.fail_count, 0)


class TestErrorCode(unittest.TestCase):
    """错误代码测试"""
    
    def test_error_code_values(self):
        """测试错误代码值"""
        self.assertEqual(ErrorCode.FUND_NOT_FOUND.value, "FUND_NOT_FOUND")
        self.assertEqual(ErrorCode.DATA_SOURCE_ERROR.value, "DATA_SOURCE_ERROR")
        self.assertEqual(ErrorCode.DATABASE_ERROR.value, "DATABASE_ERROR")
    
    def test_error_code_count(self):
        """测试错误代码数量"""
        codes = list(ErrorCode)
        self.assertGreater(len(codes), 10)


if __name__ == '__main__':
    unittest.main(verbosity=2)
