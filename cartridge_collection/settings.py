"""
Django settings for cartridge_collection project.
"""

from pathlib import Path
import os
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Enhanced environment variable handling
# Using django-environ to simplify environment variable management
env = environ.Env(
    # Set casting and default values
    DEBUG=(bool, True),  # Default to True for local development
    SECRET_KEY=(str, 'django-insecure-$!m(uuwo%wh)!0z=a+9x*k=o6@y#%ku=uk6!d4_(aad8mzwl4@'),
    ALLOWED_HOSTS=(list, ['127.0.0.1', 'localhost']),  # Safe defaults for local development
    USE_POSTGRES=(bool, False),  # Keep your existing local DB setup option
)

# Read .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    
    # My apps
    'collection',
]

# Conditionally add debug_toolbar for development only
# This avoids errors in production where debug_toolbar might not be installed
# Not installing debug_toolbar even in debug mode because of performance.
# if DEBUG:
#     INSTALLED_APPS.append('debug_toolbar')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Add debug toolbar middleware only in debug mode
# Not installing debug_toolbar even in debug mode because of performance.
# if DEBUG:
#     MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')

ROOT_URLCONF = 'cartridge_collection.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'cartridge_collection.wsgi.application'

# Database configuration that works in both environments
# Use DATABASE_URL environment variable if available (for future Render deployment)
if env('DATABASE_URL', default=None):
    # This will be used in production on Render
    DATABASES = {
        'default': env.db(),
    }
# Use PostgreSQL for local development if specified in .env
elif env('USE_POSTGRES', default=False):
    # This maintains your current local PostgreSQL setup
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME', default='cartridge_collection'),
            'USER': env('DB_USER', default='django_user'),
            'PASSWORD': env('DB_PASSWORD', default='collectionAdmin'),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='5432'),
        }
    }
# Default to SQLite for simplest local development (if needed)
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
# Define STATIC_ROOT for collectstatic command
# This is where static files will be collected for production
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Enable WhiteNoise's GZip and Brotli compression of static files
WHITENOISE_COMPRESSION_ENABLED = True

# Extra directories for collectstatic to find static files
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'collection'),
    # Add any other app static directories here
]

# Configure WhiteNoise with compression
WHITENOISE_MIDDLEWARE_ENABLED = True
WHITENOISE_USE_FINDERS = True

# Use appropriate static file storage based on environment
if DEBUG:
    # Use simpler storage in development - still compressed but doesn't create manifest files
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
else:
    # Use full compression and manifest for production
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configure debug toolbar for development
if DEBUG:
    INTERNAL_IPS = ['127.0.0.1']

# Authentication settings
LOGIN_REDIRECT_URL = '/'  # Default redirect if no 'next' parameter
LOGOUT_REDIRECT_URL = '/'  # Redirect to home page after logout

# Add this to your settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'level': 'ERROR',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'ERROR',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'collection': {  # Your app name
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

