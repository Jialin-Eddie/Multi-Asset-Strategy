"""Strategy variants routes."""
from flask import Blueprint, render_template
from app.services.data_loader import get_data_loader

bp = Blueprint('variants', __name__, url_prefix='/variants')


@bp.route('/')
def index():
    """Strategy variants comparison page."""
    loader = get_data_loader()
    strategies = loader.get_all_strategies()

    # Get core strategy metrics
    final_metrics = strategies['final']['metrics']
    initial_metrics = strategies['initial']['metrics']

    # Hardcoded variant data for MVP (will compute dynamically later)
    # These are example values - in production, compute from actual backtests
    variants = [
        {
            'name': 'Core Strategy',
            'description': 'EMA 126d, equal weight, monthly rebalancing',
            'total_return': final_metrics['total_return'],
            'sharpe': final_metrics['sharpe_ratio'],
            'max_dd': final_metrics['max_drawdown'],
            'turnover': 0.37,  # Estimated monthly turnover
            'best_for': 'Balanced risk-return, default choice'
        },
        {
            'name': 'Conservative',
            'description': 'EMA 189d (9 months), lower turnover',
            'total_return': initial_metrics['total_return'],
            'sharpe': initial_metrics['sharpe_ratio'],
            'max_dd': initial_metrics['max_drawdown'],
            'turnover': 0.29,
            'best_for': 'Lower costs, smoother trends'
        },
        {
            'name': 'Aggressive',
            'description': 'EMA 63d (3 months), faster response',
            'total_return': 6.35,
            'sharpe': 0.77,
            'max_dd': -0.26,
            'turnover': 0.48,
            'best_for': 'Trending markets, higher costs acceptable'
        },
        {
            'name': 'Buy & Hold',
            'description': 'Equal weight rebalance only',
            'total_return': strategies['benchmark']['metrics']['total_return'],
            'sharpe': strategies['benchmark']['metrics']['sharpe_ratio'],
            'max_dd': strategies['benchmark']['metrics']['max_drawdown'],
            'turnover': 0.05,
            'best_for': 'Benchmark comparison'
        }
    ]

    return render_template(
        'variants.html',
        variants=variants
    )
