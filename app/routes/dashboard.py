"""Dashboard routes with live monitoring."""
from flask import Blueprint, render_template
from app.services.data_loader import get_data_loader
from app.services.charts import (
    create_cumulative_returns_chart,
    create_holdings_pie_chart
)

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@bp.route('/')
def index():
    """Dashboard home page with live monitoring."""
    loader = get_data_loader()
    strategies = loader.get_all_strategies()
    final_strategy = strategies['final']
    benchmark = strategies['benchmark']

    # Get key metrics
    final_metrics = final_strategy['metrics']
    bench_metrics = benchmark['metrics']

    # Calculate improvements
    improvements = {
        'return': (final_metrics['total_return'] - bench_metrics['total_return']) * 100,
        'sharpe': final_metrics['sharpe_ratio'] - bench_metrics['sharpe_ratio'],
        'dd': (final_metrics['max_drawdown'] - bench_metrics['max_drawdown']) * 100
    }

    # Generate charts
    cumulative_chart = create_cumulative_returns_chart(strategies)
    holdings_chart = create_holdings_pie_chart(final_strategy)

    # Get current positions
    current_signals = final_strategy['signals'].iloc[-1]
    active_positions = current_signals[current_signals > 0].index.tolist()
    num_positions = len(active_positions)

    # Recent performance
    returns = final_strategy['backtest']['returns']
    last_30d = (1 + returns.tail(30)).prod() - 1
    last_90d = (1 + returns.tail(90)).prod() - 1
    ytd_returns = returns[returns.index.year == returns.index[-1].year]
    ytd = (1 + ytd_returns).prod() - 1 if len(ytd_returns) > 0 else 0

    return render_template(
        'dashboard.html',
        metrics=final_metrics,
        bench_metrics=bench_metrics,
        improvements=improvements,
        cumulative_chart=cumulative_chart,
        holdings_chart=holdings_chart,
        active_positions=active_positions,
        num_positions=num_positions,
        last_30d=last_30d,
        last_90d=last_90d,
        ytd=ytd,
        last_date=final_strategy['backtest']['portfolio_value'].index[-1].strftime('%Y-%m-%d')
    )
