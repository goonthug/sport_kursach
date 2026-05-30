"""
Django settings for SportRent project.
"""

from pathlib import Path
import os

from decouple import Config, RepositoryEnv

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# .env: сначала sportrent/.env (рядом с manage.py), иначе корень репозитория
_env_file = None
for _candidate in (BASE_DIR / '.env', BASE_DIR.parent / '.env'):
    if _candidate.is_file():
        _env_file = _candidate
        break

if _env_file is not None:
    config = Config(RepositoryEnv(str(_env_file)))
else:
    from decouple import config as auto_config

    config = auto_config

# Security settings
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Доверяем заголовкам от nginx-прокси (нужно для корректной работы request.is_secure()
# и извлечения реального IP клиента через X-Forwarded-For)
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Автоматическое добавление туннельного хоста (Tuna/ngrok) для webhook'ов.
# URL меняется при каждом перезапуске тоннеля — обновляй только TUNNEL_URL в .env.
TUNNEL_URL = config('TUNNEL_URL', default='')
if TUNNEL_URL:
    _tunnel_host = TUNNEL_URL.replace('https://', '').replace('http://', '').rstrip('/')
    if _tunnel_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_tunnel_host)

    # CSRF_TRUSTED_ORIGINS обязателен в Django 4+ — без него POST через туннель отклоняется.
    CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=lambda v: [x for x in v.split(',') if x])
    if TUNNEL_URL not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(TUNNEL_URL)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    'channels',
    'rest_framework',
    # Local apps
    'core.apps.CoreConfig',
    'users.apps.UsersConfig',
    'inventory.apps.InventoryConfig',
    'rentals.apps.RentalsConfig',
    'reviews.apps.ReviewsConfig',
    'chat.apps.ChatConfig',
    'custom_admin.apps.CustomAdminConfig',
    'ai_search.apps.AiSearchConfig',
    'payments.apps.PaymentsConfig',
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

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'core.context_processors.geo_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database — PostgreSQL (адаптер: psycopg2, пакет psycopg2-binary)
# Параметры задаются в .env (см. .env.example в корне репозитория).
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='sportrent'),
        'USER': config('DB_USER', default='sportrent'),
        'PASSWORD': config('DB_PASSWORD', default='sportrent'),
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=0, cast=int),
    }
}

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Redis
REDIS_URL = config('REDIS_URL', default='redis://127.0.0.1:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
    }
}

# MongoDB
MONGO_URL = config('MONGO_URL', default='mongodb://127.0.0.1:27017/')
MONGO_DB = config('MONGO_DB', default='sportrent_logs')

# Channels (WebSocket) — Redis channel layer
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
        },
    },
}

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Login/Logout URLs
LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'core:home'
LOGOUT_REDIRECT_URL = 'core:home'

# Messages
from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'sportrent.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'mongo': {
            'level': 'WARNING',
            'class': 'core.mongo_logger.MongoDBHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console', 'mongo'],
            'level': 'INFO',
            'propagate': True,
        },
        'users': {
            'handlers': ['file', 'console', 'mongo'],
            'level': 'INFO',
            'propagate': False,
        },
        'inventory': {
            'handlers': ['file', 'console', 'mongo'],
            'level': 'INFO',
            'propagate': False,
        },
        'rentals': {
            'handlers': ['file', 'console', 'mongo'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Session settings (для сохранения сессии после перезагрузки)
SESSION_COOKIE_AGE = 1209600  # 2 недели
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True

# AI-поиск: GigaChat (основной LLM) + Yandex карты/геокодер
#
# os.environ.get() идёт первым: RepositoryEnv читает только из файла и игнорирует
# OS-переменные, которые docker-compose прокидывает через секцию environment:.
# Такая двойная проверка позволяет управлять ключами и через .env, и через docker-compose.
GIGACHAT_CREDENTIALS = (
    os.environ.get('GIGACHAT_CREDENTIALS')
    or config('GIGACHAT_CREDENTIALS', default='')
)
LLM_PROVIDER = (
    os.environ.get('LLM_PROVIDER')
    or config('LLM_PROVIDER', default='gigachat')
)
_rfid_raw = os.environ.get('USE_REGEX_FALLBACK_IN_DEBUG', '')
USE_REGEX_FALLBACK_IN_DEBUG = (
    _rfid_raw.lower() in ('1', 'true', 'yes')
    if _rfid_raw
    else config('USE_REGEX_FALLBACK_IN_DEBUG', default=False, cast=bool)
)
YANDEX_GEOCODER_KEY = config('YANDEX_GEOCODER_KEY', default='')
YANDEX_MAPS_KEY = config('YANDEX_MAPS_KEY', default='')

# ЮКасса — онлайн-оплата (тестовый режим до защиты диплома)
# YOOKASSA_MODE=test — реальных списаний нет, тестовые карты из документации ЮКассы
YOOKASSA_SHOP_ID = (
    os.environ.get('YOOKASSA_SHOP_ID')
    or config('YOOKASSA_SHOP_ID', default='')
)
YOOKASSA_SECRET_KEY = (
    os.environ.get('YOOKASSA_SECRET_KEY')
    or config('YOOKASSA_SECRET_KEY', default='')
)
YOOKASSA_MODE = (
    os.environ.get('YOOKASSA_MODE')
    or config('YOOKASSA_MODE', default='test')
)