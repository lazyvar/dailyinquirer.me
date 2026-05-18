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

# Run the Django test suite. Any arguments are passed through to manage.py
# test, so `./test.sh core.tests.EmailConfirmationTests` runs a single class.
exec $PYTHON manage.py test "$@"
