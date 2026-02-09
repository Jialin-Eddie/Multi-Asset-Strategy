# tests/test_signals/test_volatility.py
"""Tests for volatility-based signals."""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from signals.volatility import (
    vol_term_structure,
    vol_of_vol,
    vol_mean_reversion,
    generate_vol_signal,
)


@pytest.fixture
def steady_prices():
    """Steady market with consistent volatility."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=400, freq="D")
    prices = pd.DataFrame({
        "SPY": 100 * np.exp(np.cumsum(np.random.normal(0.0004, 0.012, 400))),
        "TLT": 100 * np.exp(np.cumsum(np.random.normal(0.0001, 0.008, 400))),
    }, index=dates)
    return prices


@pytest.fixture
def vol_spike_prices():
    """Market with a vol spike in the middle."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=400, freq="D")
    # Low vol first 200 days, high vol last 200 days
    returns_low = np.random.normal(0.0004, 0.008, 200)
    returns_high = np.random.normal(-0.001, 0.035, 200)
    returns = np.concatenate([returns_low, returns_high])
    prices = pd.DataFrame({
        "SPY": 100 * np.exp(np.cumsum(returns)),
    }, index=dates)
    return prices


class TestVolTermStructure:
    def test_output_shape(self, steady_prices):
        result = vol_term_structure(steady_prices)
        assert result.shape == steady_prices.shape

    def test_values_in_range(self, steady_prices):
        result = vol_term_structure(steady_prices)
        valid = result.dropna()
        assert (valid >= 0.0).all().all()
        assert (valid <= 1.0).all().all()

    def test_nan_at_start(self, steady_prices):
        result = vol_term_structure(steady_prices, short_window=21, long_window=63)
        assert result.iloc[0].isna().all()

    def test_steady_market_neutral(self, steady_prices):
        """Steady vol → short vol ≈ long vol → signal near 0.5."""
        result = vol_term_structure(steady_prices)
        valid = result.dropna()
        mean_signal = valid.mean().mean()
        assert 0.3 < mean_signal < 0.7

    def test_vol_spike_lower_signal(self, vol_spike_prices):
        """Right after vol spike, short vol > long vol → signal drops."""
        result = vol_term_structure(vol_spike_prices, short_window=21, long_window=63)
        # Check right after the transition (day 200-230) vs calm period (day 100-180)
        # Short vol reacts faster to the spike than long vol
        transition_signal = result.iloc[210:230].mean().mean()
        calm_signal = result.iloc[100:180].mean().mean()
        assert transition_signal < calm_signal


class TestVolOfVol:
    def test_output_shape(self, steady_prices):
        result = vol_of_vol(steady_prices)
        assert result.shape == steady_prices.shape

    def test_values_in_range(self, steady_prices):
        result = vol_of_vol(steady_prices)
        valid = result.dropna()
        assert (valid >= 0.0).all().all()
        assert (valid <= 1.0).all().all()

    def test_nan_at_start(self, steady_prices):
        result = vol_of_vol(steady_prices, vol_window=21, vov_window=63)
        # First vol_window + vov_window rows should be NaN
        assert result.iloc[0].isna().all()


class TestVolMeanReversion:
    def test_output_shape(self, steady_prices):
        result = vol_mean_reversion(steady_prices)
        assert result.shape == steady_prices.shape

    def test_values_in_range(self, steady_prices):
        result = vol_mean_reversion(steady_prices)
        valid = result.dropna()
        assert (valid >= 0.0).all().all()
        assert (valid <= 1.0).all().all()

    def test_steady_market_near_half(self, steady_prices):
        """Steady vol → z-score near 0 → signal near 0.5."""
        result = vol_mean_reversion(steady_prices)
        valid = result.dropna()
        mean_signal = valid.mean().mean()
        assert 0.3 < mean_signal < 0.7


class TestGenerateVolSignal:
    def test_term_structure(self, steady_prices):
        result = generate_vol_signal(steady_prices, method="term_structure")
        assert result.shape == steady_prices.shape

    def test_vol_of_vol(self, steady_prices):
        result = generate_vol_signal(steady_prices, method="vol_of_vol")
        assert result.shape == steady_prices.shape

    def test_mean_reversion(self, steady_prices):
        result = generate_vol_signal(steady_prices, method="mean_reversion")
        assert result.shape == steady_prices.shape

    def test_invalid_method(self, steady_prices):
        with pytest.raises(ValueError, match="Unknown method"):
            generate_vol_signal(steady_prices, method="invalid")

    def test_kwargs_passed(self, steady_prices):
        result = generate_vol_signal(
            steady_prices, method="term_structure",
            short_window=10, long_window=30,
        )
        assert result.shape == steady_prices.shape
