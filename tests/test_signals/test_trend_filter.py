# tests/test_signals/test_trend_filter.py
"""Unit tests for trend filter signals."""

import pytest
import pandas as pd
import numpy as np
from src.signals.trend_filter import (
    calculate_sma,
    sma_trend_signal,
    calculate_ema,
    ema_trend_signal,
    calculate_momentum,
    absolute_momentum_signal,
    relative_momentum_signal,
    dual_momentum_signal
)


class TestSMACalculation:
    """Test Simple Moving Average calculations."""

    def test_sma_basic(self, simple_uptrend):
        """Test basic SMA calculation on uptrend."""
        result = calculate_sma(simple_uptrend, window=10)

        # Check shape matches input
        assert result.shape == simple_uptrend.shape

        # Check first 9 values are NaN (not enough data)
        assert result.iloc[:9].isna().all().all()

        # Check 10th value is average of first 10 prices
        expected_sma_10 = simple_uptrend.iloc[:10].mean()
        pd.testing.assert_series_equal(
            result.iloc[9],
            expected_sma_10,
            check_names=False
        )

    def test_sma_window_252(self, sample_prices):
        """Test SMA with 252-day window (standard for 12-month MA)."""
        result = calculate_sma(sample_prices, window=252)

        # Check first 251 values are NaN
        assert result.iloc[:251].isna().all().all()

        # Check valid values after window period
        assert not result.iloc[252:].isna().any().any()

    def test_sma_values_manual(self):
        """Test SMA with hand-calculated values."""
        # Create simple data: [10, 20, 30, 40, 50]
        df = pd.DataFrame({'A': [10, 20, 30, 40, 50]})

        result = calculate_sma(df, window=3)

        # First 2 should be NaN
        assert pd.isna(result.iloc[0, 0])
        assert pd.isna(result.iloc[1, 0])

        # Third value: (10 + 20 + 30) / 3 = 20
        assert result.iloc[2, 0] == 20.0

        # Fourth value: (20 + 30 + 40) / 3 = 30
        assert result.iloc[3, 0] == 30.0

        # Fifth value: (30 + 40 + 50) / 3 = 40
        assert result.iloc[4, 0] == 40.0

    def test_sma_with_nan(self, prices_with_nan):
        """Test SMA handles NaN values correctly."""
        result = calculate_sma(prices_with_nan, window=5)

        # Should propagate NaN forward
        assert pd.isna(result.iloc[10, 0])


class TestSMASignal:
    """Test SMA-based trend signals."""

    def test_signal_above_ma(self, simple_uptrend):
        """Test signal is 1 when price > SMA."""
        signals = sma_trend_signal(simple_uptrend, window=10)

        # In uptrend, later prices should be above MA
        # Check last 20 values are all 1
        assert (signals.iloc[-20:] == 1).all().all()

    def test_signal_below_ma(self, simple_downtrend):
        """Test signal is 0 when price < SMA."""
        signals = sma_trend_signal(simple_downtrend, window=10)

        # In downtrend, later prices should be below MA
        # Check last 20 values are all 0
        assert (signals.iloc[-20:] == 0).all().all()

    def test_signal_nan_handling(self, sample_prices):
        """Test signal is NaN when insufficient data for MA."""
        signals = sma_trend_signal(sample_prices, window=50)

        # First 49 should be NaN
        assert signals.iloc[:49].isna().all().all()

        # Rest should be valid (0 or 1)
        assert signals.iloc[50:].isin([0, 1]).all().all()

    def test_signal_crossover(self):
        """Test signal changes at MA crossover points."""
        # Create data that crosses MA
        prices = [100, 105, 110, 108, 106, 104, 102, 100, 98, 96,
                  94, 92, 90, 92, 94, 96, 98, 100, 102, 104]
        df = pd.DataFrame({'A': prices})

        signals = sma_trend_signal(df, window=5)

        # Check that signal changes occur
        signal_diff = signals.diff()
        assert (signal_diff.abs() > 0).any().any()


class TestEMACalculation:
    """Test Exponential Moving Average calculations."""

    def test_ema_basic(self, simple_uptrend):
        """Test basic EMA calculation."""
        result = calculate_ema(simple_uptrend, span=10)

        # EMA should have same shape
        assert result.shape == simple_uptrend.shape

        # Should not have NaN for EMA (uses exponential weighting)
        # Except possibly first value depending on implementation
        assert not result.iloc[10:].isna().any().any()

    def test_ema_vs_sma(self, sample_prices):
        """Test EMA is more responsive than SMA (weights recent data more)."""
        ema = calculate_ema(sample_prices, span=20)
        sma = calculate_sma(sample_prices, window=20)

        # Both should have similar values but EMA reacts faster
        # Just check they are computed without errors
        assert ema.shape == sma.shape


class TestEMASignal:
    """Test EMA-based trend signals."""

    def test_ema_signal_uptrend(self, simple_uptrend):
        """Test EMA signal on uptrend."""
        signals = ema_trend_signal(simple_uptrend, span=10)

        # Later values in uptrend should be 1
        assert (signals.iloc[-20:] == 1).all().all()

    def test_ema_signal_downtrend(self, simple_downtrend):
        """Test EMA signal on downtrend."""
        signals = ema_trend_signal(simple_downtrend, span=10)

        # Later values in downtrend should be 0
        assert (signals.iloc[-20:] == 0).all().all()


class TestMomentumCalculation:
    """Test momentum calculations."""

    def test_momentum_basic(self, sample_prices):
        """Test basic momentum calculation (% change over lookback)."""
        result = calculate_momentum(sample_prices, lookback=21)

        # Check shape
        assert result.shape == sample_prices.shape

        # First 21 values should be NaN
        assert result.iloc[:21].isna().all().all()

        # Valid values should be returns (can be positive or negative)
        assert result.iloc[21:].notna().any().any()

    def test_momentum_manual(self):
        """Test momentum with hand-calculated values."""
        # Prices: [100, 110, 120, 130, 140]
        df = pd.DataFrame({'A': [100, 110, 120, 130, 140]})

        result = calculate_momentum(df, lookback=2)

        # First 2 should be NaN
        assert pd.isna(result.iloc[0, 0])
        assert pd.isna(result.iloc[1, 0])

        # Third: (120 - 100) / 100 = 0.20
        assert np.isclose(result.iloc[2, 0], 0.20)

        # Fourth: (130 - 110) / 110 = 0.1818...
        assert np.isclose(result.iloc[3, 0], 130/110 - 1)

        # Fifth: (140 - 120) / 120 = 0.1666...
        assert np.isclose(result.iloc[4, 0], 140/120 - 1)


class TestAbsoluteMomentum:
    """Test absolute momentum signals."""

    def test_absolute_momentum_positive(self, simple_uptrend):
        """Test absolute momentum signal for positive momentum."""
        signals = absolute_momentum_signal(simple_uptrend, lookback=10)

        # Uptrend should have positive momentum -> signal = 1
        assert (signals.iloc[-20:] == 1).all().all()

    def test_absolute_momentum_negative(self, simple_downtrend):
        """Test absolute momentum signal for negative momentum."""
        signals = absolute_momentum_signal(simple_downtrend, lookback=10)

        # Downtrend should have negative momentum -> signal = 0
        assert (signals.iloc[-20:] == 0).all().all()

    def test_absolute_momentum_threshold(self):
        """Test absolute momentum with custom threshold."""
        # Small positive momentum
        df = pd.DataFrame({'A': [100, 101, 102, 103, 104]})

        # With 0% threshold, should be 1
        signals_0 = absolute_momentum_signal(df, lookback=2, threshold=0.0)
        assert (signals_0.iloc[2:] == 1).all().all()

        # With 5% threshold, should be 0 (only ~2% momentum)
        signals_5 = absolute_momentum_signal(df, lookback=2, threshold=0.05)
        assert (signals_5.iloc[2:] == 0).all().all()


class TestRelativeMomentum:
    """Test relative (cross-sectional) momentum signals."""

    def test_relative_momentum_ranking(self, cross_sectional_data):
        """Test relative momentum ranks assets correctly."""
        signals = relative_momentum_signal(cross_sectional_data, lookback=60, top_n=2)

        # Should return signals for all assets
        assert signals.shape == cross_sectional_data.shape

        # Check that exactly top_n assets have signal = 1 per row
        # (after sufficient lookback period)
        signals_valid = signals.iloc[60:]
        assert (signals_valid.sum(axis=1) == 2).all()

    def test_relative_momentum_top_performers(self, cross_sectional_data):
        """Test that top performers get signal = 1."""
        signals = relative_momentum_signal(cross_sectional_data, lookback=60, top_n=1)

        # ASSET1 has strongest momentum, should dominate signals
        # Count how often each asset gets signal
        signal_counts = signals.iloc[60:].sum()

        # ASSET1 should have most signals (though not guaranteed every period)
        assert signal_counts['ASSET1'] > signal_counts['ASSET5']


class TestDualMomentum:
    """Test dual momentum (absolute + relative) signals."""

    def test_dual_momentum_both_conditions(self, cross_sectional_data):
        """Test dual momentum requires both absolute and relative momentum."""
        signals = dual_momentum_signal(
            cross_sectional_data,
            lookback=60,
            top_n=3,
            abs_threshold=0.0
        )

        # Shape should match
        assert signals.shape == cross_sectional_data.shape

        # Should have NaN for insufficient data
        assert signals.iloc[:60].isna().all().all()

        # Valid signals should be 0 or 1
        assert signals.iloc[60:].isin([0, 1]).all().all()

    def test_dual_momentum_filters_negative(self):
        """Test that dual momentum filters out negative absolute momentum."""
        # Create data where some assets have negative momentum
        dates = pd.date_range('2020-01-01', periods=100)
        df = pd.DataFrame({
            'A': np.linspace(100, 120, 100),  # Positive momentum
            'B': np.linspace(100, 80, 100),   # Negative momentum (best relative but negative absolute)
        }, index=dates)

        signals = dual_momentum_signal(df, lookback=20, top_n=1, abs_threshold=0.0)

        # Even though B might have best relative momentum in downtrend,
        # it should get signal = 0 due to negative absolute momentum
        # A should get signal = 1
        assert (signals['A'].iloc[-20:] == 1).all()
        assert (signals['B'].iloc[-20:] == 0).all()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_short_history(self, short_history):
        """Test behavior with insufficient data."""
        # 10 days of data, 20-day lookback
        signals = sma_trend_signal(short_history, window=20)

        # All should be NaN
        assert signals.isna().all().all()

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()

        # Empty dataframe should return empty result
        result = calculate_sma(df, window=10)
        assert result.empty

    def test_single_column(self):
        """Test functions work with single column."""
        df = pd.DataFrame({'A': range(50)})

        sma = calculate_sma(df, window=10)
        assert sma.shape == df.shape

        signals = sma_trend_signal(df, window=10)
        assert signals.shape == df.shape

    def test_invalid_window(self, sample_prices):
        """Test invalid window/lookback parameters."""
        with pytest.raises(ValueError):
            calculate_sma(sample_prices, window=0)

        with pytest.raises(ValueError):
            calculate_sma(sample_prices, window=-10)
