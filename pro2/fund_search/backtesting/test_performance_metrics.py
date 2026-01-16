#!/usr/bin/env python
# coding: utf-8

"""
绩效指标计算测试
Tests for Performance Metrics Calculator

验证任务 4.4 的实现正确性：
- 计算总收益率、年化收益率
- 计算最大回撤、波动率
- 计算夏普比率、索提诺比率、卡玛比率
- 计算胜率、盈亏比
"""

import sys
import os
import math

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from backtesting.performance_metrics import (
    PerformanceCalculator, PerformanceMetrics, calculate_performance_metrics
)


def test_total_return_calculation():
    """测试总收益率计算"""
    print("\n=== 测试总收益率计算 ===")
    
    calculator = PerformanceCalculator()
    
    # 测试正收益
    values = [100, 110, 120, 130]
    total_return = calculator.calculate_total_return(values)
    expected = (130 - 100) / 100  # 0.3 = 30%
    assert abs(total_return - expected) < 1e-10, f"期望 {expected}, 得到 {total_return}"
    print(f"✓ 正收益测试通过: {total_return:.2%}")
    
    # 测试负收益
    values = [100, 90, 80, 70]
    total_return = calculator.calculate_total_return(values)
    expected = (70 - 100) / 100  # -0.3 = -30%
    assert abs(total_return - expected) < 1e-10, f"期望 {expected}, 得到 {total_return}"
    print(f"✓ 负收益测试通过: {total_return:.2%}")
    
    # 测试零收益
    values = [100, 100, 100, 100]
    total_return = calculator.calculate_total_return(values)
    assert abs(total_return) < 1e-10
    print(f"✓ 零收益测试通过: {total_return:.2%}")
    
    # 测试空列表
    total_return = calculator.calculate_total_return([])
    assert total_return == 0.0
    print("✓ 空列表测试通过")
    
    # 测试单个值
    total_return = calculator.calculate_total_return([100])
    assert total_return == 0.0
    print("✓ 单个值测试通过")
    
    return True


def test_annual_return_calculation():
    """测试年化收益率计算"""
    print("\n=== 测试年化收益率计算 ===")
    
    calculator = PerformanceCalculator()
    
    # 测试一年期收益
    total_return = 0.10  # 10%
    days = 365
    annual_return = calculator.calculate_annual_return(total_return, days)
    assert abs(annual_return - 0.10) < 1e-10, f"期望 0.10, 得到 {annual_return}"
    print(f"✓ 一年期收益测试通过: {annual_return:.2%}")
    
    # 测试半年期收益
    total_return = 0.05  # 5%
    days = 182  # 约半年
    annual_return = calculator.calculate_annual_return(total_return, days)
    # 年化收益率 = (1 + 0.05)^(365/182) - 1 ≈ 10.25%
    expected = (1 + 0.05) ** (365 / 182) - 1
    assert abs(annual_return - expected) < 1e-10, f"期望 {expected}, 得到 {annual_return}"
    print(f"✓ 半年期收益测试通过: {annual_return:.2%}")
    
    # 测试负收益
    total_return = -0.10  # -10%
    days = 365
    annual_return = calculator.calculate_annual_return(total_return, days)
    assert abs(annual_return - (-0.10)) < 1e-10
    print(f"✓ 负收益年化测试通过: {annual_return:.2%}")
    
    # 测试零天数
    annual_return = calculator.calculate_annual_return(0.10, 0)
    assert annual_return == 0.0
    print("✓ 零天数测试通过")
    
    # 测试完全亏损
    annual_return = calculator.calculate_annual_return(-1.0, 365)
    assert annual_return == -1.0
    print("✓ 完全亏损测试通过")
    
    return True


def test_max_drawdown_calculation():
    """测试最大回撤计算"""
    print("\n=== 测试最大回撤计算 ===")
    
    calculator = PerformanceCalculator()
    
    # 测试简单回撤
    values = [100, 110, 100, 90, 95]  # 从110跌到90，回撤 = (110-90)/110 = 18.18%
    max_dd = calculator.calculate_max_drawdown(values)
    expected = (110 - 90) / 110
    assert abs(max_dd - expected) < 1e-10, f"期望 {expected}, 得到 {max_dd}"
    print(f"✓ 简单回撤测试通过: {max_dd:.2%}")
    
    # 测试多次回撤取最大值
    values = [100, 120, 100, 130, 100]  # 两次回撤：16.67% 和 23.08%
    max_dd = calculator.calculate_max_drawdown(values)
    expected = (130 - 100) / 130  # 23.08%
    assert abs(max_dd - expected) < 1e-10, f"期望 {expected}, 得到 {max_dd}"
    print(f"✓ 多次回撤测试通过: {max_dd:.2%}")
    
    # 测试无回撤（持续上涨）
    values = [100, 110, 120, 130, 140]
    max_dd = calculator.calculate_max_drawdown(values)
    assert max_dd == 0.0
    print("✓ 无回撤测试通过")
    
    # 测试空列表
    max_dd = calculator.calculate_max_drawdown([])
    assert max_dd == 0.0
    print("✓ 空列表测试通过")
    
    return True


def test_volatility_calculation():
    """测试波动率计算"""
    print("\n=== 测试波动率计算 ===")
    
    calculator = PerformanceCalculator()
    
    # 测试正常波动率
    values = [100, 102, 98, 103, 97, 105]
    daily_returns = calculator.calculate_daily_returns(values)
    volatility = calculator.calculate_volatility(daily_returns)
    
    # 手动计算验证
    expected_std = np.std(daily_returns)
    expected_vol = expected_std * np.sqrt(252)
    assert abs(volatility - expected_vol) < 1e-10, f"期望 {expected_vol}, 得到 {volatility}"
    print(f"✓ 正常波动率测试通过: {volatility:.2%}")
    
    # 测试零波动率（价格不变）
    values = [100, 100, 100, 100]
    daily_returns = calculator.calculate_daily_returns(values)
    volatility = calculator.calculate_volatility(daily_returns)
    assert volatility == 0.0
    print("✓ 零波动率测试通过")
    
    # 测试空数组
    volatility = calculator.calculate_volatility(np.array([]))
    assert volatility == 0.0
    print("✓ 空数组测试通过")
    
    return True


def test_sharpe_ratio_calculation():
    """测试夏普比率计算"""
    print("\n=== 测试夏普比率计算 ===")
    
    calculator = PerformanceCalculator(risk_free_rate=0.02)
    
    # 测试正夏普比率
    # 生成稳定正收益的序列
    np.random.seed(42)
    daily_returns = np.random.normal(0.001, 0.01, 252)  # 日均0.1%收益，1%波动
    sharpe = calculator.calculate_sharpe_ratio(daily_returns)
    print(f"✓ 正夏普比率测试: {sharpe:.2f}")
    
    # 测试负夏普比率
    daily_returns = np.random.normal(-0.001, 0.01, 252)  # 日均-0.1%收益
    sharpe = calculator.calculate_sharpe_ratio(daily_returns)
    print(f"✓ 负夏普比率测试: {sharpe:.2f}")
    
    # 测试零波动率
    daily_returns = np.zeros(100)
    sharpe = calculator.calculate_sharpe_ratio(daily_returns)
    assert sharpe == 0.0
    print("✓ 零波动率夏普比率测试通过")
    
    return True


def test_sortino_ratio_calculation():
    """测试索提诺比率计算"""
    print("\n=== 测试索提诺比率计算 ===")
    
    calculator = PerformanceCalculator(risk_free_rate=0.02)
    
    # 测试正索提诺比率
    np.random.seed(42)
    daily_returns = np.random.normal(0.001, 0.01, 252)
    annual_return = 0.15  # 15%年化收益
    sortino = calculator.calculate_sortino_ratio(daily_returns, annual_return)
    print(f"✓ 正索提诺比率测试: {sortino:.2f}")
    
    # 测试无下行波动
    daily_returns = np.abs(np.random.normal(0.001, 0.01, 252))  # 全部正收益
    sortino = calculator.calculate_sortino_ratio(daily_returns, annual_return)
    assert sortino == 0.0  # 无下行波动时返回0
    print("✓ 无下行波动测试通过")
    
    return True


def test_calmar_ratio_calculation():
    """测试卡玛比率计算"""
    print("\n=== 测试卡玛比率计算 ===")
    
    calculator = PerformanceCalculator()
    
    # 测试正常卡玛比率
    annual_return = 0.20  # 20%年化收益
    max_drawdown = 0.10  # 10%最大回撤
    calmar = calculator.calculate_calmar_ratio(annual_return, max_drawdown)
    expected = 0.20 / 0.10  # 2.0
    assert abs(calmar - expected) < 1e-10, f"期望 {expected}, 得到 {calmar}"
    print(f"✓ 正常卡玛比率测试通过: {calmar:.2f}")
    
    # 测试零回撤
    calmar = calculator.calculate_calmar_ratio(0.20, 0.0)
    assert calmar == 0.0
    print("✓ 零回撤测试通过")
    
    # 测试负收益
    calmar = calculator.calculate_calmar_ratio(-0.10, 0.20)
    expected = -0.10 / 0.20  # -0.5
    assert abs(calmar - expected) < 1e-10
    print(f"✓ 负收益卡玛比率测试通过: {calmar:.2f}")
    
    return True


def test_win_rate_calculation():
    """测试胜率计算"""
    print("\n=== 测试胜率计算 ===")
    
    calculator = PerformanceCalculator()
    
    # 测试正常胜率
    profits = [100, 200, 150]  # 3次盈利
    losses = [50, 80]  # 2次亏损
    win_rate = calculator.calculate_win_rate(profits, losses)
    expected = 3 / 5  # 60%
    assert abs(win_rate - expected) < 1e-10, f"期望 {expected}, 得到 {win_rate}"
    print(f"✓ 正常胜率测试通过: {win_rate:.2%}")
    
    # 测试100%胜率
    win_rate = calculator.calculate_win_rate([100, 200], [])
    assert win_rate == 1.0
    print("✓ 100%胜率测试通过")
    
    # 测试0%胜率
    win_rate = calculator.calculate_win_rate([], [50, 80])
    assert win_rate == 0.0
    print("✓ 0%胜率测试通过")
    
    # 测试无交易
    win_rate = calculator.calculate_win_rate([], [])
    assert win_rate == 0.0
    print("✓ 无交易测试通过")
    
    return True


def test_profit_loss_ratio_calculation():
    """测试盈亏比计算"""
    print("\n=== 测试盈亏比计算 ===")
    
    calculator = PerformanceCalculator()
    
    # 测试正常盈亏比
    profits = [100, 200, 150]  # 总盈利450
    losses = [50, 100]  # 总亏损150
    pl_ratio = calculator.calculate_profit_loss_ratio(profits, losses)
    expected = 450 / 150  # 3.0
    assert abs(pl_ratio - expected) < 1e-10, f"期望 {expected}, 得到 {pl_ratio}"
    print(f"✓ 正常盈亏比测试通过: {pl_ratio:.2f}")
    
    # 测试无亏损
    pl_ratio = calculator.calculate_profit_loss_ratio([100, 200], [])
    assert pl_ratio == float('inf')
    print("✓ 无亏损测试通过")
    
    # 测试无盈利
    pl_ratio = calculator.calculate_profit_loss_ratio([], [50, 80])
    assert pl_ratio == 0.0
    print("✓ 无盈利测试通过")
    
    # 测试无交易
    pl_ratio = calculator.calculate_profit_loss_ratio([], [])
    assert pl_ratio == 0.0
    print("✓ 无交易测试通过")
    
    return True


def test_daily_returns_calculation():
    """测试日收益率计算"""
    print("\n=== 测试日收益率计算 ===")
    
    calculator = PerformanceCalculator()
    
    # 测试正常日收益率
    values = [100, 110, 105, 115]
    daily_returns = calculator.calculate_daily_returns(values)
    expected = np.array([0.10, -0.0454545, 0.0952381])
    assert len(daily_returns) == 3
    for i, (actual, exp) in enumerate(zip(daily_returns, expected)):
        assert abs(actual - exp) < 1e-5, f"第{i}天: 期望 {exp}, 得到 {actual}"
    print("✓ 正常日收益率测试通过")
    
    # 测试空列表
    daily_returns = calculator.calculate_daily_returns([])
    assert len(daily_returns) == 0
    print("✓ 空列表测试通过")
    
    # 测试单个值
    daily_returns = calculator.calculate_daily_returns([100])
    assert len(daily_returns) == 0
    print("✓ 单个值测试通过")
    
    return True


def test_calculate_all_metrics():
    """测试计算所有指标"""
    print("\n=== 测试计算所有指标 ===")
    
    # 生成测试数据
    np.random.seed(42)
    initial_value = 100000
    days = 252
    
    # 生成净值曲线
    daily_returns = np.random.normal(0.0005, 0.015, days)
    values = [initial_value]
    for r in daily_returns:
        values.append(values[-1] * (1 + r))
    
    # 生成交易记录
    trades = [
        {'fund_code': '000001', 'action': 'buy', 'amount': 10000, 'shares': 100, 'price': 100},
        {'fund_code': '000001', 'action': 'sell', 'amount': 11000, 'shares': 100, 'price': 110},
        {'fund_code': '000002', 'action': 'buy', 'amount': 10000, 'shares': 100, 'price': 100},
        {'fund_code': '000002', 'action': 'sell', 'amount': 9000, 'shares': 100, 'price': 90},
    ]
    
    # 计算所有指标
    metrics = calculate_performance_metrics(values, trades=trades)
    
    # 验证指标存在且合理
    assert isinstance(metrics, PerformanceMetrics)
    print(f"  总收益率: {metrics.total_return:.2%}")
    print(f"  年化收益率: {metrics.annual_return:.2%}")
    print(f"  最大回撤: {metrics.max_drawdown:.2%}")
    print(f"  波动率: {metrics.volatility:.2%}")
    print(f"  夏普比率: {metrics.sharpe_ratio:.2f}")
    print(f"  索提诺比率: {metrics.sortino_ratio:.2f}")
    print(f"  卡玛比率: {metrics.calmar_ratio:.2f}")
    print(f"  胜率: {metrics.win_rate:.2%}")
    print(f"  盈亏比: {metrics.profit_loss_ratio:.2f}")
    print(f"  总交易次数: {metrics.total_trades}")
    print(f"  盈利交易: {metrics.winning_trades}")
    print(f"  亏损交易: {metrics.losing_trades}")
    
    # 验证指标合理性
    assert -1 <= metrics.total_return <= 10  # 收益率在合理范围
    assert 0 <= metrics.max_drawdown <= 1  # 回撤在0-100%
    assert metrics.volatility >= 0  # 波动率非负
    assert 0 <= metrics.win_rate <= 1  # 胜率在0-100%
    assert metrics.profit_loss_ratio >= 0  # 盈亏比非负
    
    print("✓ 所有指标计算测试通过")
    
    return True


def test_metrics_to_dict():
    """测试指标转换为字典"""
    print("\n=== 测试指标转换为字典 ===")
    
    metrics = PerformanceMetrics(
        total_return=0.15,
        annual_return=0.20,
        max_drawdown=0.10,
        volatility=0.25,
        sharpe_ratio=1.5,
        sortino_ratio=2.0,
        calmar_ratio=2.0,
        win_rate=0.6,
        profit_loss_ratio=2.5,
        total_trades=10,
        winning_trades=6,
        losing_trades=4
    )
    
    metrics_dict = metrics.to_dict()
    
    assert metrics_dict['total_return'] == 0.15
    assert metrics_dict['annual_return'] == 0.20
    assert metrics_dict['max_drawdown'] == 0.10
    assert metrics_dict['volatility'] == 0.25
    assert metrics_dict['sharpe_ratio'] == 1.5
    assert metrics_dict['sortino_ratio'] == 2.0
    assert metrics_dict['calmar_ratio'] == 2.0
    assert metrics_dict['win_rate'] == 0.6
    assert metrics_dict['profit_loss_ratio'] == 2.5
    assert metrics_dict['total_trades'] == 10
    
    print("✓ 指标转换为字典测试通过")
    
    return True


def test_edge_cases():
    """测试边界情况"""
    print("\n=== 测试边界情况 ===")
    
    calculator = PerformanceCalculator()
    
    # 测试极端收益
    values = [100, 200]  # 100%收益
    total_return = calculator.calculate_total_return(values)
    assert abs(total_return - 1.0) < 1e-10
    print("✓ 极端正收益测试通过")
    
    # 测试接近完全亏损
    values = [100, 10]  # -90%收益
    total_return = calculator.calculate_total_return(values)
    assert abs(total_return - (-0.9)) < 1e-10
    print("✓ 极端负收益测试通过")
    
    # 测试初始值为0
    values = [0, 100]
    total_return = calculator.calculate_total_return(values)
    assert total_return == 0.0  # 避免除零
    print("✓ 初始值为0测试通过")
    
    # 测试包含NaN的数据
    values = [100, float('nan'), 110]
    daily_returns = calculator.calculate_daily_returns(values)
    assert not any(np.isnan(daily_returns))  # NaN应被处理
    print("✓ NaN数据处理测试通过")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("绩效指标计算测试")
    print("=" * 60)
    
    tests = [
        ("总收益率计算", test_total_return_calculation),
        ("年化收益率计算", test_annual_return_calculation),
        ("最大回撤计算", test_max_drawdown_calculation),
        ("波动率计算", test_volatility_calculation),
        ("夏普比率计算", test_sharpe_ratio_calculation),
        ("索提诺比率计算", test_sortino_ratio_calculation),
        ("卡玛比率计算", test_calmar_ratio_calculation),
        ("胜率计算", test_win_rate_calculation),
        ("盈亏比计算", test_profit_loss_ratio_calculation),
        ("日收益率计算", test_daily_returns_calculation),
        ("计算所有指标", test_calculate_all_metrics),
        ("指标转换为字典", test_metrics_to_dict),
        ("边界情况", test_edge_cases),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n✗ {name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
