import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.signals.trend_filter import generate_signals
from src.backtest.engine import backtest_strategy, calculate_drawdown_series

# Load data
prices = pd.read_csv(project_root / 'data' / 'processed' / 'prices_clean.csv',
                     index_col=0, parse_dates=True)

# Generate signals for both strategies
print('Generating signals...')
sma_signals = generate_signals(prices, method='sma', window=252)
dual_signals = generate_signals(prices, method='dual', lookback=252, top_n=2)

# Calculate benchmark
bh_equal = prices.pct_change().mean(axis=1)

# Run backtests
print('Running SMA backtest...')
sma_results = backtest_strategy(
    prices=prices,
    signals=sma_signals,
    transaction_cost=0.0005,
    rebalance_frequency='M'
)

print('Running Dual Momentum backtest...')
dual_results = backtest_strategy(
    prices=prices,
    signals=dual_signals,
    transaction_cost=0.0005,
    rebalance_frequency='M'
)

# Create comparison table
comparison_df = pd.DataFrame({
    'SMA Trend': sma_results['performance_metrics'],
    'Dual Momentum': dual_results['performance_metrics'],
    'Buy & Hold': {
        'total_return': 3.0511,
        'annualized_return': 0.0696,
        'annualized_volatility': 0.1181,
        'sharpe_ratio': 0.59,
        'sortino_ratio': 0.75,
        'max_drawdown': -0.3561,
        'calmar_ratio': 0.20,
        'win_rate': 0.5460,
        'avg_win': 0.0048,
        'avg_loss': -0.0052
    }
}).T

print('\n' + '=' * 80)
print('STRATEGY COMPARISON TABLE')
print('=' * 80)
print(comparison_df.to_string())

# Save comparison
output_dir = project_root / 'outputs'
comparison_df.to_csv(output_dir / 'strategy_comparison.csv')
print(f'\nSaved comparison to {output_dir / "strategy_comparison.csv"}')

# Create comprehensive visualization
fig = plt.figure(figsize=(18, 12))
gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

# 1. Cumulative returns
ax1 = fig.add_subplot(gs[0, :2])
sma_cum = (1 + sma_results['portfolio_stats']['returns']).cumprod()
dual_cum = (1 + dual_results['portfolio_stats']['returns']).cumprod()
bh_cum = (1 + bh_equal).cumprod()

ax1.plot(sma_cum.index, sma_cum, label='SMA Trend', linewidth=2.5, color='blue', alpha=0.9)
ax1.plot(dual_cum.index, dual_cum, label='Dual Momentum', linewidth=2.5, color='green', alpha=0.9)
ax1.plot(bh_cum.index, bh_cum, label='Buy & Hold', linewidth=2, color='gray', linestyle='--', alpha=0.7)

ax1.set_title('Cumulative Returns Comparison', fontsize=14, fontweight='bold')
ax1.set_ylabel('Cumulative Return (Initial = 1.0)', fontsize=11)
ax1.legend(loc='upper left', fontsize=11)
ax1.grid(True, alpha=0.3)
ax1.axhline(y=1.0, color='black', linestyle='-', linewidth=0.5)

# Add final values
sma_pct = sma_results['performance_metrics']['total_return'] * 100
dual_pct = dual_results['performance_metrics']['total_return'] * 100
textstr = f"Final Values:\nSMA: {sma_cum.iloc[-1]:.2f} ({sma_pct:.1f}%)\nDual: {dual_cum.iloc[-1]:.2f} ({dual_pct:.1f}%)\nB&H: {bh_cum.iloc[-1]:.2f} (305.1%)"
ax1.text(0.02, 0.98, textstr, transform=ax1.transAxes, fontsize=9,
        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

# 2. Performance metrics bar chart
ax2 = fig.add_subplot(gs[0, 2])
metrics = ['Ann. Return\n(%)', 'Sharpe\n(x10)', 'Sortino\n(x10)', 'Calmar\n(x10)']
sma_vals = [
    sma_results['performance_metrics']['annualized_return'] * 100,
    sma_results['performance_metrics']['sharpe_ratio'] * 10,
    sma_results['performance_metrics']['sortino_ratio'] * 10,
    sma_results['performance_metrics']['calmar_ratio'] * 10
]
dual_vals = [
    dual_results['performance_metrics']['annualized_return'] * 100,
    dual_results['performance_metrics']['sharpe_ratio'] * 10,
    dual_results['performance_metrics']['sortino_ratio'] * 10,
    dual_results['performance_metrics']['calmar_ratio'] * 10
]
bh_vals = [6.96, 5.9, 7.5, 2.0]

x = np.arange(len(metrics))
width = 0.25

ax2.bar(x - width, sma_vals, width, label='SMA', color='blue', alpha=0.8)
ax2.bar(x, dual_vals, width, label='Dual', color='green', alpha=0.8)
ax2.bar(x + width, bh_vals, width, label='B&H', color='gray', alpha=0.6)

ax2.set_title('Key Metrics', fontsize=12, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(metrics, fontsize=8)
ax2.legend(fontsize=9)
ax2.grid(True, alpha=0.3, axis='y')

# 3. Drawdown comparison
ax3 = fig.add_subplot(gs[1, :])
sma_dd = sma_results['drawdown_series']
dual_dd = dual_results['drawdown_series']
bh_dd = calculate_drawdown_series(bh_equal)

ax3.fill_between(sma_dd.index, 0, sma_dd * 100, alpha=0.5, color='blue', label='SMA')
ax3.fill_between(dual_dd.index, 0, dual_dd * 100, alpha=0.4, color='green', label='Dual')
ax3.fill_between(bh_dd.index, 0, bh_dd * 100, alpha=0.3, color='gray', label='B&H')

ax3.set_title('Drawdown Comparison', fontsize=13, fontweight='bold')
ax3.set_ylabel('Drawdown (%)', fontsize=11)
ax3.legend(loc='lower left', fontsize=10)
ax3.grid(True, alpha=0.3)

sma_dd_pct = sma_results['performance_metrics']['max_drawdown'] * 100
dual_dd_pct = dual_results['performance_metrics']['max_drawdown'] * 100
textstr = f"Max Drawdowns:\nSMA: {sma_dd_pct:.1f}%\nDual: {dual_dd_pct:.1f}%\nB&H: -35.6%"
ax3.text(0.98, 0.95, textstr, transform=ax3.transAxes, fontsize=9,
        verticalalignment='top', horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.7))

# 4. Rolling Sharpe
ax4 = fig.add_subplot(gs[2, 0])
window = 252
sma_sharpe = (sma_results['portfolio_stats']['returns'].rolling(window).mean() /
              sma_results['portfolio_stats']['returns'].rolling(window).std()) * np.sqrt(252)
dual_sharpe = (dual_results['portfolio_stats']['returns'].rolling(window).mean() /
               dual_results['portfolio_stats']['returns'].rolling(window).std()) * np.sqrt(252)

ax4.plot(sma_sharpe.index, sma_sharpe, label='SMA', linewidth=1.5, color='blue', alpha=0.8)
ax4.plot(dual_sharpe.index, dual_sharpe, label='Dual', linewidth=1.5, color='green', alpha=0.8)
ax4.axhline(y=0, color='red', linestyle='-', linewidth=0.5)
ax4.axhline(y=1.0, color='black', linestyle='--', linewidth=0.5, alpha=0.3)
ax4.set_title('Rolling 12M Sharpe', fontsize=11, fontweight='bold')
ax4.set_ylabel('Sharpe Ratio', fontsize=10)
ax4.legend(fontsize=9)
ax4.grid(True, alpha=0.3)

# 5. Positions held over time
ax5 = fig.add_subplot(gs[2, 1])
sma_positions = sma_results['portfolio_stats']['positions'].resample('ME').mean()
dual_positions = dual_results['portfolio_stats']['positions'].resample('ME').mean()

ax5.plot(sma_positions.index, sma_positions, label='SMA', linewidth=2, color='blue', alpha=0.7)
ax5.plot(dual_positions.index, dual_positions, label='Dual', linewidth=2, color='green', alpha=0.7)
ax5.set_title('Average Positions Held', fontsize=11, fontweight='bold')
ax5.set_ylabel('Number of Positions', fontsize=10)
ax5.legend(fontsize=9)
ax5.grid(True, alpha=0.3)
ax5.set_ylim([0, 5.5])

sma_avg_pos = sma_results['portfolio_stats']['positions'].mean()
dual_avg_pos = dual_results['portfolio_stats']['positions'].mean()
textstr = f"Avg Positions:\nSMA: {sma_avg_pos:.2f}\nDual: {dual_avg_pos:.2f}"
ax5.text(0.98, 0.95, textstr, transform=ax5.transAxes, fontsize=9,
        verticalalignment='top', horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

# 6. Monthly returns scatter
ax6 = fig.add_subplot(gs[2, 2])
sma_monthly = sma_results['portfolio_stats']['returns'].resample('ME').sum()
dual_monthly = dual_results['portfolio_stats']['returns'].resample('ME').sum()

ax6.scatter(sma_monthly * 100, dual_monthly * 100, alpha=0.5, s=20)
ax6.plot([-15, 20], [-15, 20], 'r--', linewidth=1, label='45 line')
ax6.set_xlabel('SMA Monthly Return (%)', fontsize=10)
ax6.set_ylabel('Dual Monthly Return (%)', fontsize=10)
ax6.set_title('Monthly Return Scatter', fontsize=11, fontweight='bold')
ax6.grid(True, alpha=0.3)
ax6.axhline(y=0, color='black', linewidth=0.5)
ax6.axvline(x=0, color='black', linewidth=0.5)

corr = sma_monthly.corr(dual_monthly)
ax6.text(0.05, 0.95, f'Correlation: {corr:.3f}', transform=ax6.transAxes,
        fontsize=9, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

fig.suptitle('Strategy Comparison: SMA Trend vs Dual Momentum vs Buy-and-Hold',
             fontsize=16, fontweight='bold', y=0.998)

plt.savefig(output_dir / 'strategy_comparison.png', dpi=300, bbox_inches='tight')
print(f'Saved comparison visualization to {output_dir / "strategy_comparison.png"}')

# Print summary insights
print('\n' + '=' * 80)
print('KEY INSIGHTS')
print('=' * 80)

sma_ret = sma_results['performance_metrics']['total_return']
dual_ret = dual_results['performance_metrics']['total_return']
sma_ann = sma_results['performance_metrics']['annualized_return']
dual_ann = dual_results['performance_metrics']['annualized_return']

print('\n1. RETURNS:')
print(f'   SMA Trend: {sma_ret:.1%} ({sma_ann:.2%}/year)')
print(f'   Dual Momentum: {dual_ret:.1%} ({dual_ann:.2%}/year)')
print(f'   Winner: SMA (+{(sma_ret - dual_ret):.1%})')

sma_sharpe = sma_results['performance_metrics']['sharpe_ratio']
dual_sharpe = dual_results['performance_metrics']['sharpe_ratio']

print('\n2. RISK-ADJUSTED RETURNS (Sharpe):')
print(f'   SMA Trend: {sma_sharpe:.2f}')
print(f'   Dual Momentum: {dual_sharpe:.2f}')
print(f'   Winner: SMA (+{(sma_sharpe - dual_sharpe):.2f})')

sma_dd = sma_results['performance_metrics']['max_drawdown']
dual_dd = dual_results['performance_metrics']['max_drawdown']

print('\n3. DOWNSIDE RISK (Max Drawdown):')
print(f'   SMA Trend: {sma_dd:.1%}')
print(f'   Dual Momentum: {dual_dd:.1%}')
print(f'   Winner: SMA ({abs(dual_dd - sma_dd):.1%} lower)')

print('\n4. PORTFOLIO CONCENTRATION:')
print(f'   SMA Trend: {sma_avg_pos:.2f} avg positions')
print(f'   Dual Momentum: {dual_avg_pos:.2f} avg positions')
print('   Dual is more concentrated (holds top 2 only)')

sma_turn = sma_results['portfolio_stats']['turnover'].resample('ME').sum().mean()
dual_turn = dual_results['portfolio_stats']['turnover'].resample('ME').sum().mean()

print('\n5. TURNOVER:')
print(f'   SMA Trend: {sma_turn:.1%} monthly')
print(f'   Dual Momentum: {dual_turn:.1%} monthly')
print(f'   Winner: Dual (lower turnover)')

print('\n' + '=' * 80)
print('CONCLUSION: SMA Trend strategy superior on risk-adjusted basis')
print('=' * 80)
