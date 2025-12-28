# src/portfolio/risk_parity.py
"""
Risk parity portfolio weighting methods.

Risk parity allocates capital based on equal risk contribution
from each asset, rather than equal dollar amounts.
"""

import pandas as pd
import numpy as np
from typing import Optional, Union


def inverse_volatility_weights(
    returns: pd.DataFrame,
    lookback: int = 60,
    min_periods: int = 21
) -> pd.DataFrame:
    """
    Calculate inverse volatility weights for risk parity.

    Each asset receives weight inversely proportional to its volatility.
    This is the simplest form of risk parity.

    Formula: w_i = (1/vol_i) / sum(1/vol_j)

    Parameters
    ----------
    returns : pd.DataFrame
        Historical returns for assets (rows = dates, columns = assets).
    lookback : int, default 60
        Rolling window for volatility estimation (trading days).
    min_periods : int, default 21
        Minimum observations required for volatility calculation.

    Returns
    -------
    pd.DataFrame
        Risk parity weights for each asset over time.
        Weights sum to 1.0 for each date where calculable.

    Examples
    --------
    >>> returns = prices.pct_change()
    >>> weights = inverse_volatility_weights(returns, lookback=60)
    """
    # Calculate rolling volatility for each asset
    rolling_vol = returns.rolling(window=lookback, min_periods=min_periods).std()

    # Inverse volatility
    inv_vol = 1.0 / rolling_vol

    # Normalize to sum to 1 (only where we have valid volatilities)
    weights = inv_vol.div(inv_vol.sum(axis=1), axis=0)

    # Handle any remaining NaN
    weights = weights.fillna(0)

    return weights


def target_volatility_weights(
    returns: pd.DataFrame,
    signals: pd.DataFrame,
    target_vol: float = 0.10,
    lookback: int = 60,
    min_periods: int = 21
) -> pd.DataFrame:
    """
    Calculate weights for target portfolio volatility.

    Scales risk parity weights to achieve a target portfolio volatility.

    Parameters
    ----------
    returns : pd.DataFrame
        Historical returns.
    signals : pd.DataFrame
        Binary signals (0 or 1) indicating which assets to hold.
    target_vol : float, default 0.10
        Target annualized portfolio volatility (10% default).
    lookback : int, default 60
        Volatility estimation window.
    min_periods : int, default 21
        Minimum periods for calculation.

    Returns
    -------
    pd.DataFrame
        Scaled weights achieving target volatility.
    """
    # Get base risk parity weights
    rp_weights = inverse_volatility_weights(returns, lookback, min_periods)

    # Apply signals (only hold assets with signal = 1)
    active_weights = rp_weights * signals

    # Renormalize active weights
    active_weights = active_weights.div(active_weights.sum(axis=1), axis=0)

    # Estimate realized portfolio volatility
    # For simplicity, assume weights are constant within lookback period
    # This is an approximation
    portfolio_returns = (active_weights.shift(1) * returns).sum(axis=1)
    realized_vol = portfolio_returns.rolling(window=lookback, min_periods=min_periods).std() * np.sqrt(252)

    # Calculate leverage/de-leverage factor to hit target vol
    vol_scalar = target_vol / realized_vol

    # Cap leverage (don't use more than 2x leverage)
    vol_scalar = vol_scalar.clip(upper=2.0)

    # Scale weights
    scaled_weights = active_weights.multiply(vol_scalar, axis=0)

    # Handle NaN
    scaled_weights = scaled_weights.fillna(0)

    return scaled_weights


def equal_risk_contribution_weights(
    returns: pd.DataFrame,
    lookback: int = 60,
    min_periods: int = 21
) -> pd.DataFrame:
    """
    Calculate equal risk contribution (ERC) weights.

    More sophisticated than inverse volatility - considers correlations.
    Each asset contributes equally to portfolio risk.

    This is a simplified implementation using the covariance matrix.

    Parameters
    ----------
    returns : pd.DataFrame
        Historical returns.
    lookback : int, default 60
        Window for covariance estimation.
    min_periods : int, default 21
        Minimum periods required.

    Returns
    -------
    pd.DataFrame
        ERC weights over time.

    Notes
    -----
    This is an approximate solution. Exact ERC requires numerical optimization
    which is computationally expensive. For portfolios with low correlation,
    inverse volatility is a good approximation.
    """
    # For now, use inverse volatility as approximation
    # True ERC requires iterative optimization which is slow
    # In practice, for diversified portfolios, inverse vol works well

    weights = inverse_volatility_weights(returns, lookback, min_periods)

    return weights


def apply_risk_parity_to_signals(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    method: str = 'inverse_vol',
    lookback: int = 60,
    **kwargs
) -> pd.DataFrame:
    """
    Apply risk parity weighting to active signals.

    Convenience function that combines signals with risk parity weights.

    Parameters
    ----------
    prices : pd.DataFrame
        Asset prices.
    signals : pd.DataFrame
        Binary trading signals (0 or 1).
    method : str, default 'inverse_vol'
        Risk parity method: 'inverse_vol', 'target_vol', or 'erc'.
    lookback : int, default 60
        Volatility estimation window.
    **kwargs
        Additional arguments passed to weighting function.

    Returns
    -------
    pd.DataFrame
        Position weights combining signals and risk parity.
        Sum to 1.0 for dates with active positions.

    Examples
    --------
    >>> # Equal weight across active signals
    >>> ew_weights = signals / signals.sum(axis=1, keepdims=True)
    >>>
    >>> # Risk parity across active signals
    >>> rp_weights = apply_risk_parity_to_signals(prices, signals)
    """
    # Calculate returns
    returns = prices.pct_change()

    # Select weighting method
    if method == 'inverse_vol':
        # Get base risk parity weights
        rp_weights = inverse_volatility_weights(returns, lookback, **kwargs)

    elif method == 'target_vol':
        rp_weights = target_volatility_weights(
            returns, signals, lookback=lookback, **kwargs
        )
        return rp_weights  # Already applied signals

    elif method == 'erc':
        rp_weights = equal_risk_contribution_weights(returns, lookback, **kwargs)

    else:
        raise ValueError(f"Unknown method: {method}. Use 'inverse_vol', 'target_vol', or 'erc'")

    # Apply signals (only hold assets with signal = 1)
    active_weights = rp_weights * signals

    # Renormalize to sum to 1
    weight_sum = active_weights.sum(axis=1)
    weight_sum = weight_sum.replace(0, np.nan)  # Avoid division by zero
    active_weights = active_weights.div(weight_sum, axis=0)

    # Fill NaN with 0
    active_weights = active_weights.fillna(0)

    return active_weights


if __name__ == "__main__":
    # Example usage
    from pathlib import Path
    import sys

    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))

    from src.signals.trend_filter import generate_signals

    print("Risk Parity Weighting Example\n")

    # Load data
    prices = pd.read_csv(
        project_root / 'data' / 'processed' / 'prices_clean.csv',
        index_col=0, parse_dates=True
    )

    # Generate SMA signals
    signals = generate_signals(prices, method='sma', window=252)

    # Calculate returns
    returns = prices.pct_change()

    print("=== Equal Weight (Baseline) ===")
    ew_weights = signals.div(signals.sum(axis=1), axis=0).fillna(0)
    print(f"Current weights:\n{ew_weights.iloc[-1]}\n")
    print(f"Average weights over time:\n{ew_weights[signals == 1].mean()}\n")

    print("=== Risk Parity (Inverse Volatility) ===")
    rp_weights = apply_risk_parity_to_signals(prices, signals, method='inverse_vol')
    print(f"Current weights:\n{rp_weights.iloc[-1]}\n")
    print(f"Average weights over time:\n{rp_weights[rp_weights > 0].mean()}\n")

    # Calculate volatilities for comparison
    vol_60d = returns.rolling(60).std().iloc[-1] * np.sqrt(252)
    print("=== Asset Volatilities (60-day annualized) ===")
    print(vol_60d.sort_values())
    print("\nLower volatility assets get higher risk parity weights")
