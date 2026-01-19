# Status Label Calculation Logic

## Overview

The `status_label` represents the investment status of a fund based on its daily return performance. This label is calculated using the `get_investment_strategy` function in `enhanced_main.py`, which analyzes today's return rate and yesterday's return rate to determine market trends and investment recommendations.

## Calculation Parameters

- `today_return`: Today's return rate (in %)
- `prev_day_return`: Yesterday's return rate (in %)
- `return_diff = today_return - prev_day_return`

## Status Label Categories

The logic divides scenarios into 16 main categories based on the combination of today's and yesterday's returns:

### 1. Continuous Positive Returns (Both Days Positive)

| Condition | Status Label | Operation Suggestion | Buy | Redeem | Multiplier |
|-----------|-------------|---------------------|-----|--------|------------|
| `return_diff > 1%` | 🟢 大涨 (Big Rise) | 不买入，不赎回 (No buy, no redeem) | False | 0 | 0 |
| `0 < return_diff ≤ 1%` | 🟡 连涨 (Continuous Rise) | 不买入，赎回15元 (No buy, redeem ¥15) | False | 15 | 0 |
| `-1% ≤ return_diff ≤ 0` | 🟠 连涨放缓 (Rise Slowing) | 不买入，不赎回 (No buy, no redeem) | False | 0 | 0 |
| `return_diff < -1%` | 🟠 连涨回落 (Rise Falling Back) | 不买入，不赎回 (No buy, no redeem) | False | 0 | 0 |

### 2. Reversal Scenarios

| Condition | Status Label | Operation Suggestion | Buy | Redeem | Multiplier |
|-----------|-------------|---------------------|-----|--------|------------|
| `today_return > 0` and `prev_day_return ≤ 0` | 🔵 反转涨 (Reversal Rise) | 定投买入，不赎回 (DCA buy, no redeem) | True | 0 | 1.5 |
| `today_return = 0` and `prev_day_return > 0` | 🔴 转势休整 (Trend Reversal Rest) | 不买入，赎回30元 (No buy, redeem ¥30) | False | 30 | 0 |
| `today_return < 0` and `prev_day_return > 0` | 🔴 反转跌 (Reversal Fall) | 不买入，赎回30元 (No buy, redeem ¥30) | False | 30 | 0 |
| `today_return = 0` and `prev_day_return ≤ 0` | ⚪ 持平 (Holding Steady) | 定投买入，不赎回 (DCA buy, no redeem) | True | 0 | 2.0 |

### 3. First-Time Negative Scenarios (Yesterday = 0)

| Condition | Status Label | Operation Suggestion | Buy | Redeem | Multiplier |
|-----------|-------------|---------------------|-----|--------|------------|
| `today_return ≤ -2%` | 🔴 首次大跌 (First Big Fall) | 定投买入，不赎回 (DCA buy, no redeem) | True | 0 | 0.5 |
| `-2% < today_return ≤ -0.5%` | 🟠 首次下跌 (First Fall) | 定投买入，不赎回 (DCA buy, no redeem) | True | 0 | 1.5 |
| `today_return > -0.5%` | 🔵 微跌试探 (Micro Fall Probe) | 定投买入，不赎回 (DCA buy, no redeem) | True | 0 | 1.0 |

### 4. Continuous Negative Returns (Both Days Negative)

| Condition | Status Label | Operation Suggestion | Buy | Redeem | Multiplier |
|-----------|-------------|---------------------|-----|--------|------------|
| `return_diff > 1%` and `today_return ≤ -2%` | 🔴 暴跌加速 (Crash Acceleration) | 定投买入，不赎回 (DCA buy, no redeem) | True | 0 | 0.5 |
| `return_diff > 1%` and `today_return > -2%` | 🟣 跌速扩大 (Fall Speed Expansion) | 定投买入，不赎回 (DCA buy, no redeem) | True | 0 | 1.0 |
| `(prev_day_return - today_return) > 0` and `prev_day_return ≤ -2%` | 🔵 暴跌回升 (Crash Recovery) | 定投买入，不赎回 (DCA buy, no redeem) | True | 0 | 1.5 |
| `(prev_day_return - today_return) > 0` and `prev_day_return > -2%` | 🟦 跌速放缓 (Fall Speed Slowing) | 定投买入，不赎回 (DCA buy, no redeem) | True | 0 | 1.0 |
| `abs(return_diff) ≤ 1%` | 🟣 阴跌筑底 (Slow Fall Bottoming) | 定投买入，不赎回 (DCA buy, no redeem) | True | 0 | 1.0 |

### 5. Default Case

If none of the above conditions are met:
- Status Label: 🔴 下跌 (Falling)
- Operation: 定投买入，不赎回 (DCA buy, no redeem)
- Buy Multiplier: 1.0

## Return Values

The function returns a tuple containing:
1. `status_label`: The descriptive status string with emoji
2. `is_buy`: Boolean indicating if buying is recommended
3. `redeem_amount`: Amount to redeem (in yuan)
4. `comparison_value`: The return difference (return_diff)
5. `operation_suggestion`: Text description of recommended action
6. `execution_amount`: Specific execution details
7. `buy_multiplier`: Multiplier for buy amount (relative to standard DCA amount)

## Usage in System

This status label is used throughout the fund analysis system:
- Displayed in web interfaces (`fund_index.html`, `my_holdings.html`)
- Stored in database (`enhanced_database.py`)
- Used in notification systems (`enhanced_notification.py`)
- Integrated into strategy backtesting (`enhanced_strategy.py`, `unified_strategy_engine.py`)

## Notes

- All return rates are in percentage format
- Buy multiplier represents the factor to multiply standard Dollar-Cost Averaging (DCA) amount
- Redeem amounts are fixed values in yuan
- The logic prioritizes trend continuation and reversal detection
- During rising markets, it suggests profit-taking through redemptions
- During falling markets, it suggests buying opportunities with varying multipliers</content>
<parameter name="filePath">D:\coding\trae_project\py4zinia\pro2\STATUS_LABEL_README.md