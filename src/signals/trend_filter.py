# src/signals/trend_filter.py
"""
Trend filter signal generation for multi-asset portfolio.

This module implements various trend-following indicators:
- Simple Moving Average (SMA) crossover
- Exponential Moving Average (EMA) crossover
- Absolute momentum (time-series momentum)
- Relative momentum (cross-sectional momentum)
- Dual momentum (combination of absolute and relative)
"""

import pandas as pd
import numpy as np
from typing import Union


def calculate_sma(prices: pd.DataFrame, window: int) -> pd.DataFrame:
    """
    Calculate Simple Moving Average for each column in DataFrame.

    Parameters
    ----------
    prices : pd.DataFrame
        DataFrame of asset prices with DatetimeIndex.
    window : int
        Lookback window for moving average (e.g., 252 for 12-month MA).

    Returns
    -------
    pd.DataFrame
        DataFrame of SMA values, same shape as input.
        First (window-1) rows will be NaN.

    Raises
    ------
    ValueError
        If window is <= 0.
    """
    if window <= 0:
        raise ValueError(f"Window must be positive, got {window}")

    return prices.rolling(window=window, min_periods=window).mean()


def sma_trend_signal(prices: pd.DataFrame, window: int = 252) -> pd.DataFrame:
    """
    Generate trend signals based on price vs SMA.

    Signal = 1 if price > SMA, else 0.

    Parameters
    ----------
    prices : pd.DataFrame
        DataFrame of asset prices.
    window : int, default 252
        Lookback window for SMA (252 trading days ≈ 12 months).

    Returns
    -------
    pd.DataFrame
        DataFrame of signals (0 or 1), NaN where insufficient data.
    """
    sma = calculate_sma(prices, window)

    # Signal: 1 if price > SMA, 0 otherwise
    signals = (prices > sma).astype(float)

    # Set to NaN where SMA is NaN (insufficient data)
    signals[sma.isna()] = np.nan

    return signals


def calculate_ema(prices: pd.DataFrame, span: int) -> pd.DataFrame:
    """
    Calculate Exponential Moving Average for each column.

    EMA gives more weight to recent prices using exponential decay.

    Parameters
    ----------
    prices : pd.DataFrame
        DataFrame of asset prices.
    span : int
        Span for EMA calculation (equivalent to window for comparison).
        Roughly span ≈ 2/(1-α) where α is the smoothing factor.

    Returns
    -------
    pd.DataFrame
        DataFrame of EMA values, same shape as input.
    """
    return prices.ewm(span=span, adjust=False).mean()


def ema_trend_signal(prices: pd.DataFrame, span: int = 252) -> pd.DataFrame:
    """
    Generate trend signals based on price vs EMA.

    Signal = 1 if price > EMA, else 0.

    Parameters
    ----------
    prices : pd.DataFrame
        DataFrame of asset prices.
    span : int, default 252
        Span for EMA calculation.

    Returns
    -------
    pd.DataFrame
        DataFrame of signals (0 or 1).
    """
    ema = calculate_ema(prices, span)

    # Signal: 1 if price > EMA, 0 otherwise
    signals = (prices > ema).astype(float)

    return signals


def calculate_momentum(prices: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """
    Calculate momentum as percentage return over lookback period.

    Momentum = (Price_t / Price_{t-lookback}) - 1

    Parameters
    ----------
    prices : pd.DataFrame
        DataFrame of asset prices.
    lookback : int
        Lookback period in days (e.g., 252 for 12-month momentum).

    Returns
    -------
    pd.DataFrame
        DataFrame of momentum values (percentage returns).
        First lookback rows will be NaN.
    """
    return prices.pct_change(periods=lookback)


def absolute_momentum_signal(
    prices: pd.DataFrame,
    lookback: int = 252,
    threshold: float = 0.0
) -> pd.DataFrame:
    """
    Generate absolute (time-series) momentum signals.

    Signal = 1 if momentum > threshold, else 0.
    This captures whether each asset is trending up or down.

    Parameters
    ----------
    prices : pd.DataFrame
        DataFrame of asset prices.
    lookback : int, default 252
        Lookback period for momentum calculation (12 months).
    threshold : float, default 0.0
        Minimum momentum to generate long signal.
        0.0 means positive momentum required.

    Returns
    -------
    pd.DataFrame
        DataFrame of signals (0 or 1), NaN where insufficient data.
    """
    momentum = calculate_momentum(prices, lookback)

    # Signal: 1 if momentum > threshold, 0 otherwise
    signals = (momentum > threshold).astype(float)

    # Set to NaN where momentum is NaN
    signals[momentum.isna()] = np.nan

    return signals


def relative_momentum_signal(
    prices: pd.DataFrame,
    lookback: int = 252,
    top_n: int = 1
) -> pd.DataFrame:
    """
    Generate relative (cross-sectional) momentum signals.

    Ranks assets by momentum and signals top N performers.
    Signal = 1 for top N assets, 0 for others.

    Parameters
    ----------
    prices : pd.DataFrame
        DataFrame of asset prices.
    lookback : int, default 252
        Lookback period for momentum calculation.
    top_n : int, default 1
        Number of top-performing assets to signal.

    Returns
    -------
    pd.DataFrame
        DataFrame of signals (0 or 1), NaN where insufficient data.
    """
    momentum = calculate_momentum(prices, lookback)

    # Rank assets by momentum (higher is better)
    # rank(ascending=False) gives 1 to highest, 2 to second, etc.
    ranks = momentum.rank(axis=1, ascending=False)

    # Signal top N
    signals = (ranks <= top_n).astype(float)

    # Set to NaN where momentum is NaN
    signals[momentum.isna()] = np.nan

    return signals


def dual_momentum_signal(
    prices: pd.DataFrame,
    lookback: int = 252,
    top_n: int = 1,
    abs_threshold: float = 0.0
) -> pd.DataFrame:
    """
    Generate dual momentum signals (absolute AND relative).

    Combines time-series and cross-sectional momentum:
    1. Asset must have positive absolute momentum (trending up)
    2. Asset must be in top N by relative momentum

    Signal = 1 only if BOTH conditions are met.

    This is the strategy from Gary Antonacci's "Dual Momentum Investing".

    Parameters
    ----------
    prices : pd.DataFrame
        DataFrame of asset prices.
    lookback : int, default 252
        Lookback period for momentum calculation.
    top_n : int, default 1
        Number of top-performing assets to select.
    abs_threshold : float, default 0.0
        Minimum absolute momentum threshold.

    Returns
    -------
    pd.DataFrame
        DataFrame of signals (0 or 1), NaN where insufficient data.
    """
    # Get both signals
    abs_signals = absolute_momentum_signal(prices, lookback, abs_threshold)
    rel_signals = relative_momentum_signal(prices, lookback, top_n)

    # Dual momentum: both conditions must be true
    dual_signals = (abs_signals == 1) & (rel_signals == 1)
    dual_signals = dual_signals.astype(float)

    # Set to NaN where either input is NaN
    dual_signals[(abs_signals.isna()) | (rel_signals.isna())] = np.nan

    return dual_signals


def generate_signals(
    prices: pd.DataFrame,
    method: str = 'sma',
    **kwargs
) -> pd.DataFrame:
    """
    Convenience function to generate signals using specified method.

    Parameters
    ----------
    prices : pd.DataFrame
        DataFrame of asset prices.
    method : str, default 'sma'
        Signal generation method. Options:
        - 'sma': Simple moving average crossover
        - 'ema': Exponential moving average crossover
        - 'absolute': Absolute momentum
        - 'relative': Relative momentum
        - 'dual': Dual momentum
    **kwargs
        Additional arguments passed to signal function.

    Returns
    -------
    pd.DataFrame
        DataFrame of signals.

    Raises
    ------
    ValueError
        If method is not recognized.

    Examples
    --------
    >>> signals = generate_signals(prices, method='sma', window=252)
    >>> signals = generate_signals(prices, method='dual', lookback=252, top_n=2)
    """
    methods = {
        'sma': sma_trend_signal,
        'ema': ema_trend_signal,
        'absolute': absolute_momentum_signal,
        'relative': relative_momentum_signal,
        'dual': dual_momentum_signal
    }

    if method not in methods:
        raise ValueError(
            f"Unknown method '{method}'. "
            f"Available methods: {list(methods.keys())}"
        )

    return methods[method](prices, **kwargs)


if __name__ == "__main__":
    # Example usage
    from pathlib import Path

    # Load data
    data_path = Path(__file__).resolve().parents[2] / "data" / "processed" / "prices_clean.csv"
    prices = pd.read_csv(data_path, index_col=0, parse_dates=True)

    print("Generating trend signals...")
    print(f"Data shape: {prices.shape}")
    print(f"Date range: {prices.index.min()} to {prices.index.max()}\n")

    # SMA signals
    sma_signals = generate_signals(prices, method='sma', window=252)
    print("SMA Trend Signals (252-day):")
    print(sma_signals.tail())
    print(f"Current signals: {sma_signals.iloc[-1].to_dict()}\n")

    # Dual momentum signals
    dual_signals = generate_signals(prices, method='dual', lookback=252, top_n=2)
    print("Dual Momentum Signals (top 2):")
    print(dual_signals.tail())
    print(f"Current signals: {dual_signals.iloc[-1].to_dict()}\n")

    # Signal statistics
    print("Signal Statistics (% of time in position):")
    signal_pct = sma_signals.mean() * 100
    print(signal_pct)
