"""
Experiment 7: Parameter Stability (Walk-Forward Validation)

Test whether EMA 126d is a stable parameter choice or an overfit artifact.
Uses rolling walk-forward windows to check if the optimal span stays
consistently near 126d across different periods.

WALK-FORWARD DECLARATION:
  Rolling windows: 5-year train, 2-year validation
  Spans tested: [42, 63, 84, 126, 168, 189, 252, 378]
  Test periods: rolling from 2006 to 2024

FAILURE CRITERIA (defined before running):
  - Optimal span varies by > 2x across windows (instability)
  - EMA 126d is never in top-3 across >50% of windows
  - Sharpe variance across windows > 0.5 (inconsistent performance)
  - Any window shows Sharpe < 0.0 (strategy breaks down entirely)
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
# FAILURE CRITERIA
# ============================================================================

FAILURE_CRITERIA = {
    'max_optimal_ratio': 2.0,       # Optimal span shouldn't vary > 2x
    'min_top3_pct': 0.50,           # 126d should be top-3 in >50% of windows
    'max_sharpe_variance': 0.50,    # Sharpe variance across windows
    'min_any_window_sharpe': 0.0,   # No window should have negative Sharpe
}

# Spans to test (covering short to long trend horizons)
SPANS_TO_TEST = [42, 63, 84, 126, 168, 189, 252, 378]

# Walk-forward configuration
TRAIN_YEARS = 5
VAL_YEARS = 2
STEP_YEARS = 1  # Slide forward by 1 year each step


# ============================================================================
# Walk-Forward Engine
# ============================================================================

def rolling_walk_forward(
    prices: pd.DataFrame,
    spans: List[int],
    train_years: int = 5,
    val_years: int = 2,
    step_years: int = 1,
    transaction_cost: float = 0.0005,
) -> List[Dict]:
    """
    Run rolling walk-forward analysis across multiple EMA spans.

    For each rolling window:
    1. Train period: find best span (highest Sharpe)
    2. Validation period: test that span out-of-sample

    Parameters
    ----------
    prices : pd.DataFrame
        Full price data.
    spans : List[int]
        EMA spans to test.
    train_years : int
        Training window size.
    val_years : int
        Validation window size.
    step_years : int
        How many years to slide forward each step.
    transaction_cost : float
        Transaction cost per unit turnover.

    Returns
    -------
    List[Dict]
        Results for each walk-forward window.
    """
    results = []
    start_date = prices.index[0]
    end_date = prices.index[-1]

    # Generate rolling windows
    window_start = start_date
    window_id = 0

    while True:
        train_end = window_start + pd.DateOffset(years=train_years)
        val_start = train_end
        val_end = val_start + pd.DateOffset(years=val_years)

        # Stop if validation end exceeds data
        if val_end > end_date:
            break

        window_id += 1
        print(f"\n  Window {window_id}: Train {window_start.date()}-{train_end.date()}, "
              f"Val {val_start.date()}-{val_end.date()}")

        # Slice data
        train_mask = (prices.index >= window_start) & (prices.index < train_end)
        val_mask = (prices.index >= val_start) & (prices.index < val_end)

        train_prices = prices.loc[train_mask]
        val_prices = prices.loc[val_mask]

        if len(train_prices) < 252 or len(val_prices) < 126:
            print(f"    Skipping: insufficient data (train={len(train_prices)}, val={len(val_prices)})")
            window_start += pd.DateOffset(years=step_years)
            continue

        # Test each span on training period
        train_sharpes = {}
        for span in spans:
            try:
                signals = generate_signals(train_prices, method='ema', span=span)
                bt = calculate_strategy_returns(
                    train_prices, signals,
                    transaction_cost=transaction_cost,
                    rebalance_frequency='M'
                )
                metrics = calculate_performance_metrics(bt['returns'])
                train_sharpes[span] = metrics['sharpe_ratio']
            except Exception as e:
                train_sharpes[span] = np.nan

        # Find best span in training
        best_span = max(train_sharpes, key=lambda k: train_sharpes[k] if not np.isnan(train_sharpes[k]) else -999)

        # Rank all spans
        sorted_spans = sorted(train_sharpes.items(), key=lambda x: x[1] if not np.isnan(x[1]) else -999, reverse=True)
        rank_126 = next((i + 1 for i, (s, _) in enumerate(sorted_spans) if s == 126), len(spans))

        # Validate best span and 126d on validation period
        val_results = {}
        for span in [best_span, 126]:
            try:
                signals = generate_signals(val_prices, method='ema', span=span)
                bt = calculate_strategy_returns(
                    val_prices, signals,
                    transaction_cost=transaction_cost,
                    rebalance_frequency='M'
                )
                metrics = calculate_performance_metrics(bt['returns'])
                val_results[span] = {
                    'sharpe': metrics['sharpe_ratio'],
                    'annual_return': metrics['annualized_return'],
                    'max_drawdown': metrics['max_drawdown'],
                }
            except Exception:
                val_results[span] = {
                    'sharpe': np.nan,
                    'annual_return': np.nan,
                    'max_drawdown': np.nan,
                }

        # Also test all spans on validation for completeness
        val_all_sharpes = {}
        for span in spans:
            try:
                signals = generate_signals(val_prices, method='ema', span=span)
                bt = calculate_strategy_returns(
                    val_prices, signals,
                    transaction_cost=transaction_cost,
                    rebalance_frequency='M'
                )
                metrics = calculate_performance_metrics(bt['returns'])
                val_all_sharpes[span] = metrics['sharpe_ratio']
            except Exception:
                val_all_sharpes[span] = np.nan

        window_result = {
            'window_id': window_id,
            'train_start': window_start.isoformat(),
            'train_end': train_end.isoformat(),
            'val_start': val_start.isoformat(),
            'val_end': val_end.isoformat(),
            'train_sharpes': {str(k): float(v) if not np.isnan(v) else None for k, v in train_sharpes.items()},
            'best_span_train': int(best_span),
            'best_sharpe_train': float(train_sharpes[best_span]) if not np.isnan(train_sharpes[best_span]) else None,
            'rank_126_train': rank_126,
            'val_sharpes': {str(k): float(v) if not np.isnan(v) else None for k, v in val_all_sharpes.items()},
            'val_best_span': val_results.get(best_span, {}),
            'val_126': val_results.get(126, {}),
        }

        print(f"    Best train span: {best_span} (Sharpe={train_sharpes[best_span]:.3f})")
        print(f"    126d rank in train: #{rank_126} (Sharpe={train_sharpes.get(126, np.nan):.3f})")
        if 126 in val_results:
            print(f"    126d val Sharpe: {val_results[126]['sharpe']:.3f}")

        results.append(window_result)

        # Slide forward
        window_start += pd.DateOffset(years=step_years)

    return results


# ============================================================================
# Stability Metrics
# ============================================================================

def compute_stability_metrics(windows: List[Dict]) -> Dict:
    """
    Compute overall stability metrics from walk-forward results.

    Parameters
    ----------
    windows : List[Dict]
        Results from rolling_walk_forward.

    Returns
    -------
    Dict
        Stability metrics.
    """
    if not windows:
        return {'error': 'No valid windows'}

    best_spans = [w['best_span_train'] for w in windows]
    val_sharpes_126 = []
    for w in windows:
        s = w.get('val_126', {}).get('sharpe')
        if s is not None and not (isinstance(s, float) and np.isnan(s)):
            val_sharpes_126.append(s)

    # Top-3 analysis: how often is 126d in top-3 during training
    top3_count = sum(1 for w in windows if w['rank_126_train'] <= 3)
    top3_pct = top3_count / len(windows) if windows else 0

    # Optimal span range
    optimal_min = min(best_spans)
    optimal_max = max(best_spans)
    optimal_ratio = optimal_max / optimal_min if optimal_min > 0 else float('inf')

    # Sharpe variance for 126d across validation windows
    sharpe_var = np.var(val_sharpes_126) if len(val_sharpes_126) > 1 else 0.0
    min_val_sharpe = min(val_sharpes_126) if val_sharpes_126 else np.nan

    # Consistency: how often does the best train span also work in val?
    consistent_count = 0
    for w in windows:
        best = w['best_span_train']
        val_sharpes = w.get('val_sharpes', {})
        best_val = val_sharpes.get(str(best))
        s126_val = val_sharpes.get('126')
        if best_val is not None and s126_val is not None:
            # Check if best train span outperforms 126d in val too
            if best_val >= s126_val:
                consistent_count += 1

    consistency_pct = consistent_count / len(windows) if windows else 0

    return {
        'n_windows': len(windows),
        'optimal_spans': best_spans,
        'optimal_span_min': optimal_min,
        'optimal_span_max': optimal_max,
        'optimal_span_ratio': optimal_ratio,
        'optimal_span_mode': int(pd.Series(best_spans).mode().iloc[0]) if best_spans else None,
        'rank_126_top3_pct': top3_pct,
        'val_sharpe_126_mean': np.mean(val_sharpes_126) if val_sharpes_126 else np.nan,
        'val_sharpe_126_std': np.std(val_sharpes_126) if val_sharpes_126 else np.nan,
        'val_sharpe_126_var': sharpe_var,
        'val_sharpe_126_min': min_val_sharpe,
        'train_val_consistency': consistency_pct,
    }


# ============================================================================
# Failure Criteria Check
# ============================================================================

def check_failure_criteria(stability: Dict) -> Dict:
    """
    Check failure criteria.

    Parameters
    ----------
    stability : Dict
        From compute_stability_metrics.

    Returns
    -------
    Dict
        {'passed': bool, 'failures': List[str], 'metrics': Dict}
    """
    failures = []

    # 1. Optimal span ratio
    ratio = stability.get('optimal_span_ratio', float('inf'))
    if ratio > FAILURE_CRITERIA['max_optimal_ratio']:
        failures.append(
            f"Optimal span ratio = {ratio:.2f}x > {FAILURE_CRITERIA['max_optimal_ratio']}x "
            f"(range: {stability['optimal_span_min']}-{stability['optimal_span_max']})"
        )

    # 2. 126d in top-3 frequency
    top3_pct = stability.get('rank_126_top3_pct', 0)
    if top3_pct < FAILURE_CRITERIA['min_top3_pct']:
        failures.append(
            f"126d in top-3: {top3_pct:.1%} < {FAILURE_CRITERIA['min_top3_pct']:.1%}"
        )

    # 3. Sharpe variance across windows
    sharpe_var = stability.get('val_sharpe_126_var', float('inf'))
    if sharpe_var > FAILURE_CRITERIA['max_sharpe_variance']:
        failures.append(
            f"Sharpe variance = {sharpe_var:.3f} > {FAILURE_CRITERIA['max_sharpe_variance']}"
        )

    # 4. Minimum window Sharpe
    min_sharpe = stability.get('val_sharpe_126_min', -999)
    if not np.isnan(min_sharpe) and min_sharpe < FAILURE_CRITERIA['min_any_window_sharpe']:
        failures.append(
            f"Min window Sharpe = {min_sharpe:.3f} < {FAILURE_CRITERIA['min_any_window_sharpe']}"
        )

    return {
        'passed': len(failures) == 0,
        'failures': failures,
        'metrics': {
            'optimal_span_ratio': ratio,
            'top3_pct': top3_pct,
            'sharpe_variance': sharpe_var,
            'min_window_sharpe': min_sharpe,
        }
    }


# ============================================================================
# Main Experiment
# ============================================================================

def run_experiment_7() -> Dict:
    """
    Run Experiment 7: Parameter Stability Walk-Forward.

    Returns
    -------
    Dict
        Complete experiment results.
    """
    print("=" * 80)
    print("EXPERIMENT 7: Parameter Stability (Walk-Forward Validation)")
    print("=" * 80)

    # Load data
    data_path = PROJECT_ROOT / "data" / "processed" / "prices_clean.csv"
    prices = pd.read_csv(data_path, index_col=0, parse_dates=True)

    print(f"\nData loaded: {prices.shape[0]} days, {prices.shape[1]} assets")
    print(f"Date range: {prices.index.min()} to {prices.index.max()}")
    print(f"\nSpans to test: {SPANS_TO_TEST}")
    print(f"Walk-forward: {TRAIN_YEARS}y train, {VAL_YEARS}y val, {STEP_YEARS}y step")

    # ── Run walk-forward ──
    print(f"\n{'─' * 60}")
    print("Rolling Walk-Forward Analysis")
    print(f"{'─' * 60}")

    windows = rolling_walk_forward(
        prices,
        spans=SPANS_TO_TEST,
        train_years=TRAIN_YEARS,
        val_years=VAL_YEARS,
        step_years=STEP_YEARS,
        transaction_cost=0.0005,
    )

    # ── Stability metrics ──
    print(f"\n{'─' * 60}")
    print("Stability Metrics")
    print(f"{'─' * 60}")

    stability = compute_stability_metrics(windows)

    print(f"\n  Number of windows: {stability['n_windows']}")
    print(f"  Optimal spans seen: {stability['optimal_spans']}")
    print(f"  Optimal span range: {stability['optimal_span_min']}-{stability['optimal_span_max']} "
          f"(ratio: {stability['optimal_span_ratio']:.2f}x)")
    print(f"  Mode of optimal span: {stability['optimal_span_mode']}")
    print(f"  126d in top-3: {stability['rank_126_top3_pct']:.1%} of windows")
    print(f"  Val Sharpe (126d): mean={stability['val_sharpe_126_mean']:.3f}, "
          f"std={stability['val_sharpe_126_std']:.3f}")
    print(f"  Train→Val consistency: {stability['train_val_consistency']:.1%}")

    # ── Heatmap data (span x window) ──
    print(f"\n{'─' * 60}")
    print("Span x Window Sharpe Heatmap (Validation)")
    print(f"{'─' * 60}")

    header = f"  {'Window':<8}" + "".join(f"{s:>8}" for s in SPANS_TO_TEST)
    print(header)
    print(f"  {'-' * (8 + 8 * len(SPANS_TO_TEST))}")

    for w in windows:
        row = f"  W{w['window_id']:<7}"
        for span in SPANS_TO_TEST:
            val = w['val_sharpes'].get(str(span))
            if val is not None:
                row += f"{val:>8.2f}"
            else:
                row += f"{'N/A':>8}"
        print(row)

    # ── Failure criteria ──
    print(f"\n{'=' * 80}")
    print("FAILURE CRITERIA CHECK")
    print(f"{'=' * 80}")

    failure_check = check_failure_criteria(stability)

    if failure_check['passed']:
        print("\n  [PASS] EMA 126d is a stable parameter choice")
    else:
        print("\n  [FAIL] Parameter stability concerns")
        for f in failure_check['failures']:
            print(f"    - {f}")

    # ── Assemble results ──
    # Clean up non-serializable values
    clean_stability = {}
    for k, v in stability.items():
        if isinstance(v, (np.floating, np.integer)):
            clean_stability[k] = float(v)
        elif isinstance(v, list):
            clean_stability[k] = [int(x) if isinstance(x, (np.integer,)) else x for x in v]
        elif isinstance(v, float) and np.isnan(v):
            clean_stability[k] = None
        else:
            clean_stability[k] = v

    clean_failure = {
        'passed': failure_check['passed'],
        'failures': failure_check['failures'],
        'metrics': {},
    }
    for k, v in failure_check['metrics'].items():
        if isinstance(v, float) and np.isnan(v):
            clean_failure['metrics'][k] = None
        elif isinstance(v, (np.floating, np.integer)):
            clean_failure['metrics'][k] = float(v)
        else:
            clean_failure['metrics'][k] = v

    results = {
        'experiment_id': '07',
        'experiment_name': 'Parameter Stability Walk-Forward',
        'timestamp': pd.Timestamp.now().isoformat(),
        'config': {
            'spans': SPANS_TO_TEST,
            'train_years': TRAIN_YEARS,
            'val_years': VAL_YEARS,
            'step_years': STEP_YEARS,
            'transaction_cost': 0.0005,
        },
        'failure_criteria': FAILURE_CRITERIA,
        'n_windows': len(windows),
        'windows': windows,
        'stability_metrics': clean_stability,
        'failure_check': clean_failure,
    }

    return results


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    results = run_experiment_7()

    # Save results
    output_dir = PROJECT_ROOT / "outputs" / "experiments"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
    output_path = output_dir / f"exp_07_parameter_stability_{timestamp}.json"

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n\nResults saved to: {output_path}")

    # Final conclusion
    print(f"\n{'=' * 80}")
    print("CONCLUSION")
    print(f"{'=' * 80}")

    if results['failure_check']['passed']:
        print("\n  [PASS] EMA 126d is robust across time periods.")
        print(f"  Optimal span range: {results['stability_metrics']['optimal_span_min']}-"
              f"{results['stability_metrics']['optimal_span_max']}")
        print(f"  126d in top-3: {results['stability_metrics']['rank_126_top3_pct']:.0%} of windows")
    else:
        print("\n  [FAIL] Parameter instability detected.")
        print("  Recommendation: Consider adaptive span or ensemble of spans.")
        for f in results['failure_check']['failures']:
            print(f"    - {f}")
