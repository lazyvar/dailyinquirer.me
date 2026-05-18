from .base import *

DEBUG = True

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

# Sent emails are captured in memory and browsable at /mailbox/.
# Requires the dev dependency: pip install -r requirements-dev.txt
INSTALLED_APPS.append('django_mail_viewer')

EMAIL_BACKEND = 'django_mail_viewer.backends.locmem.EmailBackend'

SITE_URL = 'http://localhost:8000'
