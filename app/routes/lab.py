"""Interactive lab routes."""
from flask import Blueprint, render_template
from app.services.data_loader import get_data_loader

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

    return render_template(
        'lab.html',
        trade_log=trade_log,
        stats=stats
    )
