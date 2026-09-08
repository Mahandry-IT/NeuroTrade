# ── Stage 1: build dependencies ──
FROM python:3.12-slim AS builder

WORKDIR /app

# System deps pour psycopg2 + cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime minimal ──
FROM python:3.12-slim

WORKDIR /app

# Runtime deps pour psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copier les packages installés
COPY --from=builder /install /usr/local

# Copier le code
COPY alembic/ alembic/
COPY alembic.ini .
COPY app/ app/

# Créer un user non-root
RUN groupadd -r botuser && useradd -r -g botuser botuser
RUN chown -R botuser:botuser /app
USER botuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
