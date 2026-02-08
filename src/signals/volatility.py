# src/signals/volatility.py
"""
Volatility-based signals — low correlation with momentum.

Generates trading signals from volatility structure:
- Vol term structure: short-term vs long-term realized vol
- Vol of vol: second-order volatility as uncertainty measure
- Vol mean reversion: extreme vol tends to revert

These signals exploit the mean-reverting nature of volatility
and are largely orthogonal to price momentum signals.
"""

import pandas as pd
import numpy as np


def vol_term_structure(
    prices: pd.DataFrame,
    short_window: int = 21,
    long_window: int = 63,
) -> pd.DataFrame:
    """
    Vol term structure signal: compare short-term vs long-term realized vol.

    When short-term vol > long-term vol (backwardation/inverted):
    → Market stress, reduce exposure (signal < 0.5)

    When short-term vol < long-term vol (contango/normal):
    → Calm market, maintain exposure (signal > 0.5)

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices.
    short_window : int
        Window for short-term vol (default 21 = ~1 month).
    long_window : int
        Window for long-term vol (default 63 = ~3 months).

    Returns
    -------
    pd.DataFrame
        Signal values 0.0 to 1.0 per asset.
        >0.5 = normal (contango), <0.5 = stressed (backwardation).
    """
    returns = prices.pct_change()
    short_vol = returns.rolling(window=short_window).std() * np.sqrt(252)
    long_vol = returns.rolling(window=long_window).std() * np.sqrt(252)

    # Ratio: < 1 means short vol < long vol (calm), > 1 means stressed
    ratio = short_vol / long_vol

    # Convert to 0-1 signal: use sigmoid-like mapping
    # ratio = 1.0 → signal = 0.5 (neutral)
    # ratio = 0.5 → signal ≈ 1.0 (very calm)
    # ratio = 1.5 → signal ≈ 0.0 (very stressed)
    signal = 1.0 / (1.0 + np.exp(5 * (ratio - 1.0)))

    signal[long_vol.isna()] = np.nan
    return signal


def vol_of_vol(
    prices: pd.DataFrame,
    vol_window: int = 21,
    vov_window: int = 63,
    high_percentile: float = 0.80,
) -> pd.DataFrame:
    """
    Volatility of volatility signal — uncertainty measure.

    High vol-of-vol indicates regime uncertainty. Strategy should
    reduce exposure when uncertainty is elevated.

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices.
    vol_window : int
        Window for first-order vol calculation.
    vov_window : int
        Window for second-order vol (vol of vol).
    high_percentile : float
        Expanding percentile above which vol-of-vol is "high".

    Returns
    -------
    pd.DataFrame
        Signal 1.0 (low uncertainty) to 0.0 (high uncertainty).
    """
    returns = prices.pct_change()
    vol = returns.rolling(window=vol_window).std()

    # Vol of vol = rolling std of the vol series
    vov = vol.rolling(window=vov_window).std()

    # Percentile rank: what fraction of historical vov is below current?
    vov_pctile = vov.expanding(min_periods=vov_window).apply(
        lambda x: (x.iloc[:-1] < x.iloc[-1]).mean() if len(x) > 1 else np.nan,
        raw=False,
    )

    # High vov percentile → low signal (reduce exposure)
    signal = 1.0 - vov_pctile

    signal[vov.isna()] = np.nan
    return signal


def vol_mean_reversion(
    prices: pd.DataFrame,
    vol_window: int = 21,
    zscore_window: int = 252,
    entry_z: float = 1.5,
    exit_z: float = 0.0,
) -> pd.DataFrame:
    """
    Volatility mean reversion signal.

    When vol is extremely high (z-score > entry_z), it tends to revert down,
    which is bullish for risk assets. When vol is extremely low, it
    can spike, which is bearish.

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices.
    vol_window : int
        Window for realized vol.
    zscore_window : int
        Lookback for z-score calculation.
    entry_z : float
        Z-score threshold for high-vol (expect reversion → go long).
    exit_z : float
        Z-score threshold for neutral.

    Returns
    -------
    pd.DataFrame
        Signal: 1.0 = expect vol to drop (bullish), 0.0 = expect vol spike.
    """
    returns = prices.pct_change()
    vol = returns.rolling(window=vol_window).std() * np.sqrt(252)

    vol_mean = vol.rolling(window=zscore_window).mean()
    vol_std = vol.rolling(window=zscore_window).std()

    zscore = (vol - vol_mean) / vol_std

    # High vol z-score → vol will likely revert down → bullish
    # Low vol z-score → vol may spike → bearish
    # Map: z > entry_z → 1.0, z < -entry_z → 0.0, linear between
    signal = 0.5 + (zscore / (2 * entry_z))
    signal = signal.clip(0.0, 1.0)

    signal[vol_std.isna()] = np.nan
    return signal


def generate_vol_signal(
    prices: pd.DataFrame,
    method: str = "term_structure",
    **kwargs,
) -> pd.DataFrame:
    """
    Convenience function for volatility signals.

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices.
    method : str
        One of: 'term_structure', 'vol_of_vol', 'mean_reversion'.
    **kwargs
        Passed to the underlying signal function.

    Returns
    -------
    pd.DataFrame
        Signal values.
    """
    methods = {
        "term_structure": vol_term_structure,
        "vol_of_vol": vol_of_vol,
        "mean_reversion": vol_mean_reversion,
    }

    if method not in methods:
        raise ValueError(
            f"Unknown method '{method}'. Available: {list(methods.keys())}"
        )

    return methods[method](prices, **kwargs)


if __name__ == "__main__":
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=500, freq="D")
    prices = pd.DataFrame({
        "SPY": 100 * np.exp(np.cumsum(np.random.normal(0.0004, 0.015, 500))),
        "TLT": 100 * np.exp(np.cumsum(np.random.normal(0.0001, 0.010, 500))),
        "GLD": 100 * np.exp(np.cumsum(np.random.normal(0.0002, 0.012, 500))),
    }, index=dates)

    print("Volatility Signals Demo")
    print("=" * 50)

    ts = vol_term_structure(prices)
    print(f"\nVol Term Structure (last 5):\n{ts.tail()}")

    vov = vol_of_vol(prices)
    print(f"\nVol of Vol (last 5):\n{vov.tail()}")

    mr = vol_mean_reversion(prices)
    print(f"\nVol Mean Reversion (last 5):\n{mr.tail()}")
