import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-secret")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") in {"1", "true", "True"}

ALLOWED_HOSTS = [host.strip() for host in os.environ.get("ALLOWED_HOSTS", "*").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "sms_gateway",
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

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "sms_gateway.auth.JWTAuthentication",
        "sms_gateway.auth.ApiKeyAuthentication",
        "sms_gateway.auth.AgentTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

APP_NAME = os.environ.get("APP_NAME", "sms")
APP_ENV = os.environ.get("APP_ENV", "development")
BASE_PATH = os.environ.get("BASE_PATH", "/sms")

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.environ.get("MONGO_DB", "sms_gateway")

JWT_SECRET = os.environ.get("JWT_SECRET", "jwt-secret")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_MINUTES = int(os.environ.get("JWT_ACCESS_MINUTES", "240"))
JWT_ISSUER = os.environ.get("JWT_ISSUER", "").strip()
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "").strip()

LEASE_SECONDS = int(os.environ.get("LEASE_SECONDS", "300"))
AGENT_RATE_LIMIT_PER_MIN = int(os.environ.get("AGENT_RATE_LIMIT_PER_MIN", "10"))
APIKEY_RATE_LIMIT_PER_DAY_DEFAULT = int(os.environ.get("APIKEY_RATE_LIMIT_PER_DAY_DEFAULT", "20000"))
DEFAULT_COUNTRY_PREFIX = os.environ.get("DEFAULT_COUNTRY_PREFIX", "+84")
BLOCK_INTERNATIONAL = os.environ.get("BLOCK_INTERNATIONAL", "1") in {"1", "true", "True"}
ANTI_DUP_MINUTES = int(os.environ.get("ANTI_DUP_MINUTES", "3"))
MAX_RECIPIENTS_PER_REQUEST = int(os.environ.get("MAX_RECIPIENTS_PER_REQUEST", "5000"))
MAX_TEXT_LENGTH = int(os.environ.get("MAX_TEXT_LENGTH", "1600"))

SEED_ADMIN = os.environ.get("SEED_ADMIN", "0") in {"1", "true", "True"}
SEED_ADMIN_USERNAME = os.environ.get("SEED_ADMIN_USERNAME", "admin")
SEED_ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "admin123")

AGENT_REGISTRATION_SECRET = os.environ.get("AGENT_REGISTRATION_SECRET", "")

USE_X_FORWARDED_HOST = os.environ.get("USE_X_FORWARDED_HOST", "false").lower() in {"1", "true"}
proxy_header = os.environ.get("SECURE_PROXY_SSL_HEADER")
if proxy_header:
    header_parts = [part.strip() for part in proxy_header.split(",") if part.strip()]
    SECURE_PROXY_SSL_HEADER = tuple(header_parts[:2]) if len(header_parts) >= 2 else None
else:
    SECURE_PROXY_SSL_HEADER = None
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]
