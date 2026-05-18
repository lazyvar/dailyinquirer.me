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
# An optional "-p <port>" overrides the default port 8000.
if [ "$1" = "dev" ]; then
    PORT=8000
    shift
    while [ $# -gt 0 ]; do
        case "$1" in
            -p)
                PORT="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1" >&2
                exit 1
                ;;
        esac
    done
    exec $PYTHON manage.py runserver "0.0.0.0:$PORT"
fi

# Run the hourly prompt cron alongside the web server (production only — the
# dev branch above execs and never reaches here).
supercronic /app/crontab &

exec gunicorn dailyinquirer.wsgi --bind 0.0.0.0:8000
