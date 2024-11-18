import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-621mr=g-bw*ojnya^d#0dsj$$k^1bup=mh3jl^+6-i2841&oj$'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    'localhost',
    'openassistants.io',
    'test.openassistants.io',
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'oa.main',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'oa.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'oa/templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'oa.context_processors.user_projects',
            ],
        },
    },
]

ASGI_APPLICATION = 'oa.asgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/


IS_LOCAL = os.getenv("IS_LOCAL", "false").lower() == "true"

if IS_LOCAL:
    # Local settings for static and media files
    STATIC_URL = "/static/"
    STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
    STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
    MEDIA_URL = "/media/"
    MEDIA_ROOT = os.path.join(BASE_DIR, "media")

else:
    BRANCH_NAME = os.getenv("BRANCH_NAME")
    S3_BUCKET_NAME = f"openassistants-{BRANCH_NAME}".lower()

    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_S3_REGION_NAME = os.getenv("AWS_REGION_NAME")

    AWS_STORAGE_BUCKET_NAME = f"openassistants-{BRANCH_NAME}".lower()

    # Use S3 for static and media files
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"

    # Static files (CSS, JavaScript, Images)
    STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"
    STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

    # Media files (Uploaded by users)
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


#
# Settings for the private version
#

SECRET_KEY = '621mr=g-bw*ojnya^d#0dsj$$k^1bup=mh3jl^+6-i2841&oj$!/&T5*=|-R3<'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db-private.sqlite3',
    }
}


INSTALLED_APPS += [
    "django_recaptcha",
    "widget_tweaks",

    'accounts',
]


# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',  # Only log errors for database operations
            'propagate': False,
        },
        'http': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}


LOGIN_URL = 'home'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

SESSION_COOKIE_AGE = 315360000  # 10 years
SESSION_EXPIRE_AT_BROWSER_CLOSE = False


# reCAPTCHA v2
RECAPTCHA_PUBLIC_KEY = os.getenv('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = os.getenv('RECAPTCHA_PRIVATE_KEY')


EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "sesame.backends.ModelBackend",
]

SESAME_MAX_AGE = 300


STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')


try:
    from settings_local import *
except ImportError:
    pass
