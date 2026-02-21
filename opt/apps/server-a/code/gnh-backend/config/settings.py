import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-secret")
DEBUG = os.environ.get("DJANGO_DEBUG", "0").lower() in {"1", "true", "yes"}
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("ALLOWED_HOSTS", "*").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "gnh_gateway",
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

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (),
    "DEFAULT_PERMISSION_CLASSES": (),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

APP_NAME = os.environ.get("APP_NAME", "gnh")
APP_ENV = os.environ.get("APP_ENV", "development")
BASE_PATH = os.environ.get("BASE_PATH", "/gnh").strip()
if BASE_PATH and not BASE_PATH.startswith("/"):
    BASE_PATH = f"/{BASE_PATH}"
BASE_PATH = BASE_PATH.rstrip("/") or ""

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://shared_mongo:27017")
MONGO_DB = os.environ.get("MONGO_DB", "db_gnh")

JWT_SECRET = os.environ.get("JWT_SECRET", SECRET_KEY)
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")

GNH_SHEET_NAME = os.environ.get("GNH_SHEET_NAME", "NVC-GIAONHANHANG")
GNH_WORKSHEET_NAME = os.environ.get("GNH_WORKSHEET_NAME", "GNH")
GOOGLE_SERVICE_ACCOUNT_FILE = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    str(BASE_DIR / "secrets" / "google-service-account.json"),
)
GNH_SYNC_INTERVAL = int(os.environ.get("GNH_SYNC_INTERVAL", "30"))
GNH_SYNC_LOOP = os.environ.get("GNH_SYNC_LOOP", "0").lower() in {"1", "true", "yes"}

IMAGE_SERVICE_BASE_URL = os.environ.get("IMAGE_SERVICE_BASE_URL", "http://svc_image:8000").rstrip("/")
SHEET_SYNC_ENABLED = os.environ.get("SHEET_SYNC_ENABLED", "1").lower() in {"1", "true", "yes"}
SHEET_SYNC_BASE_URL = os.environ.get("SHEET_SYNC_BASE_URL", "http://svc_sheet_sync:8000/sheet")
SHEET_SYNC_SERVICE_TOKEN = os.environ.get("SHEET_SYNC_SERVICE_TOKEN", "")

USE_X_FORWARDED_HOST = os.environ.get("USE_X_FORWARDED_HOST", "false").lower() in {"1", "true", "yes"}
proxy_header = os.environ.get("SECURE_PROXY_SSL_HEADER")
if proxy_header:
    header_parts = [part.strip() for part in proxy_header.split(",") if part.strip()]
    SECURE_PROXY_SSL_HEADER = tuple(header_parts[:2]) if len(header_parts) >= 2 else None
else:
    SECURE_PROXY_SSL_HEADER = None
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]
