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
# SECURITY
# ============================================================
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-insecure-key-for-local-only"
)

DEBUG = True  # مؤقتًا فقط، لاحقًا False في الإنتاج

ALLOWED_HOSTS = [
    ".onrender.com",
    "127.0.0.1",
    "localhost",
]

# بعد تسجيل الدخول، تحويل المستخدم مباشرة للوحة التحكم
LOGIN_REDIRECT_URL = '/dashboard/'

# ============================================================
# DATABASE - SQLite مؤقت للسيرفر
# ============================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': r'E:\accounting_web\db.sqlite3',  # ← المسار الصحيح لقاعدة البيانات
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

    # apps
    'cost_centers.apps.CostCentersConfig',
    'accounting',
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

    # ⭐ POS
    'pos',

    # 🟢 HR الجديد
    'hr',   # هنا ضيفنا تطبيق الموارد البشرية
]

# ============================================================
# MIDDLEWARE
# ============================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',

    # WhiteNoise
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',

    # ✅ إنشاء شجرة الحسابات تلقائيًا عند أول تشغيل
    'accounting.middleware.chart_init_middleware.EnsureChartExistsMiddleware',

    'django.middleware.locale.LocaleMiddleware',
    'accounting.language_middleware.SettingsLanguageMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
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
            BASE_DIR / 'templates',   # مجلد القوالب العام
            BASE_DIR / 'layout',
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
EMAIL_HOST = "smtp.gmail.com"  # يمكن تغييره حسب السيرفر
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "your_email@gmail.com")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "your_email_password")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# ============================================================
# DEFAULT FIELD
# ============================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
