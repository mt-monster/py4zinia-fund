# Enhanced Backtest API Endpoint Implementation

## Overview

This document describes the implementation of the enhanced backtest API endpoint (`/api/strategy/backtest-holdings`) for the strategy page refactor project.

## Endpoint Details

### URL
`POST /api/strategy/backtest-holdings`

### Purpose
Enable users to backtest their fund holdings using selected strategies from the strategy comparison report.

### Request Parameters

```json
{
  "fund_codes": ["000001", "000002"],  // Array of fund codes (required)
  "strategy_id": "dual_ma",            // Strategy identifier (optional, default: "enhanced_rule_based")
  "initial_amount": 10000,             // Initial investment amount (required, min: 100)
  "base_invest": 100,                  // Base investment per period (required, min: 10)
  "days": 90                           // Backtest period in days (required, must be: 30, 60, 90, 180, or 365)
}
```

### Response Format

```json
{
  "success": true,
  "data": {
    "fund_code": "000001",
    "strategy_id": "dual_ma",
    "initial_amount": 10000,
    "final_value": 11500,
    "total_return": 15.0,
    "annualized_return": 60.0,
    "max_drawdown": -8.5,
    "sharpe_ratio": 1.2,
    "trades_count": 25,
    "trades": [
      {
        "date": "2024-01-15",
        "action": "buy",
        "amount": 200,
        "balance": 9800,
        "holdings": 200,
        "profit": 0,
        "multiplier": 2.0,
        "trend": "uptrend",
        "volatility_adj": 1.0
      }
    ],
    "evaluation": {
      "hit_rate": 0.65,
      "profit_factor": 1.8,
      "max_consecutive_losses": 3,
      "max_consecutive_wins": 5,
      "avg_profit_per_trade": 15.5,
      "expectancy": 12.3
    }
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

## Implementation Details

### Parameter Validation

The endpoint validates all input parameters according to requirements:

1. **fund_codes**: Must be a non-empty array
2. **initial_amount**: Must be >= 100
3. **base_invest**: Must be >= 10
4. **days**: Must be one of [30, 60, 90, 180, 365]
5. **strategy_id**: Must be a valid strategy from the strategy report

### Backtest Process

1. **Data Retrieval**: Fetches historical fund data from the database
2. **Strategy Application**: Uses the unified strategy engine to apply selected strategy rules
3. **Simulation**: Simulates buy/sell decisions based on strategy signals
4. **Evaluation**: Calculates performance metrics and evaluation statistics
5. **Response**: Returns complete backtest results with all required fields

### Integration Points

- **Database**: `fund_analysis_results` table for historical data
- **Strategy Engine**: `UnifiedStrategyEngine` for strategy analysis
- **Strategy Parser**: `StrategyReportParser` for strategy metadata
- **Evaluator**: `StrategyEvaluator` for performance evaluation

## Requirements Validation

This implementation satisfies the following requirements:

- **Requirement 4.1**: Accepts fund codes, strategy_id, and backtest parameters
- **Requirement 4.2**: Uses selected fund codes from user holdings
- **Requirement 4.3**: Applies selected strategy rules from parsed report
- **Requirement 4.4**: Returns complete backtest results with evaluation metrics
- **Requirement 4.5**: Displays error messages for failures

## Testing

Comprehensive unit tests have been implemented in `test_enhanced_backtest_api.py`:

- Parameter validation tests (13 test cases)
- Response structure validation
- Error handling tests
- Edge case tests

All tests pass successfully.

## Usage Example

```javascript
// Frontend JavaScript example
async function runBacktest() {
  const response = await fetch('/api/strategy/backtest-holdings', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      fund_codes: ['000001'],
      strategy_id: 'dual_ma',
      initial_amount: 10000,
      base_invest: 100,
      days: 90
    })
  });
  
  const result = await response.json();
  
  if (result.success) {
    console.log('Backtest completed:', result.data);
    displayResults(result.data);
  } else {
    console.error('Backtest failed:', result.error);
    showError(result.error);
  }
}
```

## Future Enhancements

1. **Multi-Fund Support**: Currently processes single fund; can be extended for portfolio backtesting
2. **Strategy Comparison**: Add ability to compare multiple strategies simultaneously
3. **Custom Parameters**: Allow users to customize strategy parameters
4. **Caching**: Implement result caching for frequently requested backtests
5. **Async Processing**: For long-running backtests, implement async task processing

## Files Modified

- `pro2/fund_search/web/app.py`: Added new endpoint implementation
- `pro2/fund_search/tests/test_enhanced_backtest_api.py`: Added comprehensive tests

## Dependencies

- Flask (web framework)
- pandas (data processing)
- numpy (numerical calculations)
- UnifiedStrategyEngine (strategy analysis)
- StrategyReportParser (strategy metadata)
- StrategyEvaluator (performance evaluation)

## Notes

- The endpoint currently handles single fund backtesting; multi-fund support is planned for future releases
- Strategy validation requires the strategy comparison report to be present at the configured path
- Historical data must be available in the database for the requested backtest period
- All monetary values are rounded to 2 decimal places for consistency
- Sharpe ratio and other metrics are calculated using simplified formulas suitable for daily data
