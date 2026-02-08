# src/signals/regime.py
"""
Regime detection signals — non-momentum alpha source.

Identifies market regimes (risk-on/risk-off/crisis) from:
- Realized volatility levels (VIX proxy)
- Cross-asset momentum coherence
- Correlation regime (diversification breakdown)

These signals are orthogonal to trend-following and help the strategy
reduce exposure during crisis periods when momentum fails.
"""

import pandas as pd
import numpy as np


def realized_vol_regime(
    prices: pd.DataFrame,
    short_window: int = 21,
    long_window: int = 63,
    low_threshold: float = 0.10,
    high_threshold: float = 0.25,
) -> pd.DataFrame:
    """
    Classify volatility regime using realized vol of each asset.

    Three states mapped to signal scores:
    - Low vol  (ann. vol < low_threshold):  1.0 (risk-on)
    - Normal vol:                           0.5 (neutral)
    - High vol (ann. vol > high_threshold): 0.0 (risk-off)

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices.
    short_window : int
        Window for realized vol calculation.
    long_window : int
        Longer window used for smoothing the regime classification.
    low_threshold : float
        Annualized vol below this = low-vol regime.
    high_threshold : float
        Annualized vol above this = high-vol regime.

    Returns
    -------
    pd.DataFrame
        Signal scores 0.0 / 0.5 / 1.0 per asset per day.
    """
    returns = prices.pct_change()
    vol = returns.rolling(window=short_window).std() * np.sqrt(252)

    # Smooth with longer window to avoid whipsaw
    vol_smooth = vol.rolling(window=long_window, min_periods=short_window).mean()

    signal = pd.DataFrame(0.5, index=prices.index, columns=prices.columns)
    signal[vol_smooth < low_threshold] = 1.0
    signal[vol_smooth > high_threshold] = 0.0
    signal[vol_smooth.isna()] = np.nan

    return signal


def cross_asset_momentum_regime(
    prices: pd.DataFrame,
    lookback: int = 63,
    threshold: float = 0.6,
) -> pd.Series:
    """
    Detect risk-off regime when most assets decline simultaneously.

    When fraction of assets with negative momentum > threshold,
    it signals a broad risk-off environment.

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices.
    lookback : int
        Lookback for momentum calculation.
    threshold : float
        Fraction of assets declining that triggers risk-off (0-1).

    Returns
    -------
    pd.Series
        1.0 = risk-on (few assets declining),
        0.0 = risk-off (most assets declining).
        NaN where insufficient data.
    """
    momentum = prices.pct_change(periods=lookback)
    frac_negative = (momentum < 0).sum(axis=1) / momentum.shape[1]

    signal = pd.Series(1.0, index=prices.index)
    signal[frac_negative > threshold] = 0.0
    signal[momentum.iloc[:, 0].isna()] = np.nan

    return signal


def correlation_regime(
    prices: pd.DataFrame,
    window: int = 63,
    threshold: float = 0.75,
) -> pd.Series:
    """
    Detect correlation regime — crisis when correlations spike.

    During crises, asset correlations tend toward 1.0 and
    diversification breaks down. This signal detects that.

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices (>= 2 columns).
    window : int
        Rolling window for correlation calculation.
    threshold : float
        Average correlation above this = crisis regime.

    Returns
    -------
    pd.Series
        1.0 = normal (low correlation, diversification works),
        0.0 = crisis (high correlation, diversification fails).
        NaN where insufficient data.
    """
    returns = prices.pct_change()
    n_assets = returns.shape[1]

    if n_assets < 2:
        return pd.Series(1.0, index=prices.index)

    avg_corr_series = pd.Series(np.nan, index=prices.index)

    for i in range(window, len(returns)):
        window_returns = returns.iloc[i - window:i]
        corr_matrix = window_returns.corr()
        # Extract upper triangle (exclude diagonal)
        mask = np.triu(np.ones(corr_matrix.shape, dtype=bool), k=1)
        avg_corr = corr_matrix.values[mask].mean()
        avg_corr_series.iloc[i] = avg_corr

    signal = pd.Series(np.nan, index=prices.index)
    valid = avg_corr_series.notna()
    signal[valid] = 1.0
    signal[valid & (avg_corr_series > threshold)] = 0.0

    return signal


def composite_regime(
    prices: pd.DataFrame,
    vol_weight: float = 0.4,
    momentum_weight: float = 0.3,
    corr_weight: float = 0.3,
    vol_kwargs: dict = None,
    mom_kwargs: dict = None,
    corr_kwargs: dict = None,
) -> pd.Series:
    """
    Combine multiple regime indicators into a single composite score.

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices.
    vol_weight, momentum_weight, corr_weight : float
        Weights for each regime signal (should sum to 1.0).
    vol_kwargs, mom_kwargs, corr_kwargs : dict
        Keyword arguments for each sub-signal.

    Returns
    -------
    pd.Series
        Composite regime score 0.0 (crisis) to 1.0 (risk-on).
    """
    vol_kwargs = vol_kwargs or {}
    mom_kwargs = mom_kwargs or {}
    corr_kwargs = corr_kwargs or {}

    # Vol regime: average across assets → single series
    vol_sig = realized_vol_regime(prices, **vol_kwargs).mean(axis=1)
    mom_sig = cross_asset_momentum_regime(prices, **mom_kwargs)
    corr_sig = correlation_regime(prices, **corr_kwargs)

    # Combine with weights, handling NaN
    composite = pd.Series(np.nan, index=prices.index)
    all_valid = vol_sig.notna() & mom_sig.notna() & corr_sig.notna()
    composite[all_valid] = (
        vol_weight * vol_sig[all_valid]
        + momentum_weight * mom_sig[all_valid]
        + corr_weight * corr_sig[all_valid]
    )

    return composite


def regime_position_scalar(
    regime_score: pd.Series,
    full_threshold: float = 0.6,
    zero_threshold: float = 0.2,
) -> pd.Series:
    """
    Convert regime score to a position scalar (0 to 1).

    Linear interpolation between thresholds:
    - score >= full_threshold → scalar = 1.0 (full position)
    - score <= zero_threshold → scalar = 0.0 (no position)
    - between → linear interpolation

    Parameters
    ----------
    regime_score : pd.Series
        Composite regime score (0 to 1).
    full_threshold : float
        Score above which full positions are taken.
    zero_threshold : float
        Score below which positions are zeroed.

    Returns
    -------
    pd.Series
        Position scalar 0.0 to 1.0.
    """
    scalar = (regime_score - zero_threshold) / (full_threshold - zero_threshold)
    scalar = scalar.clip(0.0, 1.0)
    scalar[regime_score.isna()] = np.nan
    return scalar


if __name__ == "__main__":
    # Demo with synthetic data
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=500, freq="D")
    prices = pd.DataFrame({
        "SPY": 100 * np.exp(np.cumsum(np.random.normal(0.0004, 0.015, 500))),
        "TLT": 100 * np.exp(np.cumsum(np.random.normal(0.0001, 0.010, 500))),
        "GLD": 100 * np.exp(np.cumsum(np.random.normal(0.0002, 0.012, 500))),
    }, index=dates)

    print("Regime Signals Demo")
    print("=" * 50)

    vol_sig = realized_vol_regime(prices)
    print(f"\nVol Regime (last 5 days):\n{vol_sig.tail()}")

    mom_sig = cross_asset_momentum_regime(prices)
    print(f"\nCross-Asset Momentum Regime (last 5):\n{mom_sig.tail()}")

    comp = composite_regime(prices)
    print(f"\nComposite Regime (last 5):\n{comp.tail()}")

    scalar = regime_position_scalar(comp)
    print(f"\nPosition Scalar (last 5):\n{scalar.tail()}")
