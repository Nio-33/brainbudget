"""
Configuration settings for BrainBudget Flask application.
"""
import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class."""

    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    DEBUG = os.environ.get('DEBUG', 'False').lower() in ['true', '1', 'yes']
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)  # 24 hour session duration
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Firebase configuration
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID')
    FIREBASE_PRIVATE_KEY = os.environ.get('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n')
    FIREBASE_CLIENT_EMAIL = os.environ.get('FIREBASE_CLIENT_EMAIL')

    # Firebase client configuration (for frontend)
    FIREBASE_API_KEY = os.environ.get('FIREBASE_API_KEY')
    FIREBASE_AUTH_DOMAIN = os.environ.get('FIREBASE_AUTH_DOMAIN')
    FIREBASE_STORAGE_BUCKET = os.environ.get('FIREBASE_STORAGE_BUCKET')
    FIREBASE_MESSAGING_SENDER_ID = os.environ.get('FIREBASE_MESSAGING_SENDER_ID')
    FIREBASE_APP_ID = os.environ.get('FIREBASE_APP_ID')

    # Google Gemini API configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

    # Plaid API configuration
    PLAID_CLIENT_ID = os.environ.get('PLAID_CLIENT_ID')
    PLAID_SECRET = os.environ.get('PLAID_SECRET')
    PLAID_ENV = os.environ.get('PLAID_ENV', 'sandbox')
    PLAID_WEBHOOK_SECRET = os.environ.get('PLAID_WEBHOOK_SECRET')

    # Firebase Cloud Messaging configuration
    FCM_SERVER_KEY = os.environ.get('FCM_SERVER_KEY')  # For server-to-server communication
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY')  # For web push
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY')

    # Notification system configuration
    NOTIFICATION_RATE_LIMIT_DAILY = int(os.environ.get('NOTIFICATION_RATE_LIMIT_DAILY', '10'))
    NOTIFICATION_QUIET_HOURS_START = int(os.environ.get('NOTIFICATION_QUIET_HOURS_START', '22'))  # 10 PM
    NOTIFICATION_QUIET_HOURS_END = int(os.environ.get('NOTIFICATION_QUIET_HOURS_END', '8'))  # 8 AM

    # File upload configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

    # Currency configuration
    SUPPORTED_CURRENCIES = {
        'USD': {'symbol': '$', 'name': 'US Dollar', 'format': 'before'},
        'NGN': {'symbol': '₦', 'name': 'Nigerian Naira', 'format': 'before'},
        'EUR': {'symbol': '€', 'name': 'Euro', 'format': 'before'},
        'GBP': {'symbol': '£', 'name': 'British Pound', 'format': 'before'}
    }
    DEFAULT_CURRENCY = os.environ.get('DEFAULT_CURRENCY', 'USD')

    # CORS configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')

    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    @staticmethod
    def validate_config():
        """Validate required configuration variables."""
        required_vars = [
            'FIREBASE_PROJECT_ID',
            'FIREBASE_CLIENT_EMAIL',
            'GEMINI_API_KEY'
        ]

        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)

        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    
    # Security settings for production
    SESSION_COOKIE_SECURE = True  # Require HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # Performance settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)  # Shorter session in prod
    
    # Security headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }
    
    # Rate limiting and security
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    RATE_LIMIT_STORAGE_URL = REDIS_URL
    
    # File upload restrictions (stricter in production)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB in production
    
    # Logging configuration
    LOG_LEVEL = 'WARNING'
    ENABLE_ACCESS_LOGS = True
    
    # CORS - restrictive in production
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',') if os.environ.get('CORS_ORIGINS') else []
    
    # Database connection pooling
    FIRESTORE_MAX_CONNECTIONS = 100
    
    # SSL Configuration
    SSL_DISABLE = False
    PREFERRED_URL_SCHEME = 'https'

    @staticmethod
    def validate_config():
        """Additional validation for production."""
        Config.validate_config()

        # Ensure secret key is set in production
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY must be set in production")
        
        # Validate security-critical environment variables
        required_prod_vars = [
            'FIREBASE_PRIVATE_KEY',
            'GEMINI_API_KEY',
            'PLAID_SECRET'
        ]
        
        missing_vars = []
        for var in required_prod_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing critical production environment variables: {', '.join(missing_vars)}")
        
        # Validate Redis URL format
        redis_url = os.environ.get('REDIS_URL')
        if redis_url and not redis_url.startswith(('redis://', 'rediss://')):
            raise ValueError("Invalid REDIS_URL format")
        
        # Validate CORS origins in production
        cors_origins = os.environ.get('CORS_ORIGINS', '')
        if cors_origins:
            origins = cors_origins.split(',')
            for origin in origins:
                if not origin.startswith(('https://', 'http://localhost')):
                    raise ValueError(f"Invalid CORS origin in production: {origin}")


class StagingConfig(ProductionConfig):
    """Staging configuration - like production but less restrictive."""
    DEBUG = False
    
    # Staging-specific settings
    LOG_LEVEL = 'INFO'
    SESSION_COOKIE_SECURE = True  # Still require HTTPS in staging
    
    # More lenient file size for testing
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB in staging
    
    @staticmethod 
    def validate_config():
        """Staging configuration validation."""
        # Use base Config validation (less strict than production)
        Config.validate_config()


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    FIREBASE_PROJECT_ID = 'test-project'


config = {
    'development': DevelopmentConfig,
    'staging': StagingConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
