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
    adx: float = 0.0
    adx_trend_strength: str = "unknown"
    
    # 波动率调整
    volatility: float = 0.0
    volatility_level: str = "unknown"
    volatility_adjustment: float = 1.0
    
    # 市场Beta调整
    market_beta_adjusted: bool = False
    market_condition: str = "neutral"
    
    # 成交量确认
    volume_confirmed: bool = False
    volume_ratio: float = 1.0
    
    # 风险调整标志
    risk_adjusted: bool = False
    
    # 综合建议
    final_suggestion: str = ""


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
        performance_metrics: Optional[Dict] = None,
        strategy_id: Optional[str] = None,
        market_data: Optional[Dict] = None,
        volume_data: Optional[Dict] = None,
        base_invest: float = 100.0
    ) -> UnifiedStrategyResult:
        """
        综合策略分析
        
        Args:
            today_return: 当日收益率（%）
            prev_day_return: 前一日收益率（%）
            returns_history: 历史收益率序列（用于趋势和波动率分析）
            cumulative_pnl: 累计盈亏率（用于止损检查）
            performance_metrics: 绩效指标（可选增强分析）
            strategy_id: 特定策略ID（可选），如果指定则只应用该策略
            market_data: 市场数据（可选），包含大盘指数收益等
            volume_data: 成交量数据（可选），包含近期成交量等
            
        Returns:
            UnifiedStrategyResult: 综合策略分析结果
        """
        try:
            # 1. 基础策略分析
            base_result = self._basic_strategy_analysis(today_return, prev_day_return, strategy_id)
            
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
            
            # 6. 新增：市场Beta调整
            beta_adjusted_result = self._apply_market_beta_adjustment(
                base_result, enhanced_multiplier, market_data
            )
            
            # 7. 新增：成交量确认
            volume_confirmed_result = self._apply_volume_confirmation(
                beta_adjusted_result, volume_data, today_return
            )
            
            # 8. 综合结果
            return self._create_unified_result(
                volume_confirmed_result,
                stop_loss_result,
                trend_result,
                position_adjustment,
                volume_confirmed_result.get('final_multiplier', enhanced_multiplier),
                base_invest
            )
            
        except Exception as e:
            logger.error(f"策略分析失败: {str(e)}")
            return self._create_default_result()
    
    def _basic_strategy_analysis(
        self, 
        today_return: float, 
        prev_day_return: float,
        strategy_id: Optional[str] = None
    ) -> Dict:
        """
        基础策略分析
        
        Args:
            today_return: 当日收益率（%）
            prev_day_return: 前一日收益率（%）
            strategy_id: 特定策略ID（可选），如果指定则只应用该策略
            
        Returns:
            基础策略结果字典
        """
        # 如果指定了特定策略ID，则只应用该策略
        if strategy_id and strategy_id in self.strategy_rules:
            rule = self.strategy_rules[strategy_id]
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
                        'strategy_name': strategy_id,
                        'action': action,
                        'buy_multiplier': buy_multiplier,
                        'redeem_amount': rule.get('redeem_amount', 0),
                        'status_label': rule.get('label', ''),
                        'operation_suggestion': rule.get('description', ''),
                        'comparison_value': today_return - prev_day_return
                    }
            
            # 如果指定了策略ID但条件不匹配，返回该策略的默认行为
            return {
                'strategy_name': strategy_id,
                'action': 'hold',  # 默认为持有
                'buy_multiplier': 0.0,
                'redeem_amount': 0,
                'status_label': f'{strategy_id} - 未满足执行条件',
                'operation_suggestion': f'当前市场条件下，{strategy_id}策略建议保持观望',
                'comparison_value': today_return - prev_day_return
            }
        
        # 否则，按优先级遍历所有策略规则
        # 获取优先级配置
        priority_weights = self.config.get('priority_weights', {})
        
        # 按优先级排序（数值越大优先级越高）
        sorted_strategies = sorted(
            self.strategy_rules.items(),
            key=lambda x: priority_weights.get(x[0], 0),
            reverse=True
        )
        
        # 遍历排序后的策略规则
        for strategy_name, rule in sorted_strategies:
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
    
    def _apply_market_beta_adjustment(
        self,
        base_result: Dict,
        current_multiplier: float,
        market_data: Optional[Dict]
    ) -> Dict:
        """
        应用市场Beta调整
        
        Args:
            base_result: 基础策略结果
            current_multiplier: 当前买入倍数
            market_data: 市场数据
            
        Returns:
            调整后的结果字典
        """
        result = base_result.copy()
        result['final_multiplier'] = current_multiplier
        
        if market_data is None:
            return result
        
        market_return = market_data.get('index_return', 0.0)
        market_sentiment = market_data.get('sentiment', 'neutral')
        
        # 熊市中降低买入倍数
        if market_return < -0.02:  # 大盘跌2%以上
            result['final_multiplier'] = current_multiplier * 0.7
            result['status_label'] += " 📉大盘弱势"
            result['operation_suggestion'] += "（大盘走弱，降低仓位）"
            logger.debug(f"市场Beta调整: 大盘跌{market_return:.2%}, 倍数 {current_multiplier} -> {result['final_multiplier']}")
        
        # 牛市中提高止盈阈值
        elif market_return > 0.02:  # 大盘涨2%以上
            if base_result['action'] == 'sell':
                result['action'] = 'hold'
                result['final_multiplier'] = 0.0
                result['status_label'] += " 📈大盘强势"
                result['operation_suggestion'] = "牛市中暂停止盈，让利润奔跑"
                logger.debug("市场Beta调整: 大盘强势，暂停卖出")
        
        # 极端情绪调整
        if market_sentiment == 'extreme_fear':
            # 极度恐慌可能是买入机会（ contrarian）
            if base_result['action'] in ['buy', 'strong_buy']:
                result['final_multiplier'] = min(3.0, result['final_multiplier'] * 1.3)
                result['status_label'] += " 😰极端恐慌"
        elif market_sentiment == 'extreme_greed':
            # 极度贪婪，降低买入
            result['final_multiplier'] = result['final_multiplier'] * 0.6
            result['status_label'] += " 🤪极端贪婪"
        
        return result
    
    def _apply_volume_confirmation(
        self,
        base_result: Dict,
        volume_data: Optional[Dict],
        today_return: float
    ) -> Dict:
        """
        应用成交量确认
        
        Args:
            base_result: 基础策略结果
            volume_data: 成交量数据
            today_return: 当日收益率
            
        Returns:
            调整后的结果字典
        """
        result = base_result.copy()
        
        if volume_data is None:
            return result
        
        recent_volume = volume_data.get('recent_volume', 0)
        avg_volume = volume_data.get('avg_volume', 1)
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
        
        # 放量下跌 - 可能是真下跌，降低买入倍数
        if today_return < -1.0 and volume_ratio > 1.5:
            result['final_multiplier'] = base_result.get('final_multiplier', base_result['buy_multiplier']) * 0.5
            result['status_label'] += " 📊放量下跌"
            result['operation_suggestion'] += "（放量下跌，谨慎买入）"
            logger.debug(f"成交量调整: 放量下跌，倍数降低50%")
        
        # 缩量下跌 - 可能是洗盘，保持或略微增加买入
        elif today_return < -0.5 and volume_ratio < 0.8:
            result['final_multiplier'] = base_result.get('final_multiplier', base_result['buy_multiplier']) * 1.1
            result['status_label'] += " 📊缩量下跌"
            result['operation_suggestion'] += "（缩量下跌，可能是洗盘）"
        
        # 放量上涨 - 确认上涨趋势
        elif today_return > 1.0 and volume_ratio > 1.3:
            result['status_label'] += " 📊放量上涨"
            result['operation_suggestion'] += "（放量上涨，趋势确认）"
        
        # 缩量上涨 - 可能是假突破
        elif today_return > 1.0 and volume_ratio < 0.7:
            if base_result['action'] == 'buy':
                result['final_multiplier'] = base_result.get('final_multiplier', base_result['buy_multiplier']) * 0.8
                result['status_label'] += " 📊缩量上涨"
                result['operation_suggestion'] += "（缩量上涨，谨慎追高）"
        
        return result
    
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
            adx=0.0,
            adx_trend_strength='unknown',
            volatility=0.0,
            volatility_level='unknown',
            volatility_adjustment=1.0,
            market_beta_adjusted=False,
            market_condition='neutral',
            volume_confirmed=False,
            volume_ratio=1.0,
            risk_adjusted=True,
            final_suggestion=f"⚠️ 止损触发！累计亏损 {stop_loss_result.cumulative_loss:.1%}，建议全部赎回止损。"
        )
    
    def _create_unified_result(
        self,
        base_result: Dict,
        stop_loss_result: StopLossResult,
        trend_result: TrendResult,
        position_adjustment: PositionAdjustment,
        final_multiplier: float,
        base_invest: float = 100.0
    ) -> UnifiedStrategyResult:
        """创建统一结果"""
        # 应用趋势调整
        trend_adjusted_multiplier = final_multiplier * trend_result.multiplier_adjustment
        
        # 生成执行金额描述
        execution_amount = self._get_execution_amount(
            base_result['action'],
            trend_adjusted_multiplier,
            base_result['redeem_amount'],
            base_invest
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
            adx=trend_result.adx,
            adx_trend_strength=trend_result.adx_trend_strength,
            volatility=position_adjustment.volatility,
            volatility_level=position_adjustment.volatility_level.value,
            volatility_adjustment=position_adjustment.adjustment_factor,
            market_beta_adjusted=base_result.get('market_beta_adjusted', False),
            market_condition=base_result.get('market_condition', 'neutral'),
            volume_confirmed=base_result.get('volume_confirmed', False),
            volume_ratio=base_result.get('volume_ratio', 1.0),
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
            adx=0.0,
            adx_trend_strength='unknown',
            volatility=0.0,
            volatility_level='normal',
            volatility_adjustment=1.0,
            market_beta_adjusted=False,
            market_condition='neutral',
            volume_confirmed=False,
            volume_ratio=1.0,
            risk_adjusted=False,
            final_suggestion='数据不足，建议持有观望'
        )
    
    def _get_execution_amount(
        self,
        action: str,
        multiplier: float,
        redeem_amount: float,
        base_invest: float = 100.0
    ) -> str:
        """获取执行金额描述
        
        Args:
            action: 操作类型 ('buy', 'sell', 'hold', 'stop_loss')
            multiplier: 买入倍数
            redeem_amount: 赎回金额
            base_invest: 基准定投金额（默认100元）
            
        Returns:
            str: 明确具体的执行金额描述
        """
        if action == 'stop_loss':
            return "⚠️ 立即止损 - 全部赎回"
        elif action in ['sell', 'weak_sell']:
            # 明确显示赎回金额
            if redeem_amount > 0:
                if 0 < redeem_amount <= 1:  # 如果是比例
                    return f"建议赎回：赎回 {redeem_amount*100:.0f}% 持仓"
                else:  # 如果是具体金额
                    return f"建议赎回：赎回金额 ¥{redeem_amount:.2f}"
            else:
                return "无需赎回"
        elif action == 'hold':
            return "持有观望：无需买入"
        elif action in ['buy', 'strong_buy', 'weak_buy'] and multiplier > 0:
            # 明确显示买入金额
            buy_amount = base_invest * multiplier
            if action == 'strong_buy':
                return f"今日买入：买入金额 ¥{buy_amount:.2f}（强力买入 {multiplier:.1f}×基准定投）"
            elif action == 'weak_buy':
                return f"今日买入：买入金额 ¥{buy_amount:.2f}（轻度买入 {multiplier:.1f}×基准定投）"
            else:
                return f"今日买入：买入金额 ¥{buy_amount:.2f}（标准买入 {multiplier:.1f}×基准定投）"
        else:
            return "持有观望：无需买入"
    
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
            'adx': result.adx,
            'adx_trend_strength': result.adx_trend_strength,
            'volatility': result.volatility,
            'volatility_level': result.volatility_level,
            'volatility_adjustment': result.volatility_adjustment,
            'market_beta_adjusted': result.market_beta_adjusted,
            'market_condition': result.market_condition,
            'volume_confirmed': result.volume_confirmed,
            'volume_ratio': result.volume_ratio,
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


# 模块级函数和类，供测试使用
class StrategyRegistry:
    """策略注册表"""
    
    def __init__(self):
        self._strategies = {}
    
    def register(self, name: str):
        """注册策略装饰器"""
        def decorator(cls):
            self._strategies[name] = cls
            return cls
        return decorator
    
    def get(self, name: str):
        """获取策略类"""
        return self._strategies.get(name)
    
    def __contains__(self, name: str) -> bool:
        return name in self._strategies
    
    def list_strategies(self) -> List[str]:
        """列出所有已注册的策略"""
        return list(self._strategies.keys())


class ExecutionContext:
    """策略执行上下文"""
    
    def __init__(self, initial_capital: float, start_date, end_date):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.start_date = start_date
        self.end_date = end_date
        self.positions = {}
        self.trades = []
    
    def update_capital(self, amount: float):
        """更新资金"""
        self.current_capital += amount
    
    def add_position(self, fund_code: str, shares: float, price: float):
        """添加持仓"""
        self.positions[fund_code] = {
            'shares': shares,
            'price': price,
            'value': shares * price
        }
    
    def get_position(self, fund_code: str) -> Optional[Dict]:
        """获取持仓信息"""
        return self.positions.get(fund_code)


def calculate_portfolio_allocation(signals: Dict[str, float], total_capital: float) -> Dict[str, float]:
    """
    计算投资组合配置
    
    参数:
        signals: 基金代码到信号强度的映射（正数表示买入，负数表示卖出）
        total_capital: 总资金
        
    返回:
        基金代码到配置金额的映射
    """
    if not signals or total_capital <= 0:
        return {}
    
    # 只考虑买入信号
    buy_signals = {k: v for k, v in signals.items() if v > 0}
    
    if not buy_signals:
        return {}
    
    # 计算信号总和
    total_signal = sum(buy_signals.values())
    
    if total_signal == 0:
        return {}
    
    # 按信号强度分配资金
    allocation = {}
    for fund_code, signal in buy_signals.items():
        weight = signal / total_signal
        allocation[fund_code] = total_capital * weight
    
    return allocation


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
