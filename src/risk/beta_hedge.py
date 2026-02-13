# src/risk/beta_hedge.py
"""
Beta hedge overlay — reduces portfolio beta exposure.

Three public functions:
- compute_beta: rolling beta of each asset vs. a benchmark
- beta_hedge_weights: adjust weights to reduce portfolio beta
- apply_beta_hedge_overlay: full backtest loop with beta hedge + drawdown/vol controls
"""

import pandas as pd
import numpy as np
from typing import Optional

from src.core.settings import BacktestSettings


def compute_beta(
    asset_returns: pd.DataFrame,
    benchmark_returns: pd.Series,
    lookback: int = 252,
) -> pd.DataFrame:
    """
    Compute rolling beta of each asset vs. benchmark.

    beta_i = cov(asset_i, benchmark) / var(benchmark)

    Parameters
    ----------
    asset_returns : pd.DataFrame
        Daily asset returns (columns = tickers).
    benchmark_returns : pd.Series
        Daily benchmark returns aligned to asset_returns index.
    lookback : int
        Rolling window in trading days.

    Returns
    -------
    pd.DataFrame
        Rolling beta per asset. First (lookback-1) rows are NaN.
    """
    betas = pd.DataFrame(index=asset_returns.index, columns=asset_returns.columns, dtype=float)

    bench_var = benchmark_returns.rolling(window=lookback, min_periods=lookback).var()

    for col in asset_returns.columns:
        cov = asset_returns[col].rolling(window=lookback, min_periods=lookback).cov(benchmark_returns)
        # Guard against zero variance
        beta_col = np.where(bench_var > 0, cov / bench_var, np.nan)
        betas[col] = beta_col

    return betas


def beta_hedge_weights(
    weights: pd.Series,
    betas: pd.Series,
    hedge_ratio: float = 1.0,
) -> pd.Series:
    """
    Adjust weights to reduce portfolio beta.

    A hedge_ratio of 1.0 targets a portfolio beta of 0 (full hedge).
    A hedge_ratio of 0.5 halves the portfolio beta.

    High-beta assets have their weights reduced proportionally.
    The adjusted weights are clipped to [0, 1] (long-only) and
    rescaled to preserve the original total weight (cash buffer if
    total drops below original sum is intentional).

    Parameters
    ----------
    weights : pd.Series
        Current portfolio weights (should sum to <= 1).
    betas : pd.Series
        Per-asset beta vs. benchmark.
    hedge_ratio : float
        Fraction of portfolio beta to hedge away (0 = no hedge, 1 = full).

    Returns
    -------
    pd.Series
        Adjusted weights. Not forced to re-normalize; difference is cash buffer.
    """
    if weights.sum() == 0:
        return weights.copy()

    portfolio_beta = (weights * betas).sum()

    if portfolio_beta <= 0:
        return weights.copy()

    # avg_beta per unit weight
    avg_beta = portfolio_beta / weights.sum()

    # Reduce each asset weight proportionally to its beta excess
    # Assets with beta > avg_beta get cut more; beta < avg_beta get cut less
    adjusted = weights * (1 - betas / (avg_beta + 1e-9) * hedge_ratio)
    adjusted = adjusted.clip(lower=0)  # long-only

    # Rescale to preserve original total weight
    total_orig = weights.sum()
    if adjusted.sum() > 0:
        adjusted = adjusted * total_orig / adjusted.sum()

    return adjusted


def apply_beta_hedge_overlay(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    benchmark_col: str = 'SPY',
    hedge_ratio: float = 1.0,
    beta_lookback: int = 252,
    initial_capital: float = 100.0,
    transaction_cost: float = 0.0005,
    rebalance_frequency: str = 'M',
    dd_threshold_1: float = -0.10,
    dd_threshold_2: float = -0.20,
    dd_scale_1: float = 0.50,
    dd_scale_2: float = 0.00,
    vol_target: Optional[float] = None,
    vol_lookback: int = 60,
    vol_max_leverage: float = 1.5,
    settings: Optional[BacktestSettings] = None,
) -> pd.DataFrame:
    """
    Run backtest with beta hedge overlay applied on top of drawdown/vol controls.

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices. Must include benchmark_col.
    signals : pd.DataFrame
        Trading signals (0 or 1), same columns as prices.
    benchmark_col : str
        Column in prices used as benchmark for beta calculation.
    hedge_ratio : float
        Fraction of portfolio beta to hedge (0 = disabled, 1 = full hedge).
    beta_lookback : int
        Rolling window for beta estimation.
    initial_capital : float
        Starting portfolio value.
    transaction_cost : float
        Cost per unit of turnover.
    rebalance_frequency : str
        'D', 'W', or 'M'.
    dd_threshold_1 : float
        First drawdown trigger (e.g. -0.10).
    dd_threshold_2 : float
        Second drawdown trigger (e.g. -0.20).
    dd_scale_1 : float
        Position scalar at first trigger.
    dd_scale_2 : float
        Position scalar at second trigger.
    vol_target : float or None
        Target annualized volatility. None disables vol scaling.
    vol_lookback : int
        Window for realized volatility estimate.
    vol_max_leverage : float
        Maximum vol scalar.
    settings : BacktestSettings or None
        If provided, overrides capital/cost/frequency params.

    Returns
    -------
    pd.DataFrame
        Columns: portfolio_value, returns, positions, turnover
    """
    if benchmark_col not in prices.columns:
        raise ValueError(
            f"benchmark_col '{benchmark_col}' not found in prices columns: {list(prices.columns)}"
        )

    runtime = settings or BacktestSettings(
        initial_capital=initial_capital,
        transaction_cost=transaction_cost,
        rebalance_frequency=rebalance_frequency,
        position_size="equal_weight",
    )
    runtime.validate()

    daily_returns = prices.pct_change()
    benchmark_returns = daily_returns[benchmark_col]

    # Pre-compute rolling beta for all assets once
    all_betas = compute_beta(daily_returns, benchmark_returns, lookback=beta_lookback)

    signals_shifted = signals.shift(1).fillna(0)

    if runtime.rebalance_frequency == 'M':
        rebalance_dates = pd.date_range(
            start=prices.index[0], end=prices.index[-1], freq='MS')
    elif runtime.rebalance_frequency == 'W':
        rebalance_dates = pd.date_range(
            start=prices.index[0], end=prices.index[-1], freq='W')
    else:
        rebalance_dates = prices.index

    portfolio_value = pd.Series(index=prices.index, dtype=float)
    portfolio_value.iloc[0] = runtime.initial_capital
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

            # Apply combined scalar from drawdown + vol controls
            combined_scalar = dd_scalar * vol_scalar
            target_weights = target_weights * combined_scalar

            # ── Beta hedge overlay (applied after combined scalar, before turnover) ──
            if hedge_ratio > 0:
                current_betas = all_betas.loc[date]
                if not current_betas.isna().all():
                    # Fill any NaN betas with 1.0 (assume market-like exposure)
                    current_betas = current_betas.fillna(1.0)
                    target_weights = beta_hedge_weights(
                        target_weights, current_betas, hedge_ratio=hedge_ratio
                    )

            turnover.iloc[i] = (target_weights - prev_weights).abs().sum()
            tc_cost = turnover.iloc[i] * runtime.transaction_cost
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
