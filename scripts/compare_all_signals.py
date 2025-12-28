#!/usr/bin/env python3
"""
Comprehensive comparison of all signal generation methods.

Backtests all implemented signal methods:
- SMA (Simple Moving Average)
- EMA (Exponential Moving Average)
- Absolute Momentum (time-series)
- Relative Momentum (cross-sectional, top 3)
- Dual Momentum (top 2)

Compares performance metrics and visualizes results.
"""

from pathlib import Path
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.signals.trend_filter import generate_signals
from src.backtest.engine import calculate_strategy_returns, calculate_performance_metrics, calculate_drawdown_series


def backtest_all_signals(prices: pd.DataFrame) -> dict:
    """
    Backtest all signal methods and return results.

    Parameters
    ----------
    prices : pd.DataFrame
        Historical price data.

    Returns
    -------
    dict
        Dictionary mapping strategy name to results DataFrame and metrics.
    """
    results = {}

    # 1. SMA (252-day simple moving average)
    print("Backtesting SMA (252-day)...")
    sma_signals = generate_signals(prices, method='sma', window=252)
    sma_results = calculate_strategy_returns(
        prices,
        sma_signals,
        transaction_cost=0.0005,
        rebalance_frequency='M'
    )
    sma_metrics = calculate_performance_metrics(sma_results['returns'])
    results['SMA (252d)'] = {
        'signals': sma_signals,
        'results': sma_results,
        'metrics': sma_metrics
    }

    # 2. EMA (252-day exponential moving average)
    print("Backtesting EMA (252-day)...")
    ema_signals = generate_signals(prices, method='ema', span=252)
    ema_results = calculate_strategy_returns(
        prices,
        ema_signals,
        transaction_cost=0.0005,
        rebalance_frequency='M'
    )
    ema_metrics = calculate_performance_metrics(ema_results['returns'])
    results['EMA (252d)'] = {
        'signals': ema_signals,
        'results': ema_results,
        'metrics': ema_metrics
    }

    # 3. Absolute Momentum (252-day lookback)
    print("Backtesting Absolute Momentum (252-day)...")
    abs_signals = generate_signals(prices, method='absolute', lookback=252, threshold=0.0)
    abs_results = calculate_strategy_returns(
        prices,
        abs_signals,
        transaction_cost=0.0005,
        rebalance_frequency='M'
    )
    abs_metrics = calculate_performance_metrics(abs_results['returns'])
    results['Absolute Mom'] = {
        'signals': abs_signals,
        'results': abs_results,
        'metrics': abs_metrics
    }

    # 4. Relative Momentum (top 3 assets)
    print("Backtesting Relative Momentum (top 3)...")
    rel_signals = generate_signals(prices, method='relative', lookback=252, top_n=3)
    rel_results = calculate_strategy_returns(
        prices,
        rel_signals,
        transaction_cost=0.0005,
        rebalance_frequency='M'
    )
    rel_metrics = calculate_performance_metrics(rel_results['returns'])
    results['Relative Mom (top 3)'] = {
        'signals': rel_signals,
        'results': rel_results,
        'metrics': rel_metrics
    }

    # 5. Dual Momentum (top 2 assets with positive momentum)
    print("Backtesting Dual Momentum (top 2)...")
    dual_signals = generate_signals(prices, method='dual', lookback=252, top_n=2)
    dual_results = calculate_strategy_returns(
        prices,
        dual_signals,
        transaction_cost=0.0005,
        rebalance_frequency='M'
    )
    dual_metrics = calculate_performance_metrics(dual_results['returns'])
    results['Dual Mom (top 2)'] = {
        'signals': dual_signals,
        'results': dual_results,
        'metrics': dual_metrics
    }

    # 6. Buy & Hold benchmark (all assets equally weighted)
    print("Calculating Buy & Hold benchmark...")
    bh_signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
    bh_results = calculate_strategy_returns(
        prices,
        bh_signals,
        transaction_cost=0.0,  # No rebalancing
        rebalance_frequency='M'
    )
    bh_metrics = calculate_performance_metrics(bh_results['returns'])
    results['Buy & Hold'] = {
        'signals': bh_signals,
        'results': bh_results,
        'metrics': bh_metrics
    }

    return results


def create_comparison_table(results: dict) -> pd.DataFrame:
    """Create performance comparison table."""
    metrics_list = []

    for strategy_name, data in results.items():
        metrics = data['metrics'].copy()
        metrics['strategy'] = strategy_name

        # Add average positions
        avg_positions = data['signals'].sum(axis=1).mean()
        metrics['avg_positions'] = avg_positions

        # Add signal statistics
        signal_uptime = (data['signals'] > 0).mean().mean() * 100
        metrics['signal_uptime_pct'] = signal_uptime

        metrics_list.append(metrics)

    comparison_df = pd.DataFrame(metrics_list)

    # Reorder columns
    cols = ['strategy', 'total_return', 'annualized_return', 'annualized_volatility',
            'sharpe_ratio', 'sortino_ratio', 'max_drawdown', 'calmar_ratio',
            'win_rate', 'avg_positions', 'signal_uptime_pct']
    comparison_df = comparison_df[cols]

    # Rename for cleaner display
    comparison_df = comparison_df.rename(columns={'annualized_volatility': 'volatility'})

    # Sort by Sharpe ratio descending
    comparison_df = comparison_df.sort_values('sharpe_ratio', ascending=False)

    return comparison_df


def plot_comprehensive_comparison(results: dict, comparison_df: pd.DataFrame, output_path: Path):
    """Create comprehensive visualization comparing all strategies."""
    fig = plt.figure(figsize=(16, 12))

    # 1. Cumulative returns
    ax1 = plt.subplot(3, 3, 1)
    for strategy_name, data in results.items():
        equity = data['results']['portfolio_value']
        ax1.plot(equity.index, equity.values, label=strategy_name, linewidth=1.5)
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.set_title('Cumulative Performance')
    ax1.legend(fontsize=8, loc='upper left')
    ax1.grid(True, alpha=0.3)

    # 2. Drawdowns
    ax2 = plt.subplot(3, 3, 2)
    for strategy_name, data in results.items():
        returns = data['results']['returns']
        drawdown = calculate_drawdown_series(returns)
        ax2.plot(drawdown.index, drawdown.values * 100, label=strategy_name, linewidth=1)
    ax2.set_ylabel('Drawdown (%)')
    ax2.set_title('Drawdown Evolution')
    ax2.legend(fontsize=8, loc='lower left')
    ax2.grid(True, alpha=0.3)

    # 3. Sharpe ratio comparison
    ax3 = plt.subplot(3, 3, 3)
    sharpe_data = comparison_df.set_index('strategy')['sharpe_ratio'].sort_values()
    colors = ['green' if x > 0.6 else 'orange' if x > 0.4 else 'red' for x in sharpe_data]
    sharpe_data.plot(kind='barh', ax=ax3, color=colors)
    ax3.set_xlabel('Sharpe Ratio')
    ax3.set_title('Risk-Adjusted Returns (Sharpe)')
    ax3.grid(True, alpha=0.3, axis='x')

    # 4. Total returns comparison
    ax4 = plt.subplot(3, 3, 4)
    returns_data = comparison_df.set_index('strategy')['total_return'].sort_values() * 100
    returns_data.plot(kind='barh', ax=ax4, color='steelblue')
    ax4.set_xlabel('Total Return (%)')
    ax4.set_title('Total Returns (2005-2025)')
    ax4.grid(True, alpha=0.3, axis='x')

    # 5. Max drawdown comparison
    ax5 = plt.subplot(3, 3, 5)
    dd_data = comparison_df.set_index('strategy')['max_drawdown'].sort_values(ascending=False) * 100
    colors = ['green' if x > -25 else 'orange' if x > -35 else 'red' for x in dd_data]
    dd_data.plot(kind='barh', ax=ax5, color=colors)
    ax5.set_xlabel('Max Drawdown (%)')
    ax5.set_title('Worst Drawdown')
    ax5.grid(True, alpha=0.3, axis='x')

    # 6. Volatility comparison
    ax6 = plt.subplot(3, 3, 6)
    vol_data = comparison_df.set_index('strategy')['volatility'].sort_values() * 100
    vol_data.plot(kind='barh', ax=ax6, color='coral')
    ax6.set_xlabel('Volatility (%)')
    ax6.set_title('Annualized Volatility')
    ax6.grid(True, alpha=0.3, axis='x')

    # 7. Rolling Sharpe (252-day)
    ax7 = plt.subplot(3, 3, 7)
    for strategy_name, data in results.items():
        if strategy_name == 'Buy & Hold':
            continue  # Skip to reduce clutter
        returns = data['results']['returns']
        rolling_sharpe = (
            returns.rolling(252).mean() / returns.rolling(252).std() * np.sqrt(252)
        )
        ax7.plot(rolling_sharpe.index, rolling_sharpe.values, label=strategy_name, alpha=0.7)
    ax7.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
    ax7.set_ylabel('Rolling Sharpe (252d)')
    ax7.set_title('Rolling Sharpe Ratio Evolution')
    ax7.legend(fontsize=7, loc='upper left')
    ax7.grid(True, alpha=0.3)

    # 8. Average positions
    ax8 = plt.subplot(3, 3, 8)
    pos_data = comparison_df.set_index('strategy')['avg_positions'].sort_values()
    pos_data.plot(kind='barh', ax=ax8, color='mediumseagreen')
    ax8.set_xlabel('Average # of Positions')
    ax8.set_title('Portfolio Concentration')
    ax8.grid(True, alpha=0.3, axis='x')

    # 9. Returns vs Volatility scatter
    ax9 = plt.subplot(3, 3, 9)
    ax9.scatter(
        comparison_df['volatility'] * 100,
        comparison_df['annualized_return'] * 100,
        s=100,
        alpha=0.6
    )
    for idx, row in comparison_df.iterrows():
        ax9.annotate(
            row['strategy'],
            (row['volatility'] * 100, row['annualized_return'] * 100),
            fontsize=7,
            ha='right'
        )
    ax9.set_xlabel('Volatility (%)')
    ax9.set_ylabel('Annualized Return (%)')
    ax9.set_title('Risk-Return Trade-off')
    ax9.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nVisualization saved to: {output_path}")
    plt.close()


def main():
    """Main execution function."""
    print("=" * 70)
    print("COMPREHENSIVE SIGNAL METHOD COMPARISON")
    print("=" * 70)

    # Load data
    data_path = project_root / 'data' / 'processed' / 'prices_clean.csv'
    prices = pd.read_csv(data_path, index_col=0, parse_dates=True)

    print(f"\nData loaded: {prices.shape[0]} days, {prices.shape[1]} assets")
    print(f"Date range: {prices.index.min().date()} to {prices.index.max().date()}")
    print(f"Assets: {', '.join(prices.columns)}\n")

    # Backtest all methods
    results = backtest_all_signals(prices)

    # Create comparison table
    comparison_df = create_comparison_table(results)

    # Display results
    print("\n" + "=" * 70)
    print("PERFORMANCE COMPARISON")
    print("=" * 70)
    print(comparison_df.to_string(index=False, float_format='%.4f'))

    # Save results
    output_dir = project_root / 'outputs'
    output_dir.mkdir(exist_ok=True)

    csv_path = output_dir / 'signal_comparison.csv'
    comparison_df.to_csv(csv_path, index=False)
    print(f"\nResults saved to: {csv_path}")

    # Create visualization
    plot_path = output_dir / 'signal_comparison.png'
    plot_comprehensive_comparison(results, comparison_df, plot_path)

    # Print key insights
    print("\n" + "=" * 70)
    print("KEY INSIGHTS")
    print("=" * 70)

    best_sharpe = comparison_df.iloc[0]
    print(f"\nBest Sharpe Ratio: {best_sharpe['strategy']}")
    print(f"  Sharpe: {best_sharpe['sharpe_ratio']:.2f}")
    print(f"  Return: {best_sharpe['annualized_return']*100:.1f}% annualized")
    print(f"  Max DD: {best_sharpe['max_drawdown']*100:.1f}%")

    best_return = comparison_df.loc[comparison_df['total_return'].idxmax()]
    print(f"\nHighest Total Return: {best_return['strategy']}")
    print(f"  Return: {best_return['total_return']*100:.1f}%")
    print(f"  Sharpe: {best_return['sharpe_ratio']:.2f}")

    best_dd = comparison_df.loc[comparison_df['max_drawdown'].idxmax()]
    print(f"\nBest Drawdown Control: {best_dd['strategy']}")
    print(f"  Max DD: {best_dd['max_drawdown']*100:.1f}%")
    print(f"  Sharpe: {best_dd['sharpe_ratio']:.2f}")

    # Strategy characteristics
    print("\n" + "-" * 70)
    print("STRATEGY CHARACTERISTICS")
    print("-" * 70)
    for _, row in comparison_df.iterrows():
        print(f"\n{row['strategy']}:")
        print(f"  Avg Positions: {row['avg_positions']:.1f}")
        print(f"  Signal Uptime: {row['signal_uptime_pct']:.1f}%")
        print(f"  Win Rate: {row['win_rate']*100:.1f}%")


if __name__ == "__main__":
    main()
