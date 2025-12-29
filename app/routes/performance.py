"""Performance analytics routes."""
from flask import Blueprint, render_template
from app.services.data_loader import get_data_loader
from app.services.charts import (
    create_cumulative_returns_chart,
    create_drawdown_chart,
    create_rolling_sharpe_chart,
    create_monthly_returns_heatmap,
    create_annual_returns_chart,
    create_return_distribution_chart
)

bp = Blueprint('performance', __name__, url_prefix='/performance')


@bp.route('/')
def index():
    """Performance analytics page."""
    loader = get_data_loader()
    strategies = loader.get_all_strategies()
    final_strategy = strategies['final']

    # Generate all charts
    cumulative_chart = create_cumulative_returns_chart(strategies)
    drawdown_chart = create_drawdown_chart(strategies)
    rolling_sharpe_chart = create_rolling_sharpe_chart(strategies)
    monthly_heatmap = create_monthly_returns_heatmap(final_strategy)
    annual_chart = create_annual_returns_chart(strategies)
    distribution_chart = create_return_distribution_chart(final_strategy)

    # Get metrics for all strategies
    comparison_data = []
    for key, strategy in strategies.items():
        metrics = strategy['metrics'].copy()
        metrics['name'] = strategy['name']
        comparison_data.append(metrics)

    return render_template(
        'performance.html',
        cumulative_chart=cumulative_chart,
        drawdown_chart=drawdown_chart,
        rolling_sharpe_chart=rolling_sharpe_chart,
        monthly_heatmap=monthly_heatmap,
        annual_chart=annual_chart,
        distribution_chart=distribution_chart,
        comparison_data=comparison_data
    )
