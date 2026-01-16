"""
Enhanced Fund Backtesting Engine

This module provides advanced quantitative analysis capabilities for fund backtesting,
including sophisticated risk metrics, multi-factor performance attribution,
Monte Carlo simulations, and portfolio optimization.
"""

__version__ = "1.0.0"
__author__ = "Enhanced Backtesting Team"

# Core modules - always available
from .risk_metrics import EnhancedRiskMetrics, RiskMetrics

# Optional modules - may have additional dependencies
try:
    from .attribution import MultiFactorAttribution
except ImportError:
    MultiFactorAttribution = None

try:
    from .data_validator import DataValidator
except ImportError:
    DataValidator = None

try:
    from .monitoring import RealTimeMonitor
except ImportError:
    RealTimeMonitor = None

try:
    from .monte_carlo import MonteCarloEngine
except ImportError:
    MonteCarloEngine = None

try:
    from .optimization import PortfolioOptimizer
except ImportError:
    PortfolioOptimizer = None

try:
    from .visualization import AdvancedVisualization
except ImportError:
    AdvancedVisualization = None

__all__ = [
    "EnhancedRiskMetrics",
    "RiskMetrics",
    "MultiFactorAttribution",
    "MonteCarloEngine",
    "PortfolioOptimizer",
    "RealTimeMonitor",
    "AdvancedVisualization",
    "DataValidator",
]
