# src/signals/mean_reversion.py
"""
Mean reversion signals — natural hedge to momentum.

Short-term mean reversion signals that counterbalance medium/long-term
trend following. When combined with momentum, they reduce whipsaw
and improve Sharpe by 0.1-0.3 in typical multi-asset portfolios.

Signals:
- Relative value (Z-score): short-term deviation from mean
- RSI: relative strength index for overbought/oversold
- Bollinger band position: price position within bands
"""

import pandas as pd
import numpy as np


def zscore_signal(
    prices: pd.DataFrame,
    lookback: int = 21,
    entry_z: float = 2.0,
) -> pd.DataFrame:
    """
    Short-term Z-score mean reversion signal.

    When price deviates significantly from its short-term mean,
    expect reversion. This is contrarian to momentum.

    Signal mapping (continuous 0-1):
    - Z < -entry_z → 1.0 (oversold, expect bounce)
    - Z > +entry_z → 0.0 (overbought, expect pullback)
    - Z = 0        → 0.5 (neutral)

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices.
    lookback : int
        Lookback window for mean/std calculation.
    entry_z : float
        Z-score magnitude for full signal.

    Returns
    -------
    pd.DataFrame
        Signal 0.0 (overbought) to 1.0 (oversold).
    """
    rolling_mean = prices.rolling(window=lookback).mean()
    rolling_std = prices.rolling(window=lookback).std()

    zscore = (prices - rolling_mean) / rolling_std

    # Invert: negative z → buy signal, positive z → sell signal
    signal = 0.5 - (zscore / (2 * entry_z))
    signal = signal.clip(0.0, 1.0)

    signal[rolling_std.isna()] = np.nan
    return signal


def rsi_signal(
    prices: pd.DataFrame,
    period: int = 14,
    overbought: float = 70.0,
    oversold: float = 30.0,
) -> pd.DataFrame:
    """
    RSI-based mean reversion signal.

    RSI measures the magnitude of recent gains vs losses.
    Extreme RSI levels indicate overbought/oversold conditions.

    Signal mapping:
    - RSI < oversold  → 1.0 (buy signal)
    - RSI > overbought → 0.0 (sell signal)
    - Between → linear interpolation

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices.
    period : int
        RSI calculation period (default 14).
    overbought : float
        RSI level above which = overbought (default 70).
    oversold : float
        RSI level below which = oversold (default 30).

    Returns
    -------
    pd.DataFrame
        Signal 0.0 (overbought) to 1.0 (oversold).
    """
    delta = prices.diff()

    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # Map RSI to signal: oversold=1.0, overbought=0.0
    signal = (overbought - rsi) / (overbought - oversold)
    signal = signal.clip(0.0, 1.0)

    signal[avg_loss.isna()] = np.nan
    # Handle edge case: zero loss → RSI=100 → signal=0
    signal[avg_loss == 0] = 0.0

    return signal


def bollinger_signal(
    prices: pd.DataFrame,
    window: int = 20,
    num_std: float = 2.0,
) -> pd.DataFrame:
    """
    Bollinger Band position as mean reversion signal.

    Measures where price sits within its Bollinger Bands.
    Near lower band = oversold, near upper band = overbought.

    Signal = (upper_band - price) / (upper_band - lower_band)
    - 0.0 = at upper band (overbought)
    - 1.0 = at lower band (oversold)
    - 0.5 = at middle (neutral)

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices.
    window : int
        Moving average window.
    num_std : float
        Number of standard deviations for bands.

    Returns
    -------
    pd.DataFrame
        Signal 0.0 (overbought) to 1.0 (oversold).
    """
    rolling_mean = prices.rolling(window=window).mean()
    rolling_std = prices.rolling(window=window).std()

    upper_band = rolling_mean + num_std * rolling_std
    lower_band = rolling_mean - num_std * rolling_std

    band_width = upper_band - lower_band
    signal = (upper_band - prices) / band_width
    signal = signal.clip(0.0, 1.0)

    signal[rolling_std.isna()] = np.nan
    return signal


def generate_mr_signal(
    prices: pd.DataFrame,
    method: str = "zscore",
    **kwargs,
) -> pd.DataFrame:
    """
    Convenience function for mean reversion signals.

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices.
    method : str
        One of: 'zscore', 'rsi', 'bollinger'.
    **kwargs
        Passed to the underlying signal function.

    Returns
    -------
    pd.DataFrame
        Signal values.
    """
    methods = {
        "zscore": zscore_signal,
        "rsi": rsi_signal,
        "bollinger": bollinger_signal,
    }

    if method not in methods:
        raise ValueError(
            f"Unknown method '{method}'. Available: {list(methods.keys())}"
        )

    return methods[method](prices, **kwargs)


if __name__ == "__main__":
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=300, freq="D")
    prices = pd.DataFrame({
        "SPY": 100 * np.exp(np.cumsum(np.random.normal(0.0004, 0.015, 300))),
        "TLT": 100 * np.exp(np.cumsum(np.random.normal(0.0001, 0.010, 300))),
        "GLD": 100 * np.exp(np.cumsum(np.random.normal(0.0002, 0.012, 300))),
    }, index=dates)

    print("Mean Reversion Signals Demo")
    print("=" * 50)

    zs = zscore_signal(prices)
    print(f"\nZ-Score Signal (last 5):\n{zs.tail()}")

    rsi = rsi_signal(prices)
    print(f"\nRSI Signal (last 5):\n{rsi.tail()}")

    bb = bollinger_signal(prices)
    print(f"\nBollinger Signal (last 5):\n{bb.tail()}")
