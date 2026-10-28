FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBUG=0 \
    SQLITE_PATH=/app/data/db.sqlite3 \
    MEDIA_ROOT=/app/data/media

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Arquivos estáticos (admin) servidos pelo WhiteNoise
RUN SECRET_KEY=build-only python manage.py collectstatic --noinput \
    && chmod +x /app/entrypoint.sh \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /app/data/media \
    && chown -R app:app /app

USER app

VOLUME ["/app/data"]
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
