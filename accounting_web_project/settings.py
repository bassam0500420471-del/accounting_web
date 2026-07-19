"""
Django settings for accounting project
Production settings for Render
"""

from pathlib import Path
import os
from django.utils.translation import gettext_lazy as _

# ============================================================
# BASE DIR
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# ============================================================
# SECURITY
# ============================================================

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-insecure-key-for-local-only"
)

DEBUG = False


ALLOWED_HOSTS = [
    "accounting-system.net",
    "www.accounting-system.net",
    "accounting-web-72p4.onrender.com",
    "localhost",
    "127.0.0.1",
]


CSRF_TRUSTED_ORIGINS = [
    "https://accounting-system.net",
    "https://www.accounting-system.net",
    "https://accounting-web-72p4.onrender.com",
]

SECURE_SSL_REDIRECT = True

SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SECURE = True

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

# ============================================================
# AUTH SETTINGS
# ============================================================
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

# ============================================================
# MEDIA FILES
# ============================================================
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ============================================================
# DATABASE - SQLite مؤقت للسيرفر
# ============================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3'
    }
}

# ============================================================
# INSTALLED APPS
# ============================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',

    # apps
    'cost_centers.apps.CostCentersConfig',
    'accounting.apps.AccountingConfig',
    'products',
    'customers',
    'sales',
    'quotations',
    'company',
    'suppliers',
    'purchase',
    'dashboard',
    'app_settings',
    'journal',
    'lookup',
    'payments',
    'reports',
    'accounts',

    # POS
    'pos',

    # ZATCA
    'zatca',

    # HR
    'hr',

    'django_extensions',
]

SITE_ID = 1
SITE_DOMAIN = "accounting-system.net"

# ============================================================
# MIDDLEWARE
# ============================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',

    # لازم يكون بعد Session مباشرة
    'django.middleware.locale.LocaleMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',

    'accounting.middleware.chart_init_middleware.EnsureChartExistsMiddleware',
    'accounts.middleware.CurrentCompanyMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ============================================================
# URLS / WSGI
# ============================================================
ROOT_URLCONF = 'accounting_web_project.urls'
WSGI_APPLICATION = 'accounting_web_project.wsgi.application'

# ============================================================
# TEMPLATES
# ============================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'layout' / 'templates',
            BASE_DIR / 'templates',
            BASE_DIR / 'accounts' / 'templates',
        ],
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

# ============================================================
# PASSWORD VALIDATION
# ============================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ============================================================
# INTERNATIONALIZATION
# ============================================================
LANGUAGE_CODE = 'ar'

LANGUAGES = [
    ('ar', _('Arabic')),
    ('en', _('English')),
]

TIME_ZONE = 'Asia/Riyadh'

USE_I18N = True
USE_TZ = True

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# ============================================================
# STATIC FILES
# ============================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.StaticFilesStorage"

# ============================================================
# EMAIL CONFIGURATION
# ============================================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 465

EMAIL_USE_SSL = True
EMAIL_USE_TLS = False

EMAIL_HOST_USER = "bassam0500420471@gmail.com"
EMAIL_HOST_PASSWORD = "setvxdopwqjfguqv"
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# ============================================================
# ADVANCED CONFIGURATIONS
# ============================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# تفعيل تفضيل https الافتراضي لحقول الروابط وإسكات تحذير جنجو للأبد
FORMS_URLFIELD_ASSUME_HTTPS = True