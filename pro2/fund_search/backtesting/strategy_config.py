#!/usr/bin/env python
# coding: utf-8

"""
策略配置管理器
负责加载和管理投资策略配置
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class StrategyConfig:
    """策略配置管理器"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        'buy_multipliers': {
            'strong_buy': 3.0,
            'buy': 1.5,
            'weak_buy': 1.0,
            'hold': 0.0,
            'sell': 0.0,
            'weak_sell': 0.0,
            'stop_loss': 0.0
        },
        'stop_loss': {
            'warning_threshold': -0.10,
            'stop_loss_threshold': -0.15,
            'full_redeem': True,
            'stop_loss_label': "🛑 **止损触发**",
            'warning_label': "⚠️ **亏损警告**",
            'stop_loss_suggestion': "累计亏损超过阈值，建议全部赎回止损",
            'warning_suggestion': "累计亏损接近止损线，请密切关注"
        },
        'volatility': {
            'high_threshold': 0.25,
            'low_threshold': 0.10,
            'high_adjustment': 0.5,
            'low_adjustment': 1.2,
            'normal_adjustment': 1.0,
            'lookback_days': 20
        },
        'trend': {
            'ma_short_period': 5,
            'ma_long_period': 10,
            'uptrend_adjustment': 1.2,
            'downtrend_adjustment': 0.7,
            'sideways_adjustment': 1.0
        },
        'risk_metrics': {
            'var_confidence_levels': [0.95, 0.99],
            'risk_free_rate': 0.03,
            'trading_days_per_year': 252,
            'historical_days': 365
        },
        'default_strategy': {
            'action': 'hold',
            'buy_multiplier': 0.0,
            'redeem_amount': 0,
            'label': "🔴 **未知状态**",
            'description': "不买入，不赎回"
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为 shared/strategy_config.yaml
        """
        if config_path is None:
            # 默认配置文件路径
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / 'shared' / 'strategy_config.yaml'
        
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = yaml.safe_load(f)
                    if loaded_config:
                        self._config = self._merge_with_defaults(loaded_config)
                        logger.info(f"配置文件加载成功: {self.config_path}")
                    else:
                        logger.warning(f"配置文件为空，使用默认配置: {self.config_path}")
                        self._config = self.DEFAULT_CONFIG.copy()
            else:
                logger.warning(f"配置文件不存在，使用默认配置: {self.config_path}")
                self._config = self.DEFAULT_CONFIG.copy()
        except yaml.YAMLError as e:
            logger.error(f"配置文件解析错误，使用默认配置: {e}")
            self._config = self.DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error(f"加载配置文件失败，使用默认配置: {e}")
            self._config = self.DEFAULT_CONFIG.copy()
    
    def _merge_with_defaults(self, loaded_config: Dict) -> Dict:
        """
        将加载的配置与默认配置合并
        
        Args:
            loaded_config: 从文件加载的配置
            
        Returns:
            合并后的配置
        """
        merged = self.DEFAULT_CONFIG.copy()
        
        for key, value in loaded_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # 递归合并字典
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
        
        return merged
    
    def reload_config(self) -> bool:
        """
        运行时重新加载配置
        
        Returns:
            是否重新加载成功
        """
        try:
            self._load_config()
            logger.info("配置重新加载成功")
            return True
        except Exception as e:
            logger.error(f"配置重新加载失败: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置键名，支持点号分隔的嵌套键（如 'stop_loss.warning_threshold'）
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_strategy_thresholds(self) -> Dict:
        """
        获取策略阈值配置
        
        Returns:
            策略阈值配置字典
        """
        return self._config.get('strategies', {})
    
    def get_stop_loss_config(self) -> Dict:
        """
        获取止损配置
        
        Returns:
            止损配置字典
        """
        return self._config.get('stop_loss', self.DEFAULT_CONFIG['stop_loss'])
    
    def get_volatility_config(self) -> Dict:
        """
        获取波动率配置
        
        Returns:
            波动率配置字典
        """
        return self._config.get('volatility', self.DEFAULT_CONFIG['volatility'])
    
    def get_trend_config(self) -> Dict:
        """
        获取趋势配置
        
        Returns:
            趋势配置字典
        """
        return self._config.get('trend', self.DEFAULT_CONFIG['trend'])
    
    def get_risk_metrics_config(self) -> Dict:
        """
        获取风险指标配置
        
        Returns:
            风险指标配置字典
        """
        return self._config.get('risk_metrics', self.DEFAULT_CONFIG['risk_metrics'])
    
    def get_buy_multipliers(self) -> Dict[str, float]:
        """
        获取买入倍数配置
        
        Returns:
            买入倍数配置字典
        """
        return self._config.get('buy_multipliers', self.DEFAULT_CONFIG['buy_multipliers'])
    
    def get_default_strategy(self) -> Dict:
        """
        获取默认策略配置
        
        Returns:
            默认策略配置字典
        """
        return self._config.get('default_strategy', self.DEFAULT_CONFIG['default_strategy'])
    
    def validate_config(self) -> tuple[bool, list[str]]:
        """
        验证配置有效性
        
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        # 验证止损配置
        stop_loss = self.get_stop_loss_config()
        if stop_loss.get('warning_threshold', 0) >= 0:
            errors.append("止损警告阈值应为负数")
        if stop_loss.get('stop_loss_threshold', 0) >= 0:
            errors.append("止损阈值应为负数")
        if stop_loss.get('warning_threshold', 0) < stop_loss.get('stop_loss_threshold', 0):
            errors.append("止损警告阈值应大于止损阈值")
        
        # 验证波动率配置
        volatility = self.get_volatility_config()
        if volatility.get('high_threshold', 0) <= volatility.get('low_threshold', 0):
            errors.append("高波动阈值应大于低波动阈值")
        if volatility.get('high_adjustment', 0) <= 0:
            errors.append("高波动调整系数应为正数")
        if volatility.get('low_adjustment', 0) <= 0:
            errors.append("低波动调整系数应为正数")
        
        # 验证趋势配置
        trend = self.get_trend_config()
        if trend.get('ma_short_period', 0) >= trend.get('ma_long_period', 0):
            errors.append("短期均线周期应小于长期均线周期")
        
        return len(errors) == 0, errors
    
    @property
    def config(self) -> Dict:
        """获取完整配置"""
        return self._config.copy()


# 全局配置实例
_global_config: Optional[StrategyConfig] = None


def get_strategy_config(config_path: Optional[str] = None) -> StrategyConfig:
    """
    获取全局策略配置实例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        StrategyConfig 实例
    """
    global _global_config
    
    if _global_config is None or config_path is not None:
        _global_config = StrategyConfig(config_path)
    
    return _global_config


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    config = StrategyConfig()
    
    print("=== 配置验证 ===")
    is_valid, errors = config.validate_config()
    print(f"配置有效: {is_valid}")
    if errors:
        print(f"错误: {errors}")
    
    print("\n=== 止损配置 ===")
    print(config.get_stop_loss_config())
    
    print("\n=== 波动率配置 ===")
    print(config.get_volatility_config())
    
    print("\n=== 趋势配置 ===")
    print(config.get_trend_config())
    
    print("\n=== 嵌套键访问 ===")
    print(f"止损阈值: {config.get('stop_loss.stop_loss_threshold')}")
    print(f"高波动调整: {config.get('volatility.high_adjustment')}")
