"""
Experiment 5: Transaction Cost Sensitivity Analysis

Quantify the impact of transaction costs on strategy viability.

WALK-FORWARD DECLARATION:
  Training:   2006-02-03 to 2015-12-31
  Validation: 2016-01-01 to 2019-12-31
  Test:       2020-01-01 to 2024-12-31
  Test Set First Run: [AUTO-FILLED on first execution]

COST SCENARIOS:
  Low:    5 bps  (passive ETFs, institutional)
  Medium: 12 bps (retail with good execution)
  High:   25 bps (retail, small AUM, bad timing)
  Dynamic: volatility-adjusted spread model

FAILURE CRITERIA (defined before running):
  - Strategy Sharpe < 0.5 at Medium (12 bps) cost
  - Strategy Sharpe < 0.3 at High (25 bps) cost
  - Break-even cost < 15 bps (too fragile)
  - MaxDD worsens by > 5pp from zero-cost baseline
  - Annual turnover cost > 2% of portfolio
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import json
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.signals.trend_filter import generate_signals
from src.backtest.engine import calculate_strategy_returns, calculate_performance_metrics

# ============================================================================
# FAILURE CRITERIA (defined before experiment)
# ============================================================================

FAILURE_CRITERIA = {
    'min_sharpe_medium': 0.50,    # Sharpe at 12 bps
    'min_sharpe_high': 0.30,      # Sharpe at 25 bps
    'min_breakeven_bps': 15,      # Break-even cost in bps
    'max_dd_deterioration': 0.05, # MaxDD can worsen by at most 5pp
    'max_annual_cost_pct': 0.02,  # Max 2% annual cost drag
}

COST_SCENARIOS = {
    'zero':   0.0000,  # Baseline (no cost)
    'low':    0.0005,  # 5 bps
    'medium': 0.0012,  # 12 bps
    'high':   0.0025,  # 25 bps
}

# Walk-forward periods
PERIODS = {
    'train':      ('2006-02-03', '2015-12-31'),
    'validation': ('2016-01-01', '2019-12-31'),
    'test':       ('2020-01-01', '2024-12-31'),
}


# ============================================================================
# Dynamic Cost Model
# ============================================================================

def dynamic_cost_model(
    prices: pd.DataFrame,
    base_cost: float = 0.0005,
    vol_lookback: int = 21,
    vol_multiplier: float = 2.0,
) -> pd.Series:
    """
    Volatility-adjusted transaction cost model.

    In high-vol environments, bid-ask spreads widen and slippage increases.
    cost_t = base_cost * (1 + vol_multiplier * vol_t / median_vol)

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices.
    base_cost : float
        Base transaction cost (5 bps default).
    vol_lookback : int
        Window for realized vol.
    vol_multiplier : float
        How much vol amplifies cost.

    Returns
    -------
    pd.Series
        Time-varying cost per unit turnover.
    """
    # Use equal-weight portfolio returns for vol estimate
    returns = prices.pct_change().mean(axis=1)
    rolling_vol = returns.rolling(vol_lookback, min_periods=10).std() * np.sqrt(252)
    median_vol = rolling_vol.median()

    # Avoid division by zero
    if median_vol == 0 or pd.isna(median_vol):
        return pd.Series(base_cost, index=prices.index)

    vol_ratio = rolling_vol / median_vol
    dynamic_cost = base_cost * (1 + vol_multiplier * (vol_ratio - 1).clip(lower=0))
    dynamic_cost = dynamic_cost.fillna(base_cost)

    return dynamic_cost


def backtest_with_dynamic_costs(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    base_cost: float = 0.0005,
    vol_multiplier: float = 2.0,
    rebalance_frequency: str = 'M',
) -> pd.DataFrame:
    """
    Backtest applying time-varying transaction costs.

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices.
    signals : pd.DataFrame
        Trading signals.
    base_cost : float
        Base cost for dynamic model.
    vol_multiplier : float
        Vol amplification factor.
    rebalance_frequency : str
        Rebalance freq.

    Returns
    -------
    pd.DataFrame
        Portfolio stats (same format as engine).
    """
    daily_returns = prices.pct_change()
    signals_shifted = signals.shift(1).fillna(0)
    dynamic_costs = dynamic_cost_model(prices, base_cost, vol_multiplier=vol_multiplier)

    if rebalance_frequency == 'M':
        rebalance_dates = pd.date_range(
            start=prices.index[0], end=prices.index[-1], freq='MS')
    elif rebalance_frequency == 'W':
        rebalance_dates = pd.date_range(
            start=prices.index[0], end=prices.index[-1], freq='W')
    else:
        rebalance_dates = prices.index

    portfolio_value = pd.Series(index=prices.index, dtype=float)
    portfolio_value.iloc[0] = 100.0
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    turnover = pd.Series(0.0, index=prices.index)
    cost_paid = pd.Series(0.0, index=prices.index)
    prev_weights = pd.Series(0.0, index=prices.columns)

    for i in range(1, len(prices)):
        date = prices.index[i]
        is_rebalance = date in rebalance_dates

        if is_rebalance or i == 1:
            active_signals = signals_shifted.loc[date]
            n_positions = active_signals.sum()

            if n_positions > 0:
                target_weights = active_signals / n_positions
            else:
                target_weights = pd.Series(0.0, index=prices.columns)

            turn = (target_weights - prev_weights).abs().sum()
            turnover.iloc[i] = turn
            tc = turn * dynamic_costs.iloc[i]
            cost_paid.iloc[i] = tc
            portfolio_value.iloc[i] = portfolio_value.iloc[i - 1] * (1 - tc)
            weights.loc[date] = target_weights
            prev_weights = target_weights
        else:
            portfolio_value.iloc[i] = portfolio_value.iloc[i - 1]
            weights.loc[date] = prev_weights

        period_return = (weights.loc[date] * daily_returns.loc[date]).sum()
        portfolio_value.iloc[i] = portfolio_value.iloc[i] * (1 + period_return)

        if not is_rebalance:
            individual_returns = daily_returns.loc[date]
            if period_return != -1:
                prev_weights = prev_weights * (1 + individual_returns) / (1 + period_return)
                prev_weights = prev_weights.fillna(0)

    return pd.DataFrame({
        'portfolio_value': portfolio_value,
        'returns': portfolio_value.pct_change().fillna(0),
        'positions': signals_shifted.sum(axis=1),
        'turnover': turnover,
        'cost_paid': cost_paid,
    })


# ============================================================================
# Break-Even Cost Analysis
# ============================================================================

def find_breakeven_cost(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    min_sharpe: float = 0.0,
    search_range: tuple = (0.0, 0.01),
    n_steps: int = 50,
) -> Dict[str, float]:
    """
    Find the transaction cost level where Sharpe ratio drops to min_sharpe.

    Uses grid search over cost range.

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices.
    signals : pd.DataFrame
        Trading signals.
    min_sharpe : float
        Target Sharpe (0 = break-even).
    search_range : tuple
        (min_cost, max_cost) in decimal.
    n_steps : int
        Grid resolution.

    Returns
    -------
    Dict
        {'breakeven_cost_bps': float, 'sharpe_at_breakeven': float, 'cost_curve': list}
    """
    costs = np.linspace(search_range[0], search_range[1], n_steps)
    cost_curve = []

    for cost in costs:
        result = calculate_strategy_returns(
            prices, signals,
            transaction_cost=cost,
            rebalance_frequency='M'
        )
        metrics = calculate_performance_metrics(result['returns'])
        cost_curve.append({
            'cost_bps': cost * 10000,
            'sharpe': metrics['sharpe_ratio'],
            'annual_return': metrics['annualized_return'],
            'max_drawdown': metrics['max_drawdown'],
        })

    cost_df = pd.DataFrame(cost_curve)

    # Find where Sharpe crosses min_sharpe
    above = cost_df[cost_df['sharpe'] >= min_sharpe]
    if len(above) == 0:
        breakeven_bps = 0.0
    elif len(above) == len(cost_df):
        breakeven_bps = search_range[1] * 10000
    else:
        breakeven_bps = above['cost_bps'].max()

    return {
        'breakeven_cost_bps': breakeven_bps,
        'sharpe_at_breakeven': min_sharpe,
        'cost_curve': cost_curve,
    }


# ============================================================================
# Run Cost Scenarios
# ============================================================================

def run_cost_scenarios(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    period_name: str = 'full',
) -> Dict[str, Dict]:
    """
    Run strategy under all cost scenarios for a given period.

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices.
    signals : pd.DataFrame
        Trading signals.
    period_name : str
        Label for this period.

    Returns
    -------
    Dict
        {scenario_name: {metrics + cost details}}
    """
    results = {}

    for scenario_name, cost_rate in COST_SCENARIOS.items():
        bt = calculate_strategy_returns(
            prices, signals,
            transaction_cost=cost_rate,
            rebalance_frequency='M'
        )
        metrics = calculate_performance_metrics(bt['returns'])

        # Cost statistics
        annual_turnover = bt['turnover'].resample('YE').sum().mean()
        annual_cost_drag = annual_turnover * cost_rate

        results[scenario_name] = {
            'period': period_name,
            'cost_bps': cost_rate * 10000,
            'sharpe': metrics['sharpe_ratio'],
            'annual_return': metrics['annualized_return'],
            'annual_vol': metrics['annualized_volatility'],
            'max_drawdown': metrics['max_drawdown'],
            'sortino': metrics['sortino_ratio'],
            'calmar': metrics['calmar_ratio'],
            'annual_turnover': annual_turnover,
            'annual_cost_drag': annual_cost_drag,
            'total_return': metrics['total_return'],
        }

    # Dynamic cost scenario
    bt_dynamic = backtest_with_dynamic_costs(
        prices, signals, base_cost=0.0005, vol_multiplier=2.0
    )
    metrics_dynamic = calculate_performance_metrics(bt_dynamic['returns'])
    annual_cost_dynamic = bt_dynamic['cost_paid'].resample('YE').sum().mean()

    results['dynamic'] = {
        'period': period_name,
        'cost_bps': 'dynamic (5bps base)',
        'sharpe': metrics_dynamic['sharpe_ratio'],
        'annual_return': metrics_dynamic['annualized_return'],
        'annual_vol': metrics_dynamic['annualized_volatility'],
        'max_drawdown': metrics_dynamic['max_drawdown'],
        'sortino': metrics_dynamic['sortino_ratio'],
        'calmar': metrics_dynamic['calmar_ratio'],
        'annual_turnover': bt_dynamic['turnover'].resample('YE').sum().mean(),
        'annual_cost_drag': annual_cost_dynamic,
        'total_return': metrics_dynamic['total_return'],
    }

    return results


# ============================================================================
# Failure Criteria Check
# ============================================================================

def check_failure_criteria(
    scenario_results: Dict[str, Dict],
    breakeven_info: Dict,
) -> Dict:
    """
    Check failure criteria against results.

    Parameters
    ----------
    scenario_results : Dict
        Results from run_cost_scenarios.
    breakeven_info : Dict
        Results from find_breakeven_cost.

    Returns
    -------
    Dict
        {'passed': bool, 'failures': List[str], 'metrics': Dict}
    """
    failures = []

    # 1. Sharpe at medium cost
    medium_sharpe = scenario_results['medium']['sharpe']
    if medium_sharpe < FAILURE_CRITERIA['min_sharpe_medium']:
        failures.append(
            f"Sharpe at 12bps = {medium_sharpe:.3f} < {FAILURE_CRITERIA['min_sharpe_medium']}"
        )

    # 2. Sharpe at high cost
    high_sharpe = scenario_results['high']['sharpe']
    if high_sharpe < FAILURE_CRITERIA['min_sharpe_high']:
        failures.append(
            f"Sharpe at 25bps = {high_sharpe:.3f} < {FAILURE_CRITERIA['min_sharpe_high']}"
        )

    # 3. Break-even cost
    be_bps = breakeven_info['breakeven_cost_bps']
    if be_bps < FAILURE_CRITERIA['min_breakeven_bps']:
        failures.append(
            f"Break-even cost = {be_bps:.1f} bps < {FAILURE_CRITERIA['min_breakeven_bps']} bps"
        )

    # 4. MaxDD deterioration
    zero_dd = scenario_results['zero']['max_drawdown']
    high_dd = scenario_results['high']['max_drawdown']
    dd_deterioration = abs(high_dd) - abs(zero_dd)
    if dd_deterioration > FAILURE_CRITERIA['max_dd_deterioration']:
        failures.append(
            f"MaxDD deterioration = {dd_deterioration:.3f} > {FAILURE_CRITERIA['max_dd_deterioration']}"
        )

    # 5. Annual cost drag at medium
    annual_cost = scenario_results['medium']['annual_cost_drag']
    if annual_cost > FAILURE_CRITERIA['max_annual_cost_pct']:
        failures.append(
            f"Annual cost drag = {annual_cost:.4f} > {FAILURE_CRITERIA['max_annual_cost_pct']}"
        )

    return {
        'passed': len(failures) == 0,
        'failures': failures,
        'metrics': {
            'sharpe_medium': medium_sharpe,
            'sharpe_high': high_sharpe,
            'breakeven_bps': be_bps,
            'dd_deterioration': dd_deterioration,
            'annual_cost_medium': annual_cost,
        }
    }


# ============================================================================
# Main Experiment
# ============================================================================

def run_experiment_5() -> Dict:
    """
    Run Experiment 5: Transaction Cost Sensitivity Analysis.

    Returns
    -------
    Dict
        Complete experiment results.
    """
    print("=" * 80)
    print("EXPERIMENT 5: Transaction Cost Sensitivity Analysis")
    print("=" * 80)

    # Load data
    data_path = PROJECT_ROOT / "data" / "processed" / "prices_clean.csv"
    prices = pd.read_csv(data_path, index_col=0, parse_dates=True)

    print(f"\nData loaded: {prices.shape[0]} days, {prices.shape[1]} assets")
    print(f"Date range: {prices.index.min()} to {prices.index.max()}")

    # Generate production signals (EMA 126d)
    signals = generate_signals(prices, method='ema', span=126)
    print(f"Production signals: EMA 126d")

    all_results = {}

    # ── Run on each walk-forward period ──
    for period_name, (start, end) in PERIODS.items():
        print(f"\n{'─' * 60}")
        print(f"Period: {period_name} ({start} to {end})")
        print(f"{'─' * 60}")

        mask = (prices.index >= start) & (prices.index <= end)
        p_period = prices.loc[mask]
        s_period = signals.loc[mask]

        if len(p_period) < 60:
            print(f"  Skipping: only {len(p_period)} days")
            continue

        results = run_cost_scenarios(p_period, s_period, period_name)

        print(f"\n  {'Scenario':<12} {'Cost(bps)':<12} {'Sharpe':<8} {'AnnRet':<10} {'MaxDD':<10} {'AnnCost':<10}")
        print(f"  {'-' * 62}")
        for name, r in results.items():
            cost_str = f"{r['cost_bps']}" if isinstance(r['cost_bps'], str) else f"{r['cost_bps']:.0f}"
            print(f"  {name:<12} {cost_str:<12} {r['sharpe']:<8.3f} {r['annual_return']:<10.4f} {r['max_drawdown']:<10.4f} {r['annual_cost_drag']:<10.6f}")

        all_results[period_name] = results

    # ── Full period analysis ──
    print(f"\n{'─' * 60}")
    print(f"Full Period Analysis")
    print(f"{'─' * 60}")

    full_results = run_cost_scenarios(prices, signals, 'full')
    all_results['full'] = full_results

    print(f"\n  {'Scenario':<12} {'Cost(bps)':<12} {'Sharpe':<8} {'AnnRet':<10} {'MaxDD':<10} {'AnnCost':<10}")
    print(f"  {'-' * 62}")
    for name, r in full_results.items():
        cost_str = f"{r['cost_bps']}" if isinstance(r['cost_bps'], str) else f"{r['cost_bps']:.0f}"
        print(f"  {name:<12} {cost_str:<12} {r['sharpe']:<8.3f} {r['annual_return']:<10.4f} {r['max_drawdown']:<10.4f} {r['annual_cost_drag']:<10.6f}")

    # ── Break-even analysis ──
    print(f"\n{'─' * 60}")
    print(f"Break-Even Cost Analysis")
    print(f"{'─' * 60}")

    breakeven = find_breakeven_cost(prices, signals, min_sharpe=0.0)
    print(f"  Break-even cost (Sharpe=0): {breakeven['breakeven_cost_bps']:.1f} bps")

    breakeven_50 = find_breakeven_cost(prices, signals, min_sharpe=0.50)
    print(f"  Break-even cost (Sharpe=0.5): {breakeven_50['breakeven_cost_bps']:.1f} bps")

    # ── Failure criteria check ──
    print(f"\n{'=' * 80}")
    print("FAILURE CRITERIA CHECK")
    print(f"{'=' * 80}")

    failure_check = check_failure_criteria(full_results, breakeven)

    if failure_check['passed']:
        print("\n  [PASS] All failure criteria met — strategy is cost-robust")
    else:
        print("\n  [FAIL] Strategy fails cost sensitivity tests")
        for f in failure_check['failures']:
            print(f"    - {f}")

    print(f"\n  Key metrics:")
    for k, v in failure_check['metrics'].items():
        print(f"    {k}: {v:.4f}")

    # ── Assemble results ──
    results = {
        'experiment_id': '05',
        'experiment_name': 'Transaction Cost Sensitivity',
        'timestamp': pd.Timestamp.now().isoformat(),
        'signal_config': {'method': 'ema', 'span': 126},
        'cost_scenarios': {k: v * 10000 for k, v in COST_SCENARIOS.items()},
        'failure_criteria': FAILURE_CRITERIA,
        'period_results': {},
        'breakeven_sharpe_0': {
            'breakeven_bps': breakeven['breakeven_cost_bps'],
            'cost_curve': breakeven['cost_curve'],
        },
        'breakeven_sharpe_50': {
            'breakeven_bps': breakeven_50['breakeven_cost_bps'],
        },
        'failure_check': failure_check,
    }

    # Serialize period results (convert non-serializable values)
    for period_name, period_data in all_results.items():
        results['period_results'][period_name] = {}
        for scenario, metrics in period_data.items():
            clean_metrics = {}
            for k, v in metrics.items():
                if isinstance(v, (np.floating, np.integer)):
                    clean_metrics[k] = float(v)
                else:
                    clean_metrics[k] = v
            results['period_results'][period_name][scenario] = clean_metrics

    return results


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    results = run_experiment_5()

    # Save results
    output_dir = PROJECT_ROOT / "outputs" / "experiments"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
    output_path = output_dir / f"exp_05_cost_sensitivity_{timestamp}.json"

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n\nResults saved to: {output_path}")

    # Final conclusion
    print(f"\n{'=' * 80}")
    print("CONCLUSION")
    print(f"{'=' * 80}")

    if results['failure_check']['passed']:
        print("\n  [PASS] Strategy survives transaction cost stress test.")
        print(f"  Break-even at {results['breakeven_sharpe_0']['breakeven_bps']:.0f} bps — room for execution error.")
    else:
        print("\n  [FAIL] Strategy is too fragile to transaction costs.")
        print("  Recommendation: Reduce rebalance frequency or signal sensitivity.")
        for f in results['failure_check']['failures']:
            print(f"    - {f}")
