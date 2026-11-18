from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.FileAwareEnv(
    DEBUG=(bool, False),
    USE_SQLITE_FALLBACK=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    CSRF_TRUSTED_ORIGINS=(list, ['http://localhost:8000', 'http://127.0.0.1:8000']),
    EMAIL_BACKEND=(str, 'django.core.mail.backends.console.EmailBackend'),
    EMAIL_HOST=(str, 'localhost'),
    EMAIL_PORT=(int, 1025),
    EMAIL_HOST_USER=(str, ''),
    EMAIL_HOST_PASSWORD=(str, ''),
    EMAIL_USE_TLS=(bool, False),
    DEFAULT_FROM_EMAIL=(str, 'nao-responda@sps.local'),
    CELERY_BROKER_URL=(str, 'amqp://sps_mq:sps_mq_dev_password@127.0.0.1:5672//'),
    CELERY_RESULT_BACKEND=(str, 'redis://127.0.0.1:6379/1'),
    REDIS_CACHE_URL=(str, 'redis://127.0.0.1:6379/0'),
    LLM_MODEL=(str, 'a_definir'),
    LLM_API_KEY=(str, ''),
)

env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.FileAwareEnv.read_env(str(env_file))

SECRET_KEY = env('SECRET_KEY', default='sps-insecure-dev-key-only-for-local-bootstrap')
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dj_celery_panel',
    'base.apps.BaseConfig',
    'salons.apps.SalonsConfig',
    'accounts.apps.AccountsConfig',
    'scheduling.apps.SchedulingConfig',
    'catalog.apps.CatalogConfig',
    'clients.apps.ClientsConfig',
    'inventory.apps.InventoryConfig',
    'orders.apps.OrdersConfig',
    'finance.apps.FinanceConfig',
    'fiscal.apps.FiscalConfig',
    'notifications.apps.NotificationsConfig',
    'reports.apps.ReportsConfig',
    'ai_assistant.apps.AiAssistantConfig',
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

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

if env.bool('USE_SQLITE_FALLBACK'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': env.db(
            'DATABASE_URL',
            default='psql://sps_user:sps_dev_password@127.0.0.1:5432/sps_dev',
        )
    }

AUTH_USER_MODEL = 'accounts.User'

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

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'base:home'
LOGOUT_REDIRECT_URL = 'accounts:login'

EMAIL_BACKEND = env('EMAIL_BACKEND')
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env.int('EMAIL_PORT')
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')

CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_ALWAYS_EAGER = env.bool(
    'CELERY_TASK_ALWAYS_EAGER',
    default=env.bool('USE_SQLITE_FALLBACK', default=False),
)
CELERY_BEAT_SCHEDULE = {
    'dispatch-upcoming-appointment-reminders-every-30m': {
        'task': 'notifications.dispatch_upcoming_appointment_reminders_task',
        'schedule': 1800.0,
        'kwargs': {'hours_ahead': 24},
    },
}

LLM_MODEL = env('LLM_MODEL')
LLM_API_KEY = env('LLM_API_KEY')

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
    SECURE_REDIRECT_EXEMPT = [r'^healthz/$', r'^readyz/$']
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
