import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-secret-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "0").lower() in {"1", "true", "yes"}

ALLOWED_HOSTS = [host.strip() for host in os.environ.get("ALLOWED_HOSTS", "*").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "auth_service",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common_auth.middleware.PrincipalMiddleware",
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
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "auth_service.authentication.JWTOrCookieAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "safecare-auth-cache",
    }
}

APP_NAME = os.environ.get("APP_NAME", "auth-service")
APP_ENV = os.environ.get("APP_ENV", "development")

BASE_PATH = os.environ.get("BASE_PATH", "/auth").strip()
if BASE_PATH and not BASE_PATH.startswith("/"):
    BASE_PATH = f"/{BASE_PATH}"
BASE_PATH = BASE_PATH.rstrip("/") or ""
FORCE_SCRIPT_NAME = os.environ.get("FORCE_SCRIPT_NAME") or (BASE_PATH or None)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.environ.get("MONGO_DB", "auth_db")

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "safecare-auth")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "safecare-api")
JWT_ACCESS_MINUTES = int(os.environ.get("JWT_ACCESS_MINUTES", "15"))
JWT_ALGORITHM = "HS256"

COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN", ".safecare.vn")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "1").lower() in {"1", "true", "yes"}
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "Lax")
COOKIE_NAME = "token"

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
MS_CLIENT_ID = os.environ.get("MS_CLIENT_ID", "")
MS_CLIENT_SECRET = os.environ.get("MS_CLIENT_SECRET", "")
MS_TENANT = os.environ.get("MS_TENANT", "common")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@safecare.vn")

CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "https://api.safecare.vn").split(",") if origin.strip()
]
USE_X_FORWARDED_HOST = os.environ.get("USE_X_FORWARDED_HOST", "true").lower() in {"1", "true", "yes"}
proxy_header = os.environ.get("SECURE_PROXY_SSL_HEADER")
if proxy_header:
    header_parts = [part.strip() for part in proxy_header.split(",") if part.strip()]
    if len(header_parts) >= 2:
        SECURE_PROXY_SSL_HEADER = (header_parts[0], header_parts[1])

CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

RATE_LIMIT_LOGIN_PER_MINUTE = int(os.environ.get("RATE_LIMIT_LOGIN_PER_MINUTE", "10"))
RATE_LIMIT_FORGOT_PER_HOUR = int(os.environ.get("RATE_LIMIT_FORGOT_PER_HOUR", "5"))
PASSWORD_RESET_EXP_MINUTES = int(os.environ.get("PASSWORD_RESET_EXP_MINUTES", "20"))
PASSWORD_RESET_URL = os.environ.get("PASSWORD_RESET_URL", "https://api.safecare.vn/auth/reset-password")

OAUTH_REDIRECT_SUCCESS = os.environ.get("OAUTH_REDIRECT_SUCCESS", "https://api.safecare.vn/auth/dashboard")
OAUTH_REDIRECT_ERROR = os.environ.get("OAUTH_REDIRECT_ERROR", "https://api.safecare.vn/auth/login?error=oauth")
