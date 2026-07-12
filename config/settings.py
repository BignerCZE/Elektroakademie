"""
Django settings for config project.

Django 6.0.4
"""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


# -----------------------------------------------------------------------------
# Zabezpečení a prostředí
# -----------------------------------------------------------------------------

SECRET_KEY = "h3)_7-)0-@qb)^s=&+&9o#j_m8y#yd9ee$1cv@yi94p=27)r66"

DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "bignercze.pythonanywhere.com",
]

CSRF_TRUSTED_ORIGINS = [
    "https://bignercze.pythonanywhere.com",
]

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)


# -----------------------------------------------------------------------------
# Aplikace
# -----------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "courses",
]


# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"


# -----------------------------------------------------------------------------
# Šablony
# -----------------------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# -----------------------------------------------------------------------------
# Databáze
# -----------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# -----------------------------------------------------------------------------
# Uživatelský model a přihlášení
# -----------------------------------------------------------------------------

AUTH_USER_MODEL = "courses.CustomUser"

LOGIN_URL = "/prihlaseni/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"


# -----------------------------------------------------------------------------
# Validace hesel
# -----------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
        "OPTIONS": {
            "min_length": 10,
        },
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# -----------------------------------------------------------------------------
# Jazyk a čas
# -----------------------------------------------------------------------------

LANGUAGE_CODE = "cs"

TIME_ZONE = "Europe/Prague"

USE_I18N = True
USE_TZ = True


# -----------------------------------------------------------------------------
# Statické soubory
# -----------------------------------------------------------------------------

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "courses" / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"


# -----------------------------------------------------------------------------
# Relace, cookies a produkční HTTPS
# -----------------------------------------------------------------------------

SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_SAVE_EVERY_REQUEST = True

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG

SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "SAMEORIGIN"


# -----------------------------------------------------------------------------
# Nastavení testů
# -----------------------------------------------------------------------------

QUIZ_PASS_PERCENTAGE = 80

QUIZ_CATEGORY_COUNTS = [
    ("obecne", 8),
    ("zdravotni", 2),
]


# -----------------------------------------------------------------------------
# Evidenční čísla a aktivace
# -----------------------------------------------------------------------------

REGISTRATION_NUMBER_PREFIX = "EA"
CERTIFICATE_PREFIX = "EA"

ACTIVATION_LINK_VALID_DAYS = 30


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"