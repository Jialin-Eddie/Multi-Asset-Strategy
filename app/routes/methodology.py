"""Methodology explanation routes."""
from flask import Blueprint, render_template
from app.services.data_loader import get_data_loader
from app.services.charts import create_ema_sensitivity_chart

bp = Blueprint('methodology', __name__, url_prefix='/methodology')


@bp.route('/')
def index():
    """Methodology page."""
    loader = get_data_loader()

    # Get optimization results if available
    ema_opt = loader.get_optimization_results()
    signal_comp = loader.get_signal_comparison()

    # Get EMA sensitivity analysis
    ema_sensitivity_data = loader.get_ema_sensitivity()
    ema_sensitivity_chart = create_ema_sensitivity_chart(ema_sensitivity_data) if ema_sensitivity_data is not None else None

    # Asset universe information
    assets = [
        {
            'ticker': 'SPY',
            'name': 'S&P 500 ETF',
            'class': 'Equities',
            'role': 'Growth engine, equity exposure'
        },
        {
            'ticker': 'TLT',
            'name': '20+ Year Treasury Bond ETF',
            'class': 'Fixed Income',
            'role': 'Safe haven, negative correlation with stocks'
        },
        {
            'ticker': 'GLD',
            'name': 'Gold ETF',
            'class': 'Commodities',
            'role': 'Inflation hedge, crisis protection'
        },
        {
            'ticker': 'DBC',
            'name': 'Commodity Index ETF',
            'class': 'Commodities',
            'role': 'Real assets, inflation protection'
        },
        {
            'ticker': 'VNQ',
            'name': 'Real Estate ETF',
            'class': 'Real Estate',
            'role': 'Income generation, diversification'
        }
    ]

    # Research timeline
    timeline = [
        {
            'phase': 'Data Acquisition',
            'date': '2025-12-21',
            'description': 'Downloaded 20 years of data (2005-2025) for 5 ETFs',
            'outcome': '5,238 trading days, 100% data quality'
        },
        {
            'phase': 'Signal Testing',
            'date': '2025-12-21',
            'description': 'Tested 5 signal methods (SMA, EMA, Absolute Mom, Relative Mom, Dual Mom)',
            'outcome': 'EMA winner: Sharpe 0.73 vs SMA 0.71'
        },
        {
            'phase': 'EMA Optimization',
            'date': '2025-12-21',
            'description': 'Optimized EMA span across 6 parameters (63d-378d)',
            'outcome': '126d optimal: Sharpe 0.82 (+12% vs 252d)'
        },
        {
            'phase': 'Position Sizing',
            'date': '2025-12-21',
            'description': 'Compared equal weight vs risk parity',
            'outcome': 'Equal weight sufficient (simpler, equivalent results)'
        },
        {
            'phase': 'Final Validation',
            'date': '2025-12-29',
            'description': 'Comprehensive backtest and robustness analysis',
            'outcome': 'PRODUCTION READY: Sharpe 0.82, 592.6% return'
        }
    ]

    # Key decisions
    decisions = [
        {
            'question': 'Why EMA over SMA?',
            'answer': 'EMA responds faster to trend changes by weighting recent prices more heavily, resulting in 2% higher Sharpe ratio (0.73 vs 0.71). Backtested across 20 years with superior drawdown control.',
            'data': 'EMA 252d: 514.2% return vs SMA 252d: 482.7% return'
        },
        {
            'question': 'Why 126 days (6 months) vs 252 days (12 months)?',
            'answer': 'Parameter optimization showed 126d optimal: +12% Sharpe improvement (0.82 vs 0.73), +78% higher total return. Faster trend response while maintaining noise filtering. Robustness validated with CV 5.5% (minimal overfitting risk).',
            'data': '126d: 592.6% return vs 252d: 514.2% return'
        },
        {
            'question': 'Why equal weight vs risk parity?',
            'answer': 'Risk parity adds no value for pre-filtered trend signals with small universe (≤5 assets). Performance nearly identical (Sharpe 0.72 vs 0.71, correlation 0.953). Equal weight preferred for simplicity and transparency.',
            'data': 'Equal Weight: 482.7%, Risk Parity: 479.6% (negligible difference)'
        },
        {
            'question': 'Why monthly rebalancing?',
            'answer': 'Balances transaction costs vs responsiveness. Monthly rebalancing controls turnover (~37% monthly) while allowing trends to develop. Lower frequency (quarterly) misses trend changes; higher frequency (weekly) increases costs.',
            'data': 'Transaction costs: ~0.18% annually with monthly rebalancing'
        }
    ]

    return render_template(
        'methodology.html',
        assets=assets,
        timeline=timeline,
        decisions=decisions,
        ema_opt=ema_opt,
        signal_comp=signal_comp,
        ema_sensitivity_chart=ema_sensitivity_chart,
        ema_sensitivity_data=ema_sensitivity_data
    )
