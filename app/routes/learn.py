"""Educational content routes."""
from flask import Blueprint, render_template

bp = Blueprint('learn', __name__, url_prefix='/learn')


@bp.route('/')
def index():
    """Learn hub with 5 educational tabs."""
    return render_template('learn.html')
