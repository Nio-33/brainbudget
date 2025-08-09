"""
Frontend routes for BrainBudget web application.
Serves HTML pages and handles static file requests.
"""
from flask import Blueprint, render_template, request, jsonify, send_from_directory
import logging
import os

logger = logging.getLogger(__name__)

# Create blueprint for frontend routes
frontend_bp = Blueprint('frontend', __name__, template_folder='../../templates', static_folder='../../static')


@frontend_bp.route('/')
def index():
    """Serve the BrainBudget home page showcasing all features."""
    try:
        return render_template('home.html')
    except Exception as e:
        logger.error(f"Error serving home page: {e}")
        return render_template('error.html', message="Unable to load the home page"), 500


@frontend_bp.route('/upload')
def upload_page():
    """Serve the upload interface page."""
    try:
        return render_template('upload.html')
    except Exception as e:
        logger.error(f"Error serving upload page: {e}")
        return render_template('error.html', message="Unable to load the upload page"), 500


@frontend_bp.route('/analysis')
def analysis_page():
    """Serve the analysis results page."""
    try:
        # In a real implementation, you might pass analysis data here
        return render_template('analysis.html')
    except Exception as e:
        logger.error(f"Error serving analysis page: {e}")
        return render_template('error.html', message="Unable to load the analysis page"), 500


@frontend_bp.route('/dashboard')
def dashboard_page():
    """Serve the dashboard page."""
    try:
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"Error serving dashboard page: {e}")
        return render_template('error.html', message="Unable to load the dashboard page"), 500


@frontend_bp.route('/settings')
def settings_page():
    """Serve the settings page."""
    try:
        return render_template('settings.html')
    except Exception as e:
        logger.error(f"Error serving settings page: {e}")
        return render_template('error.html', message="Unable to load the settings page"), 500


@frontend_bp.route('/auth/login')
def login_page():
    """Serve the authentication login page."""
    try:
        return render_template('auth/login.html')
    except Exception as e:
        logger.error(f"Error serving login page: {e}")
        return render_template('error.html', message="Unable to load the login page"), 500


@frontend_bp.route('/auth/register')
def register_page():
    """Serve the authentication register page."""
    try:
        return render_template('auth/signup.html')
    except Exception as e:
        logger.error(f"Error serving register page: {e}")
        return render_template('error.html', message="Unable to load the registration page"), 500


@frontend_bp.route('/auth/signup')
def signup_page():
    """Serve the dedicated signup page."""
    try:
        return render_template('auth/signup.html')
    except Exception as e:
        logger.error(f"Error serving signup page: {e}")
        return render_template('error.html', message="Unable to load the signup page"), 500


@frontend_bp.route('/profile')
def profile_page():
    """Serve the user profile page."""
    try:
        return render_template('auth/profile.html')
    except Exception as e:
        logger.error(f"Error serving profile page: {e}")
        return render_template('error.html', message="Unable to load the profile page"), 500


@frontend_bp.route('/charts-demo')
def charts_demo():
    """Serve the charts demonstration page."""
    try:
        return render_template('charts_demo.html')
    except Exception as e:
        logger.error(f"Error serving charts demo: {e}")
        return render_template('error.html', message="Unable to load the charts demo"), 500


@frontend_bp.route('/sw.js')
def service_worker():
    """Serve the service worker file."""
    try:
        return send_from_directory('static', 'sw.js', mimetype='application/javascript')
    except Exception as e:
        logger.error(f"Error serving service worker: {e}")
        return "Service worker not found", 404


@frontend_bp.route('/manifest.json')
def manifest():
    """Serve the PWA manifest file."""
    try:
        return send_from_directory('static', 'manifest.json', mimetype='application/json')
    except Exception as e:
        logger.error(f"Error serving manifest: {e}")
        return "Manifest not found", 404


@frontend_bp.route('/offline')
def offline_page():
    """Serve offline fallback page."""
    try:
        return render_template('offline.html')
    except Exception as e:
        logger.error(f"Error serving offline page: {e}")
        # Return minimal offline HTML if template fails
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Offline - BrainBudget</title>
            <style>
                body { font-family: system-ui, sans-serif; text-align: center; padding: 2rem; }
                .container { max-width: 400px; margin: 0 auto; }
                .icon { font-size: 3rem; margin-bottom: 1rem; }
                button { padding: 0.75rem 1.5rem; margin: 0.5rem; border: none; border-radius: 0.5rem; cursor: pointer; }
                .primary { background: #4A90E2; color: white; }
                .secondary { background: #f0f0f0; color: #333; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">📡</div>
                <h1>You're offline</h1>
                <p>Don't worry! BrainBudget works offline. Your data will sync when you're back online.</p>
                <button class="primary" onclick="location.reload()">Try Again</button>
                <button class="secondary" onclick="history.back()">Go Back</button>
            </div>
        </body>
        </html>
        """, 200


@frontend_bp.route('/favicon.ico')
def favicon():
    """Serve favicon."""
    try:
        return send_from_directory('static/icons', 'favicon.ico')
    except Exception as e:
        logger.debug(f"Favicon not found: {e}")
        return "", 204  # No content, but not an error


# Error handlers for frontend routes
@frontend_bp.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors with ADHD-friendly messaging."""
    return render_template('error.html', 
                         title="Page Not Found",
                         message="We couldn't find what you're looking for. Let's get you back on track! 🧭",
                         suggestion="Try going back to the home page or checking the URL.",
                         error_code=404), 404


@frontend_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors with ADHD-friendly messaging."""
    logger.error(f"Internal server error: {error}")
    return render_template('error.html',
                         title="Something Went Wrong",
                         message="Oops! Something unexpected happened, but don't worry - we're on it! 🛠️",
                         suggestion="Please try refreshing the page or come back in a few minutes.",
                         error_code=500), 500


@frontend_bp.errorhandler(503)
def service_unavailable(error):
    """Handle 503 errors (service unavailable)."""
    return render_template('error.html',
                         title="Service Temporarily Unavailable", 
                         message="We're doing some quick maintenance. We'll be back shortly! ⚙️",
                         suggestion="Please try again in a few minutes.",
                         error_code=503), 503


# Route for handling PWA app installation
@frontend_bp.route('/install')
def install_page():
    """Serve PWA installation guidance page."""
    try:
        return render_template('install.html')
    except Exception as e:
        logger.error(f"Error serving install page: {e}")
        return render_template('error.html', message="Unable to load installation guide"), 500


@frontend_bp.route('/connect-bank')
def connect_bank_page():
    """Serve the bank connection onboarding page."""
    try:
        return render_template('connect_bank.html')
    except Exception as e:
        logger.error(f"Error serving bank connection page: {e}")
        return render_template('error.html', message="Unable to load bank connection page"), 500


@frontend_bp.route('/goals/create')
def create_goal_page():
    """Serve the ADHD-friendly goal creation wizard."""
    try:
        return render_template('goal_wizard.html')
    except Exception as e:
        logger.error(f"Error serving goal creation page: {e}")
        return render_template('error.html', message="Unable to load goal creation page"), 500


@frontend_bp.route('/coach')
def ai_coach_page():
    """Serve the AI financial coach chat interface."""
    try:
        return render_template('ai_coach.html')
    except Exception as e:
        logger.error(f"Error serving AI coach page: {e}")
        return render_template('error.html', message="Unable to load AI coach page"), 500


@frontend_bp.route('/insights')
def insights_page():
    """Serve the ML-powered spending insights dashboard."""
    try:
        return render_template('insights.html')
    except Exception as e:
        logger.error(f"Error serving insights page: {e}")
        return render_template('error.html', message="Unable to load insights page"), 500


@frontend_bp.route('/advice')
def advice_page():
    """Serve the personalized financial advice dashboard."""
    try:
        return render_template('advice.html')
    except Exception as e:
        logger.error(f"Error serving advice page: {e}")
        return render_template('error.html', message="Unable to load advice page"), 500


@frontend_bp.route('/community')
def community_page():
    """Serve the ADHD community page (coming soon)."""
    try:
        return render_template('community.html')
    except Exception as e:
        logger.error(f"Error serving community page: {e}")
        return render_template('error.html', message="Unable to load community page"), 500


# Health check specifically for frontend
@frontend_bp.route('/frontend-health')
def frontend_health():
    """Frontend-specific health check."""
    try:
        # Test template rendering
        render_template('base.html')
        
        return jsonify({
            'status': 'healthy',
            'component': 'frontend',
            'templates': 'ok',
            'static_files': 'ok'
        }), 200
    except Exception as e:
        logger.error(f"Frontend health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'component': 'frontend',
            'error': str(e)
        }), 503


# Route to serve robots.txt
@frontend_bp.route('/robots.txt')
def robots_txt():
    """Serve robots.txt for SEO."""
    robots_content = """User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/

Sitemap: https://brainbudget.app/sitemap.xml
"""
    return robots_content, 200, {'Content-Type': 'text/plain'}


# Route to serve sitemap.xml (basic)
@frontend_bp.route('/sitemap.xml')
def sitemap():
    """Serve basic sitemap for SEO."""
    sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://brainbudget.app/</loc>
        <changefreq>weekly</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>https://brainbudget.app/upload</loc>
        <changefreq>monthly</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>https://brainbudget.app/dashboard</loc>
        <changefreq>weekly</changefreq>
        <priority>0.9</priority>
    </url>
    <url>
        <loc>https://brainbudget.app/settings</loc>
        <changefreq>monthly</changefreq>
        <priority>0.7</priority>
    </url>
</urlset>"""
    return sitemap_content, 200, {'Content-Type': 'application/xml'}


# Template filters for ADHD-friendly formatting
@frontend_bp.app_template_filter('currency')
def currency_filter(amount):
    """Format currency amounts in a friendly way."""
    if amount is None:
        return "$0.00"
    return f"${amount:,.2f}"


@frontend_bp.app_template_filter('friendly_date')
def friendly_date_filter(date):
    """Format dates in a friendly, readable way."""
    if not date:
        return "Unknown date"
    
    try:
        from datetime import datetime, date as date_type
        
        if isinstance(date, str):
            date = datetime.fromisoformat(date.replace('Z', '+00:00'))
        elif isinstance(date, date_type):
            date = datetime.combine(date, datetime.min.time())
        
        now = datetime.now(date.tzinfo)
        diff = now - date
        
        if diff.days == 0:
            return "Today"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return date.strftime("%B %d, %Y")
            
    except Exception as e:
        logger.warning(f"Date formatting error: {e}")
        return str(date)


@frontend_bp.app_template_filter('percentage')
def percentage_filter(value, total):
    """Calculate and format percentages."""
    if not total or total == 0:
        return "0%"
    try:
        percentage = (value / total) * 100
        return f"{percentage:.1f}%"
    except (TypeError, ZeroDivisionError):
        return "0%"


# Context processors for template global variables
@frontend_bp.app_context_processor
def inject_global_vars():
    """Inject global variables into all templates."""
    return {
        'app_name': 'BrainBudget',
        'app_version': '1.0.0',
        'support_email': 'help@brainbudget.app',
        'current_year': 2025
    }