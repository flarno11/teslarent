import os
import dj_database_url


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


# https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'i+acxn5(akgsn!sr4^qgf(^m&*@+g1@u^t@=8s@axc41ml*f=s')
DEBUG = os.environ.get('DJANGO_DEBUG', "False") == "True"
print("DEBUG=" + str(DEBUG))

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [os.environ.get('DJANGO_ALLOWED_HOST', None)]
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True  # your JavaScript will need to pull the value from a hidden CSRF token form input on the page instead of from the cookie
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 3600  # TODO: update to 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    X_FRAME_OPTIONS = "DENY"


# Application definition
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'teslarent'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'teslarent.middleware.ExceptionMiddleware',
)

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': True,
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
DATABASES['default'].update(dj_database_url.config(conn_max_age=500))


# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators
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
# https://docs.djangoproject.com/en/1.10/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_ROOT = os.path.join(PROJECT_ROOT, 'staticfiles')
STATIC_URL = '/static/'

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, 'static'),
)

# Simplified static file serving.
# https://warehouse.python.org/project/whitenoise/
STATICFILES_STORAGE = 'whitenoise.django.GzipManifestStaticFilesStorage'


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(module)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'teslaapi': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'manage': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'backgroundTask': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}


TESLA_CLIENT_ID = 'e4a9949fcfa04068f59abb5a658f2bac0a3428e4652315490b659d5ab3f35a9e'
TESLA_CLIENT_SECRET = 'c75f14bbadc8bee3a7594412c31416f8300256d7668ea7e6e7f06727bfb9d220'
