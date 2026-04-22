# ============================================================
# Stage 1: Builder — installera beroenden och kompilera
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================
# Stage 2: Runtime — minimal image utan byggverktyg
# ============================================================
FROM python:3.11-slim

WORKDIR /code

# Installera enbart runtime-beroenden för mysqlclient
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Kopiera installerade Python-paket från builder
COPY --from=builder /install /usr/local

# Skapa och använd non-root användare
RUN useradd --no-create-home --shell /bin/false appuser

COPY --chown=appuser:appuser app/ ./app/

USER appuser

EXPOSE 5000

CMD ["python", "-m", "app"]
