"""
Enhanced Backtesting Engine - Visualization Charts

This module creates comprehensive charts and visualizations for portfolio
performance analysis using matplotlib and seaborn.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import seaborn as sns
from typing import Dict, List, Tuple, Optional, Any
import warnings

# Set style for better looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")
warnings.filterwarnings('ignore')

# Configure matplotlib for Chinese font support (if needed)
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class PerformanceVisualizer:
    """Performance visualization class for enhanced backtesting engine"""
    
    def __init__(self, figsize: Tuple[int, int] = (12, 8)):
        """
        Initialize the visualizer
        
        Args:
            figsize: Default figure size for plots
        """
        self.figsize = figsize
        self.colors = {
            'portfolio': '#2E86AB',
            'benchmark': '#A23B72', 
            'positive': '#F18F01',
            'negative': '#C73E1D',
            'neutral': '#6C757D'
        }
    
    def plot_cumulative_returns(self, portfolio_returns: pd.Series, 
                               benchmark_returns: pd.Series,
                               save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot cumulative returns comparison
        
        Args:
            portfolio_returns: Portfolio return series
            benchmark_returns: Benchmark return series
            save_path: Optional path to save the plot
            
        Returns:
            matplotlib Figure object
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # Calculate cumulative returns
        portfolio_cum = (1 + portfolio_returns).cumprod()
        benchmark_cum = (1 + benchmark_returns).cumprod()
        
        # Plot lines
        ax.plot(portfolio_cum.index, portfolio_cum.values, 
               color=self.colors['portfolio'], linewidth=2, label='Portfolio')
        ax.plot(benchmark_cum.index, benchmark_cum.values, 
               color=self.colors['benchmark'], linewidth=2, label='Benchmark')
        
        # Formatting
        ax.set_title('Cumulative Returns Comparison', fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Cumulative Return', fontsize=12)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        plt.xticks(rotation=45)
        
        # Add performance statistics
        portfolio_total = portfolio_cum.iloc[-1] - 1
        benchmark_total = benchmark_cum.iloc[-1] - 1
        excess_return = portfolio_total - benchmark_total
        
        stats_text = f'Portfolio Total Return: {portfolio_total:.1%}\n'
        stats_text += f'Benchmark Total Return: {benchmark_total:.1%}\n'
        stats_text += f'Excess Return: {excess_return:+.1%}'
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
               verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_drawdown_analysis(self, returns: pd.Series, 
                              save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot drawdown analysis
        
        Args:
            returns: Return series
            save_path: Optional path to save the plot
            
        Returns:
            matplotlib Figure object
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(self.figsize[0], self.figsize[1]*1.2))
        
        # Calculate cumulative returns and drawdowns
        cumulative_returns = (1 + returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdowns = (cumulative_returns - running_max) / running_max
        
        # Plot 1: Cumulative returns with underwater periods
        ax1.plot(cumulative_returns.index, cumulative_returns.values, 
                color=self.colors['portfolio'], linewidth=2, label='Cumulative Returns')
        ax1.plot(running_max.index, running_max.values, 
                color=self.colors['positive'], linewidth=1, alpha=0.7, label='Previous Peak')
        
        ax1.set_title('Portfolio Performance and Drawdowns', fontsize=16, fontweight='bold')
        ax1.set_ylabel('Cumulative Return', fontsize=12)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Drawdown underwater chart
        ax2.fill_between(drawdowns.index, drawdowns.values, 0, 
                        color=self.colors['negative'], alpha=0.7, label='Drawdown')
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        ax2.set_title('Drawdown Analysis', fontsize=14)
        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_ylabel('Drawdown (%)', fontsize=12)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1%}'.format(y)))
        ax2.grid(True, alpha=0.3)
        
        # Add drawdown statistics
        max_drawdown = drawdowns.min()
        drawdown_duration = self._calculate_max_drawdown_duration(drawdowns)
        
        stats_text = f'Max Drawdown: {max_drawdown:.1%}\n'
        stats_text += f'Max Duration: {drawdown_duration} days'
        
        ax2.text(0.02, 0.02, stats_text, transform=ax2.transAxes, 
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Format x-axis
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_risk_metrics_dashboard(self, risk_metrics: Dict[str, float],
                                   save_path: Optional[str] = None) -> plt.Figure:
        """
        Create a risk metrics dashboard
        
        Args:
            risk_metrics: Dictionary of risk metrics
            save_path: Optional path to save the plot
            
        Returns:
            matplotlib Figure object
        """
        fig = plt.figure(figsize=(15, 10))
        
        # Create a 2x3 grid
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)
        
        # 1. Risk-Return Scatter (placeholder with single point)
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.scatter(risk_metrics.get('annual_volatility', 0.2), 
                   risk_metrics.get('annual_return', 0.15),
                   s=200, color=self.colors['portfolio'], alpha=0.7, edgecolors='black')
        ax1.set_xlabel('Volatility (%)')
        ax1.set_ylabel('Return (%)')
        ax1.set_title('Risk-Return Profile')
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: '{:.1%}'.format(x)))
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1%}'.format(y)))
        
        # 2. Sharpe Ratio Gauge
        ax2 = fig.add_subplot(gs[0, 1])
        sharpe = risk_metrics.get('sharpe_ratio', 0)
        self._plot_gauge(ax2, sharpe, 'Sharpe Ratio', vmin=-1, vmax=3)
        
        # 3. Information Ratio Gauge
        ax3 = fig.add_subplot(gs[0, 2])
        info_ratio = risk_metrics.get('information_ratio', 0)
        self._plot_gauge(ax3, info_ratio, 'Information Ratio', vmin=-1, vmax=2)
        
        # 4. VaR Comparison
        ax4 = fig.add_subplot(gs[1, 0])
        var_data = {
            'VaR 95%': risk_metrics.get('var_95', -0.02),
            'VaR 99%': risk_metrics.get('var_99', -0.03)
        }
        bars = ax4.bar(var_data.keys(), [abs(v) for v in var_data.values()], 
                      color=[self.colors['negative'], self.colors['negative']])
        ax4.set_title('Value at Risk')
        ax4.set_ylabel('VaR (%)')
        ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1%}'.format(y)))
        
        # Add value labels on bars
        for bar, value in zip(bars, var_data.values()):
            ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
                    f'{value:.2%}', ha='center', va='bottom')
        
        # 5. Tracking Error vs Benchmark
        ax5 = fig.add_subplot(gs[1, 1])
        tracking_error = risk_metrics.get('tracking_error', 0.05)
        benchmark_vol = 0.12  # Assumed benchmark volatility
        
        categories = ['Portfolio\nVolatility', 'Benchmark\nVolatility', 'Tracking\nError']
        values = [risk_metrics.get('annual_volatility', 0.2), benchmark_vol, tracking_error]
        colors = [self.colors['portfolio'], self.colors['benchmark'], self.colors['positive']]
        
        bars = ax5.bar(categories, values, color=colors, alpha=0.7)
        ax5.set_title('Volatility Comparison')
        ax5.set_ylabel('Volatility (%)')
        ax5.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1%}'.format(y)))
        
        # 6. Maximum Drawdown
        ax6 = fig.add_subplot(gs[1, 2])
        max_dd = abs(risk_metrics.get('max_drawdown', -0.15))
        self._plot_gauge(ax6, max_dd, 'Max Drawdown', vmin=0, vmax=0.5, 
                        color_map='Reds', format_pct=True)
        
        plt.suptitle('Risk Metrics Dashboard', fontsize=18, fontweight='bold', y=0.95)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_sector_attribution(self, portfolio_allocation: Dict[str, float],
                               benchmark_allocation: Dict[str, float],
                               save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot sector attribution analysis
        
        Args:
            portfolio_allocation: Portfolio sector allocation
            benchmark_allocation: Benchmark sector allocation
            save_path: Optional path to save the plot
            
        Returns:
            matplotlib Figure object
        """
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. Portfolio Allocation Pie Chart
        sectors = list(portfolio_allocation.keys())
        port_weights = list(portfolio_allocation.values())
        
        wedges, texts, autotexts = ax1.pie(port_weights, labels=sectors, autopct='%1.1f%%',
                                          startangle=90, colors=sns.color_palette("husl", len(sectors)))
        ax1.set_title('Portfolio Sector Allocation', fontsize=14, fontweight='bold')
        
        # 2. Benchmark Allocation Pie Chart
        bench_weights = [benchmark_allocation.get(sector, 0) for sector in sectors]
        wedges2, texts2, autotexts2 = ax2.pie(bench_weights, labels=sectors, autopct='%1.1f%%',
                                             startangle=90, colors=sns.color_palette("husl", len(sectors)))
        ax2.set_title('Benchmark Sector Allocation', fontsize=14, fontweight='bold')
        
        # 3. Active Allocation Bar Chart
        active_weights = [portfolio_allocation.get(sector, 0) - benchmark_allocation.get(sector, 0) 
                         for sector in sectors]
        
        colors = [self.colors['positive'] if w >= 0 else self.colors['negative'] for w in active_weights]
        bars = ax3.barh(sectors, active_weights, color=colors, alpha=0.7)
        ax3.set_title('Active Allocation (Portfolio - Benchmark)', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Active Weight (%)')
        ax3.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
        ax3.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: '{:.1%}'.format(x)))
        
        # Add value labels
        for bar, value in zip(bars, active_weights):
            ax3.text(value + (0.005 if value >= 0 else -0.005), bar.get_y() + bar.get_height()/2,
                    f'{value:+.1%}', ha='left' if value >= 0 else 'right', va='center')
        
        # 4. Allocation Comparison
        x = np.arange(len(sectors))
        width = 0.35
        
        bars1 = ax4.bar(x - width/2, port_weights, width, label='Portfolio', 
                       color=self.colors['portfolio'], alpha=0.7)
        bars2 = ax4.bar(x + width/2, bench_weights, width, label='Benchmark', 
                       color=self.colors['benchmark'], alpha=0.7)
        
        ax4.set_title('Sector Allocation Comparison', fontsize=14, fontweight='bold')
        ax4.set_xlabel('Sectors')
        ax4.set_ylabel('Weight (%)')
        ax4.set_xticks(x)
        ax4.set_xticklabels(sectors, rotation=45, ha='right')
        ax4.legend()
        ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1%}'.format(y)))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_monte_carlo_results(self, simulation_results: np.ndarray,
                                percentiles: Dict[int, float],
                                save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot Monte Carlo simulation results
        
        Args:
            simulation_results: Array of simulation final values
            percentiles: Dictionary of percentile values
            save_path: Optional path to save the plot
            
        Returns:
            matplotlib Figure object
        """
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. Histogram of Results
        ax1.hist(simulation_results, bins=50, alpha=0.7, color=self.colors['portfolio'], 
                edgecolor='black', linewidth=0.5)
        ax1.axvline(x=1.0, color='red', linestyle='--', linewidth=2, label='Break-even')
        ax1.axvline(x=np.mean(simulation_results), color='orange', linestyle='-', 
                   linewidth=2, label=f'Mean: {np.mean(simulation_results):.3f}')
        ax1.set_title('Distribution of 1-Year Returns', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Final Portfolio Value')
        ax1.set_ylabel('Frequency')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Percentile Analysis
        percentile_keys = sorted(percentiles.keys())
        percentile_values = [percentiles[k] for k in percentile_keys]
        
        colors = [self.colors['negative'] if v < 1.0 else self.colors['positive'] for v in percentile_values]
        bars = ax2.bar([f'{k}th' for k in percentile_keys], percentile_values, 
                      color=colors, alpha=0.7, edgecolor='black')
        ax2.axhline(y=1.0, color='red', linestyle='--', linewidth=1, alpha=0.7)
        ax2.set_title('Percentile Analysis', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Percentile')
        ax2.set_ylabel('Final Portfolio Value')
        
        # Add value labels
        for bar, value in zip(bars, percentile_values):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f'{value:.3f}\n({(value-1)*100:+.1f}%)', ha='center', va='bottom')
        
        # 3. Risk Metrics
        prob_loss = (simulation_results < 1.0).mean()
        expected_return = np.mean(simulation_results) - 1
        worst_5_percent = simulation_results[simulation_results <= np.percentile(simulation_results, 5)]
        expected_shortfall = np.mean(worst_5_percent) - 1
        
        risk_metrics = {
            'Probability\nof Loss': prob_loss,
            'Expected\nReturn': expected_return,
            'Expected\nShortfall (5%)': expected_shortfall
        }
        
        metric_names = list(risk_metrics.keys())
        metric_values = list(risk_metrics.values())
        colors = [self.colors['negative'] if v < 0 else self.colors['positive'] for v in metric_values]
        
        bars = ax3.bar(metric_names, metric_values, color=colors, alpha=0.7)
        ax3.set_title('Risk Analysis', fontsize=14, fontweight='bold')
        ax3.set_ylabel('Value')
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        # Format y-axis as percentage for first metric, others as percentage
        for i, (bar, value) in enumerate(zip(bars, metric_values)):
            if i == 0:  # Probability of loss
                label = f'{value:.1%}'
            else:  # Returns
                label = f'{value:+.1%}'
            ax3.text(bar.get_x() + bar.get_width()/2, 
                    bar.get_height() + (0.01 if value >= 0 else -0.02),
                    label, ha='center', va='bottom' if value >= 0 else 'top')
        
        # 4. Confidence Intervals
        confidence_levels = [90, 95, 99]
        lower_bounds = [np.percentile(simulation_results, (100-cl)/2) for cl in confidence_levels]
        upper_bounds = [np.percentile(simulation_results, 100-(100-cl)/2) for cl in confidence_levels]
        
        x_pos = np.arange(len(confidence_levels))
        ax4.errorbar(x_pos, [1.0]*len(confidence_levels), 
                    yerr=[np.array([1.0]*len(confidence_levels)) - np.array(lower_bounds),
                          np.array(upper_bounds) - np.array([1.0]*len(confidence_levels))],
                    fmt='o', capsize=10, capthick=2, markersize=8,
                    color=self.colors['portfolio'], ecolor=self.colors['portfolio'])
        
        ax4.set_title('Confidence Intervals', fontsize=14, fontweight='bold')
        ax4.set_xlabel('Confidence Level')
        ax4.set_ylabel('Portfolio Value Range')
        ax4.set_xticks(x_pos)
        ax4.set_xticklabels([f'{cl}%' for cl in confidence_levels])
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_rolling_metrics(self, returns: pd.Series, benchmark_returns: pd.Series,
                            window: int = 252, save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot rolling performance metrics
        
        Args:
            returns: Portfolio return series
            benchmark_returns: Benchmark return series
            window: Rolling window size (default 252 for 1 year)
            save_path: Optional path to save the plot
            
        Returns:
            matplotlib Figure object
        """
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # Calculate rolling metrics
        rolling_return = returns.rolling(window).mean() * 252
        rolling_vol = returns.rolling(window).std() * np.sqrt(252)
        rolling_sharpe = rolling_return / rolling_vol
        
        excess_returns = returns - benchmark_returns
        rolling_tracking_error = excess_returns.rolling(window).std() * np.sqrt(252)
        rolling_info_ratio = (excess_returns.rolling(window).mean() * 252) / rolling_tracking_error
        
        # 1. Rolling Returns
        ax1.plot(rolling_return.index, rolling_return.values, 
                color=self.colors['portfolio'], linewidth=2, label='Portfolio')
        benchmark_rolling_return = benchmark_returns.rolling(window).mean() * 252
        ax1.plot(benchmark_rolling_return.index, benchmark_rolling_return.values,
                color=self.colors['benchmark'], linewidth=2, label='Benchmark')
        ax1.set_title(f'Rolling {window//252}-Year Annualized Returns', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Annualized Return (%)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1%}'.format(y)))
        
        # 2. Rolling Volatility
        ax2.plot(rolling_vol.index, rolling_vol.values, 
                color=self.colors['portfolio'], linewidth=2, label='Portfolio')
        benchmark_rolling_vol = benchmark_returns.rolling(window).std() * np.sqrt(252)
        ax2.plot(benchmark_rolling_vol.index, benchmark_rolling_vol.values,
                color=self.colors['benchmark'], linewidth=2, label='Benchmark')
        ax2.set_title(f'Rolling {window//252}-Year Volatility', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Volatility (%)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1%}'.format(y)))
        
        # 3. Rolling Sharpe Ratio
        ax3.plot(rolling_sharpe.index, rolling_sharpe.values, 
                color=self.colors['positive'], linewidth=2)
        ax3.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax3.set_title(f'Rolling {window//252}-Year Sharpe Ratio', fontsize=14, fontweight='bold')
        ax3.set_ylabel('Sharpe Ratio')
        ax3.grid(True, alpha=0.3)
        
        # 4. Rolling Information Ratio
        ax4.plot(rolling_info_ratio.index, rolling_info_ratio.values, 
                color=self.colors['neutral'], linewidth=2)
        ax4.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax4.set_title(f'Rolling {window//252}-Year Information Ratio', fontsize=14, fontweight='bold')
        ax4.set_ylabel('Information Ratio')
        ax4.grid(True, alpha=0.3)
        
        # Format x-axis for all subplots
        for ax in [ax1, ax2, ax3, ax4]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def _plot_gauge(self, ax, value: float, title: str, vmin: float = 0, vmax: float = 1,
                   color_map: str = 'RdYlGn', format_pct: bool = False):
        """Helper function to create gauge plots"""
        # Normalize value
        norm_value = (value - vmin) / (vmax - vmin)
        norm_value = max(0, min(1, norm_value))  # Clamp to [0, 1]
        
        # Create gauge
        theta = np.linspace(0, np.pi, 100)
        r = np.ones_like(theta)
        
        # Color based on value
        if color_map == 'RdYlGn':
            if norm_value < 0.3:
                color = self.colors['negative']
            elif norm_value < 0.7:
                color = self.colors['positive']
            else:
                color = '#2E8B57'  # Sea green
        else:
            color = plt.cm.get_cmap(color_map)(norm_value)
        
        # Plot gauge background
        ax.fill_between(theta, 0, r, alpha=0.3, color='lightgray')
        
        # Plot value
        value_theta = np.pi * (1 - norm_value)
        ax.plot([value_theta, value_theta], [0, 1], color=color, linewidth=8)
        ax.scatter([value_theta], [1], color=color, s=100, zorder=5)
        
        # Formatting
        ax.set_ylim(0, 1.2)
        ax.set_xlim(0, np.pi)
        ax.set_aspect('equal')
        ax.axis('off')
        
        # Add title and value
        if format_pct:
            value_text = f'{value:.1%}'
        else:
            value_text = f'{value:.2f}'
        
        ax.text(np.pi/2, 0.5, value_text, ha='center', va='center', 
               fontsize=16, fontweight='bold')
        ax.text(np.pi/2, 1.1, title, ha='center', va='center', 
               fontsize=12, fontweight='bold')
        
        # Add scale labels
        ax.text(0, -0.1, f'{vmin:.1f}', ha='center', va='top', fontsize=10)
        ax.text(np.pi, -0.1, f'{vmax:.1f}', ha='center', va='top', fontsize=10)
    
    def _calculate_max_drawdown_duration(self, drawdowns: pd.Series) -> int:
        """Calculate maximum drawdown duration"""
        in_drawdown = drawdowns < 0
        drawdown_periods = []
        start = None
        
        for i, is_dd in enumerate(in_drawdown):
            if is_dd and start is None:
                start = i
            elif not is_dd and start is not None:
                drawdown_periods.append(i - start)
                start = None
        
        # Handle case where drawdown continues to the end
        if start is not None:
            drawdown_periods.append(len(drawdowns) - start)
        
        return max(drawdown_periods) if drawdown_periods else 0
    
    def create_comprehensive_report(self, data: Dict[str, Any], 
                                   save_dir: str = "charts") -> Dict[str, plt.Figure]:
        """
        Create a comprehensive visualization report
        
        Args:
            data: Dictionary containing all analysis data
            save_dir: Directory to save charts
            
        Returns:
            Dictionary of figure objects
        """
        import os
        os.makedirs(save_dir, exist_ok=True)
        
        figures = {}
        
        # 1. Cumulative Returns
        if 'portfolio_returns' in data and 'benchmark_returns' in data:
            fig1 = self.plot_cumulative_returns(
                data['portfolio_returns'], 
                data['benchmark_returns'],
                save_path=f"{save_dir}/01_cumulative_returns.png"
            )
            figures['cumulative_returns'] = fig1
        
        # 2. Drawdown Analysis
        if 'portfolio_returns' in data:
            fig2 = self.plot_drawdown_analysis(
                data['portfolio_returns'],
                save_path=f"{save_dir}/02_drawdown_analysis.png"
            )
            figures['drawdown_analysis'] = fig2
        
        # 3. Risk Metrics Dashboard
        if 'risk_metrics' in data:
            fig3 = self.plot_risk_metrics_dashboard(
                data['risk_metrics'],
                save_path=f"{save_dir}/03_risk_metrics_dashboard.png"
            )
            figures['risk_dashboard'] = fig3
        
        # 4. Sector Attribution
        if 'sector_allocation' in data and 'benchmark_allocation' in data:
            fig4 = self.plot_sector_attribution(
                data['sector_allocation'],
                data['benchmark_allocation'],
                save_path=f"{save_dir}/04_sector_attribution.png"
            )
            figures['sector_attribution'] = fig4
        
        # 5. Monte Carlo Results
        if 'simulation_results' in data and 'percentiles' in data:
            fig5 = self.plot_monte_carlo_results(
                data['simulation_results'],
                data['percentiles'],
                save_path=f"{save_dir}/05_monte_carlo_results.png"
            )
            figures['monte_carlo'] = fig5
        
        # 6. Rolling Metrics
        if 'portfolio_returns' in data and 'benchmark_returns' in data:
            fig6 = self.plot_rolling_metrics(
                data['portfolio_returns'],
                data['benchmark_returns'],
                save_path=f"{save_dir}/06_rolling_metrics.png"
            )
            figures['rolling_metrics'] = fig6
        
        print(f"📊 Generated {len(figures)} charts in '{save_dir}' directory")
        return figures