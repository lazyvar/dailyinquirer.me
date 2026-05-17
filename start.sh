#!/bin/sh
set -e

python manage.py migrate --noinput

exec gunicorn dailyinquirer.wsgi --bind 0.0.0.0:8000
