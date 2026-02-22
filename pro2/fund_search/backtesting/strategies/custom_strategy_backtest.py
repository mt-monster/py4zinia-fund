#!/usr/bin/env python
# coding: utf-8

"""
自定义策略回测引擎
Custom Strategy Backtest Engine

实现用户自定义策略的回测逻辑，包括：
- 解析策略配置中的筛选条件
- 实现排序选股逻辑
- 实现交易规则执行
- 实现风险控制（止损止盈）
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from ..core.strategy_models import (
    CustomStrategyConfig, FilterCondition, StrategyValidator,
    calculate_equal_weights, validate_weights_sum,
    SUPPORTED_FILTER_FIELDS, SUPPORTED_SORT_FIELDS
)
from ..analysis.performance_metrics import PerformanceCalculator, PerformanceMetrics

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """交易记录"""
    date: str
    fund_code: str
    fund_name: str
    action: str  # 'buy' | 'sell' | 'stop_loss' | 'take_profit'
    amount: float
    price: float
    shares: float
    balance: float
    holdings_value: float
    reason: str = ''


@dataclass
class BacktestResult:
    """回测结果数据模型"""
    # 收益指标
    total_return: float = 0.0
    annual_return: float = 0.0
    benchmark_return: float = 0.0
    excess_return: float = 0.0
    
    # 风险指标
    max_drawdown: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    
    # 交易统计
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # 时间序列数据
    equity_curve: List[Dict] = field(default_factory=list)
    benchmark_curve: List[Dict] = field(default_factory=list)
    trades: List[TradeRecord] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'benchmark_return': self.benchmark_return,
            'excess_return': self.excess_return,
            'max_drawdown': self.max_drawdown,
            'volatility': self.volatility,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'calmar_ratio': self.calmar_ratio,
            'win_rate': self.win_rate,
            'profit_loss_ratio': self.profit_loss_ratio,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'equity_curve': self.equity_curve,
            'benchmark_curve': self.benchmark_curve,
            'trades': [
                {
                    'date': t.date,
                    'fund_code': t.fund_code,
                    'fund_name': t.fund_name,
                    'action': t.action,
                    'amount': t.amount,
                    'price': t.price,
                    'shares': t.shares,
                    'balance': t.balance,
                    'holdings_value': t.holdings_value,
                    'reason': t.reason
                } for t in self.trades
            ]
        }


class FilterEngine:
    """筛选条件引擎"""
    
    @staticmethod
    def evaluate_condition(fund_data: Dict[str, Any], condition: FilterCondition) -> bool:
        """
        评估单个筛选条件
        
        Args:
            fund_data: 基金数据字典
            condition: 筛选条件
            
        Returns:
            是否满足条件
        """
        field_value = fund_data.get(condition.field)
        
        if field_value is None:
            return False
        
        try:
            # 获取比较值
            compare_value = condition.value
            
            # 类型转换
            if isinstance(compare_value, str):
                if compare_value.lower() in ['true', 'false']:
                    compare_value = compare_value.lower() == 'true'
                else:
                    try:
                        compare_value = float(compare_value)
                    except ValueError:
                        pass
            
            # 执行比较
            op = condition.operator
            if op == '>':
                return float(field_value) > float(compare_value)
            elif op == '<':
                return float(field_value) < float(compare_value)
            elif op == '>=':
                return float(field_value) >= float(compare_value)
            elif op == '<=':
                return float(field_value) <= float(compare_value)
            elif op == '==':
                if isinstance(compare_value, bool):
                    return bool(field_value) == compare_value
                return field_value == compare_value
            elif op == '!=':
                if isinstance(compare_value, bool):
                    return bool(field_value) != compare_value
                return field_value != compare_value
            else:
                logger.warning(f"未知操作符: {op}")
                return False
                
        except (ValueError, TypeError) as e:
            logger.warning(f"条件评估失败: {condition}, 错误: {e}")
            return False
    
    @staticmethod
    def filter_funds(
        funds_data: List[Dict[str, Any]], 
        conditions: List[FilterCondition],
        logic: str = 'AND'
    ) -> List[Dict[str, Any]]:
        """
        根据筛选条件过滤基金列表
        
        Args:
            funds_data: 基金数据列表
            conditions: 筛选条件列表
            logic: 组合逻辑 ('AND' | 'OR')
            
        Returns:
            满足条件的基金列表
        """
        if not conditions:
            return funds_data
        
        filtered = []
        for fund in funds_data:
            results = [
                FilterEngine.evaluate_condition(fund, cond) 
                for cond in conditions
            ]
            
            if logic == 'AND':
                if all(results):
                    filtered.append(fund)
            else:  # OR
                if any(results):
                    filtered.append(fund)
        
        return filtered


class SortingEngine:
    """排序选股引擎"""
    
    @staticmethod
    def sort_and_select(
        funds_data: List[Dict[str, Any]],
        sort_field: str,
        sort_order: str = 'DESC',
        select_count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        排序并选择基金
        
        Args:
            funds_data: 基金数据列表
            sort_field: 排序字段
            sort_order: 排序方向 ('ASC' | 'DESC')
            select_count: 选股数量
            
        Returns:
            选中的基金列表
        """
        if not funds_data:
            return []
        
        # 过滤掉排序字段为空的基金
        valid_funds = [
            f for f in funds_data 
            if f.get(sort_field) is not None
        ]
        
        if not valid_funds:
            return []
        
        # 排序
        reverse = sort_order.upper() == 'DESC'
        sorted_funds = sorted(
            valid_funds,
            key=lambda x: float(x.get(sort_field, 0)),
            reverse=reverse
        )
        
        # 选择前N只
        return sorted_funds[:select_count]



class WeightCalculator:
    """权重计算器"""
    
    @staticmethod
    def calculate_weights(
        fund_count: int,
        weight_mode: str = 'equal',
        custom_weights: Optional[List[float]] = None
    ) -> List[float]:
        """
        计算基金权重
        
        Args:
            fund_count: 基金数量
            weight_mode: 权重模式 ('equal' | 'custom')
            custom_weights: 自定义权重列表
            
        Returns:
            权重列表
        """
        if fund_count <= 0:
            return []
        
        if weight_mode == 'custom' and custom_weights:
            if len(custom_weights) >= fund_count:
                weights = custom_weights[:fund_count]
                # 归一化
                total = sum(weights)
                if total > 0:
                    return [w / total for w in weights]
            # 如果自定义权重不足，回退到等权重
            logger.warning("自定义权重数量不足，使用等权重")
        
        # 等权重
        return calculate_equal_weights(fund_count)


class RiskController:
    """风险控制器"""
    
    def __init__(
        self,
        daily_stop_loss: float = -0.05,
        daily_take_profit: float = 0.10,
        total_stop_loss: float = -0.15,
        trailing_stop: float = 0.0
    ):
        """
        初始化风险控制器
        
        Args:
            daily_stop_loss: 每日止损阈值（负数）
            daily_take_profit: 每日止盈阈值（正数）
            total_stop_loss: 累计止损阈值（负数）
            trailing_stop: 追踪止损比例
        """
        self.daily_stop_loss = daily_stop_loss
        self.daily_take_profit = daily_take_profit
        self.total_stop_loss = total_stop_loss
        self.trailing_stop = trailing_stop
        
        # 追踪止损状态
        self.peak_value = 0.0
    
    def reset(self):
        """重置状态"""
        self.peak_value = 0.0
    
    def update_peak(self, current_value: float):
        """更新峰值"""
        if current_value > self.peak_value:
            self.peak_value = current_value
    
    def check_daily_stop_loss(self, daily_return: float) -> Tuple[bool, str]:
        """
        检查每日止损
        
        Args:
            daily_return: 当日收益率
            
        Returns:
            (是否触发止损, 原因)
        """
        if daily_return <= self.daily_stop_loss:
            return True, f"每日止损触发: 当日收益率 {daily_return:.2%} <= {self.daily_stop_loss:.2%}"
        return False, ""
    
    def check_daily_take_profit(self, daily_return: float) -> Tuple[bool, str]:
        """
        检查每日止盈
        
        Args:
            daily_return: 当日收益率
            
        Returns:
            (是否触发止盈, 原因)
        """
        if daily_return >= self.daily_take_profit:
            return True, f"每日止盈触发: 当日收益率 {daily_return:.2%} >= {self.daily_take_profit:.2%}"
        return False, ""
    
    def check_total_stop_loss(self, total_return: float) -> Tuple[bool, str]:
        """
        检查累计止损
        
        Args:
            total_return: 累计收益率
            
        Returns:
            (是否触发止损, 原因)
        """
        if total_return <= self.total_stop_loss:
            return True, f"累计止损触发: 累计收益率 {total_return:.2%} <= {self.total_stop_loss:.2%}"
        return False, ""
    
    def check_trailing_stop(self, current_value: float) -> Tuple[bool, str]:
        """
        检查追踪止损
        
        Args:
            current_value: 当前资产价值
            
        Returns:
            (是否触发止损, 原因)
        """
        if self.trailing_stop <= 0 or self.peak_value <= 0:
            return False, ""
        
        drawdown = (self.peak_value - current_value) / self.peak_value
        if drawdown >= self.trailing_stop:
            return True, f"追踪止损触发: 回撤 {drawdown:.2%} >= {self.trailing_stop:.2%}"
        return False, ""
    
    def check_all(
        self, 
        daily_return: float, 
        total_return: float, 
        current_value: float
    ) -> Tuple[bool, str, str]:
        """
        检查所有风险控制条件
        
        Args:
            daily_return: 当日收益率
            total_return: 累计收益率
            current_value: 当前资产价值
            
        Returns:
            (是否触发, 触发类型, 原因)
        """
        # 更新峰值
        self.update_peak(current_value)
        
        # 检查每日止损
        triggered, reason = self.check_daily_stop_loss(daily_return)
        if triggered:
            return True, 'daily_stop_loss', reason
        
        # 检查每日止盈
        triggered, reason = self.check_daily_take_profit(daily_return)
        if triggered:
            return True, 'daily_take_profit', reason
        
        # 检查累计止损
        triggered, reason = self.check_total_stop_loss(total_return)
        if triggered:
            return True, 'total_stop_loss', reason
        
        # 检查追踪止损
        triggered, reason = self.check_trailing_stop(current_value)
        if triggered:
            return True, 'trailing_stop', reason
        
        return False, '', ''



class CustomStrategyBacktest:
    """
    自定义策略回测引擎
    
    实现用户自定义策略的完整回测流程
    """
    
    def __init__(
        self,
        strategy_config: CustomStrategyConfig,
        initial_capital: float = 100000.0,
        benchmark_code: str = '000300'  # 沪深300作为基准
    ):
        """
        初始化回测引擎
        
        Args:
            strategy_config: 策略配置
            initial_capital: 初始资金
            benchmark_code: 基准指数代码
        """
        self.config = strategy_config
        self.initial_capital = initial_capital
        self.benchmark_code = benchmark_code
        
        # 初始化组件
        self.filter_engine = FilterEngine()
        self.sorting_engine = SortingEngine()
        self.weight_calculator = WeightCalculator()
        self.risk_controller = RiskController(
            daily_stop_loss=strategy_config.daily_stop_loss,
            daily_take_profit=strategy_config.daily_take_profit,
            total_stop_loss=strategy_config.total_stop_loss,
            trailing_stop=strategy_config.trailing_stop
        )
        
        # 回测状态
        self.cash = initial_capital
        self.holdings: Dict[str, Dict] = {}  # {fund_code: {shares, cost_price, ...}}
        self.trades: List[TradeRecord] = []
        self.equity_curve: List[Dict] = []
        self.benchmark_curve: List[Dict] = []
    
    def reset(self):
        """重置回测状态"""
        self.cash = self.initial_capital
        self.holdings = {}
        self.trades = []
        self.equity_curve = []
        self.benchmark_curve = []
        self.risk_controller.reset()
    
    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        """
        计算组合总价值
        
        Args:
            prices: 基金价格字典 {fund_code: price}
            
        Returns:
            组合总价值
        """
        holdings_value = sum(
            h['shares'] * prices.get(code, h.get('last_price', 0))
            for code, h in self.holdings.items()
        )
        return self.cash + holdings_value
    
    def get_holdings_value(self, prices: Dict[str, float]) -> float:
        """
        计算持仓价值
        
        Args:
            prices: 基金价格字典
            
        Returns:
            持仓总价值
        """
        return sum(
            h['shares'] * prices.get(code, h.get('last_price', 0))
            for code, h in self.holdings.items()
        )
    
    def execute_buy(
        self,
        fund_code: str,
        fund_name: str,
        amount: float,
        price: float,
        date: str,
        reason: str = ''
    ) -> Optional[TradeRecord]:
        """
        执行买入操作
        
        Args:
            fund_code: 基金代码
            fund_name: 基金名称
            amount: 买入金额
            price: 买入价格
            date: 交易日期
            reason: 交易原因
            
        Returns:
            交易记录或None
        """
        if amount <= 0 or price <= 0:
            return None
        
        if self.cash < amount:
            amount = self.cash  # 使用可用资金
        
        if amount <= 0:
            return None
        
        shares = amount / price
        self.cash -= amount
        
        # 更新持仓
        if fund_code in self.holdings:
            old_shares = self.holdings[fund_code]['shares']
            old_cost = self.holdings[fund_code]['cost_price']
            new_shares = old_shares + shares
            # 计算新的平均成本
            new_cost = (old_shares * old_cost + shares * price) / new_shares
            self.holdings[fund_code]['shares'] = new_shares
            self.holdings[fund_code]['cost_price'] = new_cost
            self.holdings[fund_code]['last_price'] = price
        else:
            self.holdings[fund_code] = {
                'shares': shares,
                'cost_price': price,
                'last_price': price,
                'fund_name': fund_name
            }
        
        # 创建交易记录
        trade = TradeRecord(
            date=date,
            fund_code=fund_code,
            fund_name=fund_name,
            action='buy',
            amount=amount,
            price=price,
            shares=shares,
            balance=self.cash,
            holdings_value=self.get_holdings_value({fund_code: price}),
            reason=reason
        )
        self.trades.append(trade)
        
        return trade
    
    def execute_sell(
        self,
        fund_code: str,
        shares: Optional[float],
        price: float,
        date: str,
        action: str = 'sell',
        reason: str = ''
    ) -> Optional[TradeRecord]:
        """
        执行卖出操作
        
        Args:
            fund_code: 基金代码
            shares: 卖出份额（None表示全部卖出）
            price: 卖出价格
            date: 交易日期
            action: 交易类型
            reason: 交易原因
            
        Returns:
            交易记录或None
        """
        if fund_code not in self.holdings:
            return None
        
        holding = self.holdings[fund_code]
        
        if shares is None:
            shares = holding['shares']  # 全部卖出
        
        shares = min(shares, holding['shares'])
        
        if shares <= 0:
            return None
        
        amount = shares * price
        self.cash += amount
        
        fund_name = holding.get('fund_name', fund_code)
        
        # 更新持仓
        holding['shares'] -= shares
        holding['last_price'] = price
        
        if holding['shares'] <= 0:
            del self.holdings[fund_code]
        
        # 创建交易记录
        trade = TradeRecord(
            date=date,
            fund_code=fund_code,
            fund_name=fund_name,
            action=action,
            amount=amount,
            price=price,
            shares=shares,
            balance=self.cash,
            holdings_value=self.get_holdings_value({fund_code: price}),
            reason=reason
        )
        self.trades.append(trade)
        
        return trade
    
    def rebalance(
        self,
        target_funds: List[Dict[str, Any]],
        weights: List[float],
        prices: Dict[str, float],
        date: str
    ):
        """
        调仓操作
        
        Args:
            target_funds: 目标基金列表
            weights: 目标权重
            prices: 当前价格
            date: 交易日期
        """
        total_value = self.get_portfolio_value(prices)
        
        # 计算目标持仓
        target_holdings = {}
        for fund, weight in zip(target_funds, weights):
            fund_code = fund.get('fund_code')
            if fund_code and fund_code in prices:
                target_value = total_value * weight
                target_shares = target_value / prices[fund_code]
                target_holdings[fund_code] = {
                    'shares': target_shares,
                    'fund_name': fund.get('fund_name', fund_code)
                }
        
        # 卖出不在目标中的持仓
        for fund_code in list(self.holdings.keys()):
            if fund_code not in target_holdings:
                price = prices.get(fund_code, self.holdings[fund_code].get('last_price', 0))
                self.execute_sell(
                    fund_code=fund_code,
                    shares=None,  # 全部卖出
                    price=price,
                    date=date,
                    reason='不在目标持仓中'
                )
        
        # 调整现有持仓
        for fund_code, target in target_holdings.items():
            price = prices.get(fund_code, 0)
            if price <= 0:
                continue
            
            current_shares = self.holdings.get(fund_code, {}).get('shares', 0)
            target_shares = target['shares']
            diff = target_shares - current_shares
            
            if diff > 0:
                # 需要买入
                amount = diff * price
                self.execute_buy(
                    fund_code=fund_code,
                    fund_name=target['fund_name'],
                    amount=amount,
                    price=price,
                    date=date,
                    reason='调仓买入'
                )
            elif diff < 0:
                # 需要卖出
                self.execute_sell(
                    fund_code=fund_code,
                    shares=-diff,
                    price=price,
                    date=date,
                    reason='调仓卖出'
                )
    
    def run_backtest(
        self,
        funds_data: pd.DataFrame,
        start_date: str,
        end_date: str,
        rebalance_freq: str = 'monthly'  # 'daily', 'weekly', 'monthly'
    ) -> BacktestResult:
        """
        执行回测
        
        Args:
            funds_data: 基金数据DataFrame，包含日期、基金代码、净值等
            start_date: 开始日期
            end_date: 结束日期
            rebalance_freq: 调仓频率
            
        Returns:
            回测结果
        """
        self.reset()
        
        # 获取交易日期列表
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        prev_portfolio_value = self.initial_capital
        last_rebalance_date = None
        
        for date in dates:
            date_str = date.strftime('%Y-%m-%d')
            
            # 获取当日基金数据
            daily_data = self._get_daily_data(funds_data, date_str)
            if daily_data.empty:
                continue
            
            # 获取当日价格
            prices = self._get_prices(daily_data)
            
            # 计算当前组合价值
            current_value = self.get_portfolio_value(prices)
            
            # 计算收益率
            daily_return = (current_value - prev_portfolio_value) / prev_portfolio_value if prev_portfolio_value > 0 else 0
            total_return = (current_value - self.initial_capital) / self.initial_capital
            
            # 风险控制检查
            triggered, trigger_type, reason = self.risk_controller.check_all(
                daily_return, total_return, current_value
            )
            
            if triggered:
                # 触发风险控制，清仓
                for fund_code in list(self.holdings.keys()):
                    price = prices.get(fund_code, self.holdings[fund_code].get('last_price', 0))
                    self.execute_sell(
                        fund_code=fund_code,
                        shares=None,
                        price=price,
                        date=date_str,
                        action=trigger_type,
                        reason=reason
                    )
            else:
                # 检查是否需要调仓
                if self._should_rebalance(date, last_rebalance_date, rebalance_freq):
                    # 执行选股和调仓
                    self._execute_strategy(daily_data, prices, date_str)
                    last_rebalance_date = date
            
            # 更新净值曲线
            self.equity_curve.append({
                'date': date_str,
                'value': current_value
            })
            
            prev_portfolio_value = current_value
        
        # 计算绩效指标
        return self._calculate_performance()
    
    def _get_daily_data(self, funds_data: pd.DataFrame, date_str: str) -> pd.DataFrame:
        """获取指定日期的基金数据"""
        if 'date' in funds_data.columns:
            return funds_data[funds_data['date'] == date_str]
        elif 'analysis_date' in funds_data.columns:
            return funds_data[funds_data['analysis_date'] == date_str]
        return pd.DataFrame()
    
    def _get_prices(self, daily_data: pd.DataFrame) -> Dict[str, float]:
        """获取基金价格字典"""
        prices = {}
        price_col = 'nav' if 'nav' in daily_data.columns else 'current_nav'
        code_col = 'fund_code'
        
        for _, row in daily_data.iterrows():
            code = row.get(code_col)
            price = row.get(price_col)
            if code and price and pd.notna(price):
                prices[code] = float(price)
        
        return prices
    
    def _should_rebalance(
        self, 
        current_date, 
        last_rebalance_date, 
        freq: str
    ) -> bool:
        """判断是否需要调仓"""
        if last_rebalance_date is None:
            return True
        
        if freq == 'daily':
            return True
        elif freq == 'weekly':
            return (current_date - last_rebalance_date).days >= 7
        elif freq == 'monthly':
            return current_date.month != last_rebalance_date.month
        
        return False
    
    def _execute_strategy(
        self, 
        daily_data: pd.DataFrame, 
        prices: Dict[str, float],
        date_str: str
    ):
        """执行策略选股和调仓"""
        # 转换为字典列表
        funds_list = daily_data.to_dict('records')
        
        # 应用筛选条件
        filtered_funds = self.filter_engine.filter_funds(
            funds_list,
            self.config.filter_conditions,
            self.config.filter_logic
        )
        
        if not filtered_funds:
            return
        
        # 排序选股
        selected_funds = self.sorting_engine.sort_and_select(
            filtered_funds,
            self.config.sort_field,
            self.config.sort_order,
            self.config.select_count
        )
        
        if not selected_funds:
            return
        
        # 计算权重
        weights = self.weight_calculator.calculate_weights(
            len(selected_funds),
            self.config.weight_mode,
            self.config.custom_weights
        )
        
        # 执行调仓
        self.rebalance(selected_funds, weights, prices, date_str)
    
    def _calculate_performance(self) -> BacktestResult:
        """计算绩效指标"""
        result = BacktestResult()
        result.trades = self.trades
        result.equity_curve = self.equity_curve
        
        if not self.equity_curve:
            return result
        
        # 提取净值序列
        values = [e['value'] for e in self.equity_curve]
        
        if len(values) < 2:
            return result
        
        # 使用 PerformanceCalculator 计算指标
        calculator = PerformanceCalculator()
        
        # 转换交易记录为字典列表
        trades_dict = [
            {
                'fund_code': t.fund_code,
                'action': t.action,
                'amount': t.amount,
                'shares': t.shares,
                'price': t.price
            } for t in self.trades
        ]
        
        # 计算所有指标
        metrics = calculator.calculate_all_metrics(
            equity_curve=values,
            benchmark_curve=None,  # 可以后续添加基准曲线
            trades=trades_dict
        )
        
        # 填充结果
        result.total_return = metrics.total_return
        result.annual_return = metrics.annual_return
        result.benchmark_return = metrics.benchmark_return
        result.excess_return = metrics.excess_return
        result.max_drawdown = metrics.max_drawdown
        result.volatility = metrics.volatility
        result.sharpe_ratio = metrics.sharpe_ratio
        result.sortino_ratio = metrics.sortino_ratio
        result.calmar_ratio = metrics.calmar_ratio
        result.win_rate = metrics.win_rate
        result.profit_loss_ratio = metrics.profit_loss_ratio
        result.total_trades = metrics.total_trades
        result.winning_trades = metrics.winning_trades
        result.losing_trades = metrics.losing_trades
        
        return result


# 便捷函数
def run_custom_backtest(
    strategy_config: CustomStrategyConfig,
    funds_data: pd.DataFrame,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000.0,
    rebalance_freq: str = 'monthly'
) -> BacktestResult:
    """
    运行自定义策略回测
    
    Args:
        strategy_config: 策略配置
        funds_data: 基金数据
        start_date: 开始日期
        end_date: 结束日期
        initial_capital: 初始资金
        rebalance_freq: 调仓频率
        
    Returns:
        回测结果
    """
    engine = CustomStrategyBacktest(
        strategy_config=strategy_config,
        initial_capital=initial_capital
    )
    
    return engine.run_backtest(
        funds_data=funds_data,
        start_date=start_date,
        end_date=end_date,
        rebalance_freq=rebalance_freq
    )
