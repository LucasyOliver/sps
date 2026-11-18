# ==========================================================================
# SPS (Sistema Para Salões) — Dockerfile Oficial de Produção (Python 3.13)
# Estratégia de Staticfiles: collectstatic no build da imagem com WhiteNoise
# ==========================================================================
FROM python:3.13.6-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r sps && useradd -r -g sps -d /app -s /sbin/nologin sps

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Executa collectstatic durante o build sem exigir banco de dados ativo
RUN SECRET_KEY="build-only-collectstatic-key" \
    DEBUG="False" \
    USE_SQLITE_FALLBACK="True" \
    python manage.py collectstatic --noinput

RUN mkdir -p /app/media && chown -R sps:sps /app

USER sps

EXPOSE 8000

CMD ["sh", "-c", "python manage.py wait_for_db && gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60"]
