from pathlib import Path
import os

# =========================================================
# BASE DIRECTORY
# =========================================================
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent


# =========================================================
# SECURITY
# =========================================================
SECRET_KEY = 'django-insecure-change-this-key'

DEBUG = True

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
]


# =========================================================
# ROOT CONFIGURATION (IMPORTANT)
# =========================================================
ROOT_URLCONF = 'Spibeat.urls'
WSGI_APPLICATION = 'Spibeat.wsgi.application'


# =========================================================
# INSTALLED APPS
# =========================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',

    # Your Apps
    'Network.apps.GisAppConfig',
    'Energy_demand.apps.EnergyDemandConfig',
    'account',
    'rest_framework_simplejwt.token_blacklist' # 🔥 REQUIRED
]

from datetime import timedelta

# =========================================================
# REST FRAMEWORK
# =========================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}


# =========================================================
# MIDDLEWARE
# =========================================================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# =========================================================
# TEMPLATES (UPDATED FOR REACT)
# =========================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',

       
            
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# =========================================================
# DATABASE
# =========================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# =========================================================
# PASSWORD VALIDATION
# =========================================================
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


# =========================================================
# INTERNATIONALIZATION
# =========================================================
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True
USE_TZ = True


# =========================================================
# STATIC FILES (UPDATED FOR REACT)
# =========================================================
STATIC_URL = '/static/'


STATICFILES_DIRS = [
    BASE_DIR / "frontend_build" / "static"
]

STATIC_ROOT = BASE_DIR / "staticfiles"
# =========================================================
# MEDIA FILES
# =========================================================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"


# =========================================================
# FILE UPLOAD SIZE LIMIT
# =========================================================
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600


# =========================================================
# CORS SETTINGS
# =========================================================
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True


# =========================================================
# CSRF SETTINGS
# =========================================================
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"


# =========================================================
# DEFAULT PRIMARY KEY
# =========================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# =========================================================
# GOOGLE EARTH ENGINE
# =========================================================
EE_SERVICE_ACCOUNT_FILE = os.path.join(
    BASE_DIR,
    "credentials",
    "service-account.json"
)

EE_PROJECT_ID = "spibeat"

# Email Setup 
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'ravijavadevlopernamdev@gmail.com'
EMAIL_HOST_PASSWORD = 'aagzwuwvwfhqlpxz'

# Authentication 
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    )
    ,
    
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',   # 🔐 GLOBAL LOCK
    ),
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),

    "AUTH_HEADER_TYPES": ("Bearer",),

    # 🔐 SECURITY IMPROVEMENTS (YOU ARE MISSING THIS)
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,

    # optional but recommended
    "UPDATE_LAST_LOGIN": True,
}