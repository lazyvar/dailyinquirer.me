from .base import *
import dj_database_url

SECRET_KEY = os.environ.get('SECRET_KEY', SECRET_KEY)

DEBUG = os.environ.get('DEBUG', False)

ALLOWED_HOSTS = ['dailyinquirer.me', 'www.dailyinquirer.me']

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
