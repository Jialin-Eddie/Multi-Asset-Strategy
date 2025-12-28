"""
Optimize SMA lookback period for trend-following strategy.

Tests multiple lookback windows to find optimal parameter while
being mindful of overfitting risks.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.signals.trend_filter import generate_signals
from src.backtest.engine import backtest_strategy

print('=' * 80)
print('SMA LOOKBACK PERIOD OPTIMIZATION')
print('=' * 80)

# Load data
prices = pd.read_csv(project_root / 'data' / 'processed' / 'prices_clean.csv',
                     index_col=0, parse_dates=True)

# Define lookback periods to test
# 63 = 3 months, 126 = 6 months, 189 = 9 months, 252 = 12 months,
# 315 = 15 months, 378 = 18 months
lookback_periods = [63, 126, 189, 252, 315, 378]
period_labels = {
    63: '3M',
    126: '6M',
    189: '9M',
    252: '12M (baseline)',
    315: '15M',
    378: '18M'
}

print(f'\nTesting {len(lookback_periods)} lookback periods:')
for period in lookback_periods:
    print(f'  - {period} days ({period_labels[period]})')

# Store results
results = {}
performance_summary = []

# Run backtests for each lookback period
print('\nRunning backtests...')
for i, lookback in enumerate(lookback_periods, 1):
    print(f'\n[{i}/{len(lookback_periods)}] Testing {lookback}-day SMA ({period_labels[lookback]})...')

    # Generate signals
    signals = generate_signals(prices, method='sma', window=lookback)

    # Run backtest
    result = backtest_strategy(
        prices=prices,
        signals=signals,
        transaction_cost=0.0005,
        rebalance_frequency='M'
    )

    # Store results
    results[lookback] = result

    # Extract key metrics
    metrics = result['performance_metrics']
    stats = result['portfolio_stats']

    performance_summary.append({
        'lookback': lookback,
        'label': period_labels[lookback],
        'total_return': metrics['total_return'],
        'annualized_return': metrics['annualized_return'],
        'volatility': metrics['annualized_volatility'],
        'sharpe_ratio': metrics['sharpe_ratio'],
        'sortino_ratio': metrics['sortino_ratio'],
        'max_drawdown': metrics['max_drawdown'],
        'calmar_ratio': metrics['calmar_ratio'],
        'win_rate': metrics['win_rate'],
        'avg_positions': stats['positions'].mean(),
        'avg_turnover': stats['turnover'].resample('ME').sum().mean()
    })

    print(f'  Return: {metrics["total_return"]:.1%} | Sharpe: {metrics["sharpe_ratio"]:.2f} | Max DD: {metrics["max_drawdown"]:.1%}')

# Create summary DataFrame
summary_df = pd.DataFrame(performance_summary)
summary_df = summary_df.set_index('lookback')

print('\n' + '=' * 80)
print('OPTIMIZATION RESULTS SUMMARY')
print('=' * 80)
print(summary_df.to_string())

# Find optimal parameters
print('\n' + '=' * 80)
print('OPTIMAL PARAMETERS BY METRIC')
print('=' * 80)

metrics_to_optimize = {
    'Total Return': 'total_return',
    'Sharpe Ratio': 'sharpe_ratio',
    'Calmar Ratio': 'calmar_ratio',
    'Sortino Ratio': 'sortino_ratio',
    'Min Drawdown': 'max_drawdown'
}

for metric_name, metric_col in metrics_to_optimize.items():
    if metric_col == 'max_drawdown':
        # For drawdown, smaller absolute value is better
        optimal_idx = summary_df[metric_col].abs().idxmin()
        optimal_val = summary_df.loc[optimal_idx, metric_col]
        print(f'{metric_name:.<25} {optimal_idx} days ({period_labels[optimal_idx]}): {optimal_val:.2%}')
    else:
        optimal_idx = summary_df[metric_col].idxmax()
        optimal_val = summary_df.loc[optimal_idx, metric_col]
        if 'ratio' in metric_col.lower():
            print(f'{metric_name:.<25} {optimal_idx} days ({period_labels[optimal_idx]}): {optimal_val:.2f}')
        else:
            print(f'{metric_name:.<25} {optimal_idx} days ({period_labels[optimal_idx]}): {optimal_val:.2%}')

# Save results
output_dir = project_root / 'outputs'
summary_df.to_csv(output_dir / 'sma_optimization_results.csv')
print(f'\nSaved results to {output_dir / "sma_optimization_results.csv"}')

# Create comprehensive visualization
fig = plt.figure(figsize=(18, 12))
gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

# Color map for different lookbacks
colors = plt.cm.viridis(np.linspace(0, 1, len(lookback_periods)))

# 1. Cumulative returns comparison (large, spans 2 columns)
ax1 = fig.add_subplot(gs[0, :2])
for i, lookback in enumerate(lookback_periods):
    cum_returns = (1 + results[lookback]['portfolio_stats']['returns']).cumprod()
    label = f'{lookback}d ({period_labels[lookback]})'
    linewidth = 2.5 if lookback == 252 else 1.5
    alpha = 1.0 if lookback == 252 else 0.7
    ax1.plot(cum_returns.index, cum_returns, label=label,
             linewidth=linewidth, color=colors[i], alpha=alpha)

ax1.set_title('Cumulative Returns: All Lookback Periods', fontsize=14, fontweight='bold')
ax1.set_ylabel('Cumulative Return (Initial = 1.0)', fontsize=11)
ax1.legend(loc='upper left', fontsize=9)
ax1.grid(True, alpha=0.3)
ax1.axhline(y=1.0, color='black', linestyle='-', linewidth=0.5)

# Highlight baseline (252 days)
textstr = f'Baseline (252d): {results[252]["performance_metrics"]["total_return"]:.1%}'
ax1.text(0.02, 0.98, textstr, transform=ax1.transAxes, fontsize=10,
        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

# 2. Sharpe ratio by lookback
ax2 = fig.add_subplot(gs[0, 2])
sharpes = summary_df['sharpe_ratio']
bars = ax2.bar(range(len(sharpes)), sharpes.values, color=colors, alpha=0.8, edgecolor='black')
# Highlight best
best_idx = sharpes.idxmax()
best_pos = lookback_periods.index(best_idx)
bars[best_pos].set_color('gold')
bars[best_pos].set_edgecolor('red')
bars[best_pos].set_linewidth(2)

ax2.set_xticks(range(len(lookback_periods)))
ax2.set_xticklabels([period_labels[p] for p in lookback_periods], fontsize=9)
ax2.set_title('Sharpe Ratio by Lookback', fontsize=12, fontweight='bold')
ax2.set_ylabel('Sharpe Ratio', fontsize=10)
ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax2.grid(True, alpha=0.3, axis='y')

# Add values on bars
for i, (bar, val) in enumerate(zip(bars, sharpes.values)):
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
            f'{val:.2f}', ha='center', va='bottom', fontsize=8)

# 3. Max drawdown by lookback
ax3 = fig.add_subplot(gs[1, 0])
drawdowns = summary_df['max_drawdown'].abs() * 100
bars = ax3.bar(range(len(drawdowns)), drawdowns.values, color=colors, alpha=0.8, edgecolor='black')
# Highlight best (lowest)
best_idx = summary_df['max_drawdown'].abs().idxmin()
best_pos = lookback_periods.index(best_idx)
bars[best_pos].set_color('lightgreen')
bars[best_pos].set_edgecolor('darkgreen')
bars[best_pos].set_linewidth(2)

ax3.set_xticks(range(len(lookback_periods)))
ax3.set_xticklabels([period_labels[p] for p in lookback_periods], fontsize=9)
ax3.set_title('Max Drawdown by Lookback', fontsize=12, fontweight='bold')
ax3.set_ylabel('Max Drawdown (%)', fontsize=10)
ax3.grid(True, alpha=0.3, axis='y')

for i, (bar, val) in enumerate(zip(bars, drawdowns.values)):
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height,
            f'{val:.1f}%', ha='center', va='bottom', fontsize=8)

# 4. Annualized return by lookback
ax4 = fig.add_subplot(gs[1, 1])
ann_returns = summary_df['annualized_return'] * 100
bars = ax4.bar(range(len(ann_returns)), ann_returns.values, color=colors, alpha=0.8, edgecolor='black')
best_idx = ann_returns.idxmax()
best_pos = lookback_periods.index(best_idx)
bars[best_pos].set_color('gold')
bars[best_pos].set_edgecolor('red')
bars[best_pos].set_linewidth(2)

ax4.set_xticks(range(len(lookback_periods)))
ax4.set_xticklabels([period_labels[p] for p in lookback_periods], fontsize=9)
ax4.set_title('Annualized Return by Lookback', fontsize=12, fontweight='bold')
ax4.set_ylabel('Annualized Return (%)', fontsize=10)
ax4.grid(True, alpha=0.3, axis='y')

for i, (bar, val) in enumerate(zip(bars, ann_returns.values)):
    height = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2., height,
            f'{val:.1f}%', ha='center', va='bottom', fontsize=8)

# 5. Calmar ratio by lookback
ax5 = fig.add_subplot(gs[1, 2])
calmars = summary_df['calmar_ratio']
bars = ax5.bar(range(len(calmars)), calmars.values, color=colors, alpha=0.8, edgecolor='black')
best_idx = calmars.idxmax()
best_pos = lookback_periods.index(best_idx)
bars[best_pos].set_color('gold')
bars[best_pos].set_edgecolor('red')
bars[best_pos].set_linewidth(2)

ax5.set_xticks(range(len(lookback_periods)))
ax5.set_xticklabels([period_labels[p] for p in lookback_periods], fontsize=9)
ax5.set_title('Calmar Ratio by Lookback', fontsize=12, fontweight='bold')
ax5.set_ylabel('Calmar Ratio', fontsize=10)
ax5.grid(True, alpha=0.3, axis='y')

for i, (bar, val) in enumerate(zip(bars, calmars.values)):
    height = bar.get_height()
    ax5.text(bar.get_x() + bar.get_width()/2., height,
            f'{val:.2f}', ha='center', va='bottom', fontsize=8)

# 6. Return vs Risk scatter
ax6 = fig.add_subplot(gs[2, 0])
for i, lookback in enumerate(lookback_periods):
    ret = summary_df.loc[lookback, 'annualized_return'] * 100
    vol = summary_df.loc[lookback, 'volatility'] * 100
    label = period_labels[lookback]
    size = 200 if lookback == 252 else 100
    ax6.scatter(vol, ret, s=size, color=colors[i], alpha=0.8, edgecolors='black', linewidths=1.5)
    ax6.annotate(label, (vol, ret), fontsize=8, ha='center', va='bottom')

ax6.set_xlabel('Volatility (%)', fontsize=10)
ax6.set_ylabel('Annualized Return (%)', fontsize=10)
ax6.set_title('Return vs Risk', fontsize=12, fontweight='bold')
ax6.grid(True, alpha=0.3)

# 7. Average positions by lookback
ax7 = fig.add_subplot(gs[2, 1])
avg_pos = summary_df['avg_positions']
ax7.bar(range(len(avg_pos)), avg_pos.values, color=colors, alpha=0.8, edgecolor='black')
ax7.set_xticks(range(len(lookback_periods)))
ax7.set_xticklabels([period_labels[p] for p in lookback_periods], fontsize=9)
ax7.set_title('Average Positions Held', fontsize=12, fontweight='bold')
ax7.set_ylabel('Number of Positions', fontsize=10)
ax7.set_ylim([0, 5.5])
ax7.grid(True, alpha=0.3, axis='y')

# 8. Metric sensitivity heatmap
ax8 = fig.add_subplot(gs[2, 2])
# Normalize metrics to 0-100 scale for comparison
norm_metrics = pd.DataFrame({
    'Return': (summary_df['annualized_return'] - summary_df['annualized_return'].min()) / (summary_df['annualized_return'].max() - summary_df['annualized_return'].min()) * 100,
    'Sharpe': (summary_df['sharpe_ratio'] - summary_df['sharpe_ratio'].min()) / (summary_df['sharpe_ratio'].max() - summary_df['sharpe_ratio'].min()) * 100,
    'DD Control': (summary_df['max_drawdown'].abs().max() - summary_df['max_drawdown'].abs()) / (summary_df['max_drawdown'].abs().max() - summary_df['max_drawdown'].abs().min()) * 100,
    'Calmar': (summary_df['calmar_ratio'] - summary_df['calmar_ratio'].min()) / (summary_df['calmar_ratio'].max() - summary_df['calmar_ratio'].min()) * 100
})

im = ax8.imshow(norm_metrics.T.values, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)
ax8.set_xticks(range(len(lookback_periods)))
ax8.set_xticklabels([period_labels[p] for p in lookback_periods], fontsize=9)
ax8.set_yticks(range(len(norm_metrics.columns)))
ax8.set_yticklabels(norm_metrics.columns, fontsize=9)
ax8.set_title('Performance Heatmap\n(0=worst, 100=best)', fontsize=11, fontweight='bold')

# Add text annotations
for i in range(len(lookback_periods)):
    for j in range(len(norm_metrics.columns)):
        text = ax8.text(i, j, f'{norm_metrics.iloc[i, j]:.0f}',
                       ha="center", va="center", color="black", fontsize=8)

plt.colorbar(im, ax=ax8, fraction=0.046, pad=0.04)

fig.suptitle('SMA Lookback Period Optimization (63 to 378 days)',
             fontsize=16, fontweight='bold', y=0.998)

plt.savefig(output_dir / 'sma_optimization.png', dpi=300, bbox_inches='tight')
print(f'Saved visualization to {output_dir / "sma_optimization.png"}')

# Robustness analysis
print('\n' + '=' * 80)
print('ROBUSTNESS ANALYSIS')
print('=' * 80)

sharpe_std = summary_df['sharpe_ratio'].std()
sharpe_mean = summary_df['sharpe_ratio'].mean()
sharpe_cv = sharpe_std / sharpe_mean

print(f'\nSharpe Ratio Statistics:')
print(f'  Mean: {sharpe_mean:.3f}')
print(f'  Std Dev: {sharpe_std:.3f}')
print(f'  Coefficient of Variation: {sharpe_cv:.1%}')
print(f'  Range: {summary_df["sharpe_ratio"].min():.3f} to {summary_df["sharpe_ratio"].max():.3f}')

if sharpe_cv < 0.10:
    print('\n  ✓ Low sensitivity: Results robust across lookback periods')
elif sharpe_cv < 0.20:
    print('\n  ~ Moderate sensitivity: Some parameter dependence')
else:
    print('\n  ✗ High sensitivity: Significant overfitting risk')

# Recommendation
print('\n' + '=' * 80)
print('RECOMMENDATION')
print('=' * 80)

best_sharpe_period = summary_df['sharpe_ratio'].idxmax()
best_calmar_period = summary_df['calmar_ratio'].idxmax()
best_dd_period = summary_df['max_drawdown'].abs().idxmin()

print(f'\nBest by Sharpe: {best_sharpe_period} days ({period_labels[best_sharpe_period]})')
print(f'Best by Calmar: {best_calmar_period} days ({period_labels[best_calmar_period]})')
print(f'Best by Drawdown: {best_dd_period} days ({period_labels[best_dd_period]})')

if best_sharpe_period == best_calmar_period == best_dd_period:
    print(f'\n✓ CLEAR WINNER: {best_sharpe_period} days ({period_labels[best_sharpe_period]})')
    print('  All major metrics agree on optimal parameter')
elif best_sharpe_period == 252:
    print('\n✓ BASELINE OPTIMAL: 252 days (12 months)')
    print('  Original choice validated by optimization')
else:
    print(f'\n⚠ MIXED RESULTS: Different metrics favor different periods')
    print(f'  Recommend: {best_sharpe_period} days for risk-adjusted returns')
    print(f'  Or stick with 252 days (12M) as industry standard')

print('\n' + '=' * 80)
