#!/usr/bin/env python
# coding: utf-8

"""
统一策略引擎
整合所有策略组件，提供统一的策略分析入口
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from .strategy_config import StrategyConfig, get_strategy_config
from .stop_loss_manager import StopLossManager, StopLossLevel, StopLossResult
from .trend_analyzer import TrendAnalyzer, TrendType, TrendResult
from .position_manager import PositionManager, VolatilityLevel, PositionAdjustment
from .strategy_evaluator import StrategyEvaluator, EvaluationResult
from .enhanced_engine.risk_metrics import EnhancedRiskMetrics

logger = logging.getLogger(__name__)


@dataclass
class UnifiedStrategyResult:
    """统一策略分析结果"""
    # 基础策略结果
    strategy_name: str
    action: str
    base_buy_multiplier: float
    final_buy_multiplier: float
    redeem_amount: float
    status_label: str
    operation_suggestion: str
    execution_amount: str
    
    # 止损状态
    stop_loss_triggered: bool
    stop_loss_level: str
    stop_loss_label: str
    
    # 趋势分析
    trend: str
    trend_adjustment: float
    
    # 波动率调整
    volatility: float
    volatility_level: str
    volatility_adjustment: float
    
    # 风险调整标志
    risk_adjusted: bool
    
    # 综合建议
    final_suggestion: str


class UnifiedStrategyEngine:
    """统一策略引擎"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化统一策略引擎
        
        Args:
            config_path: 配置文件路径
        """
        self.config = get_strategy_config(config_path)
        self.stop_loss_manager = StopLossManager(self.config)
        self.trend_analyzer = TrendAnalyzer(self.config)
        self.position_manager = PositionManager(self.config)
        self.risk_metrics = EnhancedRiskMetrics()
        self.evaluator = StrategyEvaluator()
        
        # 加载策略规则
        self._load_strategy_rules()
        
        logger.info("统一策略引擎初始化完成")
    
    def _load_strategy_rules(self) -> None:
        """加载策略规则"""
        self.strategy_rules = self.config.get_strategy_thresholds()
        self.buy_multipliers = self.config.get_buy_multipliers()
        self.default_strategy = self.config.get_default_strategy()
    
    def analyze(
        self,
        today_return: float,
        prev_day_return: float,
        returns_history: Optional[List[float]] = None,
        cumulative_pnl: Optional[float] = None,
        performance_metrics: Optional[Dict] = None
    ) -> UnifiedStrategyResult:
        """
        综合策略分析
        
        Args:
            today_return: 当日收益率（%）
            prev_day_return: 前一日收益率（%）
            returns_history: 历史收益率序列（用于趋势和波动率分析）
            cumulative_pnl: 累计盈亏率（用于止损检查）
            performance_metrics: 绩效指标（可选增强分析）
            
        Returns:
            UnifiedStrategyResult: 综合策略分析结果
        """
        try:
            # 1. 基础策略分析
            base_result = self._basic_strategy_analysis(today_return, prev_day_return)
            
            # 2. 止损检查
            stop_loss_result = self._check_stop_loss(cumulative_pnl)
            
            # 如果触发止损，直接返回止损结果
            if stop_loss_result.triggered:
                return self._create_stop_loss_result(stop_loss_result, base_result)
            
            # 3. 趋势分析
            trend_result = self._analyze_trend(returns_history)
            
            # 4. 波动率调整
            position_adjustment = self._adjust_position(returns_history, base_result['buy_multiplier'])
            
            # 5. 绩效增强分析
            enhanced_multiplier = self._apply_performance_enhancement(
                position_adjustment.adjusted_multiplier,
                performance_metrics
            )
            
            # 6. 综合结果
            return self._create_unified_result(
                base_result,
                stop_loss_result,
                trend_result,
                position_adjustment,
                enhanced_multiplier
            )
            
        except Exception as e:
            logger.error(f"策略分析失败: {str(e)}")
            return self._create_default_result()
    
    def _basic_strategy_analysis(
        self, 
        today_return: float, 
        prev_day_return: float
    ) -> Dict:
        """
        基础策略分析
        
        Args:
            today_return: 当日收益率（%）
            prev_day_return: 前一日收益率（%）
            
        Returns:
            基础策略结果字典
        """
        # 遍历所有策略规则
        for strategy_name, rule in self.strategy_rules.items():
            conditions = rule.get('conditions', [])
            
            for condition in conditions:
                today_min = condition.get('today_return_min', float('-inf'))
                today_max = condition.get('today_return_max', float('inf'))
                prev_min = condition.get('prev_day_return_min', float('-inf'))
                prev_max = condition.get('prev_day_return_max', float('inf'))
                
                # 处理 YAML 中的 .inf 值
                if today_min == '.inf':
                    today_min = float('inf')
                elif today_min == '-.inf':
                    today_min = float('-inf')
                if today_max == '.inf':
                    today_max = float('inf')
                elif today_max == '-.inf':
                    today_max = float('-inf')
                if prev_min == '.inf':
                    prev_min = float('inf')
                elif prev_min == '-.inf':
                    prev_min = float('-inf')
                if prev_max == '.inf':
                    prev_max = float('inf')
                elif prev_max == '-.inf':
                    prev_max = float('-inf')
                
                # 检查是否满足条件
                if (today_min <= today_return <= today_max and 
                    prev_min <= prev_day_return <= prev_max):
                    
                    action = rule.get('action', 'hold')
                    buy_multiplier = rule.get('buy_multiplier', self.buy_multipliers.get(action, 0.0))
                    
                    return {
                        'strategy_name': strategy_name,
                        'action': action,
                        'buy_multiplier': buy_multiplier,
                        'redeem_amount': rule.get('redeem_amount', 0),
                        'status_label': rule.get('label', ''),
                        'operation_suggestion': rule.get('description', ''),
                        'comparison_value': today_return - prev_day_return
                    }
        
        # 默认策略
        return {
            'strategy_name': 'default',
            'action': self.default_strategy.get('action', 'hold'),
            'buy_multiplier': self.default_strategy.get('buy_multiplier', 0.0),
            'redeem_amount': self.default_strategy.get('redeem_amount', 0),
            'status_label': self.default_strategy.get('label', '🔴 **未知状态**'),
            'operation_suggestion': self.default_strategy.get('description', '不买入，不赎回'),
            'comparison_value': today_return - prev_day_return
        }
    
    def _check_stop_loss(self, cumulative_pnl: Optional[float]) -> StopLossResult:
        """检查止损"""
        if cumulative_pnl is None:
            return StopLossResult(
                triggered=False,
                level=StopLossLevel.NONE,
                action='none',
                label='',
                suggestion='',
                cumulative_loss=0.0
            )
        
        return self.stop_loss_manager.check_stop_loss(cumulative_pnl)
    
    def _analyze_trend(self, returns_history: Optional[List[float]]) -> TrendResult:
        """分析趋势"""
        if returns_history is None or len(returns_history) < 10:
            return TrendResult(
                trend=TrendType.SIDEWAYS,
                returns_short=0.0,
                returns_long=0.0,
                multiplier_adjustment=1.0,
                confidence=0.0
            )
        
        return self.trend_analyzer.analyze_trend(returns_history)
    
    def _adjust_position(
        self, 
        returns_history: Optional[List[float]],
        base_multiplier: float
    ) -> PositionAdjustment:
        """调整仓位"""
        if returns_history is None or len(returns_history) < 2:
            return PositionAdjustment(
                volatility=0.0,
                volatility_level=VolatilityLevel.NORMAL,
                adjustment_factor=1.0,
                adjusted_multiplier=base_multiplier,
                original_multiplier=base_multiplier
            )
        
        return self.position_manager.adjust_from_returns(base_multiplier, returns_history)
    
    def _apply_performance_enhancement(
        self,
        current_multiplier: float,
        performance_metrics: Optional[Dict]
    ) -> float:
        """应用绩效增强"""
        if performance_metrics is None:
            return current_multiplier
        
        enhanced_multiplier = current_multiplier
        
        # 获取绩效指标
        sharpe_ratio = performance_metrics.get('sharpe_ratio', 0.0)
        max_drawdown = performance_metrics.get('max_drawdown', 0.0)
        volatility = performance_metrics.get('volatility', 0.0)
        win_rate = performance_metrics.get('win_rate', 0.0)
        composite_score = performance_metrics.get('composite_score', 0.0)
        
        # 如果基金绩效优秀，增强买入信号
        if composite_score > 0.7 and sharpe_ratio > 1.0:
            enhanced_multiplier = min(3.0, enhanced_multiplier * 1.5)
            logger.debug(f"绩效优秀，买入倍数增强: {current_multiplier} -> {enhanced_multiplier}")
        
        # 如果基金波动率过高，降低买入倍数
        if volatility > 0.3:
            enhanced_multiplier = max(0.5, enhanced_multiplier * 0.7)
            logger.debug(f"高波动风险，买入倍数降低: {current_multiplier} -> {enhanced_multiplier}")
        
        # 如果最大回撤过大，谨慎操作
        if abs(max_drawdown) > 0.2:
            enhanced_multiplier = min(1.0, enhanced_multiplier * 0.5)
            logger.debug(f"回撤风险，买入倍数降低: {current_multiplier} -> {enhanced_multiplier}")
        
        # 如果胜率较低，降低买入信号
        if win_rate < 0.5:
            enhanced_multiplier = max(0.3, enhanced_multiplier * 0.6)
            logger.debug(f"胜率偏低，买入倍数降低: {current_multiplier} -> {enhanced_multiplier}")
        
        return enhanced_multiplier
    
    def _create_stop_loss_result(
        self,
        stop_loss_result: StopLossResult,
        base_result: Dict
    ) -> UnifiedStrategyResult:
        """创建止损结果"""
        return UnifiedStrategyResult(
            strategy_name='stop_loss',
            action='stop_loss',
            base_buy_multiplier=0.0,
            final_buy_multiplier=0.0,
            redeem_amount=100.0,  # 全部赎回
            status_label=stop_loss_result.label,
            operation_suggestion=stop_loss_result.suggestion,
            execution_amount="全部赎回",
            stop_loss_triggered=True,
            stop_loss_level=stop_loss_result.level.value,
            stop_loss_label=stop_loss_result.label,
            trend='unknown',
            trend_adjustment=1.0,
            volatility=0.0,
            volatility_level='unknown',
            volatility_adjustment=1.0,
            risk_adjusted=True,
            final_suggestion=f"⚠️ 止损触发！累计亏损 {stop_loss_result.cumulative_loss:.1%}，建议全部赎回止损。"
        )
    
    def _create_unified_result(
        self,
        base_result: Dict,
        stop_loss_result: StopLossResult,
        trend_result: TrendResult,
        position_adjustment: PositionAdjustment,
        final_multiplier: float
    ) -> UnifiedStrategyResult:
        """创建统一结果"""
        # 应用趋势调整
        trend_adjusted_multiplier = final_multiplier * trend_result.multiplier_adjustment
        
        # 生成执行金额描述
        execution_amount = self._get_execution_amount(
            base_result['action'],
            trend_adjusted_multiplier,
            base_result['redeem_amount']
        )
        
        # 生成综合建议
        final_suggestion = self._generate_final_suggestion(
            base_result,
            stop_loss_result,
            trend_result,
            position_adjustment,
            trend_adjusted_multiplier
        )
        
        # 判断是否进行了风险调整
        risk_adjusted = (
            trend_result.multiplier_adjustment != 1.0 or
            position_adjustment.adjustment_factor != 1.0 or
            stop_loss_result.level != StopLossLevel.NONE
        )
        
        return UnifiedStrategyResult(
            strategy_name=base_result['strategy_name'],
            action=base_result['action'],
            base_buy_multiplier=base_result['buy_multiplier'],
            final_buy_multiplier=trend_adjusted_multiplier,
            redeem_amount=base_result['redeem_amount'],
            status_label=base_result['status_label'],
            operation_suggestion=base_result['operation_suggestion'],
            execution_amount=execution_amount,
            stop_loss_triggered=False,
            stop_loss_level=stop_loss_result.level.value,
            stop_loss_label=stop_loss_result.label if stop_loss_result.level != StopLossLevel.NONE else '',
            trend=trend_result.trend.value,
            trend_adjustment=trend_result.multiplier_adjustment,
            volatility=position_adjustment.volatility,
            volatility_level=position_adjustment.volatility_level.value,
            volatility_adjustment=position_adjustment.adjustment_factor,
            risk_adjusted=risk_adjusted,
            final_suggestion=final_suggestion
        )
    
    def _create_default_result(self) -> UnifiedStrategyResult:
        """创建默认结果"""
        return UnifiedStrategyResult(
            strategy_name='default',
            action='hold',
            base_buy_multiplier=0.0,
            final_buy_multiplier=0.0,
            redeem_amount=0,
            status_label='🔴 **未知状态**',
            operation_suggestion='不买入，不赎回',
            execution_amount='持有不动',
            stop_loss_triggered=False,
            stop_loss_level='none',
            stop_loss_label='',
            trend='sideways',
            trend_adjustment=1.0,
            volatility=0.0,
            volatility_level='normal',
            volatility_adjustment=1.0,
            risk_adjusted=False,
            final_suggestion='数据不足，建议持有观望'
        )
    
    def _get_execution_amount(
        self,
        action: str,
        multiplier: float,
        redeem_amount: float
    ) -> str:
        """获取执行金额描述"""
        if action == 'stop_loss':
            return "全部赎回"
        elif action in ['sell', 'weak_sell']:
            return f"赎回¥{redeem_amount}"
        elif action == 'hold':
            return "持有不动"
        elif multiplier > 0:
            return f"买入{multiplier:.1f}×定额"
        else:
            return "持有不动"
    
    def _generate_final_suggestion(
        self,
        base_result: Dict,
        stop_loss_result: StopLossResult,
        trend_result: TrendResult,
        position_adjustment: PositionAdjustment,
        final_multiplier: float
    ) -> str:
        """生成综合建议"""
        suggestions = []
        
        # 基础建议
        suggestions.append(base_result['operation_suggestion'])
        
        # 止损警告
        if stop_loss_result.level == StopLossLevel.WARNING:
            suggestions.append(f"⚠️ {stop_loss_result.suggestion}")
        
        # 趋势提示
        if trend_result.trend == TrendType.UPTREND:
            suggestions.append(f"📈 上涨趋势，买入倍数+{(trend_result.multiplier_adjustment-1)*100:.0f}%")
        elif trend_result.trend == TrendType.DOWNTREND:
            suggestions.append(f"📉 下跌趋势，买入倍数-{(1-trend_result.multiplier_adjustment)*100:.0f}%")
        
        # 波动率提示
        if position_adjustment.volatility_level == VolatilityLevel.HIGH:
            suggestions.append(f"⚡ 高波动（{position_adjustment.volatility:.1%}），仓位减半")
        elif position_adjustment.volatility_level == VolatilityLevel.LOW:
            suggestions.append(f"🌊 低波动（{position_adjustment.volatility:.1%}），仓位增加")
        
        return " | ".join(suggestions)
    
    def to_dict(self, result: UnifiedStrategyResult) -> Dict:
        """将结果转换为字典"""
        return {
            'strategy_name': result.strategy_name,
            'action': result.action,
            'base_buy_multiplier': result.base_buy_multiplier,
            'final_buy_multiplier': result.final_buy_multiplier,
            'redeem_amount': result.redeem_amount,
            'status_label': result.status_label,
            'operation_suggestion': result.operation_suggestion,
            'execution_amount': result.execution_amount,
            'stop_loss_triggered': result.stop_loss_triggered,
            'stop_loss_level': result.stop_loss_level,
            'stop_loss_label': result.stop_loss_label,
            'trend': result.trend,
            'trend_adjustment': result.trend_adjustment,
            'volatility': result.volatility,
            'volatility_level': result.volatility_level,
            'volatility_adjustment': result.volatility_adjustment,
            'risk_adjusted': result.risk_adjusted,
            'final_suggestion': result.final_suggestion
        }
    
    def reload_config(self) -> bool:
        """重新加载配置"""
        success = self.config.reload_config()
        if success:
            self._load_strategy_rules()
            logger.info("策略配置重新加载成功")
        return success


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    engine = UnifiedStrategyEngine()
    
    print("=== 基础策略测试 ===")
    
    # 测试各种情况
    test_cases = [
        (2.5, 1.2, "强势上涨"),
        (0.8, 0.6, "持续上涨"),
        (0.1, 0.8, "上涨放缓"),
        (1.2, -0.5, "反转上涨"),
        (-0.8, 0.8, "反转下跌"),
        (-2.5, 0.05, "首次大跌"),
    ]
    
    for today, prev, desc in test_cases:
        result = engine.analyze(today, prev)
        print(f"\n{desc}: 今日={today}%, 昨日={prev}%")
        print(f"  策略: {result.strategy_name}")
        print(f"  操作: {result.action}")
        print(f"  买入倍数: {result.final_buy_multiplier}")
        print(f"  建议: {result.final_suggestion}")
    
    print("\n=== 止损测试 ===")
    result = engine.analyze(0.5, 0.3, cumulative_pnl=-0.18)
    print(f"累计亏损18%:")
    print(f"  止损触发: {result.stop_loss_triggered}")
    print(f"  建议: {result.final_suggestion}")
    
    print("\n=== 趋势和波动率测试 ===")
    # 模拟上涨趋势的历史数据
    uptrend_history = [0.001, 0.002, 0.001, 0.003, 0.002, 0.004, 0.003, 0.005, 0.004, 0.006]
    result = engine.analyze(0.8, 0.6, returns_history=uptrend_history)
    print(f"上涨趋势:")
    print(f"  趋势: {result.trend}")
    print(f"  趋势调整: {result.trend_adjustment}")
    print(f"  基础倍数: {result.base_buy_multiplier}")
    print(f"  最终倍数: {result.final_buy_multiplier}")
    print(f"  建议: {result.final_suggestion}")
    
    # 模拟高波动的历史数据
    high_vol_history = [0.03, -0.04, 0.05, -0.03, 0.04, -0.05, 0.03, -0.04, 0.05, -0.03]
    result = engine.analyze(0.8, 0.6, returns_history=high_vol_history)
    print(f"\n高波动:")
    print(f"  波动率: {result.volatility:.1%}")
    print(f"  波动率级别: {result.volatility_level}")
    print(f"  波动率调整: {result.volatility_adjustment}")
    print(f"  最终倍数: {result.final_buy_multiplier}")
    print(f"  建议: {result.final_suggestion}")
