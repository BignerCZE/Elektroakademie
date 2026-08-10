"""
Django settings for config project.

Django 6.0.4
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent


# -----------------------------------------------------------------------------
# Proměnné prostředí
# -----------------------------------------------------------------------------

# Lokálně se načítá BASE_DIR/.env.
# V produkci lze cestu přesměrovat přes ELEKTROAKADEMIE_ENV_FILE,
# např. na /home/<uzivatel>/.elektroakademie.env na PythonAnywhere.
ENV_FILE = os.getenv("ELEKTROAKADEMIE_ENV_FILE")

if ENV_FILE:
    load_dotenv(
        dotenv_path=ENV_FILE,
        override=False,
    )
else:
    load_dotenv(
        dotenv_path=BASE_DIR / ".env",
        override=False,
    )


# -----------------------------------------------------------------------------
# Zabezpečení a prostředí
# -----------------------------------------------------------------------------

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    raise ImproperlyConfigured(
        "Chybí povinná proměnná DJANGO_SECRET_KEY."
    )

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

SITE_URL = os.getenv(
    "SITE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

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
            "courses.validators."
            "ElektroakademiePasswordValidator"
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

# -----------------------------------------------------------------------------
# E-mailový transport a SMTP
# -----------------------------------------------------------------------------

EMAIL_TRANSPORT = os.getenv(
    "EMAIL_TRANSPORT",
    "preview",
).strip().lower()

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)

EMAIL_HOST = os.getenv(
    "EMAIL_HOST",
    "",
)

EMAIL_PORT = int(
    os.getenv(
        "EMAIL_PORT",
        "587",
    )
)

EMAIL_HOST_USER = os.getenv(
    "EMAIL_HOST_USER",
    "",
)

EMAIL_HOST_PASSWORD = os.getenv(
    "EMAIL_HOST_PASSWORD",
    "",
)

EMAIL_USE_TLS = os.getenv(
    "EMAIL_USE_TLS",
    "True",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}

EMAIL_USE_SSL = os.getenv(
    "EMAIL_USE_SSL",
    "False",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}

EMAIL_TIMEOUT = int(
    os.getenv(
        "EMAIL_TIMEOUT",
        "20",
    )
)

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    EMAIL_HOST_USER or "webmaster@localhost",
)

SERVER_EMAIL = os.getenv(
    "SERVER_EMAIL",
    DEFAULT_FROM_EMAIL,
)

# -----------------------------------------------------------------------------
# Odesílací adresy podle typu e-mailu
# -----------------------------------------------------------------------------

EMAIL_FROM_ACTIVATION = os.getenv(
    "EMAIL_FROM_ACTIVATION",
    DEFAULT_FROM_EMAIL,
)

EMAIL_FROM_INVOICES = os.getenv(
    "EMAIL_FROM_INVOICES",
    DEFAULT_FROM_EMAIL,
)

EMAIL_FROM_CERTIFICATES = os.getenv(
    "EMAIL_FROM_CERTIFICATES",
    DEFAULT_FROM_EMAIL,
)

# Volitelná společná adresa pro odpovědi.
# Prázdná hodnota znamená, že Reply-To nebude explicitně nastaveno.
EMAIL_REPLY_TO = os.getenv(
    "EMAIL_REPLY_TO",
    "",
)
