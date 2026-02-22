#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
机器学习预测策略模块
ML Prediction Strategy Module

基于多种机器学习模型的价格预测策略，包括：
- 随机森林 (RandomForest)
- XGBoost
- LSTM（可选）
- 线性回归

支持多模型集成投票机制和动态模型切换。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import logging
import warnings
from collections import deque

from .advanced_strategies import BaseStrategy, StrategySignal

logger = logging.getLogger(__name__)

# 尝试导入机器学习库
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression, Ridge, Lasso
    from sklearn.preprocessing import StandardScaler, MinMaxScaler
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    warnings.warn("scikit-learn 未安装，将使用统计预测方法")

try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    warnings.warn("XGBoost 未安装，将跳过XGBoost模型")

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    warnings.warn("TensorFlow 未安装，将跳过LSTM模型")


class ModelType(Enum):
    """模型类型枚举"""
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    LSTM = "lstm"
    LINEAR_REGRESSION = "linear_regression"
    RIDGE = "ridge"
    LASSO = "lasso"
    STATISTICAL = "statistical"  # 降级方案


class MarketRegime(Enum):
    """市场状态枚举"""
    TRENDING_UP = "trending_up"      # 上涨趋势
    TRENDING_DOWN = "trending_down"  # 下跌趋势
    RANGING = "ranging"              # 震荡市场
    HIGH_VOLATILITY = "high_volatility"  # 高波动
    LOW_VOLATILITY = "low_volatility"    # 低波动


@dataclass
class PredictionResult:
    """
    预测结果数据类
    
    Attributes:
        predicted_return: 预测的收益率
        confidence: 置信度 (0-1)
        model_used: 使用的模型名称
        features_importance: 特征重要性字典
        prediction_time: 预测时间戳
        market_regime: 当前市场状态
        raw_predictions: 各模型的原始预测值
    """
    predicted_return: float
    confidence: float
    model_used: str
    features_importance: Dict[str, float] = field(default_factory=dict)
    prediction_time: Optional[pd.Timestamp] = None
    market_regime: Optional[MarketRegime] = None
    raw_predictions: Dict[str, float] = field(default_factory=dict)
    
    def is_reliable(self, min_confidence: float = 0.6) -> bool:
        """检查预测是否可靠"""
        return self.confidence >= min_confidence
    
    def get_direction(self) -> str:
        """获取预测方向"""
        if self.predicted_return > 0.01:
            return "up"
        elif self.predicted_return < -0.01:
            return "down"
        return "neutral"


@dataclass
class ModelMetrics:
    """
    模型性能指标
    
    Attributes:
        model_name: 模型名称
        rmse: 均方根误差
        mae: 平均绝对误差
        r2_score: R²分数
        mape: 平均绝对百分比误差
        sharpe_ratio: 策略夏普比率
        max_drawdown: 最大回撤
        hit_rate: 命中率
        training_samples: 训练样本数
        last_trained: 最后训练时间
    """
    model_name: str
    rmse: float = 0.0
    mae: float = 0.0
    r2_score: float = 0.0
    mape: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    hit_rate: float = 0.0
    training_samples: int = 0
    last_trained: Optional[pd.Timestamp] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'model_name': self.model_name,
            'rmse': self.rmse,
            'mae': self.mae,
            'r2_score': self.r2_score,
            'mape': self.mape,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'hit_rate': self.hit_rate,
            'training_samples': self.training_samples,
            'last_trained': self.last_trained.isoformat() if self.last_trained else None
        }


class BaseMLModel(ABC):
    """机器学习模型基类"""
    
    def __init__(self, name: str, model_type: ModelType):
        self.name = name
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        self.metrics = ModelMetrics(model_name=name)
        self.is_trained = False
        
    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> ModelMetrics:
        """训练模型"""
        pass
    
    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        pass
    
    def preprocess_features(self, X: np.ndarray, fit: bool = False) -> np.ndarray:
        """预处理特征"""
        if self.scaler is not None:
            # 确保输入是二维数组
            if len(X.shape) == 1:
                X = X.reshape(1, -1)
            if fit:
                return self.scaler.fit_transform(X)
            # 预测时，如果特征数量不匹配，需要处理
            try:
                return self.scaler.transform(X)
            except ValueError as e:
                # 特征数量不匹配，返回原始特征
                logger.warning(f"特征标准化失败: {e}，使用原始特征")
                return X
        return X
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> ModelMetrics:
        """评估模型性能"""
        if not self.is_trained:
            logger.warning(f"模型 {self.name} 尚未训练")
            return self.metrics
        
        predictions = self.predict(X_test)
        
        self.metrics.rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))
        self.metrics.mae = float(mean_absolute_error(y_test, predictions))
        self.metrics.r2_score = float(r2_score(y_test, predictions))
        self.metrics.mape = float(np.mean(np.abs((y_test - predictions) / (y_test + 1e-8))) * 100)
        
        # 计算命中率
        actual_direction = np.sign(y_test)
        pred_direction = np.sign(predictions)
        self.metrics.hit_rate = float(np.mean(actual_direction == pred_direction))
        
        return self.metrics


class RandomForestModel(BaseMLModel):
    """随机森林模型"""
    
    def __init__(self, n_estimators: int = 100, max_depth: int = 10, **kwargs):
        super().__init__("RandomForest", ModelType.RANDOM_FOREST)
        if SKLEARN_AVAILABLE:
            self.model = RandomForestRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                random_state=42,
                n_jobs=-1,
                **kwargs
            )
    
    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> ModelMetrics:
        """训练随机森林模型"""
        if not SKLEARN_AVAILABLE or self.model is None:
            logger.error("scikit-learn 未安装")
            return self.metrics
        
        X_scaled = self.preprocess_features(X, fit=True)
        self.model.fit(X_scaled, y)
        self.is_trained = True
        self.metrics.training_samples = len(X)
        self.metrics.last_trained = pd.Timestamp.now()
        
        return self.metrics
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        if not self.is_trained:
            raise ValueError("模型尚未训练")
        # 确保输入是二维数组
        if len(X.shape) == 1:
            X = X.reshape(1, -1)
        X_scaled = self.preprocess_features(X)
        return self.model.predict(X_scaled)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """获取特征重要性"""
        if not self.is_trained or not hasattr(self.model, 'feature_importances_'):
            return {}
        
        # 使用通用特征名
        feature_names = [f"feature_{i}" for i in range(len(self.model.feature_importances_))]
        return dict(zip(feature_names, self.model.feature_importances_.tolist()))


class XGBoostModel(BaseMLModel):
    """XGBoost模型"""
    
    def __init__(self, n_estimators: int = 100, max_depth: int = 6, learning_rate: float = 0.1, **kwargs):
        super().__init__("XGBoost", ModelType.XGBOOST)
        if XGBOOST_AVAILABLE:
            self.model = XGBRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=learning_rate,
                random_state=42,
                n_jobs=-1,
                **kwargs
            )
    
    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> ModelMetrics:
        """训练XGBoost模型"""
        if not XGBOOST_AVAILABLE or self.model is None:
            logger.error("XGBoost 未安装")
            return self.metrics
        
        X_scaled = self.preprocess_features(X, fit=True)
        
        # 使用早停
        X_train, X_val, y_train, y_val = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        
        self.is_trained = True
        self.metrics.training_samples = len(X)
        self.metrics.last_trained = pd.Timestamp.now()
        
        return self.metrics
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        if not self.is_trained:
            raise ValueError("模型尚未训练")
        # 确保输入是二维数组
        if len(X.shape) == 1:
            X = X.reshape(1, -1)
        X_scaled = self.preprocess_features(X)
        return self.model.predict(X_scaled)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """获取特征重要性"""
        if not self.is_trained or not hasattr(self.model, 'feature_importances_'):
            return {}
        
        feature_names = [f"feature_{i}" for i in range(len(self.model.feature_importances_))]
        return dict(zip(feature_names, self.model.feature_importances_.tolist()))


class LinearRegressionModel(BaseMLModel):
    """线性回归模型"""
    
    def __init__(self, model_type: ModelType = ModelType.LINEAR_REGRESSION, alpha: float = 1.0):
        name = "LinearRegression" if model_type == ModelType.LINEAR_REGRESSION else \
               "Ridge" if model_type == ModelType.RIDGE else "Lasso"
        super().__init__(name, model_type)
        
        if SKLEARN_AVAILABLE:
            if model_type == ModelType.RIDGE:
                self.model = Ridge(alpha=alpha, random_state=42)
            elif model_type == ModelType.LASSO:
                self.model = Lasso(alpha=alpha, random_state=42)
            else:
                self.model = LinearRegression()
    
    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> ModelMetrics:
        """训练线性回归模型"""
        if not SKLEARN_AVAILABLE or self.model is None:
            logger.error("scikit-learn 未安装")
            return self.metrics
        
        X_scaled = self.preprocess_features(X, fit=True)
        self.model.fit(X_scaled, y)
        self.is_trained = True
        self.metrics.training_samples = len(X)
        self.metrics.last_trained = pd.Timestamp.now()
        
        return self.metrics
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        if not self.is_trained:
            raise ValueError("模型尚未训练")
        # 确保输入是二维数组
        if len(X.shape) == 1:
            X = X.reshape(1, -1)
        X_scaled = self.preprocess_features(X)
        return self.model.predict(X_scaled)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """获取特征重要性（系数）"""
        if not self.is_trained or not hasattr(self.model, 'coef_'):
            return {}
        
        # 处理多维系数（如多输出回归）
        coef = self.model.coef_
        if len(coef.shape) > 1:
            coef = coef.flatten()
        
        feature_names = [f"feature_{i}" for i in range(len(coef))]
        # 归一化系数
        coef_abs = np.abs(coef)
        coef_normalized = coef_abs / (coef_abs.sum() + 1e-8)
        return {name: float(val) for name, val in zip(feature_names, coef_normalized)}


class LSTMModel(BaseMLModel):
    """LSTM模型（深度学习）"""
    
    def __init__(self, sequence_length: int = 20, units: List[int] = None, 
                 dropout_rate: float = 0.2, epochs: int = 50, batch_size: int = 32):
        super().__init__("LSTM", ModelType.LSTM)
        self.sequence_length = sequence_length
        self.units = units or [64, 32]
        self.dropout_rate = dropout_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.model = None
        
        if TF_AVAILABLE:
            self._build_model()
    
    def _build_model(self):
        """构建LSTM网络"""
        if not TF_AVAILABLE:
            return
        
        model = Sequential()
        
        for i, units in enumerate(self.units):
            return_seq = i < len(self.units) - 1
            if i == 0:
                model.add(LSTM(units, return_sequences=return_seq, 
                              input_shape=(self.sequence_length, 1)))
            else:
                model.add(LSTM(units, return_sequences=return_seq))
            model.add(BatchNormalization())
            model.add(Dropout(self.dropout_rate))
        
        model.add(Dense(16, activation='relu'))
        model.add(Dense(1))
        
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
        self.model = model
    
    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> ModelMetrics:
        """训练LSTM模型"""
        if not TF_AVAILABLE or self.model is None:
            logger.error("TensorFlow 未安装")
            return self.metrics
        
        # 创建序列数据
        X_seq, y_seq = self._create_sequences(X, y)
        
        if len(X_seq) < 100:
            logger.warning("LSTM需要更多数据训练")
            return self.metrics
        
        # 分割训练集和验证集
        split_idx = int(len(X_seq) * 0.8)
        X_train, X_val = X_seq[:split_idx], X_seq[split_idx:]
        y_train, y_val = y_seq[:split_idx], y_seq[split_idx:]
        
        # 早停
        early_stop = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
        
        self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=self.epochs,
            batch_size=self.batch_size,
            callbacks=[early_stop],
            verbose=0
        )
        
        self.is_trained = True
        self.metrics.training_samples = len(X)
        self.metrics.last_trained = pd.Timestamp.now()
        
        return self.metrics
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        if not self.is_trained:
            raise ValueError("模型尚未训练")
        
        # 创建序列并预测
        X_seq = self._create_sequences_for_prediction(X)
        predictions = self.model.predict(X_seq, verbose=0)
        
        # 填充前面的缺失值
        padding = np.full(self.sequence_length - 1, predictions[0])
        return np.concatenate([padding, predictions.flatten()])
    
    def _create_sequences(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """创建序列数据"""
        X_seq, y_seq = [], []
        for i in range(len(X) - self.sequence_length):
            X_seq.append(X[i:i + self.sequence_length])
            y_seq.append(y[i + self.sequence_length])
        return np.array(X_seq), np.array(y_seq)
    
    def _create_sequences_for_prediction(self, X: np.ndarray) -> np.ndarray:
        """为预测创建序列"""
        X_seq = []
        for i in range(len(X) - self.sequence_length + 1):
            X_seq.append(X[i:i + self.sequence_length])
        return np.array(X_seq)


class StatisticalModel(BaseMLModel):
    """
    统计预测模型（降级方案）
    当机器学习库不可用时使用
    """
    
    def __init__(self):
        super().__init__("Statistical", ModelType.STATISTICAL)
        self.mean_return = 0.0
        self.volatility = 0.0
        self.trend_coeff = 0.0
        self.recent_returns = deque(maxlen=20)
    
    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> ModelMetrics:
        """训练统计模型（简单参数估计）"""
        self.mean_return = np.mean(y)
        self.volatility = np.std(y)
        
        # 简单趋势估计（使用最后20个点做线性回归）
        if len(y) >= 20:
            x = np.arange(len(y))
            self.trend_coeff = np.polyfit(x[-20:], y[-20:], 1)[0]
        
        self.is_trained = True
        self.metrics.training_samples = len(X)
        self.metrics.last_trained = pd.Timestamp.now()
        
        return self.metrics
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """基于统计方法预测"""
        if not self.is_trained:
            raise ValueError("模型尚未训练")
        
        # 结合均值、趋势和最新特征
        n_samples = len(X) if len(X.shape) > 1 else 1
        predictions = np.full(n_samples, self.mean_return)
        
        # 如果有特征数据，使用最后一个特征调整预测
        if len(X.shape) > 1 and X.shape[1] > 0:
            latest_feature = X[:, -1] if len(X.shape) > 1 else X[-1]
            predictions += latest_feature * 0.5  # 简单加权
        
        return predictions


class FeatureEngineer:
    """特征工程类"""
    
    def __init__(self):
        self.feature_names: List[str] = []
        
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        创建所有特征
        
        Args:
            df: 包含 'nav' 或 '单位净值' 列的DataFrame
            
        Returns:
            包含所有特征的DataFrame
        """
        df = df.copy()
        
        # 获取净值列
        if 'nav' in df.columns:
            nav = df['nav']
        elif '单位净值' in df.columns:
            nav = df['单位净值']
        elif 'close' in df.columns:
            nav = df['close']
        else:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                nav = df[numeric_cols[0]]
            else:
                raise ValueError("找不到净值列")
        
        # 1. 技术指标
        df = self._add_moving_averages(df, nav)
        df = self._add_rsi(df, nav)
        df = self._add_macd(df, nav)
        df = self._add_bollinger_bands(df, nav)
        df = self._add_atr(df, nav)
        
        # 2. 波动率特征
        df = self._add_volatility_features(df, nav)
        
        # 3. 趋势特征
        df = self._add_trend_features(df, nav)
        
        # 4. 动量特征
        df = self._add_momentum_features(df, nav)
        
        # 5. 量价特征（如有成交量数据）
        if 'volume' in df.columns or '成交量' in df.columns:
            df = self._add_volume_features(df)
        
        # 6. 收益率特征
        df = self._add_return_features(df, nav)
        
        # 更新特征名列表
        self.feature_names = [col for col in df.columns if col not in 
                             ['nav', '单位净值', 'close', 'date', 'datetime', 'volume', '成交量']]
        
        return df
    
    def _add_moving_averages(self, df: pd.DataFrame, nav: pd.Series) -> pd.DataFrame:
        """添加移动平均线"""
        # 简单移动平均
        for window in [5, 10, 20, 60]:
            df[f'ma_{window}'] = nav.rolling(window=window).mean()
            df[f'ma_{window}_ratio'] = nav / df[f'ma_{window}'] - 1
        
        # 指数移动平均
        df['ema_12'] = nav.ewm(span=12).mean()
        df['ema_26'] = nav.ewm(span=26).mean()
        
        # 均线距离
        df['ma_distance'] = df['ma_20'] - df['ma_60']
        df['ma_distance_ratio'] = df['ma_distance'] / df['ma_60']
        
        return df
    
    def _add_rsi(self, df: pd.DataFrame, nav: pd.Series, period: int = 14) -> pd.DataFrame:
        """添加RSI指标"""
        delta = nav.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi_normalized'] = df['rsi'] / 100  # 归一化到0-1
        return df
    
    def _add_macd(self, df: pd.DataFrame, nav: pd.Series) -> pd.DataFrame:
        """添加MACD指标"""
        ema_12 = nav.ewm(span=12).mean()
        ema_26 = nav.ewm(span=26).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # MACD与价格的比率
        df['macd_ratio'] = df['macd'] / nav
        
        return df
    
    def _add_bollinger_bands(self, df: pd.DataFrame, nav: pd.Series, window: int = 20) -> pd.DataFrame:
        """添加布林带"""
        sma = nav.rolling(window=window).mean()
        std = nav.rolling(window=window).std()
        
        df['bb_upper'] = sma + 2 * std
        df['bb_lower'] = sma - 2 * std
        df['bb_middle'] = sma
        
        # 布林带位置 (%B)
        df['bb_position'] = (nav - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-10)
        
        # 布林带宽度
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / sma
        
        return df
    
    def _add_atr(self, df: pd.DataFrame, nav: pd.Series, period: int = 14) -> pd.DataFrame:
        """添加ATR（平均真实波幅）"""
        high = nav.rolling(window=2).max()
        low = nav.rolling(window=2).min()
        prev_close = nav.shift(1)
        
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=period).mean()
        df['atr_ratio'] = df['atr'] / nav
        
        return df
    
    def _add_volatility_features(self, df: pd.DataFrame, nav: pd.Series) -> pd.DataFrame:
        """添加波动率特征"""
        returns = nav.pct_change()
        
        # 历史波动率
        for window in [10, 20, 60]:
            df[f'volatility_{window}d'] = returns.rolling(window=window).std() * np.sqrt(252)
        
        # 波动率变化率
        df['volatility_change'] = df['volatility_20d'].diff()
        df['volatility_change_ratio'] = df['volatility_change'] / (df['volatility_20d'].shift(1) + 1e-10)
        
        # 波动率趋势
        df['volatility_trend'] = df['volatility_10d'] - df['volatility_60d']
        
        # 价格波动范围
        df['price_range'] = (nav.rolling(window=20).max() - nav.rolling(window=20).min()) / nav
        
        return df
    
    def _add_trend_features(self, df: pd.DataFrame, nav: pd.Series) -> pd.DataFrame:
        """添加趋势特征"""
        # 趋势强度 (ADX近似)
        df['trend_strength'] = abs(nav.rolling(window=20).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=False
        ))
        
        # 趋势方向
        df['trend_direction'] = np.sign(nav.diff(20))
        
        # 长期趋势
        df['long_term_trend'] = (nav / nav.rolling(window=60).mean() - 1)
        
        # 短期趋势
        df['short_term_trend'] = (nav / nav.rolling(window=5).mean() - 1)
        
        # 趋势一致性
        df['trend_consistency'] = (
            np.sign(nav.diff(5)) == np.sign(nav.diff(20))
        ).astype(float)
        
        return df
    
    def _add_momentum_features(self, df: pd.DataFrame, nav: pd.Series) -> pd.DataFrame:
        """添加动量特征"""
        # 不同周期的动量
        for period in [5, 10, 20, 60]:
            df[f'momentum_{period}d'] = nav.pct_change(periods=period)
        
        # 动量变化
        df['momentum_change'] = df['momentum_10d'] - df['momentum_10d'].shift(5)
        
        # 动量加速度
        df['momentum_acceleration'] = df['momentum_5d'].diff()
        
        return df
    
    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加量价特征"""
        vol_col = 'volume' if 'volume' in df.columns else '成交量'
        volume = df[vol_col]
        
        # 成交量移动平均
        df['volume_ma_20'] = volume.rolling(window=20).mean()
        df['volume_ratio'] = volume / (df['volume_ma_20'] + 1e-10)
        
        # 成交量趋势
        df['volume_trend'] = np.sign(volume.diff(5))
        
        # 价量背离（简化版）
        if 'momentum_5d' in df.columns:
            df['price_volume_divergence'] = np.sign(df['momentum_5d']) != np.sign(df['volume_trend'])
        
        return df
    
    def _add_return_features(self, df: pd.DataFrame, nav: pd.Series) -> pd.DataFrame:
        """添加收益率特征"""
        returns = nav.pct_change()
        
        # 滞后收益率
        for lag in [1, 2, 3, 5]:
            df[f'return_lag_{lag}'] = returns.shift(lag)
        
        # 累计收益率
        df['cumulative_return_5d'] = (1 + returns).rolling(window=5).apply(np.prod) - 1
        df['cumulative_return_20d'] = (1 + returns).rolling(window=20).apply(np.prod) - 1
        
        # 收益率偏度（不对称性）
        df['return_skew'] = returns.rolling(window=20).skew()
        
        # 收益率峰度
        df['return_kurt'] = returns.rolling(window=20).kurt()
        
        # 目标变量：未来收益率
        df['target_return_1d'] = returns.shift(-1)
        df['target_return_5d'] = nav.pct_change(5).shift(-5)
        
        return df
    
    def get_feature_names(self) -> List[str]:
        """获取特征名称列表"""
        return self.feature_names


class ModelEnsemble:
    """模型集成类"""
    
    def __init__(self, models: Optional[List[BaseMLModel]] = None, 
                 voting_weights: Optional[Dict[str, float]] = None):
        self.models = models or []
        self.voting_weights = voting_weights or {}
        self.model_metrics: Dict[str, ModelMetrics] = {}
        
    def add_model(self, model: BaseMLModel, weight: float = 1.0):
        """添加模型到集成"""
        self.models.append(model)
        self.voting_weights[model.name] = weight
    
    def predict(self, X: np.ndarray) -> Tuple[float, float]:
        """
        集成预测
        
        Returns:
            (加权平均预测, 置信度)
        """
        if not self.models:
            return 0.0, 0.0
        
        predictions = []
        weights = []
        
        for model in self.models:
            if model.is_trained:
                try:
                    pred_raw = model.predict(X)
                    # 确保pred是标量
                    if isinstance(pred_raw, np.ndarray):
                        pred = float(pred_raw.flatten()[0])
                    else:
                        pred = float(pred_raw)
                    predictions.append(pred)
                    
                    # 根据模型性能调整权重
                    metric = model.metrics
                    if metric.rmse > 0:
                        # RMSE越小，权重越大
                        adjusted_weight = self.voting_weights.get(model.name, 1.0) / (metric.rmse + 0.01)
                    else:
                        adjusted_weight = self.voting_weights.get(model.name, 1.0)
                    weights.append(adjusted_weight)
                except Exception as e:
                    logger.warning(f"模型 {model.name} 预测失败: {e}")
        
        if not predictions:
            return 0.0, 0.0
        
        # 加权平均
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0, 0.0
        
        weighted_pred = sum(p * w for p, w in zip(predictions, weights)) / total_weight
        
        # 计算置信度（基于预测一致性）
        pred_std = np.std(predictions) if len(predictions) > 1 else 0.5
        confidence = 1 - min(pred_std * 10, 1.0)  # 标准差越小，置信度越高
        
        return float(weighted_pred), float(confidence)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """获取集成特征重要性"""
        combined_importance = {}
        total_weight = 0
        
        for model in self.models:
            if model.is_trained and hasattr(model, 'get_feature_importance'):
                importance = model.get_feature_importance()
                weight = self.voting_weights.get(model.name, 1.0)
                
                for feature, imp in importance.items():
                    combined_importance[feature] = combined_importance.get(feature, 0) + imp * weight
                total_weight += weight
        
        # 归一化
        if total_weight > 0:
            for feature in combined_importance:
                combined_importance[feature] /= total_weight
        
        return combined_importance


class MarketRegimeDetector:
    """市场状态检测器"""
    
    def __init__(self, lookback_period: int = 60):
        self.lookback_period = lookback_period
    
    def detect(self, df: pd.DataFrame) -> MarketRegime:
        """检测当前市场状态"""
        if len(df) < self.lookback_period:
            return MarketRegime.RANGING
        
        nav = df['nav'] if 'nav' in df.columns else df['单位净值']
        returns = nav.pct_change().dropna()
        
        if len(returns) < self.lookback_period:
            return MarketRegime.RANGING
        
        recent_returns = returns.iloc[-self.lookback_period:]
        
        # 计算指标
        volatility = recent_returns.std() * np.sqrt(252)
        trend = (nav.iloc[-1] / nav.iloc[-self.lookback_period] - 1)
        
        # 均线关系
        if 'ma_20' in df.columns and 'ma_60' in df.columns:
            ma_trend = (df['ma_20'].iloc[-1] / df['ma_60'].iloc[-1] - 1)
        else:
            ma_trend = 0
        
        # 判断市场状态
        if volatility > 0.25:
            if trend > 0.05 or ma_trend > 0.02:
                return MarketRegime.TRENDING_UP
            elif trend < -0.05 or ma_trend < -0.02:
                return MarketRegime.TRENDING_DOWN
            return MarketRegime.HIGH_VOLATILITY
        elif volatility < 0.10:
            return MarketRegime.LOW_VOLATILITY
        else:
            if trend > 0.03 and ma_trend > 0.01:
                return MarketRegime.TRENDING_UP
            elif trend < -0.03 and ma_trend < -0.01:
                return MarketRegime.TRENDING_DOWN
            return MarketRegime.RANGING
    
    def get_best_model_type(self, regime: MarketRegime) -> ModelType:
        """根据市场状态推荐最佳模型类型"""
        regime_model_map = {
            MarketRegime.TRENDING_UP: ModelType.XGBOOST,
            MarketRegime.TRENDING_DOWN: ModelType.RANDOM_FOREST,
            MarketRegime.RANGING: ModelType.RIDGE,
            MarketRegime.HIGH_VOLATILITY: ModelType.RANDOM_FOREST,
            MarketRegime.LOW_VOLATILITY: ModelType.LINEAR_REGRESSION
        }
        return regime_model_map.get(regime, ModelType.RANDOM_FOREST)


class MLPredictionStrategy(BaseStrategy):
    """
    机器学习预测策略
    
    基于多种机器学习模型的价格预测策略，支持多模型集成投票机制和
    根据市场状态动态选择模型。
    
    Attributes:
        prediction_horizon: 预测周期（天数）
        confidence_threshold: 置信度阈值
        min_training_samples: 最小训练样本数
        retrain_frequency: 重新训练频率（交易日数）
    
    Example:
        >>> strategy = MLPredictionStrategy(prediction_horizon=5)
        >>> strategy.train_model(historical_data)
        >>> signal = strategy.generate_signal(df, current_index=-1)
    """
    
    def __init__(self, 
                 prediction_horizon: int = 5,
                 confidence_threshold: float = 0.6,
                 min_training_samples: int = 100,
                 retrain_frequency: int = 20,
                 enable_ensemble: bool = True,
                 enable_regime_switching: bool = True):
        """
        初始化ML预测策略
        
        Args:
            prediction_horizon: 预测周期（默认5天）
            confidence_threshold: 置信度阈值（默认0.6）
            min_training_samples: 最小训练样本数（默认100）
            retrain_frequency: 重新训练频率（默认20个交易日）
            enable_ensemble: 是否启用模型集成
            enable_regime_switching: 是否启用市场状态切换
        """
        super().__init__(
            name="机器学习预测策略",
            description=f"基于多种ML模型预测{prediction_horizon}天收益率的策略"
        )
        
        self.prediction_horizon = prediction_horizon
        self.confidence_threshold = confidence_threshold
        self.min_training_samples = min_training_samples
        self.retrain_frequency = retrain_frequency
        self.enable_ensemble = enable_ensemble
        self.enable_regime_switching = enable_regime_switching
        
        # 初始化组件
        self.feature_engineer = FeatureEngineer()
        self.regime_detector = MarketRegimeDetector()
        self.models: Dict[str, BaseMLModel] = {}
        self.ensemble = ModelEnsemble()
        self.last_train_index = 0
        self.current_regime = MarketRegime.RANGING
        
        # 初始化模型
        self._init_models()
        
        # 历史预测记录
        self.prediction_history: deque = deque(maxlen=100)
        
    def _init_models(self):
        """初始化所有可用模型"""
        # 随机森林
        if SKLEARN_AVAILABLE:
            self.models['random_forest'] = RandomForestModel(n_estimators=100)
            self.ensemble.add_model(self.models['random_forest'], weight=1.0)
        
        # XGBoost
        if XGBOOST_AVAILABLE:
            self.models['xgboost'] = XGBoostModel(n_estimators=100)
            self.ensemble.add_model(self.models['xgboost'], weight=1.2)
        
        # 线性模型
        if SKLEARN_AVAILABLE:
            self.models['ridge'] = LinearRegressionModel(ModelType.RIDGE, alpha=0.1)
            self.ensemble.add_model(self.models['ridge'], weight=0.8)
            
            self.models['lasso'] = LinearRegressionModel(ModelType.LASSO, alpha=0.01)
            self.ensemble.add_model(self.models['lasso'], weight=0.6)
        
        # LSTM
        if TF_AVAILABLE:
            self.models['lstm'] = LSTMModel(sequence_length=20)
            # LSTM权重较低，因为需要更多数据
            self.ensemble.add_model(self.models['lstm'], weight=0.7)
        
        # 统计模型（降级方案）
        if not SKLEARN_AVAILABLE and not XGBOOST_AVAILABLE:
            self.models['statistical'] = StatisticalModel()
            self.ensemble.add_model(self.models['statistical'], weight=1.0)
    
    def train_model(self, historical_data: pd.DataFrame, force: bool = False) -> Dict[str, ModelMetrics]:
        """
        训练模型
        
        Args:
            historical_data: 历史数据DataFrame
            force: 是否强制重新训练
            
        Returns:
            各模型的性能指标字典
        """
        if len(historical_data) < self.min_training_samples:
            logger.warning(f"数据不足，需要至少{self.min_training_samples}条数据")
            return {}
        
        # 特征工程
        df_features = self.feature_engineer.create_features(historical_data)
        
        # 获取特征和目标
        feature_cols = self.feature_engineer.get_feature_names()
        target_col = f'target_return_{self.prediction_horizon}d' if f'target_return_{self.prediction_horizon}d' in df_features.columns else 'target_return_5d'
        
        # 删除缺失值
        df_clean = df_features[feature_cols + [target_col]].dropna()
        
        if len(df_clean) < self.min_training_samples:
            logger.warning("有效训练数据不足")
            return {}
        
        X = df_clean[feature_cols].values
        y = df_clean[target_col].values
        
        # 填充任何剩余的NaN
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
        
        # 保存训练时的特征列数
        self._n_features = X.shape[1]
        
        # 分割训练集和测试集
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # 训练各模型
        metrics = {}
        for name, model in self.models.items():
            try:
                logger.info(f"训练模型: {name}")
                model.train(X_train, y_train)
                
                if len(X_test) > 0:
                    metric = model.evaluate(X_test, y_test)
                    metrics[name] = metric
                    logger.info(f"{name} - RMSE: {metric.rmse:.4f}, R²: {metric.r2_score:.4f}, 命中率: {metric.hit_rate:.2%}")
            except Exception as e:
                logger.error(f"训练模型 {name} 失败: {e}")
        
        return metrics
    
    def predict_return(self, features: pd.DataFrame) -> PredictionResult:
        """
        预测收益率
        
        Args:
            features: 特征DataFrame
            
        Returns:
            PredictionResult: 预测结果
        """
        if not self.models:
            return PredictionResult(0.0, 0.0, "none")
        
        # 获取特征
        feature_cols = self.feature_engineer.get_feature_names()
        available_cols = [col for col in feature_cols if col in features.columns]
        
        if not available_cols:
            logger.warning("没有可用的特征")
            return PredictionResult(0.0, 0.0, "none")
        
        X = features[available_cols].values
        # 填充NaN
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        # 确保特征维度与训练时一致
        if hasattr(self, '_n_features') and X.shape[1] != self._n_features:
            logger.warning(f"特征维度不匹配: 训练时{self._n_features}, 当前{X.shape[1]}")
            # 填充或截断特征
            if X.shape[1] < self._n_features:
                padding = np.zeros((X.shape[0], self._n_features - X.shape[1]))
                X = np.hstack([X, padding])
            else:
                X = X[:, :self._n_features]
        
        # 集成预测
        prediction, confidence = self.ensemble.predict(X)
        
        # 收集各模型的预测
        raw_predictions = {}
        for name, model in self.models.items():
            if model.is_trained:
                try:
                    pred = model.predict(X[-1:])[0]
                    raw_predictions[name] = float(pred) if np.isscalar(pred) else float(pred[0])
                except:
                    pass
        
        # 获取特征重要性
        feature_importance = self.ensemble.get_feature_importance()
        
        # 根据市场状态调整置信度
        if self.enable_regime_switching:
            if self.current_regime in [MarketRegime.HIGH_VOLATILITY]:
                confidence *= 0.8  # 高波动市场降低置信度
        
        return PredictionResult(
            predicted_return=float(prediction),
            confidence=float(confidence),
            model_used="ensemble",
            features_importance=feature_importance,
            prediction_time=pd.Timestamp.now(),
            market_regime=self.current_regime,
            raw_predictions=raw_predictions
        )
    
    def generate_signal(self, 
                       df: pd.DataFrame, 
                       current_index: int,
                       **kwargs) -> StrategySignal:
        """
        生成交易信号
        
        Args:
            df: 历史数据DataFrame
            current_index: 当前交易日索引
            
        Returns:
            StrategySignal: 交易信号
        """
        # 检查是否需要重新训练
        if current_index - self.last_train_index >= self.retrain_frequency:
            if current_index >= self.min_training_samples:
                self.train_model(df.iloc[:current_index+1])
                self.last_train_index = current_index
        
        # 特征工程
        try:
            df_features = self.feature_engineer.create_features(df)
        except Exception as e:
            logger.error(f"特征工程失败: {e}")
            return StrategySignal('hold', 0.0, "特征工程失败", "无法生成信号")
        
        # 检测市场状态
        if self.enable_regime_switching:
            self.current_regime = self.regime_detector.detect(df_features.iloc[:current_index+1])
        
        # 预测
        current_features = df_features.iloc[[current_index]]
        prediction = self.predict_return(current_features)
        
        # 记录预测历史
        self.prediction_history.append(prediction)
        
        # 根据预测生成信号
        return self._prediction_to_signal(prediction, current_features)
    
    def _prediction_to_signal(self, prediction: PredictionResult, 
                             features: pd.DataFrame) -> StrategySignal:
        """将预测结果转换为交易信号"""
        
        pred_return = prediction.predicted_return
        confidence = prediction.confidence
        
        # 置信度太低，不交易
        if confidence < self.confidence_threshold:
            return StrategySignal(
                'hold', 0.0, 
                "置信度不足", 
                f"预测收益率: {pred_return:.2%}, 置信度: {confidence:.2%}"
            )
        
        # 获取当前市场状态
        regime = prediction.market_regime
        
        # 根据预测收益率和市场状态生成信号
        if pred_return > 0.02:  # 预测上涨超过2%
            if regime == MarketRegime.TRENDING_UP:
                multiplier = 2.0 if confidence > 0.8 else 1.5
                reason = "强势上涨预测"
                description = f"预测{self.prediction_horizon}天上涨{pred_return:.2%}，趋势确认"
            else:
                multiplier = 1.5 if confidence > 0.75 else 1.2
                reason = "上涨预测"
                description = f"预测{self.prediction_horizon}天上涨{pred_return:.2%}"
            
            return StrategySignal('buy', multiplier, reason, description)
        
        elif pred_return > 0.005:  # 小幅上涨预测
            multiplier = 1.0 if confidence > 0.7 else 0.8
            return StrategySignal(
                'buy', multiplier,
                "小幅上涨预测",
                f"预测{self.prediction_horizon}天上涨{pred_return:.2%}"
            )
        
        elif pred_return < -0.02:  # 预测下跌超过2%
            if regime == MarketRegime.TRENDING_DOWN:
                multiplier = 1.0  # 清仓
                reason = "强势下跌预测"
                description = f"预测{self.prediction_horizon}天下跌{abs(pred_return):.2%}，趋势确认"
                suggestion = "建议卖出"
            else:
                multiplier = 0.0  # 暂停买入
                reason = "下跌预测"
                description = f"预测{self.prediction_horizon}天下跌{abs(pred_return):.2%}"
                suggestion = "暂停买入，观望"
            
            return StrategySignal('hold' if multiplier == 0 else 'sell', multiplier, reason, description, suggestion)
        
        elif pred_return < -0.005:  # 小幅下跌预测
            return StrategySignal(
                'hold', 0.0,
                "小幅下跌预测",
                f"预测{self.prediction_horizon}天下跌{abs(pred_return):.2%}",
                "建议观望"
            )
        
        else:  # 预测走势不明朗
            return StrategySignal(
                'hold', 0.0,
                "走势不明",
                f"预测{self.prediction_horizon}天变动{pred_return:.2%}",
                "建议观望"
            )
    
    def get_model_performance(self) -> Dict[str, Dict[str, Any]]:
        """获取各模型性能报告"""
        performance = {}
        for name, model in self.models.items():
            performance[name] = model.metrics.to_dict()
        return performance
    
    def switch_model(self, regime: MarketRegime):
        """根据市场状态切换模型权重"""
        best_model = self.regime_detector.get_best_model_type(regime)
        
        # 调整权重
        for name, model in self.models.items():
            if model.model_type == best_model:
                self.ensemble.voting_weights[name] = 2.0  # 提高最佳模型权重
            else:
                self.ensemble.voting_weights[name] = 1.0
        
        logger.info(f"市场状态切换为 {regime.value}，优先使用 {best_model.value} 模型")


def create_ml_strategy(prediction_horizon: int = 5, **kwargs) -> MLPredictionStrategy:
    """
    工厂函数：创建ML预测策略实例
    
    Args:
        prediction_horizon: 预测周期
        **kwargs: 其他参数
        
    Returns:
        MLPredictionStrategy: 策略实例
    """
    return MLPredictionStrategy(prediction_horizon=prediction_horizon, **kwargs)


# 策略兼容性函数（用于strategy_selector）
def get_ml_prediction_strategy() -> MLPredictionStrategy:
    """获取默认配置的ML预测策略"""
    return MLPredictionStrategy(
        prediction_horizon=5,
        confidence_threshold=0.6,
        enable_ensemble=True,
        enable_regime_switching=True
    )
