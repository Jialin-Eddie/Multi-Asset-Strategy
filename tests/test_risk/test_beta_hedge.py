# tests/test_risk/test_beta_hedge.py
"""Tests for the beta hedge module."""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.risk.beta_hedge import compute_beta, beta_hedge_weights, apply_beta_hedge_overlay


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_data():
    dates = pd.date_range('2010-01-01', periods=500, freq='B')
    np.random.seed(42)
    spy_returns = np.random.normal(0.0005, 0.01, 500)
    # High beta asset (beta ≈ 1.5)
    high_beta = spy_returns * 1.5 + np.random.normal(0, 0.005, 500)
    # Low beta asset (beta ≈ 0.3)
    low_beta = spy_returns * 0.3 + np.random.normal(0, 0.005, 500)
    # Synthetic prices (cumulative from 100)
    prices = pd.DataFrame({
        'SPY': 100 * (1 + spy_returns).cumprod(),
        'HIGH': 100 * (1 + high_beta).cumprod(),
        'LOW': 100 * (1 + low_beta).cumprod(),
    }, index=dates)
    signals = pd.DataFrame(1, index=dates, columns=['HIGH', 'LOW'])
    returns = prices.pct_change().dropna()
    return prices, signals, returns


# ============================================================================
# Tests: compute_beta
# ============================================================================

class TestComputeBeta:

    def test_compute_beta_shape(self, sample_data):
        """Output DataFrame shape matches input asset_returns."""
        _, _, returns = sample_data
        asset_returns = returns[['HIGH', 'LOW']]
        benchmark_returns = returns['SPY']
        result = compute_beta(asset_returns, benchmark_returns, lookback=252)
        assert result.shape == asset_returns.shape

    def test_compute_beta_nan_prefix(self, sample_data):
        """First (lookback - 1) rows should all be NaN."""
        _, _, returns = sample_data
        asset_returns = returns[['HIGH', 'LOW']]
        benchmark_returns = returns['SPY']
        lookback = 60
        result = compute_beta(asset_returns, benchmark_returns, lookback=lookback)
        assert result.iloc[:lookback - 1].isna().all().all()

    def test_compute_beta_spy_vs_spy(self, sample_data):
        """SPY beta vs itself should be ≈ 1.0 in valid rows."""
        _, _, returns = sample_data
        spy_df = returns[['SPY']]
        benchmark = returns['SPY']
        lookback = 60
        result = compute_beta(spy_df, benchmark, lookback=lookback)
        valid = result.dropna()
        assert len(valid) > 0
        np.testing.assert_allclose(valid['SPY'].values, 1.0, atol=1e-6)

    def test_compute_beta_zero_benchmark_var(self, sample_data):
        """Constant benchmark (zero variance) should not raise; returns NaN or 0."""
        _, _, returns = sample_data
        asset_returns = returns[['HIGH', 'LOW']]
        # Constant benchmark = zero variance
        constant_benchmark = pd.Series(0.0, index=returns.index)
        try:
            result = compute_beta(asset_returns, constant_benchmark, lookback=60)
        except Exception as e:
            pytest.fail(f"compute_beta raised unexpectedly with zero-variance benchmark: {e}")
        # Should be all NaN (since bench_var == 0 triggers the guard)
        valid = result.dropna()
        # Either all NaN or all 0 — the guard should prevent non-finite values
        if len(valid) > 0:
            assert np.isfinite(valid.values).all()

    def test_compute_beta_short_series(self):
        """Data rows < lookback should return all NaN without raising."""
        dates = pd.date_range('2020-01-01', periods=10, freq='B')
        np.random.seed(0)
        asset_returns = pd.DataFrame(
            np.random.normal(0, 0.01, (10, 2)),
            index=dates,
            columns=['A', 'B'],
        )
        benchmark = pd.Series(np.random.normal(0, 0.01, 10), index=dates)
        try:
            result = compute_beta(asset_returns, benchmark, lookback=60)
        except Exception as e:
            pytest.fail(f"compute_beta raised with short series: {e}")
        assert result.isna().all().all()


# ============================================================================
# Tests: beta_hedge_weights
# ============================================================================

class TestBetaHedgeWeights:

    def _base_weights(self):
        return pd.Series({'HIGH': 0.5, 'LOW': 0.5})

    def _base_betas(self):
        return pd.Series({'HIGH': 1.5, 'LOW': 0.3})

    def test_hedge_ratio_zero(self):
        """hedge_ratio=0 means no adjustment; output equals input."""
        w = self._base_weights()
        b = self._base_betas()
        result = beta_hedge_weights(w, b, hedge_ratio=0.0)
        # hedge_ratio=0 → adjusted = weights * (1 - betas/avg_beta * 0) = weights * 1 = weights
        pd.testing.assert_series_equal(result, w)

    def test_hedge_ratio_one(self):
        """hedge_ratio=1 should reduce high-beta asset weight more than low-beta."""
        w = self._base_weights()
        b = self._base_betas()
        result = beta_hedge_weights(w, b, hedge_ratio=1.0)
        # After hedge, HIGH (high beta) should have smaller weight than LOW
        assert result['HIGH'] < result['LOW']

    def test_no_nan_in_output(self):
        """Normal input should produce no NaN in output."""
        w = self._base_weights()
        b = self._base_betas()
        result = beta_hedge_weights(w, b, hedge_ratio=0.5)
        assert not result.isna().any()

    def test_long_only_constraint(self):
        """Output weights must all be >= 0."""
        w = self._base_weights()
        b = pd.Series({'HIGH': 5.0, 'LOW': 0.1})  # Extreme beta
        result = beta_hedge_weights(w, b, hedge_ratio=1.0)
        assert (result >= 0).all()

    def test_empty_weights(self):
        """All-zero weights should not raise; returns zero weights."""
        w = pd.Series({'HIGH': 0.0, 'LOW': 0.0})
        b = self._base_betas()
        try:
            result = beta_hedge_weights(w, b, hedge_ratio=1.0)
        except Exception as e:
            pytest.fail(f"beta_hedge_weights raised with zero weights: {e}")
        assert (result == 0.0).all()


# ============================================================================
# Tests: apply_beta_hedge_overlay smoke tests
# ============================================================================

class TestApplyBetaHedgeOverlay:

    def test_smoke_returns_correct_columns(self, sample_data):
        """Returns DataFrame with required columns."""
        prices, signals, _ = sample_data
        result = apply_beta_hedge_overlay(
            prices, signals,
            benchmark_col='SPY',
            hedge_ratio=0.5,
            beta_lookback=60,
        )
        expected_cols = {'portfolio_value', 'returns', 'positions', 'turnover'}
        assert expected_cols.issubset(set(result.columns))

    def test_smoke_benchmark_missing(self, sample_data):
        """benchmark_col not in prices should raise ValueError."""
        prices, signals, _ = sample_data
        with pytest.raises(ValueError, match="benchmark_col"):
            apply_beta_hedge_overlay(
                prices, signals,
                benchmark_col='NONEXISTENT',
            )

    def test_smoke_no_nan_portfolio_value(self, sample_data):
        """portfolio_value column should have no NaN except possibly the first row."""
        prices, signals, _ = sample_data
        result = apply_beta_hedge_overlay(
            prices, signals,
            benchmark_col='SPY',
            hedge_ratio=0.5,
            beta_lookback=60,
        )
        # First row is initialization; rows 1 onwards must be non-NaN
        assert not result['portfolio_value'].iloc[1:].isna().any()
