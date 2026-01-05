# src/backtest/engine.py
"""
Backtesting engine for multi-asset strategies.

Simple event-driven backtester that:
- Takes price data and signals
- Applies position sizing and rebalancing rules
- Accounts for transaction costs
- Calculates portfolio returns and metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional


def calculate_strategy_returns(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    initial_capital: float = 100.0,
    transaction_cost: float = 0.0005,
    rebalance_frequency: str = 'M',
    position_size: str = 'equal_weight'
) -> pd.DataFrame:
    """
    Calculate portfolio returns from price data and signals.

    Parameters
    ----------
    prices : pd.DataFrame
        Daily asset prices (DatetimeIndex, columns = tickers).
    signals : pd.DataFrame
        Trading signals (0 or 1), same shape as prices.
        1 = long position, 0 = cash/flat.
    initial_capital : float, default 100.0
        Starting portfolio value.
    transaction_cost : float, default 0.0005
        Transaction cost as fraction of trade value (5 bps = 0.05%).
    rebalance_frequency : str, default 'M'
        Rebalancing frequency: 'D' (daily), 'W' (weekly), 'M' (monthly).
    position_size : str, default 'equal_weight'
        Position sizing method: 'equal_weight' or 'equal_risk'.

    Returns
    -------
    pd.DataFrame
        Portfolio statistics with columns:
        - portfolio_value: Total portfolio value over time
        - returns: Daily returns
        - positions: Number of positions held
        - turnover: Portfolio turnover (fraction changed)
    """
    # Calculate daily returns
    daily_returns = prices.pct_change()

    # Align signals with returns (shift signals to avoid lookahead bias)
    # Signal on day t should be executed at close of day t,
    # earning returns from t to t+1
    signals_shifted = signals.shift(1).fillna(0)

    # Rebalance dates
    if rebalance_frequency == 'M':
        rebalance_dates = pd.date_range(
            start=prices.index[0],
            end=prices.index[-1],
            freq='MS'  # Month start
        )
    elif rebalance_frequency == 'W':
        rebalance_dates = pd.date_range(
            start=prices.index[0],
            end=prices.index[-1],
            freq='W'
        )
    else:  # Daily
        rebalance_dates = prices.index

    # Initialize portfolio
    portfolio_value = pd.Series(index=prices.index, dtype=float)
    portfolio_value.iloc[0] = initial_capital

    # Track positions (weights)
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    turnover = pd.Series(0.0, index=prices.index)

    # Previous weights for turnover calculation
    prev_weights = pd.Series(0.0, index=prices.columns)

    for i in range(1, len(prices)):
        date = prices.index[i]
        prev_date = prices.index[i-1]

        # Check if rebalance date
        is_rebalance = date in rebalance_dates

        if is_rebalance or i == 1:
            # Get active signals (1 = long)
            active_signals = signals_shifted.loc[date]
            n_positions = active_signals.sum()

            if n_positions > 0:
                if position_size == 'equal_weight':
                    # Equal weight across active positions
                    target_weights = active_signals / n_positions
                else:
                    # For now, default to equal weight
                    target_weights = active_signals / n_positions
            else:
                # No positions, hold cash
                target_weights = pd.Series(0.0, index=prices.columns)

            # Calculate turnover (sum of absolute weight changes)
            turnover.iloc[i] = (target_weights - prev_weights).abs().sum()

            # Apply transaction costs
            tc_cost = turnover.iloc[i] * transaction_cost
            portfolio_value.iloc[i] = portfolio_value.iloc[i-1] * (1 - tc_cost)

            # Update weights
            weights.loc[date] = target_weights
            prev_weights = target_weights
        else:
            # No rebalance, weights drift with returns
            # Calculate new portfolio value from returns
            portfolio_value.iloc[i] = portfolio_value.iloc[i-1]
            weights.loc[date] = prev_weights

        # Apply returns based on weights
        period_return = (weights.loc[date] * daily_returns.loc[date]).sum()
        portfolio_value.iloc[i] = portfolio_value.iloc[i] * (1 + period_return)

        # Update drifted weights for next iteration
        if not is_rebalance:
            # Weights drift: w_new = w_old * (1 + r) / (1 + r_portfolio)
            individual_returns = daily_returns.loc[date]
            prev_weights = prev_weights * (1 + individual_returns) / (1 + period_return)
            prev_weights = prev_weights.fillna(0)

    # Calculate portfolio returns
    portfolio_returns = portfolio_value.pct_change().fillna(0)

    # Number of positions held
    positions = signals_shifted.sum(axis=1)

    # Combine results
    results = pd.DataFrame({
        'portfolio_value': portfolio_value,
        'returns': portfolio_returns,
        'positions': positions,
        'turnover': turnover
    })

    return results


def calculate_performance_metrics(returns: pd.Series) -> Dict[str, float]:
    """
    Calculate comprehensive performance metrics from return series.

    Parameters
    ----------
    returns : pd.Series
        Daily returns (not cumulative).

    Returns
    -------
    dict
        Performance metrics including:
        - total_return: Cumulative return
        - annualized_return: CAGR
        - annualized_volatility: Annualized std dev
        - sharpe_ratio: Risk-adjusted return (assuming 0% risk-free rate)
        - sortino_ratio: Downside risk-adjusted return
        - max_drawdown: Maximum peak-to-trough decline
        - calmar_ratio: Return / max drawdown
        - win_rate: Percentage of positive return days
        - avg_win: Average winning day return
        - avg_loss: Average losing day return
    """
    # Total return
    cumulative_returns = (1 + returns).cumprod()
    total_return = cumulative_returns.iloc[-1] - 1

    # Annualized metrics (assuming 252 trading days)
    n_years = len(returns) / 252
    annualized_return = (1 + total_return) ** (1 / n_years) - 1
    annualized_volatility = returns.std() * np.sqrt(252)

    # Sharpe ratio (risk-free rate = 0)
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0

    # Sortino ratio (downside deviation)
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() * np.sqrt(252)
    sortino_ratio = annualized_return / downside_std if downside_std > 0 else 0

    # Maximum drawdown
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()

    # Calmar ratio
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown < 0 else 0

    # Win/loss statistics
    winning_days = returns[returns > 0]
    losing_days = returns[returns < 0]
    win_rate = len(winning_days) / len(returns) if len(returns) > 0 else 0
    avg_win = winning_days.mean() if len(winning_days) > 0 else 0
    avg_loss = losing_days.mean() if len(losing_days) > 0 else 0

    return {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'annualized_volatility': annualized_volatility,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown': max_drawdown,
        'calmar_ratio': calmar_ratio,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss
    }


def calculate_drawdown_series(returns: pd.Series) -> pd.Series:
    """
    Calculate drawdown series from returns.

    Parameters
    ----------
    returns : pd.Series
        Daily returns.

    Returns
    -------
    pd.Series
        Drawdown series (negative values indicate drawdown from peak).
    """
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    return drawdown


def backtest_strategy(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    benchmark_returns: Optional[pd.Series] = None,
    **backtest_params
) -> Dict:
    """
    Run complete backtest and return all results.

    Parameters
    ----------
    prices : pd.DataFrame
        Asset prices.
    signals : pd.DataFrame
        Trading signals.
    benchmark_returns : pd.Series, optional
        Benchmark returns for comparison (e.g., buy-and-hold).
    **backtest_params
        Additional parameters passed to calculate_strategy_returns.

    Returns
    -------
    dict
        Complete backtest results including:
        - portfolio_stats: DataFrame with portfolio value, returns, positions
        - performance_metrics: Dict of performance statistics
        - drawdown_series: Drawdown series
        - benchmark_metrics: Benchmark performance (if provided)
    """
    # Run backtest
    portfolio_stats = calculate_strategy_returns(prices, signals, **backtest_params)

    # Calculate metrics
    performance_metrics = calculate_performance_metrics(portfolio_stats['returns'])

    # Drawdown series
    drawdown_series = calculate_drawdown_series(portfolio_stats['returns'])

    results = {
        'portfolio_stats': portfolio_stats,
        'performance_metrics': performance_metrics,
        'drawdown_series': drawdown_series
    }

    # Compare to benchmark if provided
    if benchmark_returns is not None:
        benchmark_metrics = calculate_performance_metrics(benchmark_returns)
        results['benchmark_metrics'] = benchmark_metrics

    return results


def classify_regimes(
    spy_prices: pd.Series,
    bull_threshold: float = 0.20,
    bear_threshold: float = -0.20
) -> pd.Series:
    """
    Classify market regimes based on S&P 500 price action.

    Parameters
    ----------
    spy_prices : pd.Series
        S&P 500 (SPY) price series.
    bull_threshold : float, default 0.20
        Threshold for bull market (>20% above 252-day low).
    bear_threshold : float, default -0.20
        Threshold for bear market (<-20% below 252-day high).

    Returns
    -------
    pd.Series
        Regime classification ('bull', 'bear', or 'sideways') for each date.
    """
    rolling_max = spy_prices.rolling(252).max()
    rolling_min = spy_prices.rolling(252).min()

    drawdown_from_peak = (spy_prices - rolling_max) / rolling_max
    rally_from_trough = (spy_prices - rolling_min) / rolling_min

    regime = pd.Series('sideways', index=spy_prices.index)
    regime[rally_from_trough > bull_threshold] = 'bull'
    regime[drawdown_from_peak < bear_threshold] = 'bear'

    return regime


def performance_by_regime(returns: pd.Series, regimes: pd.Series) -> pd.DataFrame:
    """
    Calculate performance statistics by market regime.

    Parameters
    ----------
    returns : pd.Series
        Daily returns.
    regimes : pd.Series
        Regime classification for each date.

    Returns
    -------
    pd.DataFrame
        Performance metrics by regime with columns:
        - regime: Regime type ('bull', 'bear', 'sideways')
        - days: Number of trading days in regime
        - total_return, annualized_return, sharpe_ratio, etc.
    """
    results = []
    for regime_type in ['bull', 'bear', 'sideways']:
        regime_mask = regimes == regime_type
        regime_returns = returns[regime_mask]

        if len(regime_returns) > 0:
            metrics = calculate_performance_metrics(regime_returns)
            metrics['regime'] = regime_type
            metrics['days'] = len(regime_returns)
            results.append(metrics)

    return pd.DataFrame(results)


def extract_trade_log(signals: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """
    Extract trade-level log from signal changes.

    Parameters
    ----------
    signals : pd.DataFrame
        Trading signals (0 or 1) for each asset.
    prices : pd.DataFrame
        Asset prices.

    Returns
    -------
    pd.DataFrame
        Trade log with columns:
        - entry_date: Trade entry date
        - exit_date: Trade exit date
        - asset: Asset ticker
        - entry_price: Entry price
        - exit_price: Exit price
        - return: Trade return (%)
        - days_held: Number of days held
    """
    trades = []

    for asset in signals.columns:
        asset_signals = signals[asset]
        changes = asset_signals.diff()

        # Entry: 0 → 1
        entries = changes[changes == 1].index
        # Exit: 1 → 0
        exits = changes[changes == -1].index

        # Match entries to exits
        for entry_date in entries:
            # Find next exit after this entry
            exit_dates = exits[exits > entry_date]
            if len(exit_dates) > 0:
                exit_date = exit_dates[0]
                entry_price = prices.loc[entry_date, asset]
                exit_price = prices.loc[exit_date, asset]
                ret = (exit_price - entry_price) / entry_price
                days_held = (exit_date - entry_date).days

                trades.append({
                    'entry_date': entry_date,
                    'exit_date': exit_date,
                    'asset': asset,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'return': ret,
                    'days_held': days_held
                })

    return pd.DataFrame(trades)


def calculate_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Calculate Value at Risk (VaR) at a given confidence level.

    VaR represents the maximum loss at the given confidence level.
    E.g., 95% VaR means only 5% of returns are worse than this value.

    Parameters:
    -----------
    returns : pd.Series
        Daily returns
    confidence : float
        Confidence level (default 0.95 for 95% VaR)

    Returns:
    --------
    float : VaR value (negative number representing loss threshold)
    """
    return np.percentile(returns, (1 - confidence) * 100)


def calculate_cvar(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Calculate Conditional Value at Risk (CVaR), also known as Expected Shortfall.

    CVaR is the expected loss given that losses exceed the VaR threshold.
    It represents the average of the worst (1-confidence)% of returns.

    Parameters:
    -----------
    returns : pd.Series
        Daily returns
    confidence : float
        Confidence level (default 0.95 for 95% CVaR)

    Returns:
    --------
    float : CVaR value (expected loss in worst (1-confidence)% of cases)
    """
    var = calculate_var(returns, confidence)
    # CVaR is the mean of all returns worse than VaR
    return returns[returns <= var].mean()


def calculate_rolling_var_cvar(returns: pd.Series, window: int = 252,
                                confidence_levels: list = [0.95, 0.99]) -> pd.DataFrame:
    """
    Calculate rolling VaR and CVaR over time for multiple confidence levels.

    Parameters:
    -----------
    returns : pd.Series
        Daily returns
    window : int
        Rolling window size in days (default 252 = 1 year)
    confidence_levels : list
        List of confidence levels to calculate (default [0.95, 0.99])

    Returns:
    --------
    pd.DataFrame : Rolling VaR and CVaR series for each confidence level
    """
    results = pd.DataFrame(index=returns.index)

    for conf in confidence_levels:
        conf_pct = int(conf * 100)
        # Calculate rolling VaR
        results[f'VaR_{conf_pct}%'] = returns.rolling(window).apply(
            lambda x: calculate_var(x, conf), raw=False
        )
        # Calculate rolling CVaR
        results[f'CVaR_{conf_pct}%'] = returns.rolling(window).apply(
            lambda x: calculate_cvar(x, conf), raw=False
        )

    return results


if __name__ == "__main__":
    # Example usage
    from pathlib import Path
    import sys

    # Add project root to path
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))

    from src.signals.trend_filter import generate_signals

    print("Running SMA Trend Strategy Backtest...\n")

    # Load data
    data_path = Path(__file__).resolve().parents[2] / "data" / "processed" / "prices_clean.csv"
    prices = pd.read_csv(data_path, index_col=0, parse_dates=True)

    # Generate signals
    signals = generate_signals(prices, method='sma', window=252)

    # Calculate buy-and-hold benchmark (equal weight)
    benchmark_returns = prices.pct_change().mean(axis=1)

    # Run backtest
    results = backtest_strategy(
        prices=prices,
        signals=signals,
        benchmark_returns=benchmark_returns,
        transaction_cost=0.0005,
        rebalance_frequency='M'
    )

    # Print results
    print("=== Strategy Performance ===")
    for metric, value in results['performance_metrics'].items():
        if 'return' in metric or 'drawdown' in metric:
            print(f"{metric:.<30} {value:>10.2%}")
        elif 'ratio' in metric:
            print(f"{metric:.<30} {value:>10.2f}")
        elif 'rate' in metric:
            print(f"{metric:.<30} {value:>10.2%}")
        else:
            print(f"{metric:.<30} {value:>10.4f}")

    print("\n=== Benchmark Performance (Equal Weight Buy-and-Hold) ===")
    for metric, value in results['benchmark_metrics'].items():
        if 'return' in metric or 'drawdown' in metric:
            print(f"{metric:.<30} {value:>10.2%}")
        elif 'ratio' in metric:
            print(f"{metric:.<30} {value:>10.2f}")
        elif 'rate' in metric:
            print(f"{metric:.<30} {value:>10.2%}")
        else:
            print(f"{metric:.<30} {value:>10.4f}")

    print("\n=== Portfolio Statistics ===")
    print(f"Average positions held: {results['portfolio_stats']['positions'].mean():.2f}")
    print(f"Average monthly turnover: {results['portfolio_stats']['turnover'].resample('M').sum().mean():.2%}")
    print(f"\nFinal portfolio value: ${results['portfolio_stats']['portfolio_value'].iloc[-1]:.2f}")
