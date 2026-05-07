FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# Copy project
COPY . .

# Default envs (can be overridden)
ENV DJANGO_SETTINGS_MODULE=core.settings \
    DJANGO_ALLOWED_HOSTS=* \
    DJANGO_DEBUG=0 \
    DJANGO_DB_PATH=/opt/app/data/db.sqlite3

# Ensure data dir exists (for sqlite default path)
RUN mkdir -p /opt/app/data

EXPOSE 1337

# Run migrations then start Gunicorn
CMD sh -c "python manage.py migrate && gunicorn --workers 3 --bind 0.0.0.0:1337 core.wsgi:application"