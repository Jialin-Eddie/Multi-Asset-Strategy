"""Market regime analysis routes."""
from flask import Blueprint, render_template
from app.services.data_loader import get_data_loader
from app.services.charts import create_regime_timeline_chart

bp = Blueprint('regimes', __name__, url_prefix='/regimes')


@bp.route('/')
def index():
    """Market regime analysis page."""
    loader = get_data_loader()
    strategies = loader.get_all_strategies()
    final_strategy = strategies['final']

    # Get regime data
    regimes = loader.get_regimes()
    regime_performance = loader.get_regime_performance()

    # Get prices for chart
    prices = loader.get_prices()

    # Create regime timeline chart
    regime_chart = create_regime_timeline_chart(
        prices['SPY'],
        regimes,
        final_strategy['backtest']['portfolio_value']
    )

    return render_template(
        'regimes.html',
        regime_chart=regime_chart,
        regime_performance=regime_performance,
        regimes=regimes
    )
