"""
Enhanced Backtesting Engine - Visual Example

This example demonstrates comprehensive visualization capabilities
for portfolio performance analysis with charts and graphs.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from visualization_charts import PerformanceVisualizer


def generate_enhanced_sample_data():
    """Generate enhanced sample data for visualization"""
    
    # Generate date range
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2023, 12, 31)
    dates = pd.date_range(start_date, end_date, freq='D')
    
    # Generate more realistic portfolio returns with volatility clustering
    np.random.seed(42)
    n_days = len(dates)
    
    # Create regime-based returns (bull/bear markets)
    regime_changes = [0, 300, 800, 1200]  # Days where regime changes
    regimes = ['bull', 'bear', 'recovery', 'bull']
    
    portfolio_returns = []
    benchmark_returns = []
    
    for i in range(len(regime_changes)):
        start_idx = regime_changes[i]
        end_idx = regime_changes[i+1] if i+1 < len(regime_changes) else n_days
        period_length = end_idx - start_idx
        
        if regimes[i] == 'bull':
            # Bull market: higher returns, moderate volatility
            port_ret = np.random.normal(0.0012, 0.012, period_length)
            bench_ret = np.random.normal(0.0008, 0.010, period_length)
        elif regimes[i] == 'bear':
            # Bear market: negative returns, high volatility
            port_ret = np.random.normal(-0.0008, 0.025, period_length)
            bench_ret = np.random.normal(-0.0005, 0.020, period_length)
        else:  # recovery
            # Recovery: volatile but positive returns
            port_ret = np.random.normal(0.0015, 0.020, period_length)
            bench_ret = np.random.normal(0.0010, 0.015, period_length)
        
        portfolio_returns.extend(port_ret)
        benchmark_returns.extend(bench_ret)
    
    portfolio_returns = pd.Series(portfolio_returns, index=dates, name='Portfolio')
    benchmark_returns = pd.Series(benchmark_returns, index=dates, name='Benchmark')
    
    # Generate portfolio holdings data with more detail
    securities = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'JNJ', 'PG']
    weights = np.array([0.15, 0.12, 0.10, 0.08, 0.07, 0.06, 0.05, 0.12, 0.13, 0.12])
    sectors = ['Technology', 'Technology', 'Technology', 'Technology', 'Technology',
               'Technology', 'Technology', 'Financial', 'Healthcare', 'Consumer Goods']
    
    portfolio_data = pd.DataFrame({
        'Symbol': securities,
        'Weight': weights,
        'Sector': sectors,
        'Market_Value': weights * 10000000  # $10M portfolio
    })
    
    # Sector allocations
    sector_allocation = portfolio_data.groupby('Sector')['Weight'].sum().to_dict()
    benchmark_allocation = {
        'Technology': 0.45,
        'Financial': 0.15,
        'Healthcare': 0.20,
        'Consumer Goods': 0.20
    }
    
    return {
        'portfolio_returns': portfolio_returns,
        'benchmark_returns': benchmark_returns,
        'portfolio_data': portfolio_data,
        'sector_allocation': sector_allocation,
        'benchmark_allocation': benchmark_allocation,
        'dates': dates
    }


def calculate_comprehensive_metrics(data):
    """Calculate comprehensive performance metrics"""
    
    portfolio_returns = data['portfolio_returns']
    benchmark_returns = data['benchmark_returns']
    
    # Basic metrics
    total_return = (portfolio_returns + 1).prod() - 1
    annual_return = portfolio_returns.mean() * 252
    annual_volatility = portfolio_returns.std() * np.sqrt(252)
    sharpe_ratio = annual_return / annual_volatility
    
    # Risk metrics
    excess_returns = portfolio_returns - benchmark_returns
    tracking_error = excess_returns.std() * np.sqrt(252)
    information_ratio = (excess_returns.mean() * 252) / tracking_error if tracking_error > 0 else 0
    
    # VaR calculations
    var_95 = np.percentile(portfolio_returns, 5)
    var_99 = np.percentile(portfolio_returns, 1)
    
    # Drawdown analysis
    cumulative_returns = (1 + portfolio_returns).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdowns = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdowns.min()
    
    return {
        'total_return': total_return,
        'annual_return': annual_return,
        'annual_volatility': annual_volatility,
        'sharpe_ratio': sharpe_ratio,
        'tracking_error': tracking_error,
        'information_ratio': information_ratio,
        'var_95': var_95,
        'var_99': var_99,
        'max_drawdown': max_drawdown
    }


def run_monte_carlo_simulation(returns, num_simulations=1000, time_horizon=252):
    """Run Monte Carlo simulation"""
    
    mean_return = returns.mean()
    volatility = returns.std()
    
    # Generate simulations
    np.random.seed(42)
    simulated_returns = np.random.normal(
        mean_return, volatility, 
        (num_simulations, time_horizon)
    )
    
    # Calculate cumulative returns
    cumulative_returns = (1 + simulated_returns).cumprod(axis=1)
    final_values = cumulative_returns[:, -1]
    
    # Calculate percentiles
    percentiles = {
        5: np.percentile(final_values, 5),
        25: np.percentile(final_values, 25),
        50: np.percentile(final_values, 50),
        75: np.percentile(final_values, 75),
        95: np.percentile(final_values, 95)
    }
    
    return final_values, percentiles


def create_visualization_demo():
    """Create comprehensive visualization demonstration"""
    
    print("🎨 Enhanced Backtesting Engine - Visualization Demo")
    print("=" * 60)
    
    # Generate data
    print("📊 Generating enhanced sample data...")
    data = generate_enhanced_sample_data()
    
    # Calculate metrics
    print("📈 Calculating performance metrics...")
    risk_metrics = calculate_comprehensive_metrics(data)
    
    # Run Monte Carlo simulation
    print("🎲 Running Monte Carlo simulation...")
    simulation_results, percentiles = run_monte_carlo_simulation(data['portfolio_returns'])
    
    # Prepare comprehensive data for visualization
    viz_data = {
        'portfolio_returns': data['portfolio_returns'],
        'benchmark_returns': data['benchmark_returns'],
        'risk_metrics': risk_metrics,
        'sector_allocation': data['sector_allocation'],
        'benchmark_allocation': data['benchmark_allocation'],
        'simulation_results': simulation_results,
        'percentiles': percentiles
    }
    
    # Create visualizer
    print("🎨 Creating visualizations...")
    visualizer = PerformanceVisualizer(figsize=(12, 8))
    
    # Generate all charts
    figures = visualizer.create_comprehensive_report(viz_data, save_dir="performance_charts")
    
    # Display individual charts
    print("\n📊 Displaying individual charts...")
    
    # Show charts one by one (comment out plt.show() if running in batch)
    for chart_name, fig in figures.items():
        print(f"   📈 {chart_name.replace('_', ' ').title()}")
        # plt.show()  # Uncomment to display charts interactively
    
    # Print summary statistics
    print("\n📋 Performance Summary")
    print("-" * 40)
    print(f"Total Return (4 years): {risk_metrics['total_return']:.2%}")
    print(f"Annualized Return: {risk_metrics['annual_return']:.2%}")
    print(f"Annualized Volatility: {risk_metrics['annual_volatility']:.2%}")
    print(f"Sharpe Ratio: {risk_metrics['sharpe_ratio']:.2f}")
    print(f"Information Ratio: {risk_metrics['information_ratio']:.2f}")
    print(f"Maximum Drawdown: {risk_metrics['max_drawdown']:.2%}")
    print(f"VaR (95%): {risk_metrics['var_95']:.2%}")
    
    print("\n🎯 Monte Carlo Results")
    print("-" * 40)
    for p, value in percentiles.items():
        print(f"{p:2d}th Percentile: {value:.3f} ({(value-1)*100:+.1f}%)")
    
    prob_loss = (simulation_results < 1.0).mean()
    expected_return = np.mean(simulation_results) - 1
    print(f"Probability of Loss: {prob_loss:.1%}")
    print(f"Expected Return: {expected_return:.1%}")
    
    print("\n🏢 Sector Analysis")
    print("-" * 40)
    for sector, weight in data['sector_allocation'].items():
        benchmark_weight = data['benchmark_allocation'].get(sector, 0)
        active_weight = weight - benchmark_weight
        print(f"{sector:15s}: {weight:.1%} (vs {benchmark_weight:.1%}, active: {active_weight:+.1%})")
    
    print(f"\n📁 Charts saved to 'performance_charts' directory")
    print(f"   Generated {len(figures)} comprehensive charts")
    
    return figures, viz_data


def create_custom_chart_example():
    """Example of creating custom charts"""
    
    print("\n🎨 Custom Chart Example")
    print("-" * 40)
    
    # Generate simple data
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    returns = pd.Series(np.random.normal(0.0008, 0.015, len(dates)), index=dates)
    benchmark = pd.Series(np.random.normal(0.0006, 0.012, len(dates)), index=dates)
    
    # Create visualizer
    visualizer = PerformanceVisualizer()
    
    # Create individual charts
    print("📈 Creating cumulative returns chart...")
    fig1 = visualizer.plot_cumulative_returns(returns, benchmark, 
                                             save_path="custom_cumulative_returns.png")
    
    print("📉 Creating drawdown analysis...")
    fig2 = visualizer.plot_drawdown_analysis(returns, 
                                            save_path="custom_drawdown_analysis.png")
    
    # Calculate some metrics for dashboard
    risk_metrics = {
        'annual_return': returns.mean() * 252,
        'annual_volatility': returns.std() * np.sqrt(252),
        'sharpe_ratio': (returns.mean() * 252) / (returns.std() * np.sqrt(252)),
        'information_ratio': 0.8,
        'var_95': np.percentile(returns, 5),
        'var_99': np.percentile(returns, 1),
        'tracking_error': (returns - benchmark).std() * np.sqrt(252),
        'max_drawdown': -0.12
    }
    
    print("📊 Creating risk metrics dashboard...")
    fig3 = visualizer.plot_risk_metrics_dashboard(risk_metrics, 
                                                 save_path="custom_risk_dashboard.png")
    
    print("✅ Custom charts created successfully!")
    
    return [fig1, fig2, fig3]


def main():
    """Main demonstration function"""
    
    try:
        # Run comprehensive demo
        figures, data = create_visualization_demo()
        
        # Run custom chart example
        custom_figures = create_custom_chart_example()
        
        print("\n" + "=" * 60)
        print("🎉 Visualization Demo Completed Successfully!")
        print("=" * 60)
        
        print(f"\n📊 Generated Charts:")
        print(f"   • Comprehensive Report: {len(figures)} charts")
        print(f"   • Custom Examples: {len(custom_figures)} charts")
        print(f"   • Total Charts: {len(figures) + len(custom_figures)}")
        
        print(f"\n💡 Chart Types Created:")
        chart_types = [
            "Cumulative Returns Comparison",
            "Drawdown Analysis", 
            "Risk Metrics Dashboard",
            "Sector Attribution Analysis",
            "Monte Carlo Simulation Results",
            "Rolling Performance Metrics"
        ]
        
        for i, chart_type in enumerate(chart_types, 1):
            print(f"   {i}. {chart_type}")
        
        print(f"\n📁 Files Created:")
        print(f"   • performance_charts/ - Comprehensive analysis charts")
        print(f"   • custom_*.png - Individual example charts")
        
        print(f"\n🔧 Usage Tips:")
        print(f"   • Charts are saved as high-resolution PNG files")
        print(f"   • Uncomment plt.show() to display charts interactively")
        print(f"   • Modify colors and styles in PerformanceVisualizer class")
        print(f"   • Add custom metrics to risk_metrics dictionary")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during visualization demo: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    
    if success:
        print(f"\n🚀 Ready to integrate with enhanced backtesting engine!")
    else:
        print(f"\n⚠️  Demo completed with some issues")