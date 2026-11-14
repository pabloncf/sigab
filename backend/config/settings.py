import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-development-key")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [
    x for x in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if x
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "sigab",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "sigab.middleware.CorrelationIdMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "sigab.authentication.SessionVersionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
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
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"

database_url = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
    from urllib.parse import urlparse

    parsed = urlparse(database_url)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username,
            "PASSWORD": parsed.password,
            "HOST": parsed.hostname,
            "PORT": parsed.port or 5432,
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    }

AUTH_USER_MODEL = "sigab.Account"
AUTHENTICATION_BACKENDS = ["sigab.authentication.ThrottledModelBackend"]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 8 * 60 * 60
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_FAILURE_VIEW = "sigab.api.views.csrf_failure"

# Facial biometrics (ADR 0008). Checkout and return require an approved face verification
# or an approved signed term. Production keeps the requirement on; disabling it is only
# for development and for tests of the underlying movement rules.
SIGAB_REQUIRE_IDENTITY_CHECK = os.getenv("SIGAB_REQUIRE_IDENTITY_CHECK", "true").lower() == "true"
# Fernet key (urlsafe base64, 32 bytes) used to encrypt biometric templates. Keep it out of
# the database and of database backups.
SIGAB_BIOMETRIC_KEY = os.getenv("SIGAB_BIOMETRIC_KEY", "")
# Dotted path of the face engine; empty means no engine configured (verification unavailable).
SIGAB_FACE_ENGINE = os.getenv("SIGAB_FACE_ENGINE", "")
SIGAB_FACE_DETECTOR_MODEL = os.getenv("SIGAB_FACE_DETECTOR_MODEL", "")
SIGAB_FACE_RECOGNIZER_MODEL = os.getenv("SIGAB_FACE_RECOGNIZER_MODEL", "")
SIGAB_FACE_THRESHOLD = float(os.getenv("SIGAB_FACE_THRESHOLD", "0.363"))
SIGAB_FACE_MAX_IMAGE_BYTES = 2 * 1024 * 1024
# The counter identifies the person first (registration + face) and then picks materials;
# the approved verification stays usable for this window, once, by the same operator.
SIGAB_FACE_VERIFICATION_TTL_SECONDS = int(os.getenv("SIGAB_FACE_VERIFICATION_TTL_SECONDS", "600"))
SIGAB_BIOMETRIC_LEGAL_BASIS = os.getenv("SIGAB_BIOMETRIC_LEGAL_BASIS", "lgpd-art-11-ii-g")
DATA_UPLOAD_MAX_MEMORY_SIZE = 3 * 1024 * 1024

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"correlation": {"()": "sigab.observability.CorrelationIdFilter"}},
    "formatters": {"json": {"()": "sigab.observability.JsonFormatter"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["correlation"],
            "formatter": "json",
        },
        "null": {"class": "logging.NullHandler"},
    },
    "root": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
    "loggers": {
        # Replace Django's plain-text default handlers so every line is JSON.
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        # The request middleware already logs one line per request.
        "django.server": {"handlers": ["null"], "propagate": False},
    },
}
