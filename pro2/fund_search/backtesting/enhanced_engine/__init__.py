"""
Enhanced Fund Backtesting Engine

This module provides advanced quantitative analysis capabilities for fund backtesting,
including sophisticated risk metrics, multi-factor performance attribution,
Monte Carlo simulations, and portfolio optimization.
"""

__version__ = "1.0.0"
__author__ = "Enhanced Backtesting Team"

from .attribution import MultiFactorAttribution
from .data_validator import DataValidator
from .monitoring import RealTimeMonitor
from .monte_carlo import MonteCarloEngine
from .optimization import PortfolioOptimizer

# Core modules
from .risk_metrics import EnhancedRiskMetrics
from .visualization import AdvancedVisualization

__all__ = [
    "EnhancedRiskMetrics",
    "MultiFactorAttribution",
    "MonteCarloEngine",
    "PortfolioOptimizer",
    "RealTimeMonitor",
    "AdvancedVisualization",
    "DataValidator",
]
