# tests/conftest.py
"""Pytest fixtures for testing."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def sample_prices():
    """
    Create sample price data for testing.

    Returns a DataFrame with 300 days of synthetic price data
    that exhibits a clear uptrend, suitable for testing trend filters.
    """
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=300, freq='D')

    # Create synthetic price series with upward trend
    # SPY: Strong uptrend
    spy_prices = 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.015, 300)))

    # TLT: Slight downtrend
    tlt_prices = 100 * np.exp(np.cumsum(np.random.normal(-0.0002, 0.01, 300)))

    # GLD: Sideways with volatility
    gld_prices = 100 * np.exp(np.cumsum(np.random.normal(0.0, 0.012, 300)))

    df = pd.DataFrame({
        'SPY': spy_prices,
        'TLT': tlt_prices,
        'GLD': gld_prices
    }, index=dates)

    return df


@pytest.fixture
def simple_uptrend():
    """
    Create a simple deterministic uptrend for testing.

    Returns a DataFrame with a perfect linear uptrend,
    useful for testing exact signal calculations.
    """
    dates = pd.date_range(start='2020-01-01', periods=100, freq='D')

    # Linear uptrend from 100 to 200
    prices = np.linspace(100, 200, 100)

    df = pd.DataFrame({
        'ASSET': prices
    }, index=dates)

    return df


@pytest.fixture
def simple_downtrend():
    """
    Create a simple deterministic downtrend for testing.
    """
    dates = pd.date_range(start='2020-01-01', periods=100, freq='D')

    # Linear downtrend from 100 to 50
    prices = np.linspace(100, 50, 100)

    df = pd.DataFrame({
        'ASSET': prices
    }, index=dates)

    return df


@pytest.fixture
def prices_with_nan():
    """
    Create price data with NaN values for testing edge cases.
    """
    dates = pd.date_range(start='2020-01-01', periods=50, freq='D')

    prices = np.linspace(100, 150, 50)
    # Insert some NaN values
    prices[10] = np.nan
    prices[25] = np.nan

    df = pd.DataFrame({
        'ASSET': prices
    }, index=dates)

    return df


@pytest.fixture
def short_history():
    """
    Create very short price history (less than typical lookback period).
    Useful for testing insufficient data handling.
    """
    dates = pd.date_range(start='2020-01-01', periods=10, freq='D')

    prices = np.linspace(100, 110, 10)

    df = pd.DataFrame({
        'ASSET': prices
    }, index=dates)

    return df


@pytest.fixture
def cross_sectional_data():
    """
    Create cross-sectional data for testing relative momentum.

    Returns 5 assets with different momentum profiles.
    """
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=300, freq='D')

    # Asset 1: Strong momentum (best)
    asset1 = 100 * np.exp(np.cumsum(np.random.normal(0.002, 0.01, 300)))

    # Asset 2: Moderate momentum
    asset2 = 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.01, 300)))

    # Asset 3: Flat
    asset3 = 100 * np.exp(np.cumsum(np.random.normal(0.0, 0.01, 300)))

    # Asset 4: Negative momentum
    asset4 = 100 * np.exp(np.cumsum(np.random.normal(-0.001, 0.01, 300)))

    # Asset 5: Strong negative momentum (worst)
    asset5 = 100 * np.exp(np.cumsum(np.random.normal(-0.002, 0.01, 300)))

    df = pd.DataFrame({
        'ASSET1': asset1,
        'ASSET2': asset2,
        'ASSET3': asset3,
        'ASSET4': asset4,
        'ASSET5': asset5
    }, index=dates)

    return df
