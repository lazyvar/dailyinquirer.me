FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=dailyinquirer.settings.prod

WORKDIR /app

# Install supercronic — a container-friendly cron runner. The web machine is
# always on (min_machines_running = 1) and holds the SQLite volume, so the
# hourly prompt job runs in-process here. Pinned; bump deliberately.
ADD https://github.com/aptible/supercronic/releases/download/v0.2.33/supercronic-linux-amd64 /usr/local/bin/supercronic
RUN echo "71b0d58cc53f6bd72cf2f293e09e294b79c666d8  /usr/local/bin/supercronic" | sha1sum -c - \
    && chmod +x /usr/local/bin/supercronic

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

RUN chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]
