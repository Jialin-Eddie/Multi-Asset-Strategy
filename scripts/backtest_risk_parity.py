"""
Backtest SMA strategy with risk parity weighting vs equal weighting.

Compares two position sizing methods:
1. Equal Weight: 1/N for N active positions
2. Risk Parity: Inverse volatility weighting
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.signals.trend_filter import generate_signals
from src.portfolio.risk_parity import apply_risk_parity_to_signals

print('=' * 80)
print('RISK PARITY vs EQUAL WEIGHT BACKTEST')
print('=' * 80)

# Load data
prices = pd.read_csv(project_root / 'data' / 'processed' / 'prices_clean.csv',
                     index_col=0, parse_dates=True)

# Generate SMA signals (252-day)
print('\nGenerating SMA signals (252-day)...')
signals = generate_signals(prices, method='sma', window=252)

# Calculate returns
returns = prices.pct_change()

# Method 1: Equal Weight
print('\n[1/2] Equal Weight Portfolio...')
ew_weights = signals.div(signals.sum(axis=1), axis=0).fillna(0)

# Method 2: Risk Parity (Inverse Volatility)
print('[2/2] Risk Parity Portfolio...')
rp_weights = apply_risk_parity_to_signals(prices, signals, method='inverse_vol', lookback=60)

# Manual backtest function with custom weights
def backtest_with_weights(prices, weights, transaction_cost=0.0005, rebalance_freq='M'):
    """Simple backtest with custom weights."""
    returns = prices.pct_change()

    # Shift weights to avoid lookahead
    weights_shifted = weights.shift(1).fillna(0)

    # Rebalance dates
    if rebalance_freq == 'M':
        rebalance_dates = pd.date_range(prices.index[0], prices.index[-1], freq='MS')
    else:
        rebalance_dates = prices.index

    # Initialize
    portfolio_value = pd.Series(100.0, index=prices.index)
    turnover = pd.Series(0.0, index=prices.index)
    prev_weights = pd.Series(0.0, index=prices.columns)

    for i in range(1, len(prices)):
        date = prices.index[i]
        prev_date = prices.index[i-1]

        # Check rebalance
        is_rebalance = date in rebalance_dates

        if is_rebalance or i == 1:
            target_weights = weights_shifted.loc[date]

            # Calculate turnover
            turnover.iloc[i] = (target_weights - prev_weights).abs().sum()

            # Transaction costs
            tc_cost = turnover.iloc[i] * transaction_cost
            portfolio_value.iloc[i] = portfolio_value.iloc[i-1] * (1 - tc_cost)

            # Update weights
            prev_weights = target_weights
        else:
            portfolio_value.iloc[i] = portfolio_value.iloc[i-1]

        # Apply returns
        period_return = (prev_weights * returns.loc[date]).sum()
        portfolio_value.iloc[i] = portfolio_value.iloc[i] * (1 + period_return)

        # Drift weights
        if not is_rebalance:
            individual_returns = returns.loc[date]
            prev_weights = prev_weights * (1 + individual_returns) / (1 + period_return)
            prev_weights = prev_weights.fillna(0)

    # Calculate portfolio returns
    portfolio_returns = portfolio_value.pct_change().fillna(0)

    return {
        'portfolio_value': portfolio_value,
        'returns': portfolio_returns,
        'turnover': turnover,
        'weights': weights
    }

# Run backtests
print('\nRunning backtests...')
ew_results = backtest_with_weights(prices, ew_weights)
rp_results = backtest_with_weights(prices, rp_weights)

# Calculate performance metrics
def calc_metrics(returns):
    """Calculate performance metrics."""
    cum_returns = (1 + returns).cumprod()
    total_return = cum_returns.iloc[-1] - 1
    n_years = len(returns) / 252
    ann_return = (1 + total_return) ** (1 / n_years) - 1
    ann_vol = returns.std() * np.sqrt(252)
    sharpe = ann_return / ann_vol if ann_vol > 0 else 0

    # Drawdown
    running_max = cum_returns.expanding().max()
    drawdown = (cum_returns - running_max) / running_max
    max_dd = drawdown.min()

    # Sortino
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() * np.sqrt(252)
    sortino = ann_return / downside_std if downside_std > 0 else 0

    # Calmar
    calmar = ann_return / abs(max_dd) if max_dd < 0 else 0

    return {
        'total_return': total_return,
        'annualized_return': ann_return,
        'annualized_volatility': ann_vol,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'max_drawdown': max_dd,
        'calmar_ratio': calmar
    }

ew_metrics = calc_metrics(ew_results['returns'])
rp_metrics = calc_metrics(rp_results['returns'])

# Print results
print('\n' + '=' * 80)
print('PERFORMANCE COMPARISON')
print('=' * 80)

comparison = pd.DataFrame({
    'Equal Weight': ew_metrics,
    'Risk Parity': rp_metrics
}).T

print('\n', comparison.to_string())

# Calculate differences
print('\n' + '=' * 80)
print('RISK PARITY vs EQUAL WEIGHT')
print('=' * 80)

metrics_to_compare = [
    ('Total Return', 'total_return', '%'),
    ('Annualized Return', 'annualized_return', '%'),
    ('Volatility', 'annualized_volatility', '%'),
    ('Sharpe Ratio', 'sharpe_ratio', 'ratio'),
    ('Sortino Ratio', 'sortino_ratio', 'ratio'),
    ('Max Drawdown', 'max_drawdown', '%'),
    ('Calmar Ratio', 'calmar_ratio', 'ratio')
]

for label, key, fmt in metrics_to_compare:
    rp_val = rp_metrics[key]
    ew_val = ew_metrics[key]
    diff = rp_val - ew_val

    if fmt == '%':
        print(f'{label:.<30} RP: {rp_val:>7.2%} | EW: {ew_val:>7.2%} | Diff: {diff:>+7.2%}')
    else:
        print(f'{label:.<30} RP: {rp_val:>7.2f} | EW: {ew_val:>7.2f} | Diff: {diff:>+7.2f}')

# Turnover comparison
ew_turnover = ew_results['turnover'].resample('ME').sum().mean()
rp_turnover = rp_results['turnover'].resample('ME').sum().mean()

print(f'\n{"Monthly Turnover":.<30} RP: {rp_turnover:>7.2%} | EW: {ew_turnover:>7.2%} | Diff: {(rp_turnover - ew_turnover):>+7.2%}')

# Weight analysis
print('\n' + '=' * 80)
print('WEIGHT ALLOCATION ANALYSIS')
print('=' * 80)

print('\n=== Average Weights (when position active) ===')
ew_avg_weights = ew_weights[ew_weights > 0].mean()
rp_avg_weights = rp_weights[rp_weights > 0].mean()

weight_comp = pd.DataFrame({
    'Equal Weight': ew_avg_weights,
    'Risk Parity': rp_avg_weights,
    'Difference': rp_avg_weights - ew_avg_weights
}).sort_values('Risk Parity', ascending=False)

print(weight_comp.to_string())

print('\n=== Volatility (60-day rolling, annualized) ===')
vol_60d = returns.rolling(60).std().mean() * np.sqrt(252)
print(vol_60d.sort_values().to_string())

print('\nRisk parity allocates MORE to LOW volatility assets')
print('Equal weight allocates SAME to ALL active assets')

# Save results
output_dir = project_root / 'outputs'
comparison.to_csv(output_dir / 'risk_parity_comparison.csv')
print(f'\nSaved comparison to {output_dir / "risk_parity_comparison.csv"}')

# Visualization
fig = plt.figure(figsize=(18, 12))
gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

# 1. Cumulative returns
ax1 = fig.add_subplot(gs[0, :2])
ew_cum = (1 + ew_results['returns']).cumprod()
rp_cum = (1 + rp_results['returns']).cumprod()

ax1.plot(ew_cum.index, ew_cum, label='Equal Weight', linewidth=2.5, color='blue', alpha=0.9)
ax1.plot(rp_cum.index, rp_cum, label='Risk Parity', linewidth=2.5, color='green', alpha=0.9)
ax1.set_title('Cumulative Returns: Risk Parity vs Equal Weight', fontsize=14, fontweight='bold')
ax1.set_ylabel('Cumulative Return (Initial = 1.0)', fontsize=11)
ax1.legend(loc='upper left', fontsize=11)
ax1.grid(True, alpha=0.3)

textstr = f"Final Values:\nEW: {ew_cum.iloc[-1]:.2f} ({ew_metrics['total_return']:.1%})\nRP: {rp_cum.iloc[-1]:.2f} ({rp_metrics['total_return']:.1%})"
ax1.text(0.02, 0.98, textstr, transform=ax1.transAxes, fontsize=10,
        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

# 2. Performance metrics comparison
ax2 = fig.add_subplot(gs[0, 2])
metrics_plot = ['annualized_return', 'sharpe_ratio', 'calmar_ratio']
labels = ['Ann. Return\n(%)', 'Sharpe\n(x10)', 'Calmar\n(x10)']
ew_vals = [ew_metrics['annualized_return'] * 100,
           ew_metrics['sharpe_ratio'] * 10,
           ew_metrics['calmar_ratio'] * 10]
rp_vals = [rp_metrics['annualized_return'] * 100,
           rp_metrics['sharpe_ratio'] * 10,
           rp_metrics['calmar_ratio'] * 10]

x = np.arange(len(labels))
width = 0.35
bars1 = ax2.bar(x - width/2, ew_vals, width, label='EW', color='blue', alpha=0.8)
bars2 = ax2.bar(x + width/2, rp_vals, width, label='RP', color='green', alpha=0.8)

ax2.set_xticks(x)
ax2.set_xticklabels(labels, fontsize=9)
ax2.set_title('Key Metrics', fontsize=12, fontweight='bold')
ax2.legend(fontsize=9)
ax2.grid(True, alpha=0.3, axis='y')

for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}', ha='center', va='bottom', fontsize=8)

# 3. Drawdown comparison
ax3 = fig.add_subplot(gs[1, :])
ew_cum_val = (1 + ew_results['returns']).cumprod()
rp_cum_val = (1 + rp_results['returns']).cumprod()
ew_dd = (ew_cum_val - ew_cum_val.expanding().max()) / ew_cum_val.expanding().max()
rp_dd = (rp_cum_val - rp_cum_val.expanding().max()) / rp_cum_val.expanding().max()

ax3.fill_between(ew_dd.index, 0, ew_dd * 100, alpha=0.5, color='blue', label='Equal Weight')
ax3.fill_between(rp_dd.index, 0, rp_dd * 100, alpha=0.5, color='green', label='Risk Parity')
ax3.set_title('Drawdown Comparison', fontsize=13, fontweight='bold')
ax3.set_ylabel('Drawdown (%)', fontsize=11)
ax3.legend(loc='lower left', fontsize=10)
ax3.grid(True, alpha=0.3)

textstr = f"Max DD:\nEW: {ew_metrics['max_drawdown']:.1%}\nRP: {rp_metrics['max_drawdown']:.1%}"
ax3.text(0.98, 0.95, textstr, transform=ax3.transAxes, fontsize=9,
        verticalalignment='top', horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

# 4. Rolling Sharpe
ax4 = fig.add_subplot(gs[2, 0])
window = 252
ew_sharpe = (ew_results['returns'].rolling(window).mean() /
             ew_results['returns'].rolling(window).std()) * np.sqrt(252)
rp_sharpe = (rp_results['returns'].rolling(window).mean() /
             rp_results['returns'].rolling(window).std()) * np.sqrt(252)

ax4.plot(ew_sharpe.index, ew_sharpe, label='EW', linewidth=1.5, color='blue', alpha=0.8)
ax4.plot(rp_sharpe.index, rp_sharpe, label='RP', linewidth=1.5, color='green', alpha=0.8)
ax4.axhline(y=0, color='red', linestyle='-', linewidth=0.5)
ax4.axhline(y=1.0, color='black', linestyle='--', linewidth=0.5, alpha=0.3)
ax4.set_title('Rolling 12M Sharpe', fontsize=11, fontweight='bold')
ax4.set_ylabel('Sharpe Ratio', fontsize=10)
ax4.legend(fontsize=9)
ax4.grid(True, alpha=0.3)

# 5. Weight distribution over time
ax5 = fig.add_subplot(gs[2, 1])
rp_avg = rp_weights[rp_weights > 0].mean().sort_values(ascending=False)
ew_avg = ew_weights[ew_weights > 0].mean()[rp_avg.index]

x = np.arange(len(rp_avg))
width = 0.35
ax5.bar(x - width/2, ew_avg.values, width, label='EW', color='blue', alpha=0.8)
ax5.bar(x + width/2, rp_avg.values, width, label='RP', color='green', alpha=0.8)

ax5.set_xticks(x)
ax5.set_xticklabels(rp_avg.index, fontsize=9)
ax5.set_title('Average Weights (when active)', fontsize=11, fontweight='bold')
ax5.set_ylabel('Weight', fontsize=10)
ax5.legend(fontsize=9)
ax5.grid(True, alpha=0.3, axis='y')

# 6. Monthly return scatter
ax6 = fig.add_subplot(gs[2, 2])
ew_monthly = ew_results['returns'].resample('ME').sum()
rp_monthly = rp_results['returns'].resample('ME').sum()

ax6.scatter(ew_monthly * 100, rp_monthly * 100, alpha=0.5, s=20)
ax6.plot([-10, 15], [-10, 15], 'r--', linewidth=1)
ax6.set_xlabel('EW Monthly Return (%)', fontsize=10)
ax6.set_ylabel('RP Monthly Return (%)', fontsize=10)
ax6.set_title('Monthly Return Scatter', fontsize=11, fontweight='bold')
ax6.grid(True, alpha=0.3)
ax6.axhline(y=0, color='black', linewidth=0.5)
ax6.axvline(x=0, color='black', linewidth=0.5)

corr = ew_monthly.corr(rp_monthly)
ax6.text(0.05, 0.95, f'Correlation: {corr:.3f}', transform=ax6.transAxes,
        fontsize=9, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))

fig.suptitle('SMA Trend Strategy: Risk Parity vs Equal Weight Comparison',
             fontsize=16, fontweight='bold', y=0.998)

plt.savefig(output_dir / 'risk_parity_vs_equal_weight.png', dpi=300, bbox_inches='tight')
print(f'Saved visualization to {output_dir / "risk_parity_vs_equal_weight.png"}')

# Winner determination
print('\n' + '=' * 80)
print('VERDICT')
print('=' * 80)

scores = {'Equal Weight': 0, 'Risk Parity': 0}

# Compare metrics
if rp_metrics['annualized_return'] > ew_metrics['annualized_return']:
    scores['Risk Parity'] += 1
    print('✓ Risk Parity wins on Annualized Return')
else:
    scores['Equal Weight'] += 1
    print('✓ Equal Weight wins on Annualized Return')

if rp_metrics['sharpe_ratio'] > ew_metrics['sharpe_ratio']:
    scores['Risk Parity'] += 1
    print('✓ Risk Parity wins on Sharpe Ratio')
else:
    scores['Equal Weight'] += 1
    print('✓ Equal Weight wins on Sharpe Ratio')

if abs(rp_metrics['max_drawdown']) < abs(ew_metrics['max_drawdown']):
    scores['Risk Parity'] += 1
    print('✓ Risk Parity wins on Max Drawdown (lower)')
else:
    scores['Equal Weight'] += 1
    print('✓ Equal Weight wins on Max Drawdown')

if rp_metrics['calmar_ratio'] > ew_metrics['calmar_ratio']:
    scores['Risk Parity'] += 1
    print('✓ Risk Parity wins on Calmar Ratio')
else:
    scores['Equal Weight'] += 1
    print('✓ Equal Weight wins on Calmar Ratio')

print(f'\nFinal Score: Equal Weight {scores["Equal Weight"]} - {scores["Risk Parity"]} Risk Parity')

if scores['Risk Parity'] > scores['Equal Weight']:
    print('\n🏆 WINNER: Risk Parity')
elif scores['Equal Weight'] > scores['Risk Parity']:
    print('\n🏆 WINNER: Equal Weight')
else:
    print('\n🤝 TIE: Both methods perform similarly')

print('\n' + '=' * 80)
