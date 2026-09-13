"""
PentestNotes — Django settings.

Tuned for a single-VM, self-hosted deployment on Linode:
  * SQLite (one file, no separate DB server) — data persists on disk.
  * Reads secrets and host-specific values from environment variables so the
    same code runs locally and in production without edits.
Everything here is deliberately boring and long-lived.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    return os.environ.get(key, str(default)).lower() in ("1", "true", "yes", "on")


# --- Core -------------------------------------------------------------------
# In production, set PN_SECRET_KEY in the environment (see deploy/ notes).
SECRET_KEY = env("PN_SECRET_KEY", "dev-insecure-key-change-me-in-production")
DEBUG = env_bool("PN_DEBUG", True)

# Comma-separated list, e.g. "notes.example.com,203.0.113.10"
ALLOWED_HOSTS = [h.strip() for h in env("PN_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# Caddy terminates TLS and proxies to us; trust its forwarded origin.
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env("PN_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

# --- Applications -----------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "notes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serve static files without a separate server
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
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "notes.context.workspace_tree",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database (SQLite, persistent file on disk) -----------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": env("PN_DB_PATH", str(BASE_DIR / "data" / "db.sqlite3")),
        "OPTIONS": {
            # WAL improves concurrent read performance for a read-heavy wiki.
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
            "timeout": 20,
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Passwords --------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- I18N / TZ --------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = env("PN_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

# --- Static & media ---------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = env("PN_STATIC_ROOT", str(BASE_DIR / "staticfiles"))
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "media/"
MEDIA_ROOT = env("PN_MEDIA_ROOT", str(BASE_DIR / "media"))

# Cap uploads so a single file can't fill the disk unexpectedly (default 50 MB).
PN_MAX_UPLOAD_MB = int(env("PN_MAX_UPLOAD_MB", "50"))
DATA_UPLOAD_MAX_MEMORY_SIZE = PN_MAX_UPLOAD_MB * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# --- Auth flow --------------------------------------------------------------
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# --- Production hardening (enabled when PN_DEBUG is off) ---------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("PN_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(env("PN_HSTS_SECONDS", "2592000"))  # 30 days
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    X_FRAME_OPTIONS = "DENY"
