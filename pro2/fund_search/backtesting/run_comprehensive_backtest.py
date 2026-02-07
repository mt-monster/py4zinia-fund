#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Comprehensive backtest with realistic market phases"""

import numpy as np
import pandas as pd
import json

def generate_realistic_market_data(n_days=504, scenario='bull_bear_cycle'):
    """Generate realistic market data with different scenarios"""
    np.random.seed(42)
    
    if scenario == 'bull_bear_cycle':
        # Bull-Bear cycle: bull run -> crash -> recovery
        phase1 = np.random.normal(0.0015, 0.012, 150)  # Bull
        phase2 = np.random.normal(-0.002, 0.020, 100)  # Crash
        phase3 = np.random.normal(0.0005, 0.015, 150)  # Recovery
        phase4 = np.random.normal(0, 0.010, 104)       # Sideways
        returns = np.concatenate([phase1, phase2, phase3, phase4])
    elif scenario == 'trending':
        # Strong trending market
        returns = np.random.normal(0.0008, 0.010, n_days)
    elif scenario == 'choppy':
        # Choppy, mean-reverting market
        returns = np.random.normal(0, 0.018, n_days)
    else:
        returns = np.random.normal(0.0003, 0.015, n_days)
    
    price = 1.0
    prices = [price]
    for r in returns:
        price *= (1 + r)
        prices.append(price)
    
    return pd.DataFrame({
        'nav': prices[1:],
        'return': returns
    })

class OriginalMeanReversion:
    """Original strategy with flaws"""
    def __init__(self):
        self.name = "MeanReversion_Original"
        self.window = 250
        self.threshold = 0.05
    
    def generate_signal(self, prices, current_idx):
        if current_idx < self.window:
            return 'buy', 1.0
        
        ma = np.mean(prices[current_idx-self.window:current_idx+1])
        current_price = prices[current_idx]
        deviation = (current_price - ma) / ma
        
        if deviation < -self.threshold * 2:
            return 'buy', 2.0
        elif deviation < -self.threshold:
            return 'buy', 1.5
        elif deviation > self.threshold * 2:
            return 'sell', 0.5  # BUG: Should be 1.0
        elif deviation > self.threshold:
            return 'buy', 0.5   # BUG: Should be 'sell'
        else:
            return 'buy', 1.0

class OptimizedMeanReversion:
    """Optimized strategy with fixes"""
    def __init__(self):
        self.name = "MeanReversion_Optimized"
        self.window = 250
        self.threshold = 0.05
    
    def generate_signal(self, prices, current_idx):
        if current_idx < self.window:
            return 'buy', 1.0
        
        ma = np.mean(prices[current_idx-self.window:current_idx+1])
        current_price = prices[current_idx]
        deviation = (current_price - ma) / ma
        
        # Trend filter
        if current_idx >= 60:
            ma_short = np.mean(prices[current_idx-20:current_idx+1])
            ma_long = np.mean(prices[current_idx-60:current_idx+1])
            
            if ma_short > ma_long * 1.05 and deviation > 0:
                return 'hold', 0.0  # Strong uptrend, don't sell
            
            if ma_short < ma_long * 0.95 and deviation < -self.threshold:
                return 'hold', 0.0  # Strong downtrend, don't catch falling knife
        
        if deviation < -self.threshold * 2:
            return 'buy', 2.0
        elif deviation < -self.threshold:
            return 'buy', 1.5
        elif deviation > self.threshold * 2:
            return 'sell', 1.0  # FIXED: Full exit
        elif deviation > self.threshold:
            return 'sell', 0.5  # FIXED: Partial exit
        else:
            return 'buy', 1.0

def run_backtest(strategy, data, initial_capital=100000, base_investment=1000):
    """Run backtest for a strategy"""
    capital = initial_capital
    position = 0
    cash = capital
    
    equity_curve = [capital]
    trades = []
    
    prices = data['nav'].values
    
    for i in range(len(data)):
        action, multiplier = strategy.generate_signal(prices, i)
        current_price = prices[i]
        
        if action == 'buy' and multiplier > 0:
            invest_amount = base_investment * multiplier
            invest_amount = min(invest_amount, cash)
            if invest_amount > 0:
                position += invest_amount
                cash -= invest_amount
                trades.append({'day': i, 'action': 'buy', 'amount': invest_amount})
        
        elif action == 'sell' and position > 0:
            sell_ratio = min(multiplier, 1.0)
            sell_value = position * sell_ratio
            if sell_value > 0:
                position -= sell_value
                cash += sell_value
                trades.append({'day': i, 'action': 'sell', 'amount': sell_value})
        
        # Update position value
        if position > 0 and i > 0:
            price_change = (prices[i] - prices[i-1]) / prices[i-1]
            position = position * (1 + price_change)
        
        total_value = cash + position
        equity_curve.append(total_value)
    
    # Calculate metrics
    final_value = equity_curve[-1]
    total_return = (final_value - initial_capital) / initial_capital
    
    # Max drawdown
    max_dd = 0
    peak = equity_curve[0]
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak
        max_dd = max(max_dd, dd)
    
    # Volatility and Sharpe
    daily_returns = np.diff(equity_curve) / np.array(equity_curve[:-1])
    volatility = np.std(daily_returns) * np.sqrt(250)
    annual_return = (1 + total_return) ** (250 / len(data)) - 1
    sharpe = (annual_return - 0.03) / (volatility + 1e-10) if volatility > 0 else 0
    
    buy_count = len([t for t in trades if t['action'] == 'buy'])
    sell_count = len([t for t in trades if t['action'] == 'sell'])
    
    return {
        'strategy': strategy.name,
        'total_return': total_return,
        'max_drawdown': max_dd,
        'volatility': volatility,
        'sharpe_ratio': sharpe,
        'final_value': final_value,
        'buy_count': buy_count,
        'sell_count': sell_count,
        'total_trades': len(trades)
    }

def print_comparison(results_orig, results_opt):
    """Print comparison table"""
    print("=" * 70)
    print("STRATEGY OPTIMIZATION BACKTEST RESULTS")
    print("=" * 70)
    print()
    
    print(f"{'Metric':<20} {'Original':<18} {'Optimized':<18} {'Improvement':<12}")
    print("-" * 70)
    
    metrics = [
        ('Total Return', 'total_return', True, lambda x: f"{x:.2%}"),
        ('Max Drawdown', 'max_drawdown', False, lambda x: f"{x:.2%}"),
        ('Volatility', 'volatility', False, lambda x: f"{x:.2%}"),
        ('Sharpe Ratio', 'sharpe_ratio', True, lambda x: f"{x:.2f}"),
        ('Final Value', 'final_value', True, lambda x: f"${x:,.0f}"),
        ('# of Trades', 'total_trades', None, lambda x: f"{x}"),
    ]
    
    for name, key, higher_is_better, fmt in metrics:
        orig_val = results_orig[key]
        opt_val = results_opt[key]
        
        if higher_is_better is not None:
            if higher_is_better:
                improvement = (opt_val - orig_val) / (abs(orig_val) + 1e-10) * 100
            else:
                improvement = (orig_val - opt_val) / (abs(orig_val) + 1e-10) * 100
            imp_str = f"{improvement:+.1f}%"
        else:
            imp_str = "-"
        
        print(f"{name:<20} {fmt(orig_val):<18} {fmt(opt_val):<18} {imp_str:<12}")
    
    print("-" * 70)
    print()
    print(f"Original Strategy:  Buy: {results_orig['buy_count']}, Sell: {results_orig['sell_count']}")
    print(f"Optimized Strategy: Buy: {results_opt['buy_count']}, Sell: {results_opt['sell_count']}")
    print()
    
    # Summary
    print("=" * 70)
    print("OPTIMIZATION SUMMARY")
    print("=" * 70)
    
    improvements = []
    if results_opt['total_return'] > results_orig['total_return']:
        improvements.append("Higher Returns")
    if results_opt['max_drawdown'] < results_orig['max_drawdown']:
        improvements.append("Lower Drawdown")
    if results_opt['sharpe_ratio'] > results_orig['sharpe_ratio']:
        improvements.append("Better Risk-Adjusted Returns")
    
    if improvements:
        print(f"[OK] Improvements: {', '.join(improvements)}")
    else:
        print("[WARNING] No significant improvements in this market scenario")
    
    # Key fixes
    print()
    print("Key Fixes Applied:")
    print("  1. Overbought signal: Now SELL instead of BUY")
    print("  2. Extreme overbought: Full exit (1.0x) instead of half (0.5x)")
    print("  3. Added trend filter to avoid buying in strong downtrends")
    print("  4. Added trend filter to avoid selling in strong uptrends")
    
    print("=" * 70)

# Run tests
print("\n" + "=" * 70)
print("TEST SCENARIO: Bull-Bear Market Cycle")
print("=" * 70 + "\n")

data = generate_realistic_market_data(scenario='bull_bear_cycle')
orig_strategy = OriginalMeanReversion()
opt_strategy = OptimizedMeanReversion()

results_orig = run_backtest(orig_strategy, data)
results_opt = run_backtest(opt_strategy, data)

print_comparison(results_orig, results_opt)

# Save results
with open('backtest_results.json', 'w') as f:
    json.dump({
        'original': results_orig,
        'optimized': results_opt
    }, f, indent=2, default=str)

print("\nDetailed results saved to: backtest_results.json")
