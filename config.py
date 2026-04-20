"""
🔧 Configuration Manager
Loads environment variables and provides centralized config access.
Security: Never expose sensitive values in frontend code.
"""
import os
from dotenv import load_dotenv
from datetime import timedelta

# Load .env file
load_dotenv()

class Config:
    """Application Configuration"""
    
    # 🔐 Telegram
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    ADMIN_USER_IDS = [int(x.strip()) for x in os.getenv('ADMIN_USER_IDS', '').split(',') if x.strip()]
    
    # 🗄️ Firebase (Backend - Service Account)
    FIREBASE_CONFIG = {
        'type': os.getenv('FIREBASE_TYPE', 'service_account'),
        'project_id': os.getenv('FIREBASE_PROJECT_ID', ''),
        'private_key_id': os.getenv('FIREBASE_PRIVATE_KEY_ID', ''),
        'private_key': os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
        'client_email': os.getenv('FIREBASE_CLIENT_EMAIL', ''),
        'client_id': os.getenv('FIREBASE_CLIENT_ID', ''),
        'auth_uri': os.getenv('FIREBASE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth'),
        'token_uri': os.getenv('FIREBASE_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
        'auth_provider_x509_cert_url': os.getenv('FIREBASE_AUTH_PROVIDER_X509_CERT_URL', 'https://www.googleapis.com/oauth2/v1/certs'),
        'client_x509_cert_url': os.getenv('FIREBASE_CLIENT_X509_CERT_URL', '')
    }
    
    # 🌐 Firebase (Frontend - Public Config)
    FRONTEND_FIREBASE = {
        'apiKey': os.getenv('FIREBASE_API_KEY', ''),
        'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN', ''),
        'databaseURL': os.getenv('FIREBASE_DATABASE_URL', ''),
        'projectId': os.getenv('FIREBASE_PROJECT_ID', ''),
        'storageBucket': f"{os.getenv('FIREBASE_PROJECT_ID', '')}.firebasestorage.app",
        'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID', '123003124713'),
        'appId': os.getenv('FIREBASE_APP_ID', '')
    }
    
    # 💰 Points & Monetization
    AD_SMART_LINK = os.getenv('AD_SMART_LINK', '')
    YOUTUBE_LINK = os.getenv('YOUTUBE_LINK', '')
    INSTAGRAM_LINK = os.getenv('INSTAGRAM_LINK', '')
    FACEBOOK_LINK = os.getenv('FACEBOOK_LINK', '')
    
    POINTS_PER_DOLLAR = int(os.getenv('POINTS_PER_DOLLAR', 100))
    AD_POINTS = int(os.getenv('AD_POINTS', 25))
    SOCIAL_POINTS = int(os.getenv('SOCIAL_POINTS', 100))
    REFERRAL_BONUS = int(os.getenv('REFERRAL_BONUS', 50))
    
    # 🛡️ Security
    RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', 10))
    RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', 60))  # seconds
    MAX_ACCOUNTS_PER_IP = int(os.getenv('MAX_ACCOUNTS_PER_IP', 3))
    ENABLE_IP_TRACKING = os.getenv('ENABLE_IP_TRACKING', 'true').lower() == 'true'
    
    # 🌍 URLs
    APP_URL = os.getenv('APP_URL', 'https://localhost:5000')
    WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://localhost:5000')
    ADMIN_SECRET_KEY = os.getenv('ADMIN_SECRET_KEY', 'dev-secret-change-in-production')
    
    # 🔧 Flask
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # ⏱️ Task Settings
    TASK_COOLDOWN_SECONDS = 300  # 5 minutes between same task submissions
    PENDING_REVIEW_TIMEOUT_HOURS = 48  # Auto-reject after 48h if not reviewed
    
    # 📸 Screenshot Settings
    MAX_SCREENSHOT_SIZE_MB = 5
    ALLOWED_SCREENSHOT_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    
    @classmethod
    def validate(cls):
        """Validate critical configuration values"""
        errors = []
        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN is not set")
        if not cls.FIREBASE_CONFIG['project_id']:
            errors.append("FIREBASE_PROJECT_ID is not set")
        if cls.FLASK_ENV == 'production' and cls.ADMIN_SECRET_KEY == 'dev-secret-change-in-production':
            errors.append("ADMIN_SECRET_KEY must be changed in production")
        return errors


class DevelopmentConfig(Config):
    """Development overrides"""
    DEBUG = True
    RATE_LIMIT_REQUESTS = 100  # More lenient for testing


class ProductionConfig(Config):
    """Production hardening"""
    DEBUG = False
    # Additional production security can be added here


# Configuration selector
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': Config
}

current_config = config_by_name.get(os.getenv('FLASK_ENV', 'default'), Config)
