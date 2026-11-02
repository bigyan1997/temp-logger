"""
Django settings for the Achieve Temperature Logger.
"""

from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR.parent / 'frontend' / 'dist'

SECRET_KEY = config('DJANGO_SECRET_KEY', default='dev-only-secret-key-change-me')

DEBUG = config('DJANGO_DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'accounts',
    'setup',
    'readings',
    'audit',
    'reports',
    'alerts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

AUTH_USER_MODEL = 'accounts.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'login': '10/min',
    },
}

# The Vite dev server (port 5173) proxies /api to Django, so requests are
# same-origin and no CORS setup is needed. In production Django serves the
# built frontend itself.
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS', default='http://localhost:5173,http://127.0.0.1:5173', cast=Csv()
)

# Staff stay signed in on their phones for a week; the session slides forward
# each time they use the app.
SESSION_COOKIE_AGE = config('SESSION_COOKIE_AGE', default=60 * 60 * 24 * 7, cast=int)
SESSION_SAVE_EVERY_REQUEST = True

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [FRONTEND_DIST],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='temp_logger'),
        'USER': config('DB_USER', default='temp_logger'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': config('DB_PORT', default='5432'),
    }
}


# Quick local test runs without Postgres: USE_SQLITE=1 python manage.py test
# Never set this on the orders PC; real data lives in Postgres.
if config('USE_SQLITE', default=False, cast=bool):
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'test.sqlite3'}}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'en-au'
TIME_ZONE = 'Australia/Sydney'
USE_I18N = True
USE_TZ = True


STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = (
    [('assets', FRONTEND_DIST / 'assets')] if (FRONTEND_DIST / 'assets').exists() else []
)

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Where the 4-weekly report PDFs go (see docs/DEPLOYMENT.md). They are always kept in the project's
# report_exports folder; the other two are optional extra copies (empty means not used).
REPORTS_LOCAL_DIR = BASE_DIR.parent / 'report_exports'
REPORTS_EXPORT_DIR = config('REPORTS_EXPORT_DIR', default='')  # a folder, e.g. Google Drive for desktop
GOOGLE_DRIVE_FOLDER_ID = config('GOOGLE_DRIVE_FOLDER_ID', default='')  # upload straight to this Drive folder
GOOGLE_SERVICE_ACCOUNT_FILE = config('GOOGLE_SERVICE_ACCOUNT_FILE', default='')  # the key file, kept outside the repo

# Alert emails (see docs/DEPLOYMENT.md). With no EMAIL_HOST they are only printed in the server window.
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
DEFAULT_FROM_EMAIL = config('EMAIL_FROM', default=EMAIL_HOST_USER or 'temperature-logger@localhost')
EMAIL_BACKEND = (
    'django.core.mail.backends.smtp.EmailBackend' if EMAIL_HOST else 'django.core.mail.backends.console.EmailBackend'
)
