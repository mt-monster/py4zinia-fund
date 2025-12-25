import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import random
from dataclasses import dataclass
from typing import Dict, Tuple

# =========================================
# 1. 模拟基金数据生成器
# =========================================
def generate_fund_data(days=500, start_price=1.0, fund_name="模拟基金组合"):
    """生成包含多种市场状态的模拟基金数据"""
    np.random.seed(42)
    random.seed(42)
    
    dates = [datetime.now() - timedelta(days=days-i) for i in range(days)]
    prices = [start_price]
    returns = []
    
    for i in range(1, days):
        # 模拟不同市场状态
        phase = i // 100  # 每100天一个阶段
        volatility = 0.02  # 基础波动率
        
        if phase % 5 == 0:  # 牛市
            daily_return = np.random.normal(0.001, volatility)
        elif phase % 5 == 1:  # 熊市
            daily_return = np.random.normal(-0.0015, volatility * 1.5)
        elif phase % 5 == 2:  # 震荡上行
            daily_return = np.random.normal(0.0005, volatility * 1.2)
        elif phase % 5 == 3:  # 暴跌后反弹
            if i % 100 < 30:
                daily_return = np.random.normal(-0.003, volatility * 2)
            else:
                daily_return = np.random.normal(0.002, volatility)
        else:  # 震荡筑底
            daily_return = np.random.normal(0, volatility * 0.8)
        
        # 添加随机极端事件
        if random.random() < 0.01:
            daily_return += random.choice([-0.05, 0.05])
        
        prices.append(prices[-1] * (1 + daily_return))
        returns.append(daily_return)
    
    returns.append(0)  # 最后一天收益率为0
    df = pd.DataFrame({
        'date': dates,
        'nav': prices,
        'daily_return': returns
    })
    df['prev_return'] = df['daily_return'].shift(1).fillna(0)
    return df

# =========================================
# 2. 策略A：原始策略（16条规则）
# =========================================
def apply_strategy_original(row, base_amount=1000):
    """原始策略实现"""
    today = row['daily_return'] * 100  # 转换为百分比
    prev = row['prev_return'] * 100
    
    # 初始化
    buy_multiply = 0
    sell_amount = 0
    
    # 上涨阶段
    if today > 0 and prev > 0:
        diff = today - prev
        if diff > 1:
            buy_multiply, sell_amount = 0, 0  # 大涨
        elif 0 < diff <= 1:
            buy_multiply, sell_amount = 0, 15  # 连涨加速
        elif -1 <= diff <= 0:
            buy_multiply, sell_amount = 0, 0  # 连涨放缓
        else:  # diff < -1
            buy_multiply, sell_amount = 0, 0  # 连涨回落
    
    elif today > 0 and prev <= 0:
        buy_multiply, sell_amount = 1.5, 0  # 反转涨
    
    # 零轴阶段
    elif today == 0 and prev > 0:
        buy_multiply, sell_amount = 0, 30  # 转势休整
    
    elif today < 0 and prev > 0:
        buy_multiply, sell_amount = 0, 30  # 反转跌
    
    elif today == 0 and prev <= 0:
        buy_multiply, sell_amount = 3.0, 0  # 绝对企稳
    
    # 下跌阶段
    elif today < 0 and prev == 0:
        if today <= -2:
            buy_multiply, sell_amount = 2.0, 0  # 首次大跌
        elif -2 < today <= -0.5:
            buy_multiply, sell_amount = 1.5, 0  # 首次下跌
        else:  # today > -0.5
            buy_multiply, sell_amount = 1.0, 0  # 微跌试探
    
    elif today < 0 and prev < 0:
        today_val = row['daily_return'] * 100
        prev_val = row['prev_return'] * 100
        
        if (today_val - prev_val) > 1 and today <= -2:
            buy_multiply, sell_amount = 0.5, 0  # 暴跌加速
        elif (today_val - prev_val) > 1 and today > -2:
            buy_multiply, sell_amount = 1.0, 0  # 跌速扩大
        elif (prev_val - today_val) > 0 and prev <= -2:
            buy_multiply, sell_amount = 1.5, 0  # 暴跌回升
        elif (prev_val - today_val) > 0 and prev > -2:
            buy_multiply, sell_amount = 1.0, 0  # 跌速放缓
        elif abs(today_val - prev_val) <= 1:
            buy_multiply, sell_amount = 1.0, 0  # 阴跌筑底
    
    return pd.Series({
        'buy_multiply': buy_multiply,
        'sell_amount': sell_amount,
        'action': f"买入{buy_multiply:.1f}×" if buy_multiply > 0 else (f"赎回{sell_amount}元" if sell_amount > 0 else "持有")
    })

# =========================================
# 3. 策略B：优化策略（12条规则）
# =========================================
def apply_strategy_optimized(row, base_amount=1000):
    """优化策略实现"""
    today = row['daily_return'] * 100
    prev = row['prev_return'] * 100
    
    buy_multiply = 0
    sell_amount = 0
    
    # 强势上涨
    if today > 1.5 and prev > 0:
        buy_multiply, sell_amount = 0, 60  # 高位持续大涨
    
    elif 0 < today <= 1.5 and prev > 0:
        buy_multiply, sell_amount = 0, 40  # 上涨放缓
    
    # 反转上涨
    elif today > 0 and prev <= 0:
        buy_multiply, sell_amount = 1.5, 0  # 趋势反转
    
    # 转势下跌
    elif today <= 0 and prev > 0.5:
        buy_multiply, sell_amount = 0, 40  # 快速转势
    
    # 绝对企稳
    elif -0.5 <= today <= 0.5 and prev <= 0:
        buy_multiply, sell_amount = 3.0, 0  # 波动极小
    
    # 下跌初期
    elif -2 < today < -0.5 and prev >= 0:
        buy_multiply, sell_amount = 1.5, 0  # 首次下跌
    
    # 阴跌筑底
    elif -2 < today <= -0.5 and prev < 0:
        buy_multiply, sell_amount = 1.5, 0  # 跌速放缓
    
    elif -0.5 < today < 0 and prev < 0:
        buy_multiply, sell_amount = 1.0, 0  # 跌幅收窄
    
    # 恐慌暴跌
    elif today <= -3 and prev < 0:
        buy_multiply, sell_amount = 0, 0  # 暂停买入
    
    elif today <= -2 and prev >= 0:
        buy_multiply, sell_amount = 2.0, 0  # 首次大跌
    
    elif today <= -2 and prev < -2 and (today - prev) > 1:
        buy_multiply, sell_amount = 0.5, 0  # 暴跌加速（保守）
    
    # 暴跌回升
    elif today > -2 and prev <= -2 and (prev - today) > 0:
        buy_multiply, sell_amount = 2.0, 0  # 强劲反弹
    
    # 默认情况
    else:
        buy_multiply, sell_amount = 0, 0
    
    return pd.Series({
        'buy_multiply': buy_multiply,
        'sell_amount': sell_amount,
        'action': f"买入{buy_multiply:.1f}×" if buy_multiply > 0 else (f"赎回{sell_amount}元" if sell_amount > 0 else "持有")
    })

# =========================================
# 4. 回测引擎
# =========================================
@dataclass
class BacktestResult:
    """回测结果数据结构"""
    final_value: float
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    total_invested: float
    trade_count: int
    daily_values: pd.Series
    strategy_name: str

def run_backtest(df, strategy_func, base_amount=1000, init_cash=100000, strategy_name="策略"):
    """通用回测引擎"""
    cash = init_cash
    shares = 0
    daily_values = []
    trade_count = 0
    
    for _, row in df.iterrows():
        nav = row['nav']
        strategy_result = strategy_func(row, base_amount)
        buy_multiply = strategy_result['buy_multiply']
        sell_amount = strategy_result['sell_amount']
        
        # 买入操作
        if buy_multiply > 0:
            invest_amount = base_amount * buy_multiply
            if cash >= invest_amount:
                shares += invest_amount / nav
                cash -= invest_amount
                trade_count += 1
        
        # 赎回操作
        if sell_amount > 0:
            redeem_shares = min(sell_amount / nav, shares)
            cash += redeem_shares * nav
            shares -= redeem_shares
            trade_count += 1
        
        # 计算当日总资产
        total_value = cash + shares * nav
        daily_values.append(total_value)
    
    df['portfolio_value'] = daily_values
    final_value = daily_values[-1]
    total_return = (final_value - init_cash) / init_cash
    
    # 计算年化收益率
    days = (df['date'].iloc[-1] - df['date'].iloc[0]).days
    annualized_return = (1 + total_return) ** (365 / days) - 1
    
    # 计算最大回撤
    peak = df['portfolio_value'].expanding().max()
    drawdown = (df['portfolio_value'] - peak) / peak
    max_drawdown = drawdown.min()
    
    # 计算夏普比率
    returns = df['portfolio_value'].pct_change().dropna()
    sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
    
    total_invested = init_cash - cash + sum([base_amount * strategy_func(row, base_amount)['buy_multiply'] 
                                            for _, row in df.iterrows() if strategy_func(row, base_amount)['buy_multiply'] > 0])
    
    return BacktestResult(
        final_value=final_value,
        total_return=total_return,
        annualized_return=annualized_return,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe_ratio,
        total_invested=total_invested,
        trade_count=trade_count,
        daily_values=df.set_index('date')['portfolio_value'],
        strategy_name=strategy_name
    )

# =========================================
# 5. 主程序与可视化
# =========================================
def main():
    # 生成模拟数据
    print("📊 正在生成模拟基金数据...")
    df = generate_fund_data(days=500, start_price=1.0)
    
    # 运行回测
    print("🔄 运行原始策略回测...")
    result_original = run_backtest(
        df.copy(), 
        apply_strategy_original, 
        base_amount=1000, 
        init_cash=50000,
        strategy_name="Original Strategy"
    )
    
    print("🔄 运行优化策略回测...")
    result_optimized = run_backtest(
        df.copy(), 
        apply_strategy_optimized, 
        base_amount=1000, 
        init_cash=50000,
        strategy_name="Optimized Strategy"
    )
    
    # 打印对比结果
    print("\n" + "="*60)
    print("📈 策略对比结果")
    print("="*60)
    
    results = [result_original, result_optimized]
    for r in results:
        print(f"\n{r.strategy_name}:")
        print(f"  最终资产: ¥{r.final_value:,.2f}")
        print(f"  总收益率: {r.total_return*100:.2f}%")
        print(f"  年化收益率: {r.annualized_return*100:.2f}%")
        print(f"  最大回撤: {r.max_drawdown*100:.2f}%")
        print(f"  夏普比率: {r.sharpe_ratio:.3f}")
        print(f"  交易次数: {r.trade_count}次")
    
    # 可视化
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Investment Strategy Comparison Analysis', fontsize=16, fontweight='bold')
    
    # 1. 净值曲线对比
    ax1 = axes[0, 0]
    ax1.plot(df['date'], result_original.daily_values, label='Original Strategy', linewidth=2, alpha=0.8)
    ax1.plot(df['date'], result_optimized.daily_values, label='Optimized Strategy', linewidth=2, alpha=0.8)
    ax1.plot(df['date'], 50000 * (df['nav'] / df['nav'].iloc[0]), label='Benchmark Fund', linestyle='--', alpha=0.6)
    ax1.set_title('Portfolio Value Comparison', fontweight='bold')
    ax1.set_ylabel('Portfolio Value (CNY)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 回撤对比
    ax2 = axes[0, 1]
    for r in results:
        peak = r.daily_values.expanding().max()
        drawdown = (r.daily_values - peak) / peak
        ax2.plot(df['date'], drawdown * 100, label=f'{r.strategy_name} (Max Drawdown: {r.max_drawdown*100:.1f}%)')
    ax2.set_title('Max Drawdown Comparison', fontweight='bold')
    ax2.set_ylabel('Drawdown (%)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 月度收益分布
    ax3 = axes[1, 0]
    monthly_returns = []
    labels = []
    for r in results:
        monthly_ret = r.daily_values.resample('ME').last().pct_change().dropna()
        monthly_returns.append(monthly_ret)
        labels.append(r.strategy_name)
    ax3.boxplot(monthly_returns, tick_labels=labels)
    ax3.set_title('Monthly Return Distribution', fontweight='bold')
    ax3.set_ylabel('Monthly Return Rate')
    ax3.grid(True, alpha=0.3)
    
    # 4. 关键指标对比
    ax4 = axes[1, 1]
    metrics = ['Total Return', 'Sharpe Ratio', 'Max Drawdown']
    original_metrics = [result_original.total_return, result_original.sharpe_ratio, -result_original.max_drawdown]
    optimized_metrics = [result_optimized.total_return, result_optimized.sharpe_ratio, -result_optimized.max_drawdown]
    x = np.arange(len(metrics))
    width = 0.35
    ax4.bar(x - width/2, original_metrics, width, label='Original Strategy')
    ax4.bar(x + width/2, optimized_metrics, width, label='Optimized Strategy')
    ax4.set_xticks(x)
    ax4.set_xticklabels(metrics)
    ax4.set_title('Key Metrics Comparison', fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    # 生成交易明细
    df_original = df.copy()
    df_original[['buy_multiply', 'sell_amount', 'action']] = df_original.apply(
        lambda row: apply_strategy_original(row, 1000), axis=1
    )
    
    df_optimized = df.copy()
    df_optimized[['buy_multiply', 'sell_amount', 'action']] = df_optimized.apply(
        lambda row: apply_strategy_optimized(row, 1000), axis=1
    )
    
    print("\n📋 策略信号示例（最近10天）")
    print("\n原始策略信号：")
    print(df_original[['date', 'daily_return', 'action']].tail(10).to_string(index=False))
    print("\n优化策略信号：")
    print(df_optimized[['date', 'daily_return', 'action']].tail(10).to_string(index=False))

if __name__ == "__main__":
    main()
