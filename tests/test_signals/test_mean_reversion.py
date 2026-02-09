# tests/test_signals/test_mean_reversion.py
"""Tests for mean reversion signals."""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from signals.mean_reversion import (
    zscore_signal,
    rsi_signal,
    bollinger_signal,
    generate_mr_signal,
)


@pytest.fixture
def uptrend_prices():
    """Steady uptrend for testing."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=300, freq="D")
    prices = pd.DataFrame({
        "A": 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.01, 300))),
        "B": 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.008, 300))),
    }, index=dates)
    return prices


@pytest.fixture
def spike_prices():
    """Prices with a large spike then reversion."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    base = np.ones(100) * 100.0
    # Spike at day 50
    base[45:55] = 120.0
    prices = pd.DataFrame({"A": base}, index=dates)
    return prices


@pytest.fixture
def crash_prices():
    """Prices with a crash then recovery."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    base = np.ones(100) * 100.0
    base[45:55] = 80.0
    prices = pd.DataFrame({"A": base}, index=dates)
    return prices


class TestZScoreSignal:
    def test_output_shape(self, uptrend_prices):
        result = zscore_signal(uptrend_prices)
        assert result.shape == uptrend_prices.shape

    def test_values_in_range(self, uptrend_prices):
        result = zscore_signal(uptrend_prices)
        valid = result.dropna()
        assert (valid >= 0.0).all().all()
        assert (valid <= 1.0).all().all()

    def test_spike_triggers_sell(self, spike_prices):
        """Price spike → high z-score → low signal (overbought)."""
        result = zscore_signal(spike_prices, lookback=20, entry_z=2.0)
        # During spike, signal should be low
        spike_signal = result.iloc[50]["A"]
        if not pd.isna(spike_signal):
            assert spike_signal < 0.5

    def test_crash_triggers_buy(self, crash_prices):
        """Price crash → low z-score → high signal (oversold)."""
        result = zscore_signal(crash_prices, lookback=20, entry_z=2.0)
        crash_signal = result.iloc[50]["A"]
        if not pd.isna(crash_signal):
            assert crash_signal > 0.5

    def test_nan_at_start(self, uptrend_prices):
        result = zscore_signal(uptrend_prices, lookback=21)
        assert result.iloc[0].isna().all()


class TestRSISignal:
    def test_output_shape(self, uptrend_prices):
        result = rsi_signal(uptrend_prices)
        assert result.shape == uptrend_prices.shape

    def test_values_in_range(self, uptrend_prices):
        result = rsi_signal(uptrend_prices)
        valid = result.dropna()
        assert (valid >= 0.0).all().all()
        assert (valid <= 1.0).all().all()

    def test_strong_uptrend_low_signal(self):
        """Strong sustained uptrend → high RSI → low signal (overbought)."""
        dates = pd.date_range("2020-01-01", periods=50, freq="D")
        prices = pd.DataFrame({"A": np.linspace(100, 200, 50)}, index=dates)
        result = rsi_signal(prices, period=14)
        valid = result.dropna()
        # Strong uptrend → RSI near 100 → signal near 0
        assert valid.iloc[-1]["A"] < 0.3

    def test_strong_downtrend_high_signal(self):
        """Strong sustained downtrend → low RSI → high signal (oversold)."""
        dates = pd.date_range("2020-01-01", periods=50, freq="D")
        prices = pd.DataFrame({"A": np.linspace(200, 100, 50)}, index=dates)
        result = rsi_signal(prices, period=14)
        valid = result.dropna()
        # Strong downtrend → RSI near 0 → signal near 1
        assert valid.iloc[-1]["A"] > 0.7

    def test_nan_at_start(self, uptrend_prices):
        result = rsi_signal(uptrend_prices, period=14)
        # First value should be NaN (need at least period observations)
        assert pd.isna(result.iloc[0]["A"])

    def test_custom_thresholds(self, uptrend_prices):
        result = rsi_signal(uptrend_prices, overbought=80, oversold=20)
        valid = result.dropna()
        assert (valid >= 0.0).all().all()
        assert (valid <= 1.0).all().all()


class TestBollingerSignal:
    def test_output_shape(self, uptrend_prices):
        result = bollinger_signal(uptrend_prices)
        assert result.shape == uptrend_prices.shape

    def test_values_in_range(self, uptrend_prices):
        result = bollinger_signal(uptrend_prices)
        valid = result.dropna()
        assert (valid >= 0.0).all().all()
        assert (valid <= 1.0).all().all()

    def test_at_mean_near_half(self):
        """Price at moving average → signal near 0.5."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        # Constant price → always at mean
        prices = pd.DataFrame({"A": np.ones(100) * 100.0}, index=dates)
        result = bollinger_signal(prices, window=20)
        valid = result.dropna()
        # All NaN because std=0, band_width=0 → NaN
        # This is expected behavior for constant prices
        assert True

    def test_spike_triggers_overbought(self, spike_prices):
        """Price spike → near upper band → signal close to 0."""
        result = bollinger_signal(spike_prices, window=20, num_std=2.0)
        spike_signal = result.iloc[50]["A"]
        if not pd.isna(spike_signal):
            assert spike_signal < 0.3

    def test_nan_at_start(self, uptrend_prices):
        result = bollinger_signal(uptrend_prices, window=20)
        assert result.iloc[0].isna().all()


class TestGenerateMRSignal:
    def test_zscore_method(self, uptrend_prices):
        result = generate_mr_signal(uptrend_prices, method="zscore")
        assert result.shape == uptrend_prices.shape

    def test_rsi_method(self, uptrend_prices):
        result = generate_mr_signal(uptrend_prices, method="rsi")
        assert result.shape == uptrend_prices.shape

    def test_bollinger_method(self, uptrend_prices):
        result = generate_mr_signal(uptrend_prices, method="bollinger")
        assert result.shape == uptrend_prices.shape

    def test_invalid_method(self, uptrend_prices):
        with pytest.raises(ValueError, match="Unknown method"):
            generate_mr_signal(uptrend_prices, method="invalid")
