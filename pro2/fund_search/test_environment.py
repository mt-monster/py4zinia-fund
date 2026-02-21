#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的测试示例，用于验证测试环境是否正常工作
"""

import pytest
import pandas as pd
from datetime import datetime


def test_basic_functionality():
    """测试基本功能"""
    # 测试 pandas 是否正常工作
    df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    assert len(df) == 3
    assert df['a'].sum() == 6
    
    # 测试 datetime 是否正常工作
    now = datetime.now()
    assert isinstance(now, datetime)


def test_pandas_operations():
    """测试 pandas 操作"""
    # 创建测试数据
    data = {
        'fund_code': ['000001', '000002', '000003'],
        'nav': [1.5, 1.8, 2.1],
        'date': ['2024-01-01', '2024-01-02', '2024-01-03']
    }
    
    df = pd.DataFrame(data)
    
    # 测试基本操作
    assert df.shape == (3, 3)
    assert df['nav'].mean() == 1.8
    assert df['fund_code'].iloc[0] == '000001'


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])