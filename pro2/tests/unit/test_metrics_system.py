"""关键绩效指标系统测试"""

import numpy as np

from backtesting.performance_metrics import (
    calculate_metrics_report,
    MetricsInput,
    MetricRuleSet
)


def test_metric_engine_summary_format():
    equity_curve = [1.0, 1.05, 1.02, 1.10]
    benchmark_curve = [1.0, 1.02, 1.01, 1.03]

    report = calculate_metrics_report(
        equity_curve=equity_curve,
        benchmark_curve=benchmark_curve,
        risk_free_rate=0.02,
        trading_days=252,
        metadata={'owner': 'test'}
    )

    report_dict = report.to_dict()
    assert 'summary' in report_dict
    assert 'metrics' in report_dict['summary']
    assert 'total_return' in report.summary.metrics
    assert report.summary.metrics['total_return'].value != 0


def test_metric_engine_rule_filtering():
    equity_curve = [1.0, 1.02, 0.98, 1.01]
    rule_set = MetricRuleSet(enabled_metrics=['total_return', 'max_drawdown'])

    report = calculate_metrics_report(
        equity_curve=equity_curve,
        rule_set=rule_set
    )

    metric_keys = set(report.summary.metrics.keys())
    assert metric_keys == {'total_return', 'max_drawdown'}


def test_metric_engine_dimensions():
    base_curve = [1.0, 1.03, 1.01, 1.06]
    dimension_inputs = {
        'dept_a': MetricsInput(equity_curve=base_curve),
        'dept_b': MetricsInput(equity_curve=[1.0, 1.01, 1.02, 1.04])
    }

    report = calculate_metrics_report(
        equity_curve=base_curve,
        dimensions=dimension_inputs
    )

    assert report.dimensions is not None
    assert 'dept_a' in report.dimensions
    assert 'dept_b' in report.dimensions


def test_metric_engine_rule_override_annualization():
    equity_curve = [1.0, 1.02, 1.04, 1.06]
    rule_set = MetricRuleSet(annualization_days=252)

    report = calculate_metrics_report(
        equity_curve=equity_curve,
        rule_set=rule_set
    )

    annual_return = report.summary.metrics['annual_return'].value
    assert isinstance(annual_return, float)
    assert not np.isnan(annual_return)
