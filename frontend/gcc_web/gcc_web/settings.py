import os

import dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

dotenv_file = os.path.join(BASE_DIR, ".env")
if os.path.isfile(dotenv_file):
    dotenv.load_dotenv(dotenv_file)

    SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

    RECAPTCHA_PUBLIC_KEY = os.getenv("CAPTCHA_SITE_KEY")
    RECAPTCHA_PRIVATE_KEY = os.getenv("CAPTCHA_SECRET_KEY")

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get("RDS_DB_NAME"),
            "USER": os.environ.get("RDS_DB_USER"),
            "PASSWORD": os.environ.get("RDS_DB_PASS"),
            "HOST": os.environ.get("RDS_DB_HOSTNAME"),
            "PORT": os.environ.get("RDS_DB_PORT"),
            "OPTIONS": {"init_command": "SET sql_mode='STRICT_TRANS_TABLES'"},
        }
    }

    LOGIN_URL = "/"

DEBUG = True

ALLOWED_HOSTS = [
    "gatorcompcloud.com",
    "www.gatorcompcloud.com",
    "127.0.0.1",
]

INSTALLED_APPS = [
    "gcc.apps.GccConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "widget_tweaks",
    "fernet_fields",
    "captcha",
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

ROOT_URLCONF = "gcc_web.urls"

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
    },
]

WSGI_APPLICATION = "gcc_web.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/New_York"

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = STATIC_ROOT + MEDIA_URL
