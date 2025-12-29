#!/usr/bin/env python3
"""
EMA Span Parameter Optimization

Tests EMA trend filter across multiple span parameters to find optimal
lookback period. Evaluates:
- Performance metrics across spans
- Robustness (coefficient of variation)
- Overfitting risk
- Drawdown characteristics

Spans tested: 63d (3M), 126d (6M), 189d (9M), 252d (12M), 315d (15M), 378d (18M)
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
from src.backtest.engine import calculate_strategy_returns, calculate_performance_metrics


def optimize_ema_span(prices: pd.DataFrame, spans: list) -> pd.DataFrame:
    """
    Test EMA strategy across different span parameters.

    Parameters
    ----------
    prices : pd.DataFrame
        Historical price data.
    spans : list
        List of EMA spans to test.

    Returns
    -------
    pd.DataFrame
        Performance metrics for each span.
    """
    results = []

    for span in spans:
        print(f"Testing EMA span = {span} days...")

        # Generate signals
        signals = generate_signals(prices, method='ema', span=span)

        # Backtest
        backtest_results = calculate_strategy_returns(
            prices,
            signals,
            transaction_cost=0.0005,
            rebalance_frequency='M'
        )

        # Calculate metrics
        metrics = calculate_performance_metrics(backtest_results['returns'])

        # Add span and label
        metrics['span'] = span
        if span == 63:
            metrics['label'] = '3M'
        elif span == 126:
            metrics['label'] = '6M'
        elif span == 189:
            metrics['label'] = '9M'
        elif span == 252:
            metrics['label'] = '12M (current)'
        elif span == 315:
            metrics['label'] = '15M'
        elif span == 378:
            metrics['label'] = '18M'
        else:
            metrics['label'] = f'{span}d'

        # Calculate additional statistics
        avg_positions = signals.sum(axis=1).mean()
        metrics['avg_positions'] = avg_positions

        # Calculate average turnover
        monthly_turnover = backtest_results['turnover'].resample('ME').sum().mean()
        metrics['avg_turnover'] = monthly_turnover

        results.append(metrics)

    return pd.DataFrame(results)


def analyze_robustness(results_df: pd.DataFrame) -> dict:
    """
    Analyze robustness of results across parameters.

    Lower coefficient of variation indicates more stable performance
    across parameter choices (less overfitting risk).

    Parameters
    ----------
    results_df : pd.DataFrame
        Results from parameter optimization.

    Returns
    -------
    dict
        Robustness metrics including CV of Sharpe and returns.
    """
    sharpe_mean = results_df['sharpe_ratio'].mean()
    sharpe_std = results_df['sharpe_ratio'].std()
    sharpe_cv = (sharpe_std / sharpe_mean) * 100 if sharpe_mean > 0 else np.nan

    return_mean = results_df['annualized_return'].mean()
    return_std = results_df['annualized_return'].std()
    return_cv = (return_std / return_mean) * 100 if return_mean > 0 else np.nan

    return {
        'sharpe_cv': sharpe_cv,
        'return_cv': return_cv,
        'sharpe_range': results_df['sharpe_ratio'].max() - results_df['sharpe_ratio'].min(),
        'return_range': results_df['annualized_return'].max() - results_df['annualized_return'].min()
    }


def plot_optimization_results(results_df: pd.DataFrame, robustness: dict, output_path: Path):
    """Create comprehensive visualization of optimization results."""
    fig = plt.figure(figsize=(16, 12))

    # 1. Sharpe Ratio vs Span
    ax1 = plt.subplot(3, 3, 1)
    ax1.plot(results_df['span'], results_df['sharpe_ratio'], 'o-', linewidth=2, markersize=8)
    best_idx = results_df['sharpe_ratio'].idxmax()
    ax1.plot(results_df.loc[best_idx, 'span'], results_df.loc[best_idx, 'sharpe_ratio'],
             'r*', markersize=20, label=f"Best: {results_df.loc[best_idx, 'label']}")
    ax1.set_xlabel('EMA Span (days)')
    ax1.set_ylabel('Sharpe Ratio')
    ax1.set_title('Sharpe Ratio vs EMA Span')
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # 2. Total Return vs Span
    ax2 = plt.subplot(3, 3, 2)
    ax2.plot(results_df['span'], results_df['total_return'] * 100, 'o-',
             linewidth=2, markersize=8, color='green')
    best_return_idx = results_df['total_return'].idxmax()
    ax2.plot(results_df.loc[best_return_idx, 'span'],
             results_df.loc[best_return_idx, 'total_return'] * 100,
             'r*', markersize=20, label=f"Best: {results_df.loc[best_return_idx, 'label']}")
    ax2.set_xlabel('EMA Span (days)')
    ax2.set_ylabel('Total Return (%)')
    ax2.set_title('Total Return vs EMA Span')
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # 3. Max Drawdown vs Span
    ax3 = plt.subplot(3, 3, 3)
    ax3.plot(results_df['span'], results_df['max_drawdown'] * 100, 'o-',
             linewidth=2, markersize=8, color='red')
    best_dd_idx = results_df['max_drawdown'].idxmax()  # Closest to 0
    ax3.plot(results_df.loc[best_dd_idx, 'span'],
             results_df.loc[best_dd_idx, 'max_drawdown'] * 100,
             'g*', markersize=20, label=f"Best: {results_df.loc[best_dd_idx, 'label']}")
    ax3.set_xlabel('EMA Span (days)')
    ax3.set_ylabel('Max Drawdown (%)')
    ax3.set_title('Maximum Drawdown vs EMA Span')
    ax3.grid(True, alpha=0.3)
    ax3.legend()

    # 4. Risk-Return Scatter
    ax4 = plt.subplot(3, 3, 4)
    scatter = ax4.scatter(results_df['annualized_volatility'] * 100,
                          results_df['annualized_return'] * 100,
                          c=results_df['sharpe_ratio'],
                          s=200,
                          cmap='RdYlGn',
                          edgecolors='black',
                          linewidth=2)
    for idx, row in results_df.iterrows():
        ax4.annotate(row['label'],
                     (row['annualized_volatility'] * 100, row['annualized_return'] * 100),
                     fontsize=9,
                     ha='right')
    ax4.set_xlabel('Volatility (%)')
    ax4.set_ylabel('Annualized Return (%)')
    ax4.set_title('Risk-Return Trade-off (color = Sharpe)')
    ax4.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax4, label='Sharpe Ratio')

    # 5. Calmar Ratio vs Span
    ax5 = plt.subplot(3, 3, 5)
    ax5.plot(results_df['span'], results_df['calmar_ratio'], 'o-',
             linewidth=2, markersize=8, color='purple')
    best_calmar_idx = results_df['calmar_ratio'].idxmax()
    ax5.plot(results_df.loc[best_calmar_idx, 'span'],
             results_df.loc[best_calmar_idx, 'calmar_ratio'],
             'r*', markersize=20, label=f"Best: {results_df.loc[best_calmar_idx, 'label']}")
    ax5.set_xlabel('EMA Span (days)')
    ax5.set_ylabel('Calmar Ratio')
    ax5.set_title('Calmar Ratio vs EMA Span')
    ax5.grid(True, alpha=0.3)
    ax5.legend()

    # 6. Sortino Ratio vs Span
    ax6 = plt.subplot(3, 3, 6)
    ax6.plot(results_df['span'], results_df['sortino_ratio'], 'o-',
             linewidth=2, markersize=8, color='orange')
    best_sortino_idx = results_df['sortino_ratio'].idxmax()
    ax6.plot(results_df.loc[best_sortino_idx, 'span'],
             results_df.loc[best_sortino_idx, 'sortino_ratio'],
             'r*', markersize=20, label=f"Best: {results_df.loc[best_sortino_idx, 'label']}")
    ax6.set_xlabel('EMA Span (days)')
    ax6.set_ylabel('Sortino Ratio')
    ax6.set_title('Sortino Ratio vs EMA Span')
    ax6.grid(True, alpha=0.3)
    ax6.legend()

    # 7. Average Positions vs Span
    ax7 = plt.subplot(3, 3, 7)
    ax7.plot(results_df['span'], results_df['avg_positions'], 'o-',
             linewidth=2, markersize=8, color='teal')
    ax7.set_xlabel('EMA Span (days)')
    ax7.set_ylabel('Average Positions')
    ax7.set_title('Portfolio Concentration vs EMA Span')
    ax7.grid(True, alpha=0.3)

    # 8. Performance Metrics Comparison (Bar Chart)
    ax8 = plt.subplot(3, 3, 8)
    x = np.arange(len(results_df))
    width = 0.35
    ax8.bar(x - width/2, results_df['sharpe_ratio'], width, label='Sharpe', alpha=0.8)
    ax8.bar(x + width/2, results_df['sortino_ratio'], width, label='Sortino', alpha=0.8)
    ax8.set_xlabel('EMA Span')
    ax8.set_ylabel('Ratio')
    ax8.set_title('Sharpe vs Sortino Across Spans')
    ax8.set_xticks(x)
    ax8.set_xticklabels(results_df['label'], rotation=45)
    ax8.legend()
    ax8.grid(True, alpha=0.3, axis='y')

    # 9. Robustness Summary (Text)
    ax9 = plt.subplot(3, 3, 9)
    ax9.axis('off')

    robustness_text = f"""
ROBUSTNESS ANALYSIS

Sharpe Ratio:
  Mean: {results_df['sharpe_ratio'].mean():.3f}
  Std Dev: {results_df['sharpe_ratio'].std():.3f}
  CV: {robustness['sharpe_cv']:.1f}%
  Range: {robustness['sharpe_range']:.3f}

Annualized Return:
  Mean: {results_df['annualized_return'].mean()*100:.1f}%
  Std Dev: {results_df['annualized_return'].std()*100:.1f}%
  CV: {robustness['return_cv']:.1f}%
  Range: {robustness['return_range']*100:.1f}%

Interpretation:
  CV < 10%: Robust (low overfitting)
  CV 10-20%: Moderate stability
  CV > 20%: High parameter sensitivity

Current Sharpe CV: {robustness['sharpe_cv']:.1f}%
Status: {"ROBUST" if robustness['sharpe_cv'] < 10 else "MODERATE" if robustness['sharpe_cv'] < 20 else "SENSITIVE"}
"""
    ax9.text(0.1, 0.5, robustness_text, fontsize=10, family='monospace',
             verticalalignment='center')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nVisualization saved to: {output_path}")
    plt.close()


def main():
    """Main execution function."""
    print("=" * 70)
    print("EMA SPAN PARAMETER OPTIMIZATION")
    print("=" * 70)

    # Load data
    data_path = project_root / 'data' / 'processed' / 'prices_clean.csv'
    prices = pd.read_csv(data_path, index_col=0, parse_dates=True)

    print(f"\nData loaded: {prices.shape[0]} days, {prices.shape[1]} assets")
    print(f"Date range: {prices.index.min().date()} to {prices.index.max().date()}")

    # Define spans to test (3M, 6M, 9M, 12M, 15M, 18M)
    spans_to_test = [63, 126, 189, 252, 315, 378]

    print(f"\nTesting {len(spans_to_test)} EMA spans: {spans_to_test}")
    print("-" * 70)

    # Run optimization
    results_df = optimize_ema_span(prices, spans_to_test)

    # Analyze robustness
    robustness = analyze_robustness(results_df)

    # Display results
    print("\n" + "=" * 70)
    print("OPTIMIZATION RESULTS")
    print("=" * 70)
    print(results_df[['label', 'total_return', 'annualized_return', 'annualized_volatility',
                      'sharpe_ratio', 'sortino_ratio', 'max_drawdown', 'calmar_ratio',
                      'avg_positions']].to_string(index=False, float_format='%.4f'))

    # Save results
    output_dir = project_root / 'outputs'
    csv_path = output_dir / 'ema_optimization_results.csv'
    results_df.to_csv(csv_path, index=False)
    print(f"\nResults saved to: {csv_path}")

    # Create visualization
    plot_path = output_dir / 'ema_optimization.png'
    plot_optimization_results(results_df, robustness, plot_path)

    # Print key insights
    print("\n" + "=" * 70)
    print("KEY INSIGHTS")
    print("=" * 70)

    best_sharpe_idx = results_df['sharpe_ratio'].idxmax()
    best_sharpe = results_df.loc[best_sharpe_idx]

    print(f"\nBest Sharpe Ratio: {best_sharpe['label']} ({best_sharpe['span']} days)")
    print(f"  Sharpe: {best_sharpe['sharpe_ratio']:.3f}")
    print(f"  Return: {best_sharpe['annualized_return']*100:.2f}%")
    print(f"  Max DD: {best_sharpe['max_drawdown']*100:.2f}%")
    print(f"  Calmar: {best_sharpe['calmar_ratio']:.3f}")

    best_return_idx = results_df['total_return'].idxmax()
    best_return = results_df.loc[best_return_idx]

    print(f"\nHighest Total Return: {best_return['label']} ({best_return['span']} days)")
    print(f"  Return: {best_return['total_return']*100:.1f}%")
    print(f"  Sharpe: {best_return['sharpe_ratio']:.3f}")

    best_dd_idx = results_df['max_drawdown'].idxmax()
    best_dd = results_df.loc[best_dd_idx]

    print(f"\nBest Drawdown Control: {best_dd['label']} ({best_dd['span']} days)")
    print(f"  Max DD: {best_dd['max_drawdown']*100:.2f}%")
    print(f"  Sharpe: {best_dd['sharpe_ratio']:.3f}")

    # Robustness analysis
    print("\n" + "-" * 70)
    print("ROBUSTNESS ANALYSIS")
    print("-" * 70)
    print(f"Sharpe Ratio CV: {robustness['sharpe_cv']:.2f}%")
    print(f"Return CV: {robustness['return_cv']:.2f}%")
    print(f"Sharpe Range: {robustness['sharpe_range']:.3f}")

    if robustness['sharpe_cv'] < 10:
        print("\nROBUST: Low parameter sensitivity, minimal overfitting risk")
    elif robustness['sharpe_cv'] < 20:
        print("\nMODERATE: Some parameter sensitivity, acceptable robustness")
    else:
        print("\nSENSITIVE: High parameter sensitivity, overfitting risk present")

    # Recommendation
    print("\n" + "=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)

    # Compare top performers
    top_3 = results_df.nlargest(3, 'sharpe_ratio')
    print("\nTop 3 by Sharpe Ratio:")
    for idx, row in top_3.iterrows():
        print(f"  {row['label']:15} Sharpe: {row['sharpe_ratio']:.3f}, "
              f"Return: {row['annualized_return']*100:5.1f}%, "
              f"Max DD: {row['max_drawdown']*100:5.1f}%")

    # Check if current (252d) is still optimal
    current_252 = results_df[results_df['span'] == 252].iloc[0]

    if best_sharpe['span'] == 252:
        print(f"\nCONFIRMED: EMA 252-day (12M) remains optimal")
        print(f"  No parameter change needed")
    else:
        sharpe_diff = best_sharpe['sharpe_ratio'] - current_252['sharpe_ratio']
        print(f"\nALTERNATIVE FOUND: {best_sharpe['label']} shows slightly better Sharpe")
        print(f"  Improvement: +{sharpe_diff:.3f} Sharpe")
        print(f"  Consider: Risk of overfitting vs genuine improvement")

        if sharpe_diff < 0.02:
            print(f"  Recommendation: KEEP 252-day (difference too small to justify change)")
        else:
            print(f"  Recommendation: CONSIDER switching to {best_sharpe['span']}-day span")


if __name__ == "__main__":
    main()
