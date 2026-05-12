# riwaq/settings.py

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key secret!
SECRET_KEY = 'your-secret-key-here'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']  # Update for production

SITE_URL = 'https://127.0.0.1:8000'

# Custom user model
AUTH_USER_MODEL = 'users.User'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Authentication settings
LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'courses:home'
LOGOUT_REDIRECT_URL = 'courses:home'

ADMIN_ENABLED = False

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    
    # Third party apps
    'storages',
    
    # Local apps
    'users',
    'courses',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'courses.middleware.CourseAnalyticsMiddleware',
    'courses.middleware.AntiScrapingMiddleware',
    'courses.middleware.DeviceLimitMiddleware',
]

ROOT_URLCONF = 'riwaq.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Cloudflare R2 Configuration
# Get these from your Cloudflare R2 dashboard
AWS_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
AWS_ACCOUNT_ID = os.environ.get('AWS_ACCOUNT_ID')
AWS_STORAGE_BUCKET_NAME = 'riwaq-storage-bucket-2026'
AWS_S3_ENDPOINT_URL = f'https://{AWS_ACCOUNT_ID}.r2.cloudflarestorage.com'
AWS_S3_REGION_NAME = 'auto'  # R2 uses 'auto' region
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.{AWS_ACCOUNT_ID}.r2.cloudflarestorage.com'

# Media files (videos, PDFs, images)
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'

# Static files (CSS, JS, images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# For local development (fallback)
if DEBUG:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'
    
    # Comment out R2 config for local development
    # DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

CHARGILY_API_KEY = os.environ.get('CHARGILY_API_KEY', 'your-api-key')
CHARGILY_SECRET_KEY = os.environ.get('CHARGILY_SECRET_KEY', 'your-secret-key')
CHARGILY_MODE = os.environ.get('CHARGILY_MODE', 'test')  # 'test' or 'live'

# URLs for payment callbacks
CHARGILY_SUCCESS_URL = 'https://your-domain.com/payment/success/'
CHARGILY_FAILURE_URL = 'https://your-domain.com/payment/failure/'
CHARGILY_WEBHOOK_URL = 'https://your-domain.com/payment/webhook/'

# For local development with ngrok
if DEBUG:
    CHARGILY_SUCCESS_URL = 'http://localhost:8000/payment/success/'
    CHARGILY_FAILURE_URL = 'http://localhost:8000/payment/failure/'
    CHARGILY_WEBHOOK_URL = 'http://localhost:8000/payment/webhook/'

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = False # Turn on in production
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SAMESITE = 'Strict'

# Content Security Policy
CSP_DEFAULT_SRC = ("'none'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", 'https://cdn.jsdelivr.net', 'https://challenges.cloudflare.com')
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", 'https://cdn.jsdelivr.net')
CSP_IMG_SRC = ("'self'", 'data:', 'https:')
CSP_MEDIA_SRC = ("'self'", 'https://*.r2.cloudflarestorage.com')
CSP_FRAME_SRC = ("'self'", 'https://challenges.cloudflare.com')

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Or your email provider
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'your-email@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'your-password')
DEFAULT_FROM_EMAIL = 'Riwaq Platform <noreply@riwaq.com>'

# For production, use:
# EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
# ANYMAIL = {
#     'SENDGRID_API_KEY': os.environ.get('SENDGRID_API_KEY'),
# }