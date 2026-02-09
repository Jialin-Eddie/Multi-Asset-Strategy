# src/risk/overlay.py
"""
Risk overlay layer — independent of signals.

Applies position-level risk controls on top of any strategy:
- Drawdown control: reduce exposure when drawdown exceeds threshold
- Volatility scaling: target a specific portfolio volatility
- Correlation circuit breaker: warn when diversification breaks down
"""

import pandas as pd
import numpy as np


def drawdown_scalar(
    portfolio_value: pd.Series,
    threshold_1: float = -0.10,
    threshold_2: float = -0.20,
    scale_1: float = 0.50,
    scale_2: float = 0.00,
) -> pd.Series:
    """
    Scale positions down as drawdown deepens. Two-tier system:

    - Drawdown hits threshold_1 → reduce to scale_1 (e.g. 50%)
    - Drawdown hits threshold_2 → reduce to scale_2 (e.g. 0%, full exit)

    Parameters
    ----------
    portfolio_value : pd.Series
        Portfolio value time series.
    threshold_1 : float
        First drawdown level (e.g. -0.10 = -10%).
    threshold_2 : float
        Second drawdown level (e.g. -0.20 = -20%).
    scale_1 : float
        Position scalar at threshold_1.
    scale_2 : float
        Position scalar at threshold_2.

    Returns
    -------
    pd.Series
        Scalar 0.0–1.0 for each date.
    """
    running_max = portfolio_value.expanding().max()
    drawdown = (portfolio_value - running_max) / running_max

    scalar = pd.Series(1.0, index=portfolio_value.index)
    scalar[drawdown <= threshold_1] = scale_1
    scalar[drawdown <= threshold_2] = scale_2

    return scalar


def volatility_scalar(
    returns: pd.Series,
    target_vol: float = 0.10,
    lookback: int = 60,
    max_leverage: float = 1.5,
    min_scalar: float = 0.1,
) -> pd.Series:
    """
    Scale positions to target a specific portfolio volatility.

    scalar = target_vol / realized_vol, capped at max_leverage.

    Parameters
    ----------
    returns : pd.Series
        Daily portfolio returns.
    target_vol : float
        Target annualized volatility (default 10%).
    lookback : int
        Rolling window for vol estimation (trading days).
    max_leverage : float
        Maximum scalar (prevents over-leveraging in low-vol periods).
    min_scalar : float
        Minimum scalar (prevents near-zero positions).

    Returns
    -------
    pd.Series
        Scalar for each date.
    """
    realized_vol = returns.rolling(window=lookback, min_periods=21).std() * np.sqrt(252)
    scalar = target_vol / realized_vol
    scalar = scalar.clip(lower=min_scalar, upper=max_leverage)
    scalar = scalar.fillna(1.0)
    return scalar


def apply_risk_overlay(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    initial_capital: float = 100.0,
    transaction_cost: float = 0.0005,
    rebalance_frequency: str = 'M',
    dd_threshold_1: float = -0.10,
    dd_threshold_2: float = -0.20,
    dd_scale_1: float = 0.50,
    dd_scale_2: float = 0.00,
    vol_target: float = None,
    vol_lookback: int = 60,
    vol_max_leverage: float = 1.5,
) -> pd.DataFrame:
    """
    Run backtest with risk overlay applied.

    This wraps the standard backtest loop but applies drawdown control
    and optional volatility scaling on top of signal-driven weights.

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices.
    signals : pd.DataFrame
        Trading signals (0 or 1).
    initial_capital : float
        Starting capital.
    transaction_cost : float
        Cost per unit of turnover.
    rebalance_frequency : str
        'D', 'W', or 'M'.
    dd_threshold_1 : float
        First drawdown trigger (e.g. -0.10).
    dd_threshold_2 : float
        Second drawdown trigger (e.g. -0.20).
    dd_scale_1 : float
        Scale at first trigger.
    dd_scale_2 : float
        Scale at second trigger.
    vol_target : float or None
        Target vol. None = no vol scaling.
    vol_lookback : int
        Vol estimation window.
    vol_max_leverage : float
        Max vol scalar.

    Returns
    -------
    pd.DataFrame
        Same format as engine.calculate_strategy_returns():
        portfolio_value, returns, positions, turnover
    """
    daily_returns = prices.pct_change()
    signals_shifted = signals.shift(1).fillna(0)

    if rebalance_frequency == 'M':
        rebalance_dates = pd.date_range(
            start=prices.index[0], end=prices.index[-1], freq='MS')
    elif rebalance_frequency == 'W':
        rebalance_dates = pd.date_range(
            start=prices.index[0], end=prices.index[-1], freq='W')
    else:
        rebalance_dates = prices.index

    portfolio_value = pd.Series(index=prices.index, dtype=float)
    portfolio_value.iloc[0] = initial_capital
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    turnover = pd.Series(0.0, index=prices.index)
    prev_weights = pd.Series(0.0, index=prices.columns)
    portfolio_returns = pd.Series(0.0, index=prices.index)

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

            # ── Drawdown control ──
            dd_scalar = 1.0
            if i > 1:
                pv_so_far = portfolio_value.iloc[:i].dropna()
                if len(pv_so_far) > 0:
                    peak = pv_so_far.max()
                    current_dd = (pv_so_far.iloc[-1] - peak) / peak
                    if current_dd <= dd_threshold_2:
                        dd_scalar = dd_scale_2
                    elif current_dd <= dd_threshold_1:
                        dd_scalar = dd_scale_1

            # ── Vol scaling ──
            vol_scalar = 1.0
            if vol_target is not None and i > vol_lookback:
                recent_returns = portfolio_returns.iloc[max(0, i - vol_lookback):i]
                realized = recent_returns.std() * np.sqrt(252)
                if realized > 0:
                    vol_scalar = min(vol_target / realized, vol_max_leverage)
                    vol_scalar = max(vol_scalar, 0.1)

            # Apply combined scalar
            combined_scalar = dd_scalar * vol_scalar
            target_weights = target_weights * combined_scalar

            turnover.iloc[i] = (target_weights - prev_weights).abs().sum()
            tc_cost = turnover.iloc[i] * transaction_cost
            portfolio_value.iloc[i] = portfolio_value.iloc[i - 1] * (1 - tc_cost)
            weights.loc[date] = target_weights
            prev_weights = target_weights
        else:
            portfolio_value.iloc[i] = portfolio_value.iloc[i - 1]
            weights.loc[date] = prev_weights

        period_return = (weights.loc[date] * daily_returns.loc[date]).sum()
        portfolio_value.iloc[i] = portfolio_value.iloc[i] * (1 + period_return)
        portfolio_returns.iloc[i] = period_return

        if not is_rebalance:
            individual_returns = daily_returns.loc[date]
            if period_return != -1:
                prev_weights = prev_weights * (1 + individual_returns) / (1 + period_return)
                prev_weights = prev_weights.fillna(0)

    positions = signals_shifted.sum(axis=1)

    return pd.DataFrame({
        'portfolio_value': portfolio_value,
        'returns': portfolio_value.pct_change().fillna(0),
        'positions': positions,
        'turnover': turnover,
    })
