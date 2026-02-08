# src/signals/composite.py
"""
Signal composite framework — multi-signal fusion.

Combines momentum, regime, volatility, and mean-reversion signals
into a single composite signal. Key design principle: ensure signals
are low-correlation so fusion actually improves diversification.

Fusion methods:
- Equal weight: most robust, no estimation error
- Inverse correlation: higher weight to less-correlated signals
- Regime conditional: shift blend weights based on market regime
"""

import pandas as pd
import numpy as np
from typing import Dict


def equal_weight_blend(
    signals: Dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Equal-weight average of all signals.

    Most robust fusion method — no estimation risk.
    Works well when signal quality is roughly similar.

    Parameters
    ----------
    signals : dict
        {name: signal_df} where each signal_df has same index/columns.
        Signal values should be 0-1 (0=bearish, 1=bullish).

    Returns
    -------
    pd.DataFrame
        Blended signal (0-1 scale).
    """
    if not signals:
        raise ValueError("At least one signal required")

    dfs = list(signals.values())
    stacked = pd.concat(dfs, keys=signals.keys())
    result = stacked.groupby(level=1).mean()

    return result


def inverse_correlation_blend(
    signals: Dict[str, pd.DataFrame],
    lookback: int = 252,
    min_weight: float = 0.05,
) -> pd.DataFrame:
    """
    Weight signals inversely by their pairwise correlation.

    Less-correlated signals get higher weight, maximizing
    the diversification benefit of combining them.

    Parameters
    ----------
    signals : dict
        {name: signal_df} with same index/columns.
    lookback : int
        Window for correlation estimation.
    min_weight : float
        Minimum weight per signal (prevents zero allocation).

    Returns
    -------
    pd.DataFrame
        Blended signal.
    """
    if len(signals) < 2:
        return equal_weight_blend(signals)

    names = list(signals.keys())
    dfs = list(signals.values())

    # Compute average correlation of each signal with all others
    # Use the mean across all asset columns
    signal_means = {}
    for name, df in signals.items():
        signal_means[name] = df.mean(axis=1)

    corr_df = pd.DataFrame(signal_means)

    # Rolling correlation matrix
    result_frames = []
    ref_df = dfs[0]

    for i in range(lookback, len(ref_df.index)):
        window = corr_df.iloc[i - lookback:i]
        if window.isna().all().any():
            result_frames.append(None)
            continue

        corr_matrix = window.corr()

        # Average absolute correlation per signal
        avg_corr = {}
        for name in names:
            others = [n for n in names if n != name]
            if others:
                avg_corr[name] = corr_matrix.loc[name, others].abs().mean()
            else:
                avg_corr[name] = 0.0

        # Inverse correlation → weight
        inv_corr = {k: 1.0 / (v + 0.01) for k, v in avg_corr.items()}
        total = sum(inv_corr.values())
        weights = {k: max(v / total, min_weight) for k, v in inv_corr.items()}

        # Re-normalize after min_weight clipping
        w_total = sum(weights.values())
        weights = {k: v / w_total for k, v in weights.items()}

        # Blend
        blended = sum(weights[name] * dfs[j].iloc[i] for j, name in enumerate(names))
        result_frames.append(blended)

    # Build result
    valid_idx = ref_df.index[lookback:]
    valid_frames = [f for f in result_frames if f is not None]

    if not valid_frames:
        return pd.DataFrame(np.nan, index=ref_df.index, columns=ref_df.columns)

    # Align indices
    result = pd.DataFrame(np.nan, index=ref_df.index, columns=ref_df.columns)
    for idx, frame in zip(valid_idx, result_frames):
        if frame is not None:
            result.loc[idx] = frame

    return result


def regime_conditional_blend(
    signals: Dict[str, pd.DataFrame],
    regime_score: pd.Series,
    risk_on_weights: Dict[str, float] = None,
    risk_off_weights: Dict[str, float] = None,
    regime_threshold: float = 0.5,
) -> pd.DataFrame:
    """
    Shift signal blend weights based on market regime.

    In risk-off regimes: increase weight of defensive signals
    (regime, vol) and decrease momentum weight.

    In risk-on regimes: momentum-heavy blend.

    Parameters
    ----------
    signals : dict
        {name: signal_df}.
    regime_score : pd.Series
        0 (crisis) to 1 (risk-on).
    risk_on_weights : dict
        Signal weights during risk-on (default: equal weight).
    risk_off_weights : dict
        Signal weights during risk-off (default: equal weight).
    regime_threshold : float
        Score below this = risk-off, above = risk-on.

    Returns
    -------
    pd.DataFrame
        Regime-conditional blended signal.
    """
    if not signals:
        raise ValueError("At least one signal required")

    names = list(signals.keys())
    n = len(names)

    if risk_on_weights is None:
        risk_on_weights = {name: 1.0 / n for name in names}
    if risk_off_weights is None:
        risk_off_weights = {name: 1.0 / n for name in names}

    ref_df = list(signals.values())[0]
    result = pd.DataFrame(np.nan, index=ref_df.index, columns=ref_df.columns)

    for i, date in enumerate(ref_df.index):
        score = regime_score.get(date, np.nan)
        if pd.isna(score):
            continue

        weights = risk_on_weights if score >= regime_threshold else risk_off_weights

        blended = sum(
            weights.get(name, 0) * signals[name].iloc[i]
            for name in names
        )
        result.iloc[i] = blended

    return result


def signal_to_binary(
    signal: pd.DataFrame,
    threshold: float = 0.5,
) -> pd.DataFrame:
    """
    Convert continuous signal (0-1) to binary (0 or 1).

    Parameters
    ----------
    signal : pd.DataFrame
        Continuous signal values (0 to 1).
    threshold : float
        Values >= threshold → 1, below → 0.

    Returns
    -------
    pd.DataFrame
        Binary signal (0 or 1).
    """
    binary = (signal >= threshold).astype(float)
    binary[signal.isna()] = np.nan
    return binary


def signal_correlation_report(
    signals: Dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Compute pairwise correlation between signals.

    Use this to verify signals are actually diversifying.
    Target: pairwise correlation < 0.5 for meaningful diversification.

    Parameters
    ----------
    signals : dict
        {name: signal_df}.

    Returns
    -------
    pd.DataFrame
        Correlation matrix of signal means.
    """
    means = {}
    for name, df in signals.items():
        means[name] = df.mean(axis=1)

    corr_df = pd.DataFrame(means).corr()
    return corr_df


if __name__ == "__main__":
    from signals.regime import realized_vol_regime, composite_regime
    from signals.volatility import vol_term_structure
    from signals.mean_reversion import zscore_signal
    from signals.trend_filter import ema_trend_signal

    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=500, freq="D")
    prices = pd.DataFrame({
        "SPY": 100 * np.exp(np.cumsum(np.random.normal(0.0004, 0.015, 500))),
        "TLT": 100 * np.exp(np.cumsum(np.random.normal(0.0001, 0.010, 500))),
        "GLD": 100 * np.exp(np.cumsum(np.random.normal(0.0002, 0.012, 500))),
    }, index=dates)

    print("Signal Composite Demo")
    print("=" * 50)

    # Build signals
    sig_momentum = ema_trend_signal(prices, span=126).astype(float)
    sig_vol = vol_term_structure(prices)
    sig_mr = zscore_signal(prices, lookback=21)

    signals = {
        "momentum": sig_momentum,
        "vol_structure": sig_vol,
        "mean_reversion": sig_mr,
    }

    # Correlation report
    corr = signal_correlation_report(signals)
    print(f"\nSignal Correlations:\n{corr}")

    # Equal weight blend
    blended = equal_weight_blend(signals)
    print(f"\nEqual-Weight Blend (last 5):\n{blended.tail()}")

    # Binary
    binary = signal_to_binary(blended, threshold=0.5)
    print(f"\nBinary Signal (last 5):\n{binary.tail()}")
