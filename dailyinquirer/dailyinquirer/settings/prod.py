from .base import *
import dj_database_url

SECRET_KEY = os.environ.get('SECRET_KEY', SECRET_KEY)

DEBUG = os.environ.get('DEBUG', False)

ALLOWED_HOSTS = ['dailyinquirer.me', 'www.dailyinquirer.me']

db_from_env = dj_database_url.config()

DATABASES = {
    'default': {  }
}
DATABASES['default'].update(db_from_env)

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# STATIC_ROOT = os.path.join(PROJECT_ROOT, 'staticfiles')
# STATIC_URL = '/static/'

# # Extra places for collectstatic to find static files.
# STATICFILES_DIRS = (
#     os.path.join(PROJECT_ROOT, 'static'),
# )

STATICFILES_STORAGE = 'whitenoise.django.GzipManifestStaticFilesStorage'

