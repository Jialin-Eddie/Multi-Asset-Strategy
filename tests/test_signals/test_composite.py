# tests/test_signals/test_composite.py
"""Tests for signal composite framework."""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from signals.composite import (
    equal_weight_blend,
    inverse_correlation_blend,
    regime_conditional_blend,
    signal_to_binary,
    signal_correlation_report,
)


@pytest.fixture
def three_signals():
    """Three synthetic signals with different patterns."""
    dates = pd.date_range("2020-01-01", periods=300, freq="D")
    np.random.seed(42)

    sig1 = pd.DataFrame({
        "A": np.clip(np.random.normal(0.6, 0.2, 300), 0, 1),
        "B": np.clip(np.random.normal(0.5, 0.2, 300), 0, 1),
    }, index=dates)

    sig2 = pd.DataFrame({
        "A": np.clip(np.random.normal(0.4, 0.2, 300), 0, 1),
        "B": np.clip(np.random.normal(0.6, 0.2, 300), 0, 1),
    }, index=dates)

    sig3 = pd.DataFrame({
        "A": np.clip(np.random.normal(0.5, 0.15, 300), 0, 1),
        "B": np.clip(np.random.normal(0.5, 0.15, 300), 0, 1),
    }, index=dates)

    return {"momentum": sig1, "vol": sig2, "mr": sig3}


@pytest.fixture
def binary_signals():
    """Binary (0/1) signals."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    np.random.seed(42)

    sig1 = pd.DataFrame({
        "A": np.random.choice([0.0, 1.0], 100),
        "B": np.random.choice([0.0, 1.0], 100),
    }, index=dates)

    sig2 = pd.DataFrame({
        "A": np.random.choice([0.0, 1.0], 100),
        "B": np.random.choice([0.0, 1.0], 100),
    }, index=dates)

    return {"trend": sig1, "regime": sig2}


class TestEqualWeightBlend:
    def test_output_shape(self, three_signals):
        result = equal_weight_blend(three_signals)
        assert result.shape == list(three_signals.values())[0].shape

    def test_values_in_range(self, three_signals):
        result = equal_weight_blend(three_signals)
        assert (result >= 0.0).all().all()
        assert (result <= 1.0).all().all()

    def test_single_signal_passthrough(self):
        """Single signal → output = input."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        sig = pd.DataFrame({"A": np.ones(10) * 0.7}, index=dates)
        result = equal_weight_blend({"only": sig})
        pd.testing.assert_frame_equal(result, sig)

    def test_two_signals_average(self, binary_signals):
        """Two signals → average."""
        result = equal_weight_blend(binary_signals)
        expected = (binary_signals["trend"] + binary_signals["regime"]) / 2
        np.testing.assert_array_almost_equal(result.values, expected.values)

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="At least one signal"):
            equal_weight_blend({})


class TestInverseCorrelationBlend:
    def test_output_shape(self, three_signals):
        result = inverse_correlation_blend(three_signals, lookback=50)
        assert result.shape == list(three_signals.values())[0].shape

    def test_falls_back_to_equal_weight_single(self):
        """Single signal → falls back to equal weight."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        sig = pd.DataFrame({"A": np.ones(100) * 0.7}, index=dates)
        result = inverse_correlation_blend({"only": sig})
        pd.testing.assert_frame_equal(result, sig)

    def test_values_in_range(self, three_signals):
        result = inverse_correlation_blend(three_signals, lookback=50)
        valid = result.dropna()
        assert (valid >= 0.0).all().all()
        assert (valid <= 1.0).all().all()


class TestRegimeConditionalBlend:
    def test_output_shape(self, three_signals):
        regime = pd.Series(0.7, index=list(three_signals.values())[0].index)
        result = regime_conditional_blend(three_signals, regime)
        assert result.shape == list(three_signals.values())[0].shape

    def test_risk_on_uses_risk_on_weights(self):
        """High regime score → use risk-on weights."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        sig_a = pd.DataFrame({"X": np.ones(10) * 1.0}, index=dates)
        sig_b = pd.DataFrame({"X": np.ones(10) * 0.0}, index=dates)
        signals = {"a": sig_a, "b": sig_b}

        regime = pd.Series(0.8, index=dates)  # risk-on
        result = regime_conditional_blend(
            signals, regime,
            risk_on_weights={"a": 0.8, "b": 0.2},
            risk_off_weights={"a": 0.2, "b": 0.8},
        )
        # In risk-on: 0.8*1.0 + 0.2*0.0 = 0.8
        valid = result.dropna()
        assert np.allclose(valid["X"].values, 0.8)

    def test_risk_off_uses_risk_off_weights(self):
        """Low regime score → use risk-off weights."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        sig_a = pd.DataFrame({"X": np.ones(10) * 1.0}, index=dates)
        sig_b = pd.DataFrame({"X": np.ones(10) * 0.0}, index=dates)
        signals = {"a": sig_a, "b": sig_b}

        regime = pd.Series(0.2, index=dates)  # risk-off
        result = regime_conditional_blend(
            signals, regime,
            risk_on_weights={"a": 0.8, "b": 0.2},
            risk_off_weights={"a": 0.2, "b": 0.8},
        )
        valid = result.dropna()
        # In risk-off: 0.2*1.0 + 0.8*0.0 = 0.2
        assert np.allclose(valid["X"].values, 0.2)

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="At least one signal"):
            regime_conditional_blend({}, pd.Series([0.5]))


class TestSignalToBinary:
    def test_threshold_half(self):
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        sig = pd.DataFrame({"A": [0.3, 0.5, 0.7, 0.1, 0.9]}, index=dates)
        result = signal_to_binary(sig, threshold=0.5)
        expected = pd.DataFrame({"A": [0.0, 1.0, 1.0, 0.0, 1.0]}, index=dates)
        pd.testing.assert_frame_equal(result, expected)

    def test_nan_preserved(self):
        dates = pd.date_range("2020-01-01", periods=3, freq="D")
        sig = pd.DataFrame({"A": [0.3, np.nan, 0.7]}, index=dates)
        result = signal_to_binary(sig)
        assert pd.isna(result.iloc[1]["A"])
        assert result.iloc[0]["A"] == 0.0
        assert result.iloc[2]["A"] == 1.0

    def test_custom_threshold(self):
        dates = pd.date_range("2020-01-01", periods=3, freq="D")
        sig = pd.DataFrame({"A": [0.3, 0.5, 0.7]}, index=dates)
        result = signal_to_binary(sig, threshold=0.6)
        expected = pd.DataFrame({"A": [0.0, 0.0, 1.0]}, index=dates)
        pd.testing.assert_frame_equal(result, expected)


class TestSignalCorrelationReport:
    def test_output_shape(self, three_signals):
        result = signal_correlation_report(three_signals)
        assert result.shape == (3, 3)

    def test_diagonal_is_one(self, three_signals):
        result = signal_correlation_report(three_signals)
        np.testing.assert_array_almost_equal(np.diag(result.values), 1.0)

    def test_symmetric(self, three_signals):
        result = signal_correlation_report(three_signals)
        pd.testing.assert_frame_equal(result, result.T)

    def test_identical_signals_full_correlation(self):
        """Two identical signals → correlation = 1.0."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        sig = pd.DataFrame({"A": np.random.random(100)}, index=dates)
        result = signal_correlation_report({"s1": sig, "s2": sig})
        assert np.isclose(result.loc["s1", "s2"], 1.0)
