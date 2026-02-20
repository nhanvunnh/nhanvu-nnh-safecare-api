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
    "image_gateway",
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
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

APP_NAME = os.environ.get("APP_NAME", "image")
APP_ENV = os.environ.get("APP_ENV", "development")
BASE_PATH = os.environ.get("BASE_PATH", "/image")

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.environ.get("MONGO_DB", "image_gateway")

ENABLE_S3 = os.environ.get("ENABLE_S3", "1") in {"1", "true", "True"}
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "")
AWS_BUCKET = os.environ.get("AWS_BUCKET", "")
if AWS_BUCKET and not AWS_BUCKET.endswith("/"):
    AWS_BUCKET = AWS_BUCKET + "/"

GOOD_IMAGES_USE_DRIVE = os.environ.get("GOOD_IMAGES_USE_DRIVE", "1") in {"1", "true", "True"}
GOOD_IMAGES_DRIVE_FOLDER_ID = os.environ.get("GOOD_IMAGES_DRIVE_FOLDER_ID", "")
GNH_IMAGES_DRIVE_FOLDER_ID = os.environ.get("GNH_IMAGES_DRIVE_FOLDER_ID", "")
GOOGLE_SERVICE_ACCOUNT_FILE = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    str(BASE_DIR / "secrets" / "google-service-account.json"),
)

GNH_IMAGE_CACHE_DIR = os.environ.get("GNH_IMAGE_CACHE_DIR", str(BASE_DIR / "media" / "gnh_images"))
GOOD_IMAGE_CACHE_DIR = os.environ.get("GOOD_IMAGE_CACHE_DIR", str(BASE_DIR / "media" / "good_images_cache"))
GNH_IMAGE_CACHE_MAX_BYTES = int(os.environ.get("GNH_IMAGE_CACHE_MAX_BYTES", str(2 * 1024 * 1024 * 1024)))
GNH_IMAGE_CACHE_MAX_DAYS = int(os.environ.get("GNH_IMAGE_CACHE_MAX_DAYS", "30"))
GOOD_IMAGE_CACHE_MAX_BYTES = int(os.environ.get("GOOD_IMAGE_CACHE_MAX_BYTES", str(10 * 1024 * 1024 * 1024)))
GOOD_IMAGE_CACHE_MAX_DAYS = int(os.environ.get("GOOD_IMAGE_CACHE_MAX_DAYS", "7"))

MEDIA_ROOT = os.environ.get("MEDIA_ROOT", str(BASE_DIR / "media"))

USE_X_FORWARDED_HOST = os.environ.get("USE_X_FORWARDED_HOST", "false").lower() in {"1", "true"}
proxy_header = os.environ.get("SECURE_PROXY_SSL_HEADER")
if proxy_header:
    header_parts = [part.strip() for part in proxy_header.split(",") if part.strip()]
    SECURE_PROXY_SSL_HEADER = tuple(header_parts[:2]) if len(header_parts) >= 2 else None
else:
    SECURE_PROXY_SSL_HEADER = None
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]
