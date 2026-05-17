from .base import *
import dj_database_url

SECRET_KEY = os.environ.get('SECRET_KEY', SECRET_KEY)

DEBUG = os.environ.get('DEBUG') == 'True'

ALLOWED_HOSTS = [
    'dailyinquirer.me',
    'www.dailyinquirer.me',
    'dailyinquirer.fly.dev',
]

CSRF_TRUSTED_ORIGINS = [
    'https://dailyinquirer.me',
    'https://www.dailyinquirer.me',
    'https://dailyinquirer.fly.dev',
]

SECURE_SSL_REDIRECT = True

# Fly terminates TLS at its proxy and forwards over plain HTTP with this
# header set. Without it, SECURE_SSL_REDIRECT causes an infinite redirect loop.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# db
db_from_env = dj_database_url.config()

DATABASES['default'].update(db_from_env)

# mailgun email

MAILGUN_ACCESS_KEY = os.environ.get('MAILGUN_ACCESS_KEY', None)

INSTALLED_APPS.append("anymail")

ANYMAIL = {
    "MAILGUN_API_KEY": MAILGUN_ACCESS_KEY,
    "MAILGUN_SENDER_DOMAIN": 'dailyinquirer.me',
}

EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
