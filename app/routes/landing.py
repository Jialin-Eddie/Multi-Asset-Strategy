"""Landing page route with research story."""
from flask import Blueprint, render_template
from app.services.data_loader import get_data_loader

bp = Blueprint('landing', __name__)


@bp.route('/')
def index():
    """Landing page with research story flow."""
    loader = get_data_loader()
    strategies = loader.get_all_strategies()
    final_strategy = strategies['final']
    benchmark = strategies['benchmark']

    # Get key results for the story
    final_metrics = final_strategy['metrics']
    bench_metrics = benchmark['metrics']

    # Calculate improvements
    improvements = {
        'return': (final_metrics['total_return'] - bench_metrics['total_return']) * 100,
        'sharpe': final_metrics['sharpe_ratio'] - bench_metrics['sharpe_ratio'],
        'dd': (final_metrics['max_drawdown'] - bench_metrics['max_drawdown']) * 100
    }

    # Get regime data for storytelling
    regime_performance = loader.get_regime_performance()

    return render_template(
        'landing.html',
        final_metrics=final_metrics,
        bench_metrics=bench_metrics,
        improvements=improvements,
        regime_performance=regime_performance
    )
