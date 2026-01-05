"""Interactive lab routes."""
from flask import Blueprint, render_template, request, jsonify
from app.services.data_loader import get_data_loader
from app.services.charts import create_stress_test_chart
import pandas as pd

bp = Blueprint('lab', __name__, url_prefix='/lab')


@bp.route('/')
def index():
    """Interactive lab page with trade drill-down."""
    loader = get_data_loader()
    trade_log = loader.get_trade_log()

    # Calculate aggregate statistics
    if trade_log is not None and len(trade_log) > 0:
        total_trades = len(trade_log)
        avg_holding_period = trade_log['days_held'].mean()
        win_rate = len(trade_log[trade_log['return'] > 0]) / total_trades * 100
        avg_win = trade_log[trade_log['return'] > 0]['return'].mean() * 100
        avg_loss = trade_log[trade_log['return'] < 0]['return'].mean() * 100
        best_trade = trade_log.loc[trade_log['return'].idxmax()]
        worst_trade = trade_log.loc[trade_log['return'].idxmin()]

        stats = {
            'total_trades': total_trades,
            'avg_holding_period': avg_holding_period,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'best_trade': best_trade,
            'worst_trade': worst_trade
        }
    else:
        stats = None

    # Get stress test data
    stress_tests = loader.get_stress_tests()
    stress_test_chart = create_stress_test_chart(stress_tests) if stress_tests else None

    return render_template(
        'lab.html',
        trade_log=trade_log,
        stats=stats,
        stress_tests=stress_tests,
        stress_test_chart=stress_test_chart
    )


@bp.route('/custom-backtest', methods=['POST'])
def custom_backtest():
    """Run custom backtest for user-specified date range."""
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        ema_window = int(data.get('ema_window', 126))  # Default to 126 days

        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date are required'}), 400

        # Load data
        loader = get_data_loader()
        prices = loader.get_prices()

        # Filter prices to date range
        prices_filtered = prices[start_date:end_date]

        if len(prices_filtered) < 50:
            return jsonify({'error': f'Insufficient data: only {len(prices_filtered)} days in range. Need at least 50 days.'}), 400

        # Run backtest
        from src.signals.trend_filter import generate_signals
        from src.backtest.engine import backtest_strategy

        signals = generate_signals(prices_filtered, method='ema', span=ema_window)
        benchmark_returns = prices_filtered.pct_change().mean(axis=1)

        backtest_result = backtest_strategy(
            prices=prices_filtered,
            signals=signals,
            benchmark_returns=benchmark_returns,
            transaction_cost=0.0005,
            rebalance_frequency='M'
        )

        # Extract metrics
        metrics = backtest_result['performance_metrics']
        benchmark_metrics = backtest_result['benchmark_metrics']

        # Calculate additional statistics
        final_value = backtest_result['portfolio_stats']['portfolio_value'].iloc[-1]
        total_days = len(prices_filtered)

        return jsonify({
            'success': True,
            'date_range': {
                'start': start_date,
                'end': end_date,
                'total_days': total_days
            },
            'strategy': {
                'total_return': float(metrics['total_return']),
                'annualized_return': float(metrics['annualized_return']),
                'sharpe_ratio': float(metrics['sharpe_ratio']),
                'sortino_ratio': float(metrics['sortino_ratio']),
                'max_drawdown': float(metrics['max_drawdown']),
                'calmar_ratio': float(metrics['calmar_ratio']),
                'win_rate': float(metrics['win_rate']),
                'final_value': float(final_value)
            },
            'benchmark': {
                'total_return': float(benchmark_metrics['total_return']),
                'annualized_return': float(benchmark_metrics['annualized_return']),
                'sharpe_ratio': float(benchmark_metrics['sharpe_ratio']),
                'max_drawdown': float(benchmark_metrics['max_drawdown'])
            },
            'outperformance': {
                'return': float(metrics['total_return'] - benchmark_metrics['total_return']),
                'sharpe': float(metrics['sharpe_ratio'] - benchmark_metrics['sharpe_ratio'])
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
