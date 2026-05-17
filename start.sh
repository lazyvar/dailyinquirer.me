#!/bin/sh
set -e

# Prefer the project virtualenv, then python3 (local dev), then python (container image).
if [ -x ".venv/bin/python" ]; then
    PYTHON=.venv/bin/python
elif command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
else
    PYTHON=python
fi

# Repair an inconsistent migration ledger before migrating -- see the
# command's docstring. No-op on consistent and on fresh databases.
$PYTHON manage.py repair_migration_history

$PYTHON manage.py migrate --noinput

# Pass "dev" to run the Django development server (uses settings.local).
if [ "$1" = "dev" ]; then
    exec $PYTHON manage.py runserver 0.0.0.0:8000
fi

# Run the hourly prompt cron alongside the web server (production only — the
# dev branch above execs and never reaches here).
supercronic /app/crontab &

exec gunicorn dailyinquirer.wsgi --bind 0.0.0.0:8000
