# tests/test_signals/test_regime.py
"""Tests for regime detection signals."""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from signals.regime import (
    realized_vol_regime,
    cross_asset_momentum_regime,
    correlation_regime,
    composite_regime,
    regime_position_scalar,
)


@pytest.fixture
def calm_market():
    """Synthetic calm market — low vol, steady uptrend."""
    np.random.seed(10)
    dates = pd.date_range("2020-01-01", periods=300, freq="D")
    prices = pd.DataFrame({
        "A": 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.005, 300))),
        "B": 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.005, 300))),
        "C": 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.005, 300))),
    }, index=dates)
    return prices


@pytest.fixture
def crisis_market():
    """Synthetic crisis — high vol, correlated decline."""
    np.random.seed(20)
    dates = pd.date_range("2020-01-01", periods=300, freq="D")
    # All assets declining with high vol
    common_shock = np.random.normal(-0.003, 0.03, 300)
    prices = pd.DataFrame({
        "A": 100 * np.exp(np.cumsum(common_shock + np.random.normal(0, 0.005, 300))),
        "B": 100 * np.exp(np.cumsum(common_shock + np.random.normal(0, 0.005, 300))),
        "C": 100 * np.exp(np.cumsum(common_shock + np.random.normal(0, 0.005, 300))),
    }, index=dates)
    return prices


class TestRealizedVolRegime:
    def test_output_shape(self, calm_market):
        result = realized_vol_regime(calm_market)
        assert result.shape == calm_market.shape

    def test_output_values_in_range(self, calm_market):
        result = realized_vol_regime(calm_market)
        valid = result.dropna()
        assert (valid >= 0.0).all().all()
        assert (valid <= 1.0).all().all()

    def test_calm_market_high_signal(self, calm_market):
        """Calm market should produce high signals (risk-on)."""
        result = realized_vol_regime(calm_market, low_threshold=0.10, high_threshold=0.25)
        valid = result.dropna()
        mean_signal = valid.mean().mean()
        # Calm market vol ~8% annualized, should mostly be risk-on
        assert mean_signal >= 0.5

    def test_crisis_market_low_signal(self, crisis_market):
        """Crisis market should produce low signals (risk-off)."""
        result = realized_vol_regime(crisis_market, low_threshold=0.10, high_threshold=0.25)
        valid = result.dropna()
        mean_signal = valid.mean().mean()
        # Crisis vol ~48% annualized, should be risk-off
        assert mean_signal <= 0.5

    def test_nan_at_start(self, calm_market):
        """First rows should be NaN (insufficient data)."""
        result = realized_vol_regime(calm_market, short_window=21, long_window=63)
        assert result.iloc[0].isna().all()

    def test_three_discrete_values(self, calm_market):
        """Output should contain only 0.0, 0.5, 1.0, or NaN."""
        result = realized_vol_regime(calm_market)
        valid = result.dropna().values.flatten()
        unique_vals = set(valid)
        assert unique_vals.issubset({0.0, 0.5, 1.0})


class TestCrossAssetMomentumRegime:
    def test_output_is_series(self, calm_market):
        result = cross_asset_momentum_regime(calm_market)
        assert isinstance(result, pd.Series)
        assert len(result) == len(calm_market)

    def test_values_binary(self, calm_market):
        result = cross_asset_momentum_regime(calm_market)
        valid = result.dropna()
        assert set(valid.unique()).issubset({0.0, 1.0})

    def test_uptrend_risk_on(self, calm_market):
        """All assets trending up → risk-on."""
        result = cross_asset_momentum_regime(calm_market, lookback=63)
        valid = result.dropna()
        # Most of the time should be risk-on
        assert valid.mean() > 0.5

    def test_crisis_risk_off(self, crisis_market):
        """All assets declining → risk-off."""
        result = cross_asset_momentum_regime(crisis_market, lookback=63, threshold=0.5)
        valid = result.dropna()
        risk_off_pct = (valid == 0.0).mean()
        # Should have significant risk-off periods
        assert risk_off_pct > 0.2

    def test_nan_at_start(self, calm_market):
        result = cross_asset_momentum_regime(calm_market, lookback=63)
        assert pd.isna(result.iloc[0])


class TestCorrelationRegime:
    def test_output_is_series(self, calm_market):
        result = correlation_regime(calm_market, window=30)
        assert isinstance(result, pd.Series)

    def test_values_binary(self, calm_market):
        result = correlation_regime(calm_market, window=30)
        valid = result.dropna()
        assert set(valid.unique()).issubset({0.0, 1.0})

    def test_single_asset_returns_ones(self):
        """Single asset should return 1.0 (no correlation to measure)."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        prices = pd.DataFrame({"A": range(100, 200)}, index=dates)
        result = correlation_regime(prices)
        assert (result == 1.0).all()

    def test_crisis_high_correlation(self, crisis_market):
        """Correlated decline should trigger crisis regime."""
        result = correlation_regime(crisis_market, window=30, threshold=0.5)
        valid = result.dropna()
        # Should detect high correlation
        crisis_pct = (valid == 0.0).mean()
        assert crisis_pct > 0.1


class TestCompositeRegime:
    def test_returns_series(self, calm_market):
        result = composite_regime(calm_market)
        assert isinstance(result, pd.Series)

    def test_values_in_range(self, calm_market):
        result = composite_regime(calm_market)
        valid = result.dropna()
        assert (valid >= 0.0).all()
        assert (valid <= 1.0).all()

    def test_custom_weights(self, calm_market):
        """Custom weights should work."""
        result = composite_regime(
            calm_market,
            vol_weight=0.5,
            momentum_weight=0.25,
            corr_weight=0.25,
        )
        valid = result.dropna()
        assert len(valid) > 0


class TestRegimePositionScalar:
    def test_high_score_full_position(self):
        score = pd.Series([0.8, 0.9, 1.0])
        scalar = regime_position_scalar(score, full_threshold=0.6, zero_threshold=0.2)
        assert (scalar == 1.0).all()

    def test_low_score_zero_position(self):
        score = pd.Series([0.0, 0.1, 0.2])
        scalar = regime_position_scalar(score, full_threshold=0.6, zero_threshold=0.2)
        assert (scalar == 0.0).all()

    def test_mid_score_partial(self):
        score = pd.Series([0.4])
        scalar = regime_position_scalar(score, full_threshold=0.6, zero_threshold=0.2)
        assert 0.0 < scalar.iloc[0] < 1.0

    def test_nan_preserved(self):
        score = pd.Series([0.5, np.nan, 0.3])
        scalar = regime_position_scalar(score)
        assert pd.isna(scalar.iloc[1])
