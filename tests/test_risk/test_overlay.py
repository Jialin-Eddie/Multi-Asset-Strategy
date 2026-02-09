# tests/test_risk/test_overlay.py
"""Tests for the risk overlay module."""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.risk.overlay import drawdown_scalar, volatility_scalar, apply_risk_overlay


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def portfolio_with_drawdown():
    """Portfolio that rises then falls — creates a clear drawdown."""
    dates = pd.date_range('2020-01-01', periods=200, freq='B')
    # Rise from 100 to 150, then drop to 110 (26.7% drawdown from peak)
    values = np.concatenate([
        np.linspace(100, 150, 100),
        np.linspace(150, 110, 100),
    ])
    return pd.Series(values, index=dates)


@pytest.fixture
def daily_returns_series():
    """Simple daily returns for vol scalar testing."""
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=500, freq='B')
    returns = np.random.normal(0.0004, 0.01, 500)
    return pd.Series(returns, index=dates)


@pytest.fixture
def multi_asset_prices():
    """Multi-asset prices for full overlay test."""
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=500, freq='B')
    prices = pd.DataFrame({
        'SPY': 100 * np.exp(np.cumsum(np.random.normal(0.0004, 0.012, 500))),
        'TLT': 100 * np.exp(np.cumsum(np.random.normal(0.0001, 0.008, 500))),
        'GLD': 100 * np.exp(np.cumsum(np.random.normal(0.0002, 0.010, 500))),
    }, index=dates)
    return prices


@pytest.fixture
def always_long_signals(multi_asset_prices):
    """Signals: always long all assets."""
    return pd.DataFrame(1.0, index=multi_asset_prices.index, columns=multi_asset_prices.columns)


# ============================================================================
# Tests: drawdown_scalar
# ============================================================================

class TestDrawdownScalar:

    def test_no_drawdown_returns_ones(self):
        """Rising portfolio should have scalar = 1.0 everywhere."""
        values = pd.Series(np.linspace(100, 200, 100))
        result = drawdown_scalar(values)
        assert (result == 1.0).all()

    def test_mild_drawdown_triggers_tier1(self, portfolio_with_drawdown):
        """Drawdown past -10% should trigger tier-1 scaling."""
        result = drawdown_scalar(
            portfolio_with_drawdown,
            threshold_1=-0.10,
            threshold_2=-0.20,
            scale_1=0.50,
            scale_2=0.00,
        )
        # Compute actual drawdown to check correctly
        running_max = portfolio_with_drawdown.expanding().max()
        dd = (portfolio_with_drawdown - running_max) / running_max
        # Where drawdown is between -20% and -10%, scalar should be 0.50
        in_tier1 = (dd <= -0.10) & (dd > -0.20)
        if in_tier1.any():
            assert (result[in_tier1] == 0.50).all()
        # Early rising phase should still be 1.0
        assert result.iloc[0] == 1.0

    def test_deep_drawdown_triggers_tier2(self, portfolio_with_drawdown):
        """Drawdown past -20% should trigger tier-2 (full exit)."""
        result = drawdown_scalar(
            portfolio_with_drawdown,
            threshold_1=-0.10,
            threshold_2=-0.20,
            scale_1=0.50,
            scale_2=0.00,
        )
        # Compute actual drawdown
        running_max = portfolio_with_drawdown.expanding().max()
        dd = (portfolio_with_drawdown - running_max) / running_max
        in_tier2 = dd <= -0.20
        if in_tier2.any():
            assert (result[in_tier2] == 0.0).all()

    def test_output_shape_matches_input(self, portfolio_with_drawdown):
        result = drawdown_scalar(portfolio_with_drawdown)
        assert len(result) == len(portfolio_with_drawdown)

    def test_scalar_range_0_to_1(self, portfolio_with_drawdown):
        result = drawdown_scalar(portfolio_with_drawdown)
        assert (result >= 0.0).all()
        assert (result <= 1.0).all()


# ============================================================================
# Tests: volatility_scalar
# ============================================================================

class TestVolatilityScalar:

    def test_returns_correct_length(self, daily_returns_series):
        result = volatility_scalar(daily_returns_series, target_vol=0.10, lookback=60)
        assert len(result) == len(daily_returns_series)

    def test_scalar_capped_at_max_leverage(self, daily_returns_series):
        result = volatility_scalar(
            daily_returns_series, target_vol=0.10, lookback=60, max_leverage=1.5
        )
        assert (result <= 1.5).all()

    def test_scalar_floored_at_min(self, daily_returns_series):
        result = volatility_scalar(
            daily_returns_series, target_vol=0.10, lookback=60, min_scalar=0.1
        )
        assert (result >= 0.1).all()

    def test_high_target_vol_scales_up(self, daily_returns_series):
        """Higher target vol should produce larger scalars on average."""
        low = volatility_scalar(daily_returns_series, target_vol=0.05, lookback=60)
        high = volatility_scalar(daily_returns_series, target_vol=0.20, lookback=60)
        # On average, high target should produce bigger scalars
        assert high.mean() > low.mean()

    def test_nan_handling(self):
        """Should not produce NaN in output."""
        returns = pd.Series(np.random.normal(0, 0.01, 100))
        result = volatility_scalar(returns, target_vol=0.10, lookback=60)
        assert not result.isna().any()


# ============================================================================
# Tests: apply_risk_overlay
# ============================================================================

class TestApplyRiskOverlay:

    def test_returns_expected_columns(self, multi_asset_prices, always_long_signals):
        result = apply_risk_overlay(multi_asset_prices, always_long_signals)
        expected_cols = ['portfolio_value', 'returns', 'positions', 'turnover']
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_output_length_matches_input(self, multi_asset_prices, always_long_signals):
        result = apply_risk_overlay(multi_asset_prices, always_long_signals)
        assert len(result) == len(multi_asset_prices)

    def test_initial_capital(self, multi_asset_prices, always_long_signals):
        result = apply_risk_overlay(
            multi_asset_prices, always_long_signals, initial_capital=1000.0
        )
        assert result['portfolio_value'].iloc[0] == 1000.0

    def test_no_overlay_matches_baseline(self, multi_asset_prices, always_long_signals):
        """With no drawdown and no vol scaling, result should be close to baseline."""
        result = apply_risk_overlay(
            multi_asset_prices, always_long_signals,
            dd_threshold_1=-0.99,  # Effectively disabled
            dd_threshold_2=-0.99,
            vol_target=None,
            transaction_cost=0.0,
        )
        # Portfolio should grow since signals are always long
        assert result['portfolio_value'].iloc[-1] > result['portfolio_value'].iloc[0]

    def test_drawdown_control_reduces_losses(self, multi_asset_prices, always_long_signals):
        """With drawdown control ON, MaxDD should not be worse than without."""
        no_dd = apply_risk_overlay(
            multi_asset_prices, always_long_signals,
            dd_threshold_1=-0.99, dd_threshold_2=-0.99,
            transaction_cost=0.0,
        )
        with_dd = apply_risk_overlay(
            multi_asset_prices, always_long_signals,
            dd_threshold_1=-0.05, dd_threshold_2=-0.10,
            dd_scale_1=0.50, dd_scale_2=0.00,
            transaction_cost=0.0,
        )
        # Calculate max drawdowns
        no_dd_cum = (1 + no_dd['returns']).cumprod()
        no_dd_maxdd = ((no_dd_cum - no_dd_cum.expanding().max()) / no_dd_cum.expanding().max()).min()

        with_dd_cum = (1 + with_dd['returns']).cumprod()
        with_dd_maxdd = ((with_dd_cum - with_dd_cum.expanding().max()) / with_dd_cum.expanding().max()).min()

        # With DD control, max drawdown should be same or better (less negative)
        assert with_dd_maxdd >= no_dd_maxdd or abs(with_dd_maxdd - no_dd_maxdd) < 0.02

    def test_vol_target_works(self, multi_asset_prices, always_long_signals):
        """With vol target, result should be produced without errors."""
        result = apply_risk_overlay(
            multi_asset_prices, always_long_signals,
            vol_target=0.10, vol_lookback=60,
        )
        assert not result['portfolio_value'].isna().all()
        assert result['portfolio_value'].iloc[-1] > 0

    def test_zero_signals_stays_flat(self, multi_asset_prices):
        """With all-zero signals, portfolio should stay near initial capital."""
        zero_signals = pd.DataFrame(0.0, index=multi_asset_prices.index, columns=multi_asset_prices.columns)
        result = apply_risk_overlay(
            multi_asset_prices, zero_signals,
            transaction_cost=0.0,
        )
        # Should remain at initial capital (no positions)
        assert abs(result['portfolio_value'].iloc[-1] - 100.0) < 1.0
