"""
Property-Based Tests for Strategy Report Parser

Feature: strategy-page-refactor
Property 2: Strategy Report Parsing Completeness

Validates: Requirements 2.1, 2.2, 2.3, 9.2, 9.3, 9.4
"""

import pytest
from hypothesis import given, strategies as st, settings
from pathlib import Path
import tempfile
from backtesting.strategy_report_parser import StrategyReportParser


# Expected strategy IDs from the report
EXPECTED_STRATEGY_IDS = ['dual_ma', 'mean_reversion', 'target_value', 'grid', 'enhanced_rule_based']

# Required fields for each strategy
REQUIRED_FIELDS = [
    'strategy_id',
    'name', 
    'description',
    'total_return',
    'annualized_return',
    'max_drawdown',
    'sharpe_ratio',
    'win_rate',
    'profit_loss_ratio'
]


def create_valid_report_content(strategies_data):
    """
    Create a valid markdown report with the given strategy data.
    
    Args:
        strategies_data: List of tuples containing strategy information
    """
    content = """# 基金策略对比分析报告

**生成时间**: 2026-01-18 21:56:49

**基金组合**: Fund_001, Fund_002, Fund_003

## 策略对比结果

### 绩效指标对比

| 策略名称                | 策略描述                       | 总收益率   | 年化收益率   | 年化波动率   | 最大回撤    |   夏普比率 | 胜率     |   盈亏比 |   交易次数 |    最终价值 |
|:--------------------|:---------------------------|:-------|:--------|:--------|:--------|-------:|:-------|------:|-------:|--------:|
"""
    
    for strategy_id, desc, total_ret, ann_ret, vol, drawdown, sharpe, win_rate, pl_ratio, trades, final_val in strategies_data:
        content += f"| {strategy_id} | {desc} | {total_ret}% | {ann_ret}% | {vol}% | {drawdown}% | {sharpe} | {win_rate}% | {pl_ratio} | {trades} | {final_val} |\n"
    
    content += """
## 最佳策略推荐

**策略名称**: target_value

**策略描述**: 每期目标资产增加1000.0元
"""
    
    return content


class TestStrategyReportParserProperties:
    """Property-based tests for StrategyReportParser"""
    
    def test_parse_real_report(self):
        """
        Test parsing the actual strategy comparison report.
        
        **Feature: strategy-page-refactor, Property 2: Strategy Report Parsing Completeness**
        
        For any valid strategy comparison report, parsing should extract exactly 5 strategies
        (dual_ma, mean_reversion, target_value, grid, enhanced_rule_based), with each strategy
        containing all required fields.
        """
        # Use the actual report file (path relative to workspace root)
        import os
        workspace_root = Path(__file__).parent.parent.parent.parent
        report_path = workspace_root / 'pro2' / 'fund_backtest' / 'strategy_results' / 'strategy_comparison_report.md'
        
        parser = StrategyReportParser(str(report_path))
        strategies = parser.parse()
        
        # Property: Should extract exactly 5 strategies
        assert len(strategies) == 5, f"Expected 5 strategies, got {len(strategies)}"
        
        # Property: Should contain all expected strategy IDs
        strategy_ids = [s['strategy_id'] for s in strategies]
        assert set(strategy_ids) == set(EXPECTED_STRATEGY_IDS), \
            f"Expected strategy IDs {EXPECTED_STRATEGY_IDS}, got {strategy_ids}"
        
        # Property: Each strategy should have all required fields
        for strategy in strategies:
            for field in REQUIRED_FIELDS:
                assert field in strategy, \
                    f"Strategy {strategy.get('strategy_id', 'unknown')} missing field: {field}"
            
            # Property: Numeric fields should be valid numbers
            assert isinstance(strategy['total_return'], (int, float)), \
                f"total_return should be numeric, got {type(strategy['total_return'])}"
            assert isinstance(strategy['annualized_return'], (int, float)), \
                f"annualized_return should be numeric"
            assert isinstance(strategy['max_drawdown'], (int, float)), \
                f"max_drawdown should be numeric"
            assert isinstance(strategy['sharpe_ratio'], (int, float)), \
                f"sharpe_ratio should be numeric"
            assert isinstance(strategy['win_rate'], (int, float)), \
                f"win_rate should be numeric"
            assert isinstance(strategy['profit_loss_ratio'], (int, float)), \
                f"profit_loss_ratio should be numeric"
            
            # Property: String fields should be non-empty strings
            assert isinstance(strategy['strategy_id'], str) and len(strategy['strategy_id']) > 0, \
                "strategy_id should be non-empty string"
            assert isinstance(strategy['name'], str) and len(strategy['name']) > 0, \
                "name should be non-empty string"
            assert isinstance(strategy['description'], str) and len(strategy['description']) > 0, \
                "description should be non-empty string"
    
    @settings(max_examples=100)
    @given(
        total_return=st.floats(min_value=-100, max_value=500, allow_nan=False, allow_infinity=False),
        annualized_return=st.floats(min_value=-50, max_value=100, allow_nan=False, allow_infinity=False),
        volatility=st.floats(min_value=0, max_value=200, allow_nan=False, allow_infinity=False),
        max_drawdown=st.floats(min_value=-100, max_value=0, allow_nan=False, allow_infinity=False),
        sharpe_ratio=st.floats(min_value=-5, max_value=5, allow_nan=False, allow_infinity=False),
        win_rate=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
        profit_loss_ratio=st.floats(min_value=0, max_value=10, allow_nan=False, allow_infinity=False),
        trades_count=st.integers(min_value=0, max_value=10000),
        final_value=st.floats(min_value=0, max_value=1000000, allow_nan=False, allow_infinity=False)
    )
    def test_parse_completeness_with_random_values(
        self, total_return, annualized_return, volatility, max_drawdown,
        sharpe_ratio, win_rate, profit_loss_ratio, trades_count, final_value
    ):
        """
        Test that parser extracts all 5 strategies with all required fields
        regardless of the numeric values in the report.
        
        **Feature: strategy-page-refactor, Property 2: Strategy Report Parsing Completeness**
        
        For any valid strategy comparison report with varying numeric values,
        parsing should consistently extract exactly 5 strategies with all required fields.
        """
        # Create a temporary report with random values
        strategies_data = [
            ('dual_ma', '基于均线', f'{total_return:.2f}', f'{annualized_return:.2f}', 
             f'{volatility:.2f}', f'{max_drawdown:.2f}', f'{sharpe_ratio:.2f}', 
             f'{win_rate:.2f}', f'{profit_loss_ratio:.2f}', trades_count, f'{final_value:.2f}'),
            ('mean_reversion', '均值回归', f'{total_return * 0.9:.2f}', f'{annualized_return * 0.9:.2f}',
             f'{volatility * 1.1:.2f}', f'{max_drawdown * 1.2:.2f}', f'{sharpe_ratio * 0.8:.2f}',
             f'{win_rate * 0.95:.2f}', f'{profit_loss_ratio * 1.1:.2f}', trades_count + 10, f'{final_value * 0.95:.2f}'),
            ('target_value', '目标市值', f'{total_return * 1.1:.2f}', f'{annualized_return * 1.1:.2f}',
             f'{volatility * 0.9:.2f}', f'{max_drawdown * 0.8:.2f}', f'{sharpe_ratio * 1.2:.2f}',
             f'{win_rate * 1.05:.2f}', f'{profit_loss_ratio * 1.05:.2f}', trades_count + 20, f'{final_value * 1.1:.2f}'),
            ('grid', '网格策略', f'{total_return * 0.5:.2f}', f'{annualized_return * 0.5:.2f}',
             f'{volatility * 1.5:.2f}', f'{max_drawdown * 1.5:.2f}', f'{sharpe_ratio * 0.3:.2f}',
             f'{win_rate * 0.7:.2f}', f'{profit_loss_ratio * 0.9:.2f}', trades_count // 2, f'{final_value * 0.8:.2f}'),
            ('enhanced_rule_based', '复合规则', f'{total_return * 0.95:.2f}', f'{annualized_return * 0.95:.2f}',
             f'{volatility * 1.2:.2f}', f'{max_drawdown * 1.1:.2f}', f'{sharpe_ratio * 0.9:.2f}',
             f'{win_rate * 1.02:.2f}', f'{profit_loss_ratio * 0.98:.2f}', trades_count + 5, f'{final_value * 1.05:.2f}')
        ]
        
        content = create_valid_report_content(strategies_data)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            parser = StrategyReportParser(temp_path)
            strategies = parser.parse()
            
            # Property: Should extract exactly 5 strategies
            assert len(strategies) == 5, f"Expected 5 strategies, got {len(strategies)}"
            
            # Property: Should contain all expected strategy IDs
            strategy_ids = [s['strategy_id'] for s in strategies]
            assert set(strategy_ids) == set(EXPECTED_STRATEGY_IDS), \
                f"Expected strategy IDs {EXPECTED_STRATEGY_IDS}, got {strategy_ids}"
            
            # Property: Each strategy should have all required fields
            for strategy in strategies:
                for field in REQUIRED_FIELDS:
                    assert field in strategy, \
                        f"Strategy {strategy.get('strategy_id', 'unknown')} missing field: {field}"
                
                # Property: All numeric fields should be present and numeric
                assert isinstance(strategy['total_return'], (int, float))
                assert isinstance(strategy['annualized_return'], (int, float))
                assert isinstance(strategy['max_drawdown'], (int, float))
                assert isinstance(strategy['sharpe_ratio'], (int, float))
                assert isinstance(strategy['win_rate'], (int, float))
                assert isinstance(strategy['profit_loss_ratio'], (int, float))
        
        finally:
            # Clean up temporary file
            Path(temp_path).unlink(missing_ok=True)
    
    def test_parse_idempotency(self):
        """
        Test that parsing the same report multiple times yields identical results.
        
        **Feature: strategy-page-refactor, Property 2: Strategy Report Parsing Completeness**
        
        For any valid strategy comparison report, parsing multiple times should
        return identical results (idempotency property).
        """
        workspace_root = Path(__file__).parent.parent.parent.parent
        report_path = workspace_root / 'pro2' / 'fund_backtest' / 'strategy_results' / 'strategy_comparison_report.md'
        
        parser = StrategyReportParser(str(report_path))
        
        # Parse multiple times
        result1 = parser.parse()
        result2 = parser.parse()
        result3 = parser.parse()
        
        # Property: All results should be identical
        assert len(result1) == len(result2) == len(result3)
        
        for i in range(len(result1)):
            assert result1[i] == result2[i] == result3[i], \
                f"Strategy {i} differs across parse calls"
    
    def test_get_strategy_by_id_completeness(self):
        """
        Test that get_strategy_by_id returns complete strategy data for all valid IDs.
        
        **Feature: strategy-page-refactor, Property 2: Strategy Report Parsing Completeness**
        
        For any valid strategy ID in the report, get_strategy_by_id should return
        a complete strategy object with all required fields.
        """
        workspace_root = Path(__file__).parent.parent.parent.parent
        report_path = workspace_root / 'pro2' / 'fund_backtest' / 'strategy_results' / 'strategy_comparison_report.md'
        
        parser = StrategyReportParser(str(report_path))
        
        # Property: Each expected strategy ID should return a complete strategy
        for strategy_id in EXPECTED_STRATEGY_IDS:
            strategy = parser.get_strategy_by_id(strategy_id)
            
            assert strategy is not None, f"Strategy {strategy_id} not found"
            assert strategy['strategy_id'] == strategy_id
            
            # Property: Should have all required fields
            for field in REQUIRED_FIELDS:
                assert field in strategy, \
                    f"Strategy {strategy_id} missing field: {field}"
    
    def test_get_all_strategy_ids_completeness(self):
        """
        Test that get_all_strategy_ids returns exactly the 5 expected strategy IDs.
        
        **Feature: strategy-page-refactor, Property 2: Strategy Report Parsing Completeness**
        
        For any valid strategy comparison report, get_all_strategy_ids should return
        exactly the 5 expected strategy IDs.
        """
        workspace_root = Path(__file__).parent.parent.parent.parent
        report_path = workspace_root / 'pro2' / 'fund_backtest' / 'strategy_results' / 'strategy_comparison_report.md'
        
        parser = StrategyReportParser(str(report_path))
        strategy_ids = parser.get_all_strategy_ids()
        
        # Property: Should return exactly 5 strategy IDs
        assert len(strategy_ids) == 5, f"Expected 5 strategy IDs, got {len(strategy_ids)}"
        
        # Property: Should match expected IDs
        assert set(strategy_ids) == set(EXPECTED_STRATEGY_IDS), \
            f"Expected {EXPECTED_STRATEGY_IDS}, got {strategy_ids}"
    
    def test_error_handling_missing_file(self):
        """
        Test that parser raises FileNotFoundError for non-existent files.
        
        **Feature: strategy-page-refactor, Property 2: Strategy Report Parsing Completeness**
        
        For any non-existent file path, the parser should raise FileNotFoundError.
        """
        parser = StrategyReportParser('non_existent_file.md')
        
        with pytest.raises(FileNotFoundError):
            parser.parse()
    
    def test_error_handling_malformed_report(self):
        """
        Test that parser raises ValueError for malformed reports.
        
        **Feature: strategy-page-refactor, Property 2: Strategy Report Parsing Completeness**
        
        For any malformed report (missing table, invalid format), the parser
        should raise ValueError with descriptive message.
        """
        # Create a malformed report (no table)
        content = """# 基金策略对比分析报告

This is not a valid report with no table.
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            parser = StrategyReportParser(temp_path)
            
            with pytest.raises(ValueError, match="Could not find strategy table"):
                parser.parse()
        
        finally:
            Path(temp_path).unlink(missing_ok=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
