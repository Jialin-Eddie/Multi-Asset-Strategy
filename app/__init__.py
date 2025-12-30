"""Flask application factory."""
from flask import Flask
from flask_caching import Cache

cache = Cache()


def create_app():
    """Create and configure Flask application."""
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    app.config['CACHE_TYPE'] = 'SimpleCache'
    app.config['CACHE_DEFAULT_TIMEOUT'] = 3600

    # Initialize extensions
    cache.init_app(app)

    # Register blueprints
    from app.routes import landing, dashboard, learn, performance, methodology, lab, regimes, variants
    app.register_blueprint(landing.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(learn.bp)
    app.register_blueprint(performance.bp)
    app.register_blueprint(methodology.bp)
    app.register_blueprint(lab.bp)
    app.register_blueprint(regimes.bp)
    app.register_blueprint(variants.bp)

    return app
