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

    @staticmethod
    def validate_config():
        """Additional validation for production."""
        Config.validate_config()

        # Ensure secret key is set in production
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY must be set in production")


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    FIREBASE_PROJECT_ID = 'test-project'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
