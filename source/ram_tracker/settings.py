"""
Django settings for RAM Price Tracker

Stack: Django 5.2 LTS + django-mongodb-backend 5.2 (official MongoDB backend,
built on PyMongo) + MongoDB 6.0 / 7.0 / 8.0.

Anything that differs between machines (MongoDB connection string, secret key,
debug mode) is read from environment variables so nothing sensitive is
committed to Git.  Sensible local-development defaults are provided.
"""

import os
from pathlib import Path

from django_mongodb_backend import parse_uri

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default):
    """Read a True/False environment variable."""
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
# The fallback key is for local development only.  Set DJANGO_SECRET_KEY in
# any real deployment.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-only-key-change-me-in-production",
)
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]

# --------------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------------
# The three contrib apps are replaced by MongoDB-aware AppConfig subclasses
# (see ram_tracker/apps.py) so that their models use ObjectId primary keys.
INSTALLED_APPS = [
    "ram_tracker.apps.MongoAdminConfig",
    "ram_tracker.apps.MongoAuthConfig",
    "ram_tracker.apps.MongoContentTypesConfig",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "tracker",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ram_tracker.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "tracker.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "ram_tracker.wsgi.application"

# --------------------------------------------------------------------------
# Database: MongoDB through django-mongodb-backend
# --------------------------------------------------------------------------
# MONGODB_URI examples:
#   local server  : mongodb://localhost:27017
#   Atlas cluster : mongodb+srv://<user>:<password>@<cluster>.mongodb.net
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_NAME = os.environ.get("MONGODB_NAME", "ram_price_tracker")

DATABASES = {
    "default": parse_uri(MONGODB_URI, db_name=MONGODB_NAME),
}

# Every model uses an ObjectId primary key (AutoField is unsupported).
DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"

# Django's built-in apps ship SQL-style migrations that assume integer keys.
# These Mongo-specific copies (generated with makemigrations) replace them.
MIGRATION_MODULES = {
    "admin": "mongo_migrations.admin",
    "auth": "mongo_migrations.auth",
    "contenttypes": "mongo_migrations.contenttypes",
}

# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "tracker:home"
LOGOUT_REDIRECT_URL = "tracker:home"

# --------------------------------------------------------------------------
# Internationalisation
# --------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Bahrain"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------
# Static files (Bootstrap is vendored in static/vendor so the app works offline)
# --------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# --------------------------------------------------------------------------
# Application-specific settings (used by tracker/)
# --------------------------------------------------------------------------
CURRENCY_SYMBOL = "BHD "  # display only; prices are plain decimals
PRODUCTS_PER_PAGE = 12

# "Potential deal" calculation (documented in README and tracker/services.py):
#   deal  <=>  current best price is at least DEAL_THRESHOLD_PERCENT % below the
#              average of all price records from the last DEAL_WINDOW_DAYS days,
#              and at least DEAL_MIN_RECORDS records exist in that window.
DEAL_WINDOW_DAYS = 90
DEAL_THRESHOLD_PERCENT = 10
DEAL_MIN_RECORDS = 3
