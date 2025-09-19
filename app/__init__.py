"""
Flask application factory for BrainBudget.
"""
import logging
import os
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from app.config import config
from app.services.firebase_service import FirebaseService
from app.utils.security import security_manager
from app.utils.monitoring import initialize_monitoring
from app.utils.cache import initialize_cache


def create_app(config_name=None):
    """
    Application factory function.

    Args:
        config_name (str): Configuration environment name

    Returns:
        Flask: Configured Flask application instance
    """
    # Create Flask app with explicit static folder configuration
    app = Flask(__name__, static_folder='../static', static_url_path='/static')

    # Load configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])

    # Validate configuration
    try:
        config[config_name].validate_config()
    except ValueError as e:
        app.logger.error(f"Configuration validation failed: {e}")
        if config_name == 'production':
            raise

    # Setup logging
    setup_logging(app)

    # Setup CORS
    CORS(app, origins=app.config['CORS_ORIGINS'])

    # Initialize Firebase
    try:
        firebase_service = FirebaseService()
        firebase_service.initialize(app)
        app.firebase = firebase_service
        app.logger.info("Firebase initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize Firebase: {e}")
        if config_name == 'production':
            raise

    # Initialize Security Manager
    try:
        redis_url = app.config.get('REDIS_URL')
        security_manager.initialize(redis_url)
        app.logger.info("Security manager initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize security manager: {e}")
        if config_name == 'production':
            app.logger.warning("Security features may be limited without Redis")

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)
    
    # Add security headers for production
    add_security_headers(app)
    
    # Initialize monitoring and metrics
    try:
        initialize_monitoring(app)
        app.logger.info("Monitoring initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize monitoring: {e}")
        if config_name == 'production':
            app.logger.warning("Application starting with limited monitoring")
    
    # Initialize caching system
    try:
        redis_url = app.config.get('REDIS_URL')
        initialize_cache(redis_url)
        app.logger.info("Cache system initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize cache system: {e}")
        if config_name == 'production':
            app.logger.warning("Application starting with limited caching")

    # Health check endpoin
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'app': 'BrainBudget',
            'version': '1.0.0'
        })

    app.logger.info(f"BrainBudget app created with config: {config_name}")
    return app


def setup_logging(app):
    """Setup application logging."""
    if not app.debug and not app.testing:
        # Configure logging for production
        logging.basicConfig(
            level=getattr(logging, app.config['LOG_LEVEL']),
            format='%(asctime)s %(levelname)s %(name)s %(message)s'
        )

    # Create logs directory if it doesn't exis
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # File handler for application logs
    file_handler = logging.FileHandler('logs/brainbudget.log')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s [%(filename)s:%(lineno)d] %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('BrainBudget startup')


def register_blueprints(app):
    """Register Flask blueprints."""
    from app.routes.auth import auth_bp
    from app.routes.upload import upload_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.frontend import frontend_bp
    from app.routes.analysis import analysis_bp
    from app.routes.plaid import plaid_bp
    from app.routes.plaid_webhooks import plaid_webhooks_bp
    from app.routes.notifications import notifications_bp
    from app.routes.goals import goals_bp
    from app.routes.ai_coach import ai_coach_bp
    from app.routes.ml_analytics import ml_analytics_bp
    from app.routes.advice_engine import advice_engine_bp
    from app.routes.guest import guest_bp
    from app.routes.community import community_bp
    from app.routes.profile import profile_bp

    # Register API blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(upload_bp, url_prefix='/api/upload')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
    app.register_blueprint(plaid_bp, url_prefix='/api/plaid')
    app.register_blueprint(plaid_webhooks_bp, url_prefix='/api/plaid/webhooks')
    app.register_blueprint(notifications_bp)  # Already has /api/notifications prefix
    app.register_blueprint(goals_bp)  # Already has /api/goals prefix
    app.register_blueprint(ai_coach_bp)  # Already has /api/coach prefix
    app.register_blueprint(ml_analytics_bp)  # Already has /api/analytics prefix
    app.register_blueprint(advice_engine_bp)  # Already has /api/advice prefix
    app.register_blueprint(guest_bp)  # Already has /api/guest prefix
    app.register_blueprint(community_bp)  # Already has /api/community prefix
    app.register_blueprint(profile_bp)  # Already has /api/profile prefix

    # Register frontend blueprint (no prefix for main routes)
    app.register_blueprint(frontend_bp)

    app.logger.info("Blueprints registered successfully")


def add_security_headers(app):
    """Add security headers to all responses."""
    
    @app.after_request
    def set_security_headers(response):
        # Get security headers from config
        headers = app.config.get('SECURITY_HEADERS', {})
        
        for header, value in headers.items():
            response.headers[header] = value
        
        # Content Security Policy
        if not app.debug:
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://www.gstatic.com; "
                "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
            response.headers['Content-Security-Policy'] = csp
        
        return response


def register_error_handlers(app):
    """Register application error handlers."""

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle HTTP exceptions with user-friendly messages."""
        app.logger.error(f"HTTP Exception: {error.code} - {error.description}")

        # ADHD-friendly error messages
        error_messages = {
            400: "Oops! Something wasn't quite right with your request. Let's try again! 🤗",
            401: "You'll need to log in first. No worries, it's quick and easy! 🔑",
            403: "Hmm, you don't have permission for that. Let's find another way! 🚫",
            404: "We couldn't find what you're looking for. Let's go back and try again! 🔍",
            413: "That file is a bit too big for us. Try a smaller one! 📁",
            429: "Whoa there! You're moving fast. Let's take a quick breather! ⏰",
            500: "Something went wrong on our end. We're fixing it! Don't worry! 🔧"
        }

        return jsonify({
            'error': True,
            'message': error_messages.get(error.code, "Something unexpected happened, but we're on it! 💪"),
            'status_code': error.code
        }), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected errors."""
        app.logger.error(f"Unexpected error: {str(error)}", exc_info=True)

        return jsonify({
            'error': True,
            'message': "Something unexpected happened, but don't worry - our team is looking into it! 🛠️",
            'status_code': 500
        }), 500

    @app.errorhandler(ValueError)
    def handle_value_error(error):
        """Handle validation errors."""
        app.logger.error(f"Validation error: {str(error)}")

        return jsonify({
            'error': True,
            'message': f"Hmm, there's an issue with the information provided: {str(error)} 🤔",
            'status_code': 400
        }), 400
