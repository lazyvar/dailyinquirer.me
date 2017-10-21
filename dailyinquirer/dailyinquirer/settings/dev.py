from .base import *

DEBUG = True

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

# mailgun email

MAILGUN_ACCESS_KEY = os.environ.get('MAILGUN_ACCESS_KEY', None)

INSTALLED_APPS.append("anymail")

ANYMAIL = {
    "MAILGUN_API_KEY": MAILGUN_ACCESS_KEY,
    "MAILGUN_SENDER_DOMAIN": 'dailyinquirer.me',
}

EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend" 
