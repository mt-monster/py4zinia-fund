#!/usr/bin/env python
# coding: utf-8

"""
策略修复验证测试脚本
Test Script for Strategy Fix Verification

用于验证不同策略是否产生不同的回测结果
"""

import sys
import os
import logging

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtesting.strategy_adapter import get_strategy_adapter
import pandas as pd
import numpy as np

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_data(days=90):
    """创建测试数据"""
    dates = pd.date_range('2024-01-01', periods=days, freq='D')
    
    # 模拟净值走势：先上涨，然后震荡，最后下跌
    navs = []
    nav = 1.0
    for i in range(days):
        if i < 30:
            # 前30天上涨趋势
            change = np.random.normal(0.005, 0.01)
        elif i < 60:
            # 中间30天震荡
            change = np.random.normal(0, 0.015)
        else:
            # 最后30天下跌趋势
            change = np.random.normal(-0.003, 0.01)
        
        nav *= (1 + change)
        navs.append(nav)
    
    df = pd.DataFrame({
        'date': dates,
        'nav': navs,
        'analysis_date': dates
    })
    
    # 计算today_return和prev_day_return
    df['today_return'] = df['nav'].pct_change() * 100
    df['prev_day_return'] = df['today_return'].shift(1)
    df = df.fillna(0)
    
    return df


def test_strategy(strategy_id, test_df, initial_amount=10000, base_invest=100):
    """测试单个策略"""
    logger.info(f"\n{'='*60}")
    logger.info(f"测试策略: {strategy_id}")
    logger.info(f"{'='*60}")
    
    adapter = get_strategy_adapter()
    
    # 检查是否为高级策略
    is_advanced = adapter.is_advanced_strategy(strategy_id)
    logger.info(f"策略类型: 高级策略")
    
    if not is_advanced:
        logger.warning(f"策略 {strategy_id} 不在策略列表中")
        return None
    
    # 模拟回测
    balance = initial_amount
    holdings = 0
    trades = []
    
    for idx in range(len(test_df)):
        try:
            signal = adapter.generate_signal(
                strategy_id=strategy_id,
                history_df=test_df,
                current_index=idx,
                current_holdings=holdings,
                cash=balance,
                base_invest=base_invest
            )
            
            # 执行交易
            if signal.action == 'buy' and signal.buy_multiplier > 0:
                buy_amount = base_invest * signal.buy_multiplier
                if balance >= buy_amount:
                    balance -= buy_amount
                    holdings += buy_amount
                    trades.append({
                        'date': test_df.iloc[idx]['date'],
                        'action': 'buy',
                        'amount': buy_amount,
                        'multiplier': signal.buy_multiplier,
                        'reason': signal.reason
                    })
            
            elif signal.action == 'sell' and signal.redeem_amount > 0:
                if 0 < signal.redeem_amount <= 1:
                    sell_amount = holdings * signal.redeem_amount
                else:
                    sell_amount = min(signal.redeem_amount, holdings)
                
                if sell_amount > 0:
                    holdings -= sell_amount
                    balance += sell_amount
                    trades.append({
                        'date': test_df.iloc[idx]['date'],
                        'action': 'sell',
                        'amount': sell_amount,
                        'reason': signal.reason
                    })
            
            # 更新持仓价值
            today_return = test_df.iloc[idx]['today_return'] / 100
            holdings *= (1 + today_return)
            
        except Exception as e:
            logger.error(f"第{idx}天执行失败: {str(e)}")
            continue
    
    # 计算结果
    final_value = balance + holdings
    total_return = (final_value - initial_amount) / initial_amount * 100
    
    # 统计交易
    buy_count = len([t for t in trades if t['action'] == 'buy'])
    sell_count = len([t for t in trades if t['action'] == 'sell'])
    
    result = {
        'strategy_id': strategy_id,
        'initial_amount': initial_amount,
        'final_value': round(final_value, 2),
        'total_return': round(total_return, 2),
        'trades_count': len(trades),
        'buy_count': buy_count,
        'sell_count': sell_count,
        'trades': trades
    }
    
    logger.info(f"初始金额: ¥{initial_amount}")
    logger.info(f"最终价值: ¥{result['final_value']}")
    logger.info(f"总收益率: {result['total_return']}%")
    logger.info(f"交易次数: {result['trades_count']} (买入: {buy_count}, 卖出: {sell_count})")
    
    if trades:
        logger.info(f"首次交易: {trades[0]['date'].strftime('%Y-%m-%d')} - {trades[0]['action']} - {trades[0]['reason']}")
        logger.info(f"最后交易: {trades[-1]['date'].strftime('%Y-%m-%d')} - {trades[-1]['action']} - {trades[-1]['reason']}")
    
    return result


def main():
    """主测试函数"""
    logger.info("="*80)
    logger.info("策略修复验证测试")
    logger.info("="*80)
    
    # 创建测试数据
    logger.info("\n创建测试数据...")
    test_df = create_test_data(days=90)
    logger.info(f"测试数据: {len(test_df)} 天")
    logger.info(f"净值范围: {test_df['nav'].min():.4f} ~ {test_df['nav'].max():.4f}")
    logger.info(f"收益率范围: {test_df['today_return'].min():.2f}% ~ {test_df['today_return'].max():.2f}%")
    
    # 测试所有高级策略
    strategies = ['dual_ma', 'mean_reversion', 'target_value', 'grid', 'enhanced_rule_based']
    results = []
    
    for strategy_id in strategies:
        result = test_strategy(strategy_id, test_df)
        if result:
            results.append(result)
    
    # 对比结果
    logger.info(f"\n{'='*80}")
    logger.info("策略对比结果")
    logger.info(f"{'='*80}")
    
    if results:
        logger.info(f"\n{'策略':<20} {'最终价值':<15} {'总收益率':<15} {'交易次数':<10}")
        logger.info("-" * 80)
        for result in results:
            logger.info(f"{result['strategy_id']:<20} ¥{result['final_value']:<14.2f} {result['total_return']:<14.2f}% {result['trades_count']:<10}")
        
        # 检查是否有差异
        returns = [r['total_return'] for r in results]
        trades = [r['trades_count'] for r in results]
        
        logger.info(f"\n{'='*80}")
        logger.info("差异性分析")
        logger.info(f"{'='*80}")
        logger.info(f"收益率标准差: {np.std(returns):.2f}%")
        logger.info(f"交易次数标准差: {np.std(trades):.2f}")
        
        if np.std(returns) > 1.0 or np.std(trades) > 5:
            logger.info("\n✅ 测试通过：不同策略产生了明显不同的结果")
        else:
            logger.warning("\n⚠️  警告：不同策略的结果差异较小，可能仍存在问题")
    else:
        logger.error("\n❌ 测试失败：没有成功执行任何策略")
    
    logger.info(f"\n{'='*80}")
    logger.info("测试完成")
    logger.info(f"{'='*80}\n")


if __name__ == "__main__":
    main()
