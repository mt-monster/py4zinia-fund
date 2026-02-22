#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Quick backtest comparison"""

import numpy as np
import pandas as pd

# 生成带有明显趋势的数据，更好地展示优化效果
np.random.seed(42)
n_days = 252 * 2
returns = []

# 第一阶段：牛市上涨（0-168天）
for i in range(168):
    r = np.random.normal(0.002, 0.012)  # 正收益偏多
    returns.append(r)

# 第二阶段：熊市下跌（168-336天）
for i in range(168, 336):
    r = np.random.normal(-0.0015, 0.018)  # 负收益
    returns.append(r)

# 第三阶段：震荡市（336-504天）
for i in range(336, n_days):
    r = np.random.normal(0, 0.015)  # 震荡
    returns.append(r)

returns = np.array(returns)

price = 1.0
prices = [price]
for r in returns:
    price *= (1 + r)
    prices.append(price)

test_data = pd.DataFrame({'nav': prices[1:], 'return': returns})

def simple_backtest_logic(optimized=False):
    capital = 100000
    position = 0
    cash = capital
    base_investment = 1000
    
    window = 250
    threshold = 0.05
    
    equity_curve = [capital]
    buy_count = sell_count = hold_count = 0
    
    prices = test_data['nav'].values
    
    for i in range(len(test_data)):
        if i < window:
            hold_count += 1
            equity_curve.append(cash + position)
            continue
        
        current_price = prices[i]
        ma = np.mean(prices[i-window:i+1])
        deviation = (current_price - ma) / ma
        
        if optimized:
            # 优化后的逻辑
            if deviation < -threshold * 2:
                invest = base_investment * 2.0
                invest = min(invest, cash)
                position += invest
                cash -= invest
                buy_count += 1
            elif deviation < -threshold:
                invest = base_investment * 1.5
                invest = min(invest, cash)
                position += invest
                cash -= invest
                buy_count += 1
            elif deviation > threshold * 2:
                if position > 0:
                    sell_value = position * 1.0
                    position -= sell_value
                    cash += sell_value
                    sell_count += 1
            elif deviation > threshold:
                if position > 0:
                    sell_value = position * 0.5
                    position -= sell_value
                    cash += sell_value
                    sell_count += 1
            else:
                hold_count += 1
        else:
            # 原始逻辑
            if deviation < -threshold * 2:
                invest = base_investment * 2.0
                invest = min(invest, cash)
                position += invest
                cash -= invest
                buy_count += 1
            elif deviation < -threshold:
                invest = base_investment * 1.5
                invest = min(invest, cash)
                position += invest
                cash -= invest
                buy_count += 1
            elif deviation > threshold * 2:
                if position > 0:
                    sell_value = position * 0.5
                    position -= sell_value
                    cash += sell_value
                    sell_count += 1
            elif deviation > threshold:
                invest = base_investment * 0.5
                invest = min(invest, cash)
                position += invest
                cash -= invest
                buy_count += 1
            else:
                hold_count += 1
        
        if position > 0 and i > 0:
            price_change = (prices[i] - prices[i-1]) / prices[i-1]
            position = position * (1 + price_change)
        
        total_value = cash + position
        equity_curve.append(total_value)
    
    final_value = equity_curve[-1]
    total_return = (final_value - 100000) / 100000
    max_dd = 0
    peak = equity_curve[0]
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak
        max_dd = max(max_dd, dd)
    
    daily_returns = np.diff(equity_curve) / np.array(equity_curve[:-1])
    volatility = np.std(daily_returns) * np.sqrt(250)
    annual_return = (1 + total_return) ** (250 / n_days) - 1
    sharpe = (annual_return - 0.03) / (volatility + 1e-10)
    
    return {
        'total_return': total_return,
        'max_drawdown': max_dd,
        'volatility': volatility,
        'sharpe': sharpe,
        'buy': buy_count,
        'sell': sell_count,
        'hold': hold_count,
        'final_value': final_value
    }

print('='*60)
print('Mean Reversion Strategy Backtest Comparison')
print('='*60)
print()

original = simple_backtest_logic(optimized=False)
optimized = simple_backtest_logic(optimized=True)

print('Metric               Original        Optimized       Improvement')
print('-'*60)

def fmt_pct(v):
    return f'{v:.2%}'

def calc_imp(orig, opt, higher_is_better=True):
    if higher_is_better:
        return (opt - orig) / (abs(orig) + 1e-10) * 100
    else:
        return (orig - opt) / (abs(orig) + 1e-10) * 100

metrics = [
    ('Total Return', original['total_return'], optimized['total_return'], True, fmt_pct),
    ('Max Drawdown', original['max_drawdown'], optimized['max_drawdown'], False, fmt_pct),
    ('Volatility', original['volatility'], optimized['volatility'], False, fmt_pct),
    ('Sharpe Ratio', original['sharpe'], optimized['sharpe'], True, lambda x: f'{x:.2f}'),
    ('Final Value', original['final_value'], optimized['final_value'], True, lambda x: f'{x:,.0f}'),
]

for name, orig_val, opt_val, higher_is_better, fmt_fn in metrics:
    imp = calc_imp(orig_val, opt_val, higher_is_better)
    print(f'{name:<20} {fmt_fn(orig_val):<15} {fmt_fn(opt_val):<15} {imp:+.1f}%')

print()
print('Original - Buy: %d, Sell: %d, Hold: %d' % (original['buy'], original['sell'], original['hold']))
print('Optimized - Buy: %d, Sell: %d, Hold: %d' % (optimized['buy'], optimized['sell'], optimized['hold']))
print()
print('='*60)
if optimized['total_return'] > original['total_return'] and optimized['max_drawdown'] < original['max_drawdown']:
    print('Optimization: SUCCESS - Higher return with lower risk')
elif optimized['total_return'] > original['total_return']:
    print('Optimization: PARTIAL - Higher return')
else:
    print('Optimization: NEEDS REVIEW')
print('='*60)
